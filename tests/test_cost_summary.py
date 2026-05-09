import json
from pathlib import Path
from types import SimpleNamespace

from mgt470_analyst.llm.client import (
    LLMClient,
    estimate_llm_cost_usd,
    finish_llm_cost_tracking,
    start_llm_cost_tracking,
    use_llm_module,
)
from mgt470_analyst.llm.config import LLMConfig
from mgt470_analyst.schemas.research import ResearchBrief, ResearchSource


class _FakeChatCompletions:
    def __init__(self, responses: list[object]) -> None:
        self._responses = responses

    def create(self, **kwargs):
        return self._responses.pop(0)


class _FakeOpenAI:
    def __init__(self, responses: list[object]) -> None:
        self.chat = SimpleNamespace(completions=_FakeChatCompletions(responses))


def _response(input_tokens: int, output_tokens: int) -> object:
    content = ResearchBrief(
        company_name="Acme",
        research_summary="Synthetic summary.",
        sources=[
            ResearchSource(
                id="S1",
                title="Synthetic source",
                url_or_path="https://example.com",
                source_type="article",
                retrieved_at="2026-05-09",
                reliability="medium",
                key_claims=["Synthetic claim."],
            )
        ],
        open_questions=[],
        conflicts=[],
    ).model_dump_json()
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        ),
    )


def test_cost_summary_written_with_correct_total(tmp_path: Path) -> None:
    client = LLMClient(
        LLMConfig(
            fast="gpt-4o-mini",
            smart="gpt-4o-mini",
            research="gpt-4o-mini",
            fast_effort="low",
            smart_effort="medium",
            research_effort="medium",
            offline=False,
        ),
        api_key="sk-test",
    )
    client._client = _FakeOpenAI(  # type: ignore[assignment]
        [
            _response(100, 20),
            _response(200, 30),
            _response(50, 10),
        ]
    )
    artifact_path = tmp_path / "cost_summary.json"

    start_llm_cost_tracking(
        run_id="acme-20260509-120000",
        company_name="Acme",
        artifact_path=artifact_path,
    )
    with use_llm_module("company_profile"):
        client.structured(
            role="fast",
            system="system",
            user="user",
            schema=ResearchBrief,
        )
    with use_llm_module("company_profile"):
        client.structured(
            role="fast",
            system="system",
            user="user",
            schema=ResearchBrief,
        )
    with use_llm_module("lens_fit"):
        client.structured(
            role="fast",
            system="system",
            user="user",
            schema=ResearchBrief,
        )
    finish_llm_cost_tracking()

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    expected_cost = (
        estimate_llm_cost_usd("gpt-4o-mini", input_tokens=350, output_tokens=60)
    )
    assert artifact["run_id"] == "acme-20260509-120000"
    assert artifact["company_name"] == "Acme"
    assert artifact["total_input_tokens"] == 350
    assert artifact["total_output_tokens"] == 60
    assert artifact["total_cost_usd"] == expected_cost
    assert artifact["by_module"]["company_profile"]["input_tokens"] == 300
    assert artifact["by_module"]["company_profile"]["output_tokens"] == 50
    assert artifact["by_module"]["lens_fit"]["input_tokens"] == 50
    assert artifact["by_module"]["gpt_researcher_internal"]["note"].startswith(
        "GPT Researcher's own LLM calls"
    )
