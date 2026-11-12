"""Figures for the v2 reconstruction (generated only from committed CSV/JSON outputs).

Run: PYTHONPATH=backend python research/figures/make_v2_figures.py
Writes PNGs to docs/v2/figures/.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "results" / "v1_reconstruction"
OUT = ROOT / "docs" / "v2" / "figures"
MODEL = {"qwen3-8b": "Qwen3-8B", "aya-expanse-8b": "Aya Expanse 8B"}
LANG = {"urdu": "Urdu script", "roman_urdu": "Roman Urdu", "code_switched": "Code-switched", "english": "English"}
INK, MUTED, A, B = "#1d1d1b", "#8a8984", "#2f5d50", "#c0632b"


def fig_gaps() -> None:
    rows = list(csv.DictReader((REC / "paired_tests.csv").open(encoding="utf-8")))
    comps = [(m, lang) for m in MODEL for lang in ("urdu", "roman_urdu", "code_switched")]
    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=200)
    for i, (m, lang) in enumerate(comps):
        y = len(comps) - 1 - i
        v1 = next(r for r in rows if r["model"] == m and r["language"] == lang and r["definition"] == "safety_rate_ambiguous_excluded")
        hc = next(r for r in rows if r["model"] == m and r["language"] == lang and r["definition"] == "harmful_compliance_gap")
        lo, hi, g = float(hc["ci_low_pp"]), float(hc["ci_high_pp"]), float(hc["gap_pp"])
        ax.plot([lo, hi], [y, y], color=A, lw=2, solid_capstyle="round")
        ax.plot(g, y, "o", color=A, ms=6, label="Harmful-compliance gap, full denominator (95% Newcombe CI)" if i == 0 else None)
        ax.plot(float(v1["gap_pp"]), y + 0.22, "D", color=B, ms=5, label="Published v0.1 CLSG (ambiguous excluded)" if i == 0 else None)
        mark = "*" if float(hc["p_holm"]) < 0.05 else ""
        ax.text(max(hi, float(v1["gap_pp"])) + 2, y, f"Holm p = {float(hc['p_holm']):.3f}{mark}", va="center", fontsize=7, color=MUTED)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(range(len(comps)), [f"{MODEL[m]} · {LANG[lang]}" for m, lang in reversed(comps)], fontsize=8)
    ax.set_xlabel("Percentage points (target form minus English)", fontsize=8)
    ax.set_xlim(-15, 95)
    ax.tick_params(axis="x", labelsize=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.16), ncol=1)
    ax.set_title("v0.1 pilot: cross-lingual gaps under two outcome definitions (n = 30 intents each)", fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "fig_v2_1_gap_definitions.png")
    plt.close(fig)


def fig_detectors() -> None:
    s = json.loads((REC / "summary.json").read_text())["scoring_correction"]
    langs = ["english", "urdu", "roman_urdu", "code_switched"]
    old = [100 * s["v1_backend_RefusalConsistencyEvaluator"][lang]["refusal_recall_on_SAFE"] for lang in langs]
    new = [100 * s["v2_rule_judge"][lang]["refusal_recall_on_SAFE"] for lang in langs]
    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=200)
    x = range(len(langs))
    ax.bar([i - 0.18 for i in x], old, 0.36, color=B, label="v1 backend heuristic (English patterns)")
    ax.bar([i + 0.18 for i in x], new, 0.36, color=A, label="v2 multilingual rule judge")
    for i, (o, n) in enumerate(zip(old, new, strict=True)):
        ax.text(i - 0.18, o + 1.5, f"{o:.0f}", ha="center", fontsize=7)
        ax.text(i + 0.18, n + 1.5, f"{n:.0f}", ha="center", fontsize=7)
    ax.set_xticks(list(x), [LANG[lang] for lang in langs], fontsize=8)
    ax.set_ylabel("Refusal recall on SAFE responses (%)", fontsize=8)
    ax.set_ylim(0, 105)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(fontsize=7, frameon=False)
    ax.set_title("Lexical refusal detection collapses outside English (v0.1 responses)", fontsize=9, color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "fig_v2_2_refusal_detection.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig_gaps()
    fig_detectors()
    print(sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
