# VeriAudit v2: pre-data-collection readiness report

> **Update 2026-11-13 (later the same day).** The step-by-step guide for the PI is now
> `docs/v2/pi_guide/`. Since this report was written:
> - model and judge revisions are pinned to verified commits;
> - human response-labelling tooling exists (`app.v2.human_labels`);
> - a preflight check and the post-pilot decision script have been added;
> - a pilot gap is documented: only one harmful scenario in non-English forms. Options P1 and P2
>   are in `calibration_pilot_package.md`.
>
> Section G is superseded by `pi_guide/02_pre_pilot_checklist.md`.

Date: 2026-11-13. Branch `veriaudit-x-dataset`, draft PR #1 (not merged).

**No v2 inference, judging, translation or human annotation has happened.** Every number in this
report comes from one of four sources:

- a simulation;
- a test on synthetic data;
- a model card;
- a count of files.

Each number is labelled as one of these. Supporting documents are linked in each section.

**Verdict:** the engineering and statistical design are ready for the calibration pilot. The study
is blocked on people (translators, reviewers, annotators) and on decisions and resources that only
the PI can provide (section G).

---

## A. Verified engineering readiness

Detail: `docs/v2/safeguard_verification.md`.

| Check | Evidence | Result |
|---|---|---|
| The 11 integrity fixes stop the original failures | `research/integrity/replay_review_scenarios.py`: 13 end-to-end scenarios replayed against the pre-fix tree (e4fc1fc) and the current tree | **13/13 bypassed before; 13/13 blocked now** (`results/integrity/`) |
| Source-change invalidation | replay s02; lifecycle test (post-release English edit makes 2.0.1 refuse; stale translations dropped) | pass |
| Adjudicator cannot be a reviewer or author of the row | replay s03 (CLI and rating layer, including hand-written ratings files) | pass |
| CSV encoding cannot corrupt Urdu | replay s04; lifecycle test re-saving real Urdu through LibreOffice: xlsx and UTF-8 CSV keep it byte for byte; Windows-1252 CSV is refused with nothing written | pass |
| Resumed runs cannot mix configurations | replay s05: a run is bound to its dataset hash and config hash | pass |
| Full dataset lifecycle | `backend/tests/test_authoring_lifecycle.py`, through the real CLI: benign authoring → benign review → translation (.xlsx) → revision → 2 reviews → adjudication → release 2.0.0 → immutability → post-release edit | pass; found and fixed 2 bugs (lost self-check on re-export; `??` corruption missed) |
| Clean checkout | fresh clone of 6376640 | 247 tests pass; ruff clean; v0.1 reconstruction 191/191; benign-candidate and calibration builders reproduce committed outputs |
| Judge execution | `app.v2.judges.run_judge` (new; the judging step had no driver). Resumable; refuses unpinned judges, judges from an organisation under test, and a changed dataset | unit and CLI tests on a fixture run |

Also fixed during this round:

- **English quality check.** The English "no Roman Urdu" check flagged 96 of the 200 English source
  prompts, because English homographs (is, in, the, to…) are also in the Roman Urdu lexicon. It now
  flags none.
- **Calibration analysis.** It computed power for the wrong test (see B) and was slowed by repeated
  quadrature setup. It is now about 20× faster.

**Remaining engineering weaknesses (documented, not fixed):**

1. **Unsigned hashes.** Run and dataset hashes detect accidents, not deliberate tampering. Archive the
   hashes externally at collection time.
2. **One person, two IDs.** The pseudonymous registry cannot detect one person holding two IDs.
   Independence rests on the PI's registration.
3. **Sheet locks.** These have no password. Locked texts are checksummed; other locked metadata is
   ignored on import.
4. **Single-letter corruption.** A single Urdu letter turned into a lone `?` is not flagged. Script
   checks and review are the backstop.
5. **Excel itself was not tested.** LibreOffice stands in for it; do one Excel round trip first.
6. **GPU paths never run here.** The vLLM backends for models and judges have not run in this
   environment, which has no GPU. The pilot is their first real test.

## B. Verified statistical readiness

Detail: `docs/v2/statistical_validation_v2.md`. Simulations: 20,000 per null, 4,000 per alternative,
2,000 per interval cell, each with Monte Carlo intervals.

**Changes made, as amendment A6 before any data:**

- The primary test changes from Wilcoxon signed-rank to the **paired t-test** on per-scenario share
  differences.
- The interval becomes the dual **t interval**, reported as approximate 95%.
- **Why:** the signed-rank test does not test the mean (CLSG). Its functional is the sign balance
  of Walsh sums of the non-zero differences. Under a mean-zero null with many zeros it rejected
  **25.5%** of the time at α = .05, and under mean-positive alternatives it was significant in the
  wrong direction up to 17.6% of the time.
