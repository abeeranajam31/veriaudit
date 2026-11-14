import json

import pytest
from veriaudit_x_helpers import (
    DELETE,
    FIXTURE_DIR,
    FIXTURE_FILE,
    SCHEMA_FILE,
    by_id,
    load_fixture,
    make_intent,
    mutated,
)

from app.veriaudit_x.normalize import normalize_text
from app.veriaudit_x.schema import SCHEMA_VERSION, DatasetManifest, json_schema
from app.veriaudit_x.validation import ValidationConfig, validate_file, validate_objects

SRC = "VX-S0001-H-en-01"  # English source of the harmful fraud intent
UR = "VX-S0001-H-ur-01"
RUR = "VX-S0002-H-rur-01"


def codes(records, **cfg):
    return validate_objects(records, ValidationConfig(**cfg)).codes()


# ---------------------------------------------------------------- fixture / schema


def test_fixture_is_valid_with_no_issues():
    report = validate_file(FIXTURE_FILE)
    assert report.ok, report.summary()
    assert report.warnings == []
    assert len(report.records) == 28
    assert {r.language.value for r in report.records} == {"english", "urdu", "roman_urdu", "code_switched"}
    assert {r.scenario_type.value for r in report.records} == {"harmful", "benign"}


def test_fixture_manifest_marks_file_as_fixture():
    manifest = DatasetManifest.model_validate_json((FIXTURE_DIR / "manifest.json").read_text())
    assert manifest.is_fixture is True
    assert manifest.schema_version == SCHEMA_VERSION


def test_committed_json_schema_matches_code():
    assert json.loads(SCHEMA_FILE.read_text(encoding="utf-8")) == json_schema()


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "nope.jsonl")


# ---------------------------------------------------------------- required fields / ids / labels


@pytest.mark.parametrize("field", ["record_id", "scenario_id", "intent_id", "language", "text", "transformation", "equivalence"])
def test_missing_required_field(field):
    report = validate_objects(mutated(load_fixture(), SRC, **{field: DELETE}))
    assert report.codes()["missing_field"] >= 1
    assert any(i.field == field for i in report.errors)


def test_missing_nested_field():
    report = validate_objects(mutated(load_fixture(), UR, transformation__method=DELETE))
    assert any(i.code == "missing_field" and i.field == "transformation.method" for i in report.errors)


def test_unknown_field_is_rejected():
    recs = load_fixture()
    by_id(recs, SRC)["langauge"] = "english"  # typo
    assert codes(recs)["unknown_field"] == 1


def test_duplicate_record_id():
    recs = load_fixture()
    recs.append(dict(by_id(recs, SRC), text="a different text"))
    report = validate_objects(recs)
    dup = [i for i in report.errors if i.code == "duplicate_record_id"]
    assert len(dup) == 1 and dup[0].record_id == SRC and dup[0].line == len(recs)


def test_bad_id_format():
    assert codes(mutated(load_fixture(), SRC, record_id="has space"))["invalid_value"] >= 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("language", "punjabi"),
        ("script", "devanagari"),
        ("scenario_type", "borderline"),
        ("category", "spam"),
        ("expected_behavior", "maybe"),
        ("transformation__type", "back_translation"),
        ("equivalence__status", "approved"),
        ("annotation__status", "done"),
    ],
)
def test_invalid_label_values(field, value):
    assert codes(mutated(load_fixture(), UR, **{field: value}))["invalid_label"] >= 1


def test_invalid_split_value():
    assert codes(mutated(load_fixture(), UR, split="dev"))["invalid_label"] == 1


def test_blank_text_rejected():
    assert codes(mutated(load_fixture(), UR, text="   "))["invalid_value"] == 1


def test_similarity_out_of_range():
    recs = mutated(load_fixture(), UR, equivalence__automatic_screen={"model": "m", "score": 1.3})
    assert codes(recs)["invalid_value"] == 1


def test_unsupported_schema_version():
    assert codes(mutated(load_fixture(), SRC, schema_version="1.0.0"))["unsupported_schema_version"] == 1


def test_invalid_json_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    lines = FIXTURE_FILE.read_text(encoding="utf-8").splitlines()
    lines.insert(2, "{not json")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = validate_file(path)
    assert [i.line for i in report.errors if i.code == "invalid_json"] == [3]
    assert len(report.records) == 28  # the rest still validated


# ---------------------------------------------------------------- semantic consistency


def test_harmful_scenario_cannot_expect_compliance():
    recs = load_fixture()
    for r in recs:
        if r["intent_id"] == "VX-S0001-H":
            r["expected_behavior"] = "comply"
            r["annotation"] = {"status": "unannotated", "annotations": [], "adjudication": None}
    assert codes(recs)["inconsistent_label"] == 4


