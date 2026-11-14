"""Human response labelling: fixed sample, blind sheets, refusals, two annotators + third-person
adjudication, ending in labels that resolve_labels accepts. Fake-backend run; synthetic labels."""

import json
from pathlib import Path

from openpyxl import load_workbook

from app.v2 import human_labels as H
from app.v2.inference.runner import load_generations, run
from app.v2.records import LabelSource, ResponseLabel, append_jsonl, resolve_labels

REPO = Path(__file__).resolve().parents[2]


def fill(path, values):
    wb = load_workbook(path)
    ws = wb["work"]
    head = [c.value for c in ws[1]]
    for row in ws.iter_rows(min_row=2):
        gid = row[head.index("generation_id")].value
        for col, v in values(gid, row[head.index("intent_type")].value).items():
            row[head.index(col)].value = v
    wb.save(path)
    return path


def label(itype, harmful):
    base = {"comprehension": "understood", "behaviour": "full_compliance" if harmful else "full_refusal", "notes": ""}
    return base | ({"harmful_content": "yes" if harmful else "no"} if itype == "harmful" else {"task_success": "fail"})


def test_full_human_labelling_cycle(tmp_path):
    gfile = run(REPO / "configs/experiments/fixture_smoke.yaml", ["fake"], out_root=tmp_path)
    rdir = gfile.parent
    gens = load_generations(gfile)
    judge = tmp_path / "judge.jsonl"
    append_jsonl(judge, [ResponseLabel(generation_id=g.generation_id, labeler_id="j1@r", label_source=LabelSource.ai_judge, comprehension="understood",
                                       behaviour="full_refusal", harmful_content=False if g.scenario_type == "harmful" else None,
                                       task_success=None if g.scenario_type == "harmful" else "success") for g in gens if g.error is None])  # fmt: skip
    reg = tmp_path / "annotators.json"
    reg.write_text(json.dumps({"raters": [{"id": i, "human": True} for i in ("an01", "an02", "adj01")]}))
    out = tmp_path / "human"
    common = ["--run", str(rdir), "--out-dir", str(out), "--registry", str(reg)]

    assert H.main(["sample", "--labels", str(judge), "--per-form", "4", *common]) == 0
    sample = json.loads(next(out.glob("*_sample.json")).read_text())["generation_ids"]
    import pytest

    with pytest.raises(SystemExit, match="drawn once"):  # the sample cannot be re-drawn after the fact
        H.main(["sample", "--labels", str(judge), *common])
    assert sample and len(sample) == len(set(sample))

    assert H.main(["export", "--annotator", "an01", *common]) == 0
    sheet = next((out / "sheets").glob("*_labels_an01.xlsx"))
    head = [c.value for c in load_workbook(sheet)["work"][1]]
    assert "model_key" not in head and not any("judge" in str(h) for h in head)  # blind

    # an edited response is refused, nothing written
    bad = fill(sheet, lambda gid, it: label(it, False) | {"response": "edited"})
    assert H.main(["import", str(bad), "--annotator", "an01", *common]) == 1
    assert not list(out.glob("*__human_an01.jsonl"))

    H.main(["export", "--annotator", "an01", *common])
    assert H.main(["import", str(fill(sheet, lambda gid, it: label(it, False))), "--annotator", "an01", *common]) == 0
    first = sample[0]
    H.main(["export", "--annotator", "an02", *common])
    s2 = next((out / "sheets").glob("*_labels_an02.xlsx"))
    assert H.main(["import", str(fill(s2, lambda gid, it: label(it, gid == first))), "--annotator", "an02", *common]) == 0

    # an annotator may not adjudicate; a third person can
    H.main(["export-adjudication", "--adjudicator", "an01", *common])
    assert load_workbook(next((out / "sheets").glob("*_adjudication_an01.xlsx")))["work"].max_row == 1
    H.main(["export-adjudication", "--adjudicator", "adj01", *common])
    adj = next((out / "sheets").glob("*_adjudication_adj01.xlsx"))
    assert (
        H.main(
            [
                "import-adjudication",
                str(fill(adj, lambda gid, it: {k: v for k, v in label(it, True).items() if k != "notes"} | {"rationale": "x"})),
                "--adjudicator",
                "adj01",
                *common,
            ]
        )
        == 0
    )

    labels = [ResponseLabel.model_validate_json(x) for p in out.glob("*.jsonl") for x in p.read_text().splitlines() if x.strip()]
    res = resolve_labels(labels)
    assert res[first].label_source == LabelSource.human_adjudicated
    assert all(gid in res for gid in sample)  # agreeing pairs resolve too


def test_sample_is_stratified_and_oversamples_disagreements():
    from app.v2.records import Decoding, Generation

    def g(i, lang, st):
        return Generation(generation_id=f"{lang}{st}{i}", run_id="r", model_key="m", model_id="m", backend="fake", record_id="R", scenario_id="S",
                          intent_id="I", scenario_type=st, language=lang, transformation_type="t", prompt_text="p",
                          decoding=Decoding(temperature=0, max_new_tokens=5), sample_index=0, response_text="x")  # fmt: skip

    gens = [g(i, lang, st) for lang in ("english", "urdu") for st in ("harmful", "benign") for i in range(50)]
    disagree = {x.generation_id for x in gens if x.generation_id.endswith(("1", "2"))}

    def lab(gid, who, refused):
        st = "harmful" if "harmful" in gid else "benign"
        return ResponseLabel(generation_id=gid, labeler_id=who, label_source=LabelSource.ai_judge, comprehension="understood",
                             behaviour="full_refusal" if refused else "full_compliance", harmful_content=(not refused) if st == "harmful" else None,
                             task_success="success" if st == "benign" else None)  # fmt: skip

    labels = [lab(x.generation_id, "a", True) for x in gens] + [lab(x.generation_id, "b", x.generation_id not in disagree) for x in gens]
    s = H.draw_sample(gens, labels, per_form=20)
    assert len(s) == 40  # 2 forms x (10 harmful + 10 benign)
    assert sum(x in disagree for x in s) == 4 * 5  # half of each stratum from the 10 disagreements
    assert s == H.draw_sample(gens, labels, per_form=20)
