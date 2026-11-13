"""Pre-flight check for the calibration pilot. Run it on the GPU machine BEFORE starting a paid or
time-limited session, so a missing licence, an unpinned model or a wrong dataset is found in
seconds rather than after an hour of generation.

    PYTHONPATH=backend python research/inference/pilot_preflight.py [--judges gpt_oss_120b mistral_small_3_2] [--offline]

Checks (FAIL blocks the pilot, WARN does not):
  dataset      calibration file hash = the hash in its manifest and in docs/v2/calibration_pilot_package.md
  pins         every confirmatory model and chosen judge pinned to a 40-hex revision
  families     no judge from an organisation under test
  annotators   >= 3 registered humans (two J0 annotators + an adjudicator)            [WARN]
  git          working tree clean, so the run manifest's commit describes the code     [WARN]
  gpu          CUDA GPU present; memory per GPU                                         [WARN off-GPU]
  vllm         importable, version                                                      [WARN off-GPU]
  hf access    each pinned revision reachable with this machine's Hugging Face token
               (gated repos: licence accepted?)                                         [skipped with --offline]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.v2.inference.runner import PINNED_REVISION  # noqa: E402
from app.v2.judges.run_judge import JudgeConfigError, check_judge  # noqa: E402

DATASET = ROOT / "data/veriaudit-x/calibration/veriaudit_x_calibration.jsonl"
EXPECTED_SHA = "41854a8a62ad8fc919922fa236e267c46e49ba6809dfc6939de50bf328a19d24"


def run_checks(judge_keys: list[str], offline: bool) -> list[tuple[str, str, str]]:
    out = []
    sha = hashlib.sha256(DATASET.read_bytes()).hexdigest()
    man = json.loads((DATASET.parent / "manifest.json").read_text(encoding="utf-8"))
    ok = sha == EXPECTED_SHA == man.get("data_sha256")
    out.append(("dataset", "PASS" if ok else "FAIL", f"sha256 {sha[:12]}… (expected {EXPECTED_SHA[:12]}…)"))

    models = yaml.safe_load((ROOT / "configs/models.yaml").read_text(encoding="utf-8"))["models"]
    judges = {j["key"]: j for j in yaml.safe_load((ROOT / "configs/judges.yaml").read_text(encoding="utf-8"))["judges"]}
    conf = [m for m in models if m.get("confirmatory")]
    chosen = [judges[k] for k in judge_keys if k in judges]
    unknown = [k for k in judge_keys if k not in judges]
    unpinned = [s["key"] for s in conf + chosen if not PINNED_REVISION.match(str(s.get("revision") or ""))]
    out.append(("pins", "FAIL" if unpinned or unknown else "PASS", f"unpinned: {unpinned or 'none'}; unknown judges: {unknown or 'none'}"))
    fam = []
    for j in chosen:
        try:
            check_judge(j, models)
        except JudgeConfigError as exc:
            if "under test" in str(exc):
                fam.append(j["key"])
    out.append(("families", "FAIL" if fam else "PASS", f"judges from an organisation under test: {fam or 'none'}"))

    reg = json.loads((ROOT / "data/annotators.json").read_text(encoding="utf-8"))["raters"]
    humans = [r["id"] for r in reg if r.get("human")]
    out.append(("annotators", "PASS" if len(humans) >= 3 else "WARN", f"{len(humans)} registered humans: {humans}"))

    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    out.append(("git", "WARN" if dirty else "PASS", "uncommitted changes" if dirty else "clean"))

    try:
        import torch

        if torch.cuda.is_available():
            n = torch.cuda.device_count()
            gpus = [f"{torch.cuda.get_device_name(i)} {torch.cuda.get_device_properties(i).total_memory / 2**30:.0f} GiB" for i in range(n)]
            out.append(("gpu", "PASS", "; ".join(gpus)))
        else:
            out.append(("gpu", "WARN", "no CUDA GPU visible"))
    except ImportError:
        out.append(("gpu", "WARN", "torch not installed"))
    try:
        import vllm

        out.append(("vllm", "PASS", vllm.__version__))
    except ImportError:
        out.append(("vllm", "WARN", "not installed"))

    if offline:
        out.append(("hf access", "SKIP", "--offline"))
    else:
        try:
            from huggingface_hub import HfApi

            api, bad = HfApi(), []
            for s in conf + chosen:
                try:
                    api.model_info(s["model_id"], revision=s["revision"])  # the pinned commit exists
                    api.auth_check(s["model_id"])  # this token may download it (raises GatedRepoError if the licence is not accepted)
                except Exception as exc:  # noqa: BLE001 - report any access failure
                    bad.append(f"{s['key']}: {type(exc).__name__}")
            out.append(("hf access", "FAIL" if bad else "PASS", "; ".join(bad) or f"{len(conf + chosen)} repos reachable at their pinned revisions"))
        except ImportError:
            out.append(("hf access", "WARN", "huggingface_hub not installed"))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--judges", nargs="*", default=["gpt_oss_120b", "mistral_small_3_2"])
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args(argv)
    checks = run_checks(args.judges, args.offline)
    for name, status, detail in checks:
        print(f"{status:5} {name:11} {detail}")
    failed = [c for c in checks if c[1] == "FAIL"]
    print("\nPREFLIGHT " + ("FAILED - fix the FAIL lines before using GPU time" if failed else "OK"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
