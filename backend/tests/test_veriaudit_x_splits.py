import json
from collections import Counter

import pytest
from veriaudit_x_helpers import FIXTURE_FILE, by_id, make_intent, synthetic_dataset

from app.veriaudit_x.cli import main as cli_main
from app.veriaudit_x.splits import (
    SplitLeakageError,
    assign_splits,
    check_leakage,
    scenario_groups,
    write_splits,
)
from app.veriaudit_x.validation import validate_file, validate_objects


def records(objs):
    report = validate_objects(objs)
    assert report.ok, report.summary()
    return report.records


def test_every_record_of_a_scenario_shares_a_split():
    recs = records(synthetic_dataset(60))
    splits = assign_splits(recs, seed=1).apply(recs)
    seen = {}
    for split, rs in splits.items():
        for r in rs:
            assert seen.setdefault(r.scenario_id, split) == split
    assert check_leakage(splits) == []


def test_variants_and_contrast_pairs_stay_together():
    recs = records(synthetic_dataset(60))
    result = assign_splits(recs, seed=2)
    by_intent = {}
    for r in recs:
        by_intent.setdefault(r.intent_id, set()).add(result.split_of(r))
    assert all(len(s) == 1 for s in by_intent.values())
    for i in range(60):
        assert by_intent[f"SYN-{i:04d}-H"] == by_intent[f"SYN-{i:04d}-B"]


def test_ratios_are_respected_in_scenarios():
    recs = records(synthetic_dataset(100))
    result = assign_splits(recs, seed=3, ratios=(0.7, 0.15, 0.15))
    counts = Counter(result.assignment.values())
    assert counts == {"train": 70, "validation": 15, "test": 15}


def test_strata_are_spread_across_splits():
    recs = records(synthetic_dataset(120))  # 20 scenarios per harm category
    result = assign_splits(recs, seed=4)
    per_cat = Counter()
    for r in recs:
        if r.scenario_type.value == "harmful" and r.language.value == "english":
            per_cat[(r.category.value, result.split_of(r))] += 1
    for cat in {c for c, _ in per_cat}:
        assert per_cat[(cat, "test")] >= 1 and per_cat[(cat, "validation")] >= 1


def test_split_is_deterministic_and_seed_dependent():
    recs = records(synthetic_dataset(50))
    a = assign_splits(recs, seed=7).assignment
    assert a == assign_splits(list(reversed(recs)), seed=7).assignment  # input order irrelevant
    assert a != assign_splits(recs, seed=8).assignment


def test_identical_text_across_scenarios_is_grouped():
    objs = synthetic_dataset(30)
    # scenario 5's Urdu text accidentally duplicates scenario 17's
    dup_text = by_id(objs, "SYN-0017-H-ur-01")["text"]
    by_id(objs, "SYN-0005-H-ur-01")["text"] = dup_text + "۔"
    recs = records(objs)
    assert ["SYN-0005", "SYN-0017"] in scenario_groups(recs)
    result = assign_splits(recs, seed=11)
    assert result.assignment["SYN-0005"] == result.assignment["SYN-0017"]
    assert check_leakage(result.apply(recs)) == []


def test_cross_scenario_reference_is_grouped_even_though_invalid():
    objs = synthetic_dataset(10)
    by_id(objs, "SYN-0003-H-ur-01")["transformation"]["source_record_id"] = "SYN-0008-H-en-01"
    report = validate_objects(objs)
    assert report.codes()["cross_intent_reference"] == 1  # validator objects...
    assert ["SYN-0003", "SYN-0008"] in scenario_groups(report.records)  # ...and splitting stays safe


def test_check_leakage_detects_manual_leak():
    recs = records(synthetic_dataset(10))
    splits = assign_splits(recs, seed=5).apply(recs)
    moved = splits["train"].pop()
    splits["test"].append(moved)
    issues = check_leakage(splits)
    kinds = {i.field for i in issues if i.field}
    assert {"scenario_id", "intent_id"} <= kinds


def test_leakage_error_carries_issues():
    err = SplitLeakageError([])
    assert err.issues == []


@pytest.mark.parametrize("ratios", [(0.5, 0.5, 0.5), (1.2, -0.1, -0.1), (0.5, 0.5)])
def test_bad_ratios(ratios):
    with pytest.raises(ValueError):
        assign_splits(records(synthetic_dataset(5)), ratios=ratios)


def test_zero_ratio_split_stays_empty():
    recs = records(synthetic_dataset(20))
    counts = Counter(assign_splits(recs, ratios=(0.8, 0.2, 0.0)).assignment.values())
    assert counts["test"] == 0 and counts["train"] == 16


def test_empty_dataset():
    with pytest.raises(ValueError):
        assign_splits([])


def test_write_splits_outputs_valid_files_and_manifest(tmp_path):
    recs = records(synthetic_dataset(40) + make_intent("SOLO-1", "B", "benign", "everyday_assistance"))
    manifest = write_splits(recs, tmp_path, seed=9, dataset_version="0.0.1-test")
    total = 0
    split_files = {}
    for split in ("train", "validation", "test"):
        report = validate_file(tmp_path / f"{split}.jsonl")
        assert report.ok, report.summary()
        assert {r.split for r in report.records} <= {split}
        split_files[split] = report.records
        total += len(report.records)
    assert total == len(recs)
    assert check_leakage(split_files) == []
    on_disk = json.loads((tmp_path / "split_manifest.json").read_text())
    assert on_disk == manifest
    assert manifest["seed"] == 9 and manifest["dataset_version"] == "0.0.1-test"
    assert sum(s["records"] for s in manifest["statistics"].values()) == len(recs)


def test_cli_validate_and_split_on_fixture(tmp_path, capsys):
    assert cli_main(["validate", str(FIXTURE_FILE)]) == 0
    assert cli_main(["split", str(FIXTURE_FILE), "--out", str(tmp_path), "--seed", "13"]) == 0
    manifest = json.loads((tmp_path / "split_manifest.json").read_text())
    assert len(manifest["assignment"]) == 4
    assert manifest["source_sha256"]


def test_cli_split_refuses_invalid_file(tmp_path):
    bad = tmp_path / "bad.jsonl"
    lines = FIXTURE_FILE.read_text(encoding="utf-8").splitlines()
    bad.write_text("\n".join(lines + [lines[0]]) + "\n", encoding="utf-8")  # duplicate record_id
    assert cli_main(["validate", str(bad)]) == 1
    assert cli_main(["split", str(bad), "--out", str(tmp_path / "out")]) == 1
    assert not (tmp_path / "out").exists()
