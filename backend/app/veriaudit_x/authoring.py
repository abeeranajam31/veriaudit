"""Human authoring workflow for VeriAudit-X variants (docs/v2/translation_guide.md).

Three stages, each a CSV exported for people and re-imported with strict validation:

  A. Benign contrasts. `benign_authoring.csv`: write an English benign contrast for each harmful
     scenario that has none. Then `benign_review.csv`: a different person checks each contrast is
     genuinely benign and on the same topic (protocol §4.2 rule 5).
  B. Translation. `translation_worksheet.csv`: one row per variant to write. Row IDs are the
     record IDs the assembled dataset will use; `derive_from` links each row to its parent row,
     so every variant stays tied to its scenario and intent. Read-only cells are protected by
     `source_check`, so an edited source or a pre-filled v0.1 cell is caught at import.
  C. Independent review. `review_<reviewer>.csv`: a human who did not write the variant rates
     equivalence, harm preservation and naturalness. Disagreements go to
     `adjudication.csv`. Ratings carry the SHA-256 of the exact text rated.

Nothing here generates text. AI may only appear as a recorded `ai_generated` drafter of
benign contrasts (column `drafted_by_ai`), which the assembler propagates to
`quality.ai_generated`; AI never counts as a reviewer or rater.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

from app.v2.quality.checks import check_variant

FORMS = ("urdu", "roman_urdu", "code_switched")
LANG_CODE = {"english": "en", "urdu": "ur", "roman_urdu": "rur", "code_switched": "cs"}
SCRIPT = {"english": "latin", "urdu": "perso_arabic", "roman_urdu": "latin", "code_switched": "latin"}
# base form -> (transformation type, parent form)
BASE_DERIVATION = {"urdu": ("translation", "english"), "roman_urdu": ("transliteration", "urdu"), "code_switched": ("code_switching", "english")}
# condition -> (target form, script, transformation type, parent form, parameters) - protocol §5.2
TRANSFORMS = {
    "T1": ("roman_urdu", "latin", "orthographic_variation", "roman_urdu", {"spelling": "alternative_informal"}),
    "T2": ("roman_urdu", "latin", "orthographic_variation", "roman_urdu", {"spelling": "consistent_formal"}),
    "T3": ("urdu", "perso_arabic", "register_shift", "urdu", {"register": "colloquial"}),
    "T4": ("code_switched", "latin", "code_switching", "code_switched", {"english_ratio_target": "<=0.20"}),
    "T5": ("code_switched", "latin", "code_switching", "code_switched", {"english_ratio_target": ">=0.60"}),
    "T6": ("code_switched", "mixed", "code_switching", "urdu", {"script_mixing": "urdu_script_with_latin_english"}),
}
INSTRUCTIONS = {
    "urdu": "Translate the English into natural, standard Urdu in Urdu script. Same request, same strength.",
    "roman_urdu": (
        "Write YOUR Urdu-script row (derive_from) in Latin letters, spelled the way people commonly type Urdu (e.g. 'kya', 'nahi', 'hai'). Do not re-translate."
    ),
    "code_switched": (
        "Write the request as a bilingual Pakistani user would type it: Urdu sentence structure in Latin letters "
        "with some English words. Natural mixing, not word-by-word."
    ),
    "T1": "Rewrite the Roman Urdu row with a different common informal spelling (e.g. nahi->nai, kya->kia, hai->he). Change spelling only.",
    "T2": "Rewrite the Roman Urdu row in a consistent, more formal transliteration (mark long vowels, render ain/hamza). Change spelling only.",
    "T3": "Rewrite the Urdu-script row in colloquial, conversational register. Keep the request and its strength the same.",
    "T4": "Rewrite the code-switched row with few English words (about 1 in 5 content words English).",
    "T5": "Rewrite the code-switched row with many English words (about 3 in 5 content words English).",
    "T6": "Rewrite the Urdu-script row keeping Urdu script, but leave English content words in Latin letters (e.g. 'script', 'password').",
}
V01_AUTHOR = "pi"  # the v0.1 variants were written by the lead researcher (dataset/README.md)
STATUS = ("todo", "done", "cannot_translate")
JUDGEMENTS = ("equivalent", "partially_equivalent", "not_equivalent")
AMBIGUITY = ("none", "lexical", "referential", "cultural", "harm_level_unclear", "other")
YES_NO = {"yes": True, "no": False}
YES_NO_UNSURE = {"yes": True, "no": False, "unsure": None}

WORKSHEET_COLUMNS = [
    "row_id", "phase", "scenario_id", "intent_id", "intent_type", "category", "condition", "target_form", "target_script",
    "derive_from", "instruction", "english_source", "locked", "source_check",
    "text", "status", "self_equivalence", "self_harm_preserved", "naturalness", "ambiguity", "comments",
]  # fmt: skip
BENIGN_COLUMNS = ["scenario_id", "category", "harmful_english", "source_check", "benign_english", "drafted_by_ai", "notes"]
BENIGN_REVIEW_COLUMNS = ["scenario_id", "category", "harmful_english", "benign_english", "source_check", "benign", "topically_matched", "notes"]
REVIEW_COLUMNS = [
    "row_id", "condition", "target_form", "instruction", "english_source", "parent_text", "text", "source_check",
    "judgement", "harm_preserved", "naturalness", "notes",
]  # fmt: skip
ADJUDICATION_COLUMNS = ["row_id", "english_source", "text", "ratings_summary", "source_check", "decision", "harm_preserved", "rationale"]
DECISIONS = {"accept": "equivalent", "revise": "partially_equivalent", "reject": "not_equivalent"}


class WorkflowError(ValueError):
    """Import refused; `problems` lists every issue (row, column, message)."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__(f"{len(problems)} problem(s):\n" + "\n".join(problems[:50]))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check(*parts: str) -> str:
    return sha("\x1f".join(parts))[:12]


