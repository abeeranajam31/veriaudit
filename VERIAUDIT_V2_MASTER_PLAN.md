# VeriAudit v2 — Master Plan

Living document. Status per milestone is tracked in `docs/v2/PROGRESS.md`;
the scientific design is fixed in `docs/v2/research_protocol.md`.

## Goal
A reproducible, publication-oriented study of how linguistic form (English,
Urdu script, Roman Urdu, code-switching) and comprehension affect LLM safety
**and** usefulness, with a released benchmark (VeriAudit-X), an evaluation
framework, classifier experiments, and a dashboard showing only real results.

## Milestones

| # | Milestone | Depends on | Runs in sandbox? |
|---|---|---|---|
| M0 | Audit of v1; VeriAudit-X schema/validation/splits | — | yes |
| M1 | Reconstruct v0.1 analysis from raw data; corrected scoring | M0 | yes |
| M2 | Research protocol; power analysis; this plan; CLAUDE.md | M1 | yes |
| M3 | Evaluation framework: response-label schema, 7 metrics, paired stats, judges | M2 | yes |
| M4 | Dataset pipeline: source ingestion + licences, scenario selection, v0.1 migration, variant generation, automated QC, dedup, splits, review UI | M0, M2 | partly (AI generation via this assistant; second-model checks need GPU/API) |
| M5 | Inference pipeline: Transformers / vLLM / OpenAI-compatible adapters, YAML configs, model manifest with pinned revisions, resumable cached jobs, Colab notebook | M3 | code + CPU tests only; real runs need GPU |
| M6 | Classifier experiments (XLM-R, mDeBERTa, MuRIL; char-n-gram baseline) | M4, M5 | baseline yes; encoders need GPU + HF access |
| M7 | Platform: FastAPI endpoints over real result files; Next.js research dashboard separated from demo | M3, M4 | yes |
| M8 | Independent reviews, figures, paper draft from actual findings, release prep, draft PR | all | yes |
| M9 | **Main study execution** (calibration pilot → frozen dataset → inference → judging → analysis) | M4, M5, GPU | **no — external** |
| M10 | Human validation sample (300 responses, double annotation) | M9, annotators | **no — external** |

## Key decisions (rationale in the protocol)

| Decision | Choice | Why |
|---|---|---|
| Unit of analysis | scenario (harmful intent + benign contrast) | paired design; lets RQ4 compare harmful compliance and over-refusal on matched topics; split unit for leakage control |
| Size | 200 scenarios | ≥ 80% power for a 10 pp harmful-compliance gap across 15 Holm-corrected tests (`results/power/`) |
| Primary outcome | harmful compliance on full denominator | v0.1 reconstruction showed the legacy safety-rate CLSG conflates comprehension failure with unsafe behaviour |
| Confirmatory tests | H1 (15 harmful-compliance tests), H2 (15 over-refusal tests), Holm | small pre-specified families; everything else exploratory with BH |
| Sampling | 3 samples (T=0.7) + greedy; majority over samples | reduces single-sample noise, keeps greedy for v0.1 continuity |
| Precision | bf16 | v0.1 4-bit artefacts (looping) confounded comprehension |
| Variant generation | AI-generated, provenance-tracked; humans optional | no translators available; validator forbids treating AI agreement as verification |
| Rule judge | triage only | 22–36% refusal recall outside English in v0.1 |
| Sources | AdvBench (MIT), XSTest prompts (CC-BY-4.0), v0.1 items | licences verified; HarmBench pending licence check |

## External blockers (need the PI)
1. GPU access (Colab Pro / remote GPU) for M9 and encoder training in M6.
2. Hugging Face access (sandbox cannot reach huggingface.co; Aya Expanse and some Gemma checkpoints are gated and need licence acceptance on the PI's account).
3. Human annotators (optional) for M10 and for verifying AI-generated variants.
4. Authorisation for any paid API use (none planned).
