from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import (
    MGT470_FRAMEWORK,
    render_evidence_for_prompt,
    render_perspective_directive,
)
from mgt470_analyst.schemas.case_perspective import CasePerspective
from mgt470_analyst.schemas.cvc import CustomerValueChain
from mgt470_analyst.schemas.value_types import ValueTypeDiagnosis
from mgt470_analyst.schemas.weak_links import WeakLinkAnalysis


def score_weak_links(
    cvc: CustomerValueChain,
    values: ValueTypeDiagnosis,
    store: EvidenceStore,
    perspective: CasePerspective | None = None,
    client: LLMClient | None = None,
    methodology_context: str = "",
) -> WeakLinkAnalysis:
    client = client or get_default_client()
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]
    directive = render_perspective_directive(
        perspective.perspective if perspective else None,
        perspective.primary_question if perspective else None,
    )

    cvc_block = "\n".join(
        f"- {a.id}: {a.activity} (current provider: {a.current_provider})" for a in cvc.activities
    )
    values_block = "\n".join(
        f"- {v.activity_id}: value_type={v.value_type}, money={v.money_cost},"
        f" time={v.time_cost}, effort={v.effort_cost}, satisfaction={v.satisfaction}"
        for v in values.activities
    )

    system = (
        MGT470_FRAMEWORK
        + "\n\nTask: score each CVC activity as a decoupling opportunity. Use"
        " each subscore on a 1-5 scale (5 = very high). Compute the score with:"
        " score = pain_intensity * frequency * ai_or_digital_leverage *"
        " willingness_to_switch * value_capture_potential / max(integration_dependency, 1)."
        " Then sort `ranked_weak_links` by score descending."
        " Each entry MUST cite specific evidence_ids. Provide rationale."
        " activity_id MUST match an input id."
    )
    user = f"""\
{methodology_context}
{directive}
Customer segment: {cvc.customer_segment}

CVC activities:
{cvc_block}

Value-type diagnosis:
{values_block}

Evidence:
{render_evidence_for_prompt(evidence_items)}

Produce a WeakLinkAnalysis with one ranked entry per CVC activity.
"""
    return client.structured(
        role="smart",
        system=system,
        user=user,
        schema=WeakLinkAnalysis,
        context={
            "activity_ids": [a.id for a in cvc.activities],
            "evidence_ids": list(store.items.keys()),
        },
    )
