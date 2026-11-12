"""Statistical primitives for VeriAudit v2.

Everything here is deterministic given its inputs (bootstrap takes an explicit
seed) and depends only on numpy/scipy, so the v1 reconstruction and the v2
analyses share one tested implementation.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats as _st


@dataclass(frozen=True)
class Interval:
    estimate: float
    low: float
    high: float


def wilson_interval(successes: int, n: int, confidence: float = 0.95) -> Interval:
    """Wilson score interval for a binomial proportion. n=0 returns NaNs."""
    if n == 0:
        return Interval(math.nan, math.nan, math.nan)
    if not 0 <= successes <= n:
        raise ValueError("successes must be in [0, n]")
    z = float(_st.norm.ppf(1 - (1 - confidence) / 2))
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return Interval(p, max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value: binomial test of b vs c discordant pairs.

    Convention matches the v1 pilot: p = min(1, 2 * P(X <= min(b, c))), X ~ Bin(b + c, 0.5).
    """
    n = b + c
    if n == 0:
        return 1.0
    return float(min(1.0, 2 * _st.binom.cdf(min(b, c), n, 0.5)))


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values (family-wise error control), in input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def benjamini_hochberg(pvalues: Sequence[float]) -> list[float]:
    """BH false-discovery-rate adjusted p-values (for exploratory families)."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i], reverse=True)
    adjusted = [0.0] * m
    running = 1.0
    for k, i in enumerate(order):
        rank = m - k
        running = min(running, pvalues[i] * m / rank)
        adjusted[i] = running
    return adjusted


def paired_difference_newcombe(a: int, b: int, c: int, d: int, confidence: float = 0.95) -> Interval:
    """Newcombe (1998, method 10) CI for p1 - p2 from a paired 2x2 table.

    Table cells (condition 1 x condition 2): a = (1,1), b = (1,0), c = (0,1), d = (0,0),
    where 1 = "event". Returns the interval for p1 - p2 = (b - c) / n.
    """
    n = a + b + c + d
    if n == 0:
        return Interval(math.nan, math.nan, math.nan)
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = (lambda w: (w.low, w.high))(wilson_interval(a + b, n, confidence))
    l2, u2 = (lambda w: (w.low, w.high))(wilson_interval(a + c, n, confidence))
    diff = p1 - p2
    # phi-hat correction term
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    if denom == 0:
        phi = 0.0
    else:
        num = a * d - b * c
        if num > 0:
            num = max(num - n / 2, 0)
        phi = num / math.sqrt(denom)
    dl = math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    du = math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return Interval(diff, max(-1.0, diff - dl), min(1.0, diff + du))


def cluster_bootstrap(
    clusters: Sequence[Sequence[float]],
    statistic,
    n_boot: int = 2000,
    seed: int = 0,
    confidence: float = 0.95,
) -> Interval:
    """Percentile bootstrap resampling whole clusters (e.g. scenarios) with replacement.

    `clusters` is a list of per-cluster payloads; `statistic(list_of_payloads) -> float`.
    """
    k = len(clusters)
    if k == 0:
        return Interval(math.nan, math.nan, math.nan)
    rng = np.random.default_rng(seed)
    point = float(statistic(list(clusters)))
    draws = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, k, size=k)
        draws[i] = statistic([clusters[j] for j in idx])
    alpha = (1 - confidence) / 2
    n_nan = int(np.isnan(draws).sum())
    if n_nan > 0.01 * n_boot:
        raise ValueError(f"{n_nan} of {n_boot} bootstrap draws were NaN; statistic undefined on many resamples")
    lo, hi = np.nanquantile(draws, [alpha, 1 - alpha])
    return Interval(point, float(lo), float(hi))


def signed_rank_test(differences: Sequence[float]) -> float:
    """Two-sided Wilcoxon signed-rank p-value on paired differences (zeros dropped, Pratt not used).

    Uses scipy's method="auto". Differences of 3-sample shares take few distinct values, so ties are
    the norm and the tie-corrected normal approximation is what applies in practice.
    Returns 1.0 when every difference is zero.
    """
    d = [x for x in differences if x != 0]
    if not d:
        return 1.0
    return float(_st.wilcoxon(d, zero_method="wilcox", alternative="two-sided").pvalue)


def paired_t_test(differences: Sequence[float]) -> float:
    """Two-sided one-sample t-test of mean difference = 0 (sensitivity analysis targeting the mean;
    protocol §10). Returns 1.0 if every difference is 0, and 0.0 if all are equal and non-zero."""
    d = np.asarray(differences, dtype=float)
    if len(d) == 0 or np.all(d == 0):
        return 1.0
    if np.all(d == d[0]):
        return 0.0
    return float(_st.ttest_1samp(d, 0.0).pvalue)


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    """Unweighted Cohen's kappa for two raters over the same items."""
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("need two equal-length, non-empty label sequences")
    cats = sorted(set(labels_a) | set(labels_b))
    n = len(labels_a)
    po = sum(x == y for x, y in zip(labels_a, labels_b, strict=True)) / n
    pe = sum((labels_a.count(k) / n) * (labels_b.count(k) / n) for k in cats)
    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def mcnemar_power(n_pairs: int, p10: float, p01: float, alpha: float = 0.05, n_sim: int = 20000, seed: int = 0) -> float:
    """Monte-Carlo power of the two-sided exact McNemar test.

    p10/p01: probabilities that a pair is discordant in each direction.
    """
    rng = np.random.default_rng(seed)
    probs = [p10, p01, 1 - p10 - p01]
    if probs[2] < 0:
        raise ValueError("p10 + p01 must be <= 1")
    draws = rng.multinomial(n_pairs, probs, size=n_sim)
    b, c = draws[:, 0], draws[:, 1]
    n_disc = b + c
    # vectorised exact two-sided p
    pvals = np.minimum(1.0, 2 * _st.binom.cdf(np.minimum(b, c), np.maximum(n_disc, 1), 0.5))
    pvals = np.where(n_disc == 0, 1.0, pvals)
    return float(np.mean(pvals < alpha))


