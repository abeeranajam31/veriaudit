"""Second-round validation of the confirmatory analysis (2026-11-13, protocol §10).

Questions
  1. Type I error with Monte Carlo uncertainty: 20,000 simulations per null, exact (Clopper-Pearson)
     95% intervals on every rejection rate, at alpha = .05 and alpha = .05/12.
  2. Estimand: what the signed-rank test responds to, versus the mean per-response gap (CLSG v2),
     including a data-generating process where the two have opposite signs.
  3. Confidence intervals for the mean gap and for a single per-response rate at rare outcome
     rates: coverage and width of several methods.
  4. Power across rare outcomes, heterogeneous scenario effects, ties/zeros, and within-unit
     correlation of the 3 sampled responses.

Design: n = 200 scenarios, 3 samples per (scenario, form). Per scenario the two forms have response
probabilities p_e, p_t; each unit's 3 samples are drawn with within-unit correlation rho (with
probability rho a sample copies the unit's first sample, else it is an independent draw), so the
marginal rate is unchanged and rho = 0 is conditional independence.

Tests (two-sided): signed-rank exactly as app.v2.stats.signed_rank_test (vectorised; scipy is used
for every row where scipy would not use the normal approximation, and the vectorised version is
checked against scipy before use); paired t on per-scenario share differences; exact McNemar on
majority votes.

Run (repo root): PYTHONPATH=backend python research/stats_validation/validate_v2.py [--quick]
Outputs: results/stats_validation/v2/*.csv, run_metadata.json. Seeded and deterministic.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import stats as st
from scipy.optimize import brentq

from app.v2.stats import signed_rank_test

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "stats_validation" / "v2"
QUICK = "--quick" in sys.argv
N = 200
K = 3
FAMILY = 12
ALPHAS = (0.05, 0.05 / FAMILY)
SIMS_NULL = 2000 if QUICK else 20000
SIMS_ALT = 1000 if QUICK else 4000
SIMS_CI = 500 if QUICK else 2000
BOOT = 300 if QUICK else 1000
Z975 = float(st.norm.ppf(0.975))


# --------------------------------------------------------------------------- data generation


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def _gh_mean(a, sd):
    x, w = np.polynomial.hermite_e.hermegauss(80)
    return float(np.sum((w / w.sum()) * expit(a + sd * x)))


def intercept(rate, sd):
    return brentq(lambda a: _gh_mean(a, sd) - rate, -40, 40)


@dataclass
class DGP:
    name: str
    kind: str  # null | alternative
    description: str
    gen: object = field(repr=False)  # (rng, sims) -> (pe, pt) arrays (sims, N)
    rho: float = 0.0

    def probs(self, rng, sims):
        return self.gen(rng, sims)


def logit_re(rate_e, rate_t, sigma_u, sigma_f=0.5):
    sd = math.sqrt(sigma_u**2 + sigma_f**2)
    a_e, a_t = intercept(rate_e, sd), intercept(rate_t, sd)

    def g(rng, sims):
        u = rng.normal(0, sigma_u, (sims, N))
        return expit(a_e + u + rng.normal(0, sigma_f, (sims, N))), expit(a_t + u + rng.normal(0, sigma_f, (sims, N)))

    return g


def mixture(types):
    """types: list of (probability, p_e, p_t); scenarios drawn i.i.d. from the mixture."""
    probs = np.array([t[0] for t in types])
    pe_v = np.array([t[1] for t in types])
    pt_v = np.array([t[2] for t in types])
    assert abs(probs.sum() - 1) < 1e-9

    def g(rng, sims):
        idx = rng.choice(len(types), size=(sims, N), p=probs)
        return pe_v[idx], pt_v[idx]

    return g


def counts_mixture(types):
    """types: list of (probability, harmful samples in English, harmful samples in target), each out
    of K. Scenarios are drawn i.i.d.; within a unit the count is fixed (an extreme of within-unit
    correlation). Returns shares directly."""
    probs = np.array([t[0] for t in types])
    ce = np.array([t[1] for t in types]) / K
    ct = np.array([t[2] for t in types]) / K
    assert abs(probs.sum() - 1) < 1e-9

    def g(rng, sims):
        idx = rng.choice(len(types), size=(sims, N), p=probs)
        return ce[idx], ct[idx]

    g.direct_shares = True
    return g


def sample_shares(rng, p, rho):
    first = rng.random(p.shape) < p
    total = first.astype(np.int16)
    for _ in range(K - 1):
        copy = rng.random(p.shape) < rho
        fresh = rng.random(p.shape) < p
        total += np.where(copy, first, fresh)
    return total / K


def simulate(dgp: DGP, rng, sims):
    pe, pt = dgp.probs(rng, sims)
    if getattr(dgp.gen, "direct_shares", False):
        return pe, pt, pe, pt
    return sample_shares(rng, pe, dgp.rho), sample_shares(rng, pt, dgp.rho), pe, pt


# Mean-zero nulls with asymmetric difference distributions (scenario types: (prob, p_e, p_t)).
ASYM_A = [(0.10, 0.10, 0.50), (0.90, 0.10, 0.10 - 0.40 * 0.10 / 0.90)]
ASYM_B = [(0.03, 0.05, 0.65), (0.97, 0.05, 0.05 - 0.60 * 0.03 / 0.97)]
ASYM_C = [(0.10, 0.40, 0.05), (0.90, 0.40, 0.40 + 0.35 * 0.10 / 0.90)]
# Direction conflict (counts out of 3, English -> target): the mean per-response gap is POSITIVE
# (+2 pp) but the largest non-zero differences are negative, so the signed-rank functional is
# negative. 12% of scenarios: 0 -> 2 harmful samples (target stochastically jailbroken);
# 6%: 3 -> 0 (English reliably complies, target reliably refuses or is not understood).
CONFLICT = [(0.12, 0, 2), (0.06, 3, 0), (0.82, 0, 0)]
CONFLICT_STRONG = [(0.30, 0, 2), (0.15, 3, 0), (0.55, 0, 0)]  # same shape, mean +5 pp
# Mean-zero null with the same shape: 0 -> 2 in 9%, 3 -> 0 in 6% (mean 0, theta < 0).
CONFLICT_NULL = [(0.09, 0, 2), (0.06, 3, 0), (0.85, 0, 0)]
CROSS_PLUS3 = [(0.10, 0.10, 0.50), (0.90, 0.10, 0.10 - (0.40 * 0.10 - 0.03) / 0.90)]


def mean_gap(types):
    return sum(w * (pt - pe) for w, pe, pt in types)


def mean_gap_counts(types):
    return sum(w * (ct - ce) / K for w, ce, ct in types)


NULLS = [
    DGP("N1_re_5pct", "null", "logit RE, 5% both forms, sigma_u 2.5", logit_re(0.05, 0.05, 2.5)),
    DGP("N2_re_20pct", "null", "logit RE, 20% both forms, sigma_u 1.0", logit_re(0.20, 0.20, 1.0)),
    DGP("N3_rare_1pct", "null", "logit RE, 1% both forms, sigma_u 2.5", logit_re(0.01, 0.01, 2.5)),
    DGP("N4_rare_0.5pct", "null", "logit RE, 0.5% both forms, sigma_u 2.5", logit_re(0.005, 0.005, 2.5)),
    DGP("N5_re_5pct_rho0.8", "null", "logit RE, 5%, within-unit correlation 0.8", logit_re(0.05, 0.05, 2.5), rho=0.8),
    DGP("N6_re_20pct_rho0.8", "null", "logit RE, 20%, sigma_u 1.0, within-unit correlation 0.8", logit_re(0.20, 0.20, 1.0), rho=0.8),
    DGP("N7_asym_A", "null", "mean 0: 10% of scenarios +40 pp, rest -4.4 pp (base 10%)", mixture(ASYM_A)),
    DGP("N8_asym_B", "null", "mean 0: 3% of scenarios +60 pp, rest -1.9 pp (base 5%)", mixture(ASYM_B)),
    DGP("N9_asym_C", "null", "mean 0: 10% of scenarios -35 pp, rest +3.9 pp (base 40%)", mixture(ASYM_C)),
    DGP("N10_asym_A_rho0.8", "null", "as N7 with within-unit correlation 0.8", mixture(ASYM_A), rho=0.8),
    DGP("N11_conflict_mean0", "null", "mean 0 with negative signed-rank functional: 9% of scenarios 0->2 of 3 harmful, 6% 3->0", counts_mixture(CONFLICT_NULL)),
]
ALTS = [
    DGP("A1_re_5to11", "alternative", "logit RE 5% -> 11%, sigma_u 2.5", logit_re(0.05, 0.11, 2.5)),
    DGP("A2_re_5to9_s1", "alternative", "logit RE 5% -> 9%, sigma_u 1.0", logit_re(0.05, 0.09, 1.0)),
    DGP("A3_rare_1to3", "alternative", "logit RE 1% -> 3%, sigma_u 2.5", logit_re(0.01, 0.03, 2.5)),
    DGP("A4_rare_0.5to2", "alternative", "logit RE 0.5% -> 2%, sigma_u 2.5", logit_re(0.005, 0.02, 2.5)),
    DGP("A5_re_5to11_rho0.8", "alternative", "as A1 with within-unit correlation 0.8", logit_re(0.05, 0.11, 2.5), rho=0.8),
    DGP("A6_re_5to11_rho0.95", "alternative", "as A1 with within-unit correlation 0.95", logit_re(0.05, 0.11, 2.5), rho=0.95),
    DGP("A7_crossover_+3", "alternative", "heterogeneous: 10% of scenarios +40 pp, rest -1.1 pp (mean +3 pp)", mixture(CROSS_PLUS3)),
    DGP("A8_direction_conflict", "alternative", "mean +2 pp, signed-rank functional negative: 12% 0->2 of 3 harmful, 6% 3->0", counts_mixture(CONFLICT)),
    DGP("A9_direction_conflict_strong", "alternative", "mean +5 pp, same shape as A8: 30% 0->2, 15% 3->0", counts_mixture(CONFLICT_STRONG)),
]
TRUE_GAP = {
    "A1_re_5to11": 0.06, "A2_re_5to9_s1": 0.04, "A3_rare_1to3": 0.02, "A4_rare_0.5to2": 0.015,
    "A5_re_5to11_rho0.8": 0.06, "A6_re_5to11_rho0.95": 0.06, "A7_crossover_+3": mean_gap(CROSS_PLUS3), "A8_direction_conflict": mean_gap_counts(CONFLICT),
    "A9_direction_conflict_strong": mean_gap_counts(CONFLICT_STRONG),
}  # fmt: skip


# --------------------------------------------------------------------------- tests (vectorised)


def signed_rank_p(D):
    """p-values identical to app.v2.stats.signed_rank_test (zeros dropped, scipy 'auto' rules)."""
    sims = D.shape[0]
    p = np.empty(sims)
    absd = np.abs(D)
    nz = absd > 0
    n_nz = nz.sum(1)
    for i in range(sims):
        d = D[i][nz[i]]
        n = len(d)
        if n == 0:
            p[i] = 1.0
            continue
        a = np.abs(d)
        ranks = st.rankdata(a)
        _, counts = np.unique(a, return_counts=True)
        ties = (counts > 1).any()
        if (not ties and n <= 50) or (ties and n <= 13):
            p[i] = signed_rank_test(d.tolist())
            continue
        r_plus = ranks[d > 0].sum()
        mean = n * (n + 1) / 4
        var = n * (n + 1) * (2 * n + 1) / 24 - (counts**3 - counts).sum() / 48
        z = (r_plus - mean) / math.sqrt(var) if var > 0 else 0.0
        p[i] = 2 * st.norm.sf(abs(z))
    return p, n_nz


def signed_rank_direction(D):
    out = np.zeros(D.shape[0])
    for i in range(D.shape[0]):
        d = D[i][D[i] != 0]
        if len(d):
            r = st.rankdata(np.abs(d))
            out[i] = np.sign(r[d > 0].sum() - r[d < 0].sum())
    return out


def paired_t_p(D):
    m = D.mean(1)
    s = D.std(1, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = m / (s / math.sqrt(N))
    p = 2 * st.t.sf(np.abs(t), N - 1)
    p = np.where(s == 0, np.where(m == 0, 1.0, 0.0), p)
    return p


def mcnemar_p(se, stt):
    me, mt = se > 0.5, stt > 0.5
    b = (mt & ~me).sum(1)
    c = (me & ~mt).sum(1)
    n = b + c
    p = np.minimum(1.0, 2 * st.binom.cdf(np.minimum(b, c), np.maximum(n, 1), 0.5))
    return np.where(n == 0, 1.0, p), np.sign(b - c)


def clopper_pearson(k, n):
    lo = st.beta.ppf(0.025, k, n - k + 1) if k > 0 else 0.0
    hi = st.beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    return float(lo), float(hi)


# --------------------------------------------------------------------------- intervals (vectorised)


def wilson(p, n_eff, z=Z975):
    denom = 1 + z**2 / n_eff
    centre = (p + z**2 / (2 * n_eff)) / denom
    half = z * np.sqrt(p * (1 - p) / n_eff + z**2 / (4 * n_eff**2)) / denom
    return np.clip(centre - half, 0, 1), np.clip(centre + half, 0, 1)


def clustered_wilson(shares):
    """Wilson interval for a per-response rate with a design-effect-adjusted sample size:
    n_eff = (K*N) / deff, deff = max(1, Var_cluster / Var_binomial)."""
    p = shares.mean(1)
    var_cl = shares.var(1, ddof=1) / N
    var_bin = p * (1 - p) / (K * N)
    with np.errstate(divide="ignore", invalid="ignore"):
        deff = np.where(var_bin > 0, var_cl / var_bin, 1.0)
    deff = np.maximum(deff, 1.0)
    n_eff = K * N / deff
    lo, hi = wilson(p, n_eff)
    return p, lo, hi


def mover(se, stt):
    """Newcombe-type MOVER interval for p_t - p_e from clustered Wilson limits and the
    scenario-level correlation of the two forms' shares."""
    pe, le, ue = clustered_wilson(se)
    pt, lt, ut = clustered_wilson(stt)
    with np.errstate(divide="ignore", invalid="ignore"):
        cov = ((se - se.mean(1, keepdims=True)) * (stt - stt.mean(1, keepdims=True))).sum(1) / (N - 1)
        r = cov / (se.std(1, ddof=1) * stt.std(1, ddof=1))
    r = np.nan_to_num(r)
    d = pt - pe
    lo = d - np.sqrt(np.maximum(0, (pt - lt) ** 2 + (ue - pe) ** 2 - 2 * r * (pt - lt) * (ue - pe)))
    hi = d + np.sqrt(np.maximum(0, (ut - pt) ** 2 + (pe - le) ** 2 - 2 * r * (ut - pt) * (pe - le)))
    return lo, hi


