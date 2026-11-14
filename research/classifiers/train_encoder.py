"""RQ5: fine-tune multilingual encoders for response- or prompt-level safety classification.

NOT RUN in the development sandbox (no GPU, no Hugging Face access). Designed for Colab/remote GPU.

Encoders (protocol §11): xlm-roberta-base, microsoft/mdeberta-v3-base, google/muril-base-cased.
Conditions:
  english_only   train on English examples only, evaluate on every form
  mixed          train on all forms
  lofo:<form>    train on the other three forms, evaluate on <form>
Splits: scenario-grouped train/validation/test from VeriAudit-X (`app.veriaudit_x.splits`) -- never random.

Input JSONL (one example per line): {"text", "label" (0/1), "form", "scenario_id", "split"}; build it from
judged main-study generations (task A) or from VeriAudit-X prompts (task B) with research/classifiers/build_examples.py.

    python research/classifiers/train_encoder.py --data examples.jsonl --model xlm-roberta-base --condition mixed --out results/v2/classifiers/xlmr_mixed
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

MODELS = {"xlmr": "xlm-roberta-base", "mdeberta": "microsoft/mdeberta-v3-base", "muril": "google/muril-base-cased"}
FORMS = ["english", "urdu", "roman_urdu", "code_switched"]


def check_splits(rows: list[dict], split_assignment: dict[str, str] | None = None) -> None:
    """Leakage gate (protocol §11). Every scenario is in exactly one split; that split matches the
    dataset's scenario-grouped assignment when given; human-validated examples are test-only."""
    where: dict[str, set[str]] = {}
    for r in rows:
        if r["split"] not in ("train", "validation", "test"):
            raise ValueError(f"invalid split {r['split']!r}")
        where.setdefault(r["scenario_id"], set()).add(r["split"])
    spread = {s: v for s, v in where.items() if len(v) > 1}
    if spread:
        raise ValueError(f"scenario leakage: {len(spread)} scenarios in several splits, e.g. {next(iter(spread.items()))}")
    if split_assignment is not None:
        wrong = {s for s, v in where.items() if split_assignment.get(s) not in v}
        if wrong:
            raise ValueError(f"{len(wrong)} scenarios disagree with the dataset split manifest, e.g. {sorted(wrong)[:3]}")
    misplaced = [r for r in rows if r.get("human_validated") and r["split"] != "test"]
    if misplaced:
        raise ValueError(f"{len(misplaced)} human-validated examples outside the test split")


