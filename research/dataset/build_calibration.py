"""Build the calibration-pilot dataset (protocol §12, amended 2026-11-13).

The calibration pilot debugs the pipeline and estimates the nuisance parameters the power
analysis depends on (response consistency across the 3 samples, outcome rates, scenario
heterogeneity). It shares NO scenario with the main study.

Set A (multilingual): the items of the earlier 13-item pilot that are not main-study scenarios
        (VA-005..010 are; they are dropped), in all four human-written forms.
Set B (English only): held-out AdvBench harmful requests and held-out XSTest safe prompts that are
        not in the main-study selection and are not near-duplicates of any selected scenario
        (same thresholds as the selection: TF-IDF cosine 0.65, content-word Jaccard 0.5), with the
        selection's category exclusions (CBRN/explosives, sexual/minors, out-of-taxonomy).

Output: data/veriaudit-x/calibration/veriaudit_x_calibration.jsonl + manifest.json
Run:    PYTHONPATH=backend python research/dataset/build_calibration.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_candidates import CONTENT_JACCARD, DEDUP_THRESHOLD, categorise  # noqa: E402

from app.v2.quality.checks import content_word_duplicates, near_duplicates  # noqa: E402
from app.veriaudit_x.schema import SCHEMA_VERSION  # noqa: E402
from app.veriaudit_x.validation import ValidationConfig, validate_objects  # noqa: E402

OUT = ROOT / "data" / "veriaudit-x" / "calibration"
VERSION = "calibration-1.0"
SEED = "veriaudit-calibration-20261113"
N_HARMFUL_B = 40
N_BENIGN_B = 30
PILOT_CATEGORY = {
    "Benign — Everyday Assistance": ("benign", "everyday_assistance"),
    "Benign — Technical Assistance": ("benign", "technical_assistance"),
    "Benign — Information Request": ("benign", "information_request"),
    "Benign — Customer Support": ("benign", "everyday_assistance"),
    "Instruction-Following — Format Constraint": ("benign", "instruction_following"),
    "Refusal Test — Privacy": ("harmful", "privacy_violation"),
}
LANG = {"english": ("en", "latin"), "urdu": ("ur", "perso_arabic"), "roman_urdu": ("rur", "latin"), "code_switched": ("cs", "latin")}
DERIV = {"urdu": ("translation", "english"), "roman_urdu": ("transliteration", "urdu"), "code_switched": ("code_switching", "english")}


def order(key: str) -> str:
    return hashlib.sha256(f"{SEED}:{key}".encode()).hexdigest()


def record(sid: str, stype: str, category: str, lang: str, text: str, origin: str, licence: str, author: str) -> dict:
    code, script = LANG[lang]
    intent = f"{sid}-{'H' if stype == 'harmful' else 'B'}"
    is_src = lang == "english"
    ttype, parent = ("source", None) if is_src else DERIV[lang]
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": f"{intent}-{code}-base",
        "scenario_id": sid,
        "intent_id": intent,
        "scenario_type": stype,
        "category": category,
        "expected_behavior": ("refuse_and_redirect" if category == "self_harm" else "refuse") if stype == "harmful" else "comply",
        "contrast_intent_id": None,
        "intent_description": f"Calibration item ({category}); not part of the main study",
        "language": lang,
        "script": script,
        "text": text,
        "transformation": {
            "type": ttype,
            "source_record_id": None if is_src else f"{intent}-{LANG[parent][0]}-base",
            "method": "human",
            "author_id": author,
            "parameters": {"condition": "base"},
        },
        "equivalence": {"status": "source"} if is_src else {"status": "pending", "reference_record_id": f"{intent}-en-base"},
        "provenance": {"created_by": "research/dataset/build_calibration.py", "origin": origin, "license": licence, "notes": "calibration pilot only"},
    }


def main() -> None:
    selection = [json.loads(x) for x in (ROOT / "data/candidates/selection.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    selected_text = {f"SEL:{c['scenario_id']}:{k}": c[k] for c in selection for k in ("harmful_en", "benign_en") if c.get(k)}
    selected_ids = {c["source_id"] for c in selection}
    selected_strings = set(selected_text.values())
    overrides_path = Path(__file__).with_name("category_overrides.json")
    overrides = json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    records, log = [], {}

    # ---- Set A: non-overlapping items of the earlier 13-item pilot (human-written variants)
    pilot = [json.loads(x) for x in (ROOT / "dataset/examples/veriaudit-pilot.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    kept = [p for p in pilot if p["english"] not in selected_strings and p["intent_category"] in PILOT_CATEGORY]
    log["set_a_dropped_overlap"] = sorted(p["id"] for p in pilot if p["english"] in selected_strings)
    for i, p in enumerate(kept, start=1):
        stype, cat = PILOT_CATEGORY[p["intent_category"]]
        for lang in LANG:
            records.append(record(f"CAL-A{i:02d}", stype, cat, lang, p[lang], f"veriaudit-pilot:{p['id']}", "MIT (VeriAudit)", "pi"))
    log["set_a_items"] = len(kept)

    # ---- Set B: held-out English source items
    def not_near_selected(cands: dict[str, str]) -> set[str]:
        texts = {**selected_text, **cands}
        bad = set()
        for a, b, _ in near_duplicates(texts, DEDUP_THRESHOLD) + content_word_duplicates(texts, CONTENT_JACCARD):
            if a in cands and (b in selected_text or b in cands):
                bad.add(a)
            if b in cands and (a in selected_text or a in cands):
                bad.add(b)
        return set(cands) - bad

    adv = list(csv.DictReader((ROOT / "data/sources/advbench_harmful_behaviors.csv").open(encoding="utf-8")))
    adv_cands = {}
    for i, row in enumerate(adv):
        key = str(i)
        if key in selected_ids or row["goal"] in selected_strings:
            continue
        cat, _ = categorise(row["goal"], overrides, f"advbench:{key}")
        if cat is not None:
            adv_cands[f"ADV:{key}:{cat}"] = row["goal"]
    adv_ok = sorted(not_near_selected(adv_cands), key=order)
    # remove near-duplicates among the chosen items themselves, greedily in seeded order
    chosen: dict[str, str] = {}
    for k in adv_ok:
        trial = {**chosen, k: adv_cands[k]}
        if not (near_duplicates(trial, DEDUP_THRESHOLD) or content_word_duplicates(trial, CONTENT_JACCARD)):
            chosen[k] = adv_cands[k]
        if len(chosen) == N_HARMFUL_B:
            break
    for i, (k, text) in enumerate(sorted(chosen.items(), key=lambda kv: order(kv[0])), start=1):
        _, src_id, cat = k.split(":")
        records.append(record(f"CAL-BH{i:03d}", "harmful", cat, "english", text, f"advbench:{src_id}", "MIT (AdvBench)", "source:advbench"))
    log["set_b_harmful"] = len(chosen)
    log["set_b_harmful_pool_after_exclusions_and_dedup"] = len(adv_ok)

    xs = list(csv.DictReader((ROOT / "data/sources/xstest_prompts.csv").open(encoding="utf-8")))
    used_xs = {part for c in selection if c["source"] == "xstest" for part in c["source_id"].split("|")}
    xs_cands = {}
    for row in xs:
        if row["label"] != "safe" or row["id"] in used_xs or row["prompt"] in selected_strings:
            continue
        cat, _ = categorise(row["prompt"], overrides, f"xstest:{row['id']}")
        if cat is None and _ == "unassigned":
            cat = "safety_information"
        if cat is None:
            continue  # excluded topic
        xs_cands[f"XS:{row['id']}"] = row["prompt"]
    xs_ok = sorted(not_near_selected(xs_cands), key=order)[:N_BENIGN_B]
    for i, k in enumerate(xs_ok, start=1):
        records.append(
            record(f"CAL-BB{i:03d}", "benign", "safety_information", "english", xs_cands[k], f"xstest:{k.split(':')[1]}", "CC-BY-4.0 (XSTest)", "source:xstest")
        )
    log["set_b_benign"] = len(xs_ok)

    report = validate_objects(records, ValidationConfig(require_all_languages=False))
    if not report.ok:
        raise SystemExit(report.summary()[:3000])
    OUT.mkdir(parents=True, exist_ok=True)
    data = OUT / "veriaudit_x_calibration.jsonl"
    data.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    manifest = {
        "dataset_name": "VeriAudit-X calibration pilot",
        "dataset_version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "description": "Calibration pilot only (protocol §12): disjoint from the main study; never analysed as main-study results.",
        "data_file": data.name,
        "is_fixture": False,
        "is_calibration": True,
        "n_records": len(records),
        "build_log": log,
        "data_sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
