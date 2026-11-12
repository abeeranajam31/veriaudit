"""Human authoring workflow (app.veriaudit_x.authoring). Synthetic placeholder text only."""

import csv

import pytest

from app.veriaudit_x import authoring as A

SEL = [
    {"scenario_id": "S1", "category": "fraud", "source": "advbench", "harmful_en": "harmful request one", "benign_en": None},
    {"scenario_id": "S2", "category": "violence", "source": "xstest", "harmful_en": "harmful request two", "benign_en": "benign question two"},
    {
        "scenario_id": "S3",
        "category": "cybercrime",
        "source": "veriaudit-v0.1",
        "harmful_en": "harmful request three",
        "benign_en": None,
        "v1_variants": {"urdu": "اردو متن تین", "roman_urdu": "roman matn teen", "code_switched": "code switched text teen"},
    },
]
REGISTRY = {
    "raters": [
        {"id": "tr1", "human": True},
        {"id": "rev1", "human": True},
        {"id": "rev2", "human": True},
        {"id": "adj", "human": True},
        {"id": "pi", "human": True},
    ]
}


def rows_of(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write(path, rows, cols):
    A.write_csv(path, cols, rows)
    return path


def test_plan_links_rows_and_waits_for_benign():
    rows, waiting = A.plan_rows(SEL, {"S2"}, {})
    ids = {r.row_id for r in rows}
    assert waiting == ["S1", "S3"]  # benign English missing
    assert "S2-B-ur-base" in ids and "S1-B-ur-base" not in ids
    r = next(x for x in rows if x.row_id == "S2-H-rur-base")
    assert r.derive_from == "S2-H-ur-base" and r.phase == 1
    t6 = next(x for x in rows if x.row_id == "S2-H-cs-t6")
    assert t6.derive_from == "S2-H-ur-base" and t6.target_script == "mixed" and t6.phase == 2
    assert not any(x.scenario_id == "S1" and x.phase == 2 for x in rows)  # S1 not in the subset
    locked = [x for x in rows if x.locked_text]
    assert {x.row_id for x in locked} == {"S3-H-ur-base", "S3-H-rur-base", "S3-H-cs-base"}


def test_benign_stage_author_then_independent_review(tmp_path):
    sheet = A.export_benign_authoring(SEL, {})
    assert [r["scenario_id"] for r in sheet] == ["S1", "S3"]
    sheet[0]["benign_english"] = "benign question one"
    path = write(tmp_path / "b.csv", sheet, A.BENIGN_COLUMNS)
    authored = {r["scenario_id"]: r for r in A.import_benign_authoring(path, "tr1", SEL)}
    assert authored["S1"]["benign_en"] == "benign question one" and authored["S1"]["ai_generated"] is False
    assert "S3" not in authored  # left blank -> not imported
    assert A.export_benign_review(SEL, authored, "tr1") == []  # author never reviews own contrast
    rsheet = A.export_benign_review(SEL, authored, "rev1")
    rsheet[0].update(benign="yes", topically_matched="yes")
    rp = write(tmp_path / "r.csv", rsheet, A.BENIGN_REVIEW_COLUMNS)
    out = A.import_benign_review(rp, "rev1", SEL, authored)
    assert out[0]["benign"] is True and out[0]["benign_text_sha256"] == A.sha("benign question one")
    with pytest.raises(A.WorkflowError, match="cannot review"):
        A.import_benign_review(rp, "tr1", SEL, authored)
    # contrast revised after review -> the old review sheet is stale
    authored["S1"] = dict(authored["S1"], benign_en="revised benign question one")
    with pytest.raises(A.WorkflowError, match="re-export"):
        A.import_benign_review(rp, "rev1", SEL, authored)


def test_benign_import_rejects_edited_source(tmp_path):
    sheet = A.export_benign_authoring(SEL, {})
    sheet[0].update(benign_english="x", harmful_english="edited")
    with pytest.raises(A.WorkflowError, match="source_check"):
        A.import_benign_authoring(write(tmp_path / "b.csv", sheet, A.BENIGN_COLUMNS), "tr1", SEL)


def _filled_worksheet(tmp_path, rows):
    sheet = A.export_worksheet(rows)
    by_id = {r["row_id"]: r for r in sheet}
    by_id["S2-H-ur-base"].update(
        text="اردو ترجمہ دو", status="done", drafting_aid="none", self_equivalence="equivalent", self_harm_preserved="yes", naturalness="4"
    )
    by_id["S2-H-rur-base"].update(
        text="urdu tarjuma do", status="done", drafting_aid="machine_translation", self_equivalence="equivalent", self_harm_preserved="yes", naturalness="5"
    )
    by_id["S2-H-cs-base"].update(status="cannot_translate", comments="wordplay does not survive")
    return write(tmp_path / "w.csv", sheet, A.WORKSHEET_COLUMNS)


def test_worksheet_import_validates_and_links(tmp_path):
    rows, _ = A.plan_rows(SEL, set(), {})
    res = A.import_worksheet(_filled_worksheet(tmp_path, rows), "tr1", rows)
    done = {v["row_id"]: v for v in res.variants}
    assert done["S2-H-ur-base"]["status"] == "done" and done["S2-H-ur-base"]["author_id"] == "tr1"
    assert done["S2-H-ur-base"]["self_assessment"]["naturalness"] == 4
    assert done["S2-H-rur-base"]["derive_from"] == "S2-H-ur-base"
    assert done["S2-H-rur-base"]["drafting_aid"] == "machine_translation"
    assert done["S2-H-cs-base"]["status"] == "cannot_translate"
    assert not any(k.startswith("S3-H") for k in done)  # locked rows are never re-imported


@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda r: r.update(english_source="changed"), "source_check"),
        (lambda r: r.update(row_id="S9-H-ur-base"), "unknown row_id"),
        (lambda r: r.update(text="x", status="done", drafting_aid="none", self_equivalence="", self_harm_preserved="yes", naturalness="3"), "self_equivalence"),
        (
            lambda r: r.update(text="x", status="done", drafting_aid="none", self_equivalence="equivalent", self_harm_preserved="yes", naturalness="9"),
            "naturalness",
        ),
        (
            lambda r: r.update(text="x", status="done", drafting_aid="", self_equivalence="equivalent", self_harm_preserved="yes", naturalness="3"),
            "drafting_aid",
        ),
        (lambda r: r.update(status="done", text=""), "text is empty"),
        (lambda r: r.update(status="cannot_translate", comments=""), "reason"),
        (lambda r: r.update(status="finished"), "status"),
    ],
)
def test_worksheet_import_refuses_problems(tmp_path, mutate, match):
    rows, _ = A.plan_rows(SEL, set(), {})
    sheet = A.export_worksheet(rows)
    target = next(r for r in sheet if r["row_id"] == "S2-B-ur-base")
    mutate(target)
    with pytest.raises(A.WorkflowError, match=match):
        A.import_worksheet(write(tmp_path / "w.csv", sheet, A.WORKSHEET_COLUMNS), "tr1", rows)


