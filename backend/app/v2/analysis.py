"""End-to-end analysis of a completed VeriAudit v2 run (protocol §9-§10).

    PYTHONPATH=backend python research/analysis/run_analysis.py \\
        --run results/v2/runs/main-study-v1 --labels results/v2/labels/*.jsonl

Refuses, unless explicitly overridden, to analyse: an incomplete run, a run with unpinned models,
a run whose generations or dataset no longer match the hashes in its run manifest, or test
fixtures. Overrides are written into every output, and fixture outputs are watermarked.

Outputs (in --out): reproducibility.json/.md, dataset_quality.md, agreement.json/.md,
cell_metrics.csv, confirmatory_H1.csv, confirmatory_H2.csv, sensitivity.csv, model_based.csv,
transformation_effects.csv, linguistic_robustness.csv, comprehension_strata.csv, figures/*.png,
summary.md. Calibration runs (--calibration) instead write calibration_parameters.csv and
calibration_power.csv (minimum detectable effects). No output contains interpretation; it is
produced only from the inputs listed in reproducibility.json.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import numpy as np
import yaml

from app.v2 import metrics as M
from app.v2.inference.runner import RUN_MANIFEST, load_generations
from app.v2.judges.llm_judge import agreement_report
from app.v2.records import Generation, LabelSource, ResponseLabel, resolve_labels
from app.v2.regression import model_based_effects
from app.v2.stats import cohen_kappa, estimate_logit_heterogeneity, logit_share_power, mde_paired_t_conservative
from app.veriaudit_x.validation import ValidationConfig, validate_file

FIXTURE_BANNER = "TEST FIXTURE OUTPUT - synthetic data, NOT research results. Never cite."
AXES = ("comprehension", "behaviour", "harmful_content", "task_success")


class AnalysisRefused(RuntimeError):
    pass


@dataclass
class Options:
    run_dir: Path
    label_files: list[Path]
    out_dir: Path
    model_manifest: Path
    calibration: bool = False
    allow_incomplete: bool = False
    allow_fixtures: bool = False
    allow_candidate_dataset: bool = False
    registry: Path | None = None
    n_boot: int = 5000
    calibration_sims: int = 600  # per (sigma_form, gap) cell of the calibration power grid
    seed: int = 20261113
    overrides_used: list[str] = field(default_factory=list)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- loading and gates


def load_inputs(o: Options):
    manifest_path = o.run_dir / RUN_MANIFEST
    if not manifest_path.exists():
        raise AnalysisRefused(f"no {RUN_MANIFEST} in {o.run_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    gen_file = o.run_dir / "generations.jsonl"
    problems = []
    if manifest.get("status") != "complete":
        problems.append(("incomplete", f"run status is {manifest.get('status')!r}"))
    if manifest.get("limit"):
        problems.append(("incomplete", f"run used --limit {manifest['limit']}"))
    if not manifest.get("generations_sha256"):
        problems.append(("integrity", "run manifest has no generations hash (run never finished); resume it to completion"))
    if manifest.get("unpinned_models"):
        problems.append(("incomplete", f"unpinned models: {manifest['unpinned_models']}"))
    if manifest.get("generations_sha256") and sha256(gen_file) != manifest["generations_sha256"]:
        problems.append(("integrity", "generations.jsonl changed after the run finished"))
    repo_root = Path(__file__).resolve().parents[3]
    ds_path = Path(manifest["dataset"]["path"])
    ds_path = ds_path if ds_path.is_absolute() else repo_root / ds_path
    if not ds_path.exists() or sha256(ds_path) != manifest["dataset"]["sha256"]:
        problems.append(("integrity", f"dataset {ds_path} missing or changed since the run"))
    if manifest.get("is_fixture_run") and not o.allow_fixtures:
        problems.append(("fixture", "run used the fake test backend"))
    ds_info = manifest["dataset"]
    if not manifest.get("is_fixture_run"):
        if o.calibration and not ds_info.get("is_calibration"):
            problems.append(("candidate", "--calibration given but the dataset is not the calibration set"))
        if not o.calibration and not ds_info.get("is_release"):
            problems.append(("candidate", f"dataset {ds_info.get('dataset_version')!r} is not a frozen release (assemble --release)"))
    for kind, msg in problems:
        if (
            kind == "integrity"
            or (kind == "incomplete" and not o.allow_incomplete)
            or (kind == "fixture" and not o.allow_fixtures)
            or (kind == "candidate" and not o.allow_candidate_dataset)
        ):
            raise AnalysisRefused(msg)
        o.overrides_used.append(msg)
    if manifest.get("is_fixture_run"):
        o.overrides_used.append("fixture run analysed with --allow-fixtures")
    generations = load_generations(gen_file)
    labels: list[ResponseLabel] = []
    for p in o.label_files:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if line.strip():
                labels.append(ResponseLabel.model_validate_json(line))
    registered = None
    if not manifest.get("is_fixture_run") and (o.registry is None or not o.registry.exists()):
        raise AnalysisRefused("a real run needs the rater registry (Options.registry, default data/annotators.json)")
    if o.registry is not None and o.registry.exists():
        reg = json.loads(o.registry.read_text(encoding="utf-8"))
        registered = frozenset(r["id"] for r in reg.get("raters", []) if r.get("human") is True)
    fixture_run = bool(manifest.get("is_fixture_run"))
    dataset = validate_file(ds_path, ValidationConfig(require_all_languages=False, registered_raters=None if fixture_run else registered))
    if dataset.errors:
        raise AnalysisRefused(f"dataset has {len(dataset.errors)} validation errors, e.g. {dataset.errors[0].format()}")
    known = {r.record_id for r in dataset.records}
    orphans = {g.record_id for g in generations} - known
    if orphans:
        raise AnalysisRefused(f"{len(orphans)} generations refer to records not in the dataset, e.g. {sorted(orphans)[0]}")
    excluded = set(manifest["config"].get("exclude_equivalence_status") or [])
    expected = len([r for r in dataset.records if r.equivalence.status.value not in excluded])
    if manifest.get("n_records") != expected:
        msg = f"run covered {manifest.get('n_records')} records but the dataset has {expected} eligible"
        if not o.allow_incomplete:
            raise AnalysisRefused(msg)
        o.overrides_used.append(msg)
    if not fixture_run and registered is not None:
        bad = sorted(
            {lab.labeler_id for lab in labels if lab.label_source in (LabelSource.human, LabelSource.human_adjudicated) and lab.labeler_id not in registered}
        )
        if bad:
            raise AnalysisRefused(f"human labels from IDs not registered as human raters: {bad[:5]}")
    return manifest, generations, labels, dataset.records, ds_path


CONFIRMATORY_FAMILY_MODELS = 4  # protocol §7: fixed before data collection


def confirmatory_models(model_manifest: Path, present: set[str], fixture: bool) -> list[str]:
    if fixture:
        return sorted(present)
    models = yaml.safe_load(model_manifest.read_text(encoding="utf-8"))["models"]
    conf = sorted(m["key"] for m in models if m.get("confirmatory"))
    if len(conf) != CONFIRMATORY_FAMILY_MODELS:
        raise AnalysisRefused(f"model manifest lists {len(conf)} confirmatory models; the protocol fixes {CONFIRMATORY_FAMILY_MODELS}")
    return conf


# --------------------------------------------------------------------------- reports


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def flatten_cells(cells: list[dict], aggregation: str) -> list[dict]:
    out = []
    for c in cells:
        for metric in ("HCR", "ARR", "ORR", "BTS", "CA"):
            out.append(
                {
                    "aggregation": aggregation,
                    "model": c["model"],
                    "language": c["language"],
                    "condition": c["condition"],
                    "metric": metric,
                    **{k: v for k, v in c[metric].items() if k != "n_unscored_by_status"},
                }
            )
    return out


def dataset_quality(records) -> str:
    by_form = defaultdict(Counter)
    for r in records:
        if r.transformation.type.value == "source":
            continue
        key = (r.language.value, r.transformation.parameters.get("condition", "base"))
        by_form[key][r.equivalence.status.value] += 1
        by_form[key]["human_reviewed"] += r.quality.human_reviewed
        by_form[key]["ai_generated_or_assisted"] += r.quality.ai_generated
        by_form[key]["failed_automated_check"] += any(not c.passed for c in r.quality.automated_checks.values())
    cols = ["pending", "flagged", "verified", "rejected", "human_reviewed", "ai_generated_or_assisted", "failed_automated_check"]
    lines = ["# Dataset quality (records used by this run)", "", "| Form | Condition | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 2)]
    for (lang, cond), c in sorted(by_form.items()):
        lines.append(f"| {lang} | {cond} | " + " | ".join(str(c[k]) for k in cols) + " |")
    return "\n".join(lines) + "\n"


def equivalence_agreement(records) -> dict:
    """Cohen's kappa between the first two independent reviewers on records rated by >= 2."""
    a, b, per_form = [], [], defaultdict(lambda: ([], []))
    for r in records:
        ind = sorted((h for h in r.equivalence.human_ratings if h.rater_role.value == "independent_reviewer"), key=lambda h: h.annotator_id)
        if len(ind) >= 2:
            a.append(ind[0].judgement.value)
            b.append(ind[1].judgement.value)
            per_form[r.language.value][0].append(ind[0].judgement.value)
            per_form[r.language.value][1].append(ind[1].judgement.value)
    out = {"n_double_rated": len(a), "kappa": cohen_kappa(a, b) if a else None}
    out["per_form"] = {k: {"n": len(x), "kappa": cohen_kappa(x, y)} for k, (x, y) in per_form.items()}
    return out


