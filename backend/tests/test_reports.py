from app.evaluation.gap_evaluator import GapEvaluator
from app.models.schemas import LinguisticForm, ModelConfig, TestCase, Variant
from app.reports.evidence_report import build_evidence_report


def test_build_evidence_report_produces_valid_pdf_bytes():
    test_case = TestCase(
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
    results = GapEvaluator().evaluate(test_case, [ModelConfig(adapter="demo", model_id="demo-a")])

    pdf_bytes = build_evidence_report("VA-AUDIT-TEST", [test_case], results)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500
