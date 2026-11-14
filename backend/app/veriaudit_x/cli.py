"""Command-line entry point.

    python -m app.veriaudit_x validate DATA.jsonl [--allow-missing-languages]
    python -m app.veriaudit_x split DATA.jsonl --out DIR [--seed 13] [--ratios 0.7 0.15 0.15]
    python -m app.veriaudit_x schema [--out FILE]

`split` refuses to run on a file with validation errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.veriaudit_x.schema import json_schema
from app.veriaudit_x.splits import DEFAULT_RATIOS, write_splits
from app.veriaudit_x.validation import ValidationConfig, validate_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.veriaudit_x")
    sub = parser.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", help="validate a VeriAudit-X JSONL file")
    v.add_argument("path", type=Path)
    v.add_argument("--allow-missing-languages", action="store_true")
    v.add_argument("--strict", action="store_true", help="treat warnings as failures")

    s = sub.add_parser("split", help="validate, then write leakage-free splits")
    s.add_argument("path", type=Path)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--seed", type=int, default=13)
    s.add_argument("--ratios", type=float, nargs=3, default=list(DEFAULT_RATIOS))
    s.add_argument("--dataset-version", default=None)
    s.add_argument("--allow-missing-languages", action="store_true")

    j = sub.add_parser("schema", help="print or write the JSON Schema")
    j.add_argument("--out", type=Path)

    args = parser.parse_args(argv)

    if args.command == "schema":
        text = json.dumps(json_schema(), indent=2, ensure_ascii=False) + "\n"
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    config = ValidationConfig(require_all_languages=not args.allow_missing_languages)
    report = validate_file(args.path, config)
    print(report.summary())

    if args.command == "validate":
        return 1 if report.errors or (args.strict and report.warnings) else 0

    if report.errors:
        print("Refusing to split: fix validation errors first.", file=sys.stderr)
        return 1
    manifest = write_splits(
        report.records,
        args.out,
        seed=args.seed,
        ratios=tuple(args.ratios),
        source_file=args.path,
        dataset_version=args.dataset_version,
    )
    print(json.dumps(manifest["statistics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
