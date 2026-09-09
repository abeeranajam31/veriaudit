"""Minimal standalone settings for the CLSG-Evaluator package.

Kept dependency-free (no pydantic-settings) since this package is meant to
be usable outside the full VERIAUDIT backend service.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    demo_mode: bool = True
    similarity_flag_threshold: float = 0.85
    huggingface_api_token: str | None = None
    openai_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings(
        demo_mode=os.environ.get("DEMO_MODE", "true").lower() != "false",
        similarity_flag_threshold=float(os.environ.get("SIMILARITY_FLAG_THRESHOLD", "0.85")),
        huggingface_api_token=os.environ.get("HUGGINGFACE_API_TOKEN"),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
    )