def row_id(scenario_id: str, kind: str, form: str, condition: str) -> str:
    return f"{scenario_id}-{kind}-{LANG_CODE[form]}-{condition.lower()}"


# --------------------------------------------------------------------------- plan


@dataclass
class PlannedRow:
    row_id: str
    phase: int  # 1 = base forms (confirmatory analyses); 2 = controlled transformations (RQ2)
    scenario_id: str
    intent_id: str
    intent_type: str
    category: str
    condition: str
    target_form: str
    target_script: str
    derive_from: str
    english_source: str
    locked_text: str = ""  # pre-filled human v0.1 variant: not to be edited
    transformation_type: str = ""
    parameters: dict = field(default_factory=dict)

    @property
    def source_check(self) -> str:
        return check(self.row_id, self.english_source, self.locked_text)


def benign_english(c: dict, authored: dict[str, dict]) -> str | None:
    return c.get("benign_en") or (authored.get(c["scenario_id"]) or {}).get("benign_en")


def plan_rows(selection: list[dict], subset: set[str], authored_benign: dict[str, dict]) -> tuple[list[PlannedRow], list[str]]:
    """Every variant row to be written, plus the scenario IDs whose benign English is still missing
    (their benign rows cannot be planned yet)."""
    rows: list[PlannedRow] = []
    waiting: list[str] = []
    for c in selection:
        sid = c["scenario_id"]
        for kind, en in (("H", c["harmful_en"]), ("B", benign_english(c, authored_benign))):
            if not en:
                waiting.append(sid)
                continue
            intent_type = "harmful" if kind == "H" else "benign"
            fixed = (c.get("v1_variants") or {}) if (kind == "H" and c["source"] == "veriaudit-v0.1") else {}
            for form in FORMS:
                ttype, parent = BASE_DERIVATION[form]
                rows.append(
                    PlannedRow(
                        row_id=row_id(sid, kind, form, "base"),
                        phase=1,
                        scenario_id=sid,
                        intent_id=f"{sid}-{kind}",
                        intent_type=intent_type,
                        category=c["category"],
                        condition="base",
                        target_form=form,
                        target_script=SCRIPT[form],
                        derive_from=row_id(sid, kind, parent, "base"),
                        english_source=en,
                        locked_text=fixed.get(form, ""),
                        transformation_type=ttype,
                    )
                )
            if sid in subset:
                for cond, (form, script, ttype, parent, params) in TRANSFORMS.items():
                    rows.append(
                        PlannedRow(
                            row_id=row_id(sid, kind, form, cond),
                            phase=2,
                            scenario_id=sid,
                            intent_id=f"{sid}-{kind}",
                            intent_type=intent_type,
                            category=c["category"],
                            condition=cond,
                            target_form=form,
                            target_script=script,
                            derive_from=row_id(sid, kind, parent, "base"),
                            english_source=en,
                            transformation_type=ttype,
                            parameters=params,
                        )
                    )
    return rows, sorted(set(waiting))


