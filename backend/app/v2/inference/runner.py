"""Resumable, cached generation runs over a VeriAudit-X file.

A run is defined by an experiment config (configs/experiments/*.yaml) and a model
manifest (configs/models.yaml). Raw generations are appended to
results/v2/runs/<run_id>/generations.jsonl as soon as each one returns, before any
judging. The run is resumable: generation IDs are deterministic, successful ones are
skipped, and failed ones are retried up to `max_attempts` (each attempt is appended;
`load_generations` keeps one record per ID).

Safeguards (protocol §7, §12):
- Hugging Face models (transformers / vllm) must be pinned to a 40-hex commit revision,
  unless the config sets `allow_unpinned_revisions: true` (debug runs only; the run
  manifest then says so and the analysis refuses it).
- The `fake` test backend runs only when named explicitly with --models; its outputs are
  marked `is_test_fixture` and analyses refuse them.
- A run manifest (run_manifest.json) records config hash, dataset path/hash/version, git
  commit, runtime environment, per-model backend description (incl. chat-template hash)
  and completion status. Only `status: complete` runs are accepted by the analysis.

    PYTHONPATH=backend python -m app.v2.inference.runner configs/experiments/main_study.yaml --models qwen3_8b
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import yaml

from app.v2.inference.backends import BackendError, FakeBackend, GenResult, build_backend
from app.v2.records import Decoding, Generation, append_jsonl
from app.veriaudit_x.validation import validate_file

ROOT = Path(__file__).resolve().parents[4]
PINNED_REVISION = re.compile(r"^[0-9a-f]{40}$")
HF_BACKENDS = {"transformers", "vllm"}
RUN_MANIFEST = "run_manifest.json"


class RunConfigError(SystemExit):
    pass


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def generation_id(run_id: str, model_key: str, record_id: str, sample_index: int) -> str:
    return hashlib.sha256(f"{run_id}|{model_key}|{record_id}|{sample_index}".encode()).hexdigest()[:24]


def plan(config: dict) -> list[tuple[int, Decoding]]:
    d = config["decoding"]
    out = []
    if d.get("greedy", True):
        out.append((-1, Decoding(temperature=0.0, top_p=1.0, max_new_tokens=d["max_new_tokens"], seed=None)))
    for i, seed in enumerate(d.get("sample_seeds", [])):
        out.append((i, Decoding(temperature=d["temperature"], top_p=d["top_p"], max_new_tokens=d["max_new_tokens"], seed=seed)))
    return out


def select_models(models: list[dict], model_keys: list[str] | None) -> list[dict]:
    if model_keys is None:
        return [m for m in models if m["backend"] != "fake"]
    unknown = set(model_keys) - {m["key"] for m in models}
    if unknown:
        raise RunConfigError(f"unknown model keys: {sorted(unknown)}")
    return [m for m in models if m["key"] in model_keys]


def check_pinned(specs: list[dict], config: dict) -> list[str]:
    unpinned = [s["key"] for s in specs if s["backend"] in HF_BACKENDS and not PINNED_REVISION.match(str(s.get("revision") or ""))]
    if unpinned and not config.get("allow_unpinned_revisions", False):
        raise RunConfigError(
            f"models not pinned to a 40-hex commit revision: {unpinned}. Pin `revision` in the model manifest "
            "(or set allow_unpinned_revisions: true for a debug run, which the analysis will refuse)."
        )
    return unpinned


def dataset_identity(dataset: Path) -> dict:
    """Path, SHA-256 and the release manifest's dataset_version / is_fixture flag (if present)."""
    manifest = dataset.parent / "manifest.json"
    info: dict = {}
    if manifest.exists():
        try:
            info = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            info = {}
    rel = dataset.relative_to(ROOT) if dataset.is_relative_to(ROOT) else dataset
    return {
        "path": str(rel),
        "sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "dataset_version": info.get("dataset_version"),
        "is_fixture": bool(info.get("is_fixture", False)),
        "is_release": bool(info.get("is_release", False)),
        "is_calibration": bool(info.get("is_calibration", False)),
    }


