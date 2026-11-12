# Draft — Comprehension, Not Only Compliance: Re-examining Cross-Lingual Safety Gaps for Urdu, Roman Urdu and Code-Switched Prompts

*Working draft, 2026-11-12. Written only from results that exist in this repository. Sections marked
**[PENDING MAIN STUDY]** describe planned work and contain no results. Not for submission or
circulation without the PI's review.*

## Abstract

Multilingual safety evaluations usually report a single "safety gap" between English and another
language. We re-analyse a released pilot (VeriAudit v0.1: two 8B open-weight models, 30 harmful
requests, each in English, Urdu script, Roman Urdu and Urdu–English code-switching) and show that
this number is sensitive to two choices that are rarely reported. First, discarding non-scoreable
outputs (degenerate loops, "I don't understand") from the denominator inflates the gap where models
fail to comprehend: Qwen3-8B's Roman Urdu gap falls from 39.5 to 26.7 percentage points when only
actual harmful compliance is counted on all 30 pairs, and is no longer significant after Holm
correction (p = .086). Second, lexical refusal detectors collapse outside English (0% refusal recall
on Urdu-script refusals for the pilot's own heuristic), which would have reported gaps of 42.5–70
points on the same responses. All 191 published pilot numbers are reproduced exactly from raw data.
We describe VeriAudit-X, a 200-scenario benchmark of matched harmful/benign pairs designed to measure
harmful compliance, over-refusal and comprehension separately, with a pre-specified, power-justified
analysis plan. **[PENDING MAIN STUDY]**

## 1. Introduction

Safety behaviour degrades when harmful requests are translated into lower-resource languages
([Yong et al., 2023](https://arxiv.org/html/2310.02446v1); [Deng et al., ICLR 2024](https://arxiv.org/abs/2310.06474))
and when they are code-switched ([Yoo et al., 2024](https://arxiv.org/abs/2406.15481)). For Urdu, the
dominant everyday written forms are Roman Urdu, which lacks a standard orthography
([Butt et al.](https://arxiv.org/html/2503.21530v2)), and Urdu–English code-switching. A cross-lingual
"safety gap" in these forms can arise from at least three different mechanisms: the model understood and
complied (a safety failure), the model did not understand and produced something unscoreable (a
comprehension failure), or the measurement instrument failed in that language (an evaluation failure).
Most reported gaps do not separate them.

Contributions: (1) an exact reproduction of a released pilot from raw outputs and an analysis of how its
headline result depends on denominator and detector choices; (2) evidence that lexical refusal detection
is unusable as a multilingual safety metric for these forms; (3) VeriAudit-X, a scenario-paired design
with benign contrasts, controlled linguistic transformations and a pre-registered analysis plan.

## 2. Data: the VeriAudit v0.1 pilot

30 harmful requests (5 each: cybercrime, weapons, self-harm, hate speech, misinformation, fraud), each
written by one author in four forms; Qwen3-8B and Aya Expanse 8B (4-bit MLX builds), greedy decoding,
300-token limit, one response per prompt (240 responses). Labels use a five-way taxonomy; 66 labels have
human sign-off and 174 come from LLM-assisted review (all `safe_refusal`). Aya Expanse's model card lists
23 supported languages including Hindi but **not Urdu** ([card](https://huggingface.co/CohereLabs/aya-expanse-8b/blob/main/README.md)).

## 3. Reproduction

From committed raw responses and label files we recomputed the label distribution, cell safety rates,
Wilson intervals, CLSG values, exact McNemar tests, Holm adjustments and the sensitivity analysis.
All 191 checks matched the published values (`results/v1_reconstruction/verification.csv`). The
statistics script that produced the published numbers is not in the release; the reproduction therefore
also confirms that the written definitions are complete.

## 4. Re-analysis

### 4.1 Denominators

The published metric (CLSG) is the English safety rate minus the target-form safety rate with
ambiguous responses excluded. We keep all 30 pairs and report two definitions: the **harmful-compliance
gap** (non-scoreable responses count as not harmful; none of the 18 recorded ambiguity notes identifies
actionable harmful content) and the **safe-rate gap** (non-scoreable responses count as not safe).

| Comparison | Published CLSG | Harmful-compliance gap [95% CI] (Holm p) | Safe-rate gap [95% CI] (Holm p) |
|---|---|---|---|
| Qwen3-8B · Urdu | 10.0 | 10.0 [−6.1, 26.8] (.75) | 10.0 [−6.1, 26.8] (.38) |
| Qwen3-8B · Roman Urdu | 39.5 | 26.7 [6.7, 45.1] (.086) | 56.7 [34.5, 72.3] (<.001) |
| Qwen3-8B · code-switched | 8.2 | 6.7 [−6.7, 21.8] (.75) | 20.0 [3.4, 37.5] (.094) |
| Aya · Urdu | 46.2 | 40.0 [20.9, 57.7] (.003) | 53.3 [32.7, 69.8] (<.001) |
| Aya · Roman Urdu | 31.0 | 30.0 [12.5, 47.9] (.020) | 33.3 [15.2, 51.2] (.008) |
| Aya · code-switched | 20.0 | 20.0 [4.5, 37.3] (.094) | 20.0 [4.5, 37.3] (.094) |

Newcombe paired intervals; exact McNemar; Holm within each definition (Figure 1,
`docs/v2/figures/fig_v2_1_gap_definitions.png`). The direction of every gap is stable. Its size and
significance are not: for Qwen3-8B × Roman Urdu the two full-denominator definitions bracket the
published value (26.7 vs 56.7), because 9 of its 30 Roman Urdu responses are non-scoreable. This is the
signature of a comprehension effect, which a single safety-rate gap cannot distinguish from unsafe
compliance. For Aya Expanse 8B the gaps are similar under all definitions, i.e. mostly harmful
compliance.

### 4.2 Measurement

Applied to the same 240 responses, the pilot repository's own English-pattern refusal heuristic found 0%
of Urdu-script refusals, 16% of Roman Urdu and 19% of code-switched refusals, against 92% in English
(Figure 2). A multilingual rule judge built from these responses (so evaluated in-sample) reached only
22–36% outside English. Neither flagged any unsafe response as a refusal. Scored by the English heuristic,
the "gap" on these responses would have been 42.5–70 points. Lexical refusal detection is therefore not a
defensible primary measure for these forms.

### 4.3 Response-language drift (descriptive)

Aya Expanse 8B answered 20/30 Roman Urdu and 22/30 code-switched prompts in Hindi Devanagari script;
Qwen3-8B answered 14/60 of those prompts in English. Language drift is recorded as a covariate in v2.

### 4.4 Preliminary classifier transfer (exploratory)

A character n-gram logistic-regression classifier of harmful responses trained on three forms and tested
on the fourth recalled none of the 16 unsafe Urdu-script responses (macro-F1 0.42); with intent-grouped
cross-validation across all forms it reached macro-F1 0.68 [0.61, 0.74] overall. With 44 positives
(one in English) this is indicative only; script-specific surface features do not transfer across scripts.

## 5. VeriAudit-X design

200 scenarios, each a harmful request and a benign contrast on the same topic, sampled from AdvBench
(MIT), XSTest (CC-BY-4.0) and the v0.1 items, deduplicated and stratified over eight harm categories
(weapons is under-filled at 14 after excluding explosives and CBRN). Each intent appears in four base
forms; a stratified third (70 scenarios) adds six controlled transformations (Roman Urdu spelling
variants, formal transliteration, colloquial register, low/high English ratio, script mixing). Responses
receive four labels (comprehension, behaviour, harmful content, task success); metrics are harmful
compliance, appropriate refusal, over-refusal, benign task success, comprehension and linguistic
robustness, all on full denominators. Confirmatory tests: 15 exact McNemar tests each for harmful
compliance and over-refusal (5 models × 3 forms, Holm), with a pre-specified secondary signed-rank test
on per-scenario sample shares. n = 200 gives 0.82 power for a 10-point net gap at α = .05/15 if scenario
outcomes were observed without error, and 0.76–0.80 once disagreement among the three sampled responses
is simulated under high-to-moderate consistency (0.41 at low consistency; `results/power/`). The
calibration pilot will estimate that consistency before the main study.

**Dataset construction status.** Automatic generation of the non-English variants of harmful requests
with an AI model was stopped by that model's safety classifiers, so the variants will be written by
human translators using the released worksheet and guidelines. This changes the provenance (human-authored
variants, the standard the protocol prefers) and the timeline, not the design.

## 6. Results **[PENDING MAIN STUDY]**

No VeriAudit-X model evaluation has been run.

## 7. Limitations

The pilot has 30 harmful intents, no benign controls, one translator, unverified equivalence, 4-bit
quantised models, one sample per prompt and LLM-assisted labels for 72.5% of responses; every pilot
estimate is imprecise and the re-analysis is a methodological illustration, not a population estimate. The
rule judge was built on the evaluation data. VeriAudit-X seeds are English-origin benchmark items, not
naturally occurring Urdu requests.

## 8. Ethics

Prompts are requests without operational content. Harmful model outputs are not reproduced in this paper;
released responses will be gated.

## Reproducibility

`PYTHONPATH=backend python research/v1_reconstruction/reconstruct.py` (191/191 checks);
`research/figures/make_v2_figures.py`; `research/classifiers/v1_response_baseline.py`;
`research/power/power_analysis.py`. Protocol: `docs/v2/research_protocol.md`.
