# Models under test and response judges: verification and recommendation

Checked 2026-11-13. Sources are listed at the end.

## 0. Pinned revisions (verified 2026-11-13)

Each hash is the `main` commit returned by the Hugging Face API on 2026-11-13. Each one was then
re-fetched with `/api/models/<repo>/revision/<hash>` to confirm that it resolves. They are pinned in
`configs/models.yaml` and `configs/judges.yaml`.

| Key | Repo | Revision | Parameters | Gated | GPU (weights, before KV cache) |
|---|---|---|---|---|---|
| qwen3_8b | Qwen/Qwen3-8B | `b968826d9c46dd6066d109eabc6255188de91218` | 8B | no | 1 × 24 GB |
| aya_expanse_8b | CohereLabs/aya-expanse-8b | `5062468bf9bc0c6035fd64e06274333ec127d980` | 8B | auto (accept terms) | 1 × 24 GB |
| qwen3_5_9b | Qwen/Qwen3.5-9B | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | 9.65B | no | 1 × 24 GB |
| gemma4_e4b | google/gemma-4-E4B-it | `4ecc2ba63bcac23ba4a767fc87025b1450f84c9c` | 8.0B (incl. embeddings) | no | 1 × 24 GB |
| gemma4_31b (exploratory) | google/gemma-4-31B-it | `842da3794eaa0b77d5f08bae87a17459d91ff475` | 31.3B | no | 1 × 80 GB |
| judge A | openai/gpt-oss-120b | `b5c939de8f754692c1647ca79fbf85e8c1e70f8a` | 116.8B MoE (5.1B active), MXFP4 | no | 1 × 80 GB (H100 preferred) |
| judge B | mistralai/Mistral-Small-3.2-24B-Instruct-2506 | `95a6d26c4bfb886c58daf9d3f7332c857cb27b43` | 24.0B | no | 1 × 80 GB (card: ~55 GB bf16; vLLM ≥ 0.9.1 with `tokenizer_mode/config_format/load_format = mistral`) |
| tie-breaker | meta-llama/Llama-4-Scout-17B-16E-Instruct | `92f3b1597a195b523d8d9e5700e57e4fbb8f20d3` | 108.6B MoE (17B active) | **manual** (Meta approves each request) | 4 × 80 GB, tensor parallel |

The 8–9B models also run on a single 40–80 GB GPU. A smaller GPU only means less KV cache. Run
`research/inference/pilot_preflight.py` on the GPU machine: it confirms that your token can access
every pinned revision.

**Still not verified from here:** whether your Hugging Face account can access the gated repos. The
preflight checks it.

## 1. Models under test (confirmatory panel fixed by protocol §7, amendment 2026-11-13)

| Key | Repo | Licence | Access | Declared Urdu support | bf16 weights / GPU |
|---|---|---|---|---|---|
| qwen3_8b | `Qwen/Qwen3-8B` | Apache-2.0 | open | 119 languages claimed; Urdu not confirmed in the text read | ~16 GB; 1× 24 GB+ |
| aya_expanse_8b | `CohereLabs/aya-expanse-8b` | **CC-BY-NC-4.0** (non-commercial) | **gated** (accept terms) | **No.** 23 languages; Hindi yes, Urdu no | ~16 GB; 1× 24 GB+ |
| qwen3_5_9b | `Qwen/Qwen3.5-9B` | Apache-2.0 | open | 201 languages claimed; Urdu not named | ~18 GB; 1× 24 GB+ |
| gemma4_e4b | `google/gemma-4-E4B-it` | Apache-2.0 | open | 140+ pre-training, 35+ supported; Urdu not named | ~8–16 GB; 1× 24 GB |
| gemma4_31b (exploratory) | `google/gemma-4-31B-it` | Apache-2.0 | open | 140+ languages; Urdu not named | ~62 GB; 1× 80 GB |

How these were checked:

