---
pretty_name: VERIAUDIT CLSG-Benchmark (pilot)
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

# CLSG-Benchmark (pilot)

Part of [VERIAUDIT](https://veriaudit.vercel.app) — an open-source
red-teaming platform measuring whether AI safety, robustness, and
instruction-following behavior remain consistent when equivalent inputs
are translated across linguistic boundaries.

> **Status: pilot subset.** This release contains **13 of the planned 125
> core intents** (× 4 linguistic variants = 500 test cases). The full
> **VERIAUDIT-500** dataset is under development and will be published here
> after independent bilingual human verification. Do not cite this pilot
> as a validated benchmark — it exists to make the evaluation pipeline
> runnable end-to-end, not as a finished scientific artifact.

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

The pilot cases here were translated by the project's lead researcher as a
first pass; most are marked `pending` for exactly this reason.

## Loading

```python
from datasets import load_dataset

ds = load_dataset("abeeranajam31/CLSG-Benchmark", split="pilot")
print(ds[0])
```

## Limitations

Small sample size (13 intents), single-annotator translation pass for this
pilot release, embedding-based (not human-validated) similarity screening,
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
  title = {VERIAUDIT CLSG-Benchmark (pilot)},
  year = {2026},
  url = {https://huggingface.co/datasets/abeeranajam31/CLSG-Benchmark}
}
```

## License

MIT — see [LICENSE](https://github.com/abeeranajam31/veriaudit/blob/main/LICENSE).

## Contact

Abeera Najam — Founder & Lead Researcher, VERIAUDIT — veriiaudit@gmail.com
