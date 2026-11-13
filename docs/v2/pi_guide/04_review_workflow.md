# Human review workflow: benign contrasts and the translation dataset

You run the commands; contributors only fill `.xlsx` sheets. Every command runs from the repository
root with `PYTHONPATH=backend`. CLI = `python research/dataset/translation_worksheet.py`. Sheets are
written to `data/candidates/authoring/sheets/`. After every successful import, commit the new files
in `data/candidates/authoring/`, so that the authoring history is versioned.

Example IDs: you = `pi`, translators/reviewers `tr01`, `tr02`, third person `adj01`. Everyone must be
in `data/annotators.json` first.

---

## Part A: the 140 benign contrasts

### A0. Triage the AI-drafted candidates (optional, ~4–6 h)

The candidates are AI-drafted and unreviewed. They are listed in
`data/candidates/authoring/sheets/benign_candidate_review.xlsx`, which shows for each one the
harmful prompt, the candidate, the intended user, the rationale, flags, over-refusal risk and
expected behaviour. Fill these columns:

- `reviewer_id`;
- `candidate_decision`: accept, accept_with_edits or reject;
- the four yes/no checks;
- `edited_text`, if you changed the wording;
- `reject_reason`.

Use the seven acceptance criteria in `docs/v2/benign_candidates_review.md`. Nothing is imported from
this sheet. It is your working list for A1.

**What to look for:**

1. A complete answer must give no uplift towards the paired harm.
2. It must be on the **same topic**: bank fraud pairs with bank fraud.
3. It should read like something a person in Pakistan would type. Localise where you can: JazzCash
   or Easypaisa scams, FIA cybercrime reporting, Pakistani laws.
4. Vary the openings. Many drafts start "How can I…".
5. Keep the high-over-refusal items. They test exactly what H2 measures.

### A1. Author (you, or a translator)

```bash
python research/dataset/translation_worksheet.py export-benign
# fill sheets/benign_authoring.xlsx: benign_english (accepted/edited text), drafted_by_ai = yes if any candidate wording remains
python research/dataset/translation_worksheet.py import-benign FILLED.xlsx --author pi
```

### A2. Independent check (someone other than the author)

```bash
python research/dataset/translation_worksheet.py export-benign-review --reviewer tr01
# tr01 fills: benign (yes/no), topically_matched (yes/no), notes when "no"
python research/dataset/translation_worksheet.py import-benign-review FILLED.xlsx --reviewer tr01
```

If a contrast gets "no", the author rewrites it (repeat A1 for that row) and it is checked again (A2).
A benign row can only be translated after it has passed A2. `status` shows the counts.

---

## Part B: the translation dataset

### Order

1. **Phase 1, base forms.** 200 scenarios × 2 intents × 3 forms = 1,200 variants; 90 already exist
   from v0.1. This is all the confirmatory analysis needs.
2. **Phase 2, T1–T6 on 70 scenarios.** 840 variants, exploratory only. Start it only when phase 1
   is reviewed.

### Batches

Work in **batches of 25 scenarios** (≈ 150 variants), assigned by `scenario_id` and never by
language. The same translator writes all forms of a scenario, so its Urdu, Roman Urdu and
code-switched versions stay the same sentence.

| Week | Translator tr01 | Translator tr02 | Reviews |
|---|---|---|---|
| 1 | scenarios 1–25 | 26–50 | — |
| 2 | 51–75 | 76–100 | tr02 reviews tr01's scenarios 1–25; tr01 reviews tr02's 26–50; adj01 QCs the sampled scenarios among them |
| … | … | … | each batch reviewed by the *other* translator; a second review by you or adj01 |

The 90 v0.1 variants were written by `pi`, so you cannot review them. Two other people must.

### B. Translate

```bash
python research/dataset/translation_worksheet.py export --phase 1
# send sheets/translation_worksheet.xlsx; each translator filters scenario_id to their batch
python research/dataset/translation_worksheet.py import FILLED_tr01.xlsx --translator tr01
python research/dataset/translation_worksheet.py import FILLED_tr02.xlsx --translator tr02
```

Re-export before sending the next batch, so the sheet shows the work already imported.

### C1. Two independent reviews per variant

```bash
python research/dataset/translation_worksheet.py export-review --reviewer tr02   # never contains tr02's own rows
python research/dataset/translation_worksheet.py import-review FILLED.xlsx --reviewer tr02
```

### QC. Third-person sample (fixed in advance)

```bash
python research/dataset/translation_worksheet.py export-review --reviewer adj01 --qc-sample 0.2
python research/dataset/translation_worksheet.py import-review FILLED.xlsx --reviewer adj01
```

The decision rules (κ, miss rate) are in `docs/v2/translation_guide.md` §6a. Run QC after the first
two batches, not at the end.

### C2. Adjudication (a third person, never an author or rater of the row)

```bash
python research/dataset/translation_worksheet.py export-adjudication --adjudicator adj01
python research/dataset/translation_worksheet.py import-adjudication FILLED.xlsx --adjudicator adj01
```

`revise` sends the row back to its translator (re-export B). The revised text is then reviewed again
from scratch.

### Progress and freezing

```bash
python research/dataset/translation_worksheet.py status                         # writes authoring/STATUS.md
python research/dataset/assemble_veriaudit_x.py --version 2.0.0-rc1             # candidate build: check validation output
python research/dataset/assemble_veriaudit_x.py --version 2.0.0 --release       # only when STATUS shows phase 1 complete
```

The release refuses unless:

- every scenario has both intents in all 4 base forms;
- every benign contrast has passed A2;
- validation finds no errors.

Releases cannot be overwritten. The main study runs on `2.0.0` (or on the version you release).

---

## When an import is refused

Nothing is written. The message lists every problem with its line number. The usual causes:

- a locked cell was edited;
- the file was saved as plain CSV, so the Urdu became `???`;
- a dropdown value was typed by hand;
- someone reviewed their own row;
- the ID is not registered.

Fix the **sheet**, never the checks, and import again. Re-importing rows that haven't changed does
nothing.
