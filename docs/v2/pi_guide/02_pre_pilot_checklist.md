# Before the calibration pilot: prioritised checklist

The calibration pilot can run as soon as items 1–8 are done. Items 9–12 run in parallel; the main
study needs them, but the pilot does not. ★ = the first three actions. Everything not marked as
yours is already prepared in the repository.

| # | Action | Why it blocks | Time | Done |
|---|---|---|---|---|
| ★1 | **Decide A6 and A7** (`01_amendments_A6_A7.md`) and record the decision in protocol §15 | A7 is the rule the pilot will be judged by. It must be fixed before the pilot runs | 30 min | [ ] |
| ★2 | **Start recruiting 3 bilingual people** (`03_recruitment_and_instructions.md`): ≥ 2 translator/reviewers + 1 adjudicator/annotator. For the pilot itself you need **2 people who can label responses in Urdu script** (J0) + 1 adjudicator (can be you) | Longest lead time. J0 (human check of the judges) needs them before the pilot's labels can be used | 1–3 weeks | [ ] |
| ★3 | **Set up Hugging Face and request gated access**: create an account/token; accept the Aya Expanse licence (approved automatically) and request Llama 4 Scout access (**Meta approves manually**; it can take days or be refused) | The runner cannot download gated models; a refusal for Llama changes the tie-breaker plan | 15 min + waiting | [ ] |
| 4 | **Decide compensation and consent** for the people in ★2. Use the information sheet and consent text in `03_…` §4. If you have an institutional affiliation for this work, ask whether ethics review is needed. Annotators will read requests about scams, self-harm and violence | People are reading harmful content; reviewers and venues ask about this | 1–2 h | [ ] |
| 5 | **Register people** in `data/annotators.json` (pseudonymous IDs such as `tr01`, `rv02`, `adj01`; no names) and commit. Registering an ID attests that it is a distinct human | Imports refuse unregistered IDs | 10 min | [ ] |
| 6 | **Confirm the judges** in `configs/judges.yaml` (recommended: gpt-oss-120b + Mistral Small 3.2; Llama 4 Scout as tie-breaker). If Llama access is refused, see `05_after_the_pilot.md` §A for the alternative (human resolution of disagreements) | Judges must be fixed before their labels are seen | 30 min | [ ] |
| 6b | **Choose pilot option P1 or P2** (`calibration_pilot_package.md`, "Known gap"). The pilot has only 1 harmful scenario in non-English forms, so it cannot check whether the judges detect harm in Urdu-script responses. P1 adds about 15 translated harmful items (45 variants; recommended). P2 defers that check to the main study | Decides whether translators work on pilot items first; P1 is an amendment before the pilot | 15 min | [ ] |
| 7 | **Authorise GPU compute** for the pilot. Needs: 1 × 24 GB GPU for the four 8–9B models (≈ 1–3 h total); 1 × 80 GB GPU per primary judge (≈ 1–2 h each, H100 preferred); 4 × 80 GB for Llama 4 Scout only if used as tie-breaker. Free Colab will not provide 80 GB. These are estimates; the pilot measures them | The only paid resource | decision | [ ] |
| 8 | **Run the preflight** on the GPU machine: `PYTHONPATH=backend python research/inference/pilot_preflight.py`. Every line must be PASS or WARN | Catches licence, pin and dataset problems before paying for GPU time | 2 min | [ ] |
| 9 | Correct the AI-written Urdu examples in `docs/v2/translation_guide.md` §4 (Lahore example, all 9 forms) before translators see the guide | Translators copy the examples | 1 h | [ ] |
| 10 | One real **Excel** round trip: open `data/candidates/authoring/sheets/benign_candidate_review.xlsx` in Excel, type an Urdu sentence in a white cell, save as .xlsx, send it back to me (or run the import) | LibreOffice was the stand-in in testing | 15 min | [ ] |
| 11 | Triage the 140 benign candidates (`04_review_workflow.md` Part A) | Benign contrasts must exist before their translation can start | 4–6 h | [ ] |
| 12 | Start phase-1 translation in batches (`04_review_workflow.md` Part B) | The main study needs a frozen dataset; the pilot does not | weeks | [ ] |

Already done and committed, needing nothing from you:

- **Pinned revisions.** All 4 confirmatory models, the exploratory 31B model and the 3 judges are
  pinned to verified commits.
- **Pilot materials.** The pilot dataset (hash-checked), the run config, the judge runner, the
  preflight check, the decision script and the Colab notebook cells.
- **Translator package.** Sheets, guide, and a QC sample fixed in advance.
