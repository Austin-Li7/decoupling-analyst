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
from mgt470_analyst.schemas.competitive_response import CompetitiveResponse
from mgt470_analyst.schemas.decoupling import DecouplingStrategy
from mgt470_analyst.schemas.final_judgment import FinalJudgment
from mgt470_analyst.schemas.lens_fit import LensFit
from mgt470_analyst.schemas.weak_links import WeakLinkAnalysis


def make_final_judgment(
    profile: CompanyProfile,
    lens_fit: LensFit,
    weak_links: WeakLinkAnalysis,
    decoupling: DecouplingStrategy,
    business_model: BusinessModelAnalysis,
    competitive: CompetitiveResponse,
    store: EvidenceStore,
    perspective: CasePerspective | None = None,
    client: LLMClient | None = None,
    methodology_context: str = "",
) -> FinalJudgment:
    client = client or get_default_client()
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]
    directive = render_perspective_directive(
        perspective.perspective if perspective else None,
        perspective.primary_question if perspective else None,
    )

    system = (
        MGT470_FRAMEWORK
        + "\n\nTask: produce the user's actual decision output. judgment must"
        " be one of: study_more, invest_watchlist, avoid, startup_opportunity,"
        " unclear. Pick `invest_watchlist` only if the analysis materially"
        " supports it; default to `study_more` when evidence is thin."
        "\n\nThis output is the deliverable, so the discipline rules apply"
        " here MORE strictly than anywhere else:"
        "\n- `staged_actions` (3-6 items) MUST be a sequenced execution path."
        " For transitioning companies, this is the layered evolution: light"
        " moves first (matching/data/trust), medium next (intermediation),"
        " heavy last (full payments/logistics) — and only if earned. Step"
        " N+1 should depend on step N landing. Avoid generic 'do market"
        " research' filler."
        "\n- `do_not_do` (2-4 items) MUST name attractive-looking actions to"
        " AVOID, with reasons. Examples: 'do not enter jobs vertical because"
        " it dilutes the classifieds brand and demands cold-start supply';"
        " 'do not subsidize shipping further because it has been the unit-"
        " economics killer'. Generic 'avoid scope creep' is not acceptable."
        "\n- Cite evidence_ids that anchor the thesis."
    )
    top = weak_links.ranked_weak_links[0]
    primary = decoupling.primary_decoupling
    user = f"""\
{methodology_context}
{directive}
Company: {profile.company.name}
Public/private: {profile.company.public_or_private}, ticker: {profile.company.ticker or "n/a"}
Lens fit: primary={lens_fit.primary_type},\
 decoupling_fit={lens_fit.decoupling_fit_score},\
 mode={lens_fit.recommended_report_mode}

Top weak link: {top.activity_id} score={top.score:.1f}
Decoupling: {primary.activity_to_decouple} -> {primary.new_offering}
Business model take: {business_model.value_creation}
  capture: {business_model.value_capture}
Recoupling vulnerability: {competitive.recoupling_vulnerability.vulnerability}

Evidence:
{render_evidence_for_prompt(evidence_items)}

Produce a FinalJudgment.
"""
    return client.structured(
        role="smart",
        system=system,
        user=user,
        schema=FinalJudgment,
        context={
            "company_name": profile.company.name,
            "evidence_ids": list(store.items.keys()),
        },
    )
