from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import MGT470_FRAMEWORK, render_evidence_for_prompt
from mgt470_analyst.schemas.company_profile import CompanyProfile
from mgt470_analyst.schemas.lens_fit import LensFit


def classify_lens(
    profile: CompanyProfile,
    store: EvidenceStore,
    client: LLMClient | None = None,
) -> LensFit:
    client = client or get_default_client()
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]
    system = (
        MGT470_FRAMEWORK
        + "\n\nTask: classify which strategic lens best fits this company."
        " Decoupling is the primary lens of this workflow but it is not always"
        " the right fit. If the evidence suggests low-end disruption, new-market"
        " creation, pure tech substitution, or business-model innovation as the"
        " dominant pattern, say so honestly."
        "\n\nrecommended_report_mode rules:"
        " - 'full_decoupling' when decoupling clearly applies."
        " - 'strategic_memo' when the company is interesting but decoupling is a"
        "   secondary lens; the report should be lighter on CVC mechanics."
        " - 'financial_first' when the user mainly cares about financial quality"
        "   (public ticker + investment goal) and decoupling is incidental."
    )
    user = f"""\
Company: {profile.company.name}
Industry: {profile.company.industry}
Public/private: {profile.company.public_or_private}
Description: {profile.company.description}

Evidence:
{render_evidence_for_prompt(evidence_items)}

Produce a LensFit. decoupling_fit_score is in [0, 1].
"""
    return client.structured(
        role="fast",
        system=system,
        user=user,
        schema=LensFit,
        context={
            "company_name": profile.company.name,
            "evidence_ids": list(store.items.keys()),
        },
    )
