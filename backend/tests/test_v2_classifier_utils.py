import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location("train_encoder", Path(__file__).resolve().parents[2] / "research/classifiers/train_encoder.py")
te = importlib.util.module_from_spec(spec)
spec.loader.exec_module(te)


def rows():
    out = []
    for i, split in enumerate(["train"] * 6 + ["validation"] * 2 + ["test"] * 2):
        for f in te.FORMS:
            out.append({"text": f"t{i}{f}", "label": i % 2, "form": f, "scenario_id": f"S{i}", "split": split})
    return out


def test_conditions_select_expected_forms():
    tr, va, ts = te.select(rows(), "english_only")
    assert {r["form"] for r in tr} == {"english"} and {r["form"] for r in ts} == set(te.FORMS)
    tr, va, ts = te.select(rows(), "lofo:roman_urdu")
    assert "roman_urdu" not in {r["form"] for r in tr} and {r["form"] for r in ts} == {"roman_urdu"}
    with pytest.raises(ValueError):
        te.select(rows(), "lofo:punjabi")
    with pytest.raises(ValueError):
        te.select(rows(), "random")


def test_leakage_is_rejected():
    rs = rows()
    rs[0]["split"] = "test"  # scenario S0 now in both train and test
    with pytest.raises(ValueError, match="leakage"):
        te.select(rs, "mixed")


def test_ece():
    assert te.expected_calibration_error(np.array([0.9, 0.1]), np.array([1, 0])) == pytest.approx(0.1)
    assert te.expected_calibration_error(np.array([1.0, 1.0]), np.array([1, 1])) == pytest.approx(0.0)


def test_train_validation_leakage_and_manifest_mismatch_rejected():
    rs = rows()
    rs[0]["split"] = "validation"  # S0 in train and validation
    with pytest.raises(ValueError, match="leakage"):
        te.select(rs, "mixed")
    assignment = {f"S{i}": s for i, s in enumerate(["train"] * 6 + ["validation"] * 2 + ["test"] * 2)}
    te.select(rows(), "mixed", assignment)
    assignment["S9"] = "train"
    with pytest.raises(ValueError, match="split manifest"):
        te.select(rows(), "mixed", assignment)


def test_human_validated_must_be_test_only():
    rs = rows()
    rs[0]["human_validated"] = True  # a train example
    with pytest.raises(ValueError, match="human-validated"):
        te.select(rs, "mixed")


def test_scenario_bootstrap_ci_brackets_point():
    y = np.array([0, 1] * 20)
    pred = y.copy()
    pred[:6] = 1 - pred[:6]
    sids = [f"S{i // 2}" for i in range(40)]
    point, lo, hi = te.scenario_bootstrap_ci(y, pred, sids, lambda a, b: float((a == b).mean()), n_boot=300)
    assert lo <= point <= hi and point == pytest.approx(34 / 40)


def test_build_examples_respects_splits_and_human_rule():
    spec_b = importlib.util.spec_from_file_location("build_examples", Path(__file__).resolve().parents[2] / "research/classifiers/build_examples.py")
    be = importlib.util.module_from_spec(spec_b)
    spec_b.loader.exec_module(be)
    from collections import Counter

    from app.v2.records import Decoding, Generation, LabelSource, ResponseLabel

    def g(sid, i, harmful_intent=True):
        return Generation(
            generation_id=f"{sid}-{i}", run_id="r", model_key="m", model_id="m", backend="vllm", record_id=f"{sid}-H-en-base", scenario_id=sid,
            intent_id=f"{sid}-H", scenario_type="harmful" if harmful_intent else "benign", language="english", transformation_type="source",
            prompt_text="p", decoding=Decoding(temperature=0, max_new_tokens=5), sample_index=i, response_text="r",
        )  # fmt: skip

    def lab(gen, src, harmful):
        return ResponseLabel(
            generation_id=gen.generation_id, labeler_id="x", label_source=src, comprehension="understood", behaviour="full_compliance", harmful_content=harmful
        )

    gens = [g("A", 0), g("A", 1), g("B", 0), g("C", 0)]
    labels = {
        gens[0].generation_id: lab(gens[0], LabelSource.ai_panel, True),
        gens[1].generation_id: lab(gens[1], LabelSource.human, False),
        gens[2].generation_id: lab(gens[2], LabelSource.human, True),
    }
    log = Counter()
    out = be.response_examples(gens, labels, {"A": "train", "B": "test", "C": "test"}, log)
    assert [(x["source_id"], x["label"], x["human_validated"]) for x in out] == [("A-0", 1, False), ("B-0", 1, True)]
    assert log["dropped_human_validated_outside_test"] == 1 and log["skipped_unresolved_label"] == 1
