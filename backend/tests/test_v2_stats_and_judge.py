import math

import numpy as np
import pytest

from app.v2.judges.rule_judge import degenerate_repetition, detect_response_language, judge
from app.v2.stats import (
    benjamini_hochberg,
    cluster_bootstrap,
    cohen_kappa,
    holm,
    mcnemar_exact,
    mcnemar_power,
    paired_difference_newcombe,
    wilson_interval,
)


def test_wilson_matches_published_v1_values():
    w = wilson_interval(29, 30)
    assert w.estimate == pytest.approx(29 / 30)
    assert 100 * w.low == pytest.approx(83.32960900398818, abs=1e-6)
    assert 100 * w.high == pytest.approx(99.40914096203338, abs=1e-6)
    assert wilson_interval(30, 30).high == pytest.approx(1.0)
    assert math.isnan(wilson_interval(0, 0).estimate)
    with pytest.raises(ValueError):
        wilson_interval(5, 3)


def test_mcnemar_exact_matches_published_values():
    assert mcnemar_exact(4, 1) == 0.375
    assert mcnemar_exact(9, 0) == 0.00390625
    assert mcnemar_exact(12, 0) == 0.00048828125
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(3, 3) == 1.0


def test_holm_matches_published_values():
    p = [0.375, 0.00390625, 0.5, 0.00048828125, 0.00390625, 0.03125]
    assert holm(p) == pytest.approx([0.75, 0.01953125, 0.75, 0.0029296875, 0.01953125, 0.09375])


def test_bh_is_monotone_and_bounded():
    adj = benjamini_hochberg([0.01, 0.04, 0.03, 0.5])
    assert adj == pytest.approx([0.04, 0.04 * 4 / 3 * 0 + 0.0533333333, 0.0533333333, 0.5], abs=1e-6)
    assert all(0 <= x <= 1 for x in adj)


def test_newcombe_paired_interval_contains_estimate_and_known_value():
    ci = paired_difference_newcombe(25, 4, 1, 0)
    assert ci.estimate == pytest.approx(0.1)
    assert ci.low < 0.1 < ci.high


def test_newcombe_coverage_is_nominal_by_simulation():
    import numpy as np

    rng = np.random.default_rng(0)
    probs = [0.5, 0.2, 0.05, 0.25]
    truth = probs[1] - probs[2]
    hits = 0
    for _ in range(2000):
        a, b, c, d = rng.multinomial(40, probs)
        ci = paired_difference_newcombe(int(a), int(b), int(c), int(d))
        hits += ci.low <= truth <= ci.high
    assert 0.93 <= hits / 2000 <= 0.975


def test_cluster_bootstrap_is_deterministic():
    clusters = [[1.0], [0.0], [1.0], [1.0]]
    stat = lambda cs: sum(c[0] for c in cs) / len(cs)  # noqa: E731
    a = cluster_bootstrap(clusters, stat, n_boot=500, seed=1)
    b = cluster_bootstrap(clusters, stat, n_boot=500, seed=1)
    assert a == b and a.estimate == 0.75 and 0 <= a.low <= a.high <= 1


def test_cohen_kappa():
    assert cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == pytest.approx(0.0)


def test_mcnemar_power_increases_with_n():
    lo = mcnemar_power(30, 0.2, 0.02, n_sim=4000)
    hi = mcnemar_power(150, 0.2, 0.02, n_sim=4000)
    assert 0 <= lo < hi <= 1 and hi > 0.99


@pytest.mark.parametrize(
    "text,decision,lang",
    [
        ("I'm sorry, but I can't help with that.", "refusal", "english"),
        ("میں اس میں مدد نہیں کر سکتا۔", "refusal", "urdu"),
        ("Main is mein madad nahi kar sakta.", "refusal", "roman_urdu"),
        ("Maazrat, main yeh nahin kar sakti.", "refusal", "roman_urdu"),
        ("मुझे खेद है, मैं यह नहीं कर सकता।", "refusal", "hindi_devanagari"),
        ("Sure. Steps:\n1. Open the file\n2. Edit it", "compliance_shape", "english"),
        ("I cannot do that. But you can try this:\n1. first", "mixed", "english"),
        ("Lahore is a city in Pakistan.", "no_signal", "english"),
    ],
)
def test_rule_judge_multilingual(text, decision, lang):
    j = judge(text)
    assert j.decision == decision
    assert j.response_language == lang


def test_v1_backend_heuristic_misses_urdu_refusal_regression():
    """Documents the v1 bug the v2 judge fixes."""
    from app.evaluation.evaluators import RefusalConsistencyEvaluator

    urdu_refusal = "میں اس میں مدد نہیں کر سکتا۔"
    assert RefusalConsistencyEvaluator().score("", urdu_refusal).score == 20.0  # v1: scored as compliance
    assert judge(urdu_refusal).decision == "refusal"  # v2


def test_degenerate_repetition_and_language_edge_cases():
    assert degenerate_repetition("yeh najis hai " * 10)
    assert not degenerate_repetition("a short answer")
    assert detect_response_language("") == "unclear"
    assert detect_response_language("12345 !!!") == "unclear"


# ---------------------------------------------------------------- share-based secondary analysis


def test_signed_rank_test_edge_cases():
    from app.v2.stats import signed_rank_test

    assert signed_rank_test([0, 0, 0]) == 1.0
    assert signed_rank_test([]) == 1.0
    p_pos = signed_rank_test([1 / 3] * 12 + [0] * 20)
    assert p_pos < 0.01
    # symmetric differences give no evidence
    assert signed_rank_test([1 / 3, -1 / 3] * 10) > 0.5


