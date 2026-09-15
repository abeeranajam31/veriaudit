# Ljubljana Research Connection

Researched and verified 2026-09-15 (web search + primary sources, not
assumed). This grounds VERIAUDIT's v0.1 pilot in a specific, real research
lineage rather than a general "LLMs4EU" reference.

## The group

**Machine Learning and Language Technologies Lab**, Faculty of Computer
and Information Science (FRI), University of Ljubljana — headed by
**Prof. Marko Robnik-Šikonja**
([FRI profile](https://fri.uni-lj.si/en/employees/marko-robnik-sikonja)).
This group leads Slovenia's participation in:

- **LLMs4EU** — EU-wide project (69 partners, 20 countries) building open
  LLMs for all EU languages. Ljubljana leads the search engine/catalogue
  for the language-technology tool registry and contributes to a planned
  **European network of evaluation centres** that will assess models on
  *"performance, robustness, safety, cybersecurity, compliance with
  European legislation, and alignment with human values."*
  ([uni-lj.si announcement](https://www.uni-lj.si/en/news/2026-09-02-development-of-language-models-in-all-eu-languages))
- **LLM4DH** — national project benchmarking LLMs for Slovenian.
  ([2025 publications](https://www.cjvt.si/llm4dh/en/publications-2025/))

## Paper #1 (primary reproduction target)

**Žagar, A. & Robnik-Šikonja, M. (2022). "Slovene SuperGLUE Benchmark:
Translation and Evaluation."** [arXiv:2202.04994](https://arxiv.org/abs/2202.04994)

| | |
|---|---|
| Research question | Does translation method affect benchmark reliability when an English NLU benchmark is adapted to a lower-resource language? |
| Dataset | SuperGLUE (RTE, CoLA, MRPC, QQP, SST-2, QNLI, etc.) |
| Languages | English → Slovene |
| Method compared | Google Translate vs. DeepL vs. human translation |
| Models | BERT (multi/mono), XLM-RoBERTa, SloBERTa |
| Metrics | Accuracy / task-specific metrics, compared across translation source |
| Main finding | Machine-translated benchmark versions showed a measurable gap from human-translated ones — translation quality materially changes what a benchmark measures |
| **What VERIAudit can reproduce** | The core comparison: run the same evaluation against MT-derived vs. human-authored variants of the same intent, and measure whether the gap is an artifact of translation quality rather than the model's underlying behavior |
| **What VERIAudit extends** | From general NLU accuracy to AI *safety* behavior specifically, and from Slovene to Urdu (further from English, more code-switching in real usage) |

**The direct link to VERIAudit's own known weak point:** the site already
states (see `docs/metric.md`) that EquivEngine's similarity screening is
"a screening signal, not proof of equivalence" — Žagar & Robnik-Šikonja
give this exact concern empirical teeth. The pilot should test it
directly rather than just cite it.

## Paper #2 (secondary precedent, same institutional lineage)

**Brglez & Vintar — "SloPragEval: Creating the First Pragmatics
Understanding Benchmark for Slovene"** (LLM4DH, 2025). Same
"first benchmark of kind X for under-resourced language Y" framing
pattern VERIAudit uses for Urdu safety evaluation — useful as a second
citable precedent from the same institutional context, not a
reproduction target itself.

## Broader landscape (related work, not Ljubljana-affiliated)

Recent (2026) sibling projects doing the same kind of work for other
under-resourced languages — cite as related work to show the niche is
active, not reproduce:

- KZ-SafetyPrompts (Kazakh) — [arXiv:2605.26947](https://arxiv.org/pdf/2605.26947)
- AlbanianLLMSafety — [arXiv:2605.26954](https://arxiv.org/pdf/2605.26954)
- Schützen (Bulgarian/German safety eval) — [arXiv:2606.11316](https://arxiv.org/pdf/2606.11316)
- IndicSafeEval (multilingual persuasive jailbreak) — [arXiv:2609.03781](https://arxiv.org/html/2609.03781)

## The reproduction/extension sentence for the application

> "Žagar & Robnik-Šikonja (2022) showed that translation method
> meaningfully affects benchmark reliability when English NLU tasks are
> adapted to Slovene. VERIAudit extends this concern from general NLU
> accuracy to AI safety specifically: does translation method and
> quality affect *measured safety behavior* when the same evaluation is
> run in Urdu, and does this interact with the Cross-Lingual Safety Gap
> metric?"
