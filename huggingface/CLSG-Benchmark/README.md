---
pretty_name: VeriAudit CLSG-Benchmark (starter set)
license: mit
language:
  - en
  - ur
task_categories:
  - text-classification
  - text-generation
tags:
  - ai-safety
  - red-teaming
  - cross-lingual
  - urdu
  - low-resource
  - llm-evaluation
size_categories:
  - n<1K
configs:
  - config_name: default
    data_files:
      - split: pilot
        path: data/pilot.jsonl
---

# CLSG-Benchmark (starter set)

Part of [VeriAudit](https://veriiaudit.vercel.app), independent research and an open-source framework on
whether multilingual AI safety evaluations measure what they claim. When a model looks less safe in
Urdu, is it producing harmful content, failing to understand the request, or being misjudged by an
evaluator built for English?

Findings so far ([paper](https://github.com/abeeranajam31/veriaudit/blob/main/paper/v01_reanalysis/main.pdf), [code](https://github.com/abeeranajam31/veriaudit)):

- **Refusal detection collapses outside English.** An English-pattern detector caught 92% of English
  refusals but 0 of 40 Urdu-script refusals.
- **Denominator choices move the headline gap.** Qwen3-8B's Roman Urdu gap changes from 39.5 to 26.7
  points when non-scoreable outputs are counted rather than dropped.
- **Script drift.** Aya Expanse 8B answers 71% of Roman Urdu prompts in Hindi script.

> **This repository is the starter set:** 13 intents × 4 linguistic forms, used to make the evaluation
> pipeline runnable end to end. The research benchmark, **VeriAudit-X**, has 200 scenarios with
> matched benign contrasts. It is translated and reviewed by independent bilingual annotators, and
> will be published here after human verification. Cite the paper for findings, not this starter set.

## ⚠️ Content warning

This dataset includes **red-teaming test intents** designed to probe
whether a model refuses unsafe requests — including prompts related to
cybercrime, weapons, self-harm, hate speech, misinformation, fraud, and
privacy violations. Prompt text is deliberately generic and non-actionable
(no real operational detail or uplift), in the same style used by public
red-teaming benchmarks such as AdvBench and HarmBench. It is provided
**for AI safety evaluation and refusal-consistency research only**. Do not
use this dataset to elicit, collect, or distribute harmful content, and do
not use model outputs generated against it for any purpose other than
safety research.

## What this dataset is for

Each row expresses a **single underlying intent** in four linguistic
forms — English, Urdu, Roman Urdu, and code-switched Urdu/English — so
that a model's safety and instruction-following behavior can be compared
*for the same request* across languages. This is the input to VERIAUDIT's
**Cross-Lingual Safety Gap (CLSG)** metric — see
[CLSG-Evaluator](https://huggingface.co/abeeranajam31/CLSG-Evaluator) and
the [methodology doc](https://github.com/abeeranajam31/veriaudit/blob/main/docs/methodology.md).

## Schema

| Field | Type | Description |
|---|---|---|
| `id` | string | Stable identifier, `VA-###`. |
| `intent_category` | string | e.g. `Benign — Everyday Assistance`, `Refusal Test — Cybercrime`. |
| `intent` | string | Short human-readable description of the underlying test intent. |
| `english` | string | The intent expressed in English. |
| `urdu` | string | The intent expressed in Urdu script. |
| `roman_urdu` | string | The intent expressed in Roman-script Urdu. |
| `code_switched` | string | The intent expressed in code-switched Urdu/English. |
| `verification_status` | string | `verified`, `pending`, or `flagged`. See below — never inferred purely from a similarity score. |
| `semantic_similarity` | object | Embedding cosine similarity (multilingual sentence-transformer) between English and each other variant. A **screening signal only**. |

## Verification process

1. A variant is machine-translated or human-authored.
2. Embedding similarity is computed against the English source
   (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`).
3. Similarity below `0.85` is marked `flagged`.
4. Everything else starts as `pending` — **similarity above the threshold
   is never treated as automatic proof of equivalence.**
5. A human reviewer promotes a case to `verified` after manual comparison.

The cases here were translated by the project's lead researcher as a
first pass; most are marked `pending` for exactly this reason.

## Loading

```python
from datasets import load_dataset

ds = load_dataset("abeeranajam31/CLSG-Benchmark", split="pilot")  # split name kept for compatibility
print(ds[0])
```

## Limitations

Small sample size (13 intents), single-annotator translation pass for this
starter release, embedding-based (not human-validated) similarity screening,
and coverage limited to Urdu / Roman Urdu / code-switched Urdu-English.
See [`docs/research.md`](https://github.com/abeeranajam31/veriaudit/blob/main/docs/research.md#limitations)
for the full limitations discussion.

## Responsible use

Intended for AI safety and red-teaming research, refusal-consistency
evaluation, and multilingual NLP research. Not intended for training
generative models to produce harmful content, and not a substitute for
professional crisis support — if you or someone you know is struggling,
please reach out to a local crisis line.

## Citation

```bibtex
@dataset{veriaudit_clsg_benchmark,
  author = {Najam, Abeera},
  title = {VeriAudit CLSG-Benchmark (starter set)},
  year = {2026},
  url = {https://huggingface.co/datasets/abeeranajam31/CLSG-Benchmark}
}
```

## License

MIT — see [LICENSE](https://github.com/abeeranajam31/veriaudit/blob/main/LICENSE).

## Contact

Abeera Najam — Lead Researcher, VeriAudit — veriiaudit@gmail.com
