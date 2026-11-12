"""Secondary model-based estimates (protocol §10, amended 2026-11-13).

The protocol's original secondary model, a random-intercept logistic GLMM
`harmful ~ form + (1 | scenario)`, has no frequentist implementation in statsmodels. It is
replaced by two models whose behaviour was checked in research/stats_validation/:

- conditional logistic regression stratified by scenario: the within-scenario log-odds ratio of
  the form effect (the same conditional estimand as the GLMM's fixed effect, without assuming a
  normal random intercept); scenarios with no outcome variation carry no information and drop out;
- GEE logistic with an exchangeable working correlation clustered by scenario: the marginal
  (population-averaged) log-odds ratio with robust standard errors.

Both are estimation, not confirmatory tests. Both act on per-response outcomes reconstructed from
units (share x n_samples harmful responses of n_samples). Fits that fail are reported, not hidden.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from app.v2.metrics import Unit


def _long_rows(pairs: list[tuple[Unit, Unit]], outcome: str):
    y, form, groups = [], [], []
    for g, (ref, tgt) in enumerate(pairs):
        for x, unit in ((0.0, ref), (1.0, tgt)):
            k = int(round(getattr(unit, outcome) * unit.n_samples))
            y += [1.0] * k + [0.0] * (unit.n_samples - k)
            form += [x] * unit.n_samples
            groups += [g] * unit.n_samples
    return np.array(y), np.array(form), np.array(groups)


def _result(name: str, beta: float, se: float, p: float, n_used: int, note: str = "") -> dict:
    ok = all(np.isfinite(v) for v in (beta, se, p))
    return {
        "model": name,
        "log_odds_ratio": beta if ok else math.nan,
        "odds_ratio": math.exp(beta) if ok else math.nan,
        "ci_low_or": math.exp(beta - 1.96 * se) if ok else math.nan,
        "ci_high_or": math.exp(beta + 1.96 * se) if ok else math.nan,
        "p_value": p if ok else math.nan,
        "n_clusters_used": n_used,
        "fit_ok": ok,
        "note": note,
    }


def conditional_logit(pairs: list[tuple[Unit, Unit]], outcome: str) -> dict:
    from statsmodels.discrete.conditional_models import ConditionalLogit

    y, form, groups = _long_rows(pairs, outcome)
    informative = {g for g in set(groups.tolist()) if 0 < y[groups == g].sum() < (groups == g).sum()}
    if not informative:
        return _result("conditional_logit", math.nan, math.nan, math.nan, 0, "no scenario with outcome variation")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            res = ConditionalLogit(y, form[:, None], groups=groups).fit(disp=0)
            return _result("conditional_logit", float(res.params[0]), float(res.bse[0]), float(res.pvalues[0]), len(informative))
        except Exception as exc:  # noqa: BLE001 - reported, never hidden
            return _result("conditional_logit", math.nan, math.nan, math.nan, len(informative), f"fit failed: {type(exc).__name__}")


def gee_logit(pairs: list[tuple[Unit, Unit]], outcome: str) -> dict:
    import statsmodels.api as sm

    y, form, groups = _long_rows(pairs, outcome)
    if y.sum() == 0 or y.sum() == len(y) or len(set(form.tolist())) < 2:
        return _result("gee_logit", math.nan, math.nan, math.nan, len(pairs), "outcome constant; model not estimable")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            res = sm.GEE(y, sm.add_constant(form), groups=groups, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
            return _result("gee_logit", float(res.params[1]), float(res.bse[1]), float(res.pvalues[1]), len(pairs))
        except Exception as exc:  # noqa: BLE001
            return _result("gee_logit", math.nan, math.nan, math.nan, len(pairs), f"fit failed: {type(exc).__name__}")


def model_based_effects(ref: dict[str, Unit], tgt: dict[str, Unit], outcome: str) -> list[dict]:
    pairs = [(ref[s], tgt[s]) for s in sorted(set(ref) & set(tgt)) if ref[s].ok and tgt[s].ok]
    return [conditional_logit(pairs, outcome), gee_logit(pairs, outcome)]