- **Repo ids and licences.** The four confirmatory models were checked on their model cards earlier
  on 2026-11-13; see the comments in `configs/models.yaml`. The 31B repo id was re-confirmed today
  through the NVIDIA model catalog, which links to the Hugging Face repo.
- **Memory figures.** These are parameter count × 2 bytes. They exclude KV cache, so leave about
  30% headroom.
- **Urdu support.** No model under test names Urdu as a supported language. That is part of the
  research question, not a defect. The paper must not say any of them "supports Urdu".
- **Aya Expanse.** Its non-commercial licence allows this research use. Generated outputs that are
  released inherit the CC-BY-NC terms; note this in the release.

Generation volume for the main study, per `configs/experiments/main_study.yaml`:

- **Prompts per model.** 200 scenarios × 2 intents × 4 base forms = 1,600, plus 70 × 2 × 6
  transformations = 840. That gives **2,440 prompts**.
- **Generations per model.** Greedy plus 3 samples is 4 per prompt, so **9,760**.
- **Confirmatory panel (4 models).** **39,040 generations**, at most 512 new tokens each.

With vLLM on a single A100/H100 80 GB, an 8B model should take roughly 0.5–2 GPU-hours per model.
That is an estimate from typical vLLM batch throughput, not measured. The calibration pilot
measures it.

## 2. Judges

The protocol (§8) requires two primary LLM judges from model families **not** under evaluation, so
not Qwen, Cohere/Aya or Gemma. Each response gets labels on four axes: comprehension, behaviour,
harmful content and task success. A third judge breaks 1–1 ties. A single judge never resolves a
label.

| Candidate | Licence / access | Size / hardware | Multilingual evidence | Fit |
|---|---|---|---|---|
| **gpt-oss-120b** (OpenAI) | Apache-2.0 + usage policy; open | 117B total / 5.1B active MoE, MXFP4; **1× 80 GB** | MMMLU 14 languages, including Hindi (80.0 at medium reasoning); **Urdu not reported** | Strong instruction following; reasoning model, so set reasoning effort and strip the reasoning trace before parsing |
| **Mistral Small 3.1 / 3.2 24B Instruct** (Mistral AI) | Apache-2.0; open | 24B dense; ~55 GB bf16, so **1× 80 GB** | "Dozens of languages"; listed names do not include Urdu | Non-reasoning, cheap; a different lineage from gpt-oss |
| Llama 4 Scout 17B-16E (Meta) | Llama 4 Community Licence; accept terms | 109B total / 17B active; 1× 80 GB only if quantised | 12 fine-tuned languages including Hindi and Arabic; Urdu not named | Suitable as the **tie-breaker**. Quantisation and licence add friction |
| gpt-oss-20b | Apache-2.0 | 21B / 3.6B active; 16 GB | MMMLU Hindi 76.6 (medium) | Cheap fallback if 80 GB GPUs are unavailable; shares a lineage with 120b, so it is **not** an independent second judge |
| Llama Guard 4 12B | Llama 4 licence (via NVIDIA) | 12B; 1× 24–40 GB | Evaluated on 7 non-English languages including Hindi; Urdu not named | Outputs only safe/unsafe plus a hazard category, so it cannot label comprehension, behaviour or task success. Use it as an **auxiliary harmful-content signal** in the RQ5 classifier study, never as a judge |

**Recommendation:**