def t_interval(D):
    m = D.mean(1)
    h = st.t.ppf(0.975, N - 1) * D.std(1, ddof=1) / math.sqrt(N)
    return m - h, m + h


def percentile_boot(D, rng):
    sims = D.shape[0]
    lo, hi = np.empty(sims), np.empty(sims)
    for i in range(sims):
        idx = rng.integers(0, N, (BOOT, N))
        means = D[i][idx].mean(1)
        lo[i], hi[i] = np.quantile(means, [0.025, 0.975])
    return lo, hi


def boot_t(D, rng):
    """Studentised (bootstrap-t) interval for the mean of D."""
    sims = D.shape[0]
    lo, hi = np.empty(sims), np.empty(sims)
    for i in range(sims):
        d = D[i]
        m, s = d.mean(), d.std(ddof=1)
        if s == 0:
            lo[i] = hi[i] = m
            continue
        idx = rng.integers(0, N, (BOOT, N))
        b = d[idx]
        bs = b.std(1, ddof=1)
        tt = np.where(bs > 0, (b.mean(1) - m) / (bs / math.sqrt(N)), 0.0)
        q_lo, q_hi = np.quantile(tt, [0.025, 0.975])
        lo[i], hi[i] = m - q_hi * s / math.sqrt(N), m - q_lo * s / math.sqrt(N)
    return lo, hi


