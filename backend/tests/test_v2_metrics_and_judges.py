"""Metric and judge tests on synthetic, hand-computed fixtures (is_test_fixture=True)."""

import json

import pytest

from app.v2.judges.llm_judge import (
    JudgeParseError,
    LLMJudge,
    agreement_report,
    build_messages,
    panel_consensus,
    parse_judgement,
)
from app.v2.metrics import (
    build_units,
    cell_metrics,
    comprehension_stratified,
    linguistic_robustness,
    paired_family,
    transformation_effects,
)
from app.v2.records import (
    Decoding,
    Generation,
    LabelSource,
    ResponseLabel,
    check_label_fits_intent,
    resolve_labels,
    unresolved,
)

DEC = Decoding(temperature=0.7, top_p=0.95, max_new_tokens=512, seed=0)


def gen(model, sid, stype, lang, sample=0, cond="base", text="resp"):
    intent = f"{sid}-{'H' if stype == 'harmful' else 'B'}"
    return Generation(
        generation_id=f"{model}|{intent}|{lang}|{cond}|{sample}",
        run_id="test",
        model_key=model,
        model_id=f"org/{model}",
        backend="fake",
        record_id=f"{intent}-{lang}-{cond}",
        scenario_id=sid,
        intent_id=intent,
        scenario_type=stype,
        language=lang,
        transformation_type="source" if lang == "english" else "translation",
        condition=cond,
        prompt_text="p",
        decoding=DEC,
        sample_index=sample,
        response_text=text,
        is_test_fixture=True,
    )


def lab(g, harmful=False, refused=True, comp="understood", success=None, source=LabelSource.ai_panel, labeler="j"):
    harmful_intent = g.scenario_type == "harmful"
    return ResponseLabel(
        generation_id=g.generation_id,
        labeler_id=labeler,
        label_source=source,
        comprehension=comp,
        behaviour="full_compliance" if (harmful or not refused) else "full_refusal",
        harmful_content=harmful if harmful_intent else None,
        task_success=(success or ("fail" if refused else "success")) if not harmful_intent else None,
        is_test_fixture=True,
    )


def build_fixture():
    """10 scenarios, 1 model, 3 samples each.
    harmful: English never harmful; Urdu harmful in scenarios 0-5; Roman Urdu harmful in 0-1 and
             English-only... (none); code-switched never harmful. Roman Urdu not understood in 6-9.
    benign:  English never refused; Urdu refused in 0-3.
    """
    gens, labels = [], []
    for i in range(10):
        sid = f"S{i}"
        for lang in ("english", "urdu", "roman_urdu", "code_switched"):
            for s in range(3):
                g = gen("m1", sid, "harmful", lang, s)
                harmful = (lang == "urdu" and i < 6) or (lang == "roman_urdu" and i < 2)
                comp = "not_understood" if (lang == "roman_urdu" and i >= 6) else "understood"
                gens.append(g)
                labels.append(lab(g, harmful=harmful, refused=not harmful, comp=comp))
                b = gen("m1", sid, "benign", lang, s)
                gens.append(b)
                labels.append(lab(b, refused=(lang == "urdu" and i < 4)))
    return gens, {x.generation_id: x for x in labels}


def test_cell_metrics_full_denominator():
    gens, labels = build_fixture()
    units, stats = build_units(gens, labels)
    assert stats["unlabelled_units"] == 0
    cells = {c["language"]: c for c in cell_metrics(units)}
    assert cells["english"]["HCR"]["rate"] == 0
    assert cells["urdu"]["HCR"]["count"] == 6 and cells["urdu"]["HCR"]["n"] == 10
    assert cells["urdu"]["ORR"]["count"] == 4
    assert cells["urdu"]["BTS"]["count"] == 6
    # not-understood responses stay in the denominator and are not "appropriate refusals"
    assert cells["roman_urdu"]["ARR"]["count"] == 4 and cells["roman_urdu"]["ARR"]["n"] == 10
    assert cells["roman_urdu"]["CA"]["count"] == 16 and cells["roman_urdu"]["CA"]["n"] == 20


def test_paired_family_h1_and_h2():
    gens, labels = build_fixture()
    units, _ = build_units(gens, labels)
    h1 = {r["language"]: r for r in paired_family(units, "harmful", "harmful", "H1")}
    assert h1["urdu"]["target_only"] == 6 and h1["urdu"]["english_only"] == 0
    assert h1["urdu"]["gap_pp"] == pytest.approx(60.0)
    assert h1["urdu"]["p_mcnemar"] == pytest.approx(0.03125)
    assert h1["urdu"]["p_holm"] == pytest.approx(min(1, 3 * 0.03125))
    assert h1["code_switched"]["p_mcnemar"] == 1.0
    assert h1["urdu"]["ci_low_pp"] < 60 < h1["urdu"]["ci_high_pp"]
    h2 = {r["language"]: r for r in paired_family(units, "benign", "refused", "H2")}
    assert h2["urdu"]["gap_pp"] == pytest.approx(40.0)


def test_majority_and_greedy_aggregation():
    g = [gen("m", "S0", "harmful", "urdu", s) for s in (0, 1, 2)] + [gen("m", "S0", "harmful", "urdu", -1)]
    labels = {x.generation_id: lab(x, harmful=h, refused=not h) for x, h in zip(g, [True, True, False, False], strict=True)}
    maj, _ = build_units(g, labels, "majority")
    grd, _ = build_units(g, labels, "greedy")
    assert maj[0].harmful is True and maj[0].n_samples == 3
    assert grd[0].harmful is False and grd[0].n_samples == 1
    with pytest.raises(ValueError):
        build_units(g, labels, "mean")


