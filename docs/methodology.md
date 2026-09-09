# Methodology

This document describes the end-to-end VERIAUDIT evaluation pipeline:
**TEST → COMPARE → SCORE → ANALYZE → REPORT**.

## 1. Define Intent

A test case starts as a single underlying intent — a request, independent
of the language it will eventually be expressed in. See
[`dataset/README.md`](../dataset/README.md) for the schema.

## 2. Generate Variants — EquivEngine

`EquivEngine` ([`backend/app/evaluation/equiv_engine.py`](../backend/app/evaluation/equiv_engine.py))
transforms the English intent into Urdu, Roman Urdu, and code-switched
forms via a pluggable `TranslationProvider`, then screens each variant for
semantic equivalence using multilingual sentence-transformer embeddings.

**Important:** embedding similarity above a threshold is a screening
signal, not proof of equivalence. VERIAUDIT never auto-verifies a variant
purely from a similarity score:

- similarity below `SIMILARITY_FLAG_THRESHOLD` (default `0.85`) → `flagged`
- everything else → `pending`, awaiting human review
- only a human reviewer can promote a case to `verified`

## 3. Evaluate — GapEvaluator

`GapEvaluator` ([`backend/app/evaluation/gap_evaluator.py`](../backend/app/evaluation/gap_evaluator.py))
runs each variant against every configured model (via a `ModelAdapter`) and
scores each response across pluggable evaluation dimensions
([`backend/app/evaluation/evaluators.py`](../backend/app/evaluation/evaluators.py)):

- **Refusal consistency** — did the model refuse equivalent unsafe requests consistently?
- **Instruction following** — did behavior remain consistent across linguistic variants?
- **Safety** — did the model provide materially different unsafe assistance?

Additional dimensions (prompt injection resistance, toxicity/harmful output
comparison) are designed to slot into the same `Evaluator` interface.

The shipped evaluators are transparent heuristics (keyword/pattern based) —
a documented starting point, not a validated safety classifier. Swap in
model-graded or human-in-the-loop evaluators behind the same interface for
production use.

## 4. Measure the Gap — CLSG

Per-model, per-language scores are aggregated into the Cross-Lingual Safety
Gap. See [`metric.md`](./metric.md) for the full specification.

## Model support

VERIAUDIT does not hardcode a dependency on any paid API. Models are
accessed through a `ModelAdapter`
([`backend/app/services/model_adapters.py`](../backend/app/services/model_adapters.py)):

- `HuggingFaceAdapter` — Hugging Face Inference API
- `OpenAIAdapter` — optional, OpenAI-compatible chat completions
- `CustomAdapter` — any self-hosted HTTP endpoint
- `DemoAdapter` — deterministic, offline, illustrative-only fallback used
  when `DEMO_MODE=true` (the default) or no credentials are configured

## Evidence reports

`EvidenceReport` ([`backend/app/reports/evidence_report.py`](../backend/app/reports/evidence_report.py))
generates a PDF via ReportLab containing the audit ID, date, models,
dataset version, languages, methodology summary, test cases, scores, CLSG,
and limitations. Every report includes:

> This report provides technical evaluation evidence that may support AI
> risk assessment and governance workflows. It is not legal advice or a
> certification of regulatory compliance.

## Reproducibility

- Dataset version, verification status, and similarity scores are recorded
  per test case.
- Demo-mode scores are deterministic (seeded by test case, model, and
  language) so illustrative output is stable across runs.
- Model adapter configuration (adapter type + model id) is recorded in
  every evaluation request/response.
