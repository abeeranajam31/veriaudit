"""Generation backends for VeriAudit v2.

Every backend implements `generate(messages, decoding) -> str` and `describe() -> dict`
(model id, pinned revision, backend name). Heavy dependencies (torch, transformers,
vllm, httpx) are imported lazily so the module loads on machines without them.

- TransformersBackend: Hugging Face Transformers, local GPU/CPU or Colab.
- VLLMBackend: vLLM offline engine for batched GPU inference.
- OpenAICompatibleBackend: any OpenAI-compatible HTTP server (vLLM serve, TGI, Ollama,
  hosted APIs). Requires an explicit base_url; never defaults to a paid endpoint.
- FakeBackend: deterministic echo for tests only; its outputs are marked as test fixtures
  by the runner and must never be analysed as results.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from app.v2.records import Decoding


class BackendError(RuntimeError):
    pass


@dataclass
class TransformersBackend:
    model_id: str
    revision: str | None = None
    dtype: str = "bfloat16"
    device_map: str = "auto"
    chat_template_kwargs: dict = field(default_factory=dict)
    _model: object = None
    _tok: object = None
    name: str = "transformers"

    def _load(self):
        if self._model is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._tok = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id, revision=self.revision, torch_dtype=getattr(torch, self.dtype), device_map=self.device_map
            )
        return self._model, self._tok

    def generate(self, messages: list[dict], decoding: Decoding) -> str:
        import torch

        model, tok = self._load()
        prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **self.chat_template_kwargs)
        inputs = tok(prompt, return_tensors="pt").to(model.device)
        if decoding.seed is not None:
            torch.manual_seed(decoding.seed)
        do_sample = decoding.temperature > 0
        out = model.generate(
            **inputs,
            max_new_tokens=decoding.max_new_tokens,
            do_sample=do_sample,
            temperature=decoding.temperature if do_sample else None,
            top_p=decoding.top_p if do_sample else None,
        )
        return tok.decode(out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)

    def describe(self) -> dict:
        return {"backend": self.name, "model_id": self.model_id, "revision": self.revision, "dtype": self.dtype}


@dataclass
class VLLMBackend:
    model_id: str
    revision: str | None = None
    dtype: str = "bfloat16"
    chat_template_kwargs: dict = field(default_factory=dict)
    max_model_len: int = 4096
    _llm: object = None
    name: str = "vllm"

    def _load(self):
        if self._llm is None:
            from vllm import LLM

            self._llm = LLM(model=self.model_id, revision=self.revision, dtype=self.dtype, max_model_len=self.max_model_len)
        return self._llm

    def generate_batch(self, batch: list[list[dict]], decoding: Decoding) -> list[str]:
        from vllm import SamplingParams

        llm = self._load()
        params = SamplingParams(temperature=decoding.temperature, top_p=decoding.top_p, max_tokens=decoding.max_new_tokens, seed=decoding.seed)
        outs = llm.chat(batch, params, chat_template_kwargs=self.chat_template_kwargs or None)
        return [o.outputs[0].text for o in outs]

    def generate(self, messages: list[dict], decoding: Decoding) -> str:
        return self.generate_batch([messages], decoding)[0]

    def describe(self) -> dict:
        return {"backend": self.name, "model_id": self.model_id, "revision": self.revision, "dtype": self.dtype}


@dataclass
class OpenAICompatibleBackend:
    model_id: str
    base_url: str
    api_key_env: str | None = None
    timeout_s: float = 120.0
    extra_body: dict = field(default_factory=dict)
    name: str = "openai_compatible"

    def generate(self, messages: list[dict], decoding: Decoding) -> str:
        import httpx

        headers = {}
        if self.api_key_env:
            key = os.environ.get(self.api_key_env)
            if not key:
                raise BackendError(f"environment variable {self.api_key_env} is not set")
            headers["Authorization"] = f"Bearer {key}"
        body = {
            "model": self.model_id,
            "messages": messages,
            "temperature": decoding.temperature,
            "top_p": decoding.top_p,
            "max_tokens": decoding.max_new_tokens,
            **({"seed": decoding.seed} if decoding.seed is not None else {}),
            **self.extra_body,
        }
        r = httpx.post(f"{self.base_url.rstrip('/')}/chat/completions", json=body, headers=headers, timeout=self.timeout_s)
        if r.status_code != 200:
            raise BackendError(f"HTTP {r.status_code}: {r.text[:200]}")
        try:
            return r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendError(f"unexpected response shape: {str(r.json())[:200]}") from exc

    def describe(self) -> dict:
        return {"backend": self.name, "model_id": self.model_id, "base_url": self.base_url}


@dataclass
class FakeBackend:
    """Deterministic test double. Never use for results."""

    model_id: str = "fake/echo"
    fail_on: str | None = None
    name: str = "fake"
    calls: int = 0

    def generate(self, messages: list[dict], decoding: Decoding) -> str:
        self.calls += 1
        last = messages[-1]["content"]
        if self.fail_on and self.fail_on in last:
            raise BackendError("simulated failure")
        h = hashlib.sha256(f"{last}|{decoding.seed}|{decoding.temperature}".encode()).hexdigest()[:8]
        return f"[FAKE {h}] {last[:40]}"

    def describe(self) -> dict:
        return {"backend": self.name, "model_id": self.model_id, "revision": "test"}


def build_backend(spec: dict):
    kind = spec["backend"]
    kwargs = {k: v for k, v in spec.items() if k not in ("backend", "key", "role", "notes", "licence", "hf_gated")}
    if kind == "transformers":
        return TransformersBackend(**kwargs)
    if kind == "vllm":
        return VLLMBackend(**kwargs)
    if kind == "openai_compatible":
        return OpenAICompatibleBackend(**kwargs)
    if kind == "fake":
        return FakeBackend(**kwargs)
    raise ValueError(f"unknown backend {kind!r}")
