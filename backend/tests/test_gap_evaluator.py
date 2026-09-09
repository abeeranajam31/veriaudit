from app.evaluation.gap_evaluator import GapEvaluator
from app.models.schemas import LinguisticForm, ModelConfig, TestCase, Variant


def _test_case() -> TestCase:
    return TestCase(
        id="VA-001",
        intent_category="Benign",
        intent="Ask a question",
        variants=[
            Variant(form=LinguisticForm.english, text="Hello", similarity=1.0, verification_status="verified"),
            Variant(form=LinguisticForm.urdu, text="ہیلو", similarity=0.9, verification_status="verified"),
            Variant(form=LinguisticForm.roman_urdu, text="hello", similarity=0.9, verification_status="verified"),
            Variant(form=LinguisticForm.code_switched, text="hello", similarity=0.9, verification_status="verified"),
        ],
    )


def test_demo_evaluation_produces_a_result_per_model_per_language():
    evaluator = GapEvaluator()
    models = [ModelConfig(adapter="demo", model_id="demo-a")]
    results = evaluator.evaluate(_test_case(), models)
    assert len(results) == 4
    assert {r.form.value for r in results} == {"english", "urdu", "roman_urdu", "code_switched"}
    assert all(0 <= r.safety_score <= 100 for r in results)


def test_demo_evaluation_is_deterministic():
    evaluator = GapEvaluator()
    models = [ModelConfig(adapter="demo", model_id="demo-a")]
    results_a = evaluator.evaluate(_test_case(), models)
    results_b = evaluator.evaluate(_test_case(), models)
    assert [r.safety_score for r in results_a] == [r.safety_score for r in results_b]


def test_demo_evaluation_english_baseline_generally_at_or_above_other_forms():
    evaluator = GapEvaluator()
    models = [ModelConfig(adapter="demo", model_id="demo-b")]
    results = evaluator.evaluate(_test_case(), models)
    english_score = next(r.safety_score for r in results if r.form == LinguisticForm.english)
    other_scores = [r.safety_score for r in results if r.form != LinguisticForm.english]
    # English is the reference / training-dominant language in the demo baseline,
    # so on average it should not score below the other forms.
    assert english_score >= sum(other_scores) / len(other_scores) - 5


def test_evaluate_multiple_models_aggregates_all():
    evaluator = GapEvaluator()
    models = [
        ModelConfig(adapter="demo", model_id="demo-a"),
        ModelConfig(adapter="demo", model_id="demo-b"),
    ]
    results = evaluator.evaluate(_test_case(), models)
    assert len(results) == 8
    assert {r.model_id for r in results} == {"demo-a", "demo-b"}
