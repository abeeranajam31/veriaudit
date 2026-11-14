"""Split the selected scenarios into generation batches and pick the controlled-transformation subset.

Transformation subset (protocol §5.2): a third of scenarios, stratified by category,
chosen by seeded hash order within category. Run after build_candidates.py:
    PYTHONPATH=backend python research/dataset/make_generation_batches.py
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAND = ROOT / "data" / "candidates"
SEED = 20261112
N_BATCHES = 8


def main() -> None:
    sel = [json.loads(x) for x in (CAND / "selection.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    by_cat = defaultdict(list)
    for c in sel:
        by_cat[c["category"]].append(c)
    subset = set()
    for _cat, items in sorted(by_cat.items()):
        ordered = sorted(items, key=lambda c: hashlib.sha256(f"{SEED}:T:{c['scenario_id']}".encode()).hexdigest())
        subset.update(c["scenario_id"] for c in ordered[: math.ceil(len(items) / 3)])
    (CAND / "transformation_subset.json").write_text(json.dumps(sorted(subset), indent=1) + "\n", encoding="utf-8")

    bdir = CAND / "batches"
    bdir.mkdir(exist_ok=True)
    size = math.ceil(len(sel) / N_BATCHES)
    for b in range(N_BATCHES):
        with (bdir / f"batch_{b + 1:02d}.jsonl").open("w", encoding="utf-8") as f:
            for c in sel[b * size : (b + 1) * size]:
                row = {
                    "scenario_id": c["scenario_id"],
                    "category": c["category"],
                    "source": c["source"],
                    "harmful_en": c["harmful_en"],
                    "benign_en": c["benign_en"],
                    "needs_benign_authoring": c["benign_en"] is None,
                    "fixed_harmful_variants": c.get("v1_variants"),
                    "needs_transformations": c["scenario_id"] in subset,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{len(subset)} scenarios in transformation subset; {N_BATCHES} batches of <= {size}")


if __name__ == "__main__":
    main()
