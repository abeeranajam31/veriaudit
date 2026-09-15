"""Builds a human-review-ready CSV, ordered by priority per
docs/labeling_protocol.md Step 4: unsafe_compliance first, then
partial_compliance, then ambiguous, then safe_refusal/safe_completion.

human_label is left blank for every row — this file is for a real
person to fill in, not something this script or any LLM fills in for
them.
"""

import csv
import json

PRIORITY = {"unsafe_compliance": 0, "partial_compliance": 1, "ambiguous": 2, "safe_refusal": 3, "safe_completion": 3}

rows = [json.loads(l) for l in open("results/labeling/labels.jsonl", encoding="utf-8")]
rows.sort(key=lambda r: (PRIORITY.get(r["preliminary_label"], 9), r["model"], r["intent_id"], r["linguistic_variant"]))

with open("results/labeling/review_priority.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "priority_rank",
            "evaluation_id",
            "intent_id",
            "category",
            "linguistic_variant",
            "model",
            "preliminary_label",
            "confidence",
            "response_language",
            "language_consistency_issue",
            "reviewer_notes",
            "human_label",
            "human_reviewer_notes",
        ]
    )
    for i, r in enumerate(rows, start=1):
        writer.writerow(
            [
                i,
                r["evaluation_id"],
                r["intent_id"],
                r["category"],
                r["linguistic_variant"],
                r["model"],
                r["preliminary_label"],
                r["confidence"],
                r["response_language"],
                r["language_consistency_issue"],
                r["reviewer_notes"],
                r["human_label"],
                r.get("human_reviewer_notes", ""),
            ]
        )

print(f"Wrote {len(rows)} rows to results/labeling/review_priority.csv")
print("Priority breakdown:")
from collections import Counter
print(Counter([r["preliminary_label"] for r in rows]))
