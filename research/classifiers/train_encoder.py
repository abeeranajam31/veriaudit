"""RQ5: fine-tune multilingual encoders for response- or prompt-level safety classification.

NOT RUN in the development sandbox (no GPU, no Hugging Face access). Designed for Colab/remote GPU.

Encoders (protocol §11): xlm-roberta-base, microsoft/mdeberta-v3-base, google/muril-base-cased.
Conditions:
  english_only   train on English examples only, evaluate on every form
  mixed          train on all forms
  lofo:<form>    train on the other three forms, evaluate on <form>
Splits: scenario-grouped train/validation/test from VeriAudit-X (`app.veriaudit_x.splits`) -- never random.

Input JSONL (one example per line): {"text", "label" (0/1), "form", "scenario_id", "split"}; build it from
judged main-study generations (task A) or from VeriAudit-X prompts (task B); the builder is a pending task (PROGRESS.md).

    python research/classifiers/train_encoder.py --data examples.jsonl --model xlm-roberta-base --condition mixed --out results/v2/classifiers/xlmr_mixed
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

MODELS = {"xlmr": "xlm-roberta-base", "mdeberta": "microsoft/mdeberta-v3-base", "muril": "google/muril-base-cased"}
FORMS = ["english", "urdu", "roman_urdu", "code_switched"]


def select(rows: list[dict], condition: str) -> tuple[list[dict], list[dict], list[dict]]:
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
    leaked = {r["scenario_id"] for r in train} & {r["scenario_id"] for r in test}
    if leaked:
        raise ValueError(f"scenario leakage between train and test: {sorted(leaked)[:5]}")
    return train, val, test


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
    args = ap.parse_args(argv)

    import torch
    from datasets import Dataset
    from sklearn.metrics import f1_score, precision_recall_fscore_support
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments

    rows = [json.loads(x) for x in args.data.read_text(encoding="utf-8").splitlines() if x.strip()]
    train, val, test = select(rows, args.condition)
    name = MODELS.get(args.model, args.model)
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForSequenceClassification.from_pretrained(name, num_labels=2)

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
    result = {
        "model": name,
        "condition": args.condition,
        "n_test": len(test),
        "macro_f1": f1_score(y, pred, average="macro"),
        "ece": expected_calibration_error(probs, y),
        "by_form": {},
    }
    for f in FORMS:
        m = np.array([r["form"] == f for r in test])
        if m.any():
            p, r_, f1, _ = precision_recall_fscore_support(y[m], pred[m], average=None, labels=[0, 1], zero_division=0)
            fpr = float(((pred[m] == 1) & (y[m] == 0)).sum() / max(1, (y[m] == 0).sum()))
            result["by_form"][f] = {"macro_f1": float(f1.mean()), "precision_unsafe": float(p[1]), "recall_unsafe": float(r_[1]), "fpr": fpr}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
