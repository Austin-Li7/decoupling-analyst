from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import MGT470_FRAMEWORK, render_evidence_for_prompt
from mgt470_analyst.schemas.cvc import CustomerValueChain
from mgt470_analyst.schemas.value_types import ValueTypeDiagnosis


def diagnose_value_types(
    cvc: CustomerValueChain,
    store: EvidenceStore,
    client: LLMClient | None = None,
) -> ValueTypeDiagnosis:
    client = client or get_default_client()
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]
    activities_block = "\n".join(
        f"- {a.id} (step {a.step}): {a.activity} | current provider: {a.current_provider}"
        f" | customer goal: {a.customer_goal} | evidence: {','.join(a.evidence_ids)}"
        for a in cvc.activities
    )
    system = (
        MGT470_FRAMEWORK
        + "\n\nTask: diagnose each CVC activity as value-creating, value-eroding,"
        " or value-capturing. For each activity also score, on a 1-5 scale, the"
        " customer's money cost, time cost, effort cost, and satisfaction (5 = high)."
        " Provide a 1-2 sentence reasoning anchored in the evidence."
        " activity_id MUST exactly match the input activity ids."
    )
    user = f"""\
Customer segment: {cvc.customer_segment}
End activity: {cvc.end_activity}

Activities:
{activities_block}

Evidence:
{render_evidence_for_prompt(evidence_items)}

Produce a ValueTypeDiagnosis with one entry per activity, in the same order.
"""
    return client.structured(
        role="fast",
        system=system,
        user=user,
        schema=ValueTypeDiagnosis,
        context={
            "activity_ids": [a.id for a in cvc.activities],
            "evidence_ids": list(store.items.keys()),
        },
    )