def label_agreement(labels: list[ResponseLabel], generations: dict[str, Generation]) -> dict:
    lang = {gid: g.language for gid, g in generations.items()}
    by_gen = defaultdict(list)
    for lab in labels:
        by_gen[lab.generation_id].append(lab)
    judges = sorted({lab.labeler_id for lab in labels if lab.label_source == LabelSource.ai_judge})
    out: dict = {"n_labels": len(labels), "by_source": dict(Counter(lab.label_source.value for lab in labels)), "judge_pairs": {}}
    for i, j1 in enumerate(judges):
        for j2 in judges[i + 1 :]:
            p = {g: x for g, labs in by_gen.items() for x in labs if x.labeler_id == j1}
            q = {g: x for g, labs in by_gen.items() for x in labs if x.labeler_id == j2}
            out["judge_pairs"][f"{j1} vs {j2}"] = agreement_report(p, q, lang)
    human = {g: x for g, labs in by_gen.items() for x in labs if x.label_source in (LabelSource.human, LabelSource.human_adjudicated)}
    for j in judges:
        p = {g: x for g, labs in by_gen.items() for x in labs if x.labeler_id == j}
        if set(p) & set(human):
            out.setdefault("judge_vs_human", {})[j] = agreement_report(p, human, lang)
    humans = defaultdict(dict)
    for g, labs in by_gen.items():
        for x in labs:
            if x.label_source == LabelSource.human:
                humans[x.labeler_id][g] = x
    hs = sorted(humans)
    if len(hs) >= 2:
        out["human_vs_human"] = agreement_report(humans[hs[0]], humans[hs[1]], lang)
    out["any_human_labels"] = bool(human)
    return out


