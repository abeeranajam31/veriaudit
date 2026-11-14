# After the calibration pilot: from the decision to the main study

`research/analysis/pilot_decision.py` applies the rules fixed in advance, and its output
`pilot_decision.md` names the next step. This page explains each outcome. Nothing here allows
changing the confirmatory test, the models or the forms because of what the pilot showed.

## A. Judges (J0) first: AI labels are usable only if J0 passes

| J0 result | Do this |
|---|---|
| PASS | Use the two primary judges for the main study, unchanged. |
| FAIL in one form, for example Urdu-script sensitivity < 0.80, or more than 0.10 below English | Replace the weaker judge, re-run it on the pilot, and draw a **new** J0 sample (the old one has been seen). If no judge passes, that form's main-study labels must come from humans, and the protocol's AI-only fallback limits the claims. |
| Shared-error ratio > 2 | The judges fail together, so their agreement means little. Send more responses to humans: raise the validation sample above 300 for that form. |
| INSUFFICIENT_DATA | Expected for non-English harmful content unless option P1 was chosen. The judges must then be validated on the main study's validation sample **before** any main-study result is computed. |
| Llama 4 Scout unavailable (access refused, or no 4 × 80 GB) | No tie-breaker. Send every primary-judge disagreement to the human queue instead. Protocol §8 already allows this. Expect about 10–20% of responses to need human labels; the pilot shows the real rate. |

## B. Sample size (A7)

| Decision | Next step |
|---|---|
| **ADEQUATE** | Freeze the dataset (`assemble_veriaudit_x.py --version 2.0.0 --release`), then run the main study at n = 200. Record the MDEs in protocol §4.3. |
| **ADEQUATE_WITH_LIMITATION** | As above. In the paper, for the listed cells, a non-significant result is reported as "not informative below X pp" (X = the upper MDE). |
| **NOT_ADEQUATE** | Choose one option **by amendment before the main study**, then proceed. (1) **Pre-register the MDEs.** Cheapest, and recommended unless a key cell has a very large MDE. (2) **5 samples per prompt.** About 1.5× GPU cost; worth it only where the decision table shows low within-unit agreement. (3) **More scenarios.** `n_needed_estimate` per failing cell; each extra scenario means 6 more translations, reviews and a benign contrast. |
| **INCOMPLETE** | A confirmatory model is missing from the pilot. Finish the run. |

## C. The main study, in order

1. Freeze the release. Pin `vllm`/`torch`/`transformers` in `backend/requirements-v2.txt` to the
   versions in the pilot's `run_manifest.json`.
2. Generate. Run `configs/experiments/main_study.yaml`, one confirmatory model per session: 2,440
   prompts × 4 decodings each.
3. Judge. Run the two primary judges, then the tie-breaker or human resolution of disagreements.
4. Validate with humans. Draw the 300-response validation sample with
   `python -m app.v2.human_labels sample --run results/v2/runs/main-study-v1 ... --per-form 75`,
   **before** looking at any result. Get it double-annotated and adjudicated.
5. Analyse. Run `run_analysis.py --run results/v2/runs/main-study-v1 --labels ...`. It refuses
   incomplete, tampered or non-release runs.
6. Report the confirmatory H1/H2 families first (paired t, Holm, approximate t intervals, bounds for
   unscored units), then the pre-specified sensitivity analyses, then exploratory results:
   - **RQ2:** Roman Urdu spelling and transliteration (T1, T2); code-switching ratio (T4, T5); script
     mixing (T6).
   - **RQ3:** comprehension versus safety failure. Are harmful completions concentrated in responses
     the model misunderstood?
   - **RQ5:** response classifiers.

The research questions behind your goal map onto the design like this:

| Your question | Where it is answered | Status |
|---|---|---|
| Cross-lingual safety gap | H1 (confirmatory), per model × form | confirmatory |
| Roman Urdu vulnerability | H1 Roman Urdu cells; T1/T2 spelling variants (RQ2) | confirmatory + exploratory |
| Code-switching | H1 code-switched cells; T4/T5 English ratio, T6 script mixing | confirmatory + exploratory |
| Comprehension versus safety failure | RQ3: harmful compliance stratified by comprehension label | exploratory (comprehension is affected by form, so it is described, not adjusted for) |
| Over-refusal in Urdu forms | H2 | confirmatory |

A non-significant confirmatory cell is reported together with its MDE, never as "no gap". Results
that were not pre-specified are labelled exploratory.