- The paper draft and protocol no longer describe it as a test of a mean. It is reported as
  descriptive only.

| Property | Finding |
|---|---|
| Type I error, paired t, 11 nulls | 0.036–0.053 at α = .05 (worst N8 0.0534 [0.0503, 0.0566]); ≤ 0.0045 at α = .05/12, every Monte Carlo interval covering or below nominal; conservative at base rates ≤ 1% |
| Power, α = .05/12, n = 200 | 0.93 for 5 → 11% (independent samples); **0.49 / 0.42 with within-unit correlation 0.8 / 0.95**; 0.43 for 5 → 9% (σ = 1); 0.32 for 1 → 3%; 0.17 for 0.5 → 2%; 0.08 for a gap concentrated in 10% of scenarios |
| Gap CI coverage (nominal 0.95) | t interval 0.921–0.968. Below 0.95 at base rates ≤ 1–2% with a non-zero gap, where the interval falls below the true gap. No method examined reaches 0.95 everywhere. Not called a reliable 95% interval at rare rates |
| Rate CI coverage | clustered Wilson as low as 0.85 at 1% with correlation; bootstrap 0.90. Labelled approximate; counts reported below 2% |

**What remains statistically open:**

- **Within-unit correlation and base rates.** These decide whether n = 200 is adequate, and only the
  calibration pilot can estimate them. The decision rule is fixed in advance (amendment A7;
  `calibration_pilot_package.md` §4).
- **Judge misclassification that differs by form.** This would bias CLSG and is not covered by the
  tests (see F).

## C. Dataset and translation readiness

| Item | State |
|---|---|
| Scenario selection | 200 scenarios (8 categories, 14–29 each); 60 benign contrasts from XSTest, **140 missing** |
| Benign contrasts | **140 AI-drafted candidates**, all marked `ai_generated`, `review_status: candidate - not reviewed`. Each has a linked harmful prompt, legitimate intent, rationale, flags (general_only 21, safe_messaging 19, jurisdiction 7, unspecified_x 3, dual_use_low 3), over-refusal risk (high 14, medium 32, low 94) and expected behaviour (comply 120, comply with safety information 20). Automated checks: full coverage, English QC, no near-duplicates, none too close to its harmful prompt. Review sheet `benign_candidate_review.xlsx`; acceptance criteria `docs/v2/benign_candidates_review.md`. Entry to the dataset only via human authoring (`drafted_by_ai = yes`) plus an independent check |
| Translations | phase 1: 90 of 1,200 variants exist (v0.1, written by the PI; need 2 independent reviews each), **1,110 to write**; phase 2: 840 to write |
| Translator package | `docs/v2/translation_guide.md`: rules and acceptable/unacceptable examples for all 9 forms (T2–T6 added); self-check fields; xlsx workflow (locked columns, dropdowns, RTL Urdu, save rules); review, adjudication and status rules; **third-person QC plan**: a fixed 20% scenario sample (40 scenarios, ≈ 240 variants), drawn by `export-review --qc-sample 0.2` from a scenario-ID hash before any translation exists, with pre-set decision rules on κ and miss rate |
| Example Urdu in the guide | written by the AI assistant for illustration. ▲ PI to correct |
| Calibration dataset | built, sha256 `41854a8a…`, 98 records, disjoint from the main study |
| Release gate | assembler refuses a release unless every scenario has both intents in all 4 base forms, every benign contrast passed its check, and validation finds no errors |

## D. Human annotation requirements

Only `pi` is registered as a rater today. Hours are rough planning figures: about 1–2 minutes per
translation and under a minute per review.

| Task | Who (independence rule) | Volume | Rough effort |
|---|---|---|---|
| A1 benign contrasts (from candidates) | author | 140 | 4–6 h |
| A2 benign-validity check | someone other than the author | 140 | 2–3 h |
| B phase-1 translation | translators; split by scenario, not language | 1,110 variants | 20–35 h |
| C1 review, phase 1 | 2 reviewers, neither the translator (the PI cannot review the 90 v0.1 rows) | 2 × 1,200 | 30–40 h total |
| QC (third person) | not the translator; ideally not a C1 reviewer | ≈ 240 | ~4 h |
| C2 adjudication | third person, never an author or rater of the row | depends on disagreement (say 10–20%) | 4–8 h |
| Phase 2 (exploratory, later) | as above | 840 + reviews | 30–45 h |
| J0 judge check (pilot) | 2 annotators who read Urdu script + adjudicator | ≈ 160 responses, double | ~7 h |
| Main-study validation sample (§8) | 2 annotators + adjudicator | 300 responses, double | ~12 h |

**Minimum team:** the PI plus two bilingual people. With one, every variant can be reviewed once
but not *verified* (S-HUM1 only). A third person is needed for QC and adjudication independence.

## E. Model and GPU requirements

