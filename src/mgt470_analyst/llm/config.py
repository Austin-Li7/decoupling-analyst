import os
from dataclasses import dataclass
from typing import Literal

ModelRole = Literal["fast", "smart", "research"]
ReasoningEffort = Literal["none", "low", "medium", "high"]

# Defaults follow OpenAI's GPT-5 family lineup. Override per-role with env vars.
# Project rationale (per Austin's recommendation 2026-05):
# - fast      → cost-optimized extraction / classification (profile, lens, values)
# - smart     → core MGT470 reasoning (cvc, weak links, decoupling, etc.)
# - research  → research synthesis adapter
DEFAULT_MODELS: dict[ModelRole, str] = {
    "fast": "gpt-5-mini",
    "smart": "gpt-5.2",
    "research": "gpt-5.2",
}

DEFAULT_REASONING: dict[ModelRole, ReasoningEffort] = {
    "fast": "low",
    "smart": "medium",
    "research": "medium",
}


@dataclass(frozen=True)
class LLMConfig:
    fast: str
    smart: str
    research: str
    fast_effort: ReasoningEffort
    smart_effort: ReasoningEffort
    research_effort: ReasoningEffort
    offline: bool

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            fast=os.getenv("MGT470_MODEL_FAST", DEFAULT_MODELS["fast"]),
            smart=os.getenv("MGT470_MODEL_SMART", DEFAULT_MODELS["smart"]),
            research=os.getenv("MGT470_MODEL_RESEARCH", DEFAULT_MODELS["research"]),
            fast_effort=_effort_env("MGT470_EFFORT_FAST", DEFAULT_REASONING["fast"]),
            smart_effort=_effort_env("MGT470_EFFORT_SMART", DEFAULT_REASONING["smart"]),
            research_effort=_effort_env("MGT470_EFFORT_RESEARCH", DEFAULT_REASONING["research"]),
            offline=_truthy(os.getenv("MGT470_OFFLINE")),
        )

    def model_for(self, role: ModelRole) -> str:
        return getattr(self, role)

    def effort_for(self, role: ModelRole) -> ReasoningEffort:
        return getattr(self, f"{role}_effort")


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _effort_env(name: str, default: ReasoningEffort) -> ReasoningEffort:
    raw = os.getenv(name, default).strip().lower()
    if raw in {"none", "low", "medium", "high"}:
        return raw  # type: ignore[return-value]
    return default
