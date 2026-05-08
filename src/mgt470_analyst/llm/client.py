from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, ValidationError

from mgt470_analyst.llm.config import LLMConfig, ModelRole, ReasoningEffort
from mgt470_analyst.llm.fake import fake_response

if TYPE_CHECKING:
    from openai import OpenAI

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Thin wrapper around OpenAI's chat completions API.

    Modules call ``structured(role, system, user, schema)`` and get back a
    validated pydantic instance. When ``config.offline`` is set or no API key
    is available, the client returns deterministic fakes from
    :mod:`mgt470_analyst.llm.fake`.

    The wrapper:
    - Routes (model, reasoning_effort) by role per :class:`LLMConfig`.
    - Asks for ``response_format=json_object`` and embeds the JSON schema in
      the system prompt so the model knows what shape to emit.
    - Retries once on JSON / validation failure before raising.
    """

    def __init__(self, config: LLMConfig | None = None, api_key: str | None = None) -> None:
        self.config = config or LLMConfig.from_env()
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client: OpenAI | None = None
        # Auto-fall back to offline mode when no key is configured. Keeps
        # tests and dry runs green.
        self._effective_offline = self.config.offline or not self._api_key

    @property
    def offline(self) -> bool:
        return self._effective_offline

    def _ensure_client(self) -> OpenAI:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise LLMError(
                "OPENAI_API_KEY is not set. Put it in .env at the project root, "
                "or export it before running. See README for details."
            )
        from openai import OpenAI

        self._client = OpenAI(api_key=self._api_key)
        return self._client

    def structured(
        self,
        *,
        role: ModelRole,
        system: str,
        user: str,
        schema: type[T],
        context: dict[str, Any] | None = None,
        temperature: float | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        max_retries: int = 1,
    ) -> T:
        if self._effective_offline:
            return fake_response(schema, context or {})

        client = self._ensure_client()
        model = self.config.model_for(role)
        effort = reasoning_effort or self.config.effort_for(role)

        json_schema = schema.model_json_schema()
        instructions = (
            "Return a single JSON object that conforms to the following JSON schema. "
            "Do not include any prose outside the JSON.\n\nSCHEMA:\n"
            + json.dumps(json_schema)
        )
        full_system = f"{system}\n\n{instructions}"

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": full_system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        # gpt-5 family accepts reasoning_effort. gpt-4o-style models silently
        # ignore unknown kwargs in chat.completions, but to be safe we only
        # pass it when explicitly set to a non-"none" value.
        if effort and effort != "none":
            kwargs["reasoning_effort"] = effort
        if temperature is not None:
            kwargs["temperature"] = temperature

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(**kwargs)
            except TypeError:
                # Older OpenAI SDK or model rejecting reasoning_effort.
                kwargs.pop("reasoning_effort", None)
                response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or "{}"
            try:
                data = json.loads(content)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                if attempt < max_retries:
                    continue
        raise LLMError(
            f"Model output failed validation after {max_retries + 1} attempts: {last_error}"
        )


_default_client: LLMClient | None = None


def get_default_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def set_default_client(client: LLMClient | None) -> None:
    """Override the process-wide LLM client. Tests use this to swap in fakes."""
    global _default_client
    _default_client = client
