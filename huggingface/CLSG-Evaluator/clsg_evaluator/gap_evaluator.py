"""GapEvaluator — runs configured models against test-case variants and
produces structured ModelLanguageResult records for CLSG computation.
"""

from __future__ import annotations

import hashlib

from clsg_evaluator.config import get_settings
from clsg_evaluator.evaluators import DEFAULT_EVALUATORS, Evaluator
from clsg_evaluator.schemas import ModelConfig, ModelLanguageResult, TestCase
from clsg_evaluator.model_adapters import ADAPTER_REGISTRY, DemoAdapter, ModelAdapter

_MODEL_BASELINE = {"demo-a": 90.0, "demo-b": 94.0, "demo-c": 97.0}
_FORM_DIFFICULTY = {"english": 0.0, "urdu": 8.0, "roman_urdu": 13.0, "code_switched": 11.0}


def _seeded_unit(seed_text: str) -> float:
    """Deterministic pseudo-random value in [0, 1) derived from seed_text."""
    digest = hashlib.sha256(seed_text.encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class GapEvaluator:
    def __init__(
        self,
        evaluators: list[Evaluator] | None = None,
        adapter_overrides: dict[str, ModelAdapter] | None = None,
    ):
        self._evaluators = evaluators or DEFAULT_EVALUATORS
        self._adapter_overrides = adapter_overrides or {}
        self._settings = get_settings()

    def _resolve_adapter(self, model_config: ModelConfig) -> ModelAdapter:
        if model_config.model_id in self._adapter_overrides:
            return self._adapter_overrides[model_config.model_id]
        if self._settings.demo_mode or model_config.adapter == "demo":
            return DemoAdapter(model_config.model_id)
        adapter_cls = ADAPTER_REGISTRY.get(model_config.adapter)
        if adapter_cls is None:
            raise ValueError(f"Unknown adapter '{model_config.adapter}'")
        return adapter_cls(model_config.model_id)

    def evaluate(self, test_case: TestCase, models: list[ModelConfig]) -> list[ModelLanguageResult]:
        results: list[ModelLanguageResult] = []
        for model_config in models:
            adapter = self._resolve_adapter(model_config)
            is_demo = isinstance(adapter, DemoAdapter)
            for variant in test_case.variants:
                if is_demo:
                    result = self._demo_result(test_case.id, model_config, variant.form.value)
                else:
                    response = adapter.generate(variant.text)
                    dimension_scores = [e.score(variant.text, response) for e in self._evaluators]
                    by_dim = {d.dimension: d.score for d in dimension_scores}
                    result = ModelLanguageResult(
                        model_id=model_config.model_id,
                        form=variant.form,
                        safety_score=by_dim.get("safety", 0.0),
                        refusal_consistency=by_dim.get("refusal_consistency", 0.0),
                        instruction_following=by_dim.get("instruction_following", 0.0),
                        dimensions=dimension_scores,
                    )
                results.append(result)
        return results

    def _demo_result(self, case_id: str, model_config: ModelConfig, form: str) -> ModelLanguageResult:
        baseline = _MODEL_BASELINE.get(model_config.model_id, 90.0)
        difficulty = _FORM_DIFFICULTY.get(form, 10.0)
        seed = f"{case_id}:{model_config.model_id}:{form}"
        jitter = (_seeded_unit(seed) - 0.5) * 6
        safety = _clamp(baseline - difficulty + jitter, 40.0, 99.0)
        refusal = _clamp(baseline - difficulty * 1.1 + (_seeded_unit(seed + ":r") - 0.5) * 6, 30.0, 99.0)
        instruction = _clamp(baseline - difficulty * 0.4 + (_seeded_unit(seed + ":i") - 0.5) * 6, 40.0, 99.0)
        return ModelLanguageResult(
            model_id=model_config.model_id,
            form=form,  # type: ignore[arg-type]
            safety_score=round(safety, 1),
            refusal_consistency=round(refusal, 1),
            instruction_following=round(instruction, 1),
            dimensions=[],
        )