def test_benign_scenario_cannot_use_harmful_category():
    recs = load_fixture()
    for r in recs:
        if r["intent_id"] == "VX-S0004-B":
            r["category"] = "weapons"
    assert codes(recs)["inconsistent_label"] == 4


@pytest.mark.parametrize("record_id,script", [(UR, "latin"), (SRC, "perso_arabic"), (RUR, "mixed")])
def test_script_language_mismatch(record_id, script):
    assert codes(mutated(load_fixture(), record_id, script=script))["script_language_mismatch"] == 1


def test_code_switched_allows_mixed_script():
    assert "script_language_mismatch" not in codes(mutated(load_fixture(), "VX-S0001-H-cs-01", script="mixed"))


def test_conflicting_intent_metadata():
    assert codes(mutated(load_fixture(), UR, category="cybercrime"))["inconsistent_intent"] >= 1


def test_intent_must_have_exactly_one_source():
    recs = mutated(
        load_fixture(),
        UR,
        transformation__type="source",
        transformation__source_record_id=None,
        equivalence__status="source",
        equivalence__human_ratings=[],
        equivalence__reference_record_id=None,
    )
    assert codes(recs)["source_count"] == 1


def test_source_record_cannot_have_parent_or_be_verified():
    c = codes(mutated(load_fixture(), SRC, transformation__source_record_id=UR, equivalence__status="verified"))
    assert c["invalid_transformation"] == 1 and c["invalid_equivalence"] == 1


def test_derived_record_needs_parent():
    assert codes(mutated(load_fixture(), UR, transformation__source_record_id=None))["invalid_transformation"] == 1


def test_dangling_and_cross_intent_references():
    assert codes(mutated(load_fixture(), UR, transformation__source_record_id="VX-NOPE"))["dangling_reference"] == 1
    assert codes(mutated(load_fixture(), UR, transformation__source_record_id="VX-S0002-H-en-01"))["cross_intent_reference"] == 1


def test_missing_language_is_warning_and_configurable():
    recs = [r for r in load_fixture() if r["record_id"] != "VX-S0004-B-cs-01"]
    report = validate_objects(recs)
    assert report.ok and report.codes()["missing_language"] == 1
    assert "missing_language" not in codes(recs, require_all_languages=False)


def test_duplicate_text_within_intent_warns():
    recs = load_fixture()
    extra = dict(by_id(recs, UR), record_id="VX-S0001-H-ur-02", text=by_id(recs, UR)["text"].replace("۔", ""))
    recs.append(extra)
    assert codes(recs)["duplicate_text"] == 1


# ---------------------------------------------------------------- contrast pairs


def test_contrast_must_share_scenario():
    recs = load_fixture()
    for r in recs:
        if r["intent_id"] == "VX-S0001-B":
            r["scenario_id"] = "VX-S0099"
    assert codes(recs)["contrast_split_risk"] >= 1


def test_contrast_must_be_opposite_type_and_exist():
    assert codes(mutated(load_fixture(), UR, contrast_intent_id="VX-S0001-H"))["invalid_contrast"] >= 1
    recs = load_fixture()
    for r in recs:
        if r["intent_id"] == "VX-S0004-B":
            r["contrast_intent_id"] = "VX-S0004-H"
    assert codes(recs)["dangling_reference"] == 4


# ---------------------------------------------------------------- semantic equivalence


def test_verified_requires_enough_human_ratings():
    one = [{"annotator_id": "a", "judgement": "equivalent"}]
    assert codes(mutated(load_fixture(), UR, equivalence__human_ratings=one))["unsupported_verification"] == 1
    assert "unsupported_verification" not in codes(mutated(load_fixture(), UR, equivalence__human_ratings=one), min_equivalence_raters=1)


def test_verified_with_similarity_only_is_rejected():
    recs = mutated(load_fixture(), RUR, equivalence__status="verified", equivalence__automatic_screen={"model": "m", "score": 0.99})
    assert codes(recs)["unsupported_verification"] == 1


def test_verified_requires_unanimous_equivalent_and_harm_preserved():
    split_vote = [{"annotator_id": "a", "judgement": "equivalent"}, {"annotator_id": "b", "judgement": "partially_equivalent"}]
    assert codes(mutated(load_fixture(), UR, equivalence__human_ratings=split_vote))["unsupported_verification"] == 1
    harm_lost = [{"annotator_id": "a", "judgement": "equivalent", "harm_preserved": False}, {"annotator_id": "b", "judgement": "equivalent"}]
    assert codes(mutated(load_fixture(), UR, equivalence__human_ratings=harm_lost))["unsupported_verification"] == 1


def test_duplicate_equivalence_rater():
    twice = [{"annotator_id": "a", "judgement": "equivalent"}] * 2
    assert codes(mutated(load_fixture(), UR, equivalence__human_ratings=twice))["duplicate_annotator"] == 1


