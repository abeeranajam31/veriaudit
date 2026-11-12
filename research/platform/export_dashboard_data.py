"""Export real research outputs into one JSON file for the static dashboard and the API.

Only files produced from real data are read; nothing here is simulated. Every block
carries a `provenance` string shown in the UI.

Run: PYTHONPATH=backend python research/platform/export_dashboard_data.py
Writes: results/v2/dashboard.json (API) and frontend/src/data/v2/dashboard.json (static site)
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTS = [ROOT / "results" / "v2" / "dashboard.json", ROOT / "frontend" / "src" / "data" / "v2" / "dashboard.json"]


def rcsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(x):
    try:
        return round(float(x), 4)
    except (TypeError, ValueError):
        return None


def build() -> dict:
    rec = ROOT / "results" / "v1_reconstruction"
    summary = json.loads((rec / "summary.json").read_text())
    paired = rcsv(rec / "paired_tests.csv")
    comparisons = {}
    for r in paired:
        key = (r["model"], r["language"])
        c = comparisons.setdefault(key, {"model": r["model"], "language": r["language"]})
        prefix = {"safety_rate_ambiguous_excluded": "v1", "harmful_compliance_gap": "hc", "safe_rate_gap_amb_not_safe": "safe"}[r["definition"]]
        c.update(
            {
                f"{prefix}_gap_pp": num(r["gap_pp"]),
                f"{prefix}_ci_low_pp": num(r["ci_low_pp"]),
                f"{prefix}_ci_high_pp": num(r["ci_high_pp"]),
                f"{prefix}_p_holm": num(r["p_holm"]),
            }
        )
    drift = [
        dict(r, n=int(r["n"]), safe=int(r["safe"]), harmful=int(r["harmful"]), non_scoreable=int(r["non_scoreable"])) for r in rcsv(rec / "language_drift.csv")
    ]
    cls = [
        {k: (num(v) if k not in ("setting", "test_form", "model") else v) for k, v in r.items()}
        for r in rcsv(ROOT / "results" / "v2" / "classifiers" / "v1_response_baseline.csv")
        if r["setting"] in ("leave_one_form_out", "intent_grouped_5fold") and r["model"] != "majority"
    ]
    sel = [json.loads(x) for x in (ROOT / "data" / "candidates" / "selection.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    sel_counts = Counter((c["category"], c["source"]) for c in sel)
    power = [
        dict(r, power_bonferroni_15=num(r["power_bonferroni_15"]), n_scenarios=int(r["n_scenarios"]))
        for r in rcsv(ROOT / "results" / "power" / "power_mcnemar.csv")
        if r["n_scenarios"] in ("120", "150", "200", "240")
    ]

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": [
            {
                "item": "v0.1 pilot reconstruction",
                "state": "done",
                "detail": f"{summary['verification']['matched']}/{summary['verification']['checks']} published numbers reproduced",
            },
            {"item": "VeriAudit-X main-study scenario selection", "state": "done", "detail": f"{len(sel)} scenarios selected from AdvBench, XSTest and v0.1"},
            {
                "item": "Urdu / Roman Urdu / code-switched variants",
                "state": "blocked",
                "detail": "awaiting human translation (AI generation stopped by model safety classifiers)",
            },
            {"item": "Main-study inference (5 models)", "state": "not run", "detail": "requires GPU; pipeline tested on CPU fixtures only"},
            {"item": "Encoder classifiers (XLM-R, mDeBERTa, MuRIL)", "state": "not run", "detail": "requires GPU and Hugging Face access"},
        ],
        "v1": {
            "provenance": "Real data: VeriAudit v0.1 pilot (Qwen3-8B, Aya Expanse 8B; 30 harmful intents x 4 forms). Labels: 66 human, 174 LLM-assisted.",
            "verification": {"checks": summary["verification"]["checks"], "matched": summary["verification"]["matched"]},
            "comparisons": sorted(comparisons.values(), key=lambda c: (c["model"], c["language"])),
            "bootstrap_mean_v1_pp": summary["v2_bootstrap_mean_clsg_s1_pp"],
            "bootstrap_mean_hc_pp": summary["v2_bootstrap_mean_harmful_compliance_gap_pp"],
            "scoring_correction": summary["scoring_correction"],
            "backend_heuristic_clsg": summary["v1_backend_heuristic_clsg_on_pilot_responses"],
            "language_drift": drift,
        },
        "classifier_baseline": {
            "provenance": "Real data: char n-gram logistic regression trained/evaluated on the 240 v0.1 responses (exploratory; 44 positives).",
            "rows": cls,
        },
        "dataset": {
            "provenance": "Selection only: English seeds chosen; no non-English variants exist yet.",
            "counts": [{"category": cat, "source": src, "n": n} for (cat, src), n in sorted(sel_counts.items())],
            "total": len(sel),
        },
        "power": {
            "provenance": (
                "Monte-Carlo power of exact McNemar on noise-free scenario outcomes, alpha .05/15 (protocol §4.3). "
                "With 3-sample response noise power is lower; see results/power/power_with_sampling_noise.csv."
            ),
            "rows": power,
        },
    }


def main() -> None:
    text = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    for out in OUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(out)


if __name__ == "__main__":
    main()