# --------------------------------------------------------------------------- csv helpers


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:  # BOM: opens correctly in Excel
        w = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)
    return path


def read_csv(path: Path, required: list[str]) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in required if c not in (reader.fieldnames or [])]
    if missing:
        raise WorkflowError([f"file is missing columns: {missing}"])
    return [{k: (v or "").strip() for k, v in row.items() if k is not None} for row in reader]


# --------------------------------------------------------------------------- stage A: benign contrasts


def export_benign_authoring(selection: list[dict], authored: dict[str, dict]) -> list[dict]:
    out = []
    for c in selection:
        if benign_english(c, authored):
            continue
        out.append(
            {
                "scenario_id": c["scenario_id"],
                "category": c["category"],
                "harmful_english": c["harmful_en"],
                "source_check": check(c["scenario_id"], c["harmful_en"]),
                "benign_english": "",
                "drafted_by_ai": "no",
                "notes": "",
            }
        )
    return out


def import_benign_authoring(path: Path, author: str, selection: list[dict]) -> list[dict]:
    by_id = {c["scenario_id"]: c for c in selection}
    problems, out, seen = [], [], set()
    for i, row in enumerate(read_csv(path, BENIGN_COLUMNS), start=2):
        sid = row["scenario_id"]
        c = by_id.get(sid)
        where = f"line {i} ({sid})"
        if c is None:
            problems.append(f"{where}: unknown scenario_id")
            continue
        if sid in seen:
            problems.append(f"{where}: duplicate scenario_id")
        seen.add(sid)
        if row["source_check"] != check(sid, c["harmful_en"]):
            problems.append(f"{where}: harmful_english or scenario_id was edited (source_check mismatch)")
        if not row["benign_english"]:
            continue  # not written yet
        if row["drafted_by_ai"] not in YES_NO:
            problems.append(f"{where}: drafted_by_ai must be yes or no")
            continue
        out.append(
            {
                "scenario_id": sid,
                "benign_en": row["benign_english"],
                "author_id": author,
                "ai_generated": YES_NO[row["drafted_by_ai"]],
                "notes": row["notes"],
            }
        )
    if problems:
        raise WorkflowError(problems)
    return out


def export_benign_review(selection: list[dict], authored: dict[str, dict], reviewer: str) -> list[dict]:
    out = []
    for c in selection:
        a = authored.get(c["scenario_id"])
        if not a or a["author_id"] == reviewer:
            continue  # nobody reviews their own contrast
        out.append(
            {
                "scenario_id": c["scenario_id"],
                "category": c["category"],
                "harmful_english": c["harmful_en"],
                "benign_english": a["benign_en"],
                "source_check": check(c["scenario_id"], c["harmful_en"], a["benign_en"]),
                "benign": "",
                "topically_matched": "",
                "notes": "",
            }
        )
    return out


def import_benign_review(path: Path, reviewer: str, selection: list[dict], authored: dict[str, dict]) -> list[dict]:
    by_id = {c["scenario_id"]: c for c in selection}
    problems, out = [], []
    for i, row in enumerate(read_csv(path, BENIGN_REVIEW_COLUMNS), start=2):
        sid = row["scenario_id"]
        where = f"line {i} ({sid})"
        c, a = by_id.get(sid), authored.get(sid)
        if c is None or a is None:
            problems.append(f"{where}: unknown scenario or no authored contrast")
            continue
        if a["author_id"] == reviewer:
            problems.append(f"{where}: {reviewer} wrote this contrast and cannot review it")
            continue
        if row["source_check"] != check(sid, c["harmful_en"], a["benign_en"]):
            problems.append(f"{where}: texts changed since export (source_check mismatch) - re-export the review sheet")
            continue
        if not row["benign"] and not row["topically_matched"]:
            continue
        if row["benign"] not in YES_NO or row["topically_matched"] not in YES_NO:
            problems.append(f"{where}: benign and topically_matched must be yes or no")
            continue
        out.append(
            {
                "scenario_id": sid,
                "reviewer_id": reviewer,
                "benign": YES_NO[row["benign"]],
                "topically_matched": YES_NO[row["topically_matched"]],
                "notes": row["notes"] or None,
                "benign_text_sha256": sha(a["benign_en"]),
            }
        )
    if problems:
        raise WorkflowError(problems)
    return out


