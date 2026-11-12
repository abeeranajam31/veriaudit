"""Merge exported human equivalence ratings (tools/review/index.html) into a VeriAudit-X file.

    PYTHONPATH=backend python research/dataset/merge_human_ratings.py DATA.jsonl ratings_*.jsonl --out DATA_reviewed.jsonl

Writes a new file (never edits the input), then validates it. Status rules are those of
app.v2.review.apply_equivalence_ratings (>= 2 unanimous 'equivalent' ratings to verify).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from app.v2.review import apply_equivalence_ratings
from app.veriaudit_x.schema import EquivalenceRating
from app.veriaudit_x.validation import validate_file


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("data", type=Path)
    ap.add_argument("ratings", type=Path, nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.resolve() == args.data.resolve():
        raise SystemExit("--out must differ from the input file")

    report = validate_file(args.data)
    if report.errors:
        raise SystemExit(f"input has {len(report.errors)} validation errors")
    pending = defaultdict(list)
    for p in args.ratings:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                pending[d.pop("record_id")].append(EquivalenceRating.model_validate(d))
    out, applied = [], 0
    for r in report.records:
        if r.record_id in pending:
            r = apply_equivalence_ratings(r, pending.pop(r.record_id))
            applied += 1
        out.append(r)
    with args.out.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r.model_dump(mode="json", exclude_none=False), ensure_ascii=False) + "\n")
    check = validate_file(args.out)
    print(f"applied ratings to {applied} records; unknown record ids: {sorted(pending)}; output valid: {check.ok}")
    return 0 if check.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
