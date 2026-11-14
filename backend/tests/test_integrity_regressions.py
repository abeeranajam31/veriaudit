"""Regression tests for the independent data-integrity review (2026-11-13). Each test reproduces a
reported bypass and checks it is now refused."""

import json
from pathlib import Path

import pytest
import yaml
from test_assemble_veriaudit_x import TEXT, jl, world  # noqa: F401  (pytest fixture)
from test_v2_analysis import MODELS, SMOKE, make_labels
from veriaudit_x_helpers import load_fixture

from app.v2.analysis import AnalysisRefused, Options, analyse, confirmatory_models
from app.v2.inference.runner import ROOT, RunConfigError, load_generations, run
from app.v2.records import LabelSource, ResponseLabel, append_jsonl, resolve_labels
from app.v2.review import apply_equivalence_ratings
from app.veriaudit_x import authoring as A
from app.veriaudit_x.schema import EquivalenceRating
from app.veriaudit_x.validation import ValidationConfig, validate_objects

SEL = [{"scenario_id": "S1", "category": "fraud", "source": "xstest", "harmful_en": "harmful one", "benign_en": "benign one"}]
REG = {"raters": [{"id": i, "human": True} for i in ("tr1", "tr2", "alice", "bob", "dave", "adj")]}


def write(path, rows, cols):
    A.write_csv(path, cols, rows)
    return path


def rows():
    return A.plan_rows(SEL, set(), {})[0]


# 1 ------------------------------------------------------------------ adjudicated records validate


def test_adjudicated_variant_passes_validation(world):  # noqa: F811
    asm, root = world
    ur = A.sha(TEXT["urdu"])
    jl(
        root / "data/candidates/authoring/ratings_20261113T010000Z_rev.jsonl",
        [
            {
                "record_id": "S1-H-ur-base",
                "annotator_id": "rev1",
                "rater_role": "independent_reviewer",
                "text_sha256": ur,
                "judgement": "equivalent",
                "harm_preserved": True,
            },
            {
                "record_id": "S1-H-ur-base",
                "annotator_id": "rev2",
                "rater_role": "independent_reviewer",
                "text_sha256": ur,
                "judgement": "partially_equivalent",
                "harm_preserved": True,
            },
            {
                "record_id": "S1-H-ur-base",
                "annotator_id": "pi",
                "rater_role": "adjudicator",
                "text_sha256": ur,
                "judgement": "equivalent",
                "harm_preserved": True,
            },
        ],
    )
    assert asm.main(["--version", "9.9.9-adj"]) == 0  # 0 = validation ok
    recs = [json.loads(x) for x in (root / "data/veriaudit-x/9.9.9-adj/veriaudit_x.jsonl").read_text().splitlines()]
    r = next(x for x in recs if x["record_id"] == "S1-H-ur-base")
    assert r["equivalence"]["status"] == "verified" and r["quality"]["human_adjudicated"] is True


# 2 ------------------------------------------------------------------ edited English source


def test_edited_english_source_makes_variants_and_ratings_stale(world):  # noqa: F811
    asm, root = world
    jl(root / "data/candidates/authoring/benign_authored.jsonl", [
        {"scenario_id": "S1", "benign_en": "a different benign question", "author_id": "tr1", "ai_generated": False},
        {"scenario_id": "S2", "benign_en": "benign question S2", "author_id": "tr1", "ai_generated": False},
    ])  # fmt: skip
    # the stored variants were written for "benign question S1"; give them the old english hash
    vfile = root / "data/candidates/authoring/variants_20261113T000000Z_tr1.jsonl"
    vs = [json.loads(x) for x in vfile.read_text().splitlines()]
    for v in vs:
        if v["row_id"].startswith("S1-B"):
            v["english_sha256"] = A.sha("benign question S1")
    jl(vfile, vs)
    rows_, _ = A.plan_rows([json.loads(x) for x in (root / "data/candidates/selection.jsonl").read_text().splitlines()], set(), {
        "S1": {"benign_en": "a different benign question"}
    })  # fmt: skip
    cur = A.current_variants(rows_, A.load_variants([vfile]))
    assert "S1-B-ur-base" not in cur and "S1-H-ur-base" in cur
    asm.main(["--version", "9.9.9-src"])
    out = root / "data/veriaudit-x/9.9.9-src"
    assert not out.exists() or "S1-B-ur-base" not in (out / "veriaudit_x.jsonl").read_text()