Detail: `docs/v2/model_and_judge_selection.md`.

| Role | Models | Access / licence | GPU |
|---|---|---|---|
| Under test (fixed 4) | Qwen3-8B, Aya Expanse 8B, Qwen3.5-9B, Gemma 4 E4B-it | Apache-2.0 except Aya (CC-BY-NC, **gated**) | 1 × 24 GB each |
| Exploratory | Gemma 4 31B-it | Apache-2.0 | 1 × 80 GB |
| Judges (recommended; PI to confirm) | gpt-oss-120b, Mistral Small 3.2 24B; tie-breaker Llama 4 Scout | Apache-2.0; Apache-2.0; Llama 4 licence (gated) | 1 × 80 GB each, sequential |

- **Urdu support.** No model under test and no judge names Urdu as supported. For the judges this is
  the main measurement risk; J0 checks it before any AI label is used.
- **Volume.** The pilot is 1,568 generations. The main study is 39,040 generations for the 4
  confirmatory models (2,440 prompts × 4 decodings), each judged by 2 judges, plus tie-breaks.
- **Time.** Rough estimate, not measured: 0.5–2 GPU-hours per model under test for the main study,
  several GPU-hours per judge. The pilot measures it.
- **Not verified here:** commit hashes, which must be pinned at download because Hugging Face
  cannot be reached from this environment, and gated-repo access.

## F. Remaining scientific limitations

1. **Power.** It is adequate for moderate gaps only if a model's three samples are not strongly
   correlated and base rates are not very low. Otherwise, n = 200 detects only large gaps, and a
   non-significant result means "no gap above the MDE could be detected".
2. **Judges.**
   - Judges with no documented Urdu support may miss harm in Urdu-script responses. That error
     depends on the form, so it biases CLSG rather than adding noise.
   - Agreement between two judges is not evidence of correctness.
   - Human labels (J0, the 300-response validation sample) are the only check.
3. **Seeds.** The prompts are English-origin benchmark items translated by humans. They are not
   naturally occurring Urdu requests.
4. **Benign contrasts.** Most are AI-drafted defensive reframings. Even after human review they may
   be easier to recognise as safe than real ambiguous requests, which affects over-refusal (H2).
5. **Translators.** One small team means style effects from individual translators. Scenarios are
   split by scenario, not by language, to avoid confounding form with translator.
6. **Generalisation.** The confirmatory models are small open models, and results do not transfer to
   larger or proprietary ones.
7. **Intervals.** CIs at rare rates are approximate, with coverage as low as 0.92 for the gap.
8. **Calibration pilot.** It estimates heterogeneity mostly from English, on a pool skewed towards
   cybercrime and violence, and cannot estimate the cross-form shared component for H1.

## G. Tasks that require the PI

Ordered roughly by when they block.

1. **Review this round.** Accept or reject amendments A6 (paired t primary) and A7 (pilot decision
   rule) in `research_protocol.md` §15. Both were made before any data. Rejecting A6 means
   reinstating a primary test that was shown not to test CLSG.
2. **Recruit and register people.** Recruit at least two bilingual translators or reviewers, ideally
   a third for QC and adjudication. Register their pseudonymous IDs in `data/annotators.json`.
   Registration is an attestation that each ID is a distinct human.
3. **Fix the guide's examples.** Correct the AI-written Urdu examples in the translation guide (§4
   examples, including the new T2–T6 rows).
4. **Benign contrasts.** Triage the 140 AI-drafted candidates, or assign that task. Then run stage A
   (A1 authoring with `drafted_by_ai = yes`, A2 by someone else).
5. **Test Excel.** Do one real Excel round trip of a filled `.xlsx` sheet with Urdu before
   translators start.
6. **Confirm the judges.** Confirm or replace them (`configs/judges.yaml`). Accept the Llama 4 and
   Aya licence terms on Hugging Face.
7. **Authorise GPU compute** for the pilot. This is the only paid resource, if Colab free tier is
   insufficient; 80 GB GPUs are needed for the judges.
8. **Pin revisions.** Pin model and judge revisions at first download (notebook step 1), and commit
   them.
9. **Run the calibration pilot,** then apply the pre-set n = 200 decision. If it is "not adequate",
   choose an option by amendment before the main study.
10. **Arrange human labelling.** Arrange J0 (~160 responses) now and the 300-response validation
    sample for the main study.
11. **Freeze the dataset.** After translation and review, freeze it with `assemble_veriaudit_x.py
    --version 2.0.0 --release`. Then run the main study.
12. **Later approvals.** Decide on merging PR #1 and on any public release of the dataset, results or
    paper. Nothing has been merged or published.
13. **Vercel.** The preview's Root Directory must be `frontend` (`docs/v2/vercel_deployment.md`).
    This is a dashboard setting and was not changed.
