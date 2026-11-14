// Every number on the landing page comes from a committed, reproducible output. Do not edit a number
// here without regenerating its source.
//   v1 findings:        results/v1_reconstruction/ (research/v1_reconstruction/reconstruct.py, 191/191 matched)
//   multi-model study:  results/v2/exploratory/v01-panel/ (single_judge_sensitivity.csv, label_agreement.json)

export const REPO = "https://github.com/abeeranajam31/veriaudit";
export const BRANCH = "veriaudit-x-dataset";
export const PAPER_PDF = `${REPO}/blob/${BRANCH}/paper/v01_reanalysis/main.pdf`;
export const EXPLORATORY_DIR = `${REPO}/tree/${BRANCH}/results/v2/exploratory/v01-panel`;
export const PROTOCOL = `${REPO}/blob/${BRANCH}/docs/v2/research_protocol.md`;
export const STATS_VALIDATION = `${REPO}/blob/${BRANCH}/docs/v2/statistical_validation_v2.md`;
export const RECONSTRUCTION = `${REPO}/tree/${BRANCH}/results/v1_reconstruction`;

export const findings = [
  {
    stat: "92% → 0%",
    label: "Refusal detection collapses outside English",
    body:
      "An English-pattern refusal detector caught 92% of English refusals but 0 of 40 Urdu-script refusals, and only 16–19% in Roman Urdu and code-switched text. Scored this way, the same responses show safety gaps of 42.5–70 points instead of 10–40.",
    source: "results/v1_reconstruction",
  },
  {
    stat: "39.5 → 26.7 pp",
    label: "Denominator choices move the headline gap",
    body:
      "Counting only genuine harmful compliance on all scenario pairs, Qwen3-8B's Roman Urdu gap falls from 39.5 to 26.7 points and is no longer significant after Holm correction; counting the same non-scoreable outputs as unsafe raises it to 56.7.",
    source: "results/v1_reconstruction",
  },
  {
    stat: "71%",
    label: "Models answer Urdu in a different language",
    body:
      "Aya Expanse 8B answers 71% of Roman Urdu prompts (85/120) and 65% of code-switched prompts (78/120) in Hindi script, reproducing what the original evaluation found (20 of 30). Script drift changes what a safety judge has to read.",
    source: "results/v2/exploratory/v01-panel",
  },
] as const;

// Harmful-compliance gap vs English (percentage points), each automated judge on its own
// (pre-specified sensitivity analysis). Paired t on per-scenario shares of 3 samples; Holm within judge.
export const multiModel = [
  { model: "Aya Expanse 8B", form: "Urdu script", nemo: "+12.2 [3.9, 20.5]", granite: "+11.1 [2.2, 20.1]", note: "Holm p = .049 (Nemo)" },
  { model: "Qwen3-8B", form: "Roman Urdu", nemo: "+10.1 [2.1, 18.2]", granite: "+20.4 [3.2, 37.6]", note: "p < .05 unadjusted, both judges" },
  { model: "Qwen3.5-9B", form: "all forms", nemo: "+1.1 to +2.2", granite: "0.0 to +2.8", note: "no evidence of a gap" },
] as const;

export const judgeAgreement = { harmful: 96, behaviour: 50, kappaHarmful: 0.44 };

export const built = [
  { title: "Exact reproduction", body: "All 191 published numbers of the original evaluation recomputed from raw outputs, as an automated check." },
  { title: "Pre-registered protocol", body: "Hypotheses, estimands, tests and decision rules fixed before data collection, with a dated amendment log." },
  { title: "Validated statistics", body: "Primary test chosen by simulation: 11 null scenarios × 20,000 runs; the common signed-rank test was shown not to test the reported gap." },
  { title: "Integrity safeguards", body: "Hash-bound runs, pinned model revisions, refusal of tampered or incomplete runs; 13 failure scenarios replayed against the code." },
  { title: "Human-validation workflow", body: "Blind, double annotation with third-person adjudication, independence enforced in code, Urdu-safe spreadsheets." },
  { title: "Open evaluation pipeline", body: "Model runners, two-judge labelling, analysis and reporting for English, Urdu script, Roman Urdu and code-switching." },
] as const;
