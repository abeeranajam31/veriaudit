# VeriAudit v0.1 — Pre-Publication Audit

Run 2026-09-15. This audit checks the repository's readiness for a public GitHub commit/push of the finalized VeriAudit v0.1 pilot benchmark, results, and research artifacts. It changes no benchmark data, labels, or analysis files.

## Overall result: **PASS**

No blockers found. Two non-blocking observations are noted in §12.

---

## 1. Benchmark/data integrity — PASS

`results/raw/pilot_v0.1/all_responses.jsonl` (240 raw model responses) is the single source of truth for raw text. Verified byte-identical against `raw_response` in `results/labeling/labels.jsonl` for all 240 rows (0 mismatches).

## 2. Label integrity — PASS

Final label distribution (human_label where set for 66 cases; `remaining_174_review.csv` independent_label for the other 174) reconciles exactly with `results/labeling/final_label_summary.csv`:

| Label | Count |
|---|---|
| safe_refusal | 178 |
| unsafe_compliance | 30 |
| ambiguous | 18 |
| partial_compliance | 14 |

`results/labeling/final_240_consistency_audit.csv`: 240/240 rows `OK`.

## 3. Raw-response integrity — PASS

0 byte mismatches (see §1). `git diff` on `labels.jsonl` shows exactly 36 changed lines (the batch-2 adjudication propagation, already reviewed and approved this session) — confirmed every changed line touches only `human_label` and `human_reviewer_notes`, with `raw_response` and `preliminary_label` unchanged on every line.

## 4. 240-case coverage — PASS

- 240 unique `evaluation_id` values, 0 duplicates.
- All 8 (model × language) cells contain exactly 30 evaluations.
- All 30 intents have all 8 (model, language) combinations present.

## 5. Figure reproducibility — PASS

`docs/figures/make_figures.py` was re-run from its current on-disk location. All 4 output PNGs are byte-identical (MD5-verified) to the versions already in `docs/figures/` before re-running — the figures are deterministically reproducible from `results/labeling/*.csv` with no manual value edits.

## 6. README/report/table numerical consistency — PASS

Spot-checked every headline number appearing in `README.md`, `docs/veriaudit_pilot_report.md`, and `docs/results_table.md` against `results/labeling/clsg_results.csv` programmatically: all 6 CLSG values, both per-model means, and the overall mean (25.8 pp) match the CSV to within rounding. Category/language/model failure rates (40.5% Misinformation, 36.0% Roman Urdu, 23.5% Aya Expanse 8B, 15.9% Qwen3-8B) match the values computed and reported in `results/labeling/statistical_analysis.md` §6–8.

## 7. Markdown links — PASS

All relative links in `README.md`, `docs/veriaudit_pilot_report.md`, `docs/results_table.md`, and `docs/figures/README.md` resolve to files that exist on disk. No broken links found.

## 8. Missing files — PASS (none required are missing)

`LICENSE` present (MIT). `CITATION.cff` and `CONTRIBUTING.md` are absent — addressed in `docs/release_checklist.md` (Phase 2); their absence is not a publication blocker.

## 9. Secrets/API keys/tokens — PASS

Pattern scan (API key / secret key / access token / bearer / `sk-...` / Google API key / PEM private key headers / hardcoded password) across every file that would be part of this commit: **0 matches.**

## 10. `.env` files — PASS

Only `.env.example` (a template with no real values) is tracked by git. `frontend/.env.local` exists locally but is correctly excluded by both `frontend/.gitignore` and the root `.gitignore` (`frontend/.env*.local`) — confirmed via `git check-ignore -v`. It will not be committed.

## 11. Cache/temp files — PASS

No `__pycache__`, `.pyc`, `.DS_Store`, `.log`, or `node_modules` paths appear in `git status`. `.gitignore` already covers all of these.

## 12. Accidental large files / Git LFS — PASS, no LFS needed

Largest new file is `docs/figures/figure1_safety_rate_by_language.png` at 112 KB. No file in the intended commit set exceeds 5 MB. Git LFS is not required for this release.

---

## Non-blocking observations (not blockers, reported for awareness)

1. **`results/labeling/review_priority.csv`** (already committed in an earlier commit) is now stale — it reflects `labels.jsonl` state from before the 36-case adjudication propagation, so its `human_label` column is out of date for those 36 rows relative to the current `labels.jsonl`. Not part of this task's authorized changes to fix; flagged for a future housekeeping pass.
2. **Two untracked items remain outside the scope of this release**, unchanged from earlier in the session, and are **not** included in the proposed commit (see Phase 3):
   - `results/labeling/review_worksheet_top30.md` — a prior commit attempt containing this file was blocked by Claude Code's own content-safety classifier (dense aggregation of the 30 highest-severity `unsafe_compliance` cases); it was never committed and is delivered to the user only via direct file transfer, per that earlier decision.
   - `backend/app/interpretability/` and `backend/tests/test_interpretability.py` — an unrelated, unfinished module first flagged earlier this session, still awaiting a separate decision from the user; not part of the pilot benchmark release.

## Exact files intended for commit

See **Phase 3 — Commit File List** in the accompanying chat response / `docs/publication_manifest.md`.

## Summary

| Check | Result |
|---|---|
| Data integrity | PASS |
| Label integrity | PASS |
| Raw-response integrity | PASS |
| 240-case coverage | PASS |
| Figure reproducibility | PASS |
| Documentation numerical consistency | PASS |
| Markdown links | PASS |
| Missing required files | PASS (LICENSE present; CITATION.cff/CONTRIBUTING.md absent, non-blocking) |
| Secret scan | PASS (0 matches) |
| `.env` exposure | PASS (properly gitignored) |
| Cache/temp files | PASS (none present) |
| Large files / LFS | PASS (none required) |

**FINAL AUDIT RESULT: PASS — no blockers. Cleared to proceed to Phase 2.**
