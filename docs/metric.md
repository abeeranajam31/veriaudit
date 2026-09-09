# Metric: Cross-Lingual Safety Gap (CLSG)

> **VERIAUDIT proposed metric — not yet independently validated.**

## Motivation

Safety evaluation is dominated by English-language benchmarks. If a
model's refusal behavior, instruction-following, or resistance to harmful
requests changes materially when the same intent is expressed in another
language, that shift is invisible to a single-language benchmark. CLSG
gives that shift a name and a number.

## Formula

```
CLSG(reference -> evaluation) = safety_score(reference) - safety_score(evaluation)
```

`safety_score` is a 0–100 aggregate computed identically for both languages
over a fixed test-case set. A positive CLSG means the model was measurably
less safe in the evaluation language. An average CLSG across models and
evaluation languages can be reported relative to a single reference
language (typically English, since it is the training-dominant language
for most widely deployed models today).

Reference implementations: [`frontend/src/lib/clsg.ts`](../frontend/src/lib/clsg.ts)
and [`backend/app/evaluation/clsg.py`](../backend/app/evaluation/clsg.py).

## Assumptions

- The reference and evaluation variants express the same underlying intent
  (semantic equivalence, screened but not guaranteed — see
  [`dataset/README.md`](../dataset/README.md)).
- The safety scoring rubric is applied identically regardless of language.
- Test cases are representative of the categories they claim to cover, not
  exhaustive.
- Model outputs are sampled under comparable decoding settings across
  languages.

## Normalization

Safety scores are bounded to `[0, 100]` before differencing, so CLSG is
reported in percentage points rather than a ratio. This keeps the metric
interpretable at the cost of not correcting for a category's intrinsic
difficulty — a harder category will tend to show larger absolute gaps even
at equal relative degradation. Per-category CLSG should be reported
alongside the aggregate for this reason.

## Limitations

- CLSG has not been validated against human judgment at scale.
- It is sensitive to translation quality and the semantic-equivalence
  similarity threshold used for screening.
- A single scalar cannot capture the full shape of behavioral difference —
  pair it with a failure-taxonomy breakdown (refusal inconsistency, partial
  compliance, harmful compliance, instruction-following shift, prompt
  injection susceptibility).
- Comparisons across unrelated language pairs, or across evaluations run on
  different underlying datasets, are not meaningful.

## Future validation

Planned work includes correlating CLSG against human-annotated safety
judgments, testing sensitivity to translation provider and similarity
threshold choice, and publishing inter-annotator agreement statistics once
the full VERIAUDIT-500 dataset is human-verified.
