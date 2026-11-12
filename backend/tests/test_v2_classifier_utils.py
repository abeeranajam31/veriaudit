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