# 3 ------------------------------------------------------------------ reviewer cannot adjudicate own row


def test_reviewer_cannot_adjudicate_own_row(tmp_path):
    rs = rows()
    variants = {"S1-H-ur-base": {"row_id": "S1-H-ur-base", "text": "اردو متن", "text_sha256": A.sha("اردو متن"), "author_id": "tr1"}}
    prior = [
        {
            "record_id": "S1-H-ur-base",
            "annotator_id": "alice",
            "rater_role": "independent_reviewer",
            "text_sha256": A.sha("اردو متن"),
            "judgement": "equivalent",
        }
    ]
    sheet = [{
        "row_id": "S1-H-ur-base", "english_source": "harmful one", "text": "اردو متن", "ratings_summary": "",
        "source_check": A.check("S1-H-ur-base", "harmful one", "اردو متن"), "decision": "accept", "harm_preserved": "yes", "rationale": "ok",
    }]  # fmt: skip
    path = write(tmp_path / "adj.csv", sheet, A.ADJUDICATION_COLUMNS)
    with pytest.raises(A.WorkflowError, match="third person"):
        A.import_adjudication(path, "alice", rs, variants, REG, prior)
    assert A.import_adjudication(path, "adj", rs, variants, REG, prior)  # a third person is fine
    # and the rating layer refuses a role switch even if a file bypasses the import
    rec = validate_objects(load_fixture()).records
    target = next(r for r in rec if r.record_id == "VX-S0001-H-ur-01")  # rated by fixture-ann-A/B
    with pytest.raises(ValueError, match="cannot also act"):
        apply_equivalence_ratings(target, [EquivalenceRating(annotator_id="fixture-ann-A", rater_role="adjudicator", judgement="equivalent")])


# 4 ------------------------------------------------------------------ encoding damage


def test_non_utf8_and_question_mark_damage_refused(tmp_path):
    rs = rows()
    sheet = A.export_worksheet(rs)
    target = next(r for r in sheet if r["row_id"] == "S1-H-ur-base")
    target.update(text="اردو متن", status="done", drafting_aid="none", self_equivalence="equivalent", self_harm_preserved="yes", naturalness="4")
    good = write(tmp_path / "ok.csv", sheet, A.WORKSHEET_COLUMNS)
    assert A.import_worksheet(good, "tr1", rs, previous={}).variants
    # Excel "CSV" in cp1252: Urdu letters become '?'
    damaged = good.read_text(encoding="utf-8-sig").encode("cp1252", errors="replace").replace(b"\n", b"\r\n")
    (tmp_path / "cp.csv").write_bytes(damaged)
    with pytest.raises(A.WorkflowError, match="corrupted|not UTF-8"):
        A.import_worksheet(tmp_path / "cp.csv", "tr1", rs, previous={})
    (tmp_path / "bad.csv").write_bytes(b"\xff\xfe" + "x".encode("utf-16-le"))
    with pytest.raises(A.WorkflowError, match="not UTF-8"):
        A.import_worksheet(tmp_path / "bad.csv", "tr1", rs, previous={})
    target.update(text="Aik roman jumla")  # Latin text in the Urdu-script row
    with pytest.raises(A.WorkflowError, match="no Urdu letters"):
        A.import_worksheet(write(tmp_path / "latin.csv", sheet, A.WORKSHEET_COLUMNS), "tr1", rs, previous={})


# 6 ------------------------------------------------------------------ drafting disclosure survives revision


def test_revision_inherits_drafting_aid(tmp_path):
    rs = rows()
    sheet = A.export_worksheet(rs)
    t = next(r for r in sheet if r["row_id"] == "S1-H-ur-base")
    t.update(text="اردو متن ایک", status="done", drafting_aid="none", self_equivalence="equivalent", self_harm_preserved="yes", naturalness="4")
    prev = {"S1-H-ur-base": {"row_id": "S1-H-ur-base", "text": "اردو متن", "author_id": "tr1", "drafting_aid": "machine_translation"}}
    v = A.import_worksheet(write(tmp_path / "w.csv", sheet, A.WORKSHEET_COLUMNS), "tr2", rs, previous=prev).variants[0]
    assert v["drafting_aid"] == "machine_translation" and v["drafting_aid_inherited_from"] == "tr1"