# --------------------------------------------------------------------------- sensitivity filters


def record_filters(records) -> dict[str, set[str]]:
    """record_ids to EXCLUDE under each sensitivity analysis (protocol §6, §10). English sources are never excluded."""
    s_eq, s_hum1, s_hum2 = set(), set(), set()
    for r in records:
        if r.transformation.type.value == "source":
            continue
        if any(not c.passed for c in r.quality.automated_checks.values()):
            s_eq.add(r.record_id)
        author = r.transformation.author_id
        ind = [h for h in r.equivalence.human_ratings if h.rater_role.value == "independent_reviewer" and h.annotator_id != author]
        ok1 = any(h.judgement.value == "equivalent" and h.harm_preserved is not False for h in ind) and not any(
            h.judgement.value == "not_equivalent" or h.harm_preserved is False for h in ind
        )
        if not ok1:
            s_hum1.add(r.record_id)
        if r.equivalence.status.value != "verified":
            s_hum2.add(r.record_id)
    return {"S-EQ": s_eq, "S-HUM1": s_hum1, "S-HUM2": s_hum2}


def _families(units, models, n_boot, seed):
    h1 = M.paired_family(units, "harmful", "harmful", "H1", n_boot=n_boot, seed=seed, models=models)
    h2 = M.paired_family(units, "benign", "refused", "H2", n_boot=n_boot, seed=seed, models=models)
    return h1, h2


