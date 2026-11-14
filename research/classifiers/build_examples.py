"""Build RQ5 classifier example files with scenario-grouped splits (protocol §11).

Task B (prompt-level harmful intent):    --task prompts   --dataset data/veriaudit-x/2.0.0
Task A (response-level harmful content): --task responses --dataset data/veriaudit-x/2.0.0 \
                                         --generations results/v2/runs/<run>/generations.jsonl --labels <labels.jsonl ...>

Each example: {"text", "label", "form", "scenario_id", "split", "human_validated", "source_id"}.
`split` comes from the release's splits/split_manifest.json (never random). Task A labels are the
resolved final labels; examples whose final label is human (or human-adjudicated) are marked
human_validated and must be in the test split - train_encoder.check_splits refuses otherwise, so
such examples outside test are dropped here and counted. Responses with no resolved label are
skipped and counted, never guessed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from app.v2.inference.runner import load_generations
from app.v2.records import LabelSource, ResponseLabel, resolve_labels
from app.veriaudit_x.validation import ValidationConfig, validate_file

HUMAN = {LabelSource.human, LabelSource.human_adjudicated}


def prompt_examples(records, assignment) -> list[dict]:
    return [
        {
            "text": r.text,
            "label": int(r.scenario_type.value == "harmful"),
            "form": r.language.value,
            "scenario_id": r.scenario_id,
            "split": assignment[r.scenario_id],
            "human_validated": r.equivalence.status.value == "verified",
            "source_id": r.record_id,
        }
        for r in records
        if r.transformation.parameters.get("condition", "base") == "base" and r.equivalence.status.value != "rejected"
    ]


def response_examples(gens, labels: dict[str, ResponseLabel], assignment, log: Counter) -> list[dict]:
    out = []
    for g in gens:
        if g.response_text is None or g.condition != "base" or g.is_test_fixture:
            log["skipped_no_response_or_fixture"] += 1
            continue
        lab = labels.get(g.generation_id)
        if lab is None:
            log["skipped_unresolved_label"] += 1
            continue
        label = int(lab.harmful_content is True) if g.scenario_type == "harmful" else 0
        human = lab.label_source in HUMAN
        split = assignment[g.scenario_id]
        if human and split != "test":
            log["dropped_human_validated_outside_test"] += 1
            continue
        out.append(
            {
                "text": g.response_text,
                "label": label,
                "form": g.language,
                "scenario_id": g.scenario_id,
                "split": split,
                "human_validated": human,
                "source_id": g.generation_id,
            }
        )
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["prompts", "responses"], required=True)
    ap.add_argument("--dataset", type=Path, required=True, help="release directory (veriaudit_x.jsonl + splits/)")
    ap.add_argument("--generations", type=Path)
    ap.add_argument("--labels", type=Path, nargs="*", default=[])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    assignment = json.loads((args.dataset / "splits" / "split_manifest.json").read_text(encoding="utf-8"))["assignment"]
    log: Counter = Counter()
    if args.task == "prompts":
        report = validate_file(args.dataset / "veriaudit_x.jsonl", ValidationConfig(require_all_languages=False))
        rows = prompt_examples(report.records, assignment)
    else:
        if not args.generations or not args.labels:
            raise SystemExit("--task responses needs --generations and --labels")
        labs = [ResponseLabel.model_validate_json(x) for p in args.labels for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        rows = response_examples(load_generations(args.generations), resolve_labels(labs), assignment, log)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(
        json.dumps({"n_examples": len(rows), "by_split": Counter(r["split"] for r in rows), "by_label": Counter(r["label"] for r in rows), **log}, default=str)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
