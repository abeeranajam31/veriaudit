---
title: VERIAUDIT CLSG Demo
emoji: 🛡️
colorFrom: green
colorTo: gray
sdk: static
pinned: false
license: mit
tags:
  - ai-safety
  - red-teaming
  - cross-lingual
  - urdu
  - llm-evaluation
---

# VERIAUDIT — CLSG interactive demo

Part of [VERIAUDIT](https://veriaudit.vercel.app) — an open-source
red-teaming platform measuring the **Cross-Lingual Safety Gap (CLSG)**
between a model's safety behavior in English and in Urdu / Roman Urdu /
code-switched Urdu-English.

Pick a pilot test intent, inspect its four linguistic variants, and run an
evaluation to see the resulting CLSG. This is a static (client-side
only) Space — the same illustrative-sample logic used at
[veriaudit.vercel.app/platform](https://veriaudit.vercel.app/platform),
ported to plain JS so it needs no server-side compute.

⚠️ **Illustrative data.** Model scores are deterministic, illustrative
placeholders under fictional codenames — no real model is queried, and the
names do not correspond to any real product. Linguistic variants are the
human-authored
[CLSG-Benchmark pilot dataset](https://huggingface.co/datasets/abeeranajam31/CLSG-Benchmark)
(13 intents so far, not the full planned 500).

## Related resources

- Dataset: [`abeeranajam31/CLSG-Benchmark`](https://huggingface.co/datasets/abeeranajam31/CLSG-Benchmark)
- Framework: [`abeeranajam31/CLSG-Evaluator`](https://huggingface.co/abeeranajam31/CLSG-Evaluator)
- Full platform (with the FastAPI backend evaluation pipeline): [veriaudit.vercel.app](https://veriaudit.vercel.app)
- Source: [github.com/abeeranajam31/veriaudit](https://github.com/abeeranajam31/veriaudit)
- Methodology: [docs/methodology.md](https://github.com/abeeranajam31/veriaudit/blob/main/docs/methodology.md)

## Responsible use

Some pilot intents are red-teaming test cases (generic, non-actionable
prompts used to test refusal consistency). See the dataset card's content
warning. This demo does not generate real model responses to any prompt.

Contact: veriiaudit@gmail.com
