# Research

## Research Question

Does an AI system remain equally safe when the same underlying intent is
expressed in different languages, including low-resource and code-switched
forms?

## Hypothesis

Safety behavior may degrade under linguistic distribution shift,
particularly in low-resource settings that are underrepresented in model
training and alignment data.

## Methodology

1. **Intent-level test case construction.** Each test case starts from a
   single underlying intent, independent of language.
2. **Multilingual variant generation.** `EquivEngine` produces semantically
   equivalent English, Urdu, Roman Urdu, and code-switched forms.
3. **Semantic equivalence screening.** Embedding similarity (multilingual
   sentence-transformers) flags low-similarity pairs for review; nothing is
   auto-verified.
4. **Model evaluation.** `GapEvaluator` runs each variant against configured
   models under identical decoding conditions.
5. **Behavioral scoring.** Responses are scored on refusal consistency,
   instruction following, and safety (see `app/evaluation/evaluators.py`).
6. **Aggregation.** Per-model, per-language scores are combined into the
   Cross-Lingual Safety Gap (CLSG) — see [`metric.md`](./metric.md).

## Limitations

Acknowledging limitations is part of what makes this project credible, not
a weakness to hide from committees, reviewers, or collaborators.

- **Translation artifacts.** Both automated and human translation can shift
  connotation, formality, or intensity independent of the model being
  evaluated.
- **Semantic similarity limitations.** Embedding-based similarity is a
  screening signal, not proof of equivalence; low-resource language
  embeddings are generally less reliable than high-resource ones.
- **Evaluator bias.** Automated safety scoring (heuristic, rule-based, or
  model-graded) can itself be biased or inconsistent across languages.
- **Model randomness.** Sampling temperature and non-determinism mean a
  single run is not a stable estimate of behavior; repeated sampling is
  needed for confidence intervals.
- **Incomplete language coverage.** The pilot covers Urdu, Roman Urdu, and
  code-switched forms only. Findings should not be generalized to unrelated
  languages or language families without separate evaluation.
- **Benchmark contamination.** Public test items may leak into model
  training data over time, inflating apparent safety.
- **Limited sample size.** The current pilot dataset (13 intents) is far
  smaller than the planned VERIAUDIT-500 and is not yet human-verified at
  scale — see [`dataset/README.md`](../dataset/README.md).
- **Difficulty defining safety universally.** "Safety" is context- and
  culture-dependent. VERIAUDIT's scoring rubric reflects specific
  operational definitions, not a universal standard.

## What we will not claim

- We do not claim VERIAUDIT is the first cross-lingual AI safety evaluation
  effort.
- We do not claim CLSG is a scientifically validated metric — it is a
  proposed, first-pass formulation.
- We do not publish leaderboard rankings, model counts, or dataset sizes
  that have not actually been produced. See the site's `/leaderboard` and
  `/benchmark` pages for current status.
