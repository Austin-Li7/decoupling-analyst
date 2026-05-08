"""Deterministic offline LLM responses for tests and no-API-key environments.

The fake produces minimal but schema-valid instances of every artifact model the
real modules ask for. It does NOT try to be analytically correct — its only job
is to keep the pipeline green when no API key is configured.
"""

from typing import Any, TypeVar

from pydantic import BaseModel

from mgt470_analyst.schemas.business_model import BusinessModelAnalysis
from mgt470_analyst.schemas.case_perspective import CasePerspective
from mgt470_analyst.schemas.company_profile import (
    BusinessModelInfo,
    CompanyInfo,
    CompanyProfile,
    CompetitionInfo,
    CustomersInfo,
)
from mgt470_analyst.schemas.competitive_response import (
    CompetitiveResponse,
    CompetitiveResponseItem,
    RecouplingVulnerability,
)
from mgt470_analyst.schemas.critic import CriticReview, DisciplineScore
from mgt470_analyst.schemas.cvc import CustomerActivity, CustomerValueChain
from mgt470_analyst.schemas.decoupling import DecouplingStrategy, DoNotDecouple, PrimaryDecoupling
from mgt470_analyst.schemas.final_judgment import FinalJudgment
from mgt470_analyst.schemas.lens_fit import LensFit
from mgt470_analyst.schemas.research import ResearchBrief, ResearchSource
from mgt470_analyst.schemas.value_types import ValueTypeActivity, ValueTypeDiagnosis
from mgt470_analyst.schemas.weak_links import WeakLink, WeakLinkAnalysis

T = TypeVar("T", bound=BaseModel)


def fake_response(schema: type[T], context: dict[str, Any]) -> T:
    builder = _BUILDERS.get(schema)
    if builder is None:
        raise NotImplementedError(f"No fake builder for {schema.__name__}")
    return builder(context)  # type: ignore[return-value]


def _evidence_ids(context: dict[str, Any], default: list[str] | None = None) -> list[str]:
    ids = context.get("evidence_ids")
    if isinstance(ids, list) and ids:
        return [str(item) for item in ids[:5]]
    return default or ["E1"]


def _company_name(context: dict[str, Any]) -> str:
    return str(context.get("company_name") or "the company")


def _build_research_brief(context: dict[str, Any]) -> ResearchBrief:
    name = _company_name(context)
    return ResearchBrief(
        company_name=name,
        research_summary=f"Offline-mode placeholder summary for {name}.",
        sources=[
            ResearchSource(
                id="S0",
                title="Offline placeholder",
                url_or_path="offline",
                source_type="stub",
                retrieved_at="1970-01-01",
                reliability="low",
                key_claims=["Offline mode."],
            )
        ],
        open_questions=["Connect a real research backend."],
        conflicts=[],
    )


def _build_company_profile(context: dict[str, Any]) -> CompanyProfile:
    name = _company_name(context)
    return CompanyProfile(
        company=CompanyInfo(name=name, description=f"Offline placeholder for {name}."),
        customers=CustomersInfo(),
        business_model=BusinessModelInfo(),
        competition=CompetitionInfo(),
        evidence_ids=_evidence_ids(context),
    )


def _build_case_perspective(context: dict[str, Any]) -> CasePerspective:
    return CasePerspective(
        perspective="unclear",
        confidence="low",
        reasoning="Offline placeholder case-perspective classification.",
        primary_question="Offline placeholder primary question.",
        evidence_ids=_evidence_ids(context),
    )


def _build_lens_fit(context: dict[str, Any]) -> LensFit:
    return LensFit(
        primary_type="decoupling",
        secondary_types=[],
        confidence="low",
        reasoning="Offline placeholder lens classification.",
        evidence_ids=_evidence_ids(context),
        decoupling_fit_score=0.5,
        recommended_report_mode="full_decoupling",
        caveats=["Offline mode."],
    )


def _build_cvc(context: dict[str, Any]) -> CustomerValueChain:
    name = _company_name(context)
    ev = _evidence_ids(context)
    return CustomerValueChain(
        customer_segment=f"Offline placeholder customer of {name}",
        end_activity=f"complete the job served by {name}",
        activities=[
            CustomerActivity(
                id=f"A{i}",
                step=i,
                activity=label,
                current_provider="incumbent workflow",
                customer_goal=label,
                evidence_ids=ev,
            )
            for i, label in enumerate(
                ["Discover", "Evaluate", "Choose", "Use and renew"], start=1
            )
        ],
        profile_vs_cvc_conflicts=[],
    )


def _build_value_types(context: dict[str, Any]) -> ValueTypeDiagnosis:
    activity_ids = context.get("activity_ids") or ["A1", "A2", "A3", "A4"]
    ev = _evidence_ids(context)
    rotation = ["create", "erode", "capture", "create"]
    return ValueTypeDiagnosis(
        activities=[
            ValueTypeActivity(
                activity_id=aid,
                value_type=rotation[idx % len(rotation)],  # type: ignore[arg-type]
                reasoning="Offline placeholder classification.",
                money_cost=2,
                time_cost=3,
                effort_cost=3,
                satisfaction=3,
                evidence_ids=ev,
            )
            for idx, aid in enumerate(activity_ids)
        ]
    )


