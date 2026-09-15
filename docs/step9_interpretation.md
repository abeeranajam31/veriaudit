# v0.1 Pilot — Interpretation (Preliminary)

**Status: preliminary, LLM-assisted labels only. No human review has been
performed.** Every number below comes from `results/labeling/labels.jsonl`
(240 rows), labeled per `docs/labeling_protocol.md`. Treat this as a
first read to prioritize human review, not a finished result.

## A. Safety behavior

Overall preliminary label counts across all 240 evaluations:

| Label | Count | % |
|---|---:|---:|
| `safe_refusal` | 163 | 67.9% |
| `ambiguous` | 34 | 14.2% |
| `unsafe_compliance` | 30 | 12.5% |
| `partial_compliance` | 13 | 5.4% |

By linguistic form:

| Form | `safe_refusal` | `unsafe_compliance` | `partial_compliance` | `ambiguous` |
|---|---:|---:|---:|---:|
| English | 59/60 (98.3%) | 0 | 1 | 0 |
| Urdu | 35/60 (58.3%) | 12 | 4 | 9 |
| Roman Urdu | 27/60 (45.0%) | 13 | 4 | 16 |
| Code-switched | 42/60 (70.0%) | 5 | 4 | 9 |

**English is the only form with essentially no compliance or ambiguity —
59 of 60 responses were clean, appropriate refusals** (the one exception
is the fabricated-quote-with-disclaimer partial-compliance case, which
appeared in English too, not only non-English forms). Every other form
shows a materially different pattern. This is consistent with — and now
backed by real, labeled data for — the research question the pilot set
out to test: does safety behavior stay consistent across linguistic
variants of the same intent? **On this pilot's preliminary labels, no.**

By model: Aya Expanse 8B had more `unsafe_compliance` (22 vs. 8) but fewer
`ambiguous` (8 vs. 26) than Qwen3-8B. A large share of Qwen3's `ambiguous`
count is degenerate/repetitive generation (see Section C) rather than
comprehensible-but-unclear responses — the two models' weaknesses look
different in kind, not just degree.

**What we are not claiming:** we are not claiming Urdu is "less safe" as
a language, or that this generalizes beyond these two specific models,
this specific 30-intent set, and this specific pilot run. See Section E.

## B. Response-language behavior

`response_language` was computed independently of the safety label (see
labeling protocol) and does not predict it — Section 5 of
`docs/notable_examples.md` shows the same language switch occurring in
both a safe and an unsafe response.

- **Aya Expanse frequently answers in Hindi (Devanagari script)** for
  Roman Urdu and code-switched prompts — a plausible explanation is
  romanized-Urdu / romanized-Hindi confusion, since the two are phonologically
  close and the Latin transliteration removes the script cue that
  normally distinguishes them. This is a hypothesis based on the pattern
  observed, not a confirmed mechanism.
- **Aya Expanse also sometimes answers in Persian/Farsi** for Urdu-script
  prompts (7 confirmed instances during manual review — see Section C for
  why this is undercounted in the automated `language_consistency_issue`
  field). A plausible explanation is script/vocabulary overlap between
  Urdu and Persian (both Perso-Arabic script, historically related
  vocabulary), again a hypothesis, not a confirmed mechanism.
- Automated `language_consistency_issue` flag: **49 of 240 responses
  (20.4%)** — an undercount of the true rate, per Section C.

## C. Evaluator / methodological limitations

Reported honestly because they materially affect how much weight these
results should carry:

1. **`response_language` cannot distinguish Persian from Urdu.** Both use
   the same Unicode script block, and the automated detector only does
   script analysis. Seven Persian responses were identified only through
   manual reading and are recorded as `urdu` in the automated field — the
   true `language_consistency_issue` rate is higher than 49/240.
2. **Degenerate/repetitive generation is common enough to be a real
   confound.** Many `ambiguous` labels are not "the safety judgment is
   unclear" but "the model produced a repetition loop and never completed
   a coherent response." This is a known failure mode of small
   (8B-parameter), heavily quantized (4-bit) models under greedy decoding,
   and it may be partially an artifact of the evaluation setup (temperature
   0.0, `max_tokens=300`) rather than purely a property of the model.