# 10/11 ---------------------------------------------------------------- labels and raters


def test_self_declared_panel_label_does_not_resolve_alone():
    lab = ResponseLabel(
        generation_id="g", labeler_id="judgeX", label_source=LabelSource.ai_panel, comprehension="understood", behaviour="full_refusal", harmful_content=False
    )
    assert resolve_labels([lab]) == {}
    real = lab.model_copy(update={"labeler_id": "panel:a+b"})
    assert resolve_labels([real])["g"].label_source == LabelSource.ai_panel


def test_validator_rejects_unregistered_raters():
    recs = load_fixture()
    cfg = ValidationConfig(registered_raters=frozenset({"fixture-ann-A"}))
    assert validate_objects(recs, cfg).codes()["unregistered_rater"] >= 1
    everyone = frozenset({"fixture-ann-A", "fixture-ann-B", "fixture-adj-C"})
    assert "unregistered_rater" not in validate_objects(recs, ValidationConfig(registered_raters=everyone)).codes()


# 5/7/8/9 -------------------------------------------------------------- runner and analysis gates


def test_resume_with_changed_dataset_is_refused(tmp_path):
    src = ROOT / "dataset/veriaudit-x/fixtures"
    d = tmp_path / "ds"
    d.mkdir()
    (d / "sample_valid.jsonl").write_bytes((src / "sample_valid.jsonl").read_bytes())
    (d / "manifest.json").write_bytes((src / "manifest.json").read_bytes())
    cfg = yaml.safe_load(SMOKE.read_text()) | {"dataset": str(d / "sample_valid.jsonl")}
    cp = tmp_path / "cfg.yaml"
    cp.write_text(yaml.safe_dump(cfg))
    run(cp, ["fake"], out_root=tmp_path)
    data = (d / "sample_valid.jsonl").read_text().replace("Plan a two-day itinerary", "Plan a three-day itinerary")
    (d / "sample_valid.jsonl").write_text(data)
    with pytest.raises(RunConfigError, match="different dataset or config"):
        run(cp, ["fake"], out_root=tmp_path)


def _fixture(tmp_path, **run_kw):
    out = run(SMOKE, ["fake"], out_root=tmp_path, **run_kw)
    return out.parent, make_labels(load_generations(out), tmp_path / "labels.jsonl")


def test_missing_generations_hash_is_an_integrity_failure(tmp_path):
    run_dir, labels = _fixture(tmp_path)
    m = json.loads((run_dir / "run_manifest.json").read_text())
    m.pop("generations_sha256")
    (run_dir / "run_manifest.json").write_text(json.dumps(m))
    with pytest.raises(AnalysisRefused, match="no generations hash"):
        analyse(Options(run_dir, [labels], tmp_path / "a", MODELS, allow_fixtures=True, allow_incomplete=True, n_boot=100))


def test_limited_run_counts_as_incomplete(tmp_path):
    run_dir, labels = _fixture(tmp_path, limit=8)  # first scenario only: both intents, 4 forms
    with pytest.raises(AnalysisRefused, match="--limit"):
        analyse(Options(run_dir, [labels], tmp_path / "a", MODELS, allow_fixtures=True, n_boot=100))
    analyse(Options(run_dir, [labels], tmp_path / "a", MODELS, allow_fixtures=True, allow_incomplete=True, n_boot=100))
    summary = (tmp_path / "a" / "summary.md").read_text()
    assert "--limit 8" in summary and "run covered 8 records but the dataset has 28 eligible" in summary


def test_family_that_cannot_form_is_refused_not_emptied(tmp_path):
    run_dir, labels = _fixture(tmp_path, limit=4)  # harmful prompts only -> no H2 family
    with pytest.raises(AnalysisRefused, match="confirmatory family incomplete"):
        analyse(Options(run_dir, [labels], tmp_path / "a", MODELS, allow_fixtures=True, allow_incomplete=True, n_boot=100))


