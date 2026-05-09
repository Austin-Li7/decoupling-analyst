from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import MGT470_FRAMEWORK, render_evidence_for_prompt
from mgt470_analyst.schemas.case_perspective import CasePerspective
from mgt470_analyst.schemas.company_profile import CompanyProfile
from mgt470_analyst.schemas.lens_fit import LensFit


def classify_case_perspective(
    profile: CompanyProfile,
    lens_fit: LensFit,
    store: EvidenceStore,
    client: LLMClient | None = None,
) -> CasePerspective:
    client = client or get_default_client()
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]

    system = (
        MGT470_FRAMEWORK
        + "\n\nTask: identify whose seat the analyst should sit in for this"
        " case. Three real perspectives appear in MGT470:"
        "\n  - disruptor: a new entrant or focused decoupler attacking an"
        " incumbent bundle. Examples: Tower vs Amazon, Trov vs traditional"
        " insurance, Birchbox vs department-store beauty. Question: 'what's"
        " the next decoupling move?'"
        "\n  - transitioning: a company already in market that is mid-pivot"
        " between business models. Examples: OLX (classifieds → services),"
        " Flipkart (1P retail → 3P marketplace), Zalora (subsidized growth →"
        " profitability), Wayfair (BoF acquisition → ToF). Question: 'which"
        " parts of the current model do we preserve, which do we restructure,"
        " in what order?'"
        "\n  - incumbent: a dominant player being attacked. Question: 'how do"
        " I defend or recouple?'"
        "\n  - unclear: only when evidence genuinely cannot place the case."
        "\n\nThe `primary_question` field MUST be the actual strategic"
        " question the case is asking about THIS company, not a generic"
        " 'how should they grow.' Get this right or downstream analysis will"
        " answer the wrong question."
    )
    user = f"""\
Company: {profile.company.name}
Industry: {profile.company.industry}
Public/private: {profile.company.public_or_private}
Description: {profile.company.description}
Stated value proposition: {profile.business_model.value_proposition}
Stated revenue model: {profile.business_model.revenue_model}
Known incumbents in space: {", ".join(profile.competition.incumbents) or "unknown"}
Known direct competitors: {", ".join(profile.competition.direct_competitors) or "unknown"}

Lens fit verdict: primary={lens_fit.primary_type}, fit_score={lens_fit.decoupling_fit_score}

Evidence:
{render_evidence_for_prompt(evidence_items)}

Classify the case perspective.
"""
    return client.structured(
        role="smart",
        system=system,
        user=user,
        schema=CasePerspective,
        context={
            "company_name": profile.company.name,
            "evidence_ids": list(store.items.keys()),
        },
        max_tokens=2000,
    )
