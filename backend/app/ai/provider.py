"""LLM provider abstraction. The demo must work with no API key, so the deterministic
provider is a first-class implementation, not a stub.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from ..config import get_settings


class LLMProvider(Protocol):
    name: str
    model: str | None

    def complete_json(self, system: str, user: str) -> dict[str, Any]: ...

    def complete_text(self, system: str, user: str) -> str: ...


class DeterministicProvider:
    """Template-based synthesis over the same evidence package. Always available."""

    name = "deterministic"
    model = None

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        from .deterministic import synthesize

        return synthesize(json.loads(user))

    def complete_text(self, system: str, user: str) -> str:
        from .deterministic import answer_question

        return answer_question(user)


class OpenAIProvider:
    name = "llm:openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _chat(self, system: str, user: str, json_mode: bool) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        r = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        return json.loads(self._chat(system, user, True))

    def complete_text(self, system: str, user: str) -> str:
        return self._chat(system, user, False)


class GeminiProvider:
    name = "llm:gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model or "gemini-2.0-flash"

    def _generate(self, system: str, user: str, json_mode: bool) -> str:
        cfg: dict[str, Any] = {"temperature": 0.2}
        if json_mode:
            cfg["responseMimeType"] = "application/json"
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": cfg,
            },
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        return json.loads(self._generate(system, user, True))

    def complete_text(self, system: str, user: str) -> str:
        return self._generate(system, user, False)


def get_provider() -> LLMProvider:
    cfg = get_settings()
    if cfg.llm_provider == "openai" and cfg.openai_api_key:
        return OpenAIProvider(cfg.openai_api_key, cfg.llm_model)
    if cfg.llm_provider == "gemini" and cfg.gemini_api_key:
        return GeminiProvider(cfg.gemini_api_key, cfg.llm_model)
    return DeterministicProvider()


FALLBACK = DeterministicProvider()
