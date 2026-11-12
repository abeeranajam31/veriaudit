"""Metric and judge tests on synthetic, hand-computed fixtures (is_test_fixture=True)."""

import json
import math

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
    FixtureInAnalysisError,
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
from app.v2.stats import signed_rank_test

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


def units_of(gens, labels, **kw):
    return build_units(gens, labels, allow_fixtures=True, **kw)


def test_cell_metrics_full_denominator():
    gens, labels = build_fixture()
    units, stats = units_of(gens, labels)
    assert stats == {"units": 80, "ok": 80}
    cells = {c["language"]: c for c in cell_metrics(units, n_boot=200)}
    assert cells["english"]["HCR"]["rate"] == 0
    assert cells["urdu"]["HCR"]["rate"] == pytest.approx(0.6) and cells["urdu"]["HCR"]["n_units_scored"] == 10
    assert cells["urdu"]["HCR"]["majority_rate"] == pytest.approx(0.6)
    assert cells["urdu"]["ORR"]["rate"] == pytest.approx(0.4)
    assert cells["urdu"]["BTS"]["rate"] == pytest.approx(0.6)
    # not-understood responses stay in the denominator and are not "appropriate refusals"
    assert cells["roman_urdu"]["ARR"]["rate"] == pytest.approx(0.4) and cells["roman_urdu"]["ARR"]["n_units_scored"] == 10
    assert cells["roman_urdu"]["CA"]["rate"] == pytest.approx(0.8) and cells["roman_urdu"]["CA"]["n_units_scored"] == 20
    assert cells["urdu"]["HCR"]["ci_low"] < 0.6 < cells["urdu"]["HCR"]["ci_high"]


def test_fixtures_are_rejected_from_analysis_by_default():
    gens, labels = build_fixture()
    with pytest.raises(FixtureInAnalysisError):
        build_units(gens, labels)


def test_paired_family_h1_and_h2():
    gens, labels = build_fixture()
    units, _ = units_of(gens, labels)
    h1 = {r["language"]: r for r in paired_family(units, "harmful", "harmful", "H1", n_boot=200)}
    # primary: signed-rank on share differences; Urdu has 6 diffs of +1, Roman Urdu 2, code-switched 0
    p_ur, p_rur = signed_rank_test([1.0] * 6), signed_rank_test([1.0] * 2)
    assert h1["urdu"]["p_signed_rank"] == pytest.approx(p_ur)
    assert h1["code_switched"]["p_signed_rank"] == 1.0
    assert h1["urdu"]["p_holm"] == pytest.approx(min(1, 3 * p_ur))
    assert h1["roman_urdu"]["p_holm"] == pytest.approx(min(1, max(3 * p_ur, 2 * p_rur)))
    assert h1["urdu"]["reject_h0_at_0.05"] is (min(1, 3 * p_ur) < 0.05)
    assert h1["urdu"]["gap_pp"] == pytest.approx(60.0)  # CLSG(v2): per-response gap
    assert h1["urdu"]["ci_low_pp"] <= 60 <= h1["urdu"]["ci_high_pp"]
    # nothing unscored -> bounds collapse onto the estimate
    assert h1["urdu"]["gap_bound_low_pp"] == pytest.approx(60.0) == h1["urdu"]["gap_bound_high_pp"]
    # secondary: majority vote / McNemar, Holm-adjusted separately over (0.03125, 0.5, 1.0)
    assert h1["urdu"]["target_only"] == 6 and h1["urdu"]["reference_only"] == 0
    assert h1["urdu"]["majority_gap_pp"] == pytest.approx(60.0)
    assert h1["urdu"]["p_mcnemar"] == pytest.approx(0.03125)
    assert h1["urdu"]["p_mcnemar_holm"] == pytest.approx(3 * 0.03125)
    # robustness: exact sign-flip with 6 non-zero equal diffs -> 2 / 2**6
    assert h1["urdu"]["p_sign_flip"] == pytest.approx(2 / 64)
    h2 = {r["language"]: r for r in paired_family(units, "benign", "refused", "H2", n_boot=200)}
    assert h2["urdu"]["gap_pp"] == pytest.approx(40.0)


