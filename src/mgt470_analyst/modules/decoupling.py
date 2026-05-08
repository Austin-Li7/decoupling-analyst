from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import (
    MGT470_FRAMEWORK,
    render_evidence_for_prompt,
    render_perspective_directive,
)
from mgt470_analyst.schemas.case_perspective import CasePerspective
from mgt470_analyst.schemas.cvc import CustomerValueChain
from mgt470_analyst.schemas.decoupling import DecouplingStrategy
from mgt470_analyst.schemas.weak_links import WeakLinkAnalysis


def design_decoupling_strategy(
    cvc: CustomerValueChain,
    weak_links: WeakLinkAnalysis,
    store: EvidenceStore,
    perspective: CasePerspective | None = None,
    client: LLMClient | None = None,
    methodology_context: str = "",
) -> DecouplingStrategy:
    client = client or get_default_client()
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]
    directive = render_perspective_directive(
        perspective.perspective if perspective else None,
        perspective.primary_question if perspective else None,
    )

    top_n = weak_links.ranked_weak_links[:3]
    weak_block = "\n".join(
        f"- {w.activity_id} score={w.score:.1f}: {w.rationale}" for w in top_n
    )
    cvc_block = "\n".join(f"- {a.id}: {a.activity}" for a in cvc.activities)

    system = (
        MGT470_FRAMEWORK
        + "\n\nTask: design the primary decoupling strategy. Pick the single"
        " most attractive weak-link activity and describe a concrete decoupled"
        " offering that wins on cheaper / faster / easier."
        "\n\n- `activity_to_decouple`: copy the activity text (not the id)."
        "\n- `from_incumbent_bundle`: who currently bundles this activity?"
        "\n- `customer_pain`: the specific friction being removed."
        "\n- `new_offering`: a 1-2 sentence concrete product/service description."
        "\n- `why_customer_switches`: the switching argument from the customer's POV."
        "\n- `cheaper_faster_easier`: subset of [\"cheaper\", \"faster\", \"easier\"]."
        "\n- `do_not_decouple`: 2-4 activities that should NOT be unbundled."
        " Each must name the activity AND give a specific reason (damages core"
        " moat / requires capabilities the company lacks / over-extends the wedge)."
        " This list is required, not optional."
        "\n\nCite evidence_ids."
    )
    user = f"""\
{methodology_context}
{directive}
CVC:
{cvc_block}

Top-ranked weak links:
{weak_block}

Evidence:
{render_evidence_for_prompt(evidence_items)}

Produce a DecouplingStrategy.
"""
    return client.structured(
        role="smart",
        system=system,
        user=user,
        schema=DecouplingStrategy,
        context={"evidence_ids": list(store.items.keys())},
    )