def boot_rate(shares, rng):
    sims = shares.shape[0]
    lo, hi = np.empty(sims), np.empty(sims)
    for i in range(sims):
        idx = rng.integers(0, N, (BOOT, N))
        means = shares[i][idx].mean(1)
        lo[i], hi[i] = np.quantile(means, [0.025, 0.975])
    return lo, hi


# --------------------------------------------------------------------------- studies


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def check_signed_rank_equivalence(rng):
    """The vectorised signed-rank must equal app.v2.stats.signed_rank_test row by row."""
    worst = 0.0
    for dgp in NULLS[:3] + ALTS[:3]:
        se, stt, _, _ = simulate(dgp, rng, 300)
        D = stt - se
        pv, _ = signed_rank_p(D)
        ref = np.array([signed_rank_test(list(d)) for d in D])
        worst = max(worst, float(np.max(np.abs(pv - ref))))
    if worst > 1e-9:
        raise SystemExit(f"vectorised signed-rank disagrees with app.v2.stats.signed_rank_test (max |diff| {worst})")
    return worst


def rejection_study(dgps, sims, seed0):
    rows = []
    for j, dgp in enumerate(dgps):
        rng = np.random.default_rng(seed0 + j)
        se, stt, pe, pt = simulate(dgp, rng, sims)
        D = stt - se
        true_mean = float((pt - pe).mean()) if dgp.name not in TRUE_GAP else TRUE_GAP[dgp.name]
        if dgp.kind == "null":
            true_mean = 0.0
        p_sr, n_nz = signed_rank_p(D)
        dir_sr = signed_rank_direction(D)
        p_t = paired_t_p(D)
        dir_t = np.sign(D.mean(1))
        p_mc, dir_mc = mcnemar_p(se, stt)
        for test, p, direction in (("signed_rank", p_sr, dir_sr), ("paired_t", p_t, dir_t), ("mcnemar_majority", p_mc, dir_mc)):
            row = {"dgp": dgp.name, "kind": dgp.kind, "description": dgp.description, "rho": dgp.rho, "true_mean_gap_pp": round(100 * true_mean, 3),
                   "test": test, "n_sim": sims, "median_nonzero_diffs": int(np.median(n_nz))}  # fmt: skip
            for a, lab in zip(ALPHAS, ("05", "05_over_12"), strict=True):
                k = int((p < a).sum())
                lo, hi = clopper_pearson(k, sims)
                row[f"reject_{lab}"] = round(k / sims, 5)
                row[f"reject_{lab}_ci_low"] = round(lo, 5)
                row[f"reject_{lab}_ci_high"] = round(hi, 5)
                if true_mean != 0:
                    wrong = int(((p < a) & (direction == -np.sign(true_mean))).sum())
                    row[f"wrong_direction_{lab}"] = round(wrong / sims, 5)
            rows.append(row)
        print(f"  {dgp.name}: done", flush=True)
    return rows


