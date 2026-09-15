"""
Generates docs/figures/*.png reproducibly from the authoritative analysis
CSVs in results/labeling/. Read-only against all source data.

Run from anywhere in the repository:
    python3 docs/figures/make_figures.py
"""
import csv
import json
from pathlib import Path
from collections import Counter, defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "results/labeling"
FIG_DIR = ROOT / "docs/figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 11,
    "font.family": "sans-serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.6,
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

MODEL_LABELS = {"qwen3-8b": "Qwen3-8B", "aya-expanse-8b": "Aya Expanse 8B"}
LANG_LABELS = {"english": "English", "urdu": "Urdu", "roman_urdu": "Roman Urdu", "code_switched": "Code-switched"}
LANG_ORDER = ["english", "urdu", "roman_urdu", "code_switched"]
MODEL_ORDER = ["qwen3-8b", "aya-expanse-8b"]
COLORS = {"qwen3-8b": "#2b6cb0", "aya-expanse-8b": "#c05621"}

# ---------- load clsg_results.csv ----------
clsg_rows = list(csv.DictReader((LAB/"clsg_results.csv").open(encoding="utf-8")))
cell = {}  # (model, lang) -> dict
for r in clsg_rows:
    lang = r["language"]
    if lang == "english (reference)":
        lang = "english"
    if lang in LANG_ORDER and r["model"] in MODEL_ORDER:
        cell[(r["model"], lang)] = r

# ============================================================
# Figure 1: Safety rate by language, separated by model
# ============================================================
fig, ax = plt.subplots(figsize=(8, 5))
x = range(len(LANG_ORDER))
width = 0.35
for i, m in enumerate(MODEL_ORDER):
    rates = [float(cell[(m,l)]["safety_rate_percentage"]) for l in LANG_ORDER]
    lo = [float(cell[(m,l)]["wilson_ci_low_pct"]) for l in LANG_ORDER]
    hi = [float(cell[(m,l)]["wilson_ci_high_pct"]) for l in LANG_ORDER]
    err_lo = [r-l for r,l in zip(rates, lo)]
    err_hi = [h-r for r,h in zip(rates, hi)]
    offset = (i - 0.5) * width
    bars = ax.bar([xi+offset for xi in x], rates, width, label=MODEL_LABELS[m],
                   color=COLORS[m], yerr=[err_lo, err_hi], capsize=4, alpha=0.9)
    for xi, r, l in zip(x, rates, LANG_ORDER):
        denom = cell[(m,l)]["valid_denominator"]
        ax.text(xi+offset, r + (err_hi[LANG_ORDER.index(l)] if l in LANG_ORDER else 0) + 2.5,
                f"{r:.1f}%\n(n={denom})", ha="center", va="bottom", fontsize=8)

ax.set_xticks(list(x))
ax.set_xticklabels([LANG_LABELS[l] for l in LANG_ORDER])
ax.set_ylabel("Safety rate (%)\nSAFE / (SAFE + UNSAFE), ambiguous excluded")
ax.set_ylim(0, 115)
ax.set_title("Figure 1. Safety rate by language, by model\nVeriAudit v0.1 pilot (30 evaluations per cell; error bars = 95% Wilson CI)")
ax.legend(loc="lower left", frameon=False)
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
fig.savefig(FIG_DIR/"figure1_safety_rate_by_language.png")
plt.close(fig)
print("Figure 1 written")

# ============================================================
# Figure 2: English-anchored CLSG by model and language
# ============================================================
NON_EN = ["urdu", "roman_urdu", "code_switched"]
fig, ax = plt.subplots(figsize=(8.5, 5.5))
x = range(len(NON_EN))
width = 0.35
for i, m in enumerate(MODEL_ORDER):
    vals = [float(cell[(m,l)]["CLSG_percentage_points"]) for l in NON_EN]
    offset = (i - 0.5) * width
    bars = ax.bar([xi+offset for xi in x], vals, width, label=MODEL_LABELS[m], color=COLORS[m], alpha=0.9)
    for xi, v in zip(x, vals):
        ax.text(xi+offset, v + 1.0, f"{v:.1f}", ha="center", va="bottom", fontsize=9)

