"""Human translation worksheet for VeriAudit-X (export and import).

AI generation of the non-English harmful variants was stopped by model safety
classifiers in this project's sandbox (see docs/v2/PROGRESS.md), so the variants
are authored by human translators following docs/v2/variant_generation_guidelines.md.

    export:  PYTHONPATH=backend python research/dataset/translation_worksheet.py export
             -> data/candidates/translation_worksheet.csv (UTF-8 with BOM, opens in Excel/Sheets)
    import:  PYTHONPATH=backend python research/dataset/translation_worksheet.py import FILLED.csv --translator ID
             -> data/candidates/generated/human_<ID>.jsonl (consumed by assemble_veriaudit_x.py)

Pre-filled cells: English sources, XSTest benign prompts, and the human-authored
v0.1 harmful variants (do not edit those).
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAND = ROOT / "data" / "candidates"
FORMS = ["urdu", "roman_urdu", "code_switched"]
TS = ["T1", "T2", "T3", "T4", "T5", "T6"]
COLUMNS = ["scenario_id", "category", "intent", "needs_transformations", "english", *FORMS, *TS, "notes"]


def export() -> Path:
    rows = []
    for p in sorted((CAND / "batches").glob("batch_*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            b = json.loads(line)
            fixed = b.get("fixed_harmful_variants") or {}
            for intent, en in (("harmful", b["harmful_en"]), ("benign", b["benign_en"] or "")):
                row = {c: "" for c in COLUMNS}
                row.update(
                    scenario_id=b["scenario_id"],
                    category=b["category"],
                    intent=intent,
                    needs_transformations="yes" if b["needs_transformations"] else "no",
                    english=en,
                )
                if intent == "harmful":
                    row.update({f: fixed.get(f, "") for f in FORMS})
                rows.append(row)
    out = CAND / "translation_worksheet.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return out


def import_filled(path: Path, translator: str) -> Path:
    by_s: dict[str, dict] = defaultdict(dict)
    with Path(path).open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            by_s[row["scenario_id"]][row["intent"]] = row
    out_rows = []
    for sid, d in by_s.items():
        if set(d) != {"harmful", "benign"}:
            continue
        h, b = d["harmful"], d["benign"]
        if not all(x[f].strip() for x in (h, b) for f in FORMS) or not b["english"].strip():
            continue  # incomplete scenarios are left for a later import
        needs_t = h["needs_transformations"] == "yes"
        out_rows.append(
            {
                "scenario_id": sid,
                "benign_en": b["english"].strip(),
                "harmful": {f: h[f].strip() for f in FORMS},
                "benign": {f: b[f].strip() for f in FORMS},
                "transformations": {"harmful": {t: h[t].strip() for t in TS}, "benign": {t: b[t].strip() for t in TS}} if needs_t else None,
                "notes": " | ".join(x["notes"] for x in (h, b) if x["notes"]),
                "skipped": False,
                "author": "human",
                "translator_id": translator,
            }
        )
    out = CAND / "generated" / f"human_{translator}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(out_rows)} complete scenarios imported")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export")
    imp = sub.add_parser("import")
    imp.add_argument("path", type=Path)
    imp.add_argument("--translator", required=True, help="pseudonymous translator ID, e.g. tr01")
    args = ap.parse_args(argv)
    print(export() if args.cmd == "export" else import_filled(args.path, args.translator))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
