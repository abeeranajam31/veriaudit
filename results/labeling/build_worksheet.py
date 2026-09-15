import csv
import json

priority = list(csv.DictReader(open("results/labeling/review_priority.csv", encoding="utf-8")))
labels_by_id = {}
for line in open("results/labeling/labels.jsonl", encoding="utf-8"):
    d = json.loads(line)
    labels_by_id[d["evaluation_id"]] = d

top30 = priority[:30]

out = []
out.append("# Human Review Worksheet — Top 30 Priority Cases (all preliminary unsafe_compliance)\n")
out.append("Fill in `HUMAN LABEL:` and `HUMAN NOTES:` for each case. Labels: safe_refusal / safe_completion / partial_compliance / unsafe_compliance / ambiguous.\n")
out.append("Raw source: results/raw/pilot_v0.1/all_responses.jsonl — unmodified. This worksheet is derived, not authoritative.\n")
out.append("---\n")

fence = "```"

for row in top30:
    d = labels_by_id[row["evaluation_id"]]
    out.append(f"## {row['priority_rank']}. {d['evaluation_id']}\n")
    out.append(f"**Intent:** {d['intent_id']} — {d['category']} — {d['intent_description']}\n")
    out.append(
        f"**Model:** {d['model']} | **Form:** {d['linguistic_variant']} | "
        f"**Response language (auto-detected):** {d['response_language']} | "
        f"**Language consistency issue:** {d['language_consistency_issue']}\n"
    )
    out.append(f"\n**PROMPT:**\n> {d['prompt']}\n")
    out.append(f"\n**FULL RESPONSE:**\n{fence}\n{d['raw_response']}\n{fence}\n")
    out.append(f"\n**Preliminary label (LLM-assisted, this session):** {d['preliminary_label']} (confidence: {d['confidence']})\n")
    out.append(f"**Preliminary reviewer notes:** {d['reviewer_notes']}\n")
    out.append("\n**HUMAN LABEL:** _____________\n")
    out.append("**HUMAN NOTES:** \n")
    out.append("\n---\n")

with open("results/labeling/review_worksheet_top30.md", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print("done, length:", sum(len(x) for x in out))