# --------------------------------------------------------------------------- stage B: translation


def export_worksheet(rows: list[PlannedRow], phases: tuple[int, ...] = (1, 2)) -> list[dict]:
    out = []
    for r in rows:
        if r.phase not in phases:
            continue
        out.append(
            {
                "row_id": r.row_id,
                "phase": r.phase,
                "scenario_id": r.scenario_id,
                "intent_id": r.intent_id,
                "intent_type": r.intent_type,
                "category": r.category,
                "condition": r.condition,
                "target_form": r.target_form,
                "target_script": r.target_script,
                "derive_from": r.derive_from,
                "instruction": INSTRUCTIONS[r.condition if r.condition != "base" else r.target_form],
                "english_source": r.english_source,
                "locked": "yes" if r.locked_text else "no",
                "source_check": r.source_check,
                "text": r.locked_text,
                "status": "done" if r.locked_text else "todo",
                "self_equivalence": "",
                "self_harm_preserved": "",
                "naturalness": "",
                "ambiguity": "",
                "comments": "pre-filled v0.1 human translation - do not edit" if r.locked_text else "",
            }
        )
    return out


@dataclass
class ImportResult:
    variants: list[dict]
    warnings: list[str]


def import_worksheet(path: Path, translator: str, rows: list[PlannedRow]) -> ImportResult:
    """Validate a filled worksheet. Any problem refuses the whole import (fix and re-import);
    automated QC concerns are returned as warnings and recorded with the variant."""
    plan = {r.row_id: r for r in rows}
    problems, warnings, out, seen = [], [], [], set()
    filled = {}
    data = read_csv(path, WORKSHEET_COLUMNS)
    for row in data:
        if row.get("text"):
            filled[row["row_id"]] = row["text"]
    for i, row in enumerate(data, start=2):
        rid = row["row_id"]
        where = f"line {i} ({rid})"
        p = plan.get(rid)
        if p is None:
            problems.append(f"{where}: unknown row_id (do not add or rename rows)")
            continue
        if rid in seen:
            problems.append(f"{where}: duplicate row_id")
        seen.add(rid)
        if row["source_check"] != p.source_check:
            problems.append(f"{where}: english_source, locked text or row_id was edited (source_check mismatch)")
            continue
        if p.locked_text:
            if row["text"] != p.locked_text:
                problems.append(f"{where}: locked v0.1 text was edited")
            continue
        status = row["status"] or "todo"
        if status not in STATUS:
            problems.append(f"{where}: status must be one of {STATUS}")
            continue
        if status == "todo":
            continue
        if status == "cannot_translate":
            if not row["comments"]:
                problems.append(f"{where}: cannot_translate needs a reason in comments")
                continue
            out.append({"row_id": rid, "status": "cannot_translate", "author_id": translator, "comments": row["comments"]})
            continue
        # status == done
        if not row["text"]:
            problems.append(f"{where}: status done but text is empty")
            continue
        if row["self_equivalence"] not in JUDGEMENTS:
            problems.append(f"{where}: self_equivalence must be one of {JUDGEMENTS}")
        if row["self_harm_preserved"] not in YES_NO_UNSURE:
            problems.append(f"{where}: self_harm_preserved must be yes, no or unsure")
        if row["naturalness"] not in {"1", "2", "3", "4", "5"}:
            problems.append(f"{where}: naturalness must be 1-5")
        if (row["ambiguity"] or "none") not in AMBIGUITY:
            problems.append(f"{where}: ambiguity must be one of {AMBIGUITY}")
        # parent = the English source, or the parent row's text in this sheet (incl. locked v0.1 text)
        parent_text = p.english_source if p.derive_from.endswith("-en-base") else filled.get(p.derive_from)
        qc_lang = "urdu" if p.condition == "T6" else p.target_form
        base_text = parent_text if p.condition != "base" else None
        qc = check_variant(qc_lang, row["text"], p.english_source, p.condition, base_text)
        failed = [q.name for q in qc if not q.passed]
        if failed:
            warnings.append(f"{where}: automated checks flagged {failed} - the variant will enter review as 'flagged'")
        out.append(
            {
                "row_id": rid,
                "status": "done",
                "text": row["text"],
                "text_sha256": sha(row["text"]),
                "author_id": translator,
                "derive_from": p.derive_from,
                "self_assessment": {
                    "equivalence": row["self_equivalence"] or None,
                    "harm_preserved": YES_NO_UNSURE.get(row["self_harm_preserved"]),
                    "naturalness": int(row["naturalness"]) if row["naturalness"] in {"1", "2", "3", "4", "5"} else None,
                    "ambiguity": row["ambiguity"] or "none",
                    "comments": row["comments"] or None,
                },
            }
        )
    if problems:
        raise WorkflowError(problems)
    return ImportResult(out, warnings)


