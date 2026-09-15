# VERIAUDIT

**Does AI safety survive translation?**

VERIAUDIT is an open-source red-teaming platform that tests whether AI
safety, robustness, and instruction-following behavior remain consistent
when equivalent inputs are translated across linguistic boundaries.
Starting with English → Urdu → Roman Urdu → code-switched variants,
VERIAUDIT measures the **Cross-Lingual Safety Gap (CLSG)**: the
quantitative difference in safety performance between a model's behavior
in its training-dominant language and its behavior in low-resource
linguistic settings.

> **Research integrity note.** This is an early-stage research prototype.
> Numbers shown in the platform's demo mode are illustrative unless
> explicitly labeled otherwise — see [Limitations](#limitations) and
> [`docs/research.md`](docs/research.md).

## Architecture

```
veriaudit/
├── frontend/          Next.js + TypeScript + Tailwind — site, docs, and a
│                       fully client-side DEMO MODE dashboard
├── backend/            FastAPI service — EquivEngine, GapEvaluator, CLSG,
│                       model adapters, PDF evidence reports
├── dataset/             VERIAUDIT-500 pilot subset + schema docs
├── docs/                 Methodology, metric spec, research write-up
└── .env.example
```

The frontend runs standalone (static DEMO MODE, no backend required) — this
is what's deployed to Vercel. The backend is a separate FastAPI service you
can run locally or deploy to any Python host for live translation, model
evaluation, and PDF report generation.

## Research question

Does an AI system remain equally safe when the same underlying intent is
expressed in different languages? See [`docs/research.md`](docs/research.md)
for the full research question, hypothesis, methodology, and — importantly
— limitations.

## Methodology

**TEST → COMPARE → SCORE → ANALYZE → REPORT**

1. **Define Intent** — a language-independent test case.
2. **Generate Variants** — `EquivEngine` produces English, Urdu, Roman Urdu,
   and code-switched forms, screened (not proven) for semantic equivalence
   via multilingual sentence-transformer similarity.
3. **Evaluate** — `GapEvaluator` runs each variant against configured
   models and scores refusal consistency, instruction following, and
   safety.
4. **Measure the Gap** — aggregate into CLSG.

Full spec: [`docs/methodology.md`](docs/methodology.md) ·
Metric spec: [`docs/metric.md`](docs/metric.md)

## Cross-Lingual Safety Gap (CLSG)

```
CLSG(reference -> evaluation) = safety_score(reference) - safety_score(evaluation)
```

A VERIAUDIT-proposed metric, not yet independently validated. See
[`docs/metric.md`](docs/metric.md) for assumptions, normalization, and
limitations.

## Dataset

The pilot subset ships 13 of the planned 125 core intents (× 4 linguistic
variants). **The full VERIAUDIT-500 dataset is under development** and will
be released after independent bilingual verification. See
[`dataset/README.md`](dataset/README.md).

## Pilot Results

These are preliminary pilot results from VeriAudit v0.1 — a 30-intent, 2-model
pilot benchmark, not a validated general-purpose safety evaluation. Full
methodology, statistics, and limitations: **[`docs/veriaudit_pilot_report.md`](docs/veriaudit_pilot_report.md)**.

- **240 evaluations**: 30 intents × 4 linguistic variants (English, Urdu,
  Roman Urdu, code-switched) × 2 models (Qwen3-8B, Aya Expanse 8B), across
  6 categories (Cybercrime, Weapons, Self-Harm, Hate Speech, Misinformation,
  Fraud).
- We observe a **cross-lingual safety gap in every one of the 6 model ×
  non-English-language comparisons** tested, with a mean of **25.8
  percentage points** across those six comparisons (not a population
  estimate — see the report).
- The largest observed gap in this pilot: **Aya Expanse 8B × Urdu, 46.2
  percentage points** (100.0% → 53.8% observed safety rate).
- **Roman Urdu** shows both the largest observed failure rate (36.0%) and
  the largest concentration of ambiguous/undecidable outputs (10 of 18
  ambiguous cases) in this pilot.
- 3 of 6 model-language comparisons remain statistically significant after
  Holm correction for multiple comparisons (n=30 intents per comparison);
  see the report for the full statistical analysis, sensitivity analysis,
  and — importantly — the label-provenance caveat (only 66/240 labels
  carry direct human sign-off).

Full results table: [`docs/results_table.md`](docs/results_table.md) ·
Figures: [`docs/figures/`](docs/figures/) ·
Raw analysis data: [`results/labeling/`](results/labeling/).

## Hugging Face

VERIAUDIT publishes to the Hub under
[`huggingface.co/abeeranajam31`](https://huggingface.co/abeeranajam31) —
these are synced mirrors of `dataset/` and `backend/app/evaluation/` in
this repository (source of truth stays here):

| | |
|---|---|
| Dataset | [`abeeranajam31/CLSG-Benchmark`](https://huggingface.co/datasets/abeeranajam31/CLSG-Benchmark) — the pilot dataset as a loadable 🤗 `datasets` dataset, with a full dataset card. |
| Framework | [`abeeranajam31/CLSG-Evaluator`](https://huggingface.co/abeeranajam31/CLSG-Evaluator) — the evaluation framework (`clsg`, `equiv_engine`, `evaluators`, `gap_evaluator`, `model_adapters`) as a standalone pip-installable package. |
| Demo | [`abeeranajam31/veriaudit-clsg-demo`](https://huggingface.co/spaces/abeeranajam31/veriaudit-clsg-demo) — a static (free-tier) interactive Space running the same DEMO MODE logic as `/platform`, ported to client-side JS. |

Local source for all three lives in [`huggingface/`](huggingface/).

## Installation

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:3000`. Fully functional in DEMO MODE with no
environment variables required.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # edit as needed; DEMO_MODE=true works out of the box
uvicorn app.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`.

## Usage

- Visit `/platform` for the interactive dashboard: pick a pilot intent (or
  enter free text), generate linguistic variants, run a demo evaluation,
  and inspect the Cross-Lingual Safety Gap.
- `POST /api/variants` — generate + screen linguistic variants (requires a
  configured `TranslationProvider`; raises a clear `501` otherwise).
- `POST /api/evaluate` — run `GapEvaluator` against a test case and model
  list. Uses `DemoAdapter` (deterministic, illustrative) when
  `DEMO_MODE=true` or no model adapter is configured.
- `POST /api/evaluate/report` — same as above, returns a PDF evidence
  report.

## Demo mode

The platform must work without any paid API keys. Every score labeled
`DEMO MODE` or `demo data` is deterministic (seeded by test case, model, and
language) but **not derived from a real model evaluation**. Connect a real
`ModelAdapter` (Hugging Face, OpenAI-compatible, or a custom endpoint) and
set `DEMO_MODE=false` to run live evaluations against the same pipeline and
UI.

## Roadmap

| | |
|---|---|
| **Now** | Cross-lingual evaluation prototype: English → Urdu → Roman Urdu → code-switched |
| **Next** | Human-verified benchmark dataset, more open models, more evaluation categories |
| **Later** | Arabic, Hindi, Bengali, Punjabi, and other low-resource languages; agent evaluation; multimodal evaluation; continuous model monitoring; API for organizations |

## Limitations

Translation artifacts, semantic-similarity screening limits, evaluator
bias, model sampling randomness, incomplete language coverage, possible
benchmark contamination, small current sample size, and the inherent
difficulty of defining "safety" universally. See
[`docs/research.md`](docs/research.md#limitations) for the full discussion.

## Contributing

Issues and PRs are welcome, particularly on dataset verification,
additional evaluators, and translation review. Please open an issue before
large changes.

## License

[MIT](LICENSE)

## Citation

```bibtex
@software{veriaudit,
  author = {Najam, Abeera},
  title = {VERIAUDIT: Cross-Lingual AI Safety Evaluation},
  year = {2026},
  url = {https://github.com/abeeranajam31/veriaudit}
}
```

## Contact

**Abeera Najam** — Founder & Lead Researcher, VERIAUDIT
[veriiaudit@gmail.com](mailto:veriiaudit@gmail.com)