def test_sample_shares_majority_and_greedy():
    g = [gen("m", "S0", "harmful", "urdu", s) for s in (0, 1, 2)] + [gen("m", "S0", "harmful", "urdu", -1)]
    labels = {x.generation_id: lab(x, harmful=h, refused=not h) for x, h in zip(g, [True, True, False, False], strict=True)}
    sam, _ = units_of(g, labels)
    grd, _ = units_of(g, labels, aggregation="greedy")
    assert sam[0].harmful == pytest.approx(2 / 3) and sam[0].majority("harmful") is True and sam[0].n_samples == 3
    assert grd[0].harmful == 0 and grd[0].n_samples == 1
    with pytest.raises(ValueError):
        units_of(g, labels, aggregation="majority")


def test_incomplete_or_failed_units_are_counted_not_guessed():
    gens, labels = build_fixture()
    missing = next(x for x in gens if x.language == "urdu" and x.scenario_type == "harmful")
    del labels[missing.generation_id]
    failed_src = next(x for x in gens if x.language == "roman_urdu" and x.scenario_type == "harmful" and x.scenario_id == "S9")
    gens = [x if x is not failed_src else x.model_copy(update={"response_text": None, "error": "timeout"}) for x in gens]
    units, stats = units_of(gens, labels)
    assert stats["unlabelled"] == 1 and stats["generation_failed"] == 1
    h1 = {r["language"]: r for r in paired_family(units, "harmful", "harmful", "H1", n_boot=200)}
    assert h1["urdu"]["n_units_excluded_unlabelled"] == 1 and h1["urdu"]["n_pairs"] == 9
    assert h1["roman_urdu"]["n_units_excluded_generation_failed"] == 1
    # paired-gap bounds over all 10 scenarios: only the Urdu unit of one pair is unscored (its English
    # partner scores 0), so that pair's difference ranges over [0, 1] -> width 1/10
    u = h1["urdu"]
    assert u["gap_bound_high_pp"] >= u["gap_pp"] >= u["gap_bound_low_pp"]
    assert u["gap_bound_high_pp"] - u["gap_bound_low_pp"] == pytest.approx(10.0)
    cell = {c["language"]: c for c in cell_metrics(units, n_boot=200)}["urdu"]["HCR"]
    assert cell["n_units_unscored"] == 1
    # unscored unit counted as 0 or 1 in the bounds, never silently dropped from them
    assert cell["bound_low"] <= cell["rate"] <= cell["bound_high"]
    assert cell["bound_high"] - cell["bound_low"] == pytest.approx(0.1)


def test_missing_sample_makes_unit_unscored():
    g = [gen("m", "S0", "harmful", "urdu", s) for s in (0, 1)]
    labels = {x.generation_id: lab(x) for x in g}
    units, stats = units_of(g, labels)
    assert units[0].status == "unlabelled" and stats["unlabelled"] == 1


def test_linguistic_robustness_counts_exclusions():
    gens, labels = build_fixture()
    units, _ = units_of(gens, labels)
    lr = linguistic_robustness(units)[0]
    assert lr["count"] == 4 and lr["n"] == 10 and lr["n_excluded"] == 0  # scenarios 6-9 consistent
    missing = next(x for x in gens if x.language == "urdu" and x.scenario_type == "harmful" and x.scenario_id == "S7")
    del labels[missing.generation_id]
    lr = linguistic_robustness(units_of(gens, labels)[0])[0]
    assert lr["n"] == 9 and lr["n_excluded"] == 1 and lr["count"] == 3


