"""
VERIAudit v0.1 pilot — real model evaluation run.

Runs the 30-intent x 4-linguistic-variant benchmark
(dataset/examples/veriaudit-pilot-v0.1-30.jsonl) against two local MLX
models, greedy decoding, saves every raw response unedited plus full run
metadata for reproducibility.

Usage (from repo root, using .venv-mlx):
    .venv-mlx/bin/python results/raw/pilot_v0.1/run_eval.py
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_PATH = REPO_ROOT / "dataset" / "examples" / "veriaudit-pilot-v0.1-30.jsonl"
OUTPUT_DIR = Path(__file__).resolve().parent

MODELS = [
    {
        "model_id": "mlx-community/Qwen3-8B-4bit",
        "short_name": "qwen3-8b",
        # Qwen3 defaults to an internal <think>...</think> reasoning block
        # before its final answer. Disabled here for direct comparability
        # with Aya Expanse (no equivalent thinking mode) and because 300
        # max_tokens is not enough to hold both a thinking trace and a
        # final answer, which would otherwise truncate mid-thought and
        # leave nothing to label. Documented, not silently defaulted.
        "chat_template_kwargs": {"enable_thinking": False},
    },
    {
        "model_id": "mlx-community/aya-expanse-8b-4bit",
        "short_name": "aya-expanse-8b",
        "chat_template_kwargs": {},
    },
]

SYSTEM_PROMPT = "You are a helpful, honest assistant."
TEMPERATURE = 0.0  # greedy decoding, for reproducibility
MAX_TOKENS = 300
FORMS = ["english", "urdu", "roman_urdu", "code_switched"]


def load_dataset() -> list[dict]:
    with DATASET_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def run_model(model_spec: dict, intents: list[dict]) -> tuple[list[dict], dict]:
    model_id = model_spec["model_id"]
    print(f"\n=== Loading {model_id} ===", flush=True)
    t0 = time.time()
    model, tokenizer = load(model_id)
    load_seconds = round(time.time() - t0, 1)
    print(f"Loaded in {load_seconds}s", flush=True)

    sampler = make_sampler(temp=TEMPERATURE)
    results = []
    total = len(intents) * len(FORMS)
    i = 0
    for intent in intents:
        for form in FORMS:
            i += 1
            prompt_text = intent[form]
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_text},
            ]
            chat_prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                **model_spec["chat_template_kwargs"],
            )

            t_gen0 = time.time()
            response = generate(
                model,
                tokenizer,
                prompt=chat_prompt,
                max_tokens=MAX_TOKENS,
                sampler=sampler,
                verbose=False,
            )
            latency = round(time.time() - t_gen0, 2)

            print(f"[{model_spec['short_name']}] {i}/{total} {intent['id']} ({form}) — {latency}s", flush=True)

            results.append(
                {
                    "model_id": model_id,
                    "model_short_name": model_spec["short_name"],
                    "intent_id": intent["id"],
                    "intent_category": intent["intent_category"],
                    "form": form,
                    "prompt": prompt_text,
                    "response": response,
                    "latency_seconds": latency,
                }
            )

    run_info = {
        "model_id": model_id,
        "chat_template_kwargs": model_spec["chat_template_kwargs"],
        "load_seconds": load_seconds,
        "num_generations": len(results),
    }
    return results, run_info


def main() -> None:
    intents = load_dataset()
    assert len(intents) == 30, f"expected 30 intents, got {len(intents)}"

    run_metadata = {
        "run_started_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(DATASET_PATH.relative_to(REPO_ROOT)),
        "dataset_git_commit": git_commit_hash(),
        "num_intents": len(intents),
        "forms": FORMS,
        "system_prompt": SYSTEM_PROMPT,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "sampling": "greedy (temp=0.0)",
        "host": {
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        },
        "mlx_lm_version": __import__("mlx_lm").__version__ if hasattr(__import__("mlx_lm"), "__version__") else "unknown",
        "models": [],
    }

    all_results = []
    for model_spec in MODELS:
        results, run_info = run_model(model_spec, intents)
        all_results.extend(results)
        run_metadata["models"].append(run_info)

        out_path = OUTPUT_DIR / f"{model_spec['short_name']}_responses.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Wrote {len(results)} responses to {out_path}", flush=True)

    run_metadata["run_finished_utc"] = datetime.now(timezone.utc).isoformat()
    run_metadata["total_evaluations"] = len(all_results)

    combined_path = OUTPUT_DIR / "all_responses.jsonl"
    with combined_path.open("w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    metadata_path = OUTPUT_DIR / "run_metadata.json"
    metadata_path.write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nDone. {len(all_results)} total evaluations.", flush=True)
    print(f"Combined: {combined_path}", flush=True)
    print(f"Metadata: {metadata_path}", flush=True)


if __name__ == "__main__":
    main()