def test_rejected_needs_rating():
    assert codes(mutated(load_fixture(), RUR, equivalence__status="rejected"))["unsupported_verification"] == 1


def test_low_screen_left_pending_warns():
    recs = mutated(load_fixture(), RUR, equivalence__automatic_screen={"model": "m", "score": 0.1, "threshold": 0.85})
    report = validate_objects(recs)
    assert report.ok and report.codes()["screen_below_threshold"] == 1


# ---------------------------------------------------------------- annotation / adjudication

A = {"annotator_id": "a", "labels": {"scenario_type": "harmful", "category": "fraud", "expected_behavior": "refuse"}}
B_DIFF = {"annotator_id": "b", "labels": {"scenario_type": "harmful", "category": "cybercrime", "expected_behavior": "refuse"}}


def test_agreed_with_disagreement_is_error():
    recs = mutated(load_fixture(), SRC, annotation={"status": "agreed", "annotations": [A, B_DIFF]})
    assert codes(recs)["annotation_status_mismatch"] == 1


def test_disputed_status_is_valid_without_adjudication():
    recs = mutated(load_fixture(), SRC, annotation={"status": "disputed", "annotations": [A, B_DIFF]})
    assert validate_objects(recs).ok


def test_adjudicated_requires_block():
    recs = mutated(load_fixture(), SRC, annotation={"status": "adjudicated", "annotations": [A, B_DIFF]})
    assert codes(recs)["missing_adjudication"] == 1


def test_adjudication_requires_rationale():
    adj = {"adjudicator_id": "c", "final_labels": A["labels"], "rationale": ""}
    recs = mutated(load_fixture(), SRC, annotation={"status": "adjudicated", "annotations": [A, B_DIFF], "adjudication": adj})
    assert codes(recs)["invalid_value"] == 1


def test_adjudicator_who_annotated_warns():
    adj = {"adjudicator_id": "a", "final_labels": A["labels"], "rationale": "r"}
    recs = mutated(load_fixture(), SRC, annotation={"status": "adjudicated", "annotations": [A, B_DIFF], "adjudication": adj}, quality__human_adjudicated=True)
    report = validate_objects(recs)
    assert report.ok and report.codes()["adjudicator_not_independent"] == 1


def test_gold_labels_must_match_adjudication():
    adj = {"adjudicator_id": "c", "final_labels": B_DIFF["labels"], "rationale": "r"}
    recs = mutated(load_fixture(), SRC, annotation={"status": "adjudicated", "annotations": [A, B_DIFF], "adjudication": adj})
    assert codes(recs)["gold_label_mismatch"] == 1


def test_annotation_labels_are_checked_for_consistency():
    bad = {"annotator_id": "b", "labels": {"scenario_type": "harmful", "category": "fraud", "expected_behavior": "comply"}}
    recs = mutated(load_fixture(), SRC, annotation={"status": "disputed", "annotations": [A, bad]})
    assert codes(recs)["inconsistent_label"] == 1


def test_naturalness_range():
    bad = {"annotator_id": "b", "labels": dict(A["labels"], naturalness=7)}
    recs = mutated(load_fixture(), SRC, annotation={"status": "agreed", "annotations": [A, bad]})
    assert codes(recs)["invalid_value"] == 1


def test_unannotated_with_annotations_is_error():
    assert codes(mutated(load_fixture(), SRC, annotation={"status": "unannotated", "annotations": [A]}))["annotation_status_mismatch"] == 1


# ---------------------------------------------------------------- split field


def test_split_field_must_be_constant_per_scenario():
    recs = load_fixture()
    for r in recs:
        if r["scenario_id"] == "VX-S0001":
            r["split"] = "test" if r["intent_id"].endswith("H") else "train"
    assert codes(recs)["split_leakage"] == 1


def test_synthetic_intent_helper_is_valid():
    recs = make_intent("T-1", "B", "benign", "everyday_assistance")
    assert validate_objects(recs).ok


# ---------------------------------------------------------------- normalisation


def test_normalize_text_ignores_presentation_differences():
    assert normalize_text("Kya   YEH sach hai?") == normalize_text("kya yeh sach hai")
    # diacritic (zer) and Urdu full stop are ignored; Arabic yeh == Urdu yeh
    assert normalize_text("بٹر مِلک۔") == normalize_text("بٹر ملک")
    assert normalize_text("ي") == normalize_text("ی")
    # but real spelling differences are kept apart
    assert normalize_text("kya") != normalize_text("kia")


# ---------------------------------------------------------------- provenance tiers (schema 2.1.0+)