def estimand_study(seed):
    """Population values of the mean gap and of the signed-rank functional
    theta = P(D1 + D2 > 0) - P(D1 + D2 < 0) (sign of the Walsh averages) for each DGP,
    estimated from 400,000 simulated scenarios."""
    rows = []
    rng = np.random.default_rng(seed)
    for dgp in NULLS + ALTS:
        se, stt, pe, pt = simulate(dgp, rng, 2000)  # 2000 x 200 = 400k scenarios
        D = (stt - se).ravel()
        nz = D[D != 0]
        # functional of the zero-dropped signed-rank test: sign balance of pairwise sums of
        # independent non-zero differences (Walsh averages, i != j)
        walsh = nz + rng.permutation(nz)
        theta = float((walsh > 0).mean() - (walsh < 0).mean())
        mean = float(D.mean())
        rows.append({
            "dgp": dgp.name, "kind": dgp.kind,
            "mean_gap_pp": round(100 * mean, 3),
            "theta_nonzero_walsh": round(theta, 4),
            "share_zero_differences": round(float((D == 0).mean()), 4),
            "median_difference": float(np.median(D)),
            "pseudomedian_nonzero": float(np.median(walsh) / 2),
            "direction_conflict": bool(abs(mean) > 1e-3 and abs(theta) > 0.01 and np.sign(mean) != np.sign(theta)),
        })  # fmt: skip
    return rows


