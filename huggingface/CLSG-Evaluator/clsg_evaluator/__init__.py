"""CLSG-Evaluator — the VERIAUDIT cross-lingual AI safety evaluation framework.

Part of VERIAUDIT: https://veriaudit.vercel.app
Source of truth (issues/PRs): https://github.com/abeeranajam31/veriaudit
"""

from clsg_evaluator.clsg import average_clsg, compute_clsg, compute_clsg_for_model
from clsg_evaluator.equiv_engine import EquivEngine, NullTranslationProvider, TranslationProvider
from clsg_evaluator.evaluators import DEFAULT_EVALUATORS, Evaluator
from clsg_evaluator.gap_evaluator import GapEvaluator
from clsg_evaluator.model_adapters import (
    ADAPTER_REGISTRY,
    CustomAdapter,
    DemoAdapter,
    HuggingFaceAdapter,
    ModelAdapter,
    OpenAIAdapter,
)

__version__ = "0.1.0"

__all__ = [
    "compute_clsg",
    "compute_clsg_for_model",
    "average_clsg",
    "EquivEngine",
    "TranslationProvider",
    "NullTranslationProvider",
    "Evaluator",
    "DEFAULT_EVALUATORS",
    "GapEvaluator",
    "ModelAdapter",
    "HuggingFaceAdapter",
    "OpenAIAdapter",
    "CustomAdapter",
    "DemoAdapter",
    "ADAPTER_REGISTRY",
]
