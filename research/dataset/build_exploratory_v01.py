"""EXPLORATORY dataset: the 30 v0.1 harmful requests in their four human-written forms (120 prompts),
for running the v2 model panel before the main study.

Why: the v0.1 variants are the only non-English prompts that already exist. Running the four v2
confirmatory models on them gives real outputs now, while translation of the main study continues.

What it is NOT: these are not confirmatory results.
- The 90 non-English variants were written by the PI and have not been verified by independent
  review (equivalence status stays `pending`).
- They have no benign contrasts, so there is no H2.
- There are 30 scenarios rather than 200.
- The 30 are main-study scenarios VX-S0001-S0030, so the main study will later produce confirmatory
  data on the same prompts; this run is reported separately and never pooled with it.

Output: data/veriaudit-x/exploratory-v01/veriaudit_x_exploratory_v01.jsonl + manifest.json
        (is_release: false, is_exploratory: true; the main analysis refuses it, by design).
Run:    PYTHONPATH=backend python research/dataset/build_exploratory_v01.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_calibration import DERIV, LANG  # noqa: E402

from app.veriaudit_x.schema import SCHEMA_VERSION  # noqa: E402
from app.veriaudit_x.validation import ValidationConfig, validate_objects  # noqa: E402

OUT = ROOT / "data" / "veriaudit-x" / "exploratory-v01"
VERSION = "exploratory-v01-1.0"


def record(c: dict, lang: str, text: str) -> dict:
    code, script = LANG[lang]
    sid, intent = c["scenario_id"], f"{c['scenario_id']}-H"
    is_src = lang == "english"
    ttype, parent = ("source", None) if is_src else DERIV[lang]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": f"{intent}-{code}-base",
        "scenario_id": sid,
        "intent_id": intent,
        "scenario_type": "harmful",
        "category": c["category"],
        "expected_behavior": "refuse_and_redirect" if c["category"] == "self_harm" else "refuse",
        "contrast_intent_id": None,
        "intent_description": f"VeriAudit v0.1 item {c['source_id']} ({c['category']}); exploratory replication, not the main study",
        "language": lang,
        "script": script,
        "text": text,
        "transformation": {
            "type": ttype,
            "source_record_id": None if is_src else f"{intent}-{LANG[parent][0]}-base",
            "method": "human",
            "author_id": "source:veriaudit-v0.1" if is_src else "pi",
            "parameters": {"condition": "base"},
        },
        "equivalence": {"status": "source"} if is_src else {"status": "pending", "reference_record_id": f"{intent}-en-base"},
        "provenance": {
            "created_by": "research/dataset/build_exploratory_v01.py",
            "origin": f"veriaudit-v0.1:{c['source_id']}",
            "license": "VeriAudit v0.1 (project's own data)",
            "notes": "exploratory replication only; variants written by the PI in v0.1, not independently verified",
        },
    }


def main() -> None:
    selection = [json.loads(x) for x in (ROOT / "data/candidates/selection.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    items = [c for c in selection if c["source"] == "veriaudit-v0.1"]
    if len(items) != 30:
        raise SystemExit(f"expected 30 v0.1 items, found {len(items)}")
    records = []
    for c in sorted(items, key=lambda c: c["scenario_id"]):
        records.append(record(c, "english", c["harmful_en"]))
        for lang in ("urdu", "roman_urdu", "code_switched"):
            records.append(record(c, lang, c["v1_variants"][lang]))
    report = validate_objects(records, ValidationConfig(require_all_languages=False))
    if not report.ok:
        raise SystemExit(report.summary()[:3000])
    OUT.mkdir(parents=True, exist_ok=True)
    data = OUT / "veriaudit_x_exploratory_v01.jsonl"
    data.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    manifest = {
        "dataset_name": "VeriAudit-X exploratory v0.1 replication",
        "dataset_version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "description": "EXPLORATORY: 30 v0.1 harmful requests x 4 human-written forms. Not a release; never pooled with the main study.",
        "data_file": data.name,
        "is_fixture": False,
        "is_release": False,
        "is_calibration": False,
        "is_exploratory": True,
        "n_records": len(records),
        "data_sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{len(records)} records -> {data} (sha256 {manifest['data_sha256'][:12]}…)")


if __name__ == "__main__":
    main()
