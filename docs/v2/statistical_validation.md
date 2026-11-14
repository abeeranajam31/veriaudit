# Statistical validation of the primary test

> **Superseded in part (2026-11-13, protocol amendment A6).** A second round of validation
> (`statistical_validation_v2.md`) found that the signed-rank test does not test the mean gap: under a
> mean-zero null with a negative signed-rank functional it rejected 25.5% of the time at α = .05. The
> primary test is now the paired t-test, with its t interval. The nulls below are all ones where the
> signed-rank functional is close to 0, which is why this round did not detect the problem. This
> document is kept as a record.

Status (original): **validated by simulation under the planning assumptions below; not yet checked against real
data.** Produced 2026-11-13 for protocol v1.1 §10. All numbers come from
`results/stats_validation/` (tables rendered in `report.md` by `make_report.py`); every simulation is
seeded and reproducible with `research/stats_validation/validate_primary_test.py` and `ci_methods.py`.

## 1. What is being tested

**Design.** For a model, each of n = 200 scenarios yields two units (English, target form). Each unit
has 3 sampled responses with a binary outcome (harmful compliance for H1; refusal of a benign
contrast for H2). Unit share = harmful responses / 3.

**Estimand.** CLSG(v2) = E_s[p_target(s) − p_english(s)], the scenario-weighted mean per-response rate
gap, where p_f(s) is the probability that a response to scenario *s* in form *f* has the outcome.
Its estimate is the mean of the per-scenario share differences D_s = share_target(s) − share_english(s),
which is unbiased because each share is unbiased for its p.

**Primary test** (`app.v2.stats.signed_rank_test`). Two-sided Wilcoxon signed-rank test on the D_s.
Zero differences are dropped (`zero_method="wilcox"`). With 3 samples, D_s takes few distinct values
(multiples of ⅓), so ties are the norm and scipy's tie-corrected normal approximation applies (no
continuity correction). Scenarios are independent; within-scenario dependence is handled by pairing.

