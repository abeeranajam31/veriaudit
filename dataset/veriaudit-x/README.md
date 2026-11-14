# VeriAudit-X (VeriAudit v2 dataset infrastructure)

Status: **infrastructure only.** This directory holds the schema, tooling
docs and a synthetic test fixture. No VeriAudit-X benchmark data exists yet;
nothing here is a result.

Code: [`backend/app/veriaudit_x/`](../../backend/app/veriaudit_x/) ·
JSON Schema: [`schema/veriaudit-x-2.2.0.schema.json`](schema/veriaudit-x-2.2.0.schema.json) ·
Fixture: [`fixtures/sample_valid.jsonl`](fixtures/sample_valid.jsonl) (built by `fixtures/build_fixtures.py`)

## Data model

Long format, one JSONL record per linguistic variant:

```
scenario_id   split unit; groups intents that must never be separated
  └─ intent_id   one canonical, language-independent request + expected behaviour
       └─ record_id   one surface form: language + script + text + transformation
```

A harmful intent and its benign contrast (`contrast_intent_id`) live in the
same scenario, so harmful-compliance and over-refusal are measured on matched
topics and the pair can never be split across train/test.

| Field | Meaning |
|---|---|
| `schema_version` | `2.2.0`. Records with any other version are rejected. |
| `record_id`, `scenario_id`, `intent_id` | IDs matching `^[A-Za-z0-9][A-Za-z0-9._-]*$`. Convention: `VX-S0001`, `VX-S0001-H`, `VX-S0001-H-ur-01`. |
| `scenario_type` | `harmful` \| `benign` |
| `category` | Harmful: `cybercrime, weapons, self_harm, hate_speech, misinformation, fraud, privacy_violation`. Benign: `everyday_assistance, technical_assistance, information_request, safety_information, health_information, instruction_following`. Must match `scenario_type`. |
| `expected_behavior` | Harmful: `refuse` \| `refuse_and_redirect`. Benign: `comply` \| `comply_with_safety_info`. |
| `contrast_intent_id` | Opposite-type intent in the same scenario, or null. |
| `language` / `script` | `english`/`latin`, `urdu`/`perso_arabic`, `roman_urdu`/`latin`, `code_switched`/`latin`\|`perso_arabic`\|`mixed`. |
| `transformation` | `type` (`source, translation, transliteration, code_switching, orthographic_variation, paraphrase, register_shift`), `source_record_id` (parent, same intent), `method` (`human, machine, machine_post_edited, rule_based`), `tool`, `author_id`, free-form `parameters` for controlled knobs (e.g. `romanization_scheme`, `english_token_ratio`). Exactly one `source` record per intent. |
| `equivalence` | `status` (`source, pending, flagged, verified, rejected`), `reference_record_id`, optional `automatic_screen {model, score, threshold}`, `human_ratings[] {annotator_id, judgement, harm_preserved, notes}`. |
| `annotation` | `status` (`unannotated, in_progress, agreed, disputed, adjudicated`), `annotations[] {annotator_id, labels{scenario_type, category, expected_behavior, naturalness 1–5}}`, `adjudication {adjudicator_id, final_labels, rationale}`. |
| `provenance` | `created_at, created_by, origin` (e.g. `veriaudit-v0.1:VA30-001`), `license, notes`. |
| `split` | Only in split output files: `train`/`validation`/`test`. |

Dataset-level metadata (dataset version, fixture flag) goes in a sidecar
`manifest.json` validated by `DatasetManifest`.

## Validation rules

`python -m app.veriaudit_x validate FILE.jsonl` (run from `backend/`). Errors block splitting; warnings need review.

- **Errors:** invalid JSON; missing or unknown fields; duplicate `record_id`; values outside the vocabularies; unsupported schema version; category / expected behaviour inconsistent with scenario type; script not allowed for language; conflicting metadata within an intent; not exactly one source per intent; dangling or cross-intent `source_record_id`/`reference_record_id`; contrast intent missing, same-type, or in another scenario; `verified` without ≥2 unanimous `equivalent` human ratings (similarity never verifies); `rejected` without a rating; annotation status inconsistent with the annotations; `adjudicated` without an adjudication; record labels differing from agreed/adjudicated labels; a scenario spread over several splits.
- **Warnings:** an intent missing one of the four languages; duplicate normalised text within an intent; similarity below threshold left `pending`; adjudicator who also annotated.

Thresholds (`min_equivalence_raters`, `min_annotators`, required languages) are set in `ValidationConfig`.

## Splits

`python -m app.veriaudit_x split FILE.jsonl --out DIR --seed 13 --ratios 0.7 0.15 0.15 --dataset-version X.Y.Z`

Writes `train/validation/test.jsonl` and `split_manifest.json` (seed, ratios, source SHA-256, per-split counts, scenario→split map). The assignment unit is a scenario group: scenarios are unioned when they share normalised text (Unicode/case/punctuation/Urdu diacritics/Arabic-vs-Urdu codepoints ignored) or cross-reference each other, so no variant, paraphrase duplicate or contrast pair can sit on both sides of a split. Groups are ordered by stratum (scenario type × category) and a seeded hash, then allocated to the split furthest below its target — global ratios are exact to within one group; per-stratum balance is approximate for small strata. A post-hoc `check_leakage` runs on every split and raises if anything crosses.

Known gap: Roman Urdu spelling variants of the *same* sentence in *different* scenarios ("kya"/"kia") are not caught by text matching. Within an intent they are linked by IDs; across scenarios this needs fuzzy matching or reviewer-assigned links.
