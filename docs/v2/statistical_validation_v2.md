# Statistical validation, round 2: estimand, Type I error, power, intervals

Script: `research/stats_validation/validate_v2.py`. Outputs: `results/stats_validation/v2/`, which
holds `type1_error.csv`, `power.csv`, `estimand.csv`, `ci_coverage.csv` and `run_metadata.json`.
Settings were n = 200 scenarios with 3 samples per unit. There were 20,000 simulations per null,
4,000 per alternative and 2,000 per interval cell; bootstraps used 1,000 resamples. Runtime was
284 s. Every rejection rate carries a Clopper–Pearson 95% interval for its Monte Carlo error. The
vectorised signed-rank implementation was checked against `scipy.stats.wilcoxon`: max |Δp| = 0.

**Outcome: the primary test changes from Wilcoxon signed-rank to the paired t-test.** The
interval becomes the t interval, which is its dual. It is reported as an *approximate* 95%
interval. This is protocol amendment A6 (§15), made before any data collection.

## 1. What the signed-rank test actually tests

The test is computed as in `stats.signed_rank_test`: zero differences are dropped, and
`scipy.stats.wilcoxon` runs with `method="auto"`. With scipy 1.18, that means:

- exact null distribution if there are no ties and n ≤ 50;
- an exhaustive sign-flip permutation if there are ties and n ≤ 13;
- otherwise the normal approximation with tie correction and **no** continuity correction.

Differences of 3-sample shares take at most 7 values (−1, −⅔, …, 1), so ties are the norm and the
normal approximation applies.

- **Null hypothesis.** The non-zero differences are symmetric about 0.
- **Functional it is consistent against.** θ = P(Dᵢ + Dⱼ > 0) − P(Dᵢ + Dⱼ < 0), taken over pairs of
  non-zero differences (the Walsh sums). Equivalently, the sign of the pseudomedian of the non-zero
  differences.
- **What it is not.** It is not a test of the mean difference (CLSG(v2)). It is not a test of the
  median either: in every scenario simulated, the median difference is 0, because 55–98% of
  differences are zero.

θ and the mean can have opposite signs, as `estimand.csv` shows:

| Scenario | Mean gap | θ (non-zero Walsh) | Signed-rank behaviour |
|---|---|---|---|
| N11 (9% of scenarios 0→⅔, 6% 1→0) | 0 | −0.28 | Rejects **25.5%** of the time at α = .05 [24.9, 26.2]; 5.1% at α = .05/12 |
| A8 (12% 0→⅔, 6% 1→0) | +2 pp | −0.12 | Significant in the **wrong direction** 7.8% of the time at α = .05 |
| A9 (30% 0→⅔, 15% 1→0) | +5 pp | −0.11 | Wrong direction 17.6% at α = .05; 3.3% at α = .05/12 |

These patterns are plausible here. A model might partially comply on many prompts in one form while
fully complying on a few prompts in the other. The earlier validation used nulls that were symmetric
by construction, or asymmetric only in ways that left θ near 0, so it did not find this. **The paper
must not describe the signed-rank test as a test of CLSG or of a mean.** It is kept as a secondary,
descriptive statistic.

## 2. Type I error, with Monte Carlo uncertainty

There were eleven nulls with mean gap 0:

- logit random effects at base rates 0.5%, 1%, 5% and 20%;
- within-unit correlation ρ = 0.8;
- three asymmetric mean-zero mixtures;
- the conflict null N11.

| Test | α = .05: range over nulls | α = .05/12 = .00417: range | Notes |
|---|---|---|---|
| Paired t | 0.036–0.053 | 0.0001–0.0045 | Highest at α = .05: N8 0.0534 [0.0503, 0.0566], slightly liberal. At .05/12 every Monte Carlo interval covers or lies below .00417, the highest being N11 at 0.0045 [0.0036, 0.0055]. Conservative at rare rates (N4 0.036) |
| Signed-rank | 0.006–**0.255** | up to **0.051** | Invalid for the mean null (N11) |
| McNemar (majority) | 0–**0.239** | up to 0.042 | Different estimand (N7 0.239) |

The paired t-test holds its level for the mean null across all eleven processes, within Monte
Carlo error at the family level. Its worst case at α = .05 is about 0.3 pp above nominal.

## 3. Power at α = .05/12 (one test of the Holm family; 4,000 simulations, SE ≤ 0.008)

| Alternative | Paired t | Signed-rank | McNemar |
|---|---|---|---|
| A1: 5% → 11%, σᵤ = 2.5 | **0.934** | 0.916 | 0.421 |
| A2: 5% → 9%, σᵤ = 1 | 0.429 | 0.420 | 0.046 |
| A3: 1% → 3% (rare) | 0.316 | 0.310 | 0.004 |
| A4: 0.5% → 2% (rare) | 0.174 | 0.191 | 0.000 |
| A5: A1 with within-unit ρ = 0.8 | 0.493 | 0.439 | 0.317 |
| A6: A1 with ρ = 0.95 | 0.424 | 0.388 | 0.326 |
| A7: heterogeneous (10% of scenarios +40 pp, rest −1.1 pp; mean +3 pp) | 0.078 | 0.076 | 0.109 |
| A8 / A9: direction conflict (+2 / +5 pp) | 0.028 / 0.071 | 0.012 / 0.034 (wrong direction 0.8% / 3.3%) | 0.155 / 0.601 |

