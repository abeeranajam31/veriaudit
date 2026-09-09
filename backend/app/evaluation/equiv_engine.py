"""EquivEngine — transforms an English intent into linguistic variants and
screens them for semantic equivalence.

Pipeline: English prompt -> Urdu translation -> Roman Urdu transformation ->
code-switched variant -> semantic equivalence analysis.

IMPORTANT: embedding similarity is a screening signal, not proof of
equivalence. VERIAUDIT never treats `similarity > threshold` as automatic
verification — every variant starts as `pending` and must be promoted to
`verified` by a human reviewer (or explicitly `flagged` when similarity is
low). See /docs/methodology.md.
"""

from __future__ import annotations

from typing import Protocol

from app.config import get_settings
from app.models.schemas import GenerateVariantsResponse, LinguisticForm, Variant, VerificationStatus

_TARGET_FORMS = [LinguisticForm.urdu, LinguisticForm.roman_urdu, LinguisticForm.code_switched]


class TranslationProvider(Protocol):
    def translate(self, text: str, target_form: LinguisticForm) -> str: ...


class NullTranslationProvider:
    """Default provider. Raises clearly instead of fabricating a translation."""

    def translate(self, text: str, target_form: LinguisticForm) -> str:
        raise NotImplementedError(
            "No TranslationProvider is configured. EquivEngine screens semantic "
            "equivalence but does not itself invent translations — plug in a "
            "TranslationProvider (e.g. an MT model or LLM-based translator) to "
            "enable live variant generation. See /dataset/README.md for the "
            "human-authored pilot dataset used by the demo UI in the meantime."
        )


class EquivEngine:
    def __init__(
        self,
        translator: TranslationProvider | None = None,
        similarity_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ):
        self._translator = translator or NullTranslationProvider()
        self._similarity_model_name = similarity_model_name
        self._similarity_model = None
        self._settings = get_settings()

    def _load_similarity_model(self):
        if self._similarity_model is None:
            from sentence_transformers import SentenceTransformer

            self._similarity_model = SentenceTransformer(self._similarity_model_name)
        return self._similarity_model

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Cosine similarity between two texts using a multilingual sentence
        embedding model. This is a screening heuristic, not a semantic
        equivalence guarantee — see module docstring.
        """
        model = self._load_similarity_model()
        from sentence_transformers import util

        embeddings = model.encode([text_a, text_b], normalize_embeddings=True)
        score = float(util.cos_sim(embeddings[0], embeddings[1])[0][0])
        return max(0.0, min(1.0, score))

    def _status_for_similarity(self, similarity: float) -> VerificationStatus:
        if similarity < self._settings.similarity_flag_threshold:
            return VerificationStatus.flagged
        return VerificationStatus.pending

    def generate_variants(self, english_text: str) -> GenerateVariantsResponse:
        variants = [
            Variant(
                form=LinguisticForm.english,
                text=english_text,
                similarity=1.0,
                verification_status=VerificationStatus.verified,
            )
        ]

        for form in _TARGET_FORMS:
            translated = self._translator.translate(english_text, form)
            similarity = self.compute_similarity(english_text, translated)
            variants.append(
                Variant(
                    form=form,
                    text=translated,
                    similarity=similarity,
                    verification_status=self._status_for_similarity(similarity),
                )
            )

        return GenerateVariantsResponse(
            variants=variants,
            note=(
                "Variants are machine-translated and screened by embedding similarity "
                "only. None are auto-verified — review before treating as ground truth."
            ),
        )
