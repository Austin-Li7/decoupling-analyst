from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import (
    MGT470_FRAMEWORK,
    render_evidence_for_prompt,
    render_perspective_directive,
)
from mgt470_analyst.schemas.case_perspective import CasePerspective
from mgt470_analyst.schemas.company_profile import CompanyProfile
from mgt470_analyst.schemas.cvc import CustomerValueChain


def map_customer_value_chain(
    profile: CompanyProfile,
    store: EvidenceStore,
    perspective: CasePerspective | None = None,
    client: LLMClient | None = None,
    methodology_context: str = "",
) -> CustomerValueChain:
    client = client or get_default_client()
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]
    directive = render_perspective_directive(
        perspective.perspective if perspective else None,
        perspective.primary_question if perspective else None,
    )
    system = (
        MGT470_FRAMEWORK
        + "\n\nTask: map the customer value chain (CVC) for this company."
        "\n\nIMPORTANT: rebuild the CVC from the customer's perspective and the"
        " evidence — do NOT simply copy the company's marketing description of"
        " its own customers. The CVC should reflect how customers actually"
        " behave to accomplish the underlying job-to-be-done, including"
        " activities the company does not currently serve."
        "\n\nProduce 4-7 ordered activities, each with id A1..An (sequential),"
        " step (1-indexed), the customer activity (verb-led, present tense),"
        " current_provider (who serves it today — could be the target company,"
        " an incumbent, a manual workaround, or 'self'), and customer_goal."
        " Cite specific evidence_ids from the list."
        "\n\nAfter mapping, populate `profile_vs_cvc_conflicts` with any"
        " mismatches between the company profile's stated customer view and the"
        " customer behavior the CVC implies. Empty list if none."
    )
    user = f"""\
{methodology_context}
{directive}
Target company: {profile.company.name}
Stated value proposition: {profile.business_model.value_proposition}
Stated primary user (per company profile): {profile.customers.primary_user}
Stated buyer: {profile.customers.buyer}

Evidence:
{render_evidence_for_prompt(evidence_items)}

Build the CustomerValueChain.
"""
    return client.structured(
        role="smart",
        system=system,
        user=user,
        schema=CustomerValueChain,
        context={
            "company_name": profile.company.name,
            "evidence_ids": list(store.items.keys()),
        },
    )
