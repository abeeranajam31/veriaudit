import pytest

from app.evaluation.equiv_engine import EquivEngine, NullTranslationProvider
from app.models.schemas import LinguisticForm, VerificationStatus


def test_null_translation_provider_raises_clear_error():
    provider = NullTranslationProvider()
    with pytest.raises(NotImplementedError):
        provider.translate("hello", LinguisticForm.urdu)


def test_generate_variants_without_translator_raises_not_implemented():
    engine = EquivEngine()
    with pytest.raises(NotImplementedError):
        engine.generate_variants("What can I use instead of buttermilk?")


class _StubTranslator:
    """Deterministic stub so tests don't require downloading an ML model."""

    def translate(self, text: str, target_form: LinguisticForm) -> str:
        return f"[{target_form.value}] {text}"


def test_status_for_similarity_flags_low_scores():
    engine = EquivEngine(translator=_StubTranslator())
    assert engine._status_for_similarity(0.5) == VerificationStatus.flagged
    assert engine._status_for_similarity(0.99) == VerificationStatus.pending


def test_generate_variants_produces_all_four_forms(monkeypatch):
    engine = EquivEngine(translator=_StubTranslator())
    monkeypatch.setattr(engine, "compute_similarity", lambda a, b: 0.9)

    response = engine.generate_variants("What can I use instead of buttermilk?")

    forms = {v.form for v in response.variants}
    assert forms == {
        LinguisticForm.english,
        LinguisticForm.urdu,
        LinguisticForm.roman_urdu,
        LinguisticForm.code_switched,
    }
    english_variant = next(v for v in response.variants if v.form == LinguisticForm.english)
    assert english_variant.verification_status == VerificationStatus.verified

    urdu_variant = next(v for v in response.variants if v.form == LinguisticForm.urdu)
    assert urdu_variant.verification_status == VerificationStatus.pending
    assert urdu_variant.similarity == 0.9