# --------------------------------------------------------------------------- main analyses


def analyse(o: Options) -> dict:
    manifest, generations, labels, records, ds_path = load_inputs(o)
    fixture = bool(manifest.get("is_fixture_run"))
    o.out_dir.mkdir(parents=True, exist_ok=True)
    gen_by_id = {g.generation_id: g for g in generations}
    resolved = resolve_labels(labels)
    in_run = set(gen_by_id)
    resolved = {k: v for k, v in resolved.items() if k in in_run}
    excluded_status = set(manifest["config"].get("exclude_equivalence_status") or [])
    record_status = {r.record_id: r.equivalence.status.value for r in records}
    gens = [g for g in generations if record_status.get(g.record_id) not in excluded_status]

    outputs: dict = {}
    units, unit_stats = M.build_units(gens, resolved, allow_fixtures=fixture)
    outputs["unit_stats"] = unit_stats

    (o.out_dir / "dataset_quality.md").write_text(dataset_quality([r for r in records if r.record_id in {g.record_id for g in gens}]), encoding="utf-8")
    agreement = {"labels": label_agreement(labels, gen_by_id), "equivalence": equivalence_agreement(records)}
    (o.out_dir / "agreement.json").write_text(json.dumps(agreement, indent=2, default=str) + "\n", encoding="utf-8")

    if o.calibration:
        outputs.update(calibration(units, o))
    else:
        outputs.update(main_analysis(units, gens, resolved, records, manifest, o, fixture, labels))
    repro = reproducibility(manifest, o, ds_path, unit_stats, labels, resolved)
    (o.out_dir / "reproducibility.json").write_text(json.dumps(repro, indent=2, default=str) + "\n", encoding="utf-8")
    (o.out_dir / "summary.md").write_text(summary_md(repro, outputs, agreement, fixture, o), encoding="utf-8")
    return outputs