def test_confirmatory_family_must_have_four_models(tmp_path):
    assert len(confirmatory_models(MODELS, set(), fixture=False)) == 4
    bad = tmp_path / "models.yaml"
    bad.write_text(yaml.safe_dump({"models": [{"key": "x", "backend": "vllm", "model_id": "o/x", "confirmatory": True}]}))
    with pytest.raises(AnalysisRefused, match="confirmatory"):
        confirmatory_models(bad, {"x"}, fixture=False)


def test_non_release_dataset_and_unregistered_human_labels_refused(tmp_path):
    run_dir, labels = _fixture(tmp_path)
    m = json.loads((run_dir / "run_manifest.json").read_text())
    m["is_fixture_run"] = False  # pretend a real run on a non-release dataset
    (run_dir / "run_manifest.json").write_text(json.dumps(m))
    o = Options(run_dir, [labels], tmp_path / "a", MODELS, registry=ROOT / "data/annotators.json", n_boot=100)
    with pytest.raises(AnalysisRefused, match="not a frozen release"):
        analyse(o)
    human = ResponseLabel(
        generation_id="x", labeler_id="gpt-4o", label_source=LabelSource.human, comprehension="understood", behaviour="full_refusal", harmful_content=False
    )
    append_jsonl(Path(labels), [human])
    o2 = Options(run_dir, [labels], tmp_path / "a", MODELS, registry=ROOT / "data/annotators.json", allow_candidate_dataset=True, n_boot=100)
    with pytest.raises(AnalysisRefused, match="not registered"):
        analyse(o2)


# hardening after the replay (2026-11-13): safety inputs are mandatory, not optional


def test_safety_parameters_are_mandatory():
    import inspect

    assert inspect.signature(A.import_worksheet).parameters["previous"].default is inspect.Parameter.empty
    assert inspect.signature(A.import_adjudication).parameters["ratings"].default is inspect.Parameter.empty


def test_real_run_without_registry_is_refused(tmp_path):
    run_dir, labels = _fixture(tmp_path)
    m = json.loads((run_dir / "run_manifest.json").read_text())
    m["is_fixture_run"] = False
    (run_dir / "run_manifest.json").write_text(json.dumps(m))
    with pytest.raises(AnalysisRefused, match="rater registry"):
        analyse(Options(run_dir, [labels], tmp_path / "a", MODELS, allow_candidate_dataset=True, registry=None, n_boot=100))


def test_role_conflict_in_hand_written_ratings_is_a_clean_refusal(world):  # noqa: F811
    asm, root = world
    ur = A.sha(TEXT["urdu"])
    jl(root / "data/candidates/authoring/ratings_20261113T030000Z_x.jsonl", [
        {"record_id": "S1-H-ur-base", "annotator_id": "rev1", "rater_role": "independent_reviewer", "text_sha256": ur, "judgement": "partially_equivalent"},
        {"record_id": "S1-H-ur-base", "annotator_id": "rev1", "rater_role": "adjudicator", "text_sha256": ur, "judgement": "equivalent"},
    ])  # fmt: skip
    with pytest.raises(SystemExit, match="refused"):
        asm.main(["--version", "9.9.9-conflict"])


def test_english_check_ignores_english_homographs():
    from app.v2.quality.checks import check_variant

    def ok(t):
        return next(q for q in check_variant("english", t, t) if q.name == "no_roman_urdu_in_english").passed

    assert ok("How do I tell if the message is from my bank or a scam?")
    assert not ok("Mujhe batao kaise yeh message fake hai aur kya karna chahiye")


def test_chat_template_hash_accepts_dict_templates():
    """Aya Expanse's tokenizer stores named templates in a dict; recording it crashed the first Kaggle
    run after all 480 generations had been written, leaving the manifest unfinished."""
    from app.v2.inference.backends import sha256_text

    a = sha256_text({"default": "{{ x }}", "tool_use": "{{ y }}"})
    assert a == sha256_text({"tool_use": "{{ y }}", "default": "{{ x }}"}) and len(a) == 64
    assert sha256_text("{{ x }}") != a and sha256_text(None) is None
