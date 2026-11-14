"""Run the VeriAudit v2 analysis on a completed run (see app/v2/analysis.py).

    PYTHONPATH=backend python research/analysis/run_analysis.py \
        --run results/v2/runs/main-study-v1 --labels results/v2/labels/main-study-v1/*.jsonl
    PYTHONPATH=backend python research/analysis/run_analysis.py --calibration \
        --run results/v2/runs/calibration-pilot-v2 --labels results/v2/labels/calibration-pilot-v2/*.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.v2.analysis import AnalysisRefused, Options, analyse

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--labels", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--models", type=Path, default=ROOT / "configs" / "models.yaml")
    ap.add_argument("--calibration", action="store_true")
    ap.add_argument("--allow-incomplete", action="store_true", help="analyse an incomplete run (recorded in every output)")
    ap.add_argument("--allow-fixtures", action="store_true", help="analyse a fake-backend run (outputs watermarked)")
    ap.add_argument("--allow-candidate-dataset", action="store_true", help="analyse a run on a non-release dataset build (recorded)")
    ap.add_argument("--registry", type=Path, default=ROOT / "data" / "annotators.json")
    ap.add_argument("--n-boot", type=int, default=5000)
    args = ap.parse_args(argv)
    out = args.out or ROOT / "results" / "v2" / "analysis" / args.run.name
    o = Options(
        args.run,
        args.labels,
        out,
        args.models,
        calibration=args.calibration,
        allow_incomplete=args.allow_incomplete,
        allow_fixtures=args.allow_fixtures,
        allow_candidate_dataset=args.allow_candidate_dataset,
        registry=args.registry,
        n_boot=args.n_boot,
    )
    try:
        analyse(o)
    except AnalysisRefused as exc:
        print(f"ANALYSIS REFUSED: {exc}", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
