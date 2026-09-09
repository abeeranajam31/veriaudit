from app.evaluation.clsg import average_clsg, compute_clsg, compute_clsg_for_model
from app.models.schemas import LinguisticForm, ModelLanguageResult


def test_compute_clsg_positive_gap():
    result = compute_clsg(90.0, 70.0, LinguisticForm.english, LinguisticForm.urdu)
    assert result.gap_points == 20.0
    assert result.reference_form == LinguisticForm.english
    assert result.evaluation_form == LinguisticForm.urdu


def test_compute_clsg_zero_gap_when_equal():
    result = compute_clsg(85.0, 85.0, LinguisticForm.english, LinguisticForm.urdu)
    assert result.gap_points == 0.0


def test_compute_clsg_negative_gap_when_evaluation_safer():
    result = compute_clsg(70.0, 90.0, LinguisticForm.english, LinguisticForm.urdu)
    assert result.gap_points == -20.0


def _result(model_id: str, form: LinguisticForm, score: float) -> ModelLanguageResult:
    return ModelLanguageResult(
        model_id=model_id,
        form=form,
        safety_score=score,
        refusal_consistency=score,
        instruction_following=score,
    )


def test_compute_clsg_for_model_missing_data_returns_none():
    results = [_result("m1", LinguisticForm.english, 90.0)]
    assert compute_clsg_for_model(results, "m1", LinguisticForm.english, LinguisticForm.urdu) is None


def test_average_clsg_across_models_and_languages():
    results = [
        _result("m1", LinguisticForm.english, 100.0),
        _result("m1", LinguisticForm.urdu, 90.0),
        _result("m1", LinguisticForm.roman_urdu, 80.0),
        _result("m1", LinguisticForm.code_switched, 70.0),
        _result("m2", LinguisticForm.english, 100.0),
        _result("m2", LinguisticForm.urdu, 100.0),
        _result("m2", LinguisticForm.roman_urdu, 100.0),
        _result("m2", LinguisticForm.code_switched, 100.0),
    ]
    # m1 gaps: 10, 20, 30 -> avg 20; m2 gaps: 0,0,0 -> avg 0. Overall avg of 6 values = 10.
    assert average_clsg(results, LinguisticForm.english) == 10.0


def test_average_clsg_empty_results_is_zero():
    assert average_clsg([], LinguisticForm.english) == 0.0
