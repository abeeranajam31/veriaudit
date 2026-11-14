"""Replay the 2026-11-13 data-integrity review scenarios against any checkout of this repository.

    python research/integrity/replay_review_scenarios.py <repo_tree> [--out results.json]

Each scenario drives a reported bypass through the real entry points (assembler, worksheet CLI,
rating layer, runner, analysis) using only behaviour, never a fix-specific API, so the same script
runs on the pre-fix tree (commit e4fc1fc) and on the fixed tree. Outcome per scenario:

    BYPASSED  the unsafe outcome happened (expected on the pre-fix tree)
    BLOCKED   the unsafe outcome was refused (expected on the fixed tree)

All data is synthetic and written to a temporary directory; nothing in the repository is changed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

TEXT = {
    "urdu": "یہ ایک مثال کا جملہ ہے جو اردو میں لکھا گیا",
    "roman_urdu": "yeh aik misaal ka jumla hai jo urdu mein likha gaya",
    "code_switched": "yeh aik example sentence hai jo urdu mein likha gaya",
}


def sha(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def jl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Ctx:
    def __init__(self, tree: Path, tmp: Path):
        self.tree, self.tmp = tree, tmp
        sys.path.insert(0, str(tree / "backend"))
        from app.veriaudit_x import authoring as A

        self.A = A

    def world(self, name: str):
        """Synthetic authoring state: 2 advbench scenarios, S1 complete, S2 incomplete."""
        root = self.tmp / name
        cand, auth = root / "data/candidates", root / "data/candidates/authoring"
        asm = load_module(self.tree / "research/dataset/assemble_veriaudit_x.py", f"asm_{name}")
        asm.ROOT, asm.CAND, asm.AUTH, asm.REGISTRY = root, cand, auth, root / "data/annotators.json"
        jl(cand / "selection.jsonl", [
            {"scenario_id": "S1", "category": "fraud", "source": "advbench", "source_id": "1", "harmful_en": "harmful request one", "benign_en": None},
        ])  # fmt: skip
        (cand / "transformation_subset.json").write_text("[]", encoding="utf-8")
        (root / "data/annotators.json").write_text(json.dumps({"raters": [{"id": i, "human": True} for i in ("tr1", "tr2", "rev1", "rev2", "alice", "pi")]}))
        jl(auth / "benign_authored.jsonl", [{"scenario_id": "S1", "benign_en": "benign question one", "author_id": "tr1", "ai_generated": False}])
        jl(
            auth / "benign_validity.jsonl",
            [{"scenario_id": "S1", "reviewer_id": "rev1", "benign": True, "topically_matched": True, "benign_text_sha256": sha("benign question one")}],
        )
        vs = []
        for kind, en in (("H", "harmful request one"), ("B", "benign question one")):
            for form in ("urdu", "roman_urdu", "code_switched"):
                code = {"urdu": "ur", "roman_urdu": "rur", "code_switched": "cs"}[form]
                vs.append({"row_id": f"S1-{kind}-{code}-base", "status": "done", "text": TEXT[form], "text_sha256": sha(TEXT[form]),
                           "english_sha256": sha(en), "author_id": "tr1", "drafting_aid": "none"})  # fmt: skip
        jl(auth / "variants_20261113T000000Z_tr1.jsonl", vs)
        return asm, root

    def rating(self, rid, who, role, text, judgement="equivalent"):
        return {"record_id": rid, "annotator_id": who, "rater_role": role, "text_sha256": sha(text), "judgement": judgement, "harm_preserved": True}

    def assembled(self, root: Path, version: str) -> dict:
        p = root / "data/veriaudit-x" / version / "veriaudit_x.jsonl"
        return {r["record_id"]: r for r in map(json.loads, p.read_text().splitlines())} if p.exists() else {}


# ------------------------------------------------------------------------- scenarios


def s01_adjudicated_variant_validates(c: Ctx):
    """Unsafe outcome: a correctly adjudicated variant makes the dataset fail validation (release blocked)."""
    asm, root = c.world("s01")
    jl(root / "data/candidates/authoring/ratings_1_r.jsonl", [
        c.rating("S1-H-ur-base", "rev1", "independent_reviewer", TEXT["urdu"]),
        c.rating("S1-H-ur-base", "rev2", "independent_reviewer", TEXT["urdu"], "partially_equivalent"),
        c.rating("S1-H-ur-base", "pi", "adjudicator", TEXT["urdu"]),
    ])  # fmt: skip
    rc = asm.main(["--version", "9.0.0-s01"])
    rec = c.assembled(root, "9.0.0-s01").get("S1-H-ur-base", {})
    ok = rc == 0 and rec.get("equivalence", {}).get("status") == "verified" and rec.get("quality", {}).get("human_adjudicated") is True
    return "BLOCKED" if ok else "BYPASSED", f"exit={rc} status={rec.get('equivalence', {}).get('status')}"


def s02_edited_source_keeps_old_translation(c: Ctx):
    """Unsafe outcome: after the English benign contrast is rewritten, translations of the OLD text stay in the dataset."""
    asm, root = c.world("s02")
    jl(
        root / "data/candidates/authoring/benign_authored.jsonl",
        [{"scenario_id": "S1", "benign_en": "a completely different benign question", "author_id": "tr1", "ai_generated": False}],
    )
    asm.main(["--version", "9.0.0-s02"])
    recs = c.assembled(root, "9.0.0-s02")
    kept = "S1-B-ur-base" in recs
    return ("BYPASSED" if kept else "BLOCKED"), f"stale Urdu translation of old source present={kept}"


def s03_reviewer_adjudicates_own_row(c: Ctx):
    """Unsafe outcome: the person who reviewed a variant also adjudicates it, through the worksheet CLI."""
    asm, root = c.world("s03")
    cli = load_module(c.tree / "research/dataset/translation_worksheet.py", "cli_s03")
    cand = root / "data/candidates"
    cli.ROOT, cli.CAND, cli.AUTH, cli.SHEETS, cli.REGISTRY = root, cand, cand / "authoring", cand / "authoring/sheets", root / "data/annotators.json"
    jl(cand / "authoring/ratings_1_alice.jsonl", [
        c.rating("S1-H-ur-base", "alice", "independent_reviewer", TEXT["urdu"], "partially_equivalent"),
        c.rating("S1-H-ur-base", "rev1", "independent_reviewer", TEXT["urdu"], "not_equivalent"),
    ])  # fmt: skip
    A = c.A
    sheet = [{"row_id": "S1-H-ur-base", "english_source": "harmful request one", "text": TEXT["urdu"], "ratings_summary": "",
              "source_check": A.check("S1-H-ur-base", "harmful request one", TEXT["urdu"]), "decision": "accept",
              "harm_preserved": "yes", "rationale": "fine"}]  # fmt: skip
    path = c.tmp / "s03_adj.csv"
    A.write_csv(path, A.ADJUDICATION_COLUMNS, sheet)
    rc = cli.main(["import-adjudication", str(path), "--adjudicator", "alice"])
    written = any("alice" in p.name for p in (cand / "authoring").glob("ratings_*") if p.name != "ratings_1_alice.jsonl")
    if rc == 0 and written:
        return "BYPASSED", "CLI accepted alice adjudicating a row she reviewed"
    # rating layer, in case a ratings file is written by hand
    from app.v2.review import apply_equivalence_ratings
    from app.veriaudit_x.schema import EquivalenceRating, VeriAuditXRecord

    asm.main(["--version", "9.0.0-s03"])
    raw = c.assembled(root, "9.0.0-s03")["S1-H-ur-base"]
    rec = VeriAuditXRecord.model_validate(raw)
    assert any(h.annotator_id == "alice" for h in rec.equivalence.human_ratings), "alice's review must be on the record"
    try:
        apply_equivalence_ratings(rec, [EquivalenceRating(annotator_id="alice", rater_role="adjudicator", judgement="equivalent")])
        return "BYPASSED", "CLI refused, but the rating layer accepted a reviewer-turned-adjudicator"
    except ValueError:
        return "BLOCKED", "refused by CLI and by the rating layer"


def s04_excel_cp1252_destroys_urdu(c: Ctx):
    """Unsafe outcome: a sheet saved by Excel as plain CSV (Urdu -> '???') is imported."""
    A = c.A
    sel = [{"scenario_id": "S1", "category": "fraud", "source": "xstest", "harmful_en": "harmful one", "benign_en": "benign one"}]
    rows = A.plan_rows(sel, set(), {})[0]
    sheet = A.export_worksheet(rows)
    t = next(r for r in sheet if r["row_id"] == "S1-H-ur-base")
    t.update(text=TEXT["urdu"], status="done", drafting_aid="none", self_equivalence="equivalent", self_harm_preserved="yes", naturalness="4")
    good = c.tmp / "s04.csv"
    A.write_csv(good, A.WORKSHEET_COLUMNS, sheet)
    damaged = c.tmp / "s04_cp1252.csv"
    damaged.write_bytes(good.read_text(encoding="utf-8-sig").encode("cp1252", errors="replace"))
    try:
        import inspect

        # version-agnostic: newer code makes `previous` a required keyword (no earlier imports here)
        extra = {"previous": {}} if "previous" in inspect.signature(A.import_worksheet).parameters else {}
        res = A.import_worksheet(damaged, "tr1", rows, **extra)
        got = [v["text"] for v in res.variants if v.get("status") == "done"]
        return "BYPASSED", f"imported text {got[0][:20]!r}"
    except (A.WorkflowError, UnicodeDecodeError) as exc:
        return "BLOCKED", type(exc).__name__


def s05_resume_mixes_datasets(c: Ctx):
    """Unsafe outcome: re-running a run_id after the dataset changed appends generations from a different dataset."""
    import yaml

    from app.v2.inference.runner import run

    d = c.tmp / "s05ds"
    d.mkdir()
    src = c.tree / "dataset/veriaudit-x/fixtures"
    for f in ("sample_valid.jsonl", "manifest.json"):
        shutil.copy(src / f, d / f)
    cfg = yaml.safe_load((c.tree / "configs/experiments/fixture_smoke.yaml").read_text()) | {"dataset": str(d / "sample_valid.jsonl")}
    cp = c.tmp / "s05.yaml"
    cp.write_text(yaml.safe_dump(cfg))
    out = run(cp, ["fake"], out_root=c.tmp / "s05runs")
    n1 = len(out.read_text().splitlines())
    (d / "sample_valid.jsonl").write_text((d / "sample_valid.jsonl").read_text().replace("two-day itinerary", "three-day itinerary"))
    try:
        run(cp, ["fake"], out_root=c.tmp / "s05runs")
    except SystemExit as exc:
        return "BLOCKED", str(exc)[:80]
    n2 = len(out.read_text().splitlines())
    return "BYPASSED", f"resumed on changed dataset ({n1} -> {n2} lines, mixed hashes)"


def s06_revision_drops_mt_disclosure(c: Ctx):
    """Unsafe outcome: a machine-translated variant revised by a second translator loses its drafting-aid disclosure."""
    asm, root = c.world("s06")
    cli = load_module(c.tree / "research/dataset/translation_worksheet.py", "cli_s06")
    cand = root / "data/candidates"
    cli.ROOT, cli.CAND, cli.AUTH, cli.SHEETS, cli.REGISTRY = root, cand, cand / "authoring", cand / "authoring/sheets", root / "data/annotators.json"
    vf = cand / "authoring/variants_20261113T000000Z_tr1.jsonl"
    vs = [json.loads(x) for x in vf.read_text().splitlines()]
    vs[0]["drafting_aid"] = "machine_translation"  # S1-H-ur-base was MT-drafted
    jl(vf, vs)
    A = c.A
    sel = [json.loads(x) for x in (cand / "selection.jsonl").read_text().splitlines()]
    rows = A.plan_rows(sel, set(), {"S1": {"benign_en": "benign question one"}})[0]
    sheet = A.export_worksheet(rows)
    t = next(r for r in sheet if r["row_id"] == "S1-H-ur-base")
    t.update(text=TEXT["urdu"] + " مزید", status="done", drafting_aid="none", self_equivalence="equivalent", self_harm_preserved="yes", naturalness="4")
    path = c.tmp / "s06.csv"
    A.write_csv(path, A.WORKSHEET_COLUMNS, sheet)
    cli.main(["import", str(path), "--translator", "tr2"])
    asm.main(["--version", "9.0.0-s06"])
    rec = c.assembled(root, "9.0.0-s06").get("S1-H-ur-base", {})
    ai = rec.get("quality", {}).get("ai_generated")
    return ("BLOCKED" if ai is True else "BYPASSED"), f"revised variant ai_generated={ai}, method={rec.get('transformation', {}).get('method')}"


def _fixture_run(c: Ctx, name: str, **kw):
    from app.v2.inference.runner import load_generations, run
    from app.v2.records import LabelSource, ResponseLabel, append_jsonl

    out = run(c.tree / "configs/experiments/fixture_smoke.yaml", ["fake"], out_root=c.tmp / name, **kw)
    labs = []
    for g in load_generations(out):
        if g.response_text is None:
            continue
        for j in ("jA", "jB"):
            h = g.scenario_type == "harmful"
            labs.append(ResponseLabel(generation_id=g.generation_id, labeler_id=j, label_source=LabelSource.ai_judge, comprehension="understood",
                                      behaviour="full_refusal" if h else "full_compliance", harmful_content=False if h else None,
                                      task_success=None if h else "success", is_test_fixture=True))  # fmt: skip
    lp = c.tmp / f"{name}_labels.jsonl"
    append_jsonl(lp, labs)
    return out.parent, lp


def _options(c: Ctx, run_dir, labels, out, **flags):
    from app.v2.analysis import Options

    accepted = inspect.signature(Options).parameters
    kw = {k: v for k, v in flags.items() if k in accepted}
    return Options(run_dir, [labels], out, c.tree / "configs/models.yaml", n_boot=50, **kw)


def _analyse(c: Ctx, opts):
    from app.v2.analysis import AnalysisRefused, analyse

    try:
        analyse(opts)
        return None
    except AnalysisRefused as exc:
        return str(exc)
    except Exception as exc:  # noqa: BLE001
        return f"CRASH {type(exc).__name__}: {exc}"


def s07_unfinished_run_without_hash(c: Ctx):
    """Unsafe outcome: a run whose manifest has no generations hash (never finished) is analysed."""
    run_dir, labels = _fixture_run(c, "s07")
    m = json.loads((run_dir / "run_manifest.json").read_text())
    m.pop("generations_sha256", None)
    (run_dir / "run_manifest.json").write_text(json.dumps(m))
    err = _analyse(c, _options(c, run_dir, labels, c.tmp / "s07a", allow_fixtures=True, allow_incomplete=True))
    return ("BLOCKED" if err else "BYPASSED"), err or "analysed"


def s08_limited_run_counts_as_complete(c: Ctx):
    """Unsafe outcome: a run made with --limit (a subset of the dataset) is analysed as complete, without any override."""
    run_dir, labels = _fixture_run(c, "s08", limit=8)
    err = _analyse(c, _options(c, run_dir, labels, c.tmp / "s08a", allow_fixtures=True))
    return ("BLOCKED" if err else "BYPASSED"), err or "analysed a partial run as complete"


def s09_family_size_not_enforced(c: Ctx):
    """Unsafe outcome: a model manifest with fewer confirmatory models silently shrinks the Holm family."""
    import yaml

    from app.v2.analysis import AnalysisRefused, confirmatory_models

    p = c.tmp / "s09_models.yaml"
    p.write_text(yaml.safe_dump({"models": [{"key": "x", "backend": "vllm", "model_id": "o/x", "confirmatory": True}]}))
    try:
        got = confirmatory_models(p, {"x"}, False)
        return "BYPASSED", f"family built from {got}"
    except AnalysisRefused as exc:
        return "BLOCKED", str(exc)


def s10_self_declared_panel_label(c: Ctx):
    """Unsafe outcome: one judge's label written with label_source=ai_panel resolves on its own."""
    from app.v2.records import LabelSource, ResponseLabel, resolve_labels

    lab = ResponseLabel(generation_id="g", labeler_id="judgeX", label_source=LabelSource.ai_panel, comprehension="understood",
                        behaviour="full_refusal", harmful_content=False)  # fmt: skip
    return ("BYPASSED" if resolve_labels([lab]) else "BLOCKED"), "single self-declared panel label"


