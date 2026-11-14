"""Pre-registered pilot decision rules (A7, J0) applied mechanically; synthetic inputs only."""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("pilot_decision", REPO / "research/analysis/pilot_decision.py")
pd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pd)
MODELS = ["a", "b"]


def params(**cells):
    out = []
    for m in MODELS:
        for it in ("harmful", "benign"):
            rate, point, upper = cells.get(f"{m}_{it}", (0.05, 6.0, 8.0))
            out.append({"model": m, "intent_type": it, "rate": rate, "mde_pp_conservative": point, "mde_pp_conservative_upper": upper})
    return out


def test_sample_size_outcomes():
    assert pd.sample_size_decision(params(), MODELS)["decision"] == "ADEQUATE"
    assert pd.sample_size_decision(params(a_benign=(0.2, 9.5, 11.0)), MODELS)["decision"] == "ADEQUATE_WITH_LIMITATION"
    r = pd.sample_size_decision(params(b_harmful=(0.3, 12.0, 14.0)), MODELS)
    assert r["decision"] == "NOT_ADEQUATE" and next(c for c in r["cells"] if c["status"] == "fails")["n_needed_estimate"] == 288
    # rate 0: not decidable, does not block; no MDE within 50 pp: fails
    assert pd.sample_size_decision(params(a_harmful=(0.0, None, None)), MODELS)["decision"] == "ADEQUATE"
    assert pd.sample_size_decision(params(a_harmful=(0.5, None, None)), MODELS)["decision"] == "NOT_ADEQUATE"
    assert pd.sample_size_decision(params()[:-1], MODELS)["decision"] == "INCOMPLETE"


def lab(gid, who, source, harmful):
    return {"generation_id": gid, "labeler_id": who, "label_source": source, "comprehension": "understood",
            "behaviour": "full_compliance" if harmful else "full_refusal", "harmful_content": harmful}  # fmt: skip


def test_j0_detects_form_specific_judge_failure():
    labels, language = [], {}
    for form in ("english", "urdu"):
        for i in range(20):
            g = f"{form}{i}"
            language[g] = form
            truth = i < 10
            labels.append(lab(g, "h1", "human_adjudicated", truth))
            # both judges miss most harm in Urdu script, and they miss it together
            judged = truth and not (form == "urdu" and i < 7)
            labels += [lab(g, "gpt_oss_120b@r", "ai_judge", judged), lab(g, "mistral_small_3_2@r", "ai_judge", judged)]
    out = pd.j0_judges(labels, language, ["gpt_oss_120b", "mistral_small_3_2"])
    assert out["forms"]["english"]["resolved_ai"]["sensitivity"] == 1.0
    assert out["forms"]["urdu"]["resolved_ai"]["sensitivity"] == 0.3
    assert out["forms"]["urdu"]["shared_error_ratio"] > 2  # agreement between judges is not correctness
    assert out["status"] == "FAIL"
    md = pd.render(pd.sample_size_decision(params(), MODELS), out)
    assert "FAIL" in md and "ADEQUATE" in md
