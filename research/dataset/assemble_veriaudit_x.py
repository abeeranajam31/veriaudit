"""Assemble VeriAudit-X records from the selection and the generated variants, run
automated QC, validate, and write leakage-free splits.

Inputs:  data/candidates/selection.jsonl, data/candidates/transformation_subset.json,
         data/candidates/generated/batch_*.jsonl
Outputs: data/veriaudit-x/<version>/veriaudit_x.jsonl, manifest.json, qc_report.md, splits/

Run: PYTHONPATH=backend python research/dataset/assemble_veriaudit_x.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from app.v2.quality.checks import check_variant
from app.veriaudit_x.schema import SCHEMA_VERSION
from app.veriaudit_x.splits import write_splits
from app.veriaudit_x.validation import ValidationConfig, validate_file

ROOT = Path(__file__).resolve().parents[2]
CAND = ROOT / "data" / "candidates"
VERSION = "2.0.0-rc1"
OUT = ROOT / "data" / "veriaudit-x" / VERSION
GENERATOR = "anthropic/claude-opus-5.5 (Claude subagent; docs/v2/variant_generation_guidelines.md v1.0)"
TODAY = date.today().isoformat()

LANG_CODE = {"english": "en", "urdu": "ur", "roman_urdu": "rur", "code_switched": "cs"}
SCRIPT = {"english": "latin", "urdu": "perso_arabic", "roman_urdu": "latin", "code_switched": "latin"}
BASE_DERIVATION = {"urdu": ("translation", "english"), "roman_urdu": ("transliteration", "urdu"), "code_switched": ("code_switching", "english")}
# condition -> (record language, script, transformation type, parent language, extra parameters, language used for QC)
TRANSFORMS = {
    "T1": ("roman_urdu", "latin", "orthographic_variation", "roman_urdu", {"spelling": "alternative_informal"}, "roman_urdu"),
    "T2": ("roman_urdu", "latin", "orthographic_variation", "roman_urdu", {"spelling": "consistent_formal"}, "roman_urdu"),
    "T3": ("urdu", "perso_arabic", "register_shift", "urdu", {"register": "colloquial"}, "urdu"),
    "T4": ("code_switched", "latin", "code_switching", "code_switched", {"english_ratio_target": "<=0.20"}, "code_switched"),
    "T5": ("code_switched", "latin", "code_switching", "code_switched", {"english_ratio_target": ">=0.60"}, "code_switched"),
    "T6": ("code_switched", "mixed", "code_switching", "urdu", {"script_mixing": "urdu_script_with_latin_english"}, "urdu"),
}
SOURCE_LICENCE = {"advbench": "MIT (AdvBench)", "xstest": "CC-BY-4.0 (XSTest)", "veriaudit-v0.1": "MIT (VeriAudit)"}


def origin(c: dict, kind: str) -> str:
    if c["source"] == "xstest":
        safe_id, unsafe_id = c["source_id"].split("|")
        return f"xstest:{unsafe_id if kind == 'H' else safe_id}"
    if c["source"] == "advbench":
        return f"advbench:{c['source_id']}" if kind == "H" else f"ai-authored benign contrast for advbench:{c['source_id']}"
    return f"veriaudit-v0.1:{c['source_id']}" if kind == "H" else f"ai-authored benign contrast for veriaudit-v0.1:{c['source_id']}"


def make_record(c, kind, lang, script, text, ttype, parent_id, cond, params, ai_generated, author, qc):
    sid = c["scenario_id"]
    intent = f"{sid}-{kind}"
    stype = "harmful" if kind == "H" else "benign"
    rid = f"{intent}-{LANG_CODE[lang]}-{cond.lower()}"
    if ttype == "source":
        eq = {"status": "source"}
    else:
        failed = [q for q in qc if not q.passed]
        eq = {"status": "flagged" if failed else "pending", "reference_record_id": f"{intent}-en-base"}
        if failed:
            eq["notes"] = "automated check failed: " + ", ".join(q.name for q in failed)
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": rid,
        "scenario_id": sid,
        "intent_id": intent,
        "scenario_type": stype,
        "category": c["category"] if kind == "H" else ("safety_information" if c["category"] not in ("misinformation",) else "information_request"),
        "expected_behavior": ("refuse_and_redirect" if c["category"] == "self_harm" else "refuse") if kind == "H" else "comply",
        "contrast_intent_id": f"{sid}-{'B' if kind == 'H' else 'H'}",
        "intent_description": (
            f"Harmful request ({c['category']}): {c['harmful_en']}" if kind == "H" else f"Benign contrast on the same topic: {c['benign_en']}"
        ),
        "language": lang,
        "script": script,
        "text": text,
        "transformation": {
            "type": ttype,
            "source_record_id": parent_id,
            "method": "machine" if ai_generated else "human",
            "tool": GENERATOR if ai_generated else None,
            "author_id": author,
            "parameters": {"condition": cond, **params},
        },
        "equivalence": eq,
        "provenance": {
            "created_at": TODAY,
            "created_by": "research/dataset/assemble_veriaudit_x.py",
            "origin": origin(c, kind) if ttype == "source" else f"variant of {origin(c, kind)}",
            "license": SOURCE_LICENCE[c["source"]] if (ttype == "source" and not ai_generated) else "VeriAudit-X (new work)",
        },
        "quality": {
            "ai_generated": ai_generated,
            "generator_id": GENERATOR if ai_generated else None,
            "automated_checks": {q.name: {"passed": q.passed, "value": q.value, "detail": q.detail} for q in qc},
        },
    }


def main() -> None:
    sel = {json.loads(x)["scenario_id"]: json.loads(x) for x in (CAND / "selection.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}
    subset = set(json.loads((CAND / "transformation_subset.json").read_text()))
    gen = {}
    for p in sorted((CAND / "generated").glob("*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                g = json.loads(line)
                gen[g["scenario_id"]] = g

    records, problems = [], Counter()
    missing = sorted(set(sel) - set(gen))
    skipped = sorted(s for s, g in gen.items() if g.get("skipped"))
    for sid, c in sel.items():
        g = gen.get(sid)
        if g is None or g.get("skipped"):
            continue
        c = dict(c, benign_en=c["benign_en"] or g["benign_en"])
        human = g.get("author") == "human"
        who = f"human:{g.get('translator_id', 'unknown')}" if human else "ai"
        for kind, key in (("H", "harmful"), ("B", "benign")):
            en_text = c["harmful_en"] if kind == "H" else c["benign_en"]
            en_ai = kind == "B" and c["source"] != "xstest" and not human
            records.append(
                make_record(
                    c,
                    kind,
                    "english",
                    "latin",
                    en_text,
                    "source",
                    None,
                    "base",
                    {},
                    en_ai,
                    "ai" if en_ai else (who if kind == "B" and human and c["source"] != "xstest" else f"source:{c['source']}"),
                    check_variant("english", en_text, en_text),
                )
            )
            fixed = kind == "H" and c["source"] == "veriaudit-v0.1"
            base_texts = {}
            for lang, (ttype, parent_lang) in BASE_DERIVATION.items():
                text = g[key][lang]
                base_texts[lang] = text
                parent = f"{sid}-{kind}-{LANG_CODE[parent_lang]}-base"
                qc = check_variant(lang, text, en_text)
                records.append(
                    make_record(
                        c, kind, lang, SCRIPT[lang], text, ttype, parent, "base", {}, not (fixed or human), "veriaudit-v0.1-translator" if fixed else who, qc
                    )
                )
            if sid in subset:
                tr = (g.get("transformations") or {}).get(key)
                if not tr:
                    problems["missing transformations"] += 1
                    continue
                for cond, (lang, script, ttype, parent_lang, params, qc_lang) in TRANSFORMS.items():
                    text = tr.get(cond, "")
                    if not text.strip():
                        problems[f"empty {cond}"] += 1
                        continue
                    parent = f"{sid}-{kind}-{LANG_CODE[parent_lang]}-base"
                    qc = check_variant(qc_lang, text, en_text, cond, base_texts[parent_lang])
                    records.append(make_record(c, kind, lang, script, text, ttype, parent, cond, params, not human, who, qc))

    OUT.mkdir(parents=True, exist_ok=True)
    data_file = OUT / "veriaudit_x.jsonl"
    with data_file.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    report = validate_file(data_file, ValidationConfig())
    manifest = {
        "dataset_name": "VeriAudit-X",
        "dataset_version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "description": "Main-study candidate release: 200 scenarios (harmful + benign contrast) in 4 base forms, "
        "controlled transformations on a stratified third. Variants are AI-generated unless provenance says otherwise; "
        "no variant is human-verified yet.",
        "data_file": data_file.name,
        "is_fixture": False,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    split_manifest = None
    if report.ok:
        split_manifest = write_splits(report.records, OUT / "splits", seed=20261112, source_file=data_file, dataset_version=VERSION)

    # QC report
    by_check = defaultdict(lambda: [0, 0])
    by_cond_lang = defaultdict(lambda: [0, 0])
    for r in records:
        if r["transformation"]["type"] == "source":
            continue
        ok = all(v["passed"] for v in r["quality"]["automated_checks"].values())
        k = (r["transformation"]["parameters"]["condition"], r["language"])
        by_cond_lang[k][0] += ok
        by_cond_lang[k][1] += 1
        for name, v in r["quality"]["automated_checks"].items():
            by_check[name][0] += v["passed"]
            by_check[name][1] += 1
    lines = [
        f"# VeriAudit-X {VERSION} — automated QC report",
        "",
        f"Records: {len(records)} · scenarios: {len({r['scenario_id'] for r in records})} · intents: {len({r['intent_id'] for r in records})}",
        f"Validation: {len(report.errors)} errors, {len(report.warnings)} warnings",
        f"Scenarios still without variants: {len(missing)} of {len(sel)} · skipped by generator: {len(skipped)}",
        f"Assembly problems: {dict(problems) or 'none'}",
        "",
        "Automated checks are screens. Passing them is not equivalence verification; no record is human-reviewed.",
        "",
        "| Check | passed / total |",
        "|---|---|",
    ]
    lines += [f"| {k} | {v[0]} / {v[1]} |" for k, v in sorted(by_check.items())]
    lines += ["", "| Condition | Language | all checks passed / total |", "|---|---|---|"]
    lines += [f"| {k[0]} | {k[1]} | {v[0]} / {v[1]} |" for k, v in sorted(by_cond_lang.items())]
    lines += ["", "## Validation warnings by code", ""] + [f"- {k}: {v}" for k, v in sorted(report.codes().items())]
    if split_manifest:
        lines += ["", "## Splits (scenario-grouped)", ""] + [
            f"- {s}: {v['scenarios']} scenarios, {v['records']} records" for s, v in split_manifest["statistics"].items()
        ]
    (OUT / "qc_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8]))
    if report.errors:
        print("\n".join(i.format() for i in report.errors[:20]))


if __name__ == "__main__":
    main()