def main_analysis(units, gens, resolved, records, manifest, o: Options, fixture: bool, labels: list[ResponseLabel]) -> dict:
    out = {}
    models = confirmatory_models(o.model_manifest, {u.model for u in units}, fixture)
    cells = M.cell_metrics(units, n_boot=o.n_boot, seed=o.seed)
    greedy_units, _ = M.build_units(gens, resolved, aggregation="greedy", allow_fixtures=fixture)
    cells_greedy = M.cell_metrics(greedy_units, n_boot=o.n_boot, seed=o.seed)
    write_csv(o.out_dir / "cell_metrics.csv", flatten_cells(cells, "samples") + flatten_cells(cells_greedy, "greedy"))
    try:
        h1, h2 = _families(units, models, o.n_boot, o.seed)
    except M.FamilyIncompleteError as exc:
        raise AnalysisRefused(f"confirmatory family incomplete: {exc}") from exc
    write_csv(o.out_dir / "confirmatory_H1.csv", h1)
    write_csv(o.out_dir / "confirmatory_H2.csv", h2)
    out["H1"], out["H2"] = h1, h2

    sens = []

    def add(name, h1x, h2x):
        if not h1x and not h2x:  # an analysis that cannot run is reported, never silently omitted
            sens.append({"analysis": name, "family": "H1+H2", "model": "", "language": "", "n_pairs": 0, "note": "not estimable"})
            return
        for fam, rows in (("H1", h1x), ("H2", h2x)):
            for r in rows:
                sens.append(
                    {
                        "analysis": name,
                        "family": fam,
                        "model": r["model"],
                        "language": r["language"],
                        "n_pairs": r["n_pairs"],
                        "gap_pp": r["gap_pp"],
                        "ci_low_pp": r["ci_low_pp"],
                        "ci_high_pp": r["ci_high_pp"],
                        "p_holm": r["p_holm"],
                    }
                )

    add("primary", h1, h2)
    for treat in ("harmful", "safe", "exclude"):
        u, _ = M.build_units(gens, resolved, ambiguous=treat, allow_fixtures=fixture)
        add(f"S-AMB harmful-intent non_scoreable={treat}", *_families(u, models, o.n_boot, o.seed))
    for treat in ("refusal", "exclude"):
        u, _ = M.build_units(gens, resolved, ambiguous_benign=treat, allow_fixtures=fixture)
        add(f"S-AMB benign non_scoreable={treat}", *_families(u, models, o.n_boot, o.seed))
    add("greedy aggregation", *_safe_families(greedy_units, models, o))
    # each primary judge alone (its labels treated as final), protocol §10
    judges = sorted({lab.labeler_id for lab in labels if lab.label_source == LabelSource.ai_judge})
    for j in judges:
        own = {lab.generation_id: lab.model_copy(update={"label_source": LabelSource.ai_panel}) for lab in labels if lab.labeler_id == j}
        u, _ = M.build_units(gens, own, allow_fixtures=fixture)
        add(f"judge {j} only", *_safe_families(u, models, o))
    for name, drop in record_filters(records).items():
        kept = [g for g in gens if g.record_id not in drop]
        u, _ = M.build_units(kept, resolved, allow_fixtures=fixture)
        res = _safe_families(u, models, o)
        add(f"{name} (excludes {len(drop)} records)" if res[0] else f"{name}: not estimable (too few records)", *res)
    write_csv(o.out_dir / "sensitivity.csv", sens)

    mb = []
    for model in models:
        for stype, outcome in (("harmful", "harmful"), ("benign", "refused")):
            ref = M._index(units, model, stype, "english", "base")
            for lang in M.BASE_LANGS[1:]:
                tgt = M._index(units, model, stype, lang, "base")
                for r in model_based_effects(ref, tgt, outcome):
                    mb.append({"model": model, "language": lang, "outcome": outcome, **r})
    write_csv(o.out_dir / "model_based.csv", mb)
    # RQ2 (exploratory): harmful compliance on harmful intents and over-refusal on benign contrasts; BH within each
    write_csv(
        o.out_dir / "transformation_effects.csv",
        M.transformation_effects(units, "harmful", o.n_boot, o.seed, "harmful") + M.transformation_effects(units, "refused", o.n_boot, o.seed, "benign"),
    )
    # ORR by benign-contrast source (protocol §4.2 rule 5): XSTest prompts vs contrasts authored for this study
    origin = {r.intent_id: r.provenance.origin or "" for r in records if r.transformation.type.value == "source"}
    by_source = []
    for src_name, pred in (("xstest", lambda o_: o_.startswith("xstest:")), ("authored", lambda o_: not o_.startswith("xstest:"))):
        sub_units = [u for u in units if u.scenario_type == "benign" and pred(origin.get(u.intent_id, ""))]
        for c in M.cell_metrics(sub_units, n_boot=o.n_boot, seed=o.seed):
            by_source.append(
                {
                    "contrast_source": src_name,
                    "model": c["model"],
                    "language": c["language"],
                    **{k: v for k, v in c["ORR"].items() if k != "n_unscored_by_status"},
                }
            )
    write_csv(o.out_dir / "orr_by_contrast_source.csv", by_source)
    write_csv(o.out_dir / "linguistic_robustness.csv", M.linguistic_robustness(units))
    write_csv(o.out_dir / "comprehension_strata.csv", M.comprehension_stratified(gens, resolved, allow_fixtures=fixture))
    out["figures"] = figures(cells, h1, h2, o)
    return out


def _safe_families(units, models, o):
    try:
        return _families(units, models, o.n_boot, o.seed)
    except (M.FamilyIncompleteError, ValueError):
        return [], []


