"""Run one LLM judge over a generation run and write AI-judge labels (protocol §8).

    PYTHONPATH=backend python -m app.v2.judges.run_judge --run results/v2/runs/calibration-pilot-v2 --judge gpt_oss_120b

Writes results/v2/labels/<run_id>__<judge_key>.jsonl (ResponseLabel records, label_source ai_judge,
labeler_id "<judge_key>@<rubric version>") and failures/<same name> for responses whose judge output
could not be parsed after retries. Those responses get no label from this judge; they stay
unresolved and go to the human queue. A judge never labels a response alone: resolution needs two
agreeing judges or a third breaking a tie (`records.resolve_labels`).

Safeguards:
- The judge must be pinned to a 40-hex revision (Hugging Face backends), as for models under test.
- The judge's organisation must not be that of any confirmatory model under test (same family).
- Resumable: generations already labelled by this judge in the output file are skipped.
- Fixture runs produce fixture-marked labels (the analysis refuses them).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import yaml

from app.v2.inference.backends import build_backend
from app.v2.inference.runner import PINNED_REVISION, load_generations
from app.v2.judges.llm_judge import JUDGE_DECODING, JudgeParseError, build_messages, parse_judgement
from app.v2.judges.llm_judge import RUBRIC_VERSION as RUBRIC
from app.v2.records import Decoding, Generation, ResponseLabel, append_jsonl

ROOT = Path(__file__).resolve().parents[4]
HF_BACKENDS = ("transformers", "vllm")


class JudgeConfigError(ValueError):
    pass


def check_judge(spec: dict, model_manifest: list[dict]) -> None:
    if spec["backend"] in HF_BACKENDS and not PINNED_REVISION.match(str(spec.get("revision") or "")):
        raise JudgeConfigError(f"judge {spec['key']} is not pinned to a 40-hex commit revision")
    org = spec["model_id"].split("/")[0].lower()
    tested = {m["model_id"].split("/")[0].lower() for m in model_manifest if m.get("confirmatory")}
    if spec["backend"] != "fake" and org in tested:
        raise JudgeConfigError(f"judge {spec['key']} ({spec['model_id']}) is from an organisation whose models are under test")


def judge_generations(
    gens: list[Generation],
    records: dict[str, dict],
    judge_key: str,
    generate_batch: Callable[[list[list[dict]], Decoding], list[str]],
    out: Path,
    decoding: Decoding = JUDGE_DECODING,
    batch_size: int = 64,
    max_attempts: int = 2,
) -> dict:
    """Label every successful generation not yet labelled in `out`. Returns counts."""
    out = Path(out)
    failures = out.parent / "failures" / out.name  # kept apart so a glob over label files never picks it up
    failures.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(x)["generation_id"] for x in out.read_text(encoding="utf-8").splitlines() if x.strip()}
    todo = [g for g in gens if g.error is None and g.response_text is not None and g.generation_id not in done]
    labeler = f"{judge_key}@{RUBRIC}"
    n_ok = n_fail = 0
    for i in range(0, len(todo), batch_size):
        pending = todo[i : i + batch_size]
        labels: list[ResponseLabel] = []
        errors: dict[str, str] = {}
        for _ in range(max_attempts):
            if not pending:
                break
            msgs = [build_messages(g, records[g.record_id]["intent_description"], records[g.record_id]["expected_behavior"]) for g in pending]
            texts = generate_batch(msgs, decoding)
            retry = []
            for g, text in zip(pending, texts, strict=True):
                try:
                    labels.append(parse_judgement(text, g, labeler))
                except JudgeParseError as exc:
                    errors[g.generation_id] = str(exc)
                    retry.append(g)
            pending = retry
        append_jsonl(out, labels)
        n_ok += len(labels)
        if pending:
            n_fail += len(pending)
            with failures.open("a", encoding="utf-8") as f:
                for g in pending:
                    f.write(json.dumps({"generation_id": g.generation_id, "judge": labeler, "error": errors[g.generation_id]}) + "\n")
    return {"labelled": n_ok, "unparseable": n_fail, "skipped_already_labelled": len(done), "not_judgeable_errored": sum(g.error is not None for g in gens)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--judge", required=True, help="judge key in the judge manifest")
    ap.add_argument("--judges", type=Path, default=ROOT / "configs" / "judges.yaml")
    ap.add_argument("--models", type=Path, default=ROOT / "configs" / "models.yaml")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--batch-size", type=int, default=64)
    args = ap.parse_args(argv)

    specs = {j["key"]: j for j in yaml.safe_load(args.judges.read_text(encoding="utf-8"))["judges"]}
    if args.judge not in specs:
        raise SystemExit(f"unknown judge {args.judge!r}; known: {sorted(specs)}")
    spec = dict(specs[args.judge])
    check_judge(spec, yaml.safe_load(args.models.read_text(encoding="utf-8"))["models"])
    manifest = json.loads((args.run / "run_manifest.json").read_text(encoding="utf-8"))
    dataset = Path(manifest["dataset"]["path"])
    dataset = dataset if dataset.is_absolute() else ROOT / dataset
    if hashlib.sha256(dataset.read_bytes()).hexdigest() != manifest["dataset"]["sha256"]:
        raise SystemExit(f"dataset {dataset} changed since the run; refusing to judge against different records")
    records = {r["record_id"]: r for r in map(json.loads, dataset.read_text(encoding="utf-8").splitlines()) if r}
    gens = load_generations(args.run / "generations.jsonl")
    max_new = int(spec.pop("max_new_tokens", JUDGE_DECODING.max_new_tokens))
    backend = build_backend(spec)
    batch = getattr(backend, "generate_batch", None) or (lambda msgs, d: [backend.generate(m, d) for m in msgs])
    out = args.out or ROOT / "results" / "v2" / "labels" / f"{manifest['run_id']}__{args.judge}.jsonl"
    decoding = JUDGE_DECODING.model_copy(update={"max_new_tokens": max_new})
    counts = judge_generations(gens, records, args.judge, batch, out, decoding=decoding, batch_size=args.batch_size)
    print(json.dumps({"judge": args.judge, "out": str(out), **counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