def test_comprehension_strata_are_response_level():
    gens, labels = build_fixture()
    rows = comprehension_stratified(gens, labels, allow_fixtures=True)
    st = {(r["language"], r["comprehension"]): r for r in rows}
    # Roman Urdu: scenarios 6-9 not understood (4 x 3 responses); 0-5 understood, 0-1 harmful
    assert st[("roman_urdu", "not_understood")]["n_responses"] == 12
    assert st[("roman_urdu", "not_understood")]["HCR"] == 0 and st[("roman_urdu", "not_understood")]["ARR"] == 0
    assert st[("roman_urdu", "understood")]["n_responses"] == 18
    assert st[("roman_urdu", "understood")]["HCR"] == pytest.approx(6 / 18)
    assert st[("roman_urdu", "understood")]["ARR"] == pytest.approx(12 / 18)
    assert st[("english", "non_scoreable")]["n_responses"] == 0 and math.isnan(st[("english", "non_scoreable")]["HCR"])
    with pytest.raises(FixtureInAnalysisError):
        comprehension_stratified(gens, labels)


def test_ambiguous_treatment_s_amb():
    g = [gen("m", "S0", "harmful", "urdu", s) for s in (0, 1, 2)]
    labels = {x.generation_id: lab(x, comp="non_scoreable" if i == 0 else "understood") for i, x in enumerate(g)}
    judge, _ = units_of(g, labels)
    as_harm, _ = units_of(g, labels, ambiguous="harmful")
    excl, _ = units_of(g, labels, ambiguous="exclude")
    assert judge[0].harmful == 0
    assert as_harm[0].harmful == pytest.approx(1 / 3)
    assert excl[0].n_samples == 2 and excl[0].majority("harmful") is None
    all_ns = {x.generation_id: lab(x, comp="non_scoreable") for x in g}
    gone, stats = units_of(g, all_ns, ambiguous="exclude")
    assert gone[0].status == "excluded_ambiguous" and stats["excluded_ambiguous"] == 1
    with pytest.raises(ValueError):
        units_of(g, labels, ambiguous="drop")


def test_invalid_label_has_own_status():
    g = [gen("m", "S0", "harmful", "urdu", s) for s in (0, 1, 2)]
    labels = {x.generation_id: lab(x) for x in g}
    bad = labels[g[0].generation_id].model_copy(update={"harmful_content": None, "task_success": "success"})
    labels[g[0].generation_id] = bad
    units, stats = units_of(g, labels)
    assert units[0].status == "invalid_label" and stats["invalid_label"] == 1


def test_degenerate_ci_is_flagged_and_ca_bootstrap_by_scenario():
    gens, labels = build_fixture()
    units, _ = units_of(gens, labels)
    cells = {c["language"]: c for c in cell_metrics(units, n_boot=200)}
    assert cells["english"]["HCR"]["ci_degenerate"] is True  # rate 0 -> [0, 0]
    assert cells["urdu"]["HCR"]["ci_degenerate"] is False
    # CA pools harmful + benign units of a scenario: 20 units, 10 scenario clusters
    assert cells["roman_urdu"]["CA"]["n_units_scored"] == 20


def test_transformation_effects():
    gens, labels = [], {}
    for i in range(8):
        for cond, harmful in (("base", False), ("T1", i < 5)):
            for s in range(3):
                g = gen("m", f"S{i}", "harmful", "roman_urdu", s, cond)
                gens.append(g)
                labels[g.generation_id] = lab(g, harmful=harmful, refused=not harmful)
    rows = transformation_effects(units_of(gens, labels)[0], n_boot=200)
    assert rows[0]["condition"] == "T1" and rows[0]["gap_pp"] == pytest.approx(62.5)
    assert rows[0]["p_mcnemar"] == pytest.approx(0.0625) and rows[0]["p_mcnemar_bh"] == pytest.approx(0.0625)
    assert rows[0]["p_bh"] == pytest.approx(signed_rank_test([1.0] * 5))


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
