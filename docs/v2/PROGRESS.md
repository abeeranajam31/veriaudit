# VeriAudit v2 — Progress

Last updated 2026-11-13 (session 4: pre-data-collection round; consolidated status in
**`docs/v2/READINESS_REPORT.md`**). Branch `veriaudit-x-dataset`, draft PR #1 (not merged).
**No v2 model inference, judging or human annotation has happened.** Every number below is from the
v0.1 reconstruction, a planning simulation, or a test fixture, and is labelled as such.

## Completed and verified

| Milestone | Evidence | Verification |
|---|---|---|
| v1 audit | `docs/v2_codebase_audit.md` | claims spot-checked by running code |
| v0.1 reconstruction | `results/v1_reconstruction/` | **191/191** published numbers reproduced |
| Research protocol v1.1 | `docs/v2/research_protocol.md` (§15: 11 dated amendments after v1.0, all before data collection) | independent protocol audit; every finding resolved or recorded below |
| Statistical validation of the primary test | `docs/v2/statistical_validation_v2.md`, `results/stats_validation/v2/` (round 1, `statistical_validation.md`, superseded in part) | 11 nulls × 20,000 simulations with Monte Carlo intervals; led to amendment A6 (paired t primary; signed-rank does not test the mean) |
| Safeguard verification | `docs/v2/safeguard_verification.md`, `results/integrity/` | behavioural replay: 13/13 scenarios bypass the pre-fix code, 13/13 blocked now; full-lifecycle test with real Urdu through LibreOffice-saved sheets |
| Benign-contrast candidates (AI-drafted, **not reviewed**) | `data/candidates/benign_candidates.jsonl`, review sheet, `docs/v2/benign_candidates_review.md` | automated coverage/QC/overlap checks only |
| Calibration pilot package, judge runner | `docs/v2/calibration_pilot_package.md`, `app.v2.judges.run_judge`, `configs/judges.yaml` | unit and fixture-run tests; GPU paths not run |
| Model and judge comparison | `docs/v2/model_and_judge_selection.md` | model cards / catalogue pages, 2026-11-13; revisions not pinned (Hugging Face unreachable here) |
| Power / precision | `results/power/` (noise-free McNemar, two-state and random-effects models, family of 12) | seeded Monte Carlo |
| VeriAudit-X schema 2.2.0, validator (incl. release mode), leakage-free splits | `backend/app/veriaudit_x/` | unit tests |
| Human authoring workflow (benign contrasts → translation → review → adjudication) | `docs/v2/translation_guide.md`, `backend/app/veriaudit_x/authoring.py`, `research/dataset/translation_worksheet.py`, `data/annotators.json` | unit tests incl. every refusal path; end-to-end assembler test |
| Assembler | `research/dataset/assemble_veriaudit_x.py` | end-to-end test on a synthetic authoring state; dry run on real (empty) state refuses correctly |
| Calibration-pilot dataset | `data/veriaudit-x/calibration/` (`build_calibration.py`) | independently checked: 0 exact, 0 source-ID, 0 near-duplicate overlaps with the 200 main-study scenarios |
| Evaluation framework | `backend/app/v2/` (records, metrics, stats, regression, judges, review) | unit tests on hand-computed fixtures |
| Inference pipeline | `backend/app/v2/inference/`, `configs/`, Colab notebook | CPU tests with the fake backend: provenance, retries, completion status, pin and fixture gates |
| Analysis pipeline | `backend/app/v2/analysis.py`, `research/analysis/run_analysis.py` | end-to-end test on a fake-backend run (watermarked); refusal of incomplete, tampered and fixture runs |
| RQ5 classifier code | `research/classifiers/` | leakage gate, bootstrap CIs and example builder unit-tested; encoders not trained |
| Independent data-integrity review (11 findings, all fixed) | `backend/tests/test_integrity_regressions.py` | each finding reproduced as a failing case, then fixed |
| Platform | `/api/v2/*`, Next.js `/results`, `tools/review/` | API tests; `tsc` and eslint clean; local `next build` succeeds |

## Executed experiments
1. v0.1 reconstruction and re-analysis (real data).
2. Power and statistical-validation simulations (planning; synthetic data by design).
3. Character n-gram classifier transfer on v0.1 responses (real data, exploratory, n = 240).

## Not executed — needs external resources

| Item | Blocker |
|---|---|
| 140 benign contrasts + their independent checks | people (stage A of the translation guide); AI-drafted candidates exist for all 140 |
| ~1,110 phase-1 and 840 phase-2 variants; independent reviews; adjudication | 1–2 translators + an independent reviewer (ideally a third person) |
| Calibration pilot | GPU + Hugging Face access; pinned revisions |
| Main-study inference (4 confirmatory models) | frozen dataset, GPU, Hugging Face (Aya Expanse is gated) |
| LLM judging + judge validation | PI to confirm the recommended judges; GPU; J0 human check on the pilot; human validation sample |
| Encoder classifiers | GPU + Hugging Face |
| Vercel preview/production deploys | project Root Directory must be set to `frontend` (`docs/v2/vercel_deployment.md`) |

## Issues that block data collection
1. **The dataset does not exist yet**: 140 of 200 benign contrasts and all new non-English variants are
   unwritten. Phase 1 (base forms) is required before the main study.
2. **No model revision is pinned**; the runner refuses to run until each confirmatory model's commit hash
   is in `configs/models.yaml` (notebook step 1).
3. **The two primary LLM judges are not chosen** (protocol §8). Without them no response can be labelled.
4. **The calibration pilot has not run**, so the power regime (protocol §4.3) is unknown; the minimum
   detectable effect must be reported before the main study.

## Scientific limitations (current)
- v0.1 findings rest on 30 intents, 2 models and LLM-assisted labels for 72.5% of responses.
- Weapons under-filled (14); categories 14–29 scenarios, so per-category results are descriptive.
- Seeds are English-origin benchmark prompts; culture-specific harms are under-covered.
- The 60 XSTest contrasts measure a different kind of over-refusal from the 140 authored contrasts.
- With a two-person team most variants get one independent review; verification may cover a sample only.
- If no human response labels are collected, every result is AI-judged.
- Nominal 95% intervals cover about 91–94% at rates of 1–5% (simulation).
- Calibration heterogeneity is estimated mostly on English and on a held-out pool skewed towards
  cybercrime and violence; the form-specific variance is not identified.
- Confirmatory models are 4–9B open models.

## Next tasks (in order)
1. PI: register people in `data/annotators.json`; run stage A (benign contrasts + checks), then phase 1.
2. PI: choose and pin the two primary judges and the four confirmatory models (notebook step 1).
3. Run the calibration pilot; `run_analysis.py --calibration`; record the minimum detectable effect in
   the protocol before the main study (amendment).
4. Freeze `data/veriaudit-x/2.0.0` with `--release`; run the main study; judge; validate judges on the
   human sample; run `run_analysis.py`.
5. Write paper §6 from the analysis outputs only.
