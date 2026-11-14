"""End-to-end analysis pipeline on a fake-backend fixture run (outputs are test fixtures)."""

import json
from pathlib import Path

import pytest

from app.v2.analysis import FIXTURE_BANNER, AnalysisRefused, Options, analyse
from app.v2.inference.backends import FakeBackend
from app.v2.inference.runner import ROOT, load_generations, run
from app.v2.records import LabelSource, ResponseLabel, append_jsonl

SMOKE = ROOT / "configs" / "experiments" / "fixture_smoke.yaml"
MODELS = ROOT / "configs" / "models.yaml"


def make_labels(gens, path: Path):
    """Two scripted judges. Rule (synthetic): harmful Urdu-script responses count as harmful
    compliance; benign Urdu-script prompts count as refused; judge B disagrees on one record."""
    labs = []
    for g in gens:
        if g.response_text is None:
            continue
        urdu = g.language == "urdu"
        for judge in ("judgeA", "judgeB"):
            harmful = g.scenario_type == "harmful" and urdu
            if judge == "judgeB" and g.record_id.endswith("cs-01") and g.scenario_type == "harmful":
                harmful = True  # one systematic disagreement -> unresolved without a third judge
            refused = (g.scenario_type == "benign" and urdu) or (g.scenario_type == "harmful" and not harmful)
            labs.append(
                ResponseLabel(
                    generation_id=g.generation_id,
                    labeler_id=judge,
                    label_source=LabelSource.ai_judge,
                    comprehension="understood",
                    behaviour="full_refusal" if refused else "full_compliance",
                    harmful_content=harmful if g.scenario_type == "harmful" else None,
                    task_success=None if g.scenario_type == "harmful" else ("fail" if refused else "success"),
                    is_test_fixture=True,
                )
            )
    append_jsonl(path, labs)
    return path


@pytest.fixture
def fixture_run(tmp_path):
    out = run(SMOKE, ["fake"], out_root=tmp_path)
    labels = make_labels(load_generations(out), tmp_path / "labels.jsonl")
    return out.parent, labels, tmp_path


def opts(run_dir, labels, tmp_path, **kw):
    return Options(run_dir, [labels], tmp_path / "analysis", MODELS, n_boot=200, **kw)


def test_fixture_run_is_refused_without_override(fixture_run):
    run_dir, labels, tmp = fixture_run
    with pytest.raises(AnalysisRefused, match="fake test backend"):
        analyse(opts(run_dir, labels, tmp))


def test_full_pipeline_on_fixture(fixture_run):
    run_dir, labels, tmp = fixture_run
    o = opts(run_dir, labels, tmp, allow_fixtures=True)
    out = analyse(o)
    d = tmp / "analysis"
    for name in (
        "summary.md", "reproducibility.json", "dataset_quality.md", "agreement.json", "cell_metrics.csv",
        "confirmatory_H1.csv", "confirmatory_H2.csv", "sensitivity.csv", "model_based.csv",
        "linguistic_robustness.csv", "comprehension_strata.csv", "figures/forest_H1.png",
    ):  # fmt: skip
        assert (d / name).exists(), name
    summary = (d / "summary.md").read_text()
    assert FIXTURE_BANNER in summary and "AI-judged" in summary
    repro = json.loads((d / "reproducibility.json").read_text())
    assert repro["run_status"] == "complete" and len(repro["generations_sha256"]) == 64
    assert any("fixture" in x for x in repro["overrides_used"])
    h1 = {r["language"]: r for r in out["H1"]}
    assert h1["urdu"]["gap_pp"] > 0
    mb = (d / "model_based.csv").read_text()
    assert mb.splitlines()[0].startswith("model,language,outcome,estimator") and ",fake," not in mb.splitlines()[0]
    assert "2.17" not in mb and "separation" in mb  # perfectly separated fixture: no absurd odds ratio
    # the code-switched disagreement between judges leaves those generations unresolved -> unscored
    assert h1["code_switched"]["n_units_excluded_unlabelled"] > 0
    agreement = json.loads((d / "agreement.json").read_text())
    assert "judgeA vs judgeB" in agreement["labels"]["judge_pairs"]
    sens = (d / "sensitivity.csv").read_text()
    assert "S-AMB" in sens and "S-HUM2" in sens and "greedy aggregation" in sens
    assert "judge judgeA only" in sens and "judge judgeB only" in sens
    assert (d / "orr_by_contrast_source.csv").exists()


def test_incomplete_run_refused_unless_allowed(tmp_path):
    out = run(SMOKE, ["fake"], out_root=tmp_path, backend_override=FakeBackend(fail_on="Lahore"))
    labels = make_labels(load_generations(out), tmp_path / "labels.jsonl")
    with pytest.raises(AnalysisRefused, match="incomplete"):
        analyse(opts(out.parent, labels, tmp_path, allow_fixtures=True))
    analyse(opts(out.parent, labels, tmp_path, allow_fixtures=True, allow_incomplete=True))
    assert "run status is 'incomplete'" in (tmp_path / "analysis" / "summary.md").read_text()


def test_tampered_generations_are_refused_even_with_overrides(fixture_run):
    run_dir, labels, tmp = fixture_run
    gen = run_dir / "generations.jsonl"
    gen.write_text(gen.read_text().replace("[FAKE", "[EDITED", 1))
    with pytest.raises(AnalysisRefused, match="changed after the run"):
        analyse(opts(run_dir, labels, tmp, allow_fixtures=True, allow_incomplete=True))


def test_calibration_mode_runs(fixture_run):
    run_dir, labels, tmp = fixture_run
    analyse(opts(run_dir, labels, tmp, allow_fixtures=True, calibration=True))
    assert (tmp / "analysis" / "calibration_parameters.csv").exists()
    assert (tmp / "analysis" / "calibration_power.csv").exists()


def test_calibration_reports_paired_t_mde(tmp_path):
    import numpy as np

    from app.v2.analysis import Options, calibration
    from app.v2.metrics import Unit

    rng = np.random.default_rng(1)
    units = []
    for i in range(40):
        p = 1 / (1 + np.exp(-(-3 + 2 * rng.normal())))
        for lang in ("english", "urdu") if i < 7 else ("english",):
            share = rng.binomial(3, p) / 3
            units.append(Unit("m", f"S{i}", f"S{i}-H", "harmful", lang, "base", "ok", 3, harmful=share))
    o = Options(run_dir=tmp_path, label_files=[], out_dir=tmp_path, model_manifest=tmp_path / "x", seed=1, calibration_sims=20)
    params = calibration(units, o)["calibration_parameters"]
    row = params[0]
    assert row["n_pairs_urdu"] == 7 and row["sd_diff_urdu"] is not None
    if 0 < row["rate"] < 0.9:
        assert row["mde_pp_conservative_upper"] is None or row["mde_pp_conservative_upper"] >= row["mde_pp_conservative"]
        assert "power_paired_t" in (tmp_path / "calibration_power.csv").read_text().splitlines()[0]
