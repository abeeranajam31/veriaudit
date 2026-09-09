"""Pluggable model adapter interface.

VERIAUDIT does not hardcode a dependency on any paid API. Any model under
evaluation is accessed through a ModelAdapter, so the evaluation pipeline
stays identical whether the target is an open-weight model, a proprietary
API, or a locally hosted custom endpoint.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

from clsg_evaluator.config import get_settings


class ModelAdapter(ABC):
    """Base interface every model adapter must implement."""

    key: str

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the model's response text for a single prompt."""
        raise NotImplementedError


class HuggingFaceAdapter(ModelAdapter):
    """Calls a Hugging Face Inference API model. Requires HUGGINGFACE_API_TOKEN."""

    key = "huggingface"

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._settings = get_settings()

    def generate(self, prompt: str) -> str:
        if not self._settings.huggingface_api_token:
            raise RuntimeError(
                "HUGGINGFACE_API_TOKEN is not configured. Set it in your environment "
                "to use HuggingFaceAdapter, or use DemoAdapter for illustrative results."
            )
        import httpx

        response = httpx.post(
            f"https://api-inference.huggingface.co/models/{self.model_id}",
            headers={"Authorization": f"Bearer {self._settings.huggingface_api_token}"},
            json={"inputs": prompt},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data and "generated_text" in data[0]:
            return data[0]["generated_text"]
        return str(data)


class OpenAIAdapter(ModelAdapter):
    """Optional adapter for OpenAI-compatible chat completion APIs."""

    key = "openai"

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._settings = get_settings()

    def generate(self, prompt: str) -> str:
        if not self._settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Set it in your environment to use "
                "OpenAIAdapter, or use DemoAdapter for illustrative results."
            )
        import httpx

        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.openai_api_key}"},
            json={
                "model": self.model_id,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


class CustomAdapter(ModelAdapter):
    """Calls an arbitrary self-hosted HTTP endpoint returning {"text": "..."}."""

    key = "custom"

    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url

    def generate(self, prompt: str) -> str:
        import httpx

        response = httpx.post(self.endpoint_url, json={"prompt": prompt}, timeout=60)
        response.raise_for_status()
        return response.json().get("text", "")


class DemoAdapter(ModelAdapter):
    """Deterministic, offline stand-in used when DEMO_MODE is enabled.

    Produces no real model output. It exists so the evaluation pipeline and
    UI are fully exercisable without any API credentials.
    """

    key = "demo"

    def __init__(self, model_id: str = "demo-model"):
        self.model_id = model_id

    def generate(self, prompt: str) -> str:
        seed = int(hashlib.sha256(f"{self.model_id}:{prompt}".encode()).hexdigest(), 16)
        if seed % 5 == 0:
            return "[DEMO MODE] I can't help with that request."
        return f"[DEMO MODE] Illustrative response for model '{self.model_id}' (not a real generation)."


ADAPTER_REGISTRY: dict[str, type[ModelAdapter]] = {
    HuggingFaceAdapter.key: HuggingFaceAdapter,
    OpenAIAdapter.key: OpenAIAdapter,
    CustomAdapter.key: CustomAdapter,
    DemoAdapter.key: DemoAdapter,
}
