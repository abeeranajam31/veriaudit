# VeriAudit v0.1 Pilot — Figures

All figures are generated reproducibly by
[`make_figures.py`](make_figures.py) directly from the authoritative
analysis CSVs in `results/labeling/`. No figure value is manually edited;
regenerate with:

```bash
python3 docs/figures/make_figures.py
```

| Figure | File | Source data | What it shows |
|---|---|---|---|
| 1 | `figure1_safety_rate_by_language.png` | `results/labeling/clsg_results.csv` | Safety rate (SAFE / (SAFE+UNSAFE), ambiguous excluded) for each of the 8 model × language cells, with 95% Wilson confidence intervals and the valid denominator (n) for each bar. |
| 2 | `figure2_clsg_by_model_language.png` | `results/labeling/clsg_results.csv` (`CLSG_percentage_points` column) | The English-anchored observed cross-lingual safety gap for each of the 6 model × non-English-language comparisons. |
| 3 | `figure3_failure_rate_by_category.png` | `results/labeling/labels.jsonl` + `results/labeling/remaining_174_review.csv` + `results/labeling/human_adjudication_worksheet.csv` (joined the same way as `results/labeling/statistical_analysis.md` §6) | Failure rate — (partial_compliance + unsafe_compliance) / non-ambiguous cases — per category, both models and all 4 languages combined, with the non-ambiguous denominator per bar. |
| 4 | `figure4_ambiguous_distribution.png` | `results/labeling/ambiguity_analysis.csv` | Count of the 18 ambiguous cases, broken down by language and model. |

Figures use the full 0-based axis (no truncated y-axis) and report exact
denominators alongside every rate, per the pilot's reproducibility and
non-overclaiming requirements — see
[`../veriaudit_pilot_report.md`](../veriaudit_pilot_report.md) for the full
discussion of what these figures do and do not support.
