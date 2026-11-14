import pytest
from test_v2_metrics_and_judges import gen, lab
from veriaudit_x_helpers import FIXTURE_FILE

from app.v2.records import LabelSource
from app.v2.review import apply_equivalence_ratings, label_queue, variant_queue
from app.veriaudit_x.schema import EquivalenceRating
from app.veriaudit_x.validation import validate_file, validate_objects


def recs():
    return {r.record_id: r for r in validate_file(FIXTURE_FILE).records}


def test_variant_queue_puts_flagged_first_and_skips_done():
    q = variant_queue(recs().values())
    assert q[0].record_id == "VX-S0003-H-rur-01"  # flagged by screen
    assert all(r.equivalence.status.value in ("pending", "flagged") for r in q)
    assert "VX-S0001-H-ur-01" not in {r.record_id for r in q}  # already verified


def R(a, j="equivalent", h=True):
    return EquivalenceRating(annotator_id=a, judgement=j, harm_preserved=h)


def test_apply_ratings_rules_and_validator_agrees():
    r = recs()["VX-S0002-H-ur-01"]
    one = apply_equivalence_ratings(r, [R("a")])
    assert one.equivalence.status.value == "pending" and one.quality.human_reviewed
    two = apply_equivalence_ratings(one, [R("b")])
    assert two.equivalence.status.value == "verified"
    assert apply_equivalence_ratings(r, [R("a"), R("b", "partially_equivalent")]).equivalence.status.value == "flagged"
    assert apply_equivalence_ratings(r, [R("a"), R("b", h=False)]).equivalence.status.value == "rejected"
    assert apply_equivalence_ratings(r, [R("a", "not_equivalent")]).equivalence.status.value == "flagged"
    # re-rating replaces the earlier rating from the same rater
    assert len(apply_equivalence_ratings(two, [R("a", "not_equivalent")]).equivalence.human_ratings) == 2
    # the dataset with an applied verification still validates
    data = [x.model_dump(mode="json") for x in recs().values() if x.record_id != r.record_id] + [two.model_dump(mode="json")]
    assert validate_objects(data).ok
    with pytest.raises(ValueError):
        apply_equivalence_ratings(recs()["VX-S0001-H-en-01"], [R("a")])


def test_label_queue_orders_disagreement_first():
    g1, g2, g3 = gen("m", "S1", "harmful", "urdu"), gen("m", "S2", "harmful", "urdu"), gen("m", "S3", "harmful", "urdu")
    a = lab(g1, harmful=True, refused=False, source=LabelSource.ai_judge, labeler="x")
    b = lab(g1, harmful=False, source=LabelSource.ai_judge, labeler="y")
    low = lab(g2, source=LabelSource.ai_judge).model_copy(update={"confidence": 0.4})
    human = lab(g3, source=LabelSource.human)
    q = label_queue([a, b, low, human], spot_check_rate=0)
    assert q == [(g1.generation_id, "ai_disagreement"), (g2.generation_id, "low_confidence")]
