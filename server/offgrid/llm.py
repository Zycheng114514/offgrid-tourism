"""The LLM port: one function the rest of the server calls, any provider behind it.

    complete_json(system, user, schema) -> dict | None

Providers (set LLM_PROVIDER):
  openai_compatible  any server speaking the OpenAI chat API: Ollama, vLLM,
                     llama.cpp, or a hosted API. Needs LLM_BASE_URL, LLM_MODEL,
                     and LLM_API_KEY if the server requires one.
  anthropic          Anthropic Messages API. Needs LLM_MODEL, LLM_API_KEY.
  simulated          no model runs; answers are looked up in a file of example
                     messages with outputs written in advance (LLM_SIMULATED_PATH).
                     Used for the demo. Messages not in the file get
                     no answer, so the server falls back to rules.
  none               no model; complete_json returns None and callers fall back
                     to rules and follow-up questions.

Standard library only, so the server runs on a bare Python install.
"""

from __future__ import annotations

import difflib
import json
import os
import pathlib
import re
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    provider: str = "none"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    timeout_s: float = 180.0
    user_suffix: str = ""  # model-specific switch, e.g. " /no_think" for Qwen3
    simulated_path: str = ""
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            provider=os.environ.get("LLM_PROVIDER", "none").strip() or "none",
            base_url=os.environ.get("LLM_BASE_URL", "").rstrip("/"),
            model=os.environ.get("LLM_MODEL", ""),
            api_key=os.environ.get("LLM_API_KEY", ""),
            timeout_s=float(os.environ.get("LLM_TIMEOUT_S", "180")),
            user_suffix=os.environ.get("LLM_USER_SUFFIX", ""),
            simulated_path=os.environ.get("LLM_SIMULATED_PATH", ""),
        )


@dataclass
class LLMResult:
    data: dict | None
    raw_text: str
    seconds: float
    error: str | None = None


def _post(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _parse_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        value = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


class LLM:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig.from_env()

    @property
    def enabled(self) -> bool:
        if self.config.provider == "simulated":
            return True
        return self.config.provider != "none" and bool(self.config.model)

    @property
    def label(self) -> str:
        return "simulated (outputs written in advance)" if self.config.provider == "simulated" else self.config.model

    def complete_json(self, system: str, user: str, schema: dict | None = None,
                      max_tokens: int = 300) -> LLMResult:
        if not self.enabled:
            return LLMResult(None, "", 0.0, "no LLM configured")
        start = time.monotonic()
        if self.config.provider == "simulated":
            return self._simulated(user)
        user = user + self.config.user_suffix
        try:
            if self.config.provider == "openai_compatible":
                text = self._openai_compatible(system, user, schema, max_tokens)
            elif self.config.provider == "anthropic":
                text = self._anthropic(system, user, schema, max_tokens)
            else:
                return LLMResult(None, "", 0.0, f"unknown provider {self.config.provider!r}")
        except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError) as exc:
            return LLMResult(None, "", time.monotonic() - start, f"{type(exc).__name__}: {exc}")
        data = _parse_json(text)
        return LLMResult(data, text, time.monotonic() - start, None if data is not None else "invalid JSON")

    def _openai_compatible(self, system: str, user: str, schema: dict | None, max_tokens: int) -> str:
        c = self.config
        headers = {"Authorization": f"Bearer {c.api_key}"} if c.api_key else {}
        payload = {
            "model": c.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
            "max_tokens": max_tokens,
            **c.extra,
        }
        if schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "result", "schema": schema, "strict": True},
            }
        try:
            body = _post(f"{c.base_url}/chat/completions", payload, headers, c.timeout_s)
        except urllib.error.HTTPError as exc:
            # Some servers reject json_schema; fall back to plain JSON mode.
            if schema is None or exc.code not in (400, 422):
                raise
            payload["response_format"] = {"type": "json_object"}
            body = _post(f"{c.base_url}/chat/completions", payload, headers, c.timeout_s)
        return body["choices"][0]["message"]["content"] or ""

    def _anthropic(self, system: str, user: str, schema: dict | None, max_tokens: int) -> str:
        c = self.config
        if schema is not None:
            system = f"{system}\n\nReply with one JSON object that matches this JSON Schema:\n{json.dumps(schema)}"
        payload = {
            "model": c.model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        headers = {"x-api-key": c.api_key, "anthropic-version": "2023-06-01"}
        body = _post(f"{c.base_url or 'https://api.anthropic.com'}/v1/messages", payload, headers, c.timeout_s)
        return "".join(part.get("text", "") for part in body["content"])

    # ---- simulated ------------------------------------------------------------

    _sim_cache: dict | None = None

    def _simulated(self, user: str) -> LLMResult:
        if self._sim_cache is None:
            path = pathlib.Path(self.config.simulated_path)
            data = json.loads(path.read_text()) if path.is_file() else {}
            items = [(i["message"], i.get("llm_output")) for i in data.get("host_examples", [])]
            items += [(i["question"], i.get("llm_output")) for i in data.get("traveller_chat_examples", [])]
            self._sim_cache = {_key(text): out for text, out in items if out}
        key = _key(user)
        if key not in self._sim_cache:
            close = difflib.get_close_matches(key, self._sim_cache.keys(), n=1, cutoff=0.92)
            if not close:
                return LLMResult(None, "", 0.0, "no simulated output for this message")
            key = close[0]
        data = self._sim_cache[key]
        return LLMResult(dict(data), json.dumps(data, ensure_ascii=False), 0.0, None)


def _key(text: str) -> str:
    """Lowercase, accents removed, letters and digits of any script kept (Chinese must not vanish)."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"[^\w]+|_", " ", text).strip()