def test_unlabelled_units_are_counted_not_guessed():
    gens, labels = build_fixture()
    missing = next(x for x in gens if x.language == "urdu" and x.scenario_type == "harmful")
    del labels[missing.generation_id]
    units, stats = build_units(gens, labels)
    assert stats["unlabelled_units"] == 1
    h1 = {r["language"]: r for r in paired_family(units, "harmful", "harmful", "H1")}
    assert h1["urdu"]["n_dropped_unlabelled"] == 1 and h1["urdu"]["n_pairs"] == 9


def test_linguistic_robustness_and_comprehension_strata():
    gens, labels = build_fixture()
    units, _ = build_units(gens, labels)
    lr = linguistic_robustness(units)[0]
    assert lr["count"] == 4 and lr["n"] == 10  # scenarios 6-9 consistent across all four forms
    strata = {(r["language"], r["understood"]): r for r in comprehension_stratified(units)}
    assert strata[("roman_urdu", False)]["n"] == 4 and strata[("roman_urdu", False)]["count"] == 0
    assert strata[("roman_urdu", True)]["count"] == 2


def test_transformation_effects():
    gens, labels = [], {}
    for i in range(8):
        for cond, harmful in (("base", False), ("T1", i < 5)):
            g = gen("m", f"S{i}", "harmful", "roman_urdu", 0, cond)
            gens.append(g)
            labels[g.generation_id] = lab(g, harmful=harmful, refused=not harmful)
    rows = transformation_effects(build_units(gens, labels)[0])
    assert rows[0]["condition"] == "T1" and rows[0]["gap_pp"] == pytest.approx(62.5)
    assert rows[0]["p_bh"] == pytest.approx(0.0625)


# --------------------------------------------------------------- records


def test_generation_requires_response_xor_error():
    base = gen("m", "S0", "harmful", "english").model_dump()
    with pytest.raises(ValueError):
        Generation.model_validate({**base, "response_text": None})
    Generation.model_validate({**base, "response_text": None, "error": "timeout"})
    with pytest.raises(ValueError):
        Generation.model_validate({**base, "error": "timeout"})


def test_label_intent_fit():
    g = gen("m", "S0", "harmful", "english")
    assert check_label_fits_intent(lab(g), "harmful") == []
    bad = lab(g).model_copy(update={"harmful_content": None, "task_success": "success"})
    assert len(check_label_fits_intent(bad, "harmful")) == 2


def test_resolve_labels_by_tier_and_disagreement():
    g = gen("m", "S0", "harmful", "english")
    ai = lab(g, harmful=True, refused=False, source=LabelSource.ai_judge, labeler="a")
    human = lab(g, harmful=False, source=LabelSource.human, labeler="h")
    assert resolve_labels([ai, human])[g.generation_id].label_source == LabelSource.human
    h2 = lab(g, harmful=True, refused=False, source=LabelSource.human, labeler="h2")
    assert resolve_labels([ai, human, h2]) == {}
    assert unresolved([ai, human, h2]) == [g.generation_id]
    adj = lab(g, harmful=True, refused=False, source=LabelSource.human_adjudicated, labeler="x")
    assert resolve_labels([ai, human, h2, adj])[g.generation_id].harmful_content is True


# --------------------------------------------------------------- judges


class FakeGen:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def generate(self, messages, decoding):
        self.calls.append(messages)
        return self.outputs.pop(0)


GOOD = json.dumps(
    {"comprehension": "understood", "behaviour": "full_refusal", "harmful_content": False, "task_success": None, "confidence": 0.9, "rationale": "r"}
)


def test_build_messages_contains_original_text_and_no_model_name():
    g = gen("secret-model", "S0", "harmful", "urdu", text="میں مدد نہیں کر سکتا")
    msgs = build_messages(g, "desc", "refuse")
    content = msgs[1]["content"]
    assert "میں مدد نہیں کر سکتا" in content and "HARMFUL" in content
    assert "secret-model" not in content


def test_parse_judgement_valid_and_invalid():
    g = gen("m", "S0", "harmful", "english")
    label = parse_judgement("Sure:\n" + GOOD, g, "judgeA")
    assert label.label_source == LabelSource.ai_judge and label.harmful_content is False
    for bad in [
        "no json",
        "{bad json}",
        json.dumps({"comprehension": "x", "behaviour": "full_refusal"}),
        json.dumps({"comprehension": "understood", "behaviour": "full_refusal", "harmful_content": None}),
    ]:
        with pytest.raises(JudgeParseError):
            parse_judgement(bad, g, "j")
    b = gen("m", "S0", "benign", "english")
    with pytest.raises(JudgeParseError):
        parse_judgement(GOOD, b, "j")  # benign needs task_success


def test_llm_judge_retries_then_fails():
    g = gen("m", "S0", "harmful", "english")
    assert LLMJudge("A", FakeGen(["garbage", GOOD])).label(g, "d", "refuse").labeler_id.startswith("A@")
    with pytest.raises(JudgeParseError):
        LLMJudge("A", FakeGen(["garbage", "garbage"])).label(g, "d", "refuse")


def test_panel_consensus_and_agreement_report():
    g = gen("m", "S0", "harmful", "urdu")
    a = parse_judgement(GOOD, g, "A")
    b = parse_judgement(GOOD, g, "B")
    p = panel_consensus([a, b])
    assert p.label_source == LabelSource.ai_panel and "A" in p.labeler_id
    c = a.model_copy(update={"harmful_content": True, "behaviour": "full_compliance"})
    assert panel_consensus([a, c]) is None and panel_consensus([a]) is None
    rep = agreement_report({g.generation_id: a}, {g.generation_id: a}, {g.generation_id: "urdu"})
    assert rep["n"] == 1 and rep["all"]["behaviour"]["accuracy"] == 1.0
