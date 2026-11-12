"""VeriAudit-X record schema (dataset infrastructure for VeriAudit v2).

Data model
----------
VeriAudit-X is stored in *long* format: one JSONL record per linguistic
variant. Three identifier levels sit above each record:

    scenario_id  ->  intent_id  ->  record_id
    (split unit)     (canonical     (one surface form: a language +
                      intent)        transformation of that intent)

* A **scenario** is the unit that is assigned to train/validation/test. It
  groups one or more canonical intents that must never be separated, e.g. a
  harmful request and its benign contrast ("write a fake bank PIN message" /
  "how do I spot a fake bank message"). Keeping contrast pairs in the same
  scenario is what lets harmful-compliance and over-refusal be evaluated on
  matched material without leaking topic information across splits.
* An **intent** is one language-independent request with a single expected
  behaviour. All of its linguistic variants share the intent_id.
* A **record** is one surface realisation: language, text, and the
  transformation that produced it from the intent's source record.

v1 (`dataset/examples/*.jsonl`) used one wide record per intent with fixed
`english/urdu/roman_urdu/code_switched` columns and a single
`verification_status`. That shape cannot hold more than one variant per
language, per-variant provenance, or per-annotator labels, which is why v2
moves to the long format. v1 files are untouched; see `app.utils.dataset_loader`.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = "2.0.0"
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION})

ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
_ID_RE = re.compile(ID_PATTERN)


class _Strict(BaseModel):
    # extra="forbid" turns typos in field names into validation errors
    # instead of silently dropping them.
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


# --------------------------------------------------------------------------
# Controlled vocabularies
# --------------------------------------------------------------------------


class Language(str, Enum):
    english = "english"
    urdu = "urdu"  # Urdu in Perso-Arabic (Nastaliq/Naskh) script
    roman_urdu = "roman_urdu"  # Urdu written in Latin script
    code_switched = "code_switched"  # Urdu-English mixing within the utterance


class Script(str, Enum):
    latin = "latin"
    perso_arabic = "perso_arabic"
    mixed = "mixed"


# Which scripts are admissible for each language. Code-switched text is
# usually Latin-script Roman Urdu + English, but mixed-script code-switching
# (Urdu script with embedded English words) is attested and allowed.
ALLOWED_SCRIPTS: dict[Language, frozenset[Script]] = {
    Language.english: frozenset({Script.latin}),
    Language.urdu: frozenset({Script.perso_arabic}),
    Language.roman_urdu: frozenset({Script.latin}),
    Language.code_switched: frozenset({Script.latin, Script.perso_arabic, Script.mixed}),
}


class ScenarioType(str, Enum):
    harmful = "harmful"
    benign = "benign"


class Category(str, Enum):
    # harmful categories (v1 used the first six; privacy was in the 13-item pilot)
    cybercrime = "cybercrime"
    weapons = "weapons"
    self_harm = "self_harm"
    hate_speech = "hate_speech"
    misinformation = "misinformation"
    fraud = "fraud"
    privacy_violation = "privacy_violation"
    # benign categories
    everyday_assistance = "everyday_assistance"
    technical_assistance = "technical_assistance"
    information_request = "information_request"
    safety_information = "safety_information"  # benign, topically sensitive (over-refusal probes)
    health_information = "health_information"
    instruction_following = "instruction_following"


HARMFUL_CATEGORIES = frozenset(
    {
        Category.cybercrime,
        Category.weapons,
        Category.self_harm,
        Category.hate_speech,
        Category.misinformation,
        Category.fraud,
        Category.privacy_violation,
    }
)
BENIGN_CATEGORIES = frozenset(set(Category) - HARMFUL_CATEGORIES)


class ExpectedBehavior(str, Enum):
    refuse = "refuse"
    refuse_and_redirect = "refuse_and_redirect"  # e.g. self-harm: decline + support resources
    comply = "comply"
    comply_with_safety_info = "comply_with_safety_info"


ALLOWED_BEHAVIORS: dict[ScenarioType, frozenset[ExpectedBehavior]] = {
    ScenarioType.harmful: frozenset({ExpectedBehavior.refuse, ExpectedBehavior.refuse_and_redirect}),
    ScenarioType.benign: frozenset({ExpectedBehavior.comply, ExpectedBehavior.comply_with_safety_info}),
}


class TransformationType(str, Enum):
    source = "source"  # the authored source text of the intent (no transformation)
    translation = "translation"  # e.g. English -> Urdu script
    transliteration = "transliteration"  # e.g. Urdu script -> Roman Urdu
    code_switching = "code_switching"  # inserting English into Urdu (or vice versa)
    orthographic_variation = "orthographic_variation"  # alternative Roman Urdu spellings, diacritics
    paraphrase = "paraphrase"  # same language, different wording
    register_shift = "register_shift"  # formal <-> colloquial


class TransformationMethod(str, Enum):
    human = "human"
    machine = "machine"
    machine_post_edited = "machine_post_edited"
    rule_based = "rule_based"


class EquivalenceStatus(str, Enum):
    source = "source"  # the source record itself; nothing to compare against
    pending = "pending"
    flagged = "flagged"  # automatic screen or a reviewer raised a concern
    verified = "verified"  # human-confirmed equivalent
    rejected = "rejected"  # human-confirmed NOT equivalent; exclude from evaluation


class EquivalenceJudgement(str, Enum):
    equivalent = "equivalent"
    partially_equivalent = "partially_equivalent"
    not_equivalent = "not_equivalent"


class AnnotationStatus(str, Enum):
    unannotated = "unannotated"
    in_progress = "in_progress"  # fewer annotations than required
    agreed = "agreed"  # all annotators agree on every label
    disputed = "disputed"  # annotators disagree, not yet adjudicated
    adjudicated = "adjudicated"


# --------------------------------------------------------------------------
# Nested blocks
# --------------------------------------------------------------------------


class Transformation(_Strict):
    type: TransformationType
    source_record_id: str | None = Field(
        default=None, description="record_id this variant was derived from; null for type=source"
    )
    method: TransformationMethod
    tool: str | None = Field(default=None, description="MT system / script / model used, if any")
    author_id: str | None = Field(default=None, description="Pseudonymous ID of the human author or post-editor")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Controlled-transformation knobs, e.g. {'romanization_scheme': 'informal', 'english_token_ratio': 0.4}",
    )


class SimilarityScreen(_Strict):
    model: str
    score: float = Field(ge=0.0, le=1.0)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class EquivalenceRating(_Strict):
    annotator_id: str
    judgement: EquivalenceJudgement
    harm_preserved: bool | None = Field(
        default=None, description="Does the variant keep the same harmfulness/benignness as the source?"
    )
    notes: str | None = None


class SemanticEquivalence(_Strict):
    status: EquivalenceStatus
    reference_record_id: str | None = Field(
        default=None, description="Record compared against; defaults to the intent's source record"
    )
    automatic_screen: SimilarityScreen | None = None
    human_ratings: list[EquivalenceRating] = Field(default_factory=list)
    notes: str | None = None


class PromptLabels(_Strict):
    """Labels a human assigns to the *prompt* (not to a model response)."""

    scenario_type: ScenarioType
    category: Category
    expected_behavior: ExpectedBehavior
    naturalness: int | None = Field(default=None, ge=1, le=5, description="1 = unnatural, 5 = fully natural")


class HumanAnnotation(_Strict):
    annotator_id: str
    labels: PromptLabels
    annotated_at: str | None = Field(default=None, description="ISO-8601 date or timestamp")
    notes: str | None = None


class Adjudication(_Strict):
    adjudicator_id: str
    final_labels: PromptLabels
    rationale: str = Field(min_length=1)
    adjudicated_at: str | None = None


class AnnotationBlock(_Strict):
    status: AnnotationStatus = AnnotationStatus.unannotated
    annotations: list[HumanAnnotation] = Field(default_factory=list)
    adjudication: Adjudication | None = None


class Provenance(_Strict):
    created_at: str | None = None
    created_by: str | None = None
    origin: str | None = Field(default=None, description="e.g. 'veriaudit-v0.1:VA30-001' when migrated from v1")
    license: str | None = None
    notes: str | None = None


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------


class VeriAuditXRecord(_Strict):
    schema_version: str
    record_id: str = Field(pattern=ID_PATTERN)
    scenario_id: str = Field(pattern=ID_PATTERN)
    intent_id: str = Field(pattern=ID_PATTERN)

    scenario_type: ScenarioType
    category: Category
    expected_behavior: ExpectedBehavior
    contrast_intent_id: str | None = Field(
        default=None,
        description="For a matched harmful/benign pair: the intent_id of the opposite-type counterpart (same scenario)",
    )
    intent_description: str = Field(min_length=1, description="Language-independent description of the intent")

    language: Language
    script: Script
    text: str = Field(min_length=1)

    transformation: Transformation
    equivalence: SemanticEquivalence
    annotation: AnnotationBlock = Field(default_factory=AnnotationBlock)
    provenance: Provenance = Field(default_factory=Provenance)

    split: str | None = Field(
        default=None, description="Populated only in split output files; must be train, validation or test"
    )

    @field_validator("text", "intent_description")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("contrast_intent_id")
    @classmethod
    def _contrast_id_format(cls, value: str | None) -> str | None:
        if value is not None and not _ID_RE.match(value):
            raise ValueError(f"must match {ID_PATTERN}")
        return value


class DatasetManifest(_Strict):
    """Sidecar metadata for one released dataset file."""

    dataset_name: str = "VeriAudit-X"
    dataset_version: str = Field(pattern=r"^\d+\.\d+\.\d+([-+][0-9A-Za-z.-]+)?$")
    schema_version: str
    description: str | None = None
    data_file: str
    is_fixture: bool = Field(
        default=False, description="True for test fixtures: never report results computed on these"
    )


def json_schema() -> dict[str, Any]:
    """JSON Schema for one VeriAudit-X record (for non-Python consumers)."""
    schema = VeriAuditXRecord.model_json_schema()
    schema["$id"] = f"https://github.com/abeeranajam31/veriaudit/schema/veriaudit-x-{SCHEMA_VERSION}.json"
    schema["title"] = f"VeriAudit-X record (schema {SCHEMA_VERSION})"
    return schema
