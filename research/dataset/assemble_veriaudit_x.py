"""Assemble VeriAudit-X records from the selection and the human authoring workflow, attach human
ratings, run automated QC, validate, and write leakage-free splits.

Inputs:  data/candidates/selection.jsonl, transformation_subset.json,
         data/candidates/authoring/{benign_authored,benign_validity}.jsonl, variants_*.jsonl,
         ratings_*.jsonl (see research/dataset/translation_worksheet.py), data/annotators.json
Outputs: data/veriaudit-x/<version>/veriaudit_x.jsonl, manifest.json, qc_report.md, splits/

    PYTHONPATH=backend python research/dataset/assemble_veriaudit_x.py --version 2.0.0-rc2
    PYTHONPATH=backend python research/dataset/assemble_veriaudit_x.py --version 2.0.0 --release

Candidate builds include only scenarios whose harmful and benign intents both have English plus
all three base forms, and list the rest. `--release` (freezing the main-study dataset, protocol
§12) additionally requires every selected scenario, uses the validator's release mode (paired
contrasts, benign-validity reviews) and writes nothing if anything fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from app.v2.quality.checks import check_variant
from app.v2.review import apply_equivalence_ratings
from app.veriaudit_x import authoring as A
from app.veriaudit_x.schema import SCHEMA_VERSION, EquivalenceRating, VeriAuditXRecord
from app.veriaudit_x.splits import write_splits
from app.veriaudit_x.validation import ValidationConfig, validate_objects

ROOT = Path(__file__).resolve().parents[2]
CAND = ROOT / "data" / "candidates"
AUTH = CAND / "authoring"
REGISTRY = ROOT / "data" / "annotators.json"
TODAY = date.today().isoformat()
SOURCE_LICENCE = {"advbench": "MIT (AdvBench)", "xstest": "CC-BY-4.0 (XSTest)", "veriaudit-v0.1": "MIT (VeriAudit)"}
SPLIT_SEED = 20261112


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.exists() else []


def sha_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def origin(c: dict, kind: str, benign: dict | None) -> str:
    if c["source"] == "xstest":
        safe_id, unsafe_id = c["source_id"].split("|")
        return f"xstest:{unsafe_id if kind == 'H' else safe_id}"
    if kind == "H":
        return f"{c['source']}:{c['source_id']}"
    how = "AI-drafted" if benign and benign.get("ai_generated") else "human-authored"
    return f"{how} benign contrast for {c['source']}:{c['source_id']}"


def benign_category(c: dict) -> str:
    # a benign contrast asks for protective/factual help on the harmful topic (protocol §3)
    return "information_request" if c["category"] == "misinformation" else "safety_information"


def base_record(c: dict, kind: str, *, lang: str, script: str, text: str, ttype: str, parent: str | None, cond: str, params: dict) -> dict:
    sid = c["scenario_id"]
    intent = f"{sid}-{kind}"
    stype = "harmful" if kind == "H" else "benign"
    return {
        "schema_version": SCHEMA_VERSION,
        "record_id": A.row_id(sid, kind, lang, cond),
        "scenario_id": sid,
        "intent_id": intent,
        "scenario_type": stype,
        "category": c["category"] if kind == "H" else benign_category(c),
        "expected_behavior": ("refuse_and_redirect" if c["category"] == "self_harm" else "refuse") if kind == "H" else "comply",
        "contrast_intent_id": f"{sid}-{'B' if kind == 'H' else 'H'}",
        "intent_description": f"Harmful request ({c['category']})" if kind == "H" else f"Benign contrast on the same topic ({c['category']})",
        "language": lang,
        "script": script,
        "text": text,
        "transformation": {
            "type": ttype,
            "source_record_id": parent,
            "method": "human",
            "tool": None,
            "author_id": None,
            "parameters": {"condition": cond, **params},
        },
        "equivalence": {"status": "source"} if ttype == "source" else {"status": "pending", "reference_record_id": f"{intent}-en-base"},
    }


def build(selection: list[dict], subset: set[str], release: bool) -> tuple[list[dict], dict]:
    benign = {r["scenario_id"]: r for r in load_jsonl(AUTH / "benign_authored.jsonl")}
    validity = defaultdict(list)
    for r in load_jsonl(AUTH / "benign_validity.jsonl"):
        validity[r["scenario_id"]].append(r)
    rows, _ = A.plan_rows(selection, subset, benign)
    plan = {r.row_id: r for r in rows}
    imported = A.load_variants(sorted(AUTH.glob("variants_*.jsonl")))
    variants = A.current_variants(rows, imported)
    stale_variants = sorted(set(imported) - set(variants))
    registry = A.load_registry(REGISTRY)
    human_ids = {r["id"] for r in registry.get("raters", []) if r.get("human") is True}

    ratings = defaultdict(list)
    stats = Counter()
    stats["stale_variants_source_changed"] = len(stale_variants)
    for p in sorted(AUTH.glob("ratings_*.jsonl")):
        for r in load_jsonl(p):
            if r["annotator_id"] not in human_ids:
                raise SystemExit(f"{p.name}: rating by unregistered rater {r['annotator_id']!r}")
            v = variants.get(r["record_id"])
            if v is None or r.get("text_sha256") != v["text_sha256"] or r.get("english_sha256", v.get("english_sha256")) != v.get("english_sha256"):
                stats["stale_or_orphan_ratings_ignored"] += 1
                continue
            ratings[r["record_id"]].append(r)

    records, excluded = [], {}
    for c in selection:
        sid = c["scenario_id"]
        b = benign.get(sid)
        en = {"H": c["harmful_en"], "B": c.get("benign_en") or (b or {}).get("benign_en")}
        missing = [f"{k}-en" for k, t in en.items() if not t]
        missing += [rid for k in "HB" if en[k] for form in A.FORMS if (rid := A.row_id(sid, k, form, "base")) not in variants]
        if missing:
            excluded[sid] = missing
            continue
        for kind in "HB":
            src = base_record(c, kind, lang="english", script="latin", text=en[kind], ttype="source", parent=None, cond="base", params={})
            ai_benign = kind == "B" and bool(b and b.get("ai_generated")) and not c.get("benign_en")
            src["transformation"]["author_id"] = (b or {}).get("author_id") if (kind == "B" and not c.get("benign_en")) else f"source:{c['source']}"
            src["transformation"]["method"] = "machine_post_edited" if ai_benign else "human"
            src["provenance"] = {
                "created_at": TODAY,
                "created_by": "research/dataset/assemble_veriaudit_x.py",
                "origin": origin(c, kind, b),
                "license": SOURCE_LICENCE[c["source"]] if (kind == "H" or c.get("benign_en")) else "VeriAudit-X (new work)",
            }
            quality = {"ai_generated": ai_benign, "automated_checks": _qc("english", en[kind], en[kind], "base", None)}
            if kind == "B" and not c.get("benign_en"):
                quality["benign_validity"] = [
                    {"reviewer_id": v["reviewer_id"], "benign": v["benign"], "topically_matched": v["topically_matched"], "notes": v.get("notes")}
                    for v in validity.get(sid, [])
                    if v.get("benign_text_sha256") == A.sha(en[kind]) and v["reviewer_id"] in human_ids
                ]
            src["quality"] = quality
            records.append(src)
            for rid, p in sorted((rid, p) for rid, p in plan.items() if p.intent_id == f"{sid}-{kind}"):
                v = variants.get(rid)
                if v is None:
                    if p.phase == 2:
                        stats["transformation_rows_not_yet_written"] += 1
                    continue
                params = p.parameters
                rec = base_record(
                    c,
                    kind,
                    lang=p.target_form,
                    script=p.target_script,
                    text=v["text"],
                    ttype=p.transformation_type,
                    parent=p.derive_from,
                    cond=p.condition,
                    params=params,
                )
                rec["transformation"]["author_id"] = v["author_id"]
                parent_text = en[kind] if p.derive_from.endswith("-en-base") else (variants.get(p.derive_from) or {}).get("text")
                qc = _qc("urdu" if p.condition == "T6" else p.target_form, v["text"], en[kind], p.condition, parent_text if p.condition != "base" else None)
                failed = [k for k, q in qc.items() if not q["passed"]]
                if failed:
                    rec["equivalence"].update(status="flagged", notes="automated check failed: " + ", ".join(failed))
                rec["provenance"] = {
                    "created_at": TODAY,
                    "created_by": "research/dataset/assemble_veriaudit_x.py",
                    "origin": f"variant of {origin(c, kind, b)}",
                    "license": "VeriAudit-X (new work)",
                }
                aid = v.get("drafting_aid", "none")
                if aid != "none":  # a tool drafted it and the translator edited it: never labelled pure human work
                    rec["transformation"].update(method="machine_post_edited", tool=f"translator-disclosed {aid}")
                rec["quality"] = {"ai_generated": aid != "none", "generator_id": aid if aid != "none" else None, "automated_checks": qc}
                if v.get("self_assessment"):
                    rec["quality"]["translator_self_assessment"] = v["self_assessment"]
                if ratings.get(rid):
                    model = VeriAuditXRecord.model_validate(rec)
                    model = apply_equivalence_ratings(
                        model,
                        [EquivalenceRating.model_validate({k: x for k, x in r.items() if k not in ("record_id", "english_sha256")}) for r in ratings[rid]],
                    )
                    rec = model.model_dump(mode="json")
                    stats["variants_with_human_ratings"] += 1
                records.append(rec)
    if release and excluded:
        raise SystemExit(f"--release: {len(excluded)} selected scenarios are incomplete, e.g. {next(iter(excluded.items()))}")
    stats["scenarios_included"] = len({r["scenario_id"] for r in records})
    stats["scenarios_excluded_incomplete"] = len(excluded)
    return records, {"stats": dict(stats), "excluded": excluded}


def _qc(lang: str, text: str, english: str, cond: str, base_text: str | None) -> dict:
    return {q.name: {"passed": q.passed, "value": q.value, "detail": q.detail} for q in check_variant(lang, text, english, cond, base_text)}


def qc_report(version: str, records: list[dict], report, info: dict, split_manifest: dict | None) -> str:
    by_check = defaultdict(lambda: [0, 0])
    by_cond_lang = defaultdict(lambda: [0, 0])
    statuses = Counter()
    for r in records:
        if r["transformation"]["type"] == "source":
            continue
        statuses[r["equivalence"]["status"]] += 1
        ok = all(v["passed"] for v in r["quality"]["automated_checks"].values())
        k = (r["transformation"]["parameters"]["condition"], r["language"])
        by_cond_lang[k][0] += ok
        by_cond_lang[k][1] += 1
        for name, v in r["quality"]["automated_checks"].items():
            by_check[name][0] += v["passed"]
            by_check[name][1] += 1
    lines = [
        f"# VeriAudit-X {version} — dataset quality report",
        "",
        f"Records: {len(records)} · scenarios: {len({r['scenario_id'] for r in records})} · intents: {len({r['intent_id'] for r in records})}",
        f"Validation: {len(report.errors)} errors, {len(report.warnings)} warnings",
        f"Assembly: {info['stats']}",
        f"Scenarios excluded as incomplete: {len(info['excluded'])}",
        "",
        "Automated checks are screens. Passing them is not equivalence verification.",
        "Equivalence status counts below come only from human ratings (translation_guide.md §6).",
        "",
        "| Equivalence status | variants |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in sorted(statuses.items())],
        "",
        "| Check | passed / total |",
        "|---|---|",
        *[f"| {k} | {v[0]} / {v[1]} |" for k, v in sorted(by_check.items())],
        "",
        "| Condition | Language | all checks passed / total |",
        "|---|---|---|",
        *[f"| {k[0]} | {k[1]} | {v[0]} / {v[1]} |" for k, v in sorted(by_cond_lang.items())],
        "",
        "## Validation issues by code",
        "",
        *[f"- {k}: {v}" for k, v in sorted(report.codes().items())],
    ]
    if split_manifest:
        lines += [
            "",
            "## Splits (scenario-grouped)",
            "",
            *[f"- {s}: {v['scenarios']} scenarios, {v['records']} records" for s, v in split_manifest["statistics"].items()],
        ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="e.g. 2.0.0-rc2 (candidate) or 2.0.0 (release)")
    ap.add_argument("--release", action="store_true")
    args = ap.parse_args(argv)
    if args.release and "-" in args.version:
        raise SystemExit("--release needs a plain version (e.g. 2.0.0)")
    out = ROOT / "data" / "veriaudit-x" / args.version
    if args.release and out.exists():
        raise SystemExit(f"{out} exists; a released version is immutable")

    selection = load_jsonl(CAND / "selection.jsonl")
    subset = set(json.loads((CAND / "transformation_subset.json").read_text(encoding="utf-8")))
    records, info = build(selection, subset, args.release)
    registry = A.load_registry(REGISTRY)
    raters = frozenset(r["id"] for r in registry.get("raters", []) if r.get("human") is True)
    report = validate_objects(records, ValidationConfig(release=args.release, registered_raters=raters))
    if args.release and not report.ok:
        print(report.summary()[:5000], file=sys.stderr)
        raise SystemExit("--release: validation failed; nothing written")
    if not records:
        print(f"no complete scenarios yet ({len(info['excluded'])} incomplete); nothing written. See authoring/STATUS.md")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    data_file = out / "veriaudit_x.jsonl"
    with data_file.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    split_manifest = write_splits(report.records, out / "splits", seed=SPLIT_SEED, source_file=data_file, dataset_version=args.version) if report.ok else None
    inputs = [CAND / "selection.jsonl", CAND / "transformation_subset.json", REGISTRY, *sorted(AUTH.glob("*.jsonl"))]
    manifest = {
        "dataset_name": "VeriAudit-X",
        "dataset_version": args.version,
        "schema_version": SCHEMA_VERSION,
        "description": (
            ("Frozen main-study release. " if args.release else "Candidate build (not for analysis). ")
            + "Harmful/benign scenario pairs in English, Urdu script, Roman Urdu and code-switched Urdu-English; "
            "non-English variants written by human translators; equivalence status from independent human review only."
        ),
        "data_file": data_file.name,
        "is_fixture": False,
        "is_release": args.release,
        "n_records": len(records),
        "n_scenarios": info["stats"]["scenarios_included"],
        "inputs_sha256": {str(p.relative_to(ROOT)): sha_file(p) for p in inputs},
        "data_sha256": sha_file(data_file),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out / "qc_report.md").write_text(qc_report(args.version, records, report, info, split_manifest), encoding="utf-8")
    print(f"wrote {len(records)} records ({info['stats']['scenarios_included']} scenarios) to {out}; validation ok: {report.ok}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
