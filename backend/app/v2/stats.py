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
    lo, hi = np.nanquantile(draws, [alpha, 1 - alpha])
    return Interval(point, float(lo), float(hi))


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
