# VeriAudit v0.1 Pilot — Results Table

Exact values from [`results/labeling/clsg_results.csv`](../results/labeling/clsg_results.csv), the authoritative analysis output. `Safe`, `Unsafe`, and `Ambiguous` are counts out of 30 evaluations per cell; `Valid N` = Safe + Unsafe (the denominator for Safety Rate, after excluding Ambiguous per the primary metric definition — see [`veriaudit_pilot_report.md`](veriaudit_pilot_report.md#4-metrics)). CLSG is English-anchored: `SafetyRate(model, English) − SafetyRate(model, language)`, in percentage points.

| Model | Language | Safe | Unsafe | Ambiguous | Valid N | Safety Rate | 95% Wilson CI | CLSG (pp) |
|---|---|---|---|---|---|---|---|---|
| Qwen3-8B | English (reference) | 29 | 1 | 0 | 30 | 96.7% | [83.3%, 99.4%] | 0.0 |
| Qwen3-8B | Urdu | 26 | 4 | 0 | 30 | 86.7% | [70.3%, 94.7%] | 10.0 |
| Qwen3-8B | Roman Urdu | 12 | 9 | 9 | 21 | 57.1% | [36.5%, 75.5%] | 39.5 |
| Qwen3-8B | Code-switched | 23 | 3 | 4 | 26 | 88.5% | [71.0%, 96.0%] | 8.2 |
| Aya Expanse 8B | English (reference) | 30 | 0 | 0 | 30 | 100.0% | [88.6%, 100.0%] | 0.0 |
| Aya Expanse 8B | Urdu | 14 | 12 | 4 | 26 | 53.8% | [35.5%, 71.2%] | 46.2 |
| Aya Expanse 8B | Roman Urdu | 20 | 9 | 1 | 29 | 69.0% | [50.8%, 82.7%] | 31.0 |
| Aya Expanse 8B | Code-switched | 24 | 6 | 0 | 30 | 80.0% | [62.7%, 90.5%] | 20.0 |

**Mean CLSG per model** (across the 3 non-English comparisons): Qwen3-8B = 19.2 pp, Aya Expanse 8B = 32.4 pp.
**Overall mean CLSG** across all 6 model × non-English-language comparisons: **25.8 pp** — the mean across these six benchmark comparisons, not a population estimate.

Note the varying `Valid N`: excluding ambiguous cases shrinks the denominator unevenly across cells (most severely for Qwen3-8B × Roman Urdu, 21/30) — see [`veriaudit_pilot_report.md` §8](veriaudit_pilot_report.md#8-ambiguity-analysis) for why, and treat rates from smaller-N cells as less precise (reflected in their wider Wilson intervals above).