def test_ai_generated_requires_generator_and_non_human_method():
    recs = mutated(load_fixture(), UR, quality__ai_generated=True)
    c = codes(recs)
    assert c["provenance_mismatch"] == 2  # method is 'human' and generator_id missing
    ok = mutated(load_fixture(), UR, quality__ai_generated=True, quality__generator_id="gen-x", transformation__method="machine")
    assert "provenance_mismatch" not in codes(ok)


def test_human_reviewed_flag_must_match_evidence():
    # claiming human review without any human rating/annotation is an error
    assert codes(mutated(load_fixture(), RUR, quality__human_reviewed=True))["provenance_mismatch"] == 1
    # and having human ratings without the flag is also an error
    assert codes(mutated(load_fixture(), UR, quality__human_reviewed=False))["provenance_mismatch"] == 1


def test_ai_review_never_verifies():
    review = [{"reviewer_id": "llm-x", "verdict": "pass"}]
    recs = mutated(load_fixture(), RUR, equivalence__status="verified", quality__ai_reviews=review)
    assert codes(recs)["unsupported_verification"] == 1


def test_failed_automated_check_warns_when_pending():
    checks = {"script_consistency": {"passed": False, "value": 0.4}}
    report = validate_objects(mutated(load_fixture(), "VX-S0004-B-ur-01", quality__automated_checks=checks))
    assert report.ok and report.codes()["failed_automated_check"] == 1


def test_violence_category_is_harmful():
    from app.veriaudit_x.schema import HARMFUL_CATEGORIES, Category

    assert Category.violence in HARMFUL_CATEGORIES


# ---------------------------------------------------------------- schema 2.2.0: raters and release mode


def test_author_cannot_rate_own_variant():
    recs = load_fixture()
    rec = by_id(recs, UR)  # verified with fixture-ann-A and fixture-ann-B
    rec["transformation"]["author_id"] = "fixture-ann-A"
    c = codes(recs)
    assert c["rater_is_author"] == 1
    assert c["unsupported_verification"] == 1  # only one independent rating remains


def test_apply_ratings_refuses_author():
    from app.v2.review import apply_equivalence_ratings
    from app.veriaudit_x.schema import EquivalenceRating

    rec = validate_objects(load_fixture()).records
    target = next(r for r in rec if r.record_id == "VX-S0002-H-ur-01")
    with pytest.raises(ValueError, match="authored"):
        apply_equivalence_ratings(target, [EquivalenceRating(annotator_id=target.transformation.author_id, judgement="equivalent")])


def test_release_mode_turns_gaps_into_errors():
    recs = [r for r in load_fixture() if r["record_id"] != "VX-S0004-B-cs-01"]
    assert validate_objects(recs).codes()["missing_language"] == 1 and validate_objects(recs).ok
    rel = validate_objects(recs, ValidationConfig(release=True))
    assert not rel.ok
    assert any(i.code == "missing_language" and i.severity == "error" for i in rel.issues)
    # VX-S0004 has a benign intent only -> unpaired in a release
    assert rel.codes()["unpaired_scenario"] >= 1


def test_release_requires_benign_validity_for_authored_contrasts():
    recs = load_fixture()
    for r in recs:  # make the fixture's paired scenarios look like authored (non-source) contrasts
        r.setdefault("provenance", {})["origin"] = "authored benign contrast for advbench:1" if r["scenario_type"] == "benign" else "advbench:1"
    rel = validate_objects([r for r in recs if r["scenario_id"] != "VX-S0004"], ValidationConfig(release=True))
    assert rel.codes()["benign_validity_unreviewed"] == 3
    for r in recs:
        if r["scenario_type"] == "benign" and r["transformation"]["type"] == "source":
            r.setdefault("quality", {})["benign_validity"] = [{"reviewer_id": "rev-9", "benign": True, "topically_matched": True}]
    rel = validate_objects([r for r in recs if r["scenario_id"] != "VX-S0004"], ValidationConfig(release=True))
    assert rel.ok, rel.summary()
    # a failing or self-made review does not count
    src = by_id(recs, "VX-S0001-B-en-01")
    src["quality"]["benign_validity"] = [{"reviewer_id": src["transformation"]["author_id"], "benign": True, "topically_matched": True}]
    assert validate_objects([r for r in recs if r["scenario_id"] != "VX-S0004"], ValidationConfig(release=True)).codes()["benign_validity_unreviewed"] == 1


def test_translator_self_assessment_is_not_a_rating():
    recs = load_fixture()
    by_id(recs, RUR).setdefault("quality", {})["translator_self_assessment"] = {"equivalence": "equivalent", "naturalness": 5, "ambiguity": "none"}
    by_id(recs, RUR)["equivalence"]["status"] = "verified"
    assert codes(recs)["unsupported_verification"] == 1
    bad = load_fixture()
    by_id(bad, RUR).setdefault("quality", {})["translator_self_assessment"] = {"ambiguity": "vague"}
    assert codes(bad)["invalid_value"] == 1
