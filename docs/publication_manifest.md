# VeriAudit v0.1.0 — Publication Manifest

Compiled 2026-09-15. This is the single top-level index of everything prepared for this release. Nothing described here as "proposed" or "pending" has been executed — see Status fields.

---

## GitHub

- **Version**: v0.1.0
- **Proposed commit message**: `Release VeriAudit v0.1.0 pilot benchmark and results`
- **Exact files** (29 total — 5 modified, 24 new): see `docs/pre_publication_audit.md` and the COMMIT FILE LIST printed in the chat response for this task. Summary by area:
  - Core: `README.md` (modified), `CITATION.cff` (new)
  - Benchmark labels: `results/labeling/labels.jsonl`, `final_flagged_cases.csv`, `final_label_summary.csv`, `labeling_run_metadata.json` (all modified — reflect the already-approved 36-case adjudication propagation)
  - Analysis: `ambiguity_analysis.csv`, `analysis_readiness_report.md`, `clsg_results.csv`, `failure_analysis.csv`, `final_240_consistency_audit.csv`, `human_adjudication_readme.md`, `paired_intent_analysis.csv`, `remaining_174_review.csv`, `sensitivity_analysis.csv`, `statistical_analysis.md` (all new)
  - Report/docs: `docs/veriaudit_pilot_report.md`, `docs/results_table.md`, `docs/pre_publication_audit.md`, `docs/release_checklist.md`, `docs/huggingface_release.md`, `docs/website_results_update.md`, `docs/publication_manifest.md` (all new)
  - Figures: `docs/figures/figure1_safety_rate_by_language.png`, `figure2_clsg_by_model_language.png`, `figure3_failure_rate_by_category.png`, `figure4_ambiguous_distribution.png`, `make_figures.py`, `README.md` (all new)
- **Explicitly excluded**: `results/labeling/review_worksheet_top30.md`, `results/labeling/human_adjudication_worksheet.csv` (redundant raw-content aggregations; see `docs/pre_publication_audit.md`), `backend/app/interpretability/`, `backend/tests/test_interpretability.py` (unrelated, unfinished, separate pending decision)
- **Status**: **Prepared, not committed, not pushed.** Awaiting explicit approval to run `git add` + `git commit` + `git push`.

## Hugging Face

- **Proposed dataset name**: `veriaudit-pilot-v0.1` — **or** an update to the existing `abeeranajam31/CLSG-Benchmark` repo; maintainer decision required (see `docs/huggingface_release.md`).
- **Files**: benchmark prompts/variants, final labels, run metadata, dataset card, licensing info — full list in `docs/huggingface_release.md`.
- **Dataset-card status**: **Drafted** (full card in `docs/huggingface_release.md`), not published.
- **Licensing status**: **Partially cleared.**
  - Qwen3-8B raw responses (120/240): clear — Apache 2.0, no redistribution restriction.
  - Aya Expanse 8B raw responses (120/240): **`REVIEW_REQUIRED`** — CC-BY-NC + C4AI Acceptable Use Policy; not yet cleared for redistribution under this dataset's license. **Do not upload the Aya Expanse response text until this is resolved.**
- **Status**: **Planning complete. No upload has occurred.**

## Website

- **Proposed updates**: a new "Pilot Benchmark" results section on `frontend/src/app/research/page.tsx` (full copy and JSX in `docs/website_results_update.md`), plus an optional badge-copy update on `frontend/src/app/benchmark/page.tsx`.
- **Deployment status**: **Not deployed. No frontend file has been edited.**

## Research artifacts

- **Technical report**: `docs/veriaudit_pilot_report.md` (12 sections, abstract through conclusion).
- **Figures**: 4 figures in `docs/figures/`, reproducibly generated (byte-identical on re-run, verified this session) from `results/labeling/*.csv` via `docs/figures/make_figures.py`.
- **Statistical analysis**: `results/labeling/statistical_analysis.md` (McNemar exact tests, Holm correction, sensitivity analysis) and its five supporting CSVs.
- **Results table**: `docs/results_table.md`.

## Claims supported by the current pilot

These are the claims this pilot's data actually supports, stated at the same strength as the technical report:

1. A cross-lingual safety gap is **observed** in every one of the 6 model × non-English-language comparisons tested (Qwen3-8B and Aya Expanse 8B, Urdu/Roman Urdu/code-switched vs. English), ranging 8.2–46.2 percentage points, mean 25.8 pp across the six comparisons.
2. 3 of these 6 comparisons remain statistically significant after Holm correction for multiple comparisons at n=30 intents (Qwen3-8B×Roman Urdu p=0.0195, Aya×Urdu p=0.0029, Aya×Roman Urdu p=0.0195); the other 3 show the same direction but do not reach significance at this sample size.
3. In this pilot, Roman Urdu shows both the highest observed failure rate (36.0%) and the largest concentration of ambiguous/undecidable model outputs (10 of 18).
4. In this pilot, Aya Expanse 8B shows a higher overall failure rate (23.5%) than Qwen3-8B (15.9%), and the single largest observed gap (Aya × Urdu, 46.2 pp).
5. In this pilot, Misinformation is the highest-risk category by failure rate (40.5%), driven mainly by fabricated/deceptive content generation.
6. In 42 of the paired English-safe cases, the identical intent produced an unsafe or partially unsafe response from the same model in a non-English form.

No claim beyond these — and none stronger than "observed in this pilot" — is supported by the current data.

## Limitations (load-bearing methodological caveats)

1. **30 intents** is a small pilot sample; category-level splits (n=5) are descriptive only, not independently powered.
2. **Only 2 models** tested (Qwen3-8B, Aya Expanse 8B, both 4-bit quantized) — findings do not generalize to other models.
3. **6 categories, 30 original intents** — illustrative coverage of the harm space, not exhaustive.
4. **174/240 labels (72.5%) were independently reviewed by an LLM-assisted process, not a second human annotator.** Only 66/240 (27.5%) carry genuine human sign-off. This is the single largest validity caveat attached to every number in this release.
5. **Roman Urdu carries a disproportionate ambiguity burden** (10/18 ambiguous cases), a generation-reliability confound layered on the safety comparison for that language.
6. **Possible prompt/translation confounds** — the non-English variants are constructed, not independently native-authored, and this pilot cannot fully separate prompt-construction artifacts from model behavior differences.
7. **CLSG is a descriptive benchmark metric, not a causal estimator** — no claim is made about *why* the gap exists.
8. **No causal inference of any kind** is supported by this data.
9. **Results require replication** with more intents, models, independent human annotators, and languages before any claim stronger than "observed in this pilot" is warranted.
10. **This benchmark does not establish that Urdu or Roman Urdu safety behavior is universally poor** — it reports what was observed for 30 specific intents and 2 specific models in one run each.
