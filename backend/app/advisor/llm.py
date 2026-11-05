"""Tiny LLM provider wrapper over httpx (no SDKs). Providers are tried in settings.llm_order.

complete_json() returns (parsed JSON object, provider name), or (None, None) when no provider answered, so the
caller falls back to the rules parser. Free tiers rate-limit: one retry on 429/5xx, then a short cool-down so the
next turns skip that provider instead of waiting on it again.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

import httpx

from ..common.mask import redact
from ..config import settings
from ..contracts import LlmProviderStatus, LlmStatus

log = logging.getLogger("udyam")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
COOLDOWN_S = 30.0
RETRY_PAUSE_S = 0.6

_last: dict[str, dict[str, Any]] = {}      # provider -> {"ok": bool, "error": str | None}
_cooldown_until: dict[str, float] = {}
_active: Optional[str] = None


class ProviderError(Exception):
    def __init__(self, message: str, retryable: bool = False, status: int | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status = status


def _key(name: str) -> str:
    return {"groq": settings.groq_api_key, "gemini": settings.gemini_api_key}.get(name, "")


def _model(name: str) -> str:
    return {"groq": settings.groq_model, "gemini": settings.gemini_model}.get(name, "")


def _post(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
    try:
        r = httpx.post(url, headers=headers, json=body, timeout=settings.llm_timeout_s)
    except httpx.TimeoutException as e:
        raise ProviderError("timeout", retryable=False) from e
    except httpx.HTTPError as e:
        raise ProviderError(f"network: {type(e).__name__}", retryable=False) from e
    if r.status_code == 429 or r.status_code >= 500:
        raise ProviderError(f"HTTP {r.status_code}", retryable=True, status=r.status_code)
    if r.status_code >= 400:
        raise ProviderError(f"HTTP {r.status_code}", status=r.status_code)
    return r.json()


def _call_groq(system: str, user: str) -> str:
    body = {
        "model": settings.groq_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }
    out = _post(GROQ_URL, {"Authorization": f"Bearer {settings.groq_api_key}"}, body)
    return out["choices"][0]["message"]["content"]


def _call_gemini(system: str, user: str) -> str:
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }
    out = _post(GEMINI_URL.format(model=settings.gemini_model), {"x-goog-api-key": settings.gemini_api_key}, body)
    return out["candidates"][0]["content"]["parts"][0]["text"]


_CALLERS = {"groq": _call_groq, "gemini": _call_gemini}


def _try(name: str, system: str, user: str) -> dict[str, Any]:
    call = _CALLERS[name]
    for attempt in (1, 2):
        try:
            raw = call(system, user)
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ProviderError("not a JSON object")
            return parsed
        except ProviderError as e:
            if e.retryable and attempt == 1:
                time.sleep(RETRY_PAUSE_S)
                continue
            if e.status == 429:
                _cooldown_until[name] = time.monotonic() + COOLDOWN_S
            raise
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise ProviderError(f"bad response: {type(e).__name__}") from e
    raise ProviderError("unreachable")


def complete_json(system: str, user: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Ask each configured provider in order for a JSON object. Never raises."""
    global _active
    for name in settings.llm_order:
        if name not in _CALLERS or not _key(name):
            continue
        if _cooldown_until.get(name, 0) > time.monotonic():
            continue
        try:
            result = _try(name, system, user)
        except ProviderError as e:
            _last[name] = {"ok": False, "error": str(e)}
            log.warning("LLM %s failed: %s", name, redact(str(e)))
            continue
        _last[name] = {"ok": True, "error": None}
        _active = name
        return result, name
    return None, None


def any_configured() -> bool:
    return any(_key(n) for n in settings.llm_order if n in _CALLERS)


def status(probe: bool = False) -> LlmStatus:
    """Configured/ok per provider. With probe=True, sends each configured provider a one-line test prompt."""
    global _active
    providers = []
    names = list(dict.fromkeys([*settings.llm_order, "groq", "gemini"]))
    for name in names:
        if name not in _CALLERS:
            continue
        configured = bool(_key(name))
        if probe and configured:
            try:
                _try(name, 'Reply with the JSON object {"ok": true}.', "ping")
                _last[name] = {"ok": True, "error": None}
                _active = _active or name
            except ProviderError as e:
                _last[name] = {"ok": False, "error": str(e)}
        last = _last.get(name, {})
        providers.append(LlmProviderStatus(name=name, configured=configured, ok=last.get("ok"), model=_model(name),
                                           error=last.get("error")))
    return LlmStatus(providers=providers, active=_active if _active and _key(_active) else None)
