import json
from collections import Counter

rows = [json.loads(l) for l in open("results/labeling/labels.jsonl", encoding="utf-8")]

print("=== Overall label counts ===")
print(Counter([r["preliminary_label"] for r in rows]))
print()
print("=== By model ===")
for model in ["qwen3-8b", "aya-expanse-8b"]:
    sub = [r for r in rows if r["model"] == model]
    print(model, Counter([r["preliminary_label"] for r in sub]))
print()
print("=== By form ===")
for form in ["english", "urdu", "roman_urdu", "code_switched"]:
    sub = [r for r in rows if r["linguistic_variant"] == form]
    print(form, Counter([r["preliminary_label"] for r in sub]))
print()
print("=== By model x form ===")
for model in ["qwen3-8b", "aya-expanse-8b"]:
    for form in ["english", "urdu", "roman_urdu", "code_switched"]:
        sub = [r for r in rows if r["model"] == model and r["linguistic_variant"] == form]
        print(model, form, Counter([r["preliminary_label"] for r in sub]))
print()
concerning = [r for r in rows if r["preliminary_label"] in ("unsafe_compliance", "partial_compliance")]
print("=== unsafe_compliance + partial_compliance cases:", len(concerning), "===")
for r in concerning:
    print(f"  {r['evaluation_id']}: {r['preliminary_label']} ({r['confidence']})")
print()
print("=== language_consistency_issue count ===")
print(sum(1 for r in rows if r["language_consistency_issue"]))
print()
print("=== response_language distribution ===")
print(Counter([r["response_language"] for r in rows]))
print()
print("=== confidence distribution ===")
print(Counter([r["confidence"] for r in rows]))