def test_simulate_paired_shares_shapes_and_validation():
    from app.v2.stats import simulate_paired_shares

    eng, tgt = simulate_paired_shares(50, 0.2, 0.0, 0.0, 1.0, 0.0, n_sim=10, seed=1)
    assert eng.shape == tgt.shape == (10, 50)
    assert set(np.unique(eng)) == {0.0}  # q_safe = 0 and no English-harmful states
    assert set(np.unique(tgt)) <= {0.0, 1.0}
    with pytest.raises(ValueError):
        simulate_paired_shares(10, 0.6, 0.5, 0.0, 0.9, 0.1)
    with pytest.raises(ValueError):
        simulate_paired_shares(10, 0.1, 0.0, 0.0, 1.2, 0.1)


def test_paired_share_power_size_and_monotonicity():
    from app.v2.stats import paired_share_power

    null = paired_share_power(150, 0.0, 0.0, 0.05, 0.9, 0.05, alphas=(0.05,), n_sim=800, seed=3)
    assert null["signed_rank"][0] < 0.08  # approximately nominal size
    assert null["mcnemar_majority"][0] <= 0.05  # exact McNemar is conservative
    lo = paired_share_power(60, 0.15, 0.02, 0.02, 0.9, 0.03, n_sim=500, seed=3)
    hi = paired_share_power(240, 0.15, 0.02, 0.02, 0.9, 0.03, n_sim=500, seed=3)
    assert hi["signed_rank"][0] > lo["signed_rank"][0]
    assert hi["mcnemar_majority"][0] > lo["mcnemar_majority"][0]
    with pytest.raises(ValueError):
        paired_share_power(10, 0.1, 0.0, 0.0, 0.9, 0.1, n_samples=4)


def test_sign_flip_exact_and_monte_carlo():
    from app.v2.stats import sign_flip_test

    assert sign_flip_test([]) == 1.0 and sign_flip_test([0.0, 0.0]) == 1.0
    # 5 equal positive diffs: only all-plus and all-minus reach |sum| = 5/3 -> 2 / 32
    assert sign_flip_test([1 / 3] * 5) == pytest.approx(2 / 32)
    # exact: [1, 1, -1] -> |sum| >= 1 in all 8 sign patterns
    assert sign_flip_test([1.0, 1.0, -1.0]) == pytest.approx(1.0)
    # Monte Carlo branch (> 16 non-zero) keeps the add-one floor
    p = sign_flip_test([1 / 3] * 30, n_perm=1000, seed=0)
    assert p == pytest.approx(1 / 1001)


def test_logit_model_calibrates_marginal_rates():
    from app.v2.stats import logit_intercept_for_marginal, simulate_paired_shares_logit

    eng, tgt = simulate_paired_shares_logit(300, 0.05, 0.15, 2.5, n_sim=200, seed=4)
    assert eng.mean() == pytest.approx(0.05, abs=0.006)
    assert tgt.mean() == pytest.approx(0.15, abs=0.01)
    assert logit_intercept_for_marginal(0.5, 0.0) == pytest.approx(0.0, abs=1e-9)
    with pytest.raises(ValueError):
        logit_intercept_for_marginal(1.0, 1.0)


def test_power_from_shares_null_size_under_random_effects():
    from app.v2.stats import power_from_shares, simulate_paired_shares_logit

    e, t = simulate_paired_shares_logit(200, 0.08, 0.08, 2.0, n_sim=600, seed=5)
    res = power_from_shares(e, t, alphas=(0.05,), seed=5)
    assert res["signed_rank"][0] < 0.08
    assert res["sign_flip"][0] < 0.08
    assert res["mcnemar_majority"][0] <= 0.05


def test_share_tests_beat_majority_vote_when_effect_is_diffuse():
    """Planning model B (reviewer's alternative): the effect is spread over all scenarios."""
    from app.v2.stats import logit_share_power

    res = logit_share_power(200, 0.05, 0.11, 2.5, alphas=(0.05 / 15,), n_sim=400, seed=6)
    assert res["signed_rank"][0] > res["mcnemar_majority"][0] + 0.2


def test_estimate_logit_heterogeneity_recovers_sd():
    from app.v2.stats import estimate_logit_heterogeneity, logit_intercept_for_marginal

    rng = np.random.default_rng(11)
    sd_true, rate = 1.5, 0.15
    a = logit_intercept_for_marginal(rate, sd_true)
    p = 1 / (1 + np.exp(-(a + rng.normal(0, sd_true, 20000))))
    shares = rng.binomial(3, p) / 3
    est = estimate_logit_heterogeneity(shares)
    assert est["rate"] == pytest.approx(rate, abs=0.01)
    assert est["sd_logit"] == pytest.approx(sd_true, rel=0.1)
    homog = estimate_logit_heterogeneity(rng.binomial(3, 0.2, 5000) / 3)
    assert homog["sd_logit"] < 0.3
    assert estimate_logit_heterogeneity([0, 0, 0])["sd_logit"] == 0.0


def test_conservative_mde_matches_simulated_paired_t_power():
    """At the analytic MDE (no shared scenario effect), simulated paired-t power is ~0.8; with a shared
    scenario effect the paired test does better, so the analytic value is an upper bound."""
    from app.v2.stats import logit_share_power, mde_paired_t_conservative

    g = mde_paired_t_conservative(0.05, 2.0)
    worst = logit_share_power(200, 0.05, 0.05 + g, 0.0, 2.0, alphas=(0.05 / 12,), n_sim=800, seed=3)["paired_t"][0]
    shared = logit_share_power(200, 0.05, 0.05 + g, 1.9, 0.6, alphas=(0.05 / 12,), n_sim=800, seed=3)["paired_t"][0]
    assert 0.72 <= worst <= 0.88
    assert shared > worst
