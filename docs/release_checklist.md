# VeriAudit v0.1.0 — Release Checklist

## Release version

`v0.1.0` — first public pilot release of the VeriAudit benchmark, labels, statistical analysis, and technical report.

## Included benchmark

- 30 safety-relevant intents, 6 categories (Cybercrime, Weapons, Self-Harm, Hate Speech, Misinformation, Fraud), 4 linguistic variants (English, Urdu, Roman Urdu, code-switched), 2 models (Qwen3-8B, Aya Expanse 8B) — 240 total evaluations.
- `dataset/examples/veriaudit-pilot-v0.1-30.jsonl` — the 30-intent benchmark definition.
- `results/raw/pilot_v0.1/all_responses.jsonl` + `run_metadata.json` — all 240 raw model responses and exact run configuration.
- `results/labeling/labels.jsonl` — the finalized 240-case label set (66 human-reviewed/adjudicated, 174 independently reviewed; see provenance note below).

## Included analysis

- `results/labeling/clsg_results.csv`, `paired_intent_analysis.csv`, `failure_analysis.csv`, `ambiguity_analysis.csv`, `sensitivity_analysis.csv` — the authoritative quantitative outputs.
- `results/labeling/statistical_analysis.md` — full statistical narrative (McNemar tests, Holm correction, sensitivity analysis).
- `results/labeling/final_240_consistency_audit.csv` — the label-consistency audit (240/240 OK).
- `results/labeling/analysis_readiness_report.md`, `human_adjudication_readme.md` — supporting methodology notes.

## Included report

- `docs/veriaudit_pilot_report.md` — the 12-section technical report (abstract through conclusion).
- `docs/results_table.md` — the clean model × language results table.
- `docs/figures/` — 4 figures + the reproducible generation script (`make_figures.py`) + a README documenting exactly which CSV produced each figure.

## Reproducibility instructions

1. **Labels/analysis**: all derived from `results/labeling/labels.jsonl` + `results/labeling/remaining_174_review.csv` + `results/labeling/human_adjudication_worksheet.csv` (the last of these is intentionally *not* part of this public commit — see the exclusion note in `docs/pre_publication_audit.md` — but the join logic and its output are fully reproducible from the committed `labels.jsonl`, which already carries every resolved `human_label`).
2. **Figures**: `python3 docs/figures/make_figures.py`, regenerates all 4 PNGs deterministically from the CSVs above.
3. **Raw model runs**: not re-runnable without the exact local MLX setup (Apple Silicon, `mlx-lm` 0.31.3, `mlx-community/Qwen3-8B-4bit`, `mlx-community/aya-expanse-8b-4bit`); exact configuration is recorded in `results/raw/pilot_v0.1/run_metadata.json` for anyone who wants to reproduce the run independently.
4. Full instructions: `docs/veriaudit_pilot_report.md` §11 (Reproducibility).

## Known limitations (see `docs/veriaudit_pilot_report.md` §10 for the full list)

- 30 intents is a small pilot sample; category-level splits (n=5) are descriptive only.
- Only 2 models tested — Qwen3-8B and Aya Expanse 8B, both 4-bit quantized.
- **174/240 final labels (72.5%) were produced by an independent LLM-assisted review, not a second human annotator.** Only 66/240 (27.5%) carry genuine human sign-off. This is the single most important caveat for anyone using this dataset.
- Roman Urdu carries a disproportionate share of ambiguous/undecidable outputs (10 of 18).
- CLSG is a descriptive metric; no causal claim is made about translation or any other mechanism.
- Results are specific to these two models at these settings and do not generalize to other models or languages without replication.

## Publication caveats

- **This is a pilot (v0.1), not a validated benchmark.** It should not be cited as evidence of a general property of "AI safety in Urdu" or of these models beyond the 240 specific evaluations reported.
- **Do not describe the 240-case dataset as fully human-validated** — only 66/240 labels carry direct human review/adjudication.
- Some response content in `labels.jsonl` includes model outputs that materially comply with harmful requests (that is the nature of a `unsafe_compliance`/`partial_compliance` safety benchmark) — this is disclosed plainly here rather than downplayed, and is the same content already present in prior commits to this repository this session.
- `review_worksheet_top30.md` and `human_adjudication_worksheet.csv` are deliberately excluded from this commit as redundant, denser re-presentations of already-included raw content (see `docs/pre_publication_audit.md` §"Non-blocking observations"). Their exclusion does not remove any information from the release — the same underlying labeled data is in `labels.jsonl`.

## Repository housekeeping status

| File | Status |
|---|---|
| `README.md` | Present, updated with Pilot Results section |
| `LICENSE` | Present — MIT. Appropriate for the code (frontend/backend/scripts). Whether the *benchmark data* itself (as opposed to the code) should carry a separate data license (e.g., CC-BY-4.0) is a decision for the maintainer — see `docs/huggingface_release.md` for the model-output redistribution licensing question specifically, which is a separate and more constrained issue. |
| `CITATION.cff` | **Missing before this task; drafted this run** (see repository root). Repository URL taken from the existing `git remote` (`https://github.com/abeeranajam31/veriaudit`), not invented. No DOI included, since none exists yet. |
| `CONTRIBUTING.md` | Missing. Not created — not requested, and a blank/templated CONTRIBUTING.md that doesn't reflect the maintainer's actual review process would arguably be worse than none. Recommend the maintainer write this when ready to accept external contributions. |
| `.gitignore` | Present, covers Node/Python caches, `.env*`, OS files, and the interpretability-module output directory. |
