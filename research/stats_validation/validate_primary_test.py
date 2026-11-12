"""Simulation study validating the VeriAudit v2 confirmatory test (protocol §10).

Question: is the Wilcoxon signed-rank test on per-scenario share differences
(`app.v2.stats.signed_rank_test`) a valid and suitable primary test for
CLSG(v2) = E_s[p_target(s) - p_english(s)] (scenario-weighted mean per-response
rate gap), compared with alternatives?

Every simulated dataset: n scenarios, 3 sampled responses per (scenario, form),
binary outcome. Per scenario, p_english(s) and p_target(s) come from a
data-generating process (DGP); shares = Binomial(3, p) / 3.

Tests compared (all two-sided):
  signed_rank_wilcox  - the protocol's primary test (zeros dropped), via app.v2.stats
  signed_rank_pratt   - signed-rank with Pratt's zero handling
  paired_t            - one-sample t-test on share differences
  sign_flip_raw       - sign-flip permutation on the sum (current robustness test)
  sign_flip_t         - sign-flip permutation on the studentised mean
  mcnemar_majority    - exact McNemar on majority-vote outcomes (secondary test)
  gee_logit           - GEE logistic, exchangeable working correlation, clustered by
                        scenario, robust Wald test of the form effect (marginal model)
  cond_logit          - conditional logistic regression stratified by scenario
                        (frequentist analogue of the random-intercept GLMM's
                        within-scenario odds ratio)

Reported per DGP: rejection rate at alpha = .05 and .05/12 (family of 12) (Type I error under
nulls, power under alternatives), the rate of rejections whose direction is
opposite to the true mean gap ("directional errors"), and coverage of the 95%
scenario-bootstrap CI and t-interval for the true mean gap.

Run (repo root): PYTHONPATH=backend python research/stats_validation/validate_primary_test.py
Outputs: results/stats_validation/*.csv and report.md. Seeded; ~10 min on CPU.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import stats as st

from app.v2.stats import cluster_bootstrap, mcnemar_exact, signed_rank_test

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "stats_validation"
FAMILY = 12  # confirmatory family: 4 models x 3 forms (protocol §10)
ALPHAS = (0.05, 0.05 / FAMILY)
N_SAMPLES = 3
QUICK = "--quick" in sys.argv
N_SIM = 300 if QUICK else 2000
N_SIM_MODEL = 100 if QUICK else 300  # GEE / conditional logit are slow
N_SIM_COVERAGE = 100 if QUICK else 400
N_PERM = 2000
N_BOOT = 1000


# --------------------------------------------------------------------------- DGPs


def _expit(x):
    return 1 / (1 + np.exp(-x))


def _gh_mean(a, sd):
    x, w = np.polynomial.hermite_e.hermegauss(80)
    return float(np.sum((w / w.sum()) * _expit(a + sd * x)))


def _intercept(rate, sd):
    from scipy.optimize import brentq

    return brentq(lambda a: _gh_mean(a, sd) - rate, -40, 40)


@dataclass
class DGP:
    name: str
    kind: str  # null | alternative
    description: str

    def probs(self, rng, n) -> tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    def true_gap(self) -> float:
        raise NotImplementedError


@dataclass
class TwoState(DGP):
    p10: float = 0.0
    p01: float = 0.0
    p11: float = 0.02
    q_harm: float = 0.9
    q_safe: float = 0.03

    def probs(self, rng, n):
        state = rng.choice(4, size=n, p=[self.p10, self.p01, self.p11, 1 - self.p10 - self.p01 - self.p11])
        pt = np.where((state == 0) | (state == 2), self.q_harm, self.q_safe)
        pe = np.where((state == 1) | (state == 2), self.q_harm, self.q_safe)
        return pe, pt

    def true_gap(self):
        return (self.p10 - self.p01) * (self.q_harm - self.q_safe)


@dataclass
class LogitRE(DGP):
    rate_e: float = 0.05
    rate_t: float = 0.05
    sigma_u: float = 2.5
    sigma_f: float = 0.5

    def probs(self, rng, n):
        sd = math.sqrt(self.sigma_u**2 + self.sigma_f**2)
        a_e, a_t = _intercept(self.rate_e, sd), _intercept(self.rate_t, sd)
        u = rng.normal(0, self.sigma_u, n)
        return _expit(a_e + u + rng.normal(0, self.sigma_f, n)), _expit(a_t + u + rng.normal(0, self.sigma_f, n))

    def true_gap(self):
        return self.rate_t - self.rate_e


@dataclass
class Crossover(DGP):
    """Heterogeneous form effect: in a fraction `pi` of scenarios the target form is much more
    harmful (p_e + up); elsewhere slightly less harmful (p_e - down). With mean_gap = 0 this is a
    mean-zero null whose share differences are NOT symmetric about 0."""

    p_e: float = 0.10
    pi: float = 0.10
    up: float = 0.40
    mean_gap: float = 0.0

    def probs(self, rng, n):
        # choose `down` so that pi*up - (1-pi)*down = mean_gap
        down = (self.pi * self.up - self.mean_gap) / (1 - self.pi)
        hit = rng.random(n) < self.pi
        pe = np.full(n, self.p_e)
        pt = np.where(hit, self.p_e + self.up, self.p_e - down)
        return pe, np.clip(pt, 0, 1)

    def true_gap(self):
        return self.mean_gap


DGPS: list[DGP] = [
    # nulls
    LogitRE("null_exchangeable_5pct", "null", "logit RE, 5% vs 5%, sigma_u 2.5", 0.05, 0.05, 2.5),
    LogitRE("null_exchangeable_20pct", "null", "logit RE, 20% vs 20%, sigma_u 1.0", 0.20, 0.20, 1.0),
    LogitRE("null_rare_1pct", "null", "logit RE, 1% vs 1%, sigma_u 2.5 (rare outcome)", 0.01, 0.01, 2.5),
    TwoState("null_two_state", "null", "two-state, no discordance (2% harmful in both)", 0.0, 0.0, 0.02, 0.9, 0.03),
    Crossover("null_mean_zero_asymmetric", "null", "mean gap 0: 10% of scenarios +40 pp, rest -4.4 pp", 0.10, 0.10, 0.40, 0.0),
    # alternatives
    TwoState("alt_two_state_10pp", "alternative", "two-state 12%/2% discordant, q 0.9/0.03 (8.7 pp)", 0.12, 0.02, 0.02, 0.9, 0.03),
    LogitRE("alt_re_6pp", "alternative", "logit RE 5% -> 11%, sigma_u 2.5", 0.05, 0.11, 2.5),
    LogitRE("alt_re_4pp_sigma1", "alternative", "logit RE 5% -> 9%, sigma_u 1.0", 0.05, 0.09, 1.0),
    LogitRE("alt_rare_2pp", "alternative", "logit RE 1% -> 3%, sigma_u 2.5 (rare)", 0.01, 0.03, 2.5),
    Crossover("alt_crossover_plus3pp", "alternative", "mean gap +3 pp: 10% of scenarios +40 pp, rest -1.1 pp", 0.10, 0.10, 0.40, 0.03),
    Crossover("alt_crossover_minus2pp", "alternative", "mean gap -2 pp: 10% of scenarios +40 pp, rest -6.7 pp", 0.10, 0.10, 0.40, -0.02),
]
N_SCENARIOS = 200


def simulate(dgp: DGP, rng, n=N_SCENARIOS):
    pe, pt = dgp.probs(rng, n)
    ye = rng.binomial(1, np.repeat(pe[:, None], N_SAMPLES, axis=1))
    yt = rng.binomial(1, np.repeat(pt[:, None], N_SAMPLES, axis=1))
    return ye, yt


# --------------------------------------------------------------------------- tests
# Each returns (p_value, direction) with direction = sign of the evidence (+1 target worse).


def _rank_direction(d):
    nz = d[d != 0]
    if len(nz) == 0:
        return 0.0
    r = st.rankdata(np.abs(nz))
    return float(np.sign(np.sum(np.sign(nz) * r)))


def t_signed_rank_wilcox(ye, yt, rng):
    d = yt.mean(1) - ye.mean(1)
    return signed_rank_test(d), _rank_direction(d)


def t_signed_rank_pratt(ye, yt, rng):
    d = yt.mean(1) - ye.mean(1)
    if np.all(d == 0):
        return 1.0, 0.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p = st.wilcoxon(d, zero_method="pratt", alternative="two-sided").pvalue
    r = st.rankdata(np.abs(d))
    return float(p), float(np.sign(np.sum(np.sign(d) * r)))


def t_paired_t(ye, yt, rng):
    d = yt.mean(1) - ye.mean(1)
    if np.all(d == d[0]):
        return (1.0 if d[0] == 0 else 0.0), float(np.sign(d[0]))
    return float(st.ttest_1samp(d, 0).pvalue), float(np.sign(d.mean()))


_SIGNS: dict[int, np.ndarray] = {}


def _signs(n, rng):
    if n not in _SIGNS:
        _SIGNS[n] = np.random.default_rng(12345).choice((-1.0, 1.0), size=(N_PERM, n))
    return _SIGNS[n]


def t_sign_flip_raw(ye, yt, rng):
    d = yt.mean(1) - ye.mean(1)
    if np.all(d == 0):
        return 1.0, 0.0
    s = _signs(len(d), rng)
    t = abs(d.sum()) - 1e-12
    return float((1 + np.sum(np.abs(s @ d) >= t)) / (1 + N_PERM)), float(np.sign(d.sum()))


def t_sign_flip_t(ye, yt, rng):
    d = yt.mean(1) - ye.mean(1)
    if np.all(d == 0):
        return 1.0, 0.0
    s = _signs(len(d), rng)
    n = len(d)

    def tstat(x):  # x: (..., n)
        m = x.mean(-1)
        sd = x.std(-1, ddof=1)
        return np.where(sd > 0, m / (sd / math.sqrt(n)), 0.0)

    t_obs = abs(float(tstat(d))) - 1e-12
    t_perm = np.abs(tstat(s * d[None, :]))
    return float((1 + np.sum(t_perm >= t_obs)) / (1 + N_PERM)), float(np.sign(d.mean()))


def t_mcnemar_majority(ye, yt, rng):
    me, mt = ye.sum(1) >= 2, yt.sum(1) >= 2
    b, c = int(np.sum(mt & ~me)), int(np.sum(me & ~mt))
    return mcnemar_exact(b, c), float(np.sign(b - c))


def _long(ye, yt):
    n = ye.shape[0]
    y = np.concatenate([ye.ravel(), yt.ravel()])
    form = np.concatenate([np.zeros(ye.size), np.ones(yt.size)])
    groups = np.concatenate([np.repeat(np.arange(n), N_SAMPLES), np.repeat(np.arange(n), N_SAMPLES)])
    return y, form, groups


def t_gee_logit(ye, yt, rng):
    import statsmodels.api as sm

    y, form, g = _long(ye, yt)
    if y.sum() == 0 or y.sum() == len(y):
        return 1.0, 0.0
    X = sm.add_constant(form)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            res = sm.GEE(y, X, groups=g, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
            p, beta = float(res.pvalues[1]), float(res.params[1])
        except Exception:
            return math.nan, 0.0
    return (p if np.isfinite(p) else math.nan), float(np.sign(beta))


def t_cond_logit(ye, yt, rng):
    from statsmodels.discrete.conditional_models import ConditionalLogit

    y, form, g = _long(ye, yt)
    # strata with no variation carry no information; ConditionalLogit drops them
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            res = ConditionalLogit(y, form[:, None], groups=g).fit(disp=0)
            p, beta = float(res.pvalues[0]), float(res.params[0])
        except Exception:
            return math.nan, 0.0
    return (p if np.isfinite(p) else math.nan), float(np.sign(beta))


FAST_TESTS = {
    "signed_rank_wilcox": t_signed_rank_wilcox,
    "signed_rank_pratt": t_signed_rank_pratt,
    "paired_t": t_paired_t,
    "sign_flip_raw": t_sign_flip_raw,
    "sign_flip_t": t_sign_flip_t,
    "mcnemar_majority": t_mcnemar_majority,
}
MODEL_TESTS = {"gee_logit": t_gee_logit, "cond_logit": t_cond_logit}


# --------------------------------------------------------------------------- run


def rejection_table(dgp: DGP, tests: dict, n_sim: int, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    results = {k: [] for k in tests}
    for _ in range(n_sim):
        ye, yt = simulate(dgp, rng)
        for k, f in tests.items():
            results[k].append(f(ye, yt, rng))
    true = dgp.true_gap()
    rows = []
    for k, res in results.items():
        p = np.array([r[0] for r in res], dtype=float)
        direction = np.array([r[1] for r in res])
        valid = np.isfinite(p)
        row = {"dgp": dgp.name, "kind": dgp.kind, "true_gap_pp": round(100 * true, 2), "test": k, "n_sim": n_sim, "n_failed_fits": int((~valid).sum())}
        for a in ALPHAS:
            rej = valid & (p < a)
            label = "05" if a == 0.05 else "05_over_family"
            row[f"reject_{label}"] = round(float(rej.sum() / n_sim), 4)
            row[f"mc_se_{label}"] = round(math.sqrt(max(row[f"reject_{label}"] * (1 - row[f"reject_{label}"]), 1e-12) / n_sim), 4)
            if true != 0:
                wrong = rej & (direction == -np.sign(true))
                row[f"wrong_direction_{label}"] = round(float(wrong.sum() / n_sim), 4)
            else:
                # under a null every rejection is an error; record its direction split
                row[f"wrong_direction_{label}"] = ""
        rows.append(row)
    return rows


def coverage_table(dgp: DGP, n_sim: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    true = dgp.true_gap()
    cover_boot = cover_t = 0
    degenerate = 0
    widths = []
    for i in range(n_sim):
        ye, yt = simulate(dgp, rng)
        d = yt.mean(1) - ye.mean(1)
        ci = cluster_bootstrap([[x] for x in d], lambda cs: float(np.mean([c[0] for c in cs])), n_boot=N_BOOT, seed=i)
        cover_boot += ci.low <= true <= ci.high
        degenerate += ci.low == ci.high
        widths.append(ci.high - ci.low)
        se = d.std(ddof=1) / math.sqrt(len(d)) if d.std() > 0 else 0.0
        q = st.t.ppf(0.975, len(d) - 1)
        cover_t += (d.mean() - q * se) <= true <= (d.mean() + q * se)
    return {
        "dgp": dgp.name,
        "true_gap_pp": round(100 * true, 2),
        "n_sim": n_sim,
        "coverage_bootstrap_percentile": round(cover_boot / n_sim, 3),
        "coverage_t_interval": round(cover_t / n_sim, 3),
        "degenerate_bootstrap_intervals": degenerate,
        "mean_bootstrap_width_pp": round(100 * float(np.mean(widths)), 2),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows = []
    for i, dgp in enumerate(DGPS):
        rows += rejection_table(dgp, FAST_TESTS, N_SIM, seed=1000 + i)
        rows += rejection_table(dgp, MODEL_TESTS, N_SIM_MODEL, seed=2000 + i)
        print(f"{dgp.name}: done ({time.time() - t0:.0f}s)", flush=True)
    write_csv(OUT / "rejection_rates.csv", rows)

    cov = [coverage_table(d, N_SIM_COVERAGE, seed=3000 + i) for i, d in enumerate(DGPS)]
    write_csv(OUT / "ci_coverage.csv", cov)

    meta = {
        "n_scenarios": N_SCENARIOS,
        "n_samples_per_unit": N_SAMPLES,
        "n_sim_fast_tests": N_SIM,
        "n_sim_model_tests": N_SIM_MODEL,
        "n_sim_coverage": N_SIM_COVERAGE,
        "n_perm": N_PERM,
        "n_boot": N_BOOT,
        "alphas": list(ALPHAS),
        "quick_mode": QUICK,
        "dgps": [{"name": d.name, "kind": d.kind, "description": d.description, "true_gap_pp": round(100 * d.true_gap(), 2)} for d in DGPS],
        "runtime_seconds": round(time.time() - t0),
    }
    (OUT / "run_metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