def _build_weak_links(context: dict[str, Any]) -> WeakLinkAnalysis:
    activity_ids = context.get("activity_ids") or ["A2"]
    ev = _evidence_ids(context)
    return WeakLinkAnalysis(
        ranked_weak_links=[
            WeakLink(
                activity_id=activity_ids[0],
                score=216.0,
                pain_intensity=4,
                frequency=3,
                ai_or_digital_leverage=3,
                willingness_to_switch=3,
                value_capture_potential=3,
                integration_dependency=2,
                rationale="Offline placeholder weak link.",
                evidence_ids=ev,
            )
        ]
    )


def _build_decoupling(context: dict[str, Any]) -> DecouplingStrategy:
    ev = _evidence_ids(context)
    return DecouplingStrategy(
        primary_decoupling=PrimaryDecoupling(
            activity_to_decouple="Evaluate",
            from_incumbent_bundle="incumbent workflow",
            customer_pain="time and effort friction",
            new_offering="Offline placeholder decoupling.",
            why_customer_switches="Reduces customer effort.",
            cheaper_faster_easier=["faster"],
            evidence_ids=ev,
        ),
        do_not_decouple=[
            DoNotDecouple(
                activity="Use and renew",
                reason="High integration dependency.",
                evidence_ids=ev,
            )
        ],
    )


def _build_business_model(context: dict[str, Any]) -> BusinessModelAnalysis:
    ev = _evidence_ids(context)
    return BusinessModelAnalysis(
        value_creation="Offline placeholder.",
        value_capture="Offline placeholder.",
        value_erosion_remaining="Offline placeholder.",
        payer="unknown",
        pricing_model="unknown",
        cac_risks=["Unknown channel costs."],
        ltv_drivers=["Unknown frequency."],
        unit_economics_concerns=["Offline mode."],
        evidence_ids=ev,
    )


def _build_competitive(context: dict[str, Any]) -> CompetitiveResponse:
    ev = _evidence_ids(context)
    return CompetitiveResponse(
        likely_responses=[
            CompetitiveResponseItem(
                response_type="copy",
                description="Offline placeholder.",
                severity="medium",
                defense="Offline placeholder defense.",
                evidence_ids=ev,
            )
        ],
        recoupling_vulnerability=RecouplingVulnerability(
            vulnerability="medium",
            rationale="Offline placeholder.",
            incumbent_capability_to_recouple="medium",
            incumbent_incentive_to_recouple="medium",
            defenses=["Offline placeholder."],
            evidence_ids=ev,
        ),
    )


def _build_final_judgment(context: dict[str, Any]) -> FinalJudgment:
    name = _company_name(context)
    ev = _evidence_ids(context)
    return FinalJudgment(
        judgment="study_more",
        one_sentence_thesis=f"{name} offline placeholder thesis.",
        why_now="Offline mode.",
        strongest_argument="Offline placeholder.",
        biggest_risk="Offline placeholder risk.",
        staged_actions=["Offline placeholder step 1.", "Offline placeholder step 2."],
        do_not_do=["Offline placeholder don't-do item."],
        next_research_steps=["Connect a real LLM backend."],
        evidence_ids=ev,
    )


def _build_critic(context: dict[str, Any]) -> CriticReview:
    ev = _evidence_ids(context)
    disciplines = [
        "preserve_core_engine",
        "layered_evolution",
        "unit_economics",
        "explicit_dont_do",
        "moat_is_relationship",
    ]
    return CriticReview(
        overall_score=3.0,
        discipline_scores=[
            DisciplineScore(
                discipline=d,  # type: ignore[arg-type]
                score=3,
                rationale="Offline placeholder.",
            )
            for d in disciplines
        ],
        weakest_aspect="Offline placeholder.",
        citation_issues=[],
        revision_suggestions=["Offline placeholder."],
        would_disagree_with_thesis=False,
        disagreement_summary="Offline placeholder defense note.",
        evidence_ids=ev,
    )


_BUILDERS: dict[type[BaseModel], Any] = {
    ResearchBrief: _build_research_brief,
    CompanyProfile: _build_company_profile,
    CasePerspective: _build_case_perspective,
    LensFit: _build_lens_fit,
    CustomerValueChain: _build_cvc,
    ValueTypeDiagnosis: _build_value_types,
    WeakLinkAnalysis: _build_weak_links,
    DecouplingStrategy: _build_decoupling,
    BusinessModelAnalysis: _build_business_model,
    CompetitiveResponse: _build_competitive,
    FinalJudgment: _build_final_judgment,
    CriticReview: _build_critic,
}
