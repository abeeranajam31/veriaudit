"""Loads the VERIAUDIT pilot dataset from dataset/examples/*.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

from app.models.schemas import TestCase, Variant, VerificationStatus

DEFAULT_DATASET_PATH = Path(__file__).resolve().parents[3] / "dataset" / "examples" / "veriaudit-pilot.jsonl"


def load_dataset(path: Path | None = None) -> list[TestCase]:
    dataset_path = path or DEFAULT_DATASET_PATH
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    cases: list[TestCase] = []
    with dataset_path.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {dataset_path}") from exc
            cases.append(_record_to_test_case(record))
    return cases


def _record_to_test_case(record: dict) -> TestCase:
    similarity = record.get("semantic_similarity", {})
    variants = [
        Variant(form="english", text=record["english"], similarity=1.0, verification_status="verified"),
        Variant(
            form="urdu",
            text=record["urdu"],
            similarity=similarity.get("english_urdu"),
            verification_status=record.get("verification_status", VerificationStatus.pending),
        ),
        Variant(
            form="roman_urdu",
            text=record["roman_urdu"],
            similarity=similarity.get("english_roman_urdu"),
            verification_status=record.get("verification_status", VerificationStatus.pending),
        ),
        Variant(
            form="code_switched",
            text=record["code_switched"],
            similarity=similarity.get("english_code_switched"),
            verification_status=record.get("verification_status", VerificationStatus.pending),
        ),
    ]
    return TestCase(
        id=record["id"],
        intent_category=record["intent_category"],
        intent=record["intent"],
        variants=variants,
    )