**What it actually tests.** The null hypothesis of the signed-rank test is that D_s is symmetric about
0. That is implied when the two forms are exchangeable within each scenario (the natural "no form
effect" null), but it is not the same as "mean gap = 0". A form effect that is large in a few
scenarios and slightly negative elsewhere can have mean 0 without symmetric differences. So the
simulation includes such a null, and the protocol adds a paired t-test (which tests the mean) as a
sensitivity analysis.

**Multiplicity.** Holm over each confirmatory family of 12 tests (4 models × 3 forms). Tests within a
model share the English reference and are positively dependent; Holm is valid under any dependence.

## 2. Simulation design

Eleven data-generating processes (DGPs), n = 200 scenarios, 3 samples per unit. 2,000 simulations for
the rank, permutation, t and McNemar tests (Monte Carlo SE ≈ 0.005 at α = .05, ≈ 0.0014 at α = .05/12);
300 for GEE and conditional logit; 400 for interval coverage.

| DGP | Type | Description |
|---|---|---|
| null_exchangeable_5pct / _20pct | null | logit random effects, equal rates (5%, σ_u 2.5; 20%, σ_u 1.0), form-specific noise σ 0.5 |
| null_rare_1pct | null | 1% in both forms (rare outcome) |
| null_two_state | null | two-state model, no discordant scenarios |
| null_mean_zero_asymmetric | null | mean gap 0, but +40 pp in 10% of scenarios and −4.4 pp elsewhere (asymmetric) |
| alt_two_state_10pp | alternative | effect concentrated in 12% vs 2% discordant scenarios |
| alt_re_6pp, alt_re_4pp_sigma1 | alternative | effect spread over all scenarios |
| alt_rare_2pp | alternative | 1% → 3% |
| alt_crossover_plus3pp / _minus2pp | alternative | heterogeneous effects with a small net mean of +3 / −2 pp |

Tests compared: signed-rank (wilcox zeros, the primary test), signed-rank with Pratt zeros, paired t,
sign-flip permutation (studentised and raw), exact McNemar on majority votes, GEE logistic (exchangeable,
scenario clusters), and conditional logistic regression stratified by scenario.

## 3. Results

### 3.1 Type I error (rejection rate under the five nulls, α = .05)

| Null | signed-rank (primary) | Pratt | paired t | sign-flip | McNemar | GEE | cond. logit |
|---|---|---|---|---|---|---|---|
| exchangeable 5% | 0.050 | 0.050 | 0.050 | 0.036 | 0.014 | 0.063 | 0.063 |
| exchangeable 20% | 0.057 | 0.051 | 0.060 | 0.049 | 0.034 | 0.033 | 0.047 |
| rare 1% | 0.017 | 0.048 | 0.046 | 0.016 | 0.001 | 0.037 | 0.030 |
| two-state | 0.052 | 0.051 | 0.056 | 0.036 | 0.000 | 0.040 | 0.040 |
| mean-zero asymmetric | 0.049 | **0.081** | 0.046 | 0.037 | **0.227** | 0.027 | 0.060 |

At the family level (α = .05/12) see §3.4.

- **The primary test holds its level** in every null (largest 0.057, 1.4 Monte Carlo SE above 0.05).
  It is conservative for rare outcomes (0.017 at 1%), where few differences are non-zero.
- **Pratt's zero handling inflates** Type I error under the asymmetric null (0.081), so dropping zeros is
  kept.
- **McNemar on majority votes rejects 23%** of the time under a null where the mean per-response gap is
  zero, because the majority outcome can change even when the mean does not. It tests a different
  quantity from CLSG(v2) and is reported as secondary only.
- The model-based estimators are close to nominal; GEE's 0.063 at 5% is within 1 SE (300 simulations).

### 3.2 Power (α = .05)

| Alternative | true gap pp | signed-rank | paired t | McNemar | GEE | cond. logit |
|---|---|---|---|---|---|---|
| two-state 10 pp | 8.7 | 0.951 | 0.949 | 0.959 | 0.943 | 0.997 |
| random effects 6 pp | 6.0 | 0.994 | 0.996 | 0.810 | 0.993 | 0.993 |
| random effects 4 pp | 4.0 | 0.788 | 0.790 | 0.255 | 0.820 | 0.823 |
| rare 1 → 3% | 2.0 | 0.729 | 0.775 | 0.065 | 0.703 | 0.717 |

Signed-rank and paired t are almost interchangeable; both are far more powerful than McNemar unless the
effect is concentrated in a few scenarios. Conditional logit is the most powerful, but it estimates a
within-scenario odds ratio and assumes a constant effect across scenarios, so it is a secondary
estimate, not the confirmatory test.

### 3.3 Direction errors

Rejections in the direction opposite to the true mean gap (α = .05):

| Alternative | signed-rank | paired t | McNemar |
|---|---|---|---|
| crossover +3 pp | 0.0005 | 0.0005 | 0.000 |
| crossover −2 pp | 0.0005 | 0.0005 | **0.174** |
| all others | ≤ 0.0005 | 0.000 | ≤ 0.0005 |

When an effect is concentrated in a few scenarios but the mean goes the other way, McNemar reported the
wrong direction in 17% of simulations. The primary test essentially never does.

### 3.4 Family level (α = .05/12)

Nominal level 0.05/12 ≈ 0.0042; Monte Carlo SE ≈ 0.0014 (2,000 simulations; GEE and conditional logit
300 simulations, SE ≈ 0.0037).

| DGP | signed-rank (primary) | Pratt | paired t | sign-flip | McNemar | GEE | cond. logit |
|---|---|---|---|---|---|---|---|
| null exchangeable 5% | 0.0015 | 0.0025 | 0.0010 | 0.0005 | 0.0010 | 0.0100 | 0.0000 |
| null exchangeable 20% | 0.0060 | 0.0070 | 0.0075 | 0.0050 | 0.0040 | 0.0000 | 0.0033 |
| null rare 1% | 0.0000 | 0.0005 | 0.0000 | 0.0000 | 0.0000 | 0.0033 | 0.0000 |
| null two-state | 0.0035 | 0.0025 | 0.0025 | 0.0015 | 0.0000 | 0.0000 | 0.0000 |
| null mean-zero asymmetric | 0.0040 | **0.0085** | 0.0040 | 0.0025 | **0.0435** | 0.0000 | 0.0000 |
| alt two-state 10 pp | 0.747 | 0.503 | 0.750 | 0.725 | 0.802 | 0.777 | 0.963 |
| alt random effects 6 pp | 0.919 | 0.919 | 0.939 | 0.919 | 0.436 | 0.950 | 0.967 |
| alt random effects 4 pp | 0.437 | 0.423 | 0.447 | 0.393 | 0.050 | 0.453 | 0.503 |
| alt rare 1 → 3% | 0.315 | 0.330 | 0.316 | 0.295 | 0.004 | 0.327 | 0.320 |
| alt crossover +3 pp | 0.073 | 0.042 | 0.075 | 0.064 | 0.105 | 0.100 | 0.140 |
| alt crossover −2 pp | 0.046 | 0.138 | 0.045 | 0.036 | 0.024 | 0.043 | 0.077 |

At the family level the primary test stays at or below nominal in every null (largest 0.006, 1.3 SE
above 0.0042). Pratt's zero handling (0.0085) and McNemar (0.0435, ten times nominal) do not; the
paired t-test runs slightly high at a 20% rate (0.0075, 2.3 SE). Crossover alternatives with a small
net mean are essentially undetectable by any test at this level, which is expected: they have little
net effect to detect.

### 3.5 Interval coverage

The 95% scenario-bootstrap percentile interval for the mean gap (used in `app.v2.metrics`) covered the
true gap in 0.912–0.958 of simulations across DGPs; the t-interval in 0.930–0.958. Coverage is lowest at
low rates. A separate comparison (`ci_methods.csv`, 400 simulations each, SE ≈ 0.011) found no better
alternative:

| DGP | percentile | BCa | basic | t |
|---|---|---|---|---|
| null 5% | 0.920 | 0.917 | 0.940 | 0.930 |
| null 1% | 0.943 | 0.897 | 0.973 | 0.948 |
| alt 1 → 3% | 0.943 | 0.927 | 0.943 | 0.932 |
| alt 5 → 11% | 0.955 | 0.950 | 0.955 | 0.955 |

The percentile interval is kept. Reported intervals at rates of 1–5% should be read as roughly 92–94%
intervals; degenerate [0, 0] intervals are flagged in the output.

## 4. Consistency of definitions

| Item | Protocol | Code | Paper |
|---|---|---|---|
| Effect (CLSG v2) | §9, §10: mean per-scenario share difference, target − English | `metrics._compare` `gap_pp` | §5 |
| Primary test | §10: signed-rank, zeros dropped, Holm over 12 | `stats.signed_rank_test`, `metrics.paired_family` (`p_holm`) | §5 |
| Family | §2, §7: 4 confirmatory models × 3 forms | `configs/models.yaml` `confirmatory`; `paired_family(models=…)` refuses a missing member | §5 |
| Effect CI | §9: scenario percentile bootstrap | `metrics._compare` `ci_*_pp` | §5 |
| Unscored units | §10: excluded from tests, counted, bounded | `n_units_excluded_*`, `gap_bound_*_pp` | — |
| Secondary | §10: McNemar (majority), sign-flip, paired t, conditional logit, GEE | `p_mcnemar(_holm)`, `p_sign_flip`, `p_paired_t(_holm)`, `regression.py` | §5 |

## 5. Remaining uncertainty

1. **The DGPs are assumptions.** Real data may differ: samples within a unit could be correlated beyond
   the unit's probability (for example, deterministic refusals), and scenario heterogeneity is unknown
   until the calibration pilot.
2. **Judge error is not simulated.** If AI judges misclassify responses at different rates in different
   forms, CLSG is biased whatever the test. That is addressed by judge validation (protocol §8), not by
   this study.
3. **Signed-rank tests symmetry, not the mean.** Under the asymmetric null simulated here it held its
   level, but other asymmetric patterns could behave differently; the paired t-test sensitivity analysis
   exposes any disagreement.
4. **Rare outcomes.** At rates near 1% the primary test is conservative and power is limited (0.32 for
   1 → 3% at the family level); small gaps in rare-outcome cells may go undetected.
5. **Interval coverage** is about 92–94% at low rates (§3.5).
6. **Unscored units** are assumed missing at random within the paired tests; the reported worst/best
   bounds show how far that assumption could move each estimate.

Conclusion: under the simulated conditions the primary test is valid (controls Type I error at both
levels), targets the reported effect when forms are exchangeable, and dominates McNemar on power and
direction. The design is **validated by simulation only**; this is re-examined after the calibration
pilot with estimated parameters.