def calibration(units, o: Options) -> dict:
    """Nuisance parameters per model and intent type, and the minimum detectable effect (MDE) of the
    primary paired t-test for the 12-test family (docs/v2/calibration_pilot_package.md).

    English units give the rate, the within-unit agreement of the 3 samples and the logit SD of
    unit probabilities. The empirical share variance already contains any within-unit correlation,
    so nothing extra is assumed about it. Reported per model and intent type (H1 harmful, H2 benign):
      mde_pp_conservative       paired-t MDE at 80% power, alpha .05/12, n = 200, assuming no
                                scenario effect shared between forms (worst case for a paired test);
      mde_pp_conservative_upper the same at the bootstrap 90th percentile of the logit SD;
      mde_pp_sigma_form_<s>     simulated MDE when the logit SD splits into a shared scenario part
                                and a form-specific part of SD s (sensitivity; not identified here);
      sd_diff_<form>, n_pairs_<form>  observed SD of per-scenario share differences on the
                                multilingual items (set A; very few scenarios - descriptive only).
    """
    params, power = [], []
    rng = np.random.default_rng(o.seed)
    gaps = (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15, 0.20)
    for model in sorted({u.model for u in units}):
        for stype, outcome in (("harmful", "harmful"), ("benign", "refused")):
            eng = {u.scenario_id: getattr(u, outcome) for u in units if u.model == model and u.scenario_type == stype and u.language == "english" and u.ok}
            shares = list(eng.values())
            if len(shares) < 10:
                continue
            est = estimate_logit_heterogeneity(shares)
            row = {"model": model, "intent_type": stype, "outcome": outcome, **est, "var_share": float(np.var(shares, ddof=1))}
            for lang in M.BASE_LANGS[1:]:
                tgt = {u.scenario_id: getattr(u, outcome) for u in units if u.model == model and u.scenario_type == stype and u.language == lang and u.ok}
                d = [tgt[s] - eng[s] for s in sorted(set(tgt) & set(eng))]
                row[f"n_pairs_{lang}"] = len(d)
                row[f"sd_diff_{lang}"] = float(np.std(d, ddof=1)) if len(d) >= 2 else None
            params.append(row)
            if not 0 < est["rate"] < 0.9:
                continue
            mde = mde_paired_t_conservative(est["rate"], est["sd_logit"])
            row["mde_pp_conservative"] = None if mde is None else 100 * mde
            boot_sd = []
            arr = np.asarray(shares)
            for _ in range(min(500, 10 * o.calibration_sims)):
                b = arr[rng.integers(0, len(arr), len(arr))]
                if 0 < b.mean() < 1:
                    boot_sd.append(estimate_logit_heterogeneity(b)["sd_logit"])
            sd_hi = float(np.quantile(boot_sd, 0.9)) if boot_sd else est["sd_logit"]
            mde_hi = mde_paired_t_conservative(est["rate"], sd_hi)
            row["sd_logit_boot_p90"] = sd_hi
            row["mde_pp_conservative_upper"] = None if mde_hi is None else 100 * mde_hi
            for sigma_f in (0.25, 0.5, 1.0):
                sigma_u = math.sqrt(max(est["sd_logit"] ** 2 - sigma_f**2, 0.0))
                found = None
                for gap in gaps:
                    target = min(est["rate"] + gap, 0.99)
                    res = logit_share_power(200, max(est["rate"], 0.001), target, sigma_u, sigma_f, alphas=(0.05 / 12,), n_sim=o.calibration_sims, seed=o.seed)
                    power.append(
                        {
                            "model": model,
                            "baseline_rate": est["rate"],
                            "sigma_scenario": sigma_u,
                            "sigma_form": sigma_f,
                            "gap_pp": 100 * gap,
                            "power_paired_t": res["paired_t"][0],
                            "power_signed_rank": res["signed_rank"][0],
                            "power_mcnemar_majority": res["mcnemar_majority"][0],
                        }
                    )
                    if found is None and res["paired_t"][0] >= 0.8:
                        found = 100 * gap
                row[f"mde_pp_sigma_form_{sigma_f}"] = found
    write_csv(o.out_dir / "calibration_parameters.csv", params)
    write_csv(o.out_dir / "calibration_power.csv", power)
    return {"calibration_parameters": params}


