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
import re
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
DRAFTING_AIDS = ("none", "machine_translation", "ai_assistant")  # disclosed by the translator; recorded as provenance
YES_NO = {"yes": True, "no": False}
YES_NO_UNSURE = {"yes": True, "no": False, "unsure": None}

WORKSHEET_COLUMNS = [
    "row_id", "phase", "scenario_id", "intent_id", "intent_type", "category", "condition", "target_form", "target_script",
    "derive_from", "instruction", "english_source", "locked", "source_check",
    "text", "status", "drafting_aid", "self_equivalence", "self_harm_preserved", "naturalness", "ambiguity", "comments",
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


# --------------------------------------------------------------------------- sheet helpers (CSV and XLSX)

# columns people fill in; every other column is read-only (locked in .xlsx, checksum-protected in both)
# Review sheet for AI-drafted benign candidates (research/dataset/benign_candidates.py). It is a
# triage aid only: nothing is imported from it. An accepted candidate enters the dataset solely when
# a human author enters it in the benign authoring sheet with drafted_by_ai = yes (stage A1).
CANDIDATE_REVIEW_COLUMNS = [
    "scenario_id", "category", "harmful_english", "candidate_benign", "legitimate_intent", "rationale", "flags",
    "over_refusal_risk", "expected_behavior", "provenance",
    "reviewer_id", "candidate_decision", "is_benign", "same_topic", "realistic", "useful_answer_possible",
    "edited_text", "reject_reason", "notes",
]  # fmt: skip

EDITABLE = {
    "worksheet": ["text", "status", "drafting_aid", "self_equivalence", "self_harm_preserved", "naturalness", "ambiguity", "comments"],
    "benign": ["benign_english", "drafted_by_ai", "notes"],
    "benign_review": ["benign", "topically_matched", "notes"],
    "review": ["judgement", "harm_preserved", "naturalness", "notes"],
    "adjudication": ["decision", "harm_preserved", "rationale"],
    "candidate_review": [
        "reviewer_id",
        "candidate_decision",
        "is_benign",
        "same_topic",
        "realistic",
        "useful_answer_possible",
        "edited_text",
        "reject_reason",
        "notes",
    ],
}
CHOICES = {
    "status": STATUS,
    "drafting_aid": DRAFTING_AIDS,
    "self_equivalence": JUDGEMENTS,
    "judgement": JUDGEMENTS,
    "self_harm_preserved": ("yes", "no", "unsure"),
    "harm_preserved": ("yes", "no", "unsure"),
    "naturalness": ("1", "2", "3", "4", "5"),
    "ambiguity": AMBIGUITY,
    "drafted_by_ai": ("yes", "no"),
    "benign": ("yes", "no"),
    "topically_matched": ("yes", "no"),
    "decision": ("accept", "revise", "reject"),
    "candidate_decision": ("accept", "accept_with_edits", "reject"),
    "is_benign": ("yes", "no", "unsure"),
    "same_topic": ("yes", "no"),
    "realistic": ("yes", "no"),
    "useful_answer_possible": ("yes", "no"),
}
SHEET_KIND = {
    tuple(WORKSHEET_COLUMNS): "worksheet",
    tuple(BENIGN_COLUMNS): "benign",
    tuple(BENIGN_REVIEW_COLUMNS): "benign_review",
    tuple(REVIEW_COLUMNS): "review",
    tuple(ADJUDICATION_COLUMNS): "adjudication",
    tuple(CANDIDATE_REVIEW_COLUMNS): "candidate_review",
}


def write_sheet(path: Path, columns: list[str], rows: list[dict]) -> Path:
    """Write `.csv` (UTF-8 with BOM) or `.xlsx` depending on the suffix."""
    return write_xlsx(path, columns, rows) if Path(path).suffix.lower() == ".xlsx" else write_csv(path, columns, rows)


def write_xlsx(path: Path, columns: list[str], rows: list[dict]) -> Path:
    """Spreadsheet for translators/reviewers: read-only columns locked and shaded, dropdowns for every
    enumerated field, Urdu-script text right-to-left. Sheet protection has no password - it prevents
    accidents, not deliberate edits (the import checksums catch those)."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Protection
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    kind = SHEET_KIND.get(tuple(columns))
    editable = set(EDITABLE.get(kind, columns))
    wb = Workbook()
    ws = wb.active
    ws.title = "work"
    ws.append(columns)
    grey = PatternFill("solid", fgColor="EEEEEE")
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in rows:
        ws.append([r.get(c, "") for c in columns])
    n = len(rows) + 1
    for j, col in enumerate(columns, start=1):
        letter = get_column_letter(j)
        ws.column_dimensions[letter].width = (
            60
            if col
            in (
                "english_source",
                "text",
                "instruction",
                "parent_text",
                "harmful_english",
                "benign_english",
                "candidate_benign",
                "edited_text",
                "rationale",
                "legitimate_intent",
            )
            else 16
        )
        for i in range(2, n + 1):
            cell = ws.cell(row=i, column=j)
            locked = col not in editable or (
                col == "text" and ws.cell(row=i, column=columns.index("locked") + 1).value == "yes" if "locked" in columns else False
            )
            cell.protection = Protection(locked=locked)
            if locked:
                cell.fill = grey
            rtl = isinstance(cell.value, str) and bool(_ARABIC.search(cell.value))
            if col == "text" and "target_script" in columns:
                rtl = rtl or ws.cell(row=i, column=columns.index("target_script") + 1).value in ("perso_arabic", "mixed")
            cell.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right" if rtl else "left", readingOrder=2 if rtl else 1)
        if col in CHOICES and col in editable and n > 1:
            dv = DataValidation(type="list", formula1='"' + ",".join(CHOICES[col]) + '"', allow_blank=True, showErrorMessage=True)
            ws.add_data_validation(dv)
            dv.add(f"{letter}2:{letter}{n}")
    ws.freeze_panes = "A2"
    ws.protection.sheet = True
    ws.protection.formatColumns = False
    ws.protection.formatRows = False
    ws.protection.autoFilter = False
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{n}"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def read_xlsx(path: Path, required: list[str]) -> list[dict]:
    from openpyxl import load_workbook

    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise WorkflowError([f"cannot read spreadsheet: {type(exc).__name__}: {exc}"]) from exc
    ws = wb["work"] if "work" in wb.sheetnames else wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(it, [])]
    missing = [c for c in required if c not in header]
    if missing:
        raise WorkflowError([f"file is missing columns: {missing}"])

    def cell(v) -> str:
        if v is None:
            return ""
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        return str(v).strip()

    out = []
    for values in it:
        if values is None or all(v is None for v in values):
            continue
        out.append({h: cell(v) for h, v in zip(header, values, strict=False) if h})
    wb.close()
    return out


def read_table(path: Path, required: list[str]) -> list[dict]:
    return read_xlsx(path, required) if Path(path).suffix.lower() == ".xlsx" else read_csv(path, required)


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:  # BOM: opens correctly in Excel
        w = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)
    return path


# a lossy save turns every Urdu letter into '?': a word made only of '?' (2+), or U+FFFD.
# "kya??" (a Roman Urdu word with emphatic question marks) is not flagged.
_CORRUPT = re.compile(r"\ufffd|(?<![\w?])\?{2,}(?![\w?])")
_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")


def corrupt_text(text: str) -> bool:
    """Signs of a lossy save (e.g. Excel 'CSV' in a non-UTF-8 code page): replacement characters
    or words made only of '?' where Urdu letters were."""
    return bool(_CORRUPT.search(text or ""))


def read_csv(path: Path, required: list[str]) -> list[dict]:
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise WorkflowError([f"file is not UTF-8 ({exc.reason} at byte {exc.start}); in Excel use 'Save As > CSV UTF-8'"]) from exc
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
    for i, row in enumerate(read_table(path, BENIGN_COLUMNS), start=2):
        sid = row["scenario_id"]
        c = by_id.get(sid)
        where = f"line {i} ({sid})"
        if c is None:
            problems.append(f"{where}: unknown scenario_id")
            continue
        if sid in seen:
            problems.append(f"{where}: duplicate scenario_id")
        seen.add(sid)
        # recompute from the visible cells: catches edits to read-only cells, not just to the checksum
        if row["source_check"] != check(sid, c["harmful_en"]) or row["harmful_english"] != c["harmful_en"]:
            problems.append(f"{where}: harmful_english or scenario_id was edited (source_check mismatch)")
        if not row["benign_english"]:
            continue  # not written yet
        if corrupt_text(row["benign_english"]):
            problems.append(f"{where}: text looks corrupted by a non-UTF-8 save (contains '???' or U+FFFD)")
            continue
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
    for i, row in enumerate(read_table(path, BENIGN_REVIEW_COLUMNS), start=2):
        sid = row["scenario_id"]
        where = f"line {i} ({sid})"
        c, a = by_id.get(sid), authored.get(sid)
        if c is None or a is None:
            problems.append(f"{where}: unknown scenario or no authored contrast")
            continue
        if a["author_id"] == reviewer:
            problems.append(f"{where}: {reviewer} wrote this contrast and cannot review it")
            continue
        current = check(sid, c["harmful_en"], a["benign_en"])
        if row["source_check"] != current or check(sid, row["harmful_english"], row["benign_english"]) != current:
            problems.append(f"{where}: texts changed or were edited since export (source_check mismatch) - re-export the review sheet")
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
                "drafting_aid": "none" if r.locked_text else "",
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


def import_worksheet(path: Path, translator: str, rows: list[PlannedRow], *, previous: dict[str, dict]) -> ImportResult:
    """Validate a filled worksheet. Any problem refuses the whole import (fix and re-import);
    automated QC concerns are returned as warnings and recorded with the variant. `previous` (the
    current variants, `{}` if none) is required so a revision can never drop an earlier
    drafting-aid disclosure."""
    plan = {r.row_id: r for r in rows}
    problems, warnings, out, seen = [], [], [], set()
    filled = {}
    data = read_table(path, WORKSHEET_COLUMNS)
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
        visible = check(rid, row["english_source"], row["text"] if p.locked_text else "")
        if row["source_check"] != p.source_check or (visible != p.source_check and not p.locked_text):
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
        if corrupt_text(row["text"]):
            problems.append(f"{where}: text looks corrupted by a non-UTF-8 save (contains '???' or U+FFFD); save as 'CSV UTF-8'")
            continue
        if p.target_script in ("perso_arabic", "mixed") and not _ARABIC.search(row["text"]):
            problems.append(f"{where}: an Urdu-script row contains no Urdu letters (wrong form, or the file lost its encoding)")
            continue
        if row["drafting_aid"] not in DRAFTING_AIDS:
            problems.append(f"{where}: drafting_aid must be one of {DRAFTING_AIDS} (say if a tool drafted this)")
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
        # a revision never loses an earlier tool-drafting disclosure (protocol §6 step 2)
        aid, inherited = row["drafting_aid"], None
        prev = (previous or {}).get(rid)
        if prev and prev.get("drafting_aid") not in (None, "none") and aid == "none":
            aid, inherited = prev["drafting_aid"], prev.get("author_id")
        out.append(
            {
                "row_id": rid,
                "status": "done",
                "text": row["text"],
                "text_sha256": sha(row["text"]),
                "english_sha256": sha(p.english_source),
                "author_id": translator,
                "drafting_aid": aid,
                "drafting_aid_inherited_from": inherited,
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
    return {
        r.row_id: {
            "row_id": r.row_id,
            "text": r.locked_text,
            "text_sha256": sha(r.locked_text),
            "english_sha256": sha(r.english_source),
            "author_id": V01_AUTHOR,
            "drafting_aid": "none",
        }
        for r in rows
        if r.locked_text
    }


def current_variants(rows: list[PlannedRow], imported: dict[str, dict]) -> dict[str, dict]:
    """Imported variants that still match their row's English source, with the locked v0.1 rows
    always winning over any imported file. Variants of an edited source are stale and dropped."""
    plan = {r.row_id: r for r in rows}
    out = {
        rid: v
        for rid, v in imported.items()
        if rid in plan and not plan[rid].locked_text and v.get("english_sha256", sha(plan[rid].english_source)) == sha(plan[rid].english_source)
    }
    out.update(locked_variants(rows))
    return out


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
    for i, row in enumerate(read_table(path, REVIEW_COLUMNS), start=2):
        rid = row["row_id"]
        where = f"line {i} ({rid})"
        p, v = plan.get(rid), variants.get(rid)
        if p is None or v is None:
            problems.append(f"{where}: unknown row or no imported variant")
            continue
        if v["author_id"] == reviewer:
            problems.append(f"{where}: {reviewer} wrote this variant and cannot review it")
            continue
        current = check(rid, p.english_source, v["text"])
        if row["source_check"] != current or check(rid, row["english_source"], row["text"]) != current:
            problems.append(f"{where}: the variant changed since this sheet was exported, or a read-only cell was edited - re-export")
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
                "english_sha256": sha(p.english_source),
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


def import_adjudication(path: Path, adjudicator: str, rows: list[PlannedRow], variants: dict[str, dict], registry: dict, ratings: list[dict]) -> list[dict]:
    """`ratings` (all existing ratings) is required: the adjudicator must not have rated the row."""
    _check_registered(adjudicator, registry)
    rated_by_adjudicator = {
        r["record_id"] for r in ratings if r["annotator_id"] == adjudicator and r.get("text_sha256") == variants.get(r["record_id"], {}).get("text_sha256")
    }
    plan = {r.row_id: r for r in rows}
    problems, out = [], []
    for i, row in enumerate(read_table(path, ADJUDICATION_COLUMNS), start=2):
        rid = row["row_id"]
        where = f"line {i} ({rid})"
        p, v = plan.get(rid), variants.get(rid)
        if p is None or v is None:
            problems.append(f"{where}: unknown row")
            continue
        if v["author_id"] == adjudicator:
            problems.append(f"{where}: {adjudicator} wrote this variant and cannot adjudicate it")
            continue
        if rid in rated_by_adjudicator:
            problems.append(f"{where}: {adjudicator} already reviewed this variant; the adjudicator must be a third person")
            continue
        current = check(rid, p.english_source, v["text"])
        if row["source_check"] != current or check(rid, row["english_source"], row["text"]) != current:
            problems.append(f"{where}: the variant changed since export, or a read-only cell was edited - re-export")
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
                "english_sha256": sha(p.english_source),
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
