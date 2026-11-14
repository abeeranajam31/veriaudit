"""End-to-end test of research/dataset/assemble_veriaudit_x.py on a synthetic authoring state."""

import importlib.util
import json
from pathlib import Path

import pytest

from app.veriaudit_x import authoring as A
from app.veriaudit_x.validation import ValidationConfig, validate_file

REPO = Path(__file__).resolve().parents[2]


def load_assembler():
    spec = importlib.util.spec_from_file_location("assemble", REPO / "research" / "dataset" / "assemble_veriaudit_x.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def jl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


TEXT = {
    "urdu": "یہ ایک مثال کا جملہ ہے جو اردو میں لکھا گیا",
    "roman_urdu": "yeh aik misaal ka jumla hai jo urdu mein likha gaya",
    "code_switched": "yeh aik example sentence hai jo urdu mein likha gaya",
}


@pytest.fixture
def world(tmp_path, monkeypatch):
    asm = load_assembler()
    cand = tmp_path / "data" / "candidates"
    auth = cand / "authoring"
    monkeypatch.setattr(asm, "ROOT", tmp_path)
    monkeypatch.setattr(asm, "CAND", cand)
    monkeypatch.setattr(asm, "AUTH", auth)
    monkeypatch.setattr(asm, "REGISTRY", tmp_path / "data" / "annotators.json")
    selection = [
        {"scenario_id": "S1", "category": "fraud", "source": "advbench", "source_id": "1", "harmful_en": "harmful request one", "benign_en": None},
        {"scenario_id": "S2", "category": "fraud", "source": "advbench", "source_id": "2", "harmful_en": "harmful request two", "benign_en": None},
    ]
    jl(cand / "selection.jsonl", selection)
    (cand / "transformation_subset.json").write_text("[]", encoding="utf-8")
    (tmp_path / "data" / "annotators.json").write_text(
        json.dumps({"raters": [{"id": i, "human": True} for i in ("tr1", "rev1", "rev2", "pi")]}), encoding="utf-8"
    )
    jl(
        auth / "benign_authored.jsonl",
        [{"scenario_id": s, "benign_en": f"benign question {s}", "author_id": "tr1", "ai_generated": False} for s in ("S1", "S2")],
    )
    jl(
        auth / "benign_validity.jsonl",
        [{"scenario_id": "S1", "reviewer_id": "rev1", "benign": True, "topically_matched": True, "benign_text_sha256": A.sha("benign question S1")}],
    )
    variants = []
    for kind in "HB":
        for form in A.FORMS:
            t = TEXT[form]
            variants.append({"row_id": A.row_id("S1", kind, form, "base"), "status": "done", "text": t, "text_sha256": A.sha(t), "author_id": "tr1"})
    variants[0]["drafting_aid"] = "machine_translation"  # S1-H-ur-base was MT-drafted, then edited
    # S2 is incomplete: only its harmful Urdu row exists
    variants.append({"row_id": "S2-H-ur-base", "status": "done", "text": TEXT["urdu"], "text_sha256": A.sha(TEXT["urdu"]), "author_id": "tr1"})
    jl(auth / "variants_20261113T000000Z_tr1.jsonl", variants)
    ur = A.sha(TEXT["urdu"])
    jl(
        auth / "ratings_20261113T010000Z_rev.jsonl",
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
                "judgement": "equivalent",
                "harm_preserved": True,
            },
            # stale: rated an older text
            {
                "record_id": "S1-B-ur-base",
                "annotator_id": "rev1",
                "rater_role": "independent_reviewer",
                "text_sha256": "0" * 64,
                "judgement": "equivalent",
                "harm_preserved": True,
            },
        ],
    )
    return asm, tmp_path


def test_candidate_build(world):
    asm, root = world
    assert asm.main(["--version", "9.9.9-test"]) == 0
    out = root / "data" / "veriaudit-x" / "9.9.9-test"
    recs = {r.record_id: r for r in validate_file(out / "veriaudit_x.jsonl").records}
    assert {r.scenario_id for r in recs.values()} == {"S1"}  # S2 excluded as incomplete
    ur = recs["S1-H-ur-base"]
    assert ur.equivalence.status.value == "verified" and ur.quality.human_reviewed
    assert {h.annotator_id for h in ur.equivalence.human_ratings} == {"rev1", "rev2"}
    assert ur.transformation.method.value == "machine_post_edited" and ur.quality.ai_generated is True
    assert recs["S1-H-rur-base"].transformation.method.value == "human" and recs["S1-H-rur-base"].quality.ai_generated is False
    assert recs["S1-B-ur-base"].equivalence.human_ratings == []  # stale rating ignored
    b = recs["S1-B-en-base"]
    assert b.transformation.author_id == "tr1" and b.provenance.origin.startswith("human-authored benign contrast")
    assert [v.reviewer_id for v in b.quality.benign_validity] == ["rev1"]
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["is_release"] is False and manifest["n_scenarios"] == 1 and len(manifest["data_sha256"]) == 64
    assert "S2" in (out / "qc_report.md").read_text() or "excluded as incomplete: 1" in (out / "qc_report.md").read_text()
    assert (out / "splits" / "split_manifest.json").exists()


def test_release_refuses_incomplete_and_writes_nothing(world):
    asm, root = world
    with pytest.raises(SystemExit, match="incomplete"):
        asm.main(["--version", "2.0.0", "--release"])
    assert not (root / "data" / "veriaudit-x" / "2.0.0").exists()
    with pytest.raises(SystemExit, match="plain version"):
        asm.main(["--version", "2.0.0-rc1", "--release"])


def test_release_validates_when_complete(world):
    asm, root = world
    sel = [json.loads(x) for x in (root / "data/candidates/selection.jsonl").read_text().splitlines()]
    jl(root / "data/candidates/selection.jsonl", sel[:1])  # drop the incomplete scenario
    assert asm.main(["--version", "2.0.0", "--release"]) == 0
    report = validate_file(root / "data/veriaudit-x/2.0.0/veriaudit_x.jsonl", ValidationConfig(release=True))
    assert report.ok, report.summary()
    with pytest.raises(SystemExit, match="immutable"):
        asm.main(["--version", "2.0.0", "--release"])


def test_unregistered_rater_is_refused(world):
    asm, root = world
    jl(
        root / "data/candidates/authoring/ratings_20261113T020000Z_x.jsonl",
        [{"record_id": "S1-H-rur-base", "annotator_id": "some-llm", "rater_role": "independent_reviewer", "text_sha256": "x", "judgement": "equivalent"}],
    )
    with pytest.raises(SystemExit, match="unregistered"):
        asm.main(["--version", "9.9.9-test"])
