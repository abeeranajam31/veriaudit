# Human Adjudication — 36 Unresolved Cases

## What this is

`human_adjudication_worksheet.csv` lists the 36 cases from the v0.1 pilot
(240 total responses) whose safety label is not confidently resolved by
automated + LLM-assisted review alone:

- 23 cases currently labeled `ambiguous`
- 13 cases currently labeled `partial_compliance`

These require genuine human adjudication before they can be treated as
final. `adjudication_label` and `adjudication_notes` are left blank for a
person to fill in — nothing in this pipeline fills them in automatically.

## Where this fits in the overall review

- **30 cases** (all originally preliminary `unsafe_compliance`) have
  already been genuinely human-reviewed. See
  `review_worksheet_top30.md` / `review_priority.csv`
  (`human_label` set, 30/30 confirmed `unsafe_compliance`).
- **36 cases** (this worksheet) — `ambiguous` and `partial_compliance` —
  still need genuine human adjudication. Not yet reviewed by a person.
- **174 cases** currently labeled `safe_refusal` were NOT individually
  human-validated. They passed a rule-based pass and/or an LLM-assisted
  read (preliminary and second-pass), but no human has confirmed them
  case-by-case.

30 + 36 + 174 = 240.

## How the final benchmark should be described

Because only a targeted subset (the 30 highest-priority cases) has
genuine human review, and this 36-case subset is pending it, the final
benchmark should be described as **human-adjudicated on a targeted
subset, with LLM-assisted second-pass annotation for the remainder** —
not as a fully human-validated dataset. Do not describe the entire
240-case dataset as "human validated."

## Sort order in the worksheet

1. `partial_compliance` cases first, then `ambiguous` cases.
2. Within each group, ordered by a documented triage heuristic (category
   severity rank, then response word count descending, then case_id) —
   this ordering is for review convenience only and carries no
   evidentiary weight; it does not determine or influence
   `adjudication_label`.

## What was NOT changed

`labels.jsonl`, `second_pass_labels.jsonl`, the raw response files, the
30 existing human labels, `final_label_summary.csv`, and
`final_flagged_cases.csv` were not modified to produce this worksheet.
No CLSG or final safety rate has been calculated.
