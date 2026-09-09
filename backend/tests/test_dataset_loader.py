import json

import pytest

from app.utils.dataset_loader import load_dataset


def test_load_dataset_default_path_has_entries():
    cases = load_dataset()
    assert len(cases) >= 10
    assert all(len(c.variants) == 4 for c in cases)
    assert all(c.id.startswith("VA-") for c in cases)


def test_load_dataset_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "does-not-exist.jsonl")


def test_load_dataset_invalid_json_raises(tmp_path):
    bad_file = tmp_path / "bad.jsonl"
    bad_file.write_text("{not valid json}\n")
    with pytest.raises(ValueError):
        load_dataset(bad_file)


def test_load_dataset_parses_all_four_languages(tmp_path):
    record = {
        "id": "VA-TEST",
        "intent_category": "Test",
        "intent": "Test intent",
        "english": "hello",
        "urdu": "ہیلو",
        "roman_urdu": "hello",
        "code_switched": "hello",
        "verification_status": "verified",
        "semantic_similarity": {
            "english_urdu": 0.9,
            "english_roman_urdu": 0.95,
            "english_code_switched": 0.92,
        },
    }
    dataset_file = tmp_path / "sample.jsonl"
    dataset_file.write_text(json.dumps(record) + "\n")

    cases = load_dataset(dataset_file)
    assert len(cases) == 1
    forms = {v.form.value for v in cases[0].variants}
    assert forms == {"english", "urdu", "roman_urdu", "code_switched"}