ax.set_xticks(list(x))
ax.set_xticklabels([LANG_LABELS[l] for l in NON_EN])
ax.set_ylabel("Observed cross-lingual safety gap (CLSG, percentage points)\nSafetyRate(English) − SafetyRate(language)")
ax.set_ylim(0, 55)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_title("Figure 2. English-anchored CLSG by model and language\nVeriAudit v0.1 pilot (descriptive; not a causal estimate)", fontsize=12)
ax.legend(loc="upper left", frameon=False)
fig.subplots_adjust(top=0.85, left=0.16)
fig.savefig(FIG_DIR/"figure2_clsg_by_model_language.png")
plt.close(fig)
print("Figure 2 written")

# ============================================================
# Figure 3: Failure rate by category
# ============================================================
labels_rows = [json.loads(l) for l in (ROOT/"results/labeling/labels.jsonl").open(encoding="utf-8")]
meta = {r["evaluation_id"]: r for r in labels_rows}
remaining = {r["case_id"]: r for r in csv.DictReader((LAB/"remaining_174_review.csv").open(encoding="utf-8"))}
worksheet = {r["case_id"]: r for r in csv.DictReader((LAB/"human_adjudication_worksheet.csv").open(encoding="utf-8"))}
worksheet_ids = set(worksheet.keys())

def final_label(eid):
    r = meta[eid]
    if r["human_label"] != "":
        return worksheet[eid]["adjudication_label"] if eid in worksheet_ids else r["human_label"]
    return remaining[eid]["independent_label"]

CATS = sorted(set(r["category"] for r in labels_rows))
cat_rate = {}
cat_denom = {}
for cat in CATS:
    rows = [r for r in labels_rows if r["category"] == cat]
    labs = [final_label(r["evaluation_id"]) for r in rows]
    non_amb = [l for l in labs if l != "ambiguous"]
    fails = [l for l in non_amb if l in ("partial_compliance", "unsafe_compliance")]
    cat_denom[cat] = len(non_amb)
    cat_rate[cat] = 100 * len(fails) / len(non_amb) if non_amb else 0

order = sorted(CATS, key=lambda c: -cat_rate[c])
fig, ax = plt.subplots(figsize=(8.5, 5))
bars = ax.barh(order, [cat_rate[c] for c in order], color="#9b2c2c", alpha=0.85)
for bar, c in zip(bars, order):
    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
            f"{cat_rate[c]:.1f}%  (n={cat_denom[c]})", va="center", fontsize=9)
ax.set_xlabel("Failure rate (%)\n(partial_compliance + unsafe_compliance) / non-ambiguous cases")
ax.set_xlim(0, 60)
ax.set_title("Figure 3. Failure rate by category\nVeriAudit v0.1 pilot, both models and all 4 languages combined")
ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
ax.invert_yaxis()
fig.savefig(FIG_DIR/"figure3_failure_rate_by_category.png")
plt.close(fig)
print("Figure 3 written")

# ============================================================
# Figure 4: Ambiguous-case distribution by language and model
# ============================================================
amb_rows = list(csv.DictReader((LAB/"ambiguity_analysis.csv").open(encoding="utf-8")))
assert len(amb_rows) == 18
counts = defaultdict(int)
for r in amb_rows:
    counts[(r["model"], r["language"])] += 1

fig, ax = plt.subplots(figsize=(8, 5))
x = range(len(LANG_ORDER))
width = 0.35
for i, m in enumerate(MODEL_ORDER):
    vals = [counts.get((m,l), 0) for l in LANG_ORDER]
    offset = (i - 0.5) * width
    bars = ax.bar([xi+offset for xi in x], vals, width, label=MODEL_LABELS[m], color=COLORS[m], alpha=0.9)
    for xi, v in zip(x, vals):
        if v:
            ax.text(xi+offset, v + 0.15, str(v), ha="center", va="bottom", fontsize=9)

ax.set_xticks(list(x))
ax.set_xticklabels([LANG_LABELS[l] for l in LANG_ORDER])
ax.set_ylabel("Ambiguous case count (of 18 total)")
ax.set_ylim(0, 12)
ax.set_title("Figure 4. Ambiguous-case distribution by language and model\nVeriAudit v0.1 pilot (18 of 240 evaluations)")
ax.legend(loc="upper right", frameon=False)
fig.savefig(FIG_DIR/"figure4_ambiguous_distribution.png")
plt.close(fig)
print("Figure 4 written")

print("\nAll figures written to", FIG_DIR)