The paired t-test never rejected in the wrong direction at α = .05/12 in any alternative (≤ 0.0008
at α = .05).

What follows for n = 200:

1. **Within-unit correlation is the dominant risk.** If a model gives the same answer to all three
   samples (ρ ≈ 0.8–0.95), the three samples carry about one sample's information. Power for a 6 pp
   gap then falls from 0.93 to 0.42–0.49. The calibration pilot must estimate ρ (§12).
2. **Rare outcomes.** At base rates of 0.5–1%, n = 200 detects only gaps of several times the base
   rate: a 1% → 3% gap has power 0.32. Strong, well-aligned models will often be in this regime for
   H1. A non-significant result there is uninformative, and the minimum detectable effect must be
   reported next to it.
3. **Heterogeneity.** A gap concentrated in a few scenarios (A7) is nearly undetectable by any test
   on means at this n. Per-category results and the scenario-level bounds are descriptive.
4. **Ties and zeros.** They make the signed-rank test's functional diverge from the mean (§1). They
   do not invalidate the t-test, whose level held at 96–98% zero differences (N3, N4), though it is
   conservative there.

## 4. Confidence interval coverage (nominal 0.95; 2,000 simulations per cell, SE ≈ 0.005)

The grid covered base rates {0.5, 1, 2, 5, 10, 20}%, gaps {0, 2, 5} pp and ρ ∈ {0, 0.8}.

**Gap interval (CLSG):**

| Method | Minimum | Mean | Mean width | Worst cell |
|---|---|---|---|---|
| **t interval (adopted)** | **0.921** | 0.947 | 5.8 pp | 0.5%, +2 pp, ρ = 0.8: misses below 7.2%, above 0.8% |
| Percentile cluster bootstrap (ρ = 0 only) | 0.934 | 0.947 | 4.6 pp | 0.5%, +2 pp |
| Bootstrap-t (ρ = 0 only) | 0.836 | 0.932 | 4.7 pp | 0.5%, gap 0 |
| MOVER (clustered Wilson) | 0.900 | 0.948 | 6.2 pp | 0.5–1%, gap 0, ρ = 0.8 |

At base rates of 2% and above, the t interval covers 0.932–0.955. At 0.5–1% with a non-zero gap,
it covers 0.921–0.938, and the misses are one-sided: the interval lies **below** the true gap. The
lower bound is therefore not optimistic, but the upper bound can understate a gap. None of the
methods examined reaches 0.95 in every cell. MOVER does better at rare non-zero gaps but worse at
rare null cells with correlation. The bootstrap intervals were run only at ρ = 0, because of runtime.

The t interval is adopted because it is the interval dual to the primary test: it excludes 0 exactly
when the unadjusted test rejects. It is reported as an **approximate 95% interval**. The paper states
its simulated coverage (0.92–0.97) and does not call it a reliable 95% interval at base rates of
≤ 1–2%. The percentile cluster bootstrap is kept as a sensitivity interval (`boot_ci_*`).

**Rate interval (per-cell HCR/ORR):**

- Clustered Wilson: minimum 0.851, at 1% with ρ = 0.8.
- Percentile bootstrap: minimum 0.903, at 1%.

Both under-cover below 2–5%. Per-cell rates are descriptive and their intervals are labelled
approximate. Below 2%, the count of harmful responses and of scenarios with any harmful response is
reported instead of relying on the interval.

## 5. Changes made

- `stats.mean_t_interval` (new); the `stats.signed_rank_test` docstring now states the scipy method
  rules and the functional.
- `metrics._compare` / `paired_family`:
  - `p_holm` is Holm over `p_paired_t`;
  - `ci_low_pp`/`ci_high_pp` hold the t interval;
  - the bootstrap interval moves to `boot_ci_*`;
  - the signed-rank result becomes `p_signed_rank` / `p_signed_rank_holm` (descriptive).
- `transformation_effects`: BH over the paired t.
- Analysis report table: the paired t p-value is primary; signed-rank is labelled descriptive.
- Protocol §10 and amendment A6; power section §4.3 updated with ρ and rare-rate results.

## 6. Limitations of this validation

- The data-generating processes are assumptions. In particular, the copy-first sampling used for ρ
  is one of many ways to induce within-unit correlation.
- The 12 tests were not simulated jointly with realistic cross-model correlation. Holm controls the
  FWER under any dependence, so this affects power, not validity.
- Label noise from judges and human resolution is not modelled. Misclassification that differs by
  form, for example if judges are worse in Urdu, would bias the gap. That is a measurement problem
  addressed by the human validation sample (§8), not by the test.
- The coverage grid stops at 20% base rates and 5 pp gaps.