# --------------------------------------------------------------------------- stage C: review and adjudication


def load_variants(paths: list[Path]) -> dict[str, dict]:
    """Imported variants keyed by row_id; a later import of the same row (a revision) replaces the earlier one."""
    out: dict[str, dict] = {}
    for p in sorted(paths):
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if line.strip():
                v = json.loads(line)
                if v.get("status") == "done":
                    out[v["row_id"]] = v
    return out


def locked_variants(rows: list[PlannedRow]) -> dict[str, dict]:
    return {r.row_id: {"row_id": r.row_id, "text": r.locked_text, "text_sha256": sha(r.locked_text), "author_id": V01_AUTHOR} for r in rows if r.locked_text}


def export_review(rows: list[PlannedRow], variants: dict[str, dict], reviewer: str, already_rated: set[str] = frozenset()) -> list[dict]:
    plan = {r.row_id: r for r in rows}
    out = []
    for rid, v in sorted(variants.items()):
        p = plan.get(rid)
        if p is None or v["author_id"] == reviewer or (rid, v["text_sha256"]) in already_rated:
            continue
        parent = variants.get(p.derive_from, {}).get("text", p.english_source if p.derive_from.endswith("-en-base") else "")
        out.append(
            {
                "row_id": rid,
                "condition": p.condition,
                "target_form": p.target_form,
                "instruction": INSTRUCTIONS[p.condition if p.condition != "base" else p.target_form],
                "english_source": p.english_source,
                "parent_text": parent,
                "text": v["text"],
                "source_check": check(rid, p.english_source, v["text"]),
                "judgement": "",
                "harm_preserved": "",
                "naturalness": "",
                "notes": "",
            }
        )
    return out


def import_review(path: Path, reviewer: str, rows: list[PlannedRow], variants: dict[str, dict], registry: dict) -> list[dict]:
    """-> rating dicts for research/dataset/merge_human_ratings.py (one per rated row)."""
    _check_registered(reviewer, registry)
    plan = {r.row_id: r for r in rows}
    problems, out = [], []
    for i, row in enumerate(read_csv(path, REVIEW_COLUMNS), start=2):
        rid = row["row_id"]
        where = f"line {i} ({rid})"
        p, v = plan.get(rid), variants.get(rid)
        if p is None or v is None:
            problems.append(f"{where}: unknown row or no imported variant")
            continue
        if v["author_id"] == reviewer:
            problems.append(f"{where}: {reviewer} wrote this variant and cannot review it")
            continue
        if row["source_check"] != check(rid, p.english_source, v["text"]):
            problems.append(f"{where}: the variant changed since this sheet was exported - re-export")
            continue
        if not row["judgement"]:
            continue
        if row["judgement"] not in JUDGEMENTS:
            problems.append(f"{where}: judgement must be one of {JUDGEMENTS}")
            continue
        if row["harm_preserved"] not in YES_NO_UNSURE:
            problems.append(f"{where}: harm_preserved must be yes, no or unsure")
            continue
        if row["naturalness"] and row["naturalness"] not in {"1", "2", "3", "4", "5"}:
            problems.append(f"{where}: naturalness must be 1-5")
            continue
        out.append(
            {
                "record_id": rid,
                "annotator_id": reviewer,
                "rater_role": "independent_reviewer",
                "text_sha256": v["text_sha256"],
                "judgement": row["judgement"],
                "harm_preserved": YES_NO_UNSURE[row["harm_preserved"]],
                "naturalness": int(row["naturalness"]) if row["naturalness"] else None,
                "notes": row["notes"] or None,
            }
        )
    if problems:
        raise WorkflowError(problems)
    return out


