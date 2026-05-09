from __future__ import annotations

import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, ValidationError

from mgt470_analyst.llm.config import LLMConfig, ModelRole, ReasoningEffort
from mgt470_analyst.llm.fake import fake_response

if TYPE_CHECKING:
    from openai import OpenAI

T = TypeVar("T", bound=BaseModel)

# Approximate USD prices per 1M tokens. These are for cost visibility, not
# accounting; verify periodically because model pricing changes over time.
MODEL_PRICES_USD_PER_M_TOKENS: dict[str, tuple[float, float]] = {
    "gpt-5.2": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4o-mini": (0.15, 0.60),
    "o4-mini": (1.10, 4.40),
}
DEFAULT_PRICE_USD_PER_M_TOKENS = (1.25, 10.00)
GPT_RESEARCHER_COST_NOTE = (
    "GPT Researcher's own LLM calls (sub-query gen, scrape summarization, "
    "report writing)"
)
_CURRENT_COST_TRACKER: ContextVar[LLMCostTracker | None] = ContextVar(
    "mgt470_cost_tracker",
    default=None,
)
_CURRENT_MODULE: ContextVar[str | None] = ContextVar(
    "mgt470_cost_module",
    default=None,
)


class LLMError(RuntimeError):
    pass


class LLMCostTracker:
    def __init__(self, *, run_id: str, company_name: str, artifact_path: Path) -> None:
        self.run_id = run_id
        self.company_name = company_name
        self.artifact_path = artifact_path
        self.by_module: dict[str, dict[str, Any]] = {}
        self.ensure_module("gpt_researcher_internal", note=GPT_RESEARCHER_COST_NOTE)
        self.write()

    def ensure_module(
        self,
        module_name: str,
        *,
        model: str = "",
        note: str | None = None,
    ) -> dict[str, Any]:
        bucket = self.by_module.setdefault(
            module_name,
            {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
        )
        if model and not bucket.get("model"):
            bucket["model"] = model
        if note is not None:
            bucket["note"] = note
        return bucket

    def record(
        self,
        *,
        module_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        note: str | None = None,
    ) -> None:
        bucket = self.ensure_module(module_name, model=model, note=note)
        bucket["input_tokens"] += input_tokens
        bucket["output_tokens"] += output_tokens
        bucket["cost_usd"] = round(bucket["cost_usd"] + cost_usd, 6)
        self.write()

    def to_json(self) -> dict[str, Any]:
        total_input = sum(bucket["input_tokens"] for bucket in self.by_module.values())
        total_output = sum(bucket["output_tokens"] for bucket in self.by_module.values())
        total_cost = round(sum(bucket["cost_usd"] for bucket in self.by_module.values()), 6)
        return {
            "run_id": self.run_id,
            "company_name": self.company_name,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": total_cost,
            "by_module": {
                module: {
                    **bucket,
                    "cost_usd": round(bucket["cost_usd"], 6),
                }
                for module, bucket in sorted(self.by_module.items())
            },
            "notes": [
                "Costs computed from per-call usage objects. GPT Researcher "
                "internal cost is read from researcher.research_costs after run.",
                "Embedding/RAG costs outside LLMClient are not captured in this artifact.",
            ],
        }

    def write(self) -> None:
        self.artifact_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_path.write_text(
            json.dumps(self.to_json(), indent=2) + "\n",
            encoding="utf-8",
        )


def estimate_llm_cost_usd(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
) -> float:
    input_price, output_price = MODEL_PRICES_USD_PER_M_TOKENS.get(
        model,
        DEFAULT_PRICE_USD_PER_M_TOKENS,
    )
    return round(
        (input_tokens / 1_000_000 * input_price)
        + (output_tokens / 1_000_000 * output_price),
        6,
    )


def start_llm_cost_tracking(
    *,
    run_id: str,
    company_name: str,
    artifact_path: Path,
) -> LLMCostTracker:
    tracker = LLMCostTracker(
        run_id=run_id,
        company_name=company_name,
        artifact_path=artifact_path,
    )
    _CURRENT_COST_TRACKER.set(tracker)
    return tracker


def finish_llm_cost_tracking() -> None:
    tracker = _CURRENT_COST_TRACKER.get()
    if tracker is not None:
        tracker.write()
    _CURRENT_COST_TRACKER.set(None)


@contextmanager
def use_llm_module(module_name: str):
    tracker = _CURRENT_COST_TRACKER.get()
    if tracker is not None:
        tracker.ensure_module(module_name)
    token = _CURRENT_MODULE.set(module_name)
    try:
        yield
    finally:
        _CURRENT_MODULE.reset(token)


def record_external_llm_cost(
    module_name: str,
    *,
    cost_usd: float,
    model: str = "",
    note: str | None = None,
) -> None:
    tracker = _CURRENT_COST_TRACKER.get()
    if tracker is None:
        return
    tracker.record(
        module_name=module_name,
        model=model,
        input_tokens=0,
        output_tokens=0,
        cost_usd=cost_usd,
        note=note,
    )


def _usage_tokens(usage: Any) -> tuple[int, int]:
    if usage is None:
        return 0, 0
    if isinstance(usage, dict):
        return int(usage.get("prompt_tokens") or 0), int(
            usage.get("completion_tokens") or 0
        )
    return int(getattr(usage, "prompt_tokens", 0) or 0), int(
        getattr(usage, "completion_tokens", 0) or 0
    )


def _record_response_usage(*, model: str, response: Any) -> None:
    tracker = _CURRENT_COST_TRACKER.get()
    if tracker is None:
        return
    input_tokens, output_tokens = _usage_tokens(getattr(response, "usage", None))
    if input_tokens == 0 and output_tokens == 0:
        return
    module_name = _CURRENT_MODULE.get() or "unattributed"
    tracker.record(
        module_name=module_name,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=estimate_llm_cost_usd(
            model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
    )


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
        max_tokens: int | None = None,
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
        if max_tokens is not None:
            kwargs["max_completion_tokens"] = max_tokens

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(**kwargs)
            except TypeError:
                # Older OpenAI SDK or model rejecting reasoning_effort.
                kwargs.pop("reasoning_effort", None)
                kwargs.pop("max_completion_tokens", None)
                response = client.chat.completions.create(**kwargs)
            _record_response_usage(model=model, response=response)
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

    def text(
        self,
        *,
        role: ModelRole,
        system: str,
        user: str,
        temperature: float | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        max_tokens: int | None = None,
    ) -> str:
        if self._effective_offline:
            return user.split("MARKDOWN:\n", maxsplit=1)[-1]

        client = self._ensure_client()
        model = self.config.model_for(role)
        effort = reasoning_effort or self.config.effort_for(role)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if effort and effort != "none":
            kwargs["reasoning_effort"] = effort
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_completion_tokens"] = max_tokens

        try:
            response = client.chat.completions.create(**kwargs)
        except TypeError:
            kwargs.pop("reasoning_effort", None)
            kwargs.pop("max_completion_tokens", None)
            response = client.chat.completions.create(**kwargs)
        _record_response_usage(model=model, response=response)
        return response.choices[0].message.content or ""


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