CONF = ("qwen3_8b", "aya_expanse_8b", "qwen3_5_9b", "gemma4_e4b")


def _registry(c: Ctx) -> Path:
    """Registry with the fixture dataset's (synthetic) raters, so only the scenario under test can trip a gate."""
    p = c.tmp / "registry.json"
    p.write_text(json.dumps({"raters": [{"id": i, "human": True} for i in ("fixture-ann-A", "fixture-ann-B", "fixture-adj-C", "pi")]}))
    return p


def _real_looking_run(c: Ctx, name: str, ghost=False):
    """A fake-backend run re-labelled as a real 4-model, non-fixture run (as a careless or malicious edit would)."""
    run_dir, labels = _fixture_run(c, name)
    gen = run_dir / "generations.jsonl"
    base = [json.loads(x) for x in gen.read_text().splitlines()]
    base_labs = [json.loads(x) for x in Path(labels).read_text().splitlines()]
    rows, labs = [], []
    for key in CONF:
        idmap = {}
        for r in base:
            nid = hashlib.sha256(f"{key}|{r['generation_id']}".encode()).hexdigest()[:24]
            idmap[r["generation_id"]] = nid
            rows.append(dict(r, generation_id=nid, model_key=key, model_id=f"org/{key}", is_test_fixture=False))
        labs += [dict(lab, generation_id=idmap[lab["generation_id"]], is_test_fixture=False) for lab in base_labs]
    if ghost:  # a generation whose record is not in the dataset, on its own scenario/intent
        rows.append(dict(rows[0], generation_id="ghost0000000000000000000", record_id="GHOST-H-en-01", scenario_id="GHOST", intent_id="GHOST-H"))
        labs += [dict(lab, generation_id="ghost0000000000000000000") for lab in labs[:2]]
    gen.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    Path(labels).write_text("".join(json.dumps(x) + "\n" for x in labs))
    m = json.loads((run_dir / "run_manifest.json").read_text())
    m.update(is_fixture_run=False, generations_sha256=sha256_file(gen))
    (run_dir / "run_manifest.json").write_text(json.dumps(m))
    return run_dir, labels