def figures(cells, h1, h2, o: Options) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = o.out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for fam, rows, label in (("H1", h1, "Harmful-compliance gap (pp, target - English)"), ("H2", h2, "Over-refusal gap (pp, target - English)")):
        if not rows:
            continue
        fig, ax = plt.subplots(figsize=(6.5, 0.35 * len(rows) + 1.2))
        for i, r in enumerate(rows):
            ax.plot([r["ci_low_pp"], r["ci_high_pp"]], [i, i], color="#555555", lw=1.5)
            ax.plot(r["gap_pp"], i, "o", color="#1f4e79" if r["reject_h0_at_0.05"] else "#9aa5b1")
        ax.axvline(0, color="#999999", lw=0.8)
        ax.set_yticks(range(len(rows)), [f"{r['model']} · {r['language']}" for r in rows], fontsize=7)
        ax.set_xlabel(label + "; 95% scenario-bootstrap CI; filled = Holm p < .05", fontsize=7)
        ax.invert_yaxis()
        fig.tight_layout()
        path = fig_dir / f"forest_{fam}.png"
        fig.savefig(path, dpi=200)
        plt.close(fig)
        made.append(str(path.name))
    return made


def reproducibility(manifest, o: Options, ds_path: Path, unit_stats, labels, resolved) -> dict:
    def pkg(n):
        try:
            return metadata.version(n)
        except metadata.PackageNotFoundError:
            return None

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=Path(__file__).resolve().parents[3], timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    return {
        "analysed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "calibration" if o.calibration else "main",
        "overrides_used": o.overrides_used,
        "run_id": manifest["run_id"],
        "model_manifest": {"path": str(o.model_manifest), "sha256": sha256(o.model_manifest)},
        "rater_registry": {"path": str(o.registry), "sha256": sha256(o.registry)} if o.registry and o.registry.exists() else None,
        "run_status": manifest.get("status"),
        "run_manifest_sha256": sha256(o.run_dir / RUN_MANIFEST),
        "generations_sha256": sha256(o.run_dir / "generations.jsonl"),
        "dataset": {**manifest["dataset"], "path_used": str(ds_path)},
        "label_files": {str(p): sha256(p) for p in o.label_files},
        "n_labels": len(labels),
        "n_resolved_generations": len(resolved),
        "label_sources": dict(Counter(lab.label_source.value for lab in labels)),
        "unit_stats": unit_stats,
        "n_boot": o.n_boot,
        "seed": o.seed,
        "analysis_git_commit": commit,
        "python": platform.python_version(),
        "packages": {n: pkg(n) for n in ("numpy", "scipy", "statsmodels", "matplotlib", "pydantic")},
        "inference_environment": manifest.get("environment"),
        "models": [{k: m.get(k) for k in ("key", "model_id", "revision", "chat_template_sha256", "backend")} for m in manifest.get("models", [])],
    }


def summary_md(repro, outputs, agreement, fixture: bool, o: Options) -> str:
    lines = []
    if fixture:
        lines += [f"> **{FIXTURE_BANNER}**", ""]
    if not agreement["labels"]["any_human_labels"]:
        lines += ["> All response labels are AI-judged; no human labels were available for this run (protocol §8, AI-only fallback).", ""]
    if o.overrides_used:
        lines += ["> Analysis overrides: " + "; ".join(o.overrides_used), ""]
    lines += [f"# Analysis summary — {repro['run_id']} ({repro['mode']})", "", f"Units: {repro['unit_stats']}", ""]
    for fam in ("H1", "H2"):
        rows = outputs.get(fam) or []
        if not rows:
            continue
        lines += [
            f"## {fam}",
            "",
            "| Model | Form | n pairs | gap pp [approx. 95% t CI] | bounds pp | p (paired t) | Holm p | signed-rank p (descriptive) | McNemar Holm p |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            lines.append(
                f"| {r['model']} | {r['language']} | {r['n_pairs']} | {r['gap_pp']:.1f} [{r['ci_low_pp']:.1f}, {r['ci_high_pp']:.1f}] | "
                f"[{r['gap_bound_low_pp']:.1f}, {r['gap_bound_high_pp']:.1f}] | {r['p_paired_t']:.3g} | {r['p_holm']:.3g} | "
                f"{r['p_signed_rank']:.3g} | {r['p_mcnemar_holm']:.3g} |"
            )
        lines.append("")
    if outputs.get("calibration_parameters"):
        lines += ["## Calibration parameters", "", "See calibration_parameters.csv and calibration_power.csv.", ""]
    lines += ["Full inputs and versions: reproducibility.json."]
    return "\n".join(lines) + "\n"
