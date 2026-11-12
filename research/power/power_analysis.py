"""Sample-size analysis for the VeriAudit v2 main study.

Design inputs come from the reconstructed v0.1 pilot
(results/v1_reconstruction/paired_tests.csv): discordant-pair probabilities for
the harmful-compliance outcome. Confirmatory family: 5 models x 3 non-English
forms = 15 paired tests (harmful compliance, target vs English), Holm-adjusted.
Power is computed at the Bonferroni level alpha/15, which is what the smallest
Holm p-value must clear, so it is conservative for every test in the family.

Run: PYTHONPATH=backend python research/power/power_analysis.py
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from app.v2.stats import mcnemar_power, wilson_interval

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

    for r in rows:
        if r["n_scenarios"] in (120, 150, 200):
            print(r)


if __name__ == "__main__":
    main()