def sign_flip_test(differences: Sequence[float], n_perm: int = 20000, seed: int = 0) -> float:
    """Two-sided paired permutation (sign-flip) test of mean difference = 0.

    Statistic |sum of differences|; under H0 each difference's sign is exchangeable. Zeros do not
    affect the statistic. Exact enumeration for <= 16 non-zero differences, otherwise Monte Carlo
    with the add-one correction p = (1 + #{|T*| >= |T|}) / (1 + n_perm), which is valid at any n_perm.
    Returns 1.0 when every difference is zero.
    """
    d = np.array([x for x in differences if x != 0], dtype=float)
    k = len(d)
    if k == 0:
        return 1.0
    t_obs = abs(d.sum()) - 1e-12  # tolerance for float ties
    if k <= 16:
        signs = ((np.arange(2**k)[:, None] >> np.arange(k)) & 1) * 2 - 1
        return float(np.mean(np.abs(signs @ d) >= t_obs))
    rng = np.random.default_rng(seed)
    signs = rng.choice((-1.0, 1.0), size=(n_perm, k))
    return float((1 + np.sum(np.abs(signs @ d) >= t_obs)) / (1 + n_perm))


def simulate_paired_shares(
    n_pairs: int,
    p10: float,
    p01: float,
    p11: float,
    q_harm: float,
    q_safe: float,
    n_samples: int = 3,
    n_sim: int = 2000,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Planning model A ("two-state"). Simulate per-scenario harmful-sample shares for
    (English, target) pairs.

    Each scenario has a latent state in each form, drawn jointly: harmful in target only (p10),
    English only (p01), both (p11), neither (rest). Each of `n_samples` responses is then harmful
    with probability q_harm in a harmful state and q_safe otherwise. The effect is concentrated in
    the few discordant scenarios, a structure under which majority voting is near-optimal.
    Returns arrays (english_shares, target_shares) of shape (n_sim, n_pairs).
    """
    probs = [p10, p01, p11, 1 - p10 - p01 - p11]
    if probs[3] < 0 or min(probs) < 0:
        raise ValueError("state probabilities must be non-negative and sum to <= 1")
    if not (0 <= q_safe <= 1 and 0 <= q_harm <= 1):
        raise ValueError("q_harm and q_safe must be probabilities")
    rng = np.random.default_rng(seed)
    state = rng.choice(4, size=(n_sim, n_pairs), p=probs)
    tgt_harm = (state == 0) | (state == 2)
    eng_harm = (state == 1) | (state == 2)
    eng = rng.binomial(n_samples, np.where(eng_harm, q_harm, q_safe)) / n_samples
    tgt = rng.binomial(n_samples, np.where(tgt_harm, q_harm, q_safe)) / n_samples
    return eng, tgt


def _logit(p: float) -> float:
    return math.log(p / (1 - p))


def logit_intercept_for_marginal(rate: float, sd: float) -> float:
    """Intercept a with E[expit(a + sd*Z)] = rate, Z ~ N(0,1) (Gauss-Hermite quadrature)."""
    if not 0 < rate < 1:
        raise ValueError("rate must be in (0, 1)")
    return _brentq(lambda a: _gh_mean(a, sd) - rate)


def _brentq(f) -> float:
    from scipy.optimize import brentq

    return float(brentq(f, -40, 40))


def simulate_paired_shares_logit(
    n_pairs: int,
    rate_english: float,
    rate_target: float,
    sigma_scenario: float,
    sigma_form: float = 0.5,
    n_samples: int = 3,
    n_sim: int = 2000,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Planning model B ("logit random effects"). Per-response harmful probability
    expit(a_form + u_scenario + v_scenario,form), u ~ N(0, sigma_scenario), v ~ N(0, sigma_form);
    intercepts are calibrated so the marginal per-response rates equal rate_english / rate_target.
    The effect is spread across all scenarios. Returns (english_shares, target_shares)."""
    sd = math.sqrt(sigma_scenario**2 + sigma_form**2)
    a_e = logit_intercept_for_marginal(rate_english, sd)
    a_t = logit_intercept_for_marginal(rate_target, sd)
    rng = np.random.default_rng(seed)
    u = rng.normal(0, sigma_scenario, size=(n_sim, n_pairs))
    pe = 1 / (1 + np.exp(-(a_e + u + rng.normal(0, sigma_form, size=u.shape))))
    pt = 1 / (1 + np.exp(-(a_t + u + rng.normal(0, sigma_form, size=u.shape))))
    return rng.binomial(n_samples, pe) / n_samples, rng.binomial(n_samples, pt) / n_samples


def _gh_mean(a: float, sd: float) -> float:
    x, w = np.polynomial.hermite_e.hermegauss(80)
    return float(np.sum((w / w.sum()) / (1 + np.exp(-(a + sd * x)))))


def power_from_shares(
    eng: np.ndarray,
    tgt: np.ndarray,
    alphas: Sequence[float] = (0.05,),
    n_samples: int = 3,
    n_perm: int = 2000,
    seed: int = 0,
) -> dict[str, list[float]]:
    """Power, on the same simulated (n_sim, n_pairs) share arrays, of:
    - "signed_rank": PRIMARY test (protocol §10) - Wilcoxon signed-rank on share differences;
    - "mcnemar_majority": secondary - exact McNemar on majority-vote (> half of samples) outcomes;
    - "sign_flip": robustness - sign-flip permutation test on the mean share difference
      (exact but conservative here because the statistic is discrete).
    Also "mean_gap": average simulated per-response gap (target - English), and
    "mc_se": Monte-Carlo standard error of a power estimate at 0.8 for this n_sim.
    The sign-flip p-values use one shared sign matrix (valid per simulated dataset)."""
    if n_samples % 2 == 0:
        raise ValueError("majority vote needs an odd number of samples")
    n_sim, n = eng.shape
    diffs = tgt - eng
    rng = np.random.default_rng(seed)
    signs = rng.choice((-1.0, 1.0), size=(n_perm, n))
    t_obs = np.abs(diffs.sum(axis=1)) - 1e-12
    t_perm = np.abs(signs @ diffs.T)  # (n_perm, n_sim)
    p_sf = (1 + np.sum(t_perm >= t_obs[None, :], axis=0)) / (1 + n_perm)
    p_sf = np.where(np.all(diffs == 0, axis=1), 1.0, p_sf)
    p_sr = np.array([signed_rank_test(row) for row in diffs])
    me, mt = eng > 0.5, tgt > 0.5
    b = np.sum(mt & ~me, axis=1)
    c = np.sum(me & ~mt, axis=1)
    p_mc = np.array([mcnemar_exact(int(x), int(y)) for x, y in zip(b, c, strict=True)])
    return {
        "sign_flip": [float(np.mean(p_sf < a)) for a in alphas],
        "mcnemar_majority": [float(np.mean(p_mc < a)) for a in alphas],
        "signed_rank": [float(np.mean(p_sr < a)) for a in alphas],
        "mean_gap": [float(diffs.mean())],
        "mc_se": [math.sqrt(0.8 * 0.2 / n_sim)],
    }


def paired_share_power(
    n_pairs: int,
    p10: float,
    p01: float,
    p11: float,
    q_harm: float,
    q_safe: float,
    alphas: Sequence[float] = (0.05,),
    n_samples: int = 3,
    n_sim: int = 2000,
    seed: int = 0,
) -> dict[str, list[float]]:
    """Power under planning model A (two-state); see `power_from_shares` for the tests."""
    if n_samples % 2 == 0:
        raise ValueError("majority vote needs an odd number of samples")
    eng, tgt = simulate_paired_shares(n_pairs, p10, p01, p11, q_harm, q_safe, n_samples, n_sim, seed)
    return power_from_shares(eng, tgt, alphas, n_samples, seed=seed)


def logit_share_power(
    n_pairs: int,
    rate_english: float,
    rate_target: float,
    sigma_scenario: float,
    sigma_form: float = 0.5,
    alphas: Sequence[float] = (0.05,),
    n_samples: int = 3,
    n_sim: int = 2000,
    seed: int = 0,
) -> dict[str, list[float]]:
    """Power under planning model B (logit random effects); see `power_from_shares`."""
    eng, tgt = simulate_paired_shares_logit(n_pairs, rate_english, rate_target, sigma_scenario, sigma_form, n_samples, n_sim, seed)
    return power_from_shares(eng, tgt, alphas, n_samples, seed=seed)
