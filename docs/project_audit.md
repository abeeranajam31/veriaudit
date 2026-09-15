# VERIAUDIT — Project Audit (2026-09-15)

Honest inventory of what exists today, split into **real** (built, tested,
verifiable) and **illustrative/placeholder** (labeled as such, not yet
backed by real experimental results). Written before any further changes,
per the plan to establish ground truth before building the v0.1 pilot.

## What's real

| Component | Status | Evidence |
|---|---|---|
| Frontend (Next.js/TS/Tailwind) | Deployed, working | [veriaudit.vercel.app](https://veriaudit.vercel.app) |
| Backend (FastAPI) — `EquivEngine`, `GapEvaluator`, `CLSG` calc, model adapters, PDF reports | Built, 27 passing pytest tests | `backend/` |
| CLSG metric — formula, docs | Defined, documented, explicitly labeled "not yet independently validated" | `docs/metric.md`, site `/methodology` |
| Pilot dataset | **13 intents** × 4 forms (English/Urdu/Roman Urdu/code-switched), human-authored by one annotator | `dataset/examples/veriaudit-pilot.jsonl` |
| Hugging Face — `CLSG-Benchmark` | Live dataset repo, loads via `datasets.load_dataset`, same 13-intent pilot | huggingface.co/datasets/abeeranajam31/CLSG-Benchmark |
| Hugging Face — `CLSG-Evaluator` | Live, pip-installable framework mirror of `backend/app/evaluation/` | huggingface.co/abeeranajam31/CLSG-Evaluator |
| Hugging Face — `veriaudit-clsg-demo` | Live static Space, client-side demo | huggingface.co/spaces/abeeranajam31/veriaudit-clsg-demo |
| GitHub | Public, all of the above committed | github.com/abeeranajam31/veriaudit |
| Separate project: Urdu Emergency Communication Corpus | Real corpus-linguistics pilot (60 utterances), different domain, own repo + HF dataset | github.com/abeeranajam31/urdu-emergency-corpus |

## What's illustrative / not yet real

| Component | Current state | What "real" would require |
|---|---|---|
| Demo-mode safety scores (Atlas-7B/Meridian-13B/Vantage-Pro) | Deterministic, seeded, fictional-model placeholders — explicitly labeled "illustrative data" everywhere they appear | Real model calls via `HuggingFaceAdapter`/`OpenAIAdapter`, real response scoring |
| CLSG example numbers ("23 pts", "28 pts" in the plan you pasted) | Not computed from any real run | Computed from actual evaluation output |
| Semantic-equivalence verification | Manual similarity scores (0.83–0.95), single-annotator, no formal human sign-off process run yet | 2+ reviewers, recorded ratings, inter-rater agreement |
| Response labeling scheme (safe refusal / partial compliance / unsafe compliance) | Not yet formally defined — `evaluators.py` uses simple keyword-heuristic scoring, not a defined label taxonomy | Explicit label definitions + a real annotated set of model responses |
| Leaderboard | Deliberately empty ("coming soon") — no fabricated rankings | Real multi-model results |
| Benchmark scale | 13 intents (pilot only, always labeled as such) | 30 (v0.1 pilot, this round) → 100 (v1) |

## What this audit changes right now

Nothing on the live site yet, per the plan — this document establishes
the starting point for the v0.1 pilot (30-intent benchmark, real model
runs, Ljubljana research connection) before any further build work.

See also: [`docs/ljubljana_research_connection.md`](ljubljana_research_connection.md).
