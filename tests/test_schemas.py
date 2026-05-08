import pytest
from pydantic import ValidationError

from mgt470_analyst.schemas.cvc import CustomerActivity, CustomerValueChain
from mgt470_analyst.schemas.evidence import EvidenceItem, EvidenceStoreArtifact
from mgt470_analyst.schemas.final_judgment import FinalJudgment
from mgt470_analyst.schemas.raw_input import RawInput
from mgt470_analyst.schemas.research import ResearchBrief, ResearchSource
from mgt470_analyst.schemas.value_types import ValueTypeActivity, ValueTypeDiagnosis


def test_core_schema_examples_accept_valid_payloads() -> None:
    raw_input = RawInput(
        analysis_goal="investment_judgment",
        company_name="Duolingo",
        ticker="DUOL",
        website="https://www.duolingo.com",
    )
    research = ResearchBrief(
        company_name="Duolingo",
        research_summary="Stub research summary generated from local input.",
        sources=[
            ResearchSource(
                id="S1",
                title="User supplied company website",
                url_or_path="https://www.duolingo.com",
                source_type="website",
                retrieved_at="2026-05-07",
                reliability="medium",
                key_claims=["Company website supplied by user."],
            )
        ],
        open_questions=["Replace stub research with cited backend research."],
        conflicts=[],
    )
    evidence = EvidenceStoreArtifact(
        root={
            "E1": EvidenceItem(
                id="E1",
                claim="Duolingo was provided as the target company by the user.",
                source_id="S0",
                locator="CLI input",
                claim_type="assumption",
                confidence="high",
                used_by_modules=["company_profile"],
            )
        }
    )
    cvc = CustomerValueChain(
        customer_segment="unknown",
        end_activity="achieve the customer goal served by the company",
        activities=[
            CustomerActivity(
                id="A1",
                step=1,
                activity="Discover available options",
                current_provider="incumbent bundle or existing behavior",
                customer_goal="Find a viable way to solve the job",
                evidence_ids=["E1"],
            )
        ],
        profile_vs_cvc_conflicts=[],
    )
    values = ValueTypeDiagnosis(
        activities=[
            ValueTypeActivity(
                activity_id="A1",
                value_type="create",
                reasoning="Discovery helps the customer begin the job.",
                money_cost=1,
                time_cost=3,
                effort_cost=3,
                satisfaction=2,
                evidence_ids=["E1"],
            )
        ]
    )
    judgment = FinalJudgment(
        judgment="study_more",
        one_sentence_thesis="The company is worth studying.",
        why_now="The workflow found a plausible weak link.",
        strongest_argument="A focused decoupling can reduce customer effort.",
        biggest_risk="Evidence is incomplete.",
        next_research_steps=["Run real cited research."],
        evidence_ids=["E1"],
    )

    assert raw_input.company_name == "Duolingo"
    assert research.sources[0].source_type == "website"
    assert evidence.root["E1"].confidence == "high"
    assert cvc.activities[0].id == "A1"
    assert values.activities[0].money_cost == 1
    assert judgment.judgment == "study_more"


def test_schema_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(
            id="E1",
            claim="claim",
            source_id="S0",
            locator="CLI",
            claim_type="assumption",
            confidence="certain",
        )


def test_schema_rejects_invalid_value_type() -> None:
    with pytest.raises(ValidationError):
        ValueTypeActivity(
            activity_id="A1",
            value_type="delight",
            reasoning="bad enum",
            money_cost=1,
            time_cost=1,
            effort_cost=1,
            satisfaction=1,
            evidence_ids=["E1"],
        )


def test_schema_rejects_out_of_range_cost_score() -> None:
    with pytest.raises(ValidationError):
        ValueTypeActivity(
            activity_id="A1",
            value_type="create",
            reasoning="bad range",
            money_cost=6,
            time_cost=1,
            effort_cost=1,
            satisfaction=1,
            evidence_ids=["E1"],
        )
