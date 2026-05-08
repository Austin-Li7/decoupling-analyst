"""Test configuration: force the LLM client into offline mode and reset its
process-wide singleton between tests so each test gets a clean fake.
"""

from __future__ import annotations

import os

import pytest

from mgt470_analyst.llm.client import set_default_client
from mgt470_analyst.llm.config import LLMConfig


@pytest.fixture(autouse=True)
def _force_offline_llm(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MGT470_OFFLINE", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Reset the singleton so the new env vars take effect for this test.
    set_default_client(None)
    yield
    set_default_client(None)


@pytest.fixture
def offline_config() -> LLMConfig:
    """Convenience for tests that want to construct LLMClient explicitly."""
    return LLMConfig(fast="fake", smart="fake", research="fake", offline=True)


# Skip fixture-environment marker for completeness — tests that need real
# OpenAI calls should be marked @pytest.mark.live and excluded from CI.
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live: requires a real OPENAI_API_KEY")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.getenv("MGT470_RUN_LIVE") == "1":
        return
    skip_live = pytest.mark.skip(reason="live test (set MGT470_RUN_LIVE=1 to run)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