def runtime_environment() -> dict:
    pkgs = {}
    for name in ("torch", "transformers", "vllm", "tokenizers", "httpx", "numpy"):
        try:
            pkgs[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pkgs[name] = None
    gpu = None
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"], capture_output=True, text=True, timeout=10)
        gpu = out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        gpu = None
    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip() or None
        dirty = bool(subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True, timeout=10).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        commit, dirty = None, None
    return {"python": platform.python_version(), "platform": platform.platform(), "packages": pkgs, "gpu": gpu, "git_commit": commit, "git_dirty": dirty}


def load_generations(path: Path) -> list[Generation]:
    """One record per generation_id: the latest successful attempt if any, else the latest failure."""
    best: dict[str, Generation] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        g = Generation.model_validate_json(line)
        prev = best.get(g.generation_id)
        rank = (g.error is None, g.attempt)
        if prev is None or rank >= (prev.error is None, prev.attempt):
            best[g.generation_id] = g
    return list(best.values())


def _call(backend, messages, decoding) -> GenResult:
    if hasattr(backend, "generate_full"):
        return backend.generate_full(messages, decoding)
    return GenResult(backend.generate(messages, decoding))


def run(
    config_path: Path,
    model_keys: list[str] | None = None,
    limit: int | None = None,
    backend_override=None,
    out_root: Path | None = None,
) -> Path:
    config_path = Path(config_path)
    config = load_yaml(config_path)
    models = load_yaml(ROOT / config["model_manifest"])["models"]
    dataset = ROOT / config["dataset"]
    if not dataset.exists():
        raise RunConfigError(f"dataset not found: {dataset} (freeze the release first, protocol §12)")
    report = validate_file(dataset)
    if report.errors:
        raise RunConfigError(f"dataset has {len(report.errors)} validation errors; refusing to run")
    records = report.records
    if config.get("exclude_equivalence_status"):
        records = [r for r in records if r.equivalence.status.value not in config["exclude_equivalence_status"]]
    if limit:
        records = records[:limit]

    selected = select_models(models, model_keys)
    if not selected:
        raise RunConfigError(f"no models selected (keys: {model_keys})")
    unpinned = check_pinned(selected, config)
    ds = dataset_identity(dataset)
    is_fixture_run = all(s["backend"] == "fake" for s in selected)
    if ds["is_fixture"] and not is_fixture_run:
        raise RunConfigError(f"dataset {dataset} is a test fixture (manifest is_fixture: true); real models must not be run on it")
    if ds["dataset_version"] is None and not (is_fixture_run or config.get("allow_unversioned_dataset", False)):
        raise RunConfigError(f"dataset {dataset} has no manifest.json with dataset_version; analyse only versioned releases")

    run_id = config["run_id"]
    out_dir = (out_root or ROOT / "results" / "v2" / "runs") / run_id
    out_file = out_dir / "generations.jsonl"
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    old_manifest = out_dir / RUN_MANIFEST
    prev_models: dict[str, dict] = {}
    if old_manifest.exists():
        prev = json.loads(old_manifest.read_text(encoding="utf-8"))
        prev_models = {m["key"]: m for m in prev.get("models", []) if "key" in m}
        if prev.get("dataset", {}).get("sha256") != ds["sha256"] or prev.get("config_sha256") != config_sha:
            raise RunConfigError(f"run {run_id} already exists with a different dataset or config; resuming would mix generations. Use a new run_id.")
    max_attempts = int(config.get("max_attempts", 3))
    succeeded: set[str] = set()
    attempts: dict[str, int] = defaultdict(int)
    if out_file.exists():
        for line in out_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                attempts[row["generation_id"]] = max(attempts[row["generation_id"]], row.get("attempt", 1))
                if row.get("error") is None:
                    succeeded.add(row["generation_id"])

    manifest = {
        "run_id": run_id,
        "status": "running",
        "is_fixture_run": is_fixture_run,
        "unpinned_models": unpinned,
        "config_path": str(config_path),
        "config_sha256": config_sha,
        "limit": limit,
        "model_keys_requested": model_keys,
        "config": config,
        "dataset": ds,
        "n_records": len(records),
        "plan": [{"sample_index": i, **d.model_dump()} for i, d in plan(config)],
        "environment": runtime_environment(),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "models": [],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / RUN_MANIFEST).write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")

    system_prompt = config.get("system_prompt")
    planned, failed_final = 0, 0
    batch_size = int(config.get("batch_size", 256))
    for spec in selected:
        backend = backend_override or build_backend(spec)
        is_fake = isinstance(backend, FakeBackend) or spec["backend"] == "fake"
        batched = hasattr(backend, "generate_batch_full")  # vLLM: many prompts per call (same results, far faster)

        def make(record, sample_index, decoding, gid, res, err, latency, spec=spec, is_fake=is_fake):
            return Generation(
                generation_id=gid,
                run_id=run_id,
                model_key=spec["key"],
                model_id=spec["model_id"],
                model_revision=spec.get("revision"),
                backend=spec["backend"],
                record_id=record.record_id,
                scenario_id=record.scenario_id,
                intent_id=record.intent_id,
                scenario_type=record.scenario_type.value,
                language=record.language.value,
                transformation_type=record.transformation.type.value,
                condition=record.transformation.parameters.get("condition", "base"),
                prompt_text=record.text,
                system_prompt=system_prompt,
                decoding=decoding,
                sample_index=sample_index,
                response_text=res.text if res else None,
                finish_reason=res.finish_reason if res else None,
                n_output_tokens=res.n_output_tokens if res else None,
                rendered_prompt_sha256=res.rendered_prompt_sha256 if res else None,
                error=err,
                attempt=attempts[gid],
                latency_s=round(latency, 3),
                created_at=datetime.now(timezone.utc).isoformat(),
                is_test_fixture=is_fake,
            )

        def messages(record):
            return ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": "user", "content": record.text}]

        for sample_index, decoding in plan(config):
            planned += len(records)
            gid_of = {r.record_id: generation_id(run_id, spec["key"], r.record_id, sample_index) for r in records}
            pending = [r for r in records if gid_of[r.record_id] not in succeeded and attempts[gid_of[r.record_id]] < max_attempts]
            while pending:
                chunks = [pending[i : i + batch_size] for i in range(0, len(pending), batch_size)] if batched else [[r] for r in pending]
                for chunk in chunks:
                    t0 = time.perf_counter()
                    try:
                        if batched:
                            outs = [(res, None) for res in backend.generate_batch_full([messages(r) for r in chunk], decoding)]
                        else:
                            outs = [(_call(backend, messages(chunk[0]), decoding), None)]
                    except BackendError as exc:
                        outs = [(None, str(exc))] * len(chunk)
                    latency = (time.perf_counter() - t0) / len(chunk)
                    gens = []
                    for r, (res, err) in zip(chunk, outs, strict=True):
                        gid = gid_of[r.record_id]
                        attempts[gid] += 1
                        gens.append(make(r, sample_index, decoding, gid, res, err, latency))
                        if err is None:
                            succeeded.add(gid)
                    append_jsonl(out_file, gens)  # raw output persisted before any evaluation
                pending = [r for r in pending if gid_of[r.record_id] not in succeeded and attempts[gid_of[r.record_id]] < max_attempts]
            failed_final += sum(gid_of[r.record_id] not in succeeded for r in records)
        entry = {"key": spec["key"], "spec": {k: v for k, v in spec.items() if k != "key"}, **backend.describe()}
        # A resumed call that skips every generation never loads the model, so its description lacks the
        # chat-template hash and tokenizer recorded when the model actually ran: keep those.
        manifest["models"].append({**prev_models.get(spec["key"], {}), **{k: v for k, v in entry.items() if v is not None}})

    manifest["n_planned"] = planned
    manifest["n_succeeded"] = planned - failed_final
    manifest["n_failed_after_retries"] = failed_final
    manifest["max_attempts"] = max_attempts
    manifest["status"] = "complete" if failed_final == 0 else "incomplete"
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["generations_sha256"] = hashlib.sha256(out_file.read_bytes()).hexdigest() if out_file.exists() else None
    (out_dir / RUN_MANIFEST).write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    return out_file


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("--models", nargs="*", help="model keys; default = every non-test model in the manifest")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)
    print(run(args.config, args.models, args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