- **Primary judge A:** gpt-oss-120b, reasoning effort "medium".
- **Primary judge B:** Mistral Small 3.2 24B Instruct (or 3.1 if 3.2's card is unavailable).
- **Tie-breaker:** Llama 4 Scout.

Why this set:

- **Independent lineages.** The three come from three different developers and lineages, none of
  them under evaluation. That reduces, but does not remove, shared failure modes.
- **One GPU each.** Each fits on a single 80 GB GPU, so all three can run sequentially on one rented
  GPU.
- **Licences.** All three permit research use; Llama needs terms accepted.

**Urdu-specific limitations to expect:**

1. **No judge documents Urdu.** The closest evidence is Hindi, which shares spoken grammar with Urdu
   but is written in a different script. Urdu-script responses are the highest risk; Roman Urdu is
   probably read better than Urdu script.
2. **Missed harm in Urdu-script responses.** A judge that fails to understand an Urdu-script
   response is most likely to mark it as not harmful or as a refusal. That error depends on the
   form, so it would **bias CLSG towards zero** (or invert it) rather than just add noise.
3. **Unequal context.** The judge prompt includes the English source of the request. This keeps the
   judge's understanding of the *request* equal across forms, but not its understanding of the
   *response*.
4. **Agreement is not correctness.** Two judges that both misread Urdu script will agree with each
   other and both be wrong. Judge–judge agreement is therefore reported as agreement only and never
   as accuracy.

## 3. Human check of the judges (required before AI labels are used as results)

**Stage J0, at the calibration pilot, before the main study.**

- **Sample.** Two registered human annotators who can read Urdu script independently label a
  stratified sample of pilot responses: about 160, which is 40 per form, balanced by intent type and
  oversampling judge disagreements. A third person adjudicates.
- **Per form, against the adjudicated human labels, compute:**
  - sensitivity and specificity of each judge, and of the resolved two-judge label, for
    `harmful_content`;
  - per-axis κ.
- **Correlated errors.** Compute P(both judges wrong) and compare it with the product of their
  individual error rates. A ratio much above 1 means the errors are shared, so agreement is
  uninformative.
- **Acceptance rules,** fixed now and recorded in the readiness report:

| Check | Accept if | Otherwise |
|---|---|---|
| Harmful-content sensitivity of the resolved label, each form | ≥ 0.80 | replace the weak judge; or mark that form "human-labelled only" |
| Sensitivity difference, each non-English form − English | within ±0.10 | form-specific bias. Report a misclassification-corrected CLSG as sensitivity, and increase human labels for that form |
| Per-axis κ (resolved vs human), each form | ≥ 0.6 | refine rubric prompt; re-run J0 on a fresh sample |
| Shared-error ratio | ≤ 2 | treat two-judge agreement as one label; send more responses to humans |

At ~40 responses per form the estimates are imprecise: a sensitivity of 0.8 based on about 15
harmful responses has a 95% CI of roughly ±0.2. J0 can therefore detect gross failures, not fine
ones. The main-study validation sample (protocol §8: 300 responses, double-annotated) is the
definitive check, and the same table is reported for it.

**Stage J1, main study.** Protocol §8 applies unchanged:

- the 300-response validation sample;
- judge disagreements go to the human queue;
- the AI-only fallback limits conclusions to effects larger than the observed judge disagreement
  rate in each cell.

## Sources

- [Hugging Face: Llama 4 release blog](https://huggingface.co/blog/llama4-release)
- [OpenAI: gpt-oss-120b and gpt-oss-20b model card (PDF)](https://cdn.openai.com/pdf/419b6906-9da6-406c-a19d-1bb078ac7637/oai_gpt-oss_model_card.pdf)
- [Mistral Small 3.2 24B Instruct 2506, model card mirror (Featherless)](https://featherless.ai/models/unsloth/Mistral-Small-3.2-24B-Instruct-2506/readme)
- [Mistral Small 3.1 24B Instruct 2503, model card mirror (Featherless)](https://featherless.ai/models/mistralai/Mistral-Small-3.1-24B-Instruct-2503/readme)
- [NVIDIA model catalog: Llama Guard 4 12B](https://build.nvidia.com/meta/llama-guard-4-12b/modelcard)
- [NVIDIA model catalog: Gemma 4 31B IT](https://build.nvidia.com/google/gemma-4-31b-it.md)
- The confirmatory models' cards are cited in `configs/models.yaml` (checked earlier on 2026-11-13).

The language lists above come from model-card and catalogue mirrors. Confirm them on the official
Hugging Face cards when pinning revisions.
