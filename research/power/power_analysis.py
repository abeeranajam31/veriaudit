"""Sample-size analysis for the VeriAudit v2 main study.

Design inputs come from the reconstructed v0.1 pilot
(results/v1_reconstruction/paired_tests.csv): discordant-pair probabilities for
the harmful-compliance outcome. Confirmatory family: 5 models x 3 non-English
forms = 15 paired tests (harmful compliance, target vs English), Holm-adjusted.
Power is computed at the Bonferroni level alpha/15, which is what the smallest
Holm p-value must clear, so it is conservative for every test in the family.

Two analyses:

1. power_mcnemar.csv - McNemar on noise-free scenario-level outcomes (original sizing, v1.0).
2. power_with_sampling_noise.csv - amendment 2026-11-12. Each unit has 3 sampled responses that
   need not agree. A scenario's latent state in each form is drawn as in (1) (plus P(harmful in
   both) = P11); each response is then harmful with probability q_harm in a harmful state and
   q_safe otherwise. On the same simulated data we compute power of the primary test (exact
   McNemar on majority-vote outcomes) and the secondary test (Wilcoxon signed-rank on
   per-scenario differences of sample shares). The q values are assumptions, to be replaced by
   estimates from the calibration pilot.

Run: PYTHONPATH=backend python research/power/power_analysis.py
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from app.v2.stats import mcnemar_power, paired_share_power, wilson_interval

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "power"
FAMILY = 15
ALPHA = 0.05
N_GRID = [60, 90, 120, 150, 180, 200, 240, 300]

# (label, p_target_only, p_english_only): probability a scenario is harmful only in the
# target form / only in English. Net gap = p10 - p01.
SCENARIOS = [
    ("pilot-like large gap (Aya x Urdu: 12/30, 0/30)", 0.40, 0.0),
    ("pilot-like moderate gap (Aya x Roman Urdu: 9/30, 0/30)", 0.30, 0.0),
    ("pilot-like small gap (Qwen3 x Urdu: 4/30, 1/30)", 4 / 30, 1 / 30),
    ("smallest effect of interest: 10 pp net, noisy (12% vs 2%)", 0.12, 0.02),
    ("smallest effect of interest: 10 pp net, very noisy (15% vs 5%)", 0.15, 0.05),
    ("7.5 pp net (10% vs 2.5%)", 0.10, 0.025),
]


# P(scenario harmful in both English and target) for the noise simulation; v0.1 English harmful
# rates were 0/30 and 1/30, so this is small.
P11 = 0.02
# (label, q_harm, q_safe): within-unit response consistency assumptions
CONSISTENCY = [
    ("high (q_harm 0.95, q_safe 0.02)", 0.95, 0.02),
    ("moderate (q_harm 0.90, q_safe 0.03)", 0.90, 0.03),
    ("low (q_harm 0.75, q_safe 0.10)", 0.75, 0.10),
]
NOISE_N_GRID = [120, 150, 200, 240, 300]
NOISE_SIMS = 1500


def half_width(p: float, n: int) -> float:
    w = wilson_interval(round(p * n), n)
    return 100 * (w.high - w.low) / 2


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, p10, p01 in SCENARIOS:
        for n in N_GRID:
            rows.append(
                {
                    "scenario": label,
                    "net_gap_pp": round(100 * (p10 - p01), 1),
                    "n_scenarios": n,
                    "power_bonferroni_15": round(mcnemar_power(n, p10, p01, alpha=ALPHA / FAMILY, n_sim=20000, seed=7), 3),
                    "power_unadjusted": round(mcnemar_power(n, p10, p01, alpha=ALPHA, n_sim=20000, seed=7), 3),
                }
            )
    with (OUT / "power_mcnemar.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    precision = [{"rate": p, "n": n, "wilson_half_width_pp": round(half_width(p, n), 1)} for p in (0.05, 0.1, 0.2, 0.3, 0.5) for n in N_GRID]
    with (OUT / "precision_wilson.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(precision[0]))
        w.writeheader()
        w.writerows(precision)

    # cost model: generations = scenarios x 2 intents x forms x models x samples
    cost = {}
    for n in N_GRID:
        base_forms = 4
        controlled = 6  # extra controlled transformations on a 1/3 subset (see protocol)
        prompts = n * 2 * base_forms + math.ceil(n / 3) * 2 * controlled
        cost[n] = {"prompts": prompts, "generations_5_models_3_samples": prompts * 5 * 3}
    (OUT / "cost_model.json").write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")

    noise_rows = []
    for label, p10, p01 in SCENARIOS:
        for c_label, q_h, q_s in CONSISTENCY:
            for n in NOISE_N_GRID:
                res = paired_share_power(n, p10, p01, P11, q_h, q_s, alphas=(ALPHA / FAMILY, ALPHA), n_sim=NOISE_SIMS, seed=7)
                noise_rows.append(
                    {
                        "scenario": label,
                        "scenario_level_net_gap_pp": round(100 * (p10 - p01), 1),
                        "consistency": c_label,
                        "expected_response_level_gap_pp": round(100 * (p10 - p01) * (q_h - q_s), 1),
                        "n_scenarios": n,
                        "power_mcnemar_majority_bonferroni_15": round(res["mcnemar_majority"][0], 3),
                        "power_signed_rank_bonferroni_15": round(res["signed_rank"][0], 3),
                        "power_mcnemar_majority_unadjusted": round(res["mcnemar_majority"][1], 3),
                        "power_signed_rank_unadjusted": round(res["signed_rank"][1], 3),
                    }
                )
    with (OUT / "power_with_sampling_noise.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(noise_rows[0]))
        w.writeheader()
        w.writerows(noise_rows)

    for r in rows:
        if r["n_scenarios"] in (120, 150, 200):
            print(r)
    for r in noise_rows:
        if r["n_scenarios"] == 200 and "smallest effect" in r["scenario"]:
            print(r)


if __name__ == "__main__":
    main()
