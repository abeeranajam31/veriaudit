"""One-time structural fix: split the concatenated 'HUMAN REVIEW (...): ...'
text back out of reviewer_notes into its own human_reviewer_notes field,
and restore reviewer_notes to its original (preliminary-only) content.

This does NOT change any human_label value or the substance of any human
note — it only moves the same text into a properly separated field, per
the user's explicit instruction not to overwrite/modify/reinterpret the
30 human-reviewed rows. Verified non-lossy below.
"""

import json
import re

LABELS_PATH = "results/labeling/labels.jsonl"

PATTERN = re.compile(r"^(?P<preliminary>.*?) \| HUMAN REVIEW \((?P<label>[a-z_]+)\): (?P<note>.*)$", re.DOTALL)

rows = [json.loads(l) for l in open(LABELS_PATH, encoding="utf-8")]
fixed = 0
for row in rows:
    if row["human_label"] == "":
        row.setdefault("human_reviewer_notes", "")
        continue
    m = PATTERN.match(row["reviewer_notes"])
    assert m, f"pattern did not match for {row['evaluation_id']}: {row['reviewer_notes']!r}"
    assert m.group("label") == row["human_label"], f"label mismatch for {row['evaluation_id']}"
    row["reviewer_notes"] = m.group("preliminary")
    row["human_reviewer_notes"] = m.group("note")
    fixed += 1

with open(LABELS_PATH, "w", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

print(f"Fixed {fixed} rows: split human note into human_reviewer_notes field.")
