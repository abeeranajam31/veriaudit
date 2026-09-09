# VERIAUDIT-500 dataset

## Status

The public MVP ships a **pilot subset**: 13 of the planned 125 core intents
(× 4 linguistic variants = 52 test cases), covering English, Urdu, Roman
Urdu, and code-switched Urdu/English. **The full VERIAUDIT-500 dataset
(125 intents × 4 variants = 500 test cases) is under development and will
be released following independent bilingual human verification.**

Do not cite the pilot subset as a validated benchmark. It exists to make the
platform's evaluation pipeline runnable end-to-end, not as a scientific
result.

## Files

- `examples/veriaudit-pilot.jsonl` — the pilot subset, one JSON object per line.

## Schema

```json
{
  "id": "VA-001",
  "intent_category": "...",
  "intent": "...",
  "english": "...",
  "urdu": "...",
  "roman_urdu": "...",
  "code_switched": "...",
  "verification_status": "pending",
  "semantic_similarity": {
    "english_urdu": 0.0,
    "english_roman_urdu": 0.0,
    "english_code_switched": 0.0
  }
}
```

| Field | Description |
|---|---|
| `id` | Stable identifier, `VA-###`. |
| `intent_category` | Category label, e.g. `Benign — Everyday Assistance`, `Refusal Test — Cybercrime`. |
| `intent` | Short human-readable description of the underlying test intent. |
| `english` / `urdu` / `roman_urdu` / `code_switched` | The four linguistic variants of the same intent. |
| `verification_status` | `verified`, `pending`, or `flagged`. Never inferred purely from a similarity score — see below. |
| `semantic_similarity` | Embedding cosine similarity between English and each other variant, computed with a multilingual sentence-transformer model. A **screening signal only**. |

## Verification process

1. A variant is machine-translated or human-authored.
2. `EquivEngine` computes embedding similarity against the English source.
3. Similarity below `SIMILARITY_FLAG_THRESHOLD` (default `0.85`) is marked `flagged`.
4. Everything else starts as `pending` — **similarity above the threshold is
   never treated as automatic proof of equivalence.**
5. A human reviewer promotes a case to `verified` after manual comparison.

The pilot cases in this release were translated by the project's lead
researcher as a first pass; most are marked `pending` for exactly this
reason. Two safety-sensitive cases are marked `flagged` pending review of
translation fidelity for sensitive phrasing.

## Categories in the pilot subset

- **Benign — Everyday Assistance / Technical Assistance / Information
  Request / Customer Support** — ordinary requests used as a baseline.
- **Refusal Test — Cybercrime / Weapons / Self-Harm / Hate Speech /
  Misinformation / Fraud / Privacy** — intents where a safe model is
  expected to refuse (or, for self-harm, refuse and redirect to support
  resources) consistently across all four languages. Prompt text mirrors
  the generic, non-actionable style used in public red-teaming benchmarks
  (e.g. AdvBench, HarmBench) — no operational detail or real uplift.
- **Instruction-Following — Format Constraint** — tests whether a
  structural instruction (e.g. "respond in exactly three bullet points")
  is followed consistently regardless of language.

## Planned expansion (VERIAUDIT-500)

125 core intents × 4 linguistic variants, with:

- broader category coverage (jailbreak robustness, prompt injection, bias/fairness),
- independent bilingual annotation and inter-annotator agreement reporting,
- a documented translation and review protocol.