def _verdict(err: str | None, expected: str, bypass_msg: str):
    """BLOCKED only when refused for the scenario's own reason; a crash or an unrelated refusal is reported as such."""
    if err is None:
        return "BYPASSED", bypass_msg
    if err.startswith("CRASH"):
        return "CRASHED", err
    return ("BLOCKED" if expected in err else "OTHER_REFUSAL"), err


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def s11_non_release_dataset_analysed(c: Ctx):
    """Unsafe outcome: a main-study analysis runs on a dataset that is not a frozen release (here: the test fixture)."""
    run_dir, labels = _real_looking_run(c, "s11")
    err = _analyse(c, _options(c, run_dir, labels, c.tmp / "s11a", registry=_registry(c)))
    return _verdict(err, "not a frozen release", "analysed a non-release dataset as the main study")


def s12_unregistered_human_labels(c: Ctx):
    """Unsafe outcome: labels claiming to be human, from an ID not in the rater registry, override AI labels."""
    run_dir, labels = _real_looking_run(c, "s12")
    g0 = json.loads((run_dir / "generations.jsonl").read_text().splitlines()[0])["generation_id"]
    fake_human = {"schema_version": "label-1.0", "generation_id": g0, "labeler_id": "gpt-4o", "label_source": "human",
                  "comprehension": "understood", "behaviour": "full_compliance", "harmful_content": True}  # fmt: skip
    with Path(labels).open("a") as f:
        f.write(json.dumps(fake_human) + "\n")
    err = _analyse(c, _options(c, run_dir, labels, c.tmp / "s12a", allow_candidate_dataset=True, registry=_registry(c)))
    return _verdict(err, "not registered", "analysed with an unregistered 'human' label overriding the AI labels")


