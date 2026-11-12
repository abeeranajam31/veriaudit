"""RQ5 preliminary: does a response-level harmful-content classifier generalise across linguistic forms?

Data: the 240 v0.1 pilot responses with their final labels (66 human, 174 LLM-assisted;
results/v1_reconstruction/final_labels.csv). Target: UNSAFE (partial or unsafe compliance)
vs NOT-UNSAFE (safe refusal or ambiguous). Only 44 positives, 1 of them in English, so
"English-only training" is impossible on this data; we run:

  (a) leave-one-form-out: train on three prompt forms, test on the fourth;
  (b) intent-grouped 5-fold CV over all forms (no intent in both train and test).

Features: character 2-5-gram TF-IDF (script-agnostic) -> logistic regression (class-balanced).
Baselines: majority class; v2 rule judge ("UNSAFE" if compliance_shape or mixed).
CIs: percentile bootstrap over intents (2,000 resamples). This is a small, exploratory
experiment on pilot data; it does not evaluate XLM-R/mDeBERTa/MuRIL (those need a GPU and
Hugging Face access; see research/classifiers/train_encoder.py).

Run: PYTHONPATH=backend python research/classifiers/v1_response_baseline.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import GroupKFold

from app.v2.judges.rule_judge import judge

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "v2" / "classifiers"
FORMS = ["english", "urdu", "roman_urdu", "code_switched"]
SEED = 20261112


def load():
    labels = {r["evaluation_id"]: r for r in csv.DictReader((ROOT / "results/v1_reconstruction/final_labels.csv").open(encoding="utf-8"))}
    raw = {}
    for line in (ROOT / "results/raw/pilot_v0.1/all_responses.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        raw[f"{r['model_short_name']}__{r['intent_id']}__{r['form']}"] = r["response"]
    ids = sorted(labels)
    X = [raw[i] for i in ids]
    y = np.array([labels[i]["final_label"] in ("partial_compliance", "unsafe_compliance") for i in ids], dtype=int)
    form = np.array([labels[i]["language"] for i in ids])
    group = np.array([labels[i]["intent_id"] for i in ids])
    prov = np.array([labels[i]["label_provenance"] for i in ids])
    return ids, X, y, form, group, prov


def model():
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=SEED)
    return vec, clf


def scores(y, p):
    return {
        "macro_f1": f1_score(y, p, average="macro", zero_division=0),
        "precision_unsafe": precision_score(y, p, zero_division=0),
        "recall_unsafe": recall_score(y, p, zero_division=0),
        "fpr": float(((p == 1) & (y == 0)).sum() / max(1, (y == 0).sum())),
        "n": int(len(y)),
        "n_unsafe": int(y.sum()),
    }


def boot_ci(y, p, groups, n=2000):
    rng = np.random.default_rng(SEED)
    uniq = np.unique(groups)
    idx_by_g = {g: np.where(groups == g)[0] for g in uniq}
    vals = []
    for _ in range(n):
        idx = np.concatenate([idx_by_g[g] for g in rng.choice(uniq, size=len(uniq), replace=True)])
        vals.append(f1_score(y[idx], p[idx], average="macro", zero_division=0))
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return float(lo), float(hi)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ids, X, y, form, group, prov = load()
    X = np.array(X, dtype=object)
    rule_pred = np.array([judge(t).decision in ("compliance_shape", "mixed") for t in X], dtype=int)
    rows = []

    # (a) leave-one-form-out
    for held in FORMS:
        tr, te = form != held, form == held
        vec, clf = model()
        clf.fit(vec.fit_transform(X[tr]), y[tr])
        p = clf.predict(vec.transform(X[te]))
        for name, pred in (("char_ngram_lr", p), ("rule_judge", rule_pred[te]), ("majority", np.zeros(te.sum(), dtype=int))):
            s = scores(y[te], pred)
            lo, hi = boot_ci(y[te], pred, group[te])
            rows.append({"setting": "leave_one_form_out", "test_form": held, "model": name, **s, "macro_f1_ci_low": lo, "macro_f1_ci_high": hi})

    # (b) intent-grouped 5-fold CV over all forms
    pred = np.zeros_like(y)
    for tr, te in GroupKFold(n_splits=5).split(X, y, group):
        vec, clf = model()
        clf.fit(vec.fit_transform(X[tr]), y[tr])
        pred[te] = clf.predict(vec.transform(X[te]))
    for f in FORMS + ["all"]:
        m = np.ones_like(y, dtype=bool) if f == "all" else form == f
        for name, pp in (("char_ngram_lr", pred[m]), ("rule_judge", rule_pred[m])):
            s = scores(y[m], pp)
            lo, hi = boot_ci(y[m], pp, group[m])
            rows.append({"setting": "intent_grouped_5fold", "test_form": f, "model": name, **s, "macro_f1_ci_low": lo, "macro_f1_ci_high": hi})

    # human-labelled rows only (provenance check)
    hm = np.char.startswith(prov.astype(str), "human")
    s = scores(y[hm], pred[hm])
    rows.append(
        {
            "setting": "intent_grouped_5fold_human_labelled_only",
            "test_form": "all",
            "model": "char_ngram_lr",
            **s,
            "macro_f1_ci_low": None,
            "macro_f1_ci_high": None,
        }
    )

    with (OUT / "v1_response_baseline.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    for r in rows:
        print(
            f"{r['setting']:<42} {r['test_form']:<14} {r['model']:<14} F1={r['macro_f1']:.3f} "
            f"[{r['macro_f1_ci_low'] if r['macro_f1_ci_low'] is None else round(r['macro_f1_ci_low'], 3)}, "
            f"{r['macro_f1_ci_high'] if r['macro_f1_ci_high'] is None else round(r['macro_f1_ci_high'], 3)}] "
            f"P={r['precision_unsafe']:.2f} R={r['recall_unsafe']:.2f} FPR={r['fpr']:.2f} n={r['n']} pos={r['n_unsafe']}"
        )


if __name__ == "__main__":
    main()
