"""EXPLORATORY analysis of the v0.1-replication run (configs/experiments/exploratory_v01_panel.yaml).

    PYTHONPATH=backend python research/analysis/exploratory_v01_panel.py \\
        --run results/v2/runs/exploratory-v01-panel \\
        --labels results/v2/labels/exploratory-v01-panel__*.jsonl results/v2/labels/human/exploratory-v01-panel__*.jsonl

The same integrity gates as the main analysis apply: a complete run, an untampered dataset,
registered human raters and no fixture output. The only difference is that this run's dataset is
explicitly non-release, which is recorded. It uses the same estimators as the main study:
- the per-response harmful-compliance rate;
- the paired t-test on per-scenario share differences, Holm across the comparisons present;
- comprehension-stratified rates, which are descriptive.

The outputs are watermarked EXPLORATORY.

Why exploratory: the non-English variants were not independently verified, n = 30, there is no
benign contrast (so no H2), and fp16 was used on T4 GPUs. The scenarios are a subset of the main
study, and this run is never pooled with it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.v2 import metrics as M  # noqa: E402
from app.v2.analysis import Options, flatten_cells, label_agreement, load_inputs, write_csv  # noqa: E402
from app.v2.records import LabelSource, resolve_labels  # noqa: E402

BANNER = (
    "EXPLORATORY: VeriAudit v0.1 prompts (30 harmful requests, PI-written variants not independently verified), "
    "v2 model panel, fp16 on T4. Not a confirmatory result; not pooled with the main study."
)


def analyse(
    run: Path, label_files: list[Path], out: Path, models_manifest: Path, n_boot: int = 2000, allow_fixtures: bool = False, allow_incomplete: bool = False
) -> dict:
    o = Options(
        run, label_files, out, models_manifest, allow_candidate_dataset=True, allow_fixtures=allow_fixtures, allow_incomplete=allow_incomplete, n_boot=n_boot
    )
    o.registry = ROOT / "data" / "annotators.json"
    manifest, gens, labels, records, _ = load_inputs(o)
    if not manifest["dataset"].get("dataset_version", "").startswith("exploratory-v01"):
        raise SystemExit("this script analyses only the exploratory v0.1-replication run")
    fixture = bool(manifest.get("is_fixture_run"))
    resolved = resolve_labels(labels)
    units, excluded = M.build_units(gens, resolved, allow_fixtures=fixture)
    greedy, _ = M.build_units(gens, resolved, aggregation="greedy", allow_fixtures=fixture)
    out.mkdir(parents=True, exist_ok=True)
    cells = flatten_cells(M.cell_metrics(units, n_boot=n_boot), "samples") + flatten_cells(M.cell_metrics(greedy, n_boot=n_boot), "greedy")
    write_csv(out / "cell_metrics.csv", cells)
    h1 = M.paired_family(units, "harmful", "harmful", "H1-exploratory", n_boot=n_boot) if units else []
    write_csv(out / "gaps_harmful_compliance.csv", h1)
    write_csv(out / "comprehension_strata.csv", M.comprehension_stratified(gens, resolved, allow_fixtures=fixture))
    write_csv(out / "linguistic_robustness.csv", M.linguistic_robustness(units))
    agree = label_agreement(labels, {g.generation_id: g for g in gens})
    (out / "label_agreement.json").write_text(json.dumps(agree, indent=2, default=str) + "\n", encoding="utf-8")

    n_succ = sum(g.error is None for g in gens)
    n_res = sum(1 for g in gens if g.generation_id in resolved)
    human_sources = (LabelSource.human, LabelSource.human_adjudicated)
    n_human = sum(1 for g in gens if g.generation_id in resolved and resolved[g.generation_id].label_source in human_sources)
    lines = [
        "# Exploratory v0.1 replication on the v2 model panel",
        "",
        f"> **{BANNER}**",
        "",
        f"Run `{manifest['run_id']}`, dataset `{manifest['dataset']['dataset_version']}` (sha256 {manifest['dataset']['sha256'][:12]}…), "
        f"status `{manifest['status']}`. Overrides recorded: {o.overrides_used or 'none'}.",
        "",
        f"Generations: {n_succ} successful of {len(gens)}. Resolved labels: {n_res} ({n_human} from humans). "
        f"Unresolved responses are unscored and counted, never guessed. Units excluded: {excluded}.",
        "",
        "## Harmful-compliance gap vs English (paired t on per-scenario shares of 3 samples; Holm over the comparisons present)",
        "",
        "| Model | Form | n pairs | gap pp [approx. 95% t CI] | bounds pp (unscored as 0/1) | p (paired t) | Holm p |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in h1:
        lines.append(
            f"| {r['model']} | {r['language']} | {r['n_pairs']} | {r['gap_pp']:.1f} [{r['ci_low_pp']:.1f}, {r['ci_high_pp']:.1f}] | "
            f"[{r['gap_bound_low_pp']:.1f}, {r['gap_bound_high_pp']:.1f}] | {r['p_paired_t']:.3g} | {r['p_holm']:.3g} |"
        )
    lines += [
        "",
        "Other outputs: `cell_metrics.csv` (rates per model × form, sampled and greedy), `comprehension_strata.csv` (RQ3, descriptive), "
        "`linguistic_robustness.csv`, `label_agreement.json` (judge–judge and judge–human agreement per form).",
        "",
        "Interpretation limits: n = 30 (power is low except for large gaps); the variants are PI-written and unverified, so a gap can "
        "partly reflect translation differences; the judges do not document Urdu support and are checked against the human sample in "
        "`label_agreement.json`; there is no H2.",
    ]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"h1": h1, "resolved": n_res, "human": n_human}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--labels", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "v2" / "exploratory" / "v01-panel")
    ap.add_argument("--models", type=Path, default=ROOT / "configs" / "models.yaml")
    ap.add_argument("--allow-incomplete", action="store_true", help="e.g. a model that could not run on T4 (recorded in summary.md)")
    args = ap.parse_args(argv)
    res = analyse(args.run, args.labels, args.out, args.models, allow_incomplete=args.allow_incomplete)
    print(f"{args.out / 'summary.md'}: {len(res['h1'])} comparisons; {res['resolved']} resolved labels ({res['human']} human)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
