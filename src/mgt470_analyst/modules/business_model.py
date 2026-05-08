from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import (
    MGT470_FRAMEWORK,
    render_evidence_for_prompt,
    render_perspective_directive,
)
from mgt470_analyst.schemas.business_model import BusinessModelAnalysis
from mgt470_analyst.schemas.case_perspective import CasePerspective
from mgt470_analyst.schemas.company_profile import CompanyProfile
from mgt470_analyst.schemas.decoupling import DecouplingStrategy


def analyze_business_model(
    profile: CompanyProfile,
    decoupling: DecouplingStrategy,
    store: EvidenceStore,
    perspective: CasePerspective | None = None,
    client: LLMClient | None = None,
) -> BusinessModelAnalysis:
    client = client or get_default_client()
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]
    primary = decoupling.primary_decoupling
    directive = render_perspective_directive(
        perspective.perspective if perspective else None,
        perspective.primary_question if perspective else None,
    )

    system = (
        MGT470_FRAMEWORK
        + "\n\nTask: judge whether the proposed decoupling strategy can become a"
        " viable business. Anchor the analysis explicitly in CAC vs CLV vs"
        " gross margin logic — even if specific numbers aren't in evidence,"
        " state the ratios that would have to hold and flag them as"
        " assumptions. List concrete CAC risks, LTV drivers, and unit-economics"
        " concerns. Cite evidence_ids."
    )
    user = f"""\
{directive}
Company: {profile.company.name}
Industry: {profile.company.industry}
Stated revenue model: {profile.business_model.revenue_model}
Stated pricing model: {profile.business_model.pricing_model}
Stated payer: {profile.customers.payer}

Primary decoupling:
- Activity: {primary.activity_to_decouple}
- New offering: {primary.new_offering}
- Why customers switch: {primary.why_customer_switches}

Evidence:
{render_evidence_for_prompt(evidence_items)}

Produce a BusinessModelAnalysis.
"""
    return client.structured(
        role="smart",
        system=system,
        user=user,
        schema=BusinessModelAnalysis,
        context={"evidence_ids": list(store.items.keys())},
    )
