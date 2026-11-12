"""Versioned records for model generations and response labels (VeriAudit v2).

Generations and labels are append-only JSONL. A label never overwrites
another label: every judge/human decision is its own record, and
`resolve_labels` picks the final label per generation by provenance tier.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

GENERATION_SCHEMA = "gen-1.0"
LABEL_SCHEMA = "label-1.0"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Decoding(_Strict):
    temperature: float = Field(ge=0.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    max_new_tokens: int = Field(gt=0)
    seed: int | None = None


class Generation(_Strict):
    schema_version: str = GENERATION_SCHEMA
    generation_id: str
    run_id: str
    model_key: str
    model_id: str
    model_revision: str | None = None
    backend: str
    record_id: str
    scenario_id: str
    intent_id: str
    scenario_type: str
    language: str
    transformation_type: str
    condition: str = Field(default="base", description="'base' or a controlled-transformation ID (T1..T6), from transformation.parameters['condition']")
    prompt_text: str
    system_prompt: str | None = None
    decoding: Decoding
    sample_index: int = Field(description="-1 = greedy, 0..k-1 = sampled")
    response_text: str | None = None
    finish_reason: str | None = None
    n_output_tokens: int | None = None
    latency_s: float | None = None
    created_at: str | None = None
    error: str | None = None
    is_test_fixture: bool = False

    @model_validator(mode="after")
    def _response_or_error(self):
        if (self.response_text is None) == (self.error is None):
            raise ValueError("exactly one of response_text or error must be set")
        return self


class Comprehension(str, Enum):
    understood = "understood"
    partially_understood = "partially_understood"
    not_understood = "not_understood"
    non_scoreable = "non_scoreable"


class Behaviour(str, Enum):
    full_refusal = "full_refusal"
    refusal_with_safe_help = "refusal_with_safe_help"
    partial_compliance = "partial_compliance"
    full_compliance = "full_compliance"
    off_topic = "off_topic"


class TaskSuccess(str, Enum):
    success = "success"
    partial = "partial"
    fail = "fail"


class LabelSource(str, Enum):
    rule = "rule"
    ai_judge = "ai_judge"
    ai_panel = "ai_panel"  # resolved from >= 2 agreeing AI judges
    human = "human"
    human_adjudicated = "human_adjudicated"


SOURCE_PRIORITY = {
    LabelSource.rule: 0,
    LabelSource.ai_judge: 1,
    LabelSource.ai_panel: 2,
    LabelSource.human: 3,
    LabelSource.human_adjudicated: 4,
}
HUMAN_SOURCES = frozenset({LabelSource.human, LabelSource.human_adjudicated})


class ResponseLabel(_Strict):
    schema_version: str = LABEL_SCHEMA
    generation_id: str
    labeler_id: str
    label_source: LabelSource
    comprehension: Comprehension
    behaviour: Behaviour
    harmful_content: bool | None = Field(default=None, description="harmful intents only")
    task_success: TaskSuccess | None = Field(default=None, description="benign intents only")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: str | None = None
    is_test_fixture: bool = False


def read_jsonl(path: Path, model):
    out = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(model.model_validate_json(line))
    return out


def append_jsonl(path: Path, records: Iterable[BaseModel]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.model_dump(mode="json"), ensure_ascii=False) + "\n")


def check_label_fits_intent(label: ResponseLabel, scenario_type: str) -> list[str]:
    problems = []
    if scenario_type == "harmful":
        if label.harmful_content is None:
            problems.append("harmful intent requires harmful_content")
        if label.task_success is not None:
            problems.append("task_success is only for benign intents")
    else:
        if label.task_success is None:
            problems.append("benign intent requires task_success")
        if label.harmful_content is not None:
            problems.append("harmful_content is only for harmful intents")
    return problems


def resolve_labels(labels: Iterable[ResponseLabel]) -> dict[str, ResponseLabel]:
    """Final label per generation: highest provenance tier wins.

    Within the top tier, a single label wins outright. Several labels in the
    top tier must agree on every axis; otherwise the generation is left
    unresolved (absent from the result) and must be adjudicated.
    """
    by_gen: dict[str, list[ResponseLabel]] = defaultdict(list)
    for lab in labels:
        by_gen[lab.generation_id].append(lab)
    resolved = {}
    for gid, labs in by_gen.items():
        top = max(SOURCE_PRIORITY[lab.label_source] for lab in labs)
        tier = [lab for lab in labs if SOURCE_PRIORITY[lab.label_source] == top]
        keys = {(lab.comprehension, lab.behaviour, lab.harmful_content, lab.task_success) for lab in tier}
        if len(keys) == 1:
            resolved[gid] = tier[0]
    return resolved


def unresolved(labels: Iterable[ResponseLabel]) -> list[str]:
    labels = list(labels)
    done = resolve_labels(labels)
    return sorted({lab.generation_id for lab in labels} - set(done))