def s13_orphan_generations(c: Ctx):
    """Unsafe outcome: generations for records that are not in the dataset enter the analysis."""
    run_dir, labels = _real_looking_run(c, "s13", ghost=True)
    err = _analyse(c, _options(c, run_dir, labels, c.tmp / "s13a", allow_candidate_dataset=True, registry=_registry(c)))
    return _verdict(err, "not in the dataset", "analysed generations for a record not in the dataset")


SCENARIOS = [
    s01_adjudicated_variant_validates, s02_edited_source_keeps_old_translation, s03_reviewer_adjudicates_own_row,
    s04_excel_cp1252_destroys_urdu, s05_resume_mixes_datasets, s06_revision_drops_mt_disclosure,
    s07_unfinished_run_without_hash, s08_limited_run_counts_as_complete, s09_family_size_not_enforced,
    s10_self_declared_panel_label, s11_non_release_dataset_analysed, s12_unregistered_human_labels, s13_orphan_generations,
]  # fmt: skip


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tree", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    tmp = Path(tempfile.mkdtemp(prefix="replay_"))
    c = Ctx(args.tree.resolve(), tmp)
    results = []
    for s in SCENARIOS:
        try:
            outcome, detail = s(c)
        except Exception as exc:  # noqa: BLE001
            outcome, detail = "ERROR", f"{type(exc).__name__}: {exc}"[:200] + " | " + traceback.format_exc().splitlines()[-3][:120]
        results.append({"scenario": s.__name__, "unsafe_outcome": s.__doc__.strip(), "outcome": outcome, "detail": str(detail)[:240]})
        print(f"{outcome:9} {s.__name__}: {str(detail)[:140]}", flush=True)
    if args.out:
        args.out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
