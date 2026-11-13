# CLAUDE.md — working rules for this repository

VeriAudit: cross-lingual safety evaluation of LLMs in English, Urdu script,
Roman Urdu and Urdu–English code-switching. v0.1 (pilot) is published; v2 is
in development on branch `veriaudit-x-dataset`.

## Read first
- `VERIAUDIT_V2_MASTER_PLAN.md` — milestones and decisions
- `docs/v2/research_protocol.md` — pre-specified design and analysis plan
- `docs/v2/PROGRESS.md` — what is done, verified, pending
- `docs/v2_codebase_audit.md` — audit of v1

## Hard rules
- Never modify or delete anything under `results/raw/`, `results/labeling/`,
  `dataset/examples/` or the v0.1 docs. New outputs go in new directories.
- Never fabricate model outputs, human annotations, citations or results.
  Demo/illustrative output must be labelled as such in code and UI.
- AI review is never human verification: keep `ai_generated`, `ai_reviewed`,
  `human_reviewed`, `human_adjudicated` separate. Only human ratings by
  registered raters (`data/annotators.json`) who did not author the variant,
  bound to the hash of the rated text, can set `equivalence.status = verified`
  (≥2 independent `equivalent`, or adjudicator acceptance + ≥1 independent).
- Never register an AI system as a rater, author or reviewer.
- A single LLM judge or the rule judge never produces a final response label.
- The primary confirmatory test is the paired t-test on share differences (amendment A6); the
  signed-rank test is descriptive only and is never described as a test of the mean/CLSG.
- The confirmatory families are fixed: 4 models × 3 forms each (H1, H2). Do not
  add or drop a confirmatory model without a protocol amendment.
- Do not drop non-scoreable/ambiguous outputs from denominators.
- No paid APIs or compute without the PI's explicit authorisation.
- Do not merge to `main` or publish datasets/results/papers without approval.
- Protocol changes after data collection go in the protocol's amendment log.

## Layout
- `backend/app/veriaudit_x/` — dataset schema, validation, splits (CLI: `python -m app.veriaudit_x`)
- `backend/app/veriaudit_x/authoring.py` — human authoring workflow (row plan, sheet import/export, review, adjudication)
- `backend/app/v2/` — stats, metrics, regression, judges, quality checks, inference, end-to-end analysis (`analysis.py`)
- `research/` — runnable scripts (repo root, `PYTHONPATH=backend`): `dataset/`, `analysis/`, `stats_validation/`, `power/`, `classifiers/`, `inference/`, `platform/`
- `data/annotators.json` — registry of human raters (pseudonymous IDs)
- `configs/` — experiment and model configs (YAML)
- `results/v1_reconstruction/`, `results/power/`, `results/stats_validation/`, `results/v2/` — generated outputs

## Commands
```bash
cd backend && python -m pytest -q          # all tests
cd backend && ruff check app tests ../research && ruff format --check app ../research
PYTHONPATH=backend python research/v1_reconstruction/reconstruct.py   # must print 191/191 matched
PYTHONPATH=backend python research/power/power_analysis.py
PYTHONPATH=backend python research/stats_validation/validate_primary_test.py && python research/stats_validation/make_report.py  # ~15 min
PYTHONPATH=backend python research/platform/export_dashboard_data.py   # refresh /results data after any result change
PYTHONPATH=backend python research/dataset/translation_worksheet.py status   # authoring progress
PYTHONPATH=backend python research/dataset/assemble_veriaudit_x.py --version 2.0.0-rcN   # candidate build
PYTHONPATH=backend python research/dataset/build_calibration.py
PYTHONPATH=backend python -m app.v2.inference.runner configs/experiments/calibration_pilot.yaml   # GPU; pinned models only
PYTHONPATH=backend python -m app.v2.judges.run_judge --run results/v2/runs/<run_id> --judge <key>   # GPU; pinned judges only (configs/judges.yaml)
PYTHONPATH=backend python research/analysis/run_analysis.py --run results/v2/runs/<run_id> --labels <labels.jsonl...>
PYTHONPATH=backend python research/stats_validation/validate_v2.py   # ~5 min; primary-test validation (amendment A6)
PYTHONPATH=backend python research/integrity/replay_review_scenarios.py <tree> --out <json>   # safeguard replay
PYTHONPATH=backend python research/dataset/benign_candidates.py   # AI-drafted benign candidates + review sheet (not reviewed)
```

## Dataset authoring
Non-English variants are written by human translators following
`docs/v2/translation_guide.md` (`research/dataset/translation_worksheet.py`:
benign contrasts → translation → independent review → adjudication). Do not
route harmful prompts through AI generation: the generating model's safety
classifiers stopped every attempt, and the protocol was amended accordingly.
Benign contrasts may be AI-drafted only if marked `drafted_by_ai = yes`; a
translator's machine/AI drafting aid is recorded via `drafting_aid`. Imports
refuse edited read-only cells, self-review and unregistered raters — fix the
sheet, never the checks.

## Git
Commit as `abeeranajam31 <128603901+abeeranajam31@users.noreply.github.com>`
(the repo's existing identity); never commit with a personal email address.

## Environment notes
The cloud sandbox has no GPU and cannot reach huggingface.co; GitHub raw and
PyPI are reachable. Inference and transformer fine-tuning are designed to run
on Colab/remote GPUs via `configs/` and `research/inference/`; CPU tests use
injected fake backends and never count as results. The runner refuses
unpinned Hugging Face models and fixture datasets for real models; the
analysis refuses incomplete, tampered or fixture runs unless overridden
(integrity is never overridable) and watermarks fixture output.

Vercel: the app lives in `frontend/`; the project's Root Directory must be
`frontend` (see `docs/v2/vercel_deployment.md`). Do not change dashboard
settings — that is the PI's.
