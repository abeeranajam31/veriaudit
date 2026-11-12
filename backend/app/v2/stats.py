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
    """Simulate per-scenario harmful-sample shares for (English, target) pairs.

    Each scenario has a latent state in each form, drawn jointly: harmful in target only (p10),
    English only (p01), both (p11), neither (rest). Each of `n_samples` responses is then harmful
    with probability q_harm in a harmful state and q_safe otherwise. Returns arrays
    (english_shares, target_shares) of shape (n_sim, n_pairs).
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
    """Monte-Carlo power, on the same simulated data, of
    (a) the primary test: Wilcoxon signed-rank on per-scenario share differences, and
    (b) the secondary test: exact McNemar on majority-vote (> half of samples) outcomes.

    Returns {"signed_rank": [power per alpha], "mcnemar_majority": [...], "mean_gap": [...]},
    where mean_gap is the average simulated per-response gap (target - English).
    """
    if n_samples % 2 == 0:
        raise ValueError("majority vote needs an odd number of samples")
    eng, tgt = simulate_paired_shares(n_pairs, p10, p01, p11, q_harm, q_safe, n_samples, n_sim, seed)
    diffs = tgt - eng
    p_sr = np.array([signed_rank_test(row) for row in diffs])
    me, mt = eng > 0.5, tgt > 0.5
    b = np.sum(mt & ~me, axis=1)
    c = np.sum(me & ~mt, axis=1)
    p_mc = np.array([mcnemar_exact(int(x), int(y)) for x, y in zip(b, c, strict=True)])
    return {
        "signed_rank": [float(np.mean(p_sr < a)) for a in alphas],
        "mcnemar_majority": [float(np.mean(p_mc < a)) for a in alphas],
        "mean_gap": [float(diffs.mean())],
    }