def select(rows: list[dict], condition: str, split_assignment: dict[str, str] | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    check_splits(rows, split_assignment)
    train = [r for r in rows if r["split"] == "train"]
    val = [r for r in rows if r["split"] == "validation"]
    test = [r for r in rows if r["split"] == "test"]
    if condition == "english_only":
        train = [r for r in train if r["form"] == "english"]
        val = [r for r in val if r["form"] == "english"]
    elif condition.startswith("lofo:"):
        held = condition.split(":", 1)[1]
        if held not in FORMS:
            raise ValueError(f"unknown form {held}")
        train = [r for r in train if r["form"] != held]
        val = [r for r in val if r["form"] != held]
        test = [r for r in test if r["form"] == held]
    elif condition != "mixed":
        raise ValueError(f"unknown condition {condition}")
    return train, val, test


def scenario_bootstrap_ci(y_true, y_pred, scenario_ids, metric, n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Point estimate and 95% percentile CI of `metric(y_true, y_pred)`, resampling whole scenarios."""
    y_true, y_pred, sids = np.asarray(y_true), np.asarray(y_pred), np.asarray(scenario_ids)
    groups = {s: np.flatnonzero(sids == s) for s in np.unique(sids)}
    keys = list(groups)
    rng = np.random.default_rng(seed)
    point = float(metric(y_true, y_pred))
    draws = []
    for _ in range(n_boot):
        idx = np.concatenate([groups[keys[i]] for i in rng.integers(0, len(keys), len(keys))])
        draws.append(metric(y_true[idx], y_pred[idx]))
    lo, hi = np.nanquantile(np.asarray(draws, dtype=float), [0.025, 0.975])
    return point, float(lo), float(hi)


def expected_calibration_error(probs: np.ndarray, labels: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        m = (probs > lo) & (probs <= hi)
        if m.any():
            ece += m.mean() * abs(labels[m].mean() - probs[m].mean())
    return float(ece)


def main(argv=None) -> int:  # pragma: no cover - GPU path
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--model", required=True, help="key in MODELS or a HF model id")
    ap.add_argument("--condition", default="mixed")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--split-manifest", type=Path, required=True, help="splits/split_manifest.json of the VeriAudit-X release")
    ap.add_argument("--revision", default=None, help="pinned commit of the encoder checkpoint")
    args = ap.parse_args(argv)

    import torch
    from datasets import Dataset
    from sklearn.metrics import f1_score, precision_recall_fscore_support
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments

    rows = [json.loads(x) for x in args.data.read_text(encoding="utf-8").splitlines() if x.strip()]
    assignment = json.loads(args.split_manifest.read_text(encoding="utf-8"))["assignment"]
    train, val, test = select(rows, args.condition, assignment)
    name = MODELS.get(args.model, args.model)
    tok = AutoTokenizer.from_pretrained(name, revision=args.revision)
    model = AutoModelForSequenceClassification.from_pretrained(name, num_labels=2, revision=args.revision)

    def enc(rs):
        return Dataset.from_list(rs).map(lambda b: tok(b["text"], truncation=True, max_length=384), batched=True)

    pos = sum(r["label"] for r in train) / max(1, len(train))
    weights = torch.tensor([pos, 1 - pos], dtype=torch.float)

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kw):
            labels = inputs.pop("labels")
            out = model(**inputs)
            loss = torch.nn.functional.cross_entropy(out.logits, labels, weight=weights.to(out.logits.device))
            return (loss, out) if return_outputs else loss

    targs = TrainingArguments(
        output_dir=str(args.out / "ckpt"),
        num_train_epochs=args.epochs,
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        seed=args.seed,
        report_to=[],
    )
    trainer = WeightedTrainer(model=model, args=targs, train_dataset=enc(train), eval_dataset=enc(val), tokenizer=tok)
    trainer.train()
    logits = trainer.predict(enc(test)).predictions
    probs = torch.softmax(torch.tensor(logits), -1)[:, 1].numpy()
    y = np.array([r["label"] for r in test])
    pred = (probs >= 0.5).astype(int)
    sids = [r["scenario_id"] for r in test]

    def macro_f1(a, b):
        return f1_score(a, b, average="macro", zero_division=0)

    point, lo, hi = scenario_bootstrap_ci(y, pred, sids, macro_f1, seed=args.seed)
    import transformers

    result = {
        "model": name,
        "revision": args.revision,
        "transformers_version": transformers.__version__,
        "torch_version": torch.__version__,
        "condition": args.condition,
        "seed": args.seed,
        "n_train": len(train),
        "n_test": len(test),
        "n_test_scenarios": len(set(sids)),
        "macro_f1": point,
        "macro_f1_ci95_scenario_bootstrap": [lo, hi],
        "ece": expected_calibration_error(probs, y),
        "by_form": {},
    }
    for f in FORMS:
        m = np.array([r["form"] == f for r in test])
        if m.any():
            p, r_, f1, _ = precision_recall_fscore_support(y[m], pred[m], average=None, labels=[0, 1], zero_division=0)
            fpr = float(((pred[m] == 1) & (y[m] == 0)).sum() / max(1, (y[m] == 0).sum()))
            fp, flo, fhi = scenario_bootstrap_ci(y[m], pred[m], np.asarray(sids)[m], macro_f1, seed=args.seed)
            result["by_form"][f] = {
                "n": int(m.sum()),
                "macro_f1": fp,
                "macro_f1_ci95": [flo, fhi],
                "precision_unsafe": float(p[1]),
                "recall_unsafe": float(r_[1]),
                "fpr": fpr,
                "ece": expected_calibration_error(probs[m], y[m]),
            }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
