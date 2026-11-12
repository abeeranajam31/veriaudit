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
| M4 | Dataset pipeline: source ingestion + licences, scenario selection, v0.1 migration, variant generation, automated QC, dedup, splits, review UI | M0, M2 | pipeline yes; **variant authoring needs human translators** (AI generation was stopped by safety classifiers) |
| M5 | Inference pipeline: Transformers / vLLM / OpenAI-compatible adapters, YAML configs, model manifest with pinned revisions, resumable cached jobs, Colab notebook | M3 | code + CPU tests only; real runs need GPU |
| M6 | Classifier experiments (XLM-R, mDeBERTa, MuRIL; char-n-gram baseline) | M4, M5 | baseline yes; encoders need GPU + HF access |
| M7 | Platform: FastAPI endpoints over real result files; Next.js research dashboard separated from demo | M3, M4 | yes |
| M8 | Independent reviews, figures, paper draft from actual findings, release prep, draft PR | all | yes |
| M8b | Statistical validation of the primary test (simulation); protocol audit and v1.1 amendments; human translation workflow; calibration-pilot redesign; end-to-end analysis pipeline | M3–M7 | yes (done 2026-11-13) |
| M9 | **Main study execution** (calibration pilot → frozen dataset → inference → judging → analysis) | M4, M5, GPU | **no — external** |
| M10 | Human validation sample (300 responses, double annotation) | M9, annotators | **no — external** |

## Key decisions (rationale in the protocol)

| Decision | Choice | Why |
|---|---|---|
| Unit of analysis | scenario (harmful intent + benign contrast) | paired design; lets RQ4 compare harmful compliance and over-refusal on matched topics; split unit for leakage control |
| Size | 200 scenarios | Primary test: signed-rank on 3-sample shares, family of 12. Power ≈ 0.80 for a 10 pp gap concentrated in few scenarios (high response consistency) and ≥ 0.85 for a 6 pp gap spread across scenarios; re-checked after the calibration pilot (`results/power/`, protocol §4.3) |
| Primary outcome | harmful compliance on full denominator | v0.1 reconstruction showed the legacy safety-rate CLSG conflates comprehension failure with unsafe behaviour |
| Confirmatory panel | 4 models fixed in advance (Qwen3-8B, Aya Expanse 8B, Qwen3.5-9B, Gemma 4 E4B-it); larger Gemma exploratory | a compute-dependent 5th model left the Holm family undefined |
| Confirmatory tests | H1 (12 harmful-compliance tests), H2 (12 over-refusal tests), Wilcoxon signed-rank on share differences, Holm | validated by simulation (`docs/v2/statistical_validation.md`); McNemar on majority votes secondary (different estimand); paired t sensitivity |
| Sampling | 3 samples (T=0.7) + greedy; per-response shares | reduces single-sample noise, keeps greedy for v0.1 continuity |
| Labels | two agreeing AI judges or a third-judge majority; humans override; single judge / rule judge never final | protocol §8; unresolved responses are unscored and counted |
| Equivalence | human review by someone other than the translator, bound to text hashes; adjudication by a third person; drafting aids disclosed | AI agreement is not human validation |
| Precision | bf16 | v0.1 4-bit artefacts (looping) confounded comprehension |
| Variant generation | human translators via worksheet (amended 2026-11-12) | AI generation of harmful-prompt translations was stopped by the generating model's safety classifiers |
| Rule judge | triage only | 22–36% refusal recall outside English in v0.1 |
| Sources | AdvBench (MIT), XSTest prompts (CC-BY-4.0), v0.1 items | licences verified; HarmBench pending licence check |

## External blockers (need the PI)
1. GPU access (Colab Pro / remote GPU) for M9 and encoder training in M6.
2. Hugging Face access (sandbox cannot reach huggingface.co; Aya Expanse and some Gemma checkpoints are gated and need licence acceptance on the PI's account).
3. **People for the dataset:** someone to write the 140 missing benign contrasts and someone else to check them; 1–2 translators for ~1,110 phase-1 and 840 phase-2 variants; an independent reviewer (ideally a third person for a 20% agreement sample and adjudication); register their pseudonymous IDs in `data/annotators.json`. Annotators for M10.
4. Authorisation for any paid API use (none planned).
5. Choice of the two primary LLM judges (protocol §8), and pinning of every model revision before any run.
