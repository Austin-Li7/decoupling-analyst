from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import (
    MGT470_FRAMEWORK,
    render_evidence_for_prompt,
    render_perspective_directive,
)
from mgt470_analyst.schemas.case_perspective import CasePerspective
from mgt470_analyst.schemas.company_profile import CompanyProfile
from mgt470_analyst.schemas.competitive_response import CompetitiveResponse
from mgt470_analyst.schemas.decoupling import DecouplingStrategy


def assess_competitive_response(
    profile: CompanyProfile,
    decoupling: DecouplingStrategy,
    store: EvidenceStore,
    perspective: CasePerspective | None = None,
    client: LLMClient | None = None,
    methodology_context: str = "",
) -> CompetitiveResponse:
    client = client or get_default_client()
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]
    primary = decoupling.primary_decoupling
    incumbents = (
        ", ".join(profile.competition.incumbents) if profile.competition.incumbents else "unknown"
    )
    directive = render_perspective_directive(
        perspective.perspective if perspective else None,
        perspective.primary_question if perspective else None,
    )

    system = (
        MGT470_FRAMEWORK
        + "\n\nTask: predict incumbent competitive response and assess recoupling"
        " risk. `likely_responses` should list 2-4 distinct response types with"
        " severity and defense. response_type must be one of:"
        " recouple, copy, block, subsidize, acquire, partner."
        "\n\n`recoupling_vulnerability` is the specific risk that the incumbent"
        " re-bundles the decoupled activity (via native AI, acquisition, pricing,"
        " etc.) and neutralizes the new entrant. Rate vulnerability,"
        " incumbent_capability_to_recouple, and incumbent_incentive_to_recouple as"
        " high / medium / low. Provide concrete defenses. Cite evidence_ids."
    )
    user = f"""\
{methodology_context}
{directive}
Company: {profile.company.name}
Known incumbents: {incumbents}

Primary decoupling:
- Activity: {primary.activity_to_decouple}
- From bundle: {primary.from_incumbent_bundle}
- New offering: {primary.new_offering}

Evidence:
{render_evidence_for_prompt(evidence_items)}

Produce a CompetitiveResponse.
"""
    return client.structured(
        role="smart",
        system=system,
        user=user,
        schema=CompetitiveResponse,
        context={"evidence_ids": list(store.items.keys())},
        max_tokens=4000,
    )
