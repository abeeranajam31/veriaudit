"""Shared helpers for the VeriAudit-X tests (not collected as tests)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "dataset" / "veriaudit-x" / "fixtures"
FIXTURE_FILE = FIXTURE_DIR / "sample_valid.jsonl"
SCHEMA_FILE = REPO_ROOT / "dataset" / "veriaudit-x" / "schema" / "veriaudit-x-2.1.0.schema.json"

LANGS = [
    ("english", "en", "latin", "source", None),
    ("urdu", "ur", "perso_arabic", "translation", "en"),
    ("roman_urdu", "rur", "latin", "transliteration", "ur"),
    ("code_switched", "cs", "latin", "code_switching", "en"),
]

HARM_CATS = ["cybercrime", "weapons", "self_harm", "hate_speech", "misinformation", "fraud"]


def load_fixture() -> list[dict]:
    return [json.loads(line) for line in FIXTURE_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]


def by_id(records: list[dict], record_id: str) -> dict:
    return next(r for r in records if r["record_id"] == record_id)


def make_intent(scenario_id: str, suffix: str, scenario_type: str, category: str, contrast: str | None = None) -> list[dict]:
    behavior = "refuse" if scenario_type == "harmful" else "comply"
    intent_id = f"{scenario_id}-{suffix}"
    out = []
    for lang, code, script, ttype, parent in LANGS:
        out.append(
            {
                "schema_version": "2.1.0",
                "record_id": f"{intent_id}-{code}-01",
                "scenario_id": scenario_id,
                "intent_id": intent_id,
                "scenario_type": scenario_type,
                "category": category,
                "expected_behavior": behavior,
                "contrast_intent_id": f"{scenario_id}-{contrast}" if contrast else None,
                "intent_description": f"synthetic intent {intent_id}",
                "language": lang,
                "script": script,
                "text": f"synthetic {lang} text for {intent_id}",
                "transformation": {
                    "type": ttype,
                    "source_record_id": f"{intent_id}-{parent}-01" if parent else None,
                    "method": "human",
                },
                "equivalence": {"status": "source" if ttype == "source" else "pending"},
            }
        )
    return out


def synthetic_dataset(n_scenarios: int = 40, with_contrast: bool = True) -> list[dict]:
    """n scenarios, each a harmful intent (+ benign contrast), 4 variants per intent."""
    records: list[dict] = []
    for i in range(n_scenarios):
        sid = f"SYN-{i:04d}"
        cat = HARM_CATS[i % len(HARM_CATS)]
        if with_contrast:
            records += make_intent(sid, "H", "harmful", cat, contrast="B")
            records += make_intent(sid, "B", "benign", "safety_information", contrast="H")
        else:
            records += make_intent(sid, "H", "harmful", cat)
    return records


def mutated(records: list[dict], _target_id: str, /, **changes) -> list[dict]:
    out = copy.deepcopy(records)
    target = by_id(out, _target_id)
    for dotted, value in changes.items():
        keys = dotted.split("__")
        node = target
        for k in keys[:-1]:
            node = node[k]
        if value is _DELETE:
            del node[keys[-1]]
        else:
            node[keys[-1]] = value
    return out


class _Delete:
    pass


_DELETE = _Delete()
DELETE = _DELETE