def needs_adjudication(ratings: list[dict]) -> bool:
    """Independent reviewers disagree, or a single reviewer raised a concern."""
    ind = [r for r in ratings if r["rater_role"] == "independent_reviewer"]
    keys = {(r["judgement"], r["harm_preserved"]) for r in ind}
    concern = any(r["judgement"] != "equivalent" or r["harm_preserved"] is not True for r in ind)
    return len(keys) > 1 or (concern and len(ind) >= 1)


def export_adjudication(rows: list[PlannedRow], variants: dict[str, dict], ratings: list[dict], adjudicator: str) -> list[dict]:
    plan = {r.row_id: r for r in rows}
    by_row: dict[str, list[dict]] = {}
    for r in ratings:
        v = variants.get(r["record_id"])
        if v and r.get("text_sha256") == v["text_sha256"]:  # ignore stale ratings
            by_row.setdefault(r["record_id"], []).append(r)
    out = []
    for rid, rs in sorted(by_row.items()):
        v = variants[rid]
        if v["author_id"] == adjudicator or any(r["annotator_id"] == adjudicator for r in rs):
            continue  # the adjudicator must be a third person
        if any(r["rater_role"] == "adjudicator" for r in rs) or not needs_adjudication(rs):
            continue
        summary = "; ".join(f"{r['annotator_id']}: {r['judgement']}, harm_preserved={r['harm_preserved']}, {r.get('notes') or ''}" for r in rs)
        out.append(
            {
                "row_id": rid,
                "english_source": plan[rid].english_source,
                "text": v["text"],
                "ratings_summary": summary,
                "source_check": check(rid, plan[rid].english_source, v["text"]),
                "decision": "",
                "harm_preserved": "",
                "rationale": "",
            }
        )
    return out


def import_adjudication(path: Path, adjudicator: str, rows: list[PlannedRow], variants: dict[str, dict], registry: dict) -> list[dict]:
    _check_registered(adjudicator, registry)
    plan = {r.row_id: r for r in rows}
    problems, out = [], []
    for i, row in enumerate(read_csv(path, ADJUDICATION_COLUMNS), start=2):
        rid = row["row_id"]
        where = f"line {i} ({rid})"
        p, v = plan.get(rid), variants.get(rid)
        if p is None or v is None:
            problems.append(f"{where}: unknown row")
            continue
        if v["author_id"] == adjudicator:
            problems.append(f"{where}: {adjudicator} wrote this variant and cannot adjudicate it")
            continue
        if row["source_check"] != check(rid, p.english_source, v["text"]):
            problems.append(f"{where}: the variant changed since export - re-export")
            continue
        if not row["decision"]:
            continue
        if row["decision"] not in DECISIONS:
            problems.append(f"{where}: decision must be accept, revise or reject")
            continue
        if not row["rationale"]:
            problems.append(f"{where}: a rationale is required")
            continue
        if row["harm_preserved"] not in YES_NO_UNSURE:
            problems.append(f"{where}: harm_preserved must be yes, no or unsure")
            continue
        out.append(
            {
                "record_id": rid,
                "annotator_id": adjudicator,
                "rater_role": "adjudicator",
                "text_sha256": v["text_sha256"],
                "judgement": DECISIONS[row["decision"]],
                "harm_preserved": YES_NO_UNSURE[row["harm_preserved"]],
                "notes": f"{row['decision']}: {row['rationale']}",
            }
        )
    if problems:
        raise WorkflowError(problems)
    return out


def load_registry(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _check_registered(rater: str, registry: dict) -> None:
    entry = next((r for r in registry.get("raters", []) if r.get("id") == rater), None)
    if entry is None or entry.get("human") is not True:
        raise WorkflowError([f"{rater!r} is not a registered human rater in the annotator registry (data/annotators.json)"])
