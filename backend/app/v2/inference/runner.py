"""Resumable, cached generation runs over a VeriAudit-X file.

A run is defined by an experiment config (configs/experiments/*.yaml) and a model
manifest (configs/models.yaml). Outputs are appended to
results/v2/runs/<run_id>/generations.jsonl; the run is resumable because every
generation has a deterministic generation_id and existing IDs are skipped.

    PYTHONPATH=backend python -m app.v2.inference.runner configs/experiments/main_study.yaml --models qwen3_8b
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.v2.inference.backends import BackendError, FakeBackend, build_backend
from app.v2.records import Decoding, Generation, append_jsonl
from app.veriaudit_x.validation import validate_file

ROOT = Path(__file__).resolve().parents[4]


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


def run(config_path: Path, model_keys: list[str] | None = None, limit: int | None = None, backend_override=None, out_root: Path | None = None) -> Path:
    config = load_yaml(config_path)
    models = load_yaml(ROOT / config["model_manifest"])["models"]
    dataset = ROOT / config["dataset"]
    report = validate_file(dataset)
    if report.errors:
        raise SystemExit(f"dataset has {len(report.errors)} validation errors; refusing to run")
    records = report.records
    if config.get("exclude_equivalence_status"):
        records = [r for r in records if r.equivalence.status.value not in config["exclude_equivalence_status"]]
    if limit:
        records = records[:limit]

    run_id = config["run_id"]
    out_dir = (out_root or ROOT / "results" / "v2" / "runs") / run_id
    out_file = out_dir / "generations.jsonl"
    done = set()
    if out_file.exists():
        for line in out_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["generation_id"])

    selected = [m for m in models if model_keys is None or m["key"] in model_keys]
    if not selected:
        raise SystemExit(f"no models match {model_keys}")
    meta = {
        "run_id": run_id,
        "config": config,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "models": [],
    }
    system_prompt = config.get("system_prompt")
    for spec in selected:
        backend = backend_override or build_backend(spec)
        is_fake = isinstance(backend, FakeBackend)
        meta["models"].append({"key": spec["key"], **backend.describe()})
        for record in records:
            for sample_index, decoding in plan(config):
                gid = generation_id(run_id, spec["key"], record.record_id, sample_index)
                if gid in done:
                    continue
                messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": "user", "content": record.text}]
                t0 = time.perf_counter()
                text, err = None, None
                try:
                    text = backend.generate(messages, decoding)
                except BackendError as exc:
                    err = str(exc)
                g = Generation(
                    generation_id=gid,
                    run_id=run_id,
                    model_key=spec["key"],
                    model_id=spec["model_id"],
                    model_revision=spec.get("revision"),
                    backend=backend.describe()["backend"],
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
                    response_text=text,
                    error=err,
                    latency_s=round(time.perf_counter() - t0, 3),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    is_test_fixture=is_fake,
                )
                append_jsonl(out_file, [g])
                done.add(gid)
    meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (out_dir / "run_metadata.json").write_text(json.dumps(meta, indent=2, default=str) + "\n", encoding="utf-8")
    return out_file


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)
    print(run(args.config, args.models, args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
