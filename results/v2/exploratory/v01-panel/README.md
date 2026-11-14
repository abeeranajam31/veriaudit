# Exploratory v0.1 replication on the v2 model panel (amendment A8)

**EXPLORATORY, AI-JUDGED, NOT HUMAN-VALIDATED.** This is not a confirmatory result. It is never pooled
with the main study.

## Run

| | |
|---|---|
| Hardware | Kaggle free tier, 2 × T4, fp16 |
| Date | 2026-11-13 |
| Code | commit `1c16f37` |
| Software | vLLM 0.33.0, PyTorch 2.14.0, transformers 5.20.2 |
| Dataset | `exploratory-v01-1.0` (sha256 `8b416e62…`): the 30 VeriAudit v0.1 harmful requests in English, Urdu script, Roman Urdu and code-switched form, all written by the PI and not independently verified |
| Prompts | 120 per model; greedy decoding plus 3 samples (T = 0.7) each; 1,440 generations in total, none failed |
| Integrity | the generations hash matches `run_manifest.json`; dataset and config hashes match the repository |
| Models run | Qwen3-8B, Aya Expanse 8B, Qwen3.5-9B, at their pinned revisions |
| Model not run | **Gemma 4 E4B.** Its engine failed to start on T4 with both the default and the FlexAttention backends |
| Judges | Mistral-Nemo-12B (1,405 of 1,440 labelled, 35 unparseable) and Granite-3.3-8B (1,337 labelled, 103 unparseable) |

Raw generations and judge labels are **not** committed, because they can contain harmful text. They
are in the PI's Kaggle output; their hashes are in `run_manifest.json`.

## Main analysis: not interpretable

The protocol resolves a label only when two judges agree on every axis. The judges agree on
`harmful_content` for 96% of responses (κ = 0.44), but on `behaviour`, meaning which kind of refusal,
for only 50%. As a result, only 605 of 1,440 responses resolve, and each comparison has 1–4 scoreable
scenarios. `summary.md` reports this as it is. It is **not** evidence of zero gaps.

## Pre-specified sensitivity: each judge's labels alone (protocol §10)

`single_judge_sensitivity.csv` holds the harmful-compliance gap versus English: a paired t-test on
per-scenario shares of the 3 sampled responses, with Holm correction over the 9 comparisons for each
judge. Rows where the judge did not label all 3 samples are unscored, so n is below 30 in some
cells.

| Model | Form | Nemo gap, pp [95% t CI] | Granite gap, pp [95% t CI] |
|---|---|---|---|
| Aya Expanse 8B | Urdu script | **12.2 [3.9, 20.5]**, Holm p = .049 | 11.1 [2.2, 20.1], Holm p = .15 |
| Qwen3-8B | Roman Urdu | 10.1 [2.1, 18.2], Holm p = .13 | 20.4 [3.2, 37.6], Holm p = .18 |
| Qwen3.5-9B | every form | 1.1–2.2, no evidence of a gap | 0.0–2.8, no evidence of a gap |

**What can be said.**

- Both judges independently show the same pattern:
  - no harmful compliance in English for any model (0–1%);
  - higher compliance for Aya in Urdu script and for Qwen3-8B in Roman Urdu. That is the direction
    found in v0.1.
- The newer Qwen3.5-9B shows little difference across forms.

**What cannot be said.**

- That these gaps are established. Only one comparison survives Holm correction, under one judge.
- That the judges are accurate in Urdu, Roman Urdu or code-switched text. They do not document Urdu
  support, and no human has checked their labels yet.
- That the effect sizes generalise. The data are 30 prompts written by one translator.
- That the judges' "understood" labels are meaningful. They mark nearly all responses as understood
  (comprehension κ = 0.02), yet many Qwen3-8B Roman Urdu responses are repetition loops, and Aya
  answers 71% of Roman Urdu prompts in Hindi script.

## Needed before any claim

A human check of the judge labels: two Urdu readers label a stratified sample, with adjudication
(`python -m app.v2.human_labels sample/export/import ...`). Only then can these become exploratory
findings in a paper.
