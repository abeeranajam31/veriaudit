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
  `human_reviewed`, `human_adjudicated` separate. Only ≥2 human
  `equivalent` ratings may set `equivalence.status = verified`.
- Do not drop non-scoreable/ambiguous outputs from denominators.
- No paid APIs or compute without the PI's explicit authorisation.
- Do not merge to `main` or publish datasets/results/papers without approval.
- Protocol changes after data collection go in the protocol's amendment log.

## Layout
- `backend/app/veriaudit_x/` — dataset schema, validation, splits (CLI: `python -m app.veriaudit_x`)
- `backend/app/v2/` — stats, metrics, judges, quality checks, inference, classifiers
- `research/` — runnable analysis scripts (run from repo root with `PYTHONPATH=backend`)
- `configs/` — experiment and model configs (YAML)
- `results/v1_reconstruction/`, `results/power/`, `results/v2/` — generated outputs

## Commands
```bash
cd backend && python -m pytest -q          # all tests
cd backend && ruff check app tests ../research && ruff format --check app ../research
PYTHONPATH=backend python research/v1_reconstruction/reconstruct.py   # must print 191/191 matched
PYTHONPATH=backend python research/power/power_analysis.py
PYTHONPATH=backend python research/platform/export_dashboard_data.py   # refresh /results data after any result change
```

## Dataset authoring
Non-English variants of harmful prompts are written by human translators
(`research/dataset/translation_worksheet.py export|import`). Do not route them
through AI generation: the generating model's safety classifiers stopped every
attempt, and the protocol was amended accordingly. Benign contrasts may still be
drafted by AI if recorded with `quality.ai_generated = true`.

## Git
Commit as `abeeranajam31 <128603901+abeeranajam31@users.noreply.github.com>`
(the repo's existing identity); never commit with a personal email address.

## Environment notes
The cloud sandbox has no GPU and cannot reach huggingface.co; GitHub raw and
PyPI are reachable. Inference and transformer fine-tuning are designed to run
on Colab/remote GPUs via `configs/` and `research/inference/`; CPU tests use
injected fake backends and never count as results.
