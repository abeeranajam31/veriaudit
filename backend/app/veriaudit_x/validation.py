"""Loading and validation for VeriAudit-X JSONL files.

Validation never stops at the first problem: every record is checked and all
issues are collected into a ValidationReport, each with the line number and
record_id so annotators can fix a file in one pass.

Severity
    error   - the file must not be used for splits or evaluation
    warning - legal but suspicious; review before release
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from app.veriaudit_x.normalize import normalize_text
from app.veriaudit_x.schema import (
    ALLOWED_BEHAVIORS,
    ALLOWED_SCRIPTS,
    BENIGN_CATEGORIES,
    HARMFUL_CATEGORIES,
    SUPPORTED_SCHEMA_VERSIONS,
    AnnotationStatus,
    EquivalenceJudgement,
    EquivalenceStatus,
    Language,
    PromptLabels,
    ScenarioType,
    TransformationMethod,
    TransformationType,
    VeriAuditXRecord,
)

VALID_SPLITS = ("train", "validation", "test")

# pydantic error type -> stable issue code
_PYDANTIC_CODE = {
    "missing": "missing_field",
    "enum": "invalid_label",
    "literal_error": "invalid_label",
    "extra_forbidden": "unknown_field",
}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str  # "error" | "warning"
    code: str
    message: str
    line: int | None = None
    record_id: str | None = None
    field: str | None = None

    def format(self) -> str:
        where = []
        if self.line is not None:
            where.append(f"line {self.line}")
        if self.record_id:
            where.append(self.record_id)
        if self.field:
            where.append(self.field)
        loc = f" [{', '.join(where)}]" if where else ""
        return f"{self.severity.upper()} {self.code}{loc}: {self.message}"


@dataclass
class ValidationConfig:
    min_equivalence_raters: int = 2
    min_annotators: int = 2
    require_all_languages: bool = True
    required_languages: tuple[Language, ...] = tuple(Language)


@dataclass
class ValidationReport:
    records: list[VeriAuditXRecord] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def codes(self) -> Counter:
        return Counter(i.code for i in self.issues)

    def summary(self) -> str:
        lines = [f"{len(self.records)} valid records, {len(self.errors)} errors, {len(self.warnings)} warnings"]
        lines += [i.format() for i in self.issues]
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[tuple[int, dict | None, str | None]]:
    """Return (line_number, parsed_object_or_None, parse_error_or_None) per non-blank line."""
    rows: list[tuple[int, dict | None, str | None]] = []
    with Path(path).open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                rows.append((line_number, None, f"invalid JSON: {exc.msg}"))
                continue
            if not isinstance(obj, dict):
                rows.append((line_number, None, "line is not a JSON object"))
                continue
            rows.append((line_number, obj, None))
    return rows


def validate_file(path: Path, config: ValidationConfig | None = None) -> ValidationReport:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    return validate_rows(read_jsonl(path), config)


def validate_objects(objects: Iterable[dict], config: ValidationConfig | None = None) -> ValidationReport:
    """Validate in-memory dicts (line numbers are 1-based positions)."""
    return validate_rows([(i, o, None) for i, o in enumerate(objects, start=1)], config)


def validate_rows(rows: list[tuple[int, dict | None, str | None]], config: ValidationConfig | None = None) -> ValidationReport:
    config = config or ValidationConfig()
    report = ValidationReport()
    line_of: dict[str, int] = {}

    for line, obj, parse_error in rows:
        if parse_error is not None:
            report.issues.append(ValidationIssue("error", "invalid_json", parse_error, line=line))
            continue
        assert obj is not None
        rid = obj.get("record_id") if isinstance(obj.get("record_id"), str) else None

        version = obj.get("schema_version")
        if version is not None and version not in SUPPORTED_SCHEMA_VERSIONS:
            report.issues.append(
                ValidationIssue(
                    "error",
                    "unsupported_schema_version",
                    f"schema_version {version!r} not in {sorted(SUPPORTED_SCHEMA_VERSIONS)}",
                    line=line,
                    record_id=rid,
                    field="schema_version",
                )
            )
            continue

        try:
            record = VeriAuditXRecord.model_validate(obj)
        except ValidationError as exc:
            for err in exc.errors():
                report.issues.append(
                    ValidationIssue(
                        "error",
                        _PYDANTIC_CODE.get(err["type"], "invalid_value"),
                        err["msg"],
                        line=line,
                        record_id=rid,
                        field=".".join(str(p) for p in err["loc"]),
                    )
                )
            continue

        if record.record_id in line_of:
            report.issues.append(
                ValidationIssue(
                    "error",
                    "duplicate_record_id",
                    f"record_id already used on line {line_of[record.record_id]}",
                    line=line,
                    record_id=record.record_id,
                    field="record_id",
                )
            )
            continue
        line_of[record.record_id] = line

        _check_record(record, line, report, config)
        report.records.append(record)

    _check_cross_record(report, line_of, config)
    return report


# --------------------------------------------------------------------------
# Per-record consistency
# --------------------------------------------------------------------------


def _err(report, code, msg, record, line, fld=None, severity="error"):
    report.issues.append(ValidationIssue(severity, code, msg, line=line, record_id=record.record_id, field=fld))


def _labels_consistent(labels: PromptLabels) -> str | None:
    if labels.scenario_type == ScenarioType.harmful and labels.category not in HARMFUL_CATEGORIES:
        return f"category {labels.category.value!r} is not a harmful category"
    if labels.scenario_type == ScenarioType.benign and labels.category not in BENIGN_CATEGORIES:
        return f"category {labels.category.value!r} is not a benign category"
    if labels.expected_behavior not in ALLOWED_BEHAVIORS[labels.scenario_type]:
        return f"expected_behavior {labels.expected_behavior.value!r} not allowed for {labels.scenario_type.value} scenarios"
    return None


def _check_record(r: VeriAuditXRecord, line: int, report: ValidationReport, config: ValidationConfig) -> None:
    gold = PromptLabels(scenario_type=r.scenario_type, category=r.category, expected_behavior=r.expected_behavior)
    problem = _labels_consistent(gold)
    if problem:
        _err(report, "inconsistent_label", problem, r, line, "category/expected_behavior")

    if r.script not in ALLOWED_SCRIPTS[r.language]:
        _err(report, "script_language_mismatch", f"script {r.script.value!r} invalid for language {r.language.value!r}", r, line, "script")

    if r.split is not None and r.split not in VALID_SPLITS:
        _err(report, "invalid_label", f"split must be one of {VALID_SPLITS}", r, line, "split")

    # transformation <-> equivalence
    t, eq = r.transformation, r.equivalence
    if t.type == TransformationType.source:
        if t.source_record_id is not None:
            _err(report, "invalid_transformation", "source records must not have source_record_id", r, line, "transformation.source_record_id")
        if eq.status != EquivalenceStatus.source:
            _err(report, "invalid_equivalence", "source records must have equivalence.status='source'", r, line, "equivalence.status")
    else:
        if t.source_record_id is None:
            _err(report, "invalid_transformation", f"{t.type.value} requires transformation.source_record_id", r, line, "transformation.source_record_id")
        elif t.source_record_id == r.record_id:
            _err(report, "invalid_transformation", "record cannot be derived from itself", r, line, "transformation.source_record_id")
        if eq.status == EquivalenceStatus.source:
            _err(report, "invalid_equivalence", "only type=source records may have equivalence.status='source'", r, line, "equivalence.status")

    # semantic-equivalence evidence
    raters = [h.annotator_id for h in eq.human_ratings]
    if len(raters) != len(set(raters)):
        _err(report, "duplicate_annotator", "an annotator rated equivalence more than once", r, line, "equivalence.human_ratings")
    if eq.status == EquivalenceStatus.verified:
        if len(eq.human_ratings) < config.min_equivalence_raters:
            _err(
                report,
                "unsupported_verification",
                f"status 'verified' requires >= {config.min_equivalence_raters} human ratings; similarity alone never verifies",
                r,
                line,
                "equivalence",
            )
        elif any(h.judgement != EquivalenceJudgement.equivalent for h in eq.human_ratings):
            _err(report, "unsupported_verification", "status 'verified' requires every human rating to be 'equivalent'", r, line, "equivalence")
        elif any(h.harm_preserved is False for h in eq.human_ratings):
            _err(report, "unsupported_verification", "a rater marked harm_preserved=false on a verified variant", r, line, "equivalence")
    if eq.status == EquivalenceStatus.rejected and not eq.human_ratings:
        _err(report, "unsupported_verification", "status 'rejected' requires at least one human rating", r, line, "equivalence")
    if eq.automatic_screen and eq.automatic_screen.threshold is not None:
        if eq.automatic_screen.score < eq.automatic_screen.threshold and eq.status == EquivalenceStatus.pending:
            _err(
                report,
                "screen_below_threshold",
                "similarity below threshold but status is 'pending' (expected 'flagged' or human-reviewed)",
                r,
                line,
                "equivalence.status",
                "warning",
            )

    # provenance tiers (quality block) must agree with the evidence actually present
    q = r.quality
    has_human = bool(eq.human_ratings) or bool(r.annotation.annotations)
    if q.human_reviewed != has_human:
        _err(
            report, "provenance_mismatch", "quality.human_reviewed must be true exactly when human ratings/annotations exist", r, line, "quality.human_reviewed"
        )
    if q.human_adjudicated != (r.annotation.adjudication is not None):
        _err(report, "provenance_mismatch", "quality.human_adjudicated must be true exactly when an adjudication exists", r, line, "quality.human_adjudicated")
    if q.ai_generated and t.method == TransformationMethod.human:
        _err(report, "provenance_mismatch", "ai_generated text cannot have transformation.method='human'", r, line, "quality.ai_generated")
    if q.ai_generated and not q.generator_id:
        _err(report, "provenance_mismatch", "ai_generated requires quality.generator_id", r, line, "quality.generator_id")
    failed = sorted(k for k, v in q.automated_checks.items() if not v.passed)
    if failed and eq.status == EquivalenceStatus.pending:
        _err(report, "failed_automated_check", f"automated checks failed: {', '.join(failed)}", r, line, "quality.automated_checks", "warning")

    # annotation / adjudication
    ann = r.annotation
    ids = [a.annotator_id for a in ann.annotations]
    if len(ids) != len(set(ids)):
        _err(report, "duplicate_annotator", "an annotator appears more than once", r, line, "annotation.annotations")
    for idx, a in enumerate(ann.annotations):
        problem = _labels_consistent(a.labels)
        if problem:
            _err(report, "inconsistent_label", problem, r, line, f"annotation.annotations.{idx}.labels")

    label_sets = {(a.labels.scenario_type, a.labels.category, a.labels.expected_behavior) for a in ann.annotations}
    disagree = len(label_sets) > 1
    st = ann.status
    if st == AnnotationStatus.unannotated and ann.annotations:
        _err(report, "annotation_status_mismatch", "status 'unannotated' but annotations are present", r, line, "annotation.status")
    if st in (AnnotationStatus.agreed, AnnotationStatus.disputed, AnnotationStatus.adjudicated) and len(ann.annotations) < config.min_annotators:
        _err(report, "annotation_status_mismatch", f"status {st.value!r} needs at least {config.min_annotators} annotations", r, line, "annotation.status")
    if st == AnnotationStatus.agreed and disagree:
        _err(report, "annotation_status_mismatch", "status 'agreed' but annotators disagree", r, line, "annotation.status")
    if st == AnnotationStatus.disputed and not disagree:
        _err(report, "annotation_status_mismatch", "status 'disputed' but all annotations agree", r, line, "annotation.status")
    if st == AnnotationStatus.adjudicated and ann.adjudication is None:
        _err(report, "missing_adjudication", "status 'adjudicated' requires an adjudication block", r, line, "annotation.adjudication")
    if ann.adjudication is not None:
        if st != AnnotationStatus.adjudicated:
            _err(report, "annotation_status_mismatch", "adjudication present but status is not 'adjudicated'", r, line, "annotation.status")
        problem = _labels_consistent(ann.adjudication.final_labels)
        if problem:
            _err(report, "inconsistent_label", problem, r, line, "annotation.adjudication.final_labels")
        if ann.adjudication.adjudicator_id in ids:
            _err(report, "adjudicator_not_independent", "adjudicator also annotated this record", r, line, "annotation.adjudication.adjudicator_id", "warning")

    # gold labels on the record must match the final human decision
    final = None
    if ann.adjudication is not None:
        final = ann.adjudication.final_labels
    elif st == AnnotationStatus.agreed and ann.annotations:
        final = ann.annotations[0].labels
    if final is not None and (final.scenario_type, final.category, final.expected_behavior) != (
        r.scenario_type,
        r.category,
        r.expected_behavior,
    ):
        _err(
            report,
            "gold_label_mismatch",
            "record-level labels differ from the agreed/adjudicated human labels",
            r,
            line,
            "scenario_type/category/expected_behavior",
        )


# --------------------------------------------------------------------------
# Cross-record consistency
# --------------------------------------------------------------------------


def _check_cross_record(report: ValidationReport, line_of: dict[str, int], config: ValidationConfig) -> None:
    by_id = {r.record_id: r for r in report.records}
    by_intent: dict[str, list[VeriAuditXRecord]] = defaultdict(list)
    for r in report.records:
        by_intent[r.intent_id].append(r)

    intent_scenario: dict[str, str] = {}
    intent_type: dict[str, ScenarioType] = {}

    for intent_id, recs in by_intent.items():
        first = recs[0]
        line = line_of[first.record_id]

        for field_name in ("scenario_id", "scenario_type", "category", "expected_behavior", "contrast_intent_id"):
            values = {getattr(r, field_name) for r in recs}
            if len(values) > 1:
                _err(report, "inconsistent_intent", f"intent {intent_id} has conflicting {field_name}: {sorted(map(str, values))}", first, line, field_name)
        intent_scenario[intent_id] = first.scenario_id
        intent_type[intent_id] = first.scenario_type

        sources = [r for r in recs if r.transformation.type == TransformationType.source]
        if len(sources) != 1:
            _err(report, "source_count", f"intent {intent_id} has {len(sources)} source records (expected exactly 1)", first, line, "transformation.type")

        if config.require_all_languages:
            missing = [lang.value for lang in config.required_languages if lang not in {r.language for r in recs}]
            if missing:
                _err(report, "missing_language", f"intent {intent_id} has no variant for: {', '.join(missing)}", first, line, "language", "warning")

        seen_text: dict[tuple[Language, str], str] = {}
        for r in recs:
            key = (r.language, normalize_text(r.text))
            if key in seen_text:
                _err(report, "duplicate_text", f"same normalised text as {seen_text[key]} within intent", r, line_of[r.record_id], "text", "warning")
            else:
                seen_text[key] = r.record_id

    for r in report.records:
        line = line_of[r.record_id]
        src = r.transformation.source_record_id
        if src is not None:
            parent = by_id.get(src)
            if parent is None:
                _err(report, "dangling_reference", f"source_record_id {src!r} does not exist", r, line, "transformation.source_record_id")
            elif parent.intent_id != r.intent_id:
                _err(
                    report,
                    "cross_intent_reference",
                    f"derived from {src!r}, which belongs to intent {parent.intent_id}",
                    r,
                    line,
                    "transformation.source_record_id",
                )
        ref = r.equivalence.reference_record_id
        if ref is not None:
            parent = by_id.get(ref)
            if parent is None:
                _err(report, "dangling_reference", f"reference_record_id {ref!r} does not exist", r, line, "equivalence.reference_record_id")
            elif parent.intent_id != r.intent_id:
                _err(
                    report,
                    "cross_intent_reference",
                    f"equivalence reference {ref!r} belongs to intent {parent.intent_id}",
                    r,
                    line,
                    "equivalence.reference_record_id",
                )

        c = r.contrast_intent_id
        if c is not None:
            if c == r.intent_id:
                _err(report, "invalid_contrast", "contrast_intent_id points at its own intent", r, line, "contrast_intent_id")
            elif c not in intent_scenario:
                _err(report, "dangling_reference", f"contrast_intent_id {c!r} does not exist", r, line, "contrast_intent_id")
            else:
                if intent_scenario[c] != r.scenario_id:
                    _err(
                        report,
                        "contrast_split_risk",
                        f"contrast intent {c} is in scenario {intent_scenario[c]}, not {r.scenario_id}; pairs must share a scenario",
                        r,
                        line,
                        "contrast_intent_id",
                    )
                if intent_type[c] == r.scenario_type:
                    _err(report, "invalid_contrast", "contrast intent must have the opposite scenario_type", r, line, "contrast_intent_id")

    # split field, when present, must be constant within a scenario
    split_by_scenario: dict[str, set[str | None]] = defaultdict(set)
    for r in report.records:
        split_by_scenario[r.scenario_id].add(r.split)
    for scenario_id, splits in split_by_scenario.items():
        if len(splits) > 1:
            rec = next(r for r in report.records if r.scenario_id == scenario_id)
            _err(
                report,
                "split_leakage",
                f"scenario {scenario_id} has records in several splits: {sorted(map(str, splits))}",
                rec,
                line_of[rec.record_id],
                "split",
            )
