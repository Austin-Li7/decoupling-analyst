from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import MGT470_FRAMEWORK, render_evidence_for_prompt
from mgt470_analyst.schemas.company_profile import CompanyProfile
from mgt470_analyst.schemas.raw_input import RawInput
from mgt470_analyst.schemas.research import ResearchBrief


def build_company_profile(
    raw_input: RawInput,
    research: ResearchBrief,
    store: EvidenceStore,
    client: LLMClient | None = None,
) -> CompanyProfile:
    client = client or get_default_client()
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]
    system = (
        MGT470_FRAMEWORK
        + "\n\nTask: produce a normalized CompanyProfile from the research brief and evidence."
        " Fill every field accurately. Use 'unknown' rather than guessing if the"
        " evidence is silent."
    )
    user = f"""\
Target company: {raw_input.company_name}
Ticker: {raw_input.ticker or "(none)"}
Website: {raw_input.website or "(none)"}

Research summary:
{research.research_summary}

Available evidence (cite by id):
{render_evidence_for_prompt(evidence_items)}

Produce a CompanyProfile. The `evidence_ids` field should list the IDs you
actually used to fill the profile.
"""
    return client.structured(
        role="fast",
        system=system,
        user=user,
        schema=CompanyProfile,
        context={
            "company_name": raw_input.company_name,
            "evidence_ids": list(store.items.keys()),
        },
    )