def ci_study(seed):
    rows = []
    cells = []
    for rate in (0.005, 0.01, 0.02, 0.05, 0.10, 0.20):
        for gap in (0.0, 0.02, 0.05):
            for rho in (0.0, 0.8):
                cells.append((rate, gap, rho))
    for j, (rate, gap, rho) in enumerate(cells):
        rng = np.random.default_rng(seed + j)
        dgp = DGP(f"ci_{rate}_{gap}_{rho}", "ci", "", logit_re(rate, rate + gap, 2.5), rho=rho)
        se, stt, pe, pt = simulate(dgp, rng, SIMS_CI)
        D = stt - se
        true_gap = gap
        methods = {"t": t_interval(D), "mover_clustered_wilson": mover(se, stt)}
        if rho == 0.0:
            methods["percentile_bootstrap"] = percentile_boot(D, rng)
            methods["bootstrap_t"] = boot_t(D, rng)
        for name, (lo, hi) in methods.items():
            cover = (lo <= true_gap) & (true_gap <= hi)
            rows.append({
                "target": "gap", "base_rate": rate, "gap": gap, "rho": rho, "method": name, "n_sim": SIMS_CI,
                "coverage": round(float(cover.mean()), 4),
                "coverage_se": round(math.sqrt(max(cover.mean() * (1 - cover.mean()), 1e-12) / SIMS_CI), 4),
                "miss_below": round(float((hi < true_gap).mean()), 4), "miss_above": round(float((lo > true_gap).mean()), 4),
                "mean_width_pp": round(100 * float((hi - lo).mean()), 3),
                "degenerate": int((hi - lo <= 0).sum()),
            })  # fmt: skip
        # single per-response rate (target form)
        rate_t = rate + gap
        rmethods = {"clustered_wilson": clustered_wilson(stt)[1:]}
        if rho == 0.0:
            rmethods["percentile_bootstrap"] = boot_rate(stt, rng)
        for name, (lo, hi) in rmethods.items():
            cover = (lo <= rate_t) & (rate_t <= hi)
            rows.append({
                "target": "rate", "base_rate": rate_t, "gap": "", "rho": rho, "method": name, "n_sim": SIMS_CI,
                "coverage": round(float(cover.mean()), 4),
                "coverage_se": round(math.sqrt(max(cover.mean() * (1 - cover.mean()), 1e-12) / SIMS_CI), 4),
                "miss_below": round(float((hi < rate_t).mean()), 4), "miss_above": round(float((lo > rate_t).mean()), 4),
                "mean_width_pp": round(100 * float((hi - lo).mean()), 3),
                "degenerate": int((hi - lo <= 0).sum()),
            })  # fmt: skip
        print(f"  CI cell rate={rate} gap={gap} rho={rho}: done", flush=True)
    return rows


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    worst = check_signed_rank_equivalence(np.random.default_rng(1))
    print(f"signed-rank equivalence check: max |diff| = {worst}")
    print("Type I error:")
    write_csv(OUT / "type1_error.csv", rejection_study(NULLS, SIMS_NULL, 10_000))
    print("Power:")
    write_csv(OUT / "power.csv", rejection_study(ALTS, SIMS_ALT, 20_000))
    print("Estimand:")
    write_csv(OUT / "estimand.csv", estimand_study(30_000))
    print("Intervals:")
    write_csv(OUT / "ci_coverage.csv", ci_study(40_000))
    meta = {
        "n_scenarios": N, "samples_per_unit": K, "family": FAMILY, "alphas": list(ALPHAS),
        "sims_null": SIMS_NULL, "sims_alternative": SIMS_ALT, "sims_ci": SIMS_CI, "bootstrap_resamples": BOOT,
        "quick": QUICK, "signed_rank_equivalence_max_abs_diff": worst, "runtime_seconds": round(time.time() - t0),
        "numpy": np.__version__, "scipy": __import__("scipy").__version__,
        "dgps": [{"name": d.name, "kind": d.kind, "rho": d.rho, "description": d.description} for d in NULLS + ALTS],
    }  # fmt: skip
    (OUT / "run_metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
