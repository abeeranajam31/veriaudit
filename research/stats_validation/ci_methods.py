"""Coverage of alternative 95% CIs for the mean share difference (CLSG v2) at low rates.

Companion to validate_primary_test.py (same DGPs). Compares the scenario percentile bootstrap
(used in app.v2.metrics), BCa, basic bootstrap and the t-interval. 400 simulations per DGP,
so a coverage estimate has Monte Carlo SE ~0.011.

Run (repo root): PYTHONPATH=backend python research/stats_validation/ci_methods.py
Output: results/stats_validation/ci_methods.csv
"""

from __future__ import annotations

import csv
import sys
import warnings
from pathlib import Path

import numpy as np
from scipy import stats as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_primary_test import DGPS, OUT, simulate  # noqa: E402

TARGETS = ["null_rare_1pct", "null_exchangeable_5pct", "alt_rare_2pp", "alt_re_6pp"]
N_SIM = 400
N_RESAMPLES = 2000


def main() -> None:
    rows = []
    for d in [x for x in DGPS if x.name in TARGETS]:
        rng = np.random.default_rng(99)
        true = d.true_gap()
        hits = {"percentile": 0, "bca": 0, "basic": 0, "t": 0}
        nonzero = []
        for i in range(N_SIM):
            ye, yt = simulate(d, rng)
            dd = yt.mean(1) - ye.mean(1)
            nonzero.append(int(np.sum(dd != 0)))
            for m in ("percentile", "BCa", "basic"):
                if np.all(dd == dd[0]):
                    lo = hi = dd[0]
                else:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        lo, hi = st.bootstrap((dd,), np.mean, n_resamples=N_RESAMPLES, method=m, random_state=i).confidence_interval
                hits[m.lower()] += bool(np.isfinite(lo) and lo <= true <= hi)
            se = dd.std(ddof=1) / np.sqrt(len(dd))
            hits["t"] += bool(abs(dd.mean() - true) <= st.t.ppf(0.975, len(dd) - 1) * se)
        rows.append(
            {
                "dgp": d.name,
                "true_gap_pp": round(100 * true, 2),
                "n_sim": N_SIM,
                "median_nonzero_differences": int(np.median(nonzero)),
                **{f"coverage_{k}": round(v / N_SIM, 3) for k, v in hits.items()},
            }
        )
        print(rows[-1], flush=True)
    with (OUT / "ci_methods.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