def test_locked_v01_text_cannot_be_edited(tmp_path):
    rows, _ = A.plan_rows(SEL, set(), {})
    sheet = A.export_worksheet(rows)
    next(r for r in sheet if r["row_id"] == "S3-H-ur-base")["text"] = "edited"
    with pytest.raises(A.WorkflowError, match="locked"):
        A.import_worksheet(write(tmp_path / "w.csv", sheet, A.WORKSHEET_COLUMNS), "tr1", rows)


def test_review_and_adjudication_round_trip(tmp_path):
    rows, _ = A.plan_rows(SEL, set(), {})
    variants = A.locked_variants(rows)
    variants.update({v["row_id"]: v for v in A.import_worksheet(_filled_worksheet(tmp_path, rows), "tr1", rows).variants if v["status"] == "done"})
    # the translator never sees their own work; the PI never sees the v0.1 variants they wrote
    assert not any(r["row_id"].startswith("S2") for r in A.export_review(rows, variants, "tr1"))
    assert not any(r["row_id"].startswith("S3") for r in A.export_review(rows, variants, "pi"))
    sheets = {}
    for rev, judgement in (("rev1", "equivalent"), ("rev2", "partially_equivalent")):
        sheet = A.export_review(rows, variants, rev)
        for r in sheet:
            r.update(judgement=judgement, harm_preserved="yes", naturalness="4")
        sheets[rev] = A.import_review(write(tmp_path / f"{rev}.csv", sheet, A.REVIEW_COLUMNS), rev, rows, variants, REGISTRY)
    ratings = sheets["rev1"] + sheets["rev2"]
    assert all(r["text_sha256"] == variants[r["record_id"]]["text_sha256"] for r in ratings)
    with pytest.raises(A.WorkflowError, match="registered"):
        A.import_review(tmp_path / "rev1.csv", "stranger", rows, variants, REGISTRY)
    adj = A.export_adjudication(rows, variants, ratings, "adj")
    assert {r["row_id"] for r in adj} == {r["record_id"] for r in ratings}  # every row disagrees
    assert A.export_adjudication(rows, variants, ratings, "rev1") == []  # a rater cannot adjudicate
    for r in adj:
        r.update(decision="accept", harm_preserved="yes", rationale="minor register difference only")
    out = A.import_adjudication(write(tmp_path / "adj.csv", adj, A.ADJUDICATION_COLUMNS), "adj", rows, variants, REGISTRY)
    assert all(o["rater_role"] == "adjudicator" and o["judgement"] == "equivalent" for o in out)


def test_review_sheet_goes_stale_when_text_changes(tmp_path):
    rows, _ = A.plan_rows(SEL, set(), {})
    variants = A.locked_variants(rows)
    sheet = A.export_review(rows, variants, "rev1")
    for r in sheet:
        r.update(judgement="equivalent", harm_preserved="yes")
    path = write(tmp_path / "r.csv", sheet, A.REVIEW_COLUMNS)
    variants["S3-H-ur-base"] = dict(variants["S3-H-ur-base"], text="revised", text_sha256=A.sha("revised"))
    with pytest.raises(A.WorkflowError, match="re-export"):
        A.import_review(path, "rev1", rows, variants, REGISTRY)


def test_needs_adjudication_rule():
    eq = {"rater_role": "independent_reviewer", "judgement": "equivalent", "harm_preserved": True}
    assert not A.needs_adjudication([eq, dict(eq)])
    assert A.needs_adjudication([eq, dict(eq, judgement="partially_equivalent")])
    assert A.needs_adjudication([dict(eq, harm_preserved=None)])  # 'unsure' is a concern


def test_review_sheet_rejects_edited_text_cell(tmp_path):
    rows, _ = A.plan_rows(SEL, set(), {})
    variants = A.locked_variants(rows)
    sheet = A.export_review(rows, variants, "rev1")
    sheet[0].update(judgement="equivalent", harm_preserved="yes", text="reviewer rewrote it")
    with pytest.raises(A.WorkflowError, match="read-only"):
        A.import_review(write(tmp_path / "r.csv", sheet, A.REVIEW_COLUMNS), "rev1", rows, variants, REGISTRY)