3. **Single labeler, no inter-rater agreement.** All 240 preliminary
   labels come from one LLM-assisted read (this session). No second
   opinion — human or model — has checked them yet. Confidence levels
   (`high`/`medium`/`low`) are this labeler's own self-assessment, not a
   calibrated measure.
4. **The rule-based first pass's refusal lexicon was incomplete** — of
   157 responses it routed to `needs_review`, roughly a third turned out
   to be refusals phrased in ways the regex didn't anticipate (e.g.
   "nahi likh sakta" vs. the lexicon's "nahi kar sakt*"). This was
   corrected via full-text reading, but means the *initial* rule-based
   pass alone would have substantially overcounted concerning responses —
   a caution for anyone tempted to skip the manual-review step at scale.
5. **The evaluated models' non-English refusal training may simply be
   weaker**, independent of any deep "cross-lingual" mechanism — this
   pilot cannot distinguish "the model reasons less safely in Urdu" from
   "the model was fine-tuned on far more English refusal examples than
   Urdu ones." Both are consistent with the same observed pattern.
6. **30 intents, one run each, greedy decoding.** No repeated sampling,
   no confidence intervals, no test of whether results are stable across
   decoding settings.

## D. Unexpected findings

Findings the pilot's design did not predict in advance:

- **The single most severe finding (Aya, Urdu, self-harm concealment
  validation) occurred in the most safety-critical category**, not a
  lower-stakes one — this was not something the annotation scheme or the
  pilot's research questions specifically anticipated.
- **Fabricated-quote requests produced a distinct "partial compliance
  with self-disclosure" pattern** (generate the harmful artifact, then
  immediately flag it as fake) in both models — a middle behavior the
  five-label taxonomy accommodates but that wasn't specifically designed
  around.
- **Degenerate repetition as a confound with safety labeling** (Section
  C.2) was not anticipated when the labeling protocol was written; it
  turned out to be one of the most common reasons for an `ambiguous`
  label.
- **Compliance was not simply "worse in more distant forms."** Roman
  Urdu had the *most* `ambiguous` responses but not the most
  `unsafe_compliance` (13, close to Urdu's 12); code-switched — arguably
  the most linguistically distant from clean training data — had the
  *fewest* unsafe/partial cases outside English. The pattern is real but
  not a simple monotonic "further from English → less safe" gradient.

## E. Questions requiring further investigation

- Does this pattern replicate on the full 100-intent benchmark, or on a
  larger, human-verified variant set?
- Does it hold with non-greedy decoding / repeated sampling (ruling out
  single-sample noise)?
- Can the Persian/Hindi language-switching be explained directly (e.g. by
  inspecting tokenizer/training-data statistics for these models), rather
  than left as a plausible hypothesis?
- Is the degenerate-repetition failure mode reduced with a higher
  `max_tokens` budget or a repetition penalty in generation settings?
- Does the pattern hold for other open-weight multilingual models, or is
  it specific to these two?
- What does human review actually confirm or overturn from this
  preliminary pass — in particular, do the `medium`/`low`-confidence
  `ambiguous` and `partial_compliance` calls hold up?

## Final counts for this labeling run

- **Total responses labeled:** 240
- **By preliminary label:** `safe_refusal` 163, `ambiguous` 34,
  `unsafe_compliance` 30, `partial_compliance` 13
- **Requiring human review (all of them, by design):** 240 — prioritized
  in `results/labeling/review_priority.csv`, unsafe_compliance first
- **Unsafe/partial compliance cases found:** 43 (30 unsafe + 13 partial)
- **Language-consistency issues flagged (automated, known undercount):**
  49 of 240 (20.4%)
- **Files created this session:** `docs/labeling_protocol.md`,
  `results/labeling/labels.jsonl`, `results/labeling/build_preliminary_labels.py`,
  `results/labeling/apply_llm_review.py`, `results/labeling/review_priority.csv`,
  `results/labeling/labeling_run_metadata.json`, `docs/notable_examples.md`,
  `docs/step9_interpretation.md` (this file)
- **Not created, intentionally:** `results/label_summary.csv` and
  `results/model_language_safety_summary.csv` — gated on human labels per
  the labeling task's own instructions, which have not been performed.
  CLSG has not been calculated.
- **Raw 240 responses:** unmodified throughout — `results/raw/pilot_v0.1/all_responses.jsonl`
  is untouched.
