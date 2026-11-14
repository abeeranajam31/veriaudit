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

Part of [VeriAudit](https://veriiaudit.vercel.app), independent research and an open-source framework on
whether multilingual AI safety evaluations measure what they claim, across English, Urdu script,
Roman Urdu and code-switched Urdu-English ([paper](https://github.com/abeeranajam31/veriaudit/blob/main/paper/v01_reanalysis/main.pdf)).

Pick a test intent, inspect its four linguistic variants, and run an
evaluation to see the resulting CLSG. This is a static (client-side
only) Space — the same illustrative-sample logic used at
[veriiaudit.vercel.app/platform](https://veriiaudit.vercel.app/platform),
ported to plain JS so it needs no server-side compute.

⚠️ **Illustrative data.** Model scores are deterministic, illustrative
placeholders under fictional codenames — no real model is queried, and the
names do not correspond to any real product. Linguistic variants are the
human-authored
[CLSG-Benchmark starter set](https://huggingface.co/datasets/abeeranajam31/CLSG-Benchmark)
(13 intents; the 200-scenario VeriAudit-X benchmark is in development).

## Related resources

- Dataset: [`abeeranajam31/CLSG-Benchmark`](https://huggingface.co/datasets/abeeranajam31/CLSG-Benchmark)
- Framework: [`abeeranajam31/CLSG-Evaluator`](https://huggingface.co/abeeranajam31/CLSG-Evaluator)
- Full platform (with the FastAPI backend evaluation pipeline): [veriiaudit.vercel.app](https://veriiaudit.vercel.app)
- Source: [github.com/abeeranajam31/veriaudit](https://github.com/abeeranajam31/veriaudit)
- Methodology: [docs/methodology.md](https://github.com/abeeranajam31/veriaudit/blob/main/docs/methodology.md)

## Responsible use

Some intents are red-teaming test cases (generic, non-actionable
prompts used to test refusal consistency). See the dataset card's content
warning. This demo does not generate real model responses to any prompt.

Contact: veriiaudit@gmail.com
