"""Critic / review pass.

Runs after final_judgment, using either:
  - the same model with reasoning_effort="high" (default), or
  - a different model entirely (set MGT470_MODEL_CRITIC env var).

The critic reads all the upstream artifacts and the final thesis, scores the
analysis against the 5 Teixeira disciplines, flags specific citation
problems, and states whether it would disagree with the thesis under the
same evidence.

This is the cheapest, highest-leverage hallucination mitigation we have:
- forces a second pass with adversarial framing,
- catches "model talks itself into a thesis" failures,
- decoupled from the original prompt so it doesn't share priors.
"""

from __future__ import annotations

import os

from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.config import LLMConfig
from mgt470_analyst.llm.prompts import MGT470_FRAMEWORK, render_evidence_for_prompt
from mgt470_analyst.schemas.business_model import BusinessModelAnalysis
from mgt470_analyst.schemas.case_perspective import CasePerspective
from mgt470_analyst.schemas.company_profile import CompanyProfile
from mgt470_analyst.schemas.competitive_response import CompetitiveResponse
from mgt470_analyst.schemas.critic import CriticReview
from mgt470_analyst.schemas.cvc import CustomerValueChain
from mgt470_analyst.schemas.decoupling import DecouplingStrategy
from mgt470_analyst.schemas.final_judgment import FinalJudgment
from mgt470_analyst.schemas.weak_links import WeakLinkAnalysis


def review_analysis(
    profile: CompanyProfile,
    perspective: CasePerspective,
    cvc: CustomerValueChain,
    weak_links: WeakLinkAnalysis,
    decoupling: DecouplingStrategy,
    business_model: BusinessModelAnalysis,
    competitive: CompetitiveResponse,
    final_judgment: FinalJudgment,
    store: EvidenceStore,
    client: LLMClient | None = None,
) -> CriticReview:
    client = _resolve_critic_client(client)
    evidence_items = [item.model_dump(mode="json") for item in store.items.values()]

    system = (
        MGT470_FRAMEWORK
        + "\n\nYou are an ADVERSARIAL CRITIC reviewing another analyst's MGT470"
        " output. Be skeptical. The analyst is allowed to be wrong, lazy, or"
        " talked-into-a-thesis. Your job is to:"
        "\n  1. Score the analysis on each of the 5 disciplines (0-5 each)."
        "\n  2. Identify specific citation problems — places where cited"
        " evidence_ids do NOT actually support the claim made in prose, or"
        " where the cited evidence is HBS boilerplate / table headers /"
        " unrelated facts."
        "\n  3. Flag overgeneralization, hidden assumptions, and unit-"
        " economics handwaving."
        "\n  4. State plainly whether you, given the same evidence, would"
        " reach a different thesis. If yes, summarize the alternative."
        "\n\nDo NOT rubber-stamp. A score of 5 means 'world-class analyst'"
        " — most outputs should be 3-4 in their strongest dimensions and"
        " lower elsewhere."
    )

    user = f"""\
Company: {profile.company.name}
Case perspective: {perspective.perspective} (confidence {perspective.confidence})
Primary question (per analyst): {perspective.primary_question}

== Analyst's final thesis ==
Judgment: {final_judgment.judgment}
Thesis: {final_judgment.one_sentence_thesis}
Why now: {final_judgment.why_now}
Strongest argument: {final_judgment.strongest_argument}
Biggest risk: {final_judgment.biggest_risk}
Staged actions:
{_bullet(final_judgment.staged_actions)}
Do-not-do:
{_bullet(final_judgment.do_not_do)}
Cited evidence: {", ".join(final_judgment.evidence_ids)}

== Upstream artifacts ==
CVC end activity: {cvc.end_activity}
Top weak link: {weak_links.ranked_weak_links[0].activity_id}\
 score={weak_links.ranked_weak_links[0].score:.1f}\
 rationale={weak_links.ranked_weak_links[0].rationale}
Decoupling primary: {decoupling.primary_decoupling.activity_to_decouple}\
 -> {decoupling.primary_decoupling.new_offering}
Decoupling do_not_decouple count: {len(decoupling.do_not_decouple)}
Business-model value_creation: {business_model.value_creation}
Business-model value_capture: {business_model.value_capture}
Recoupling vulnerability: {competitive.recoupling_vulnerability.vulnerability}\
 / capability={competitive.recoupling_vulnerability.incumbent_capability_to_recouple}\
 / incentive={competitive.recoupling_vulnerability.incumbent_incentive_to_recouple}

== Available evidence ==
{render_evidence_for_prompt(evidence_items)}

Produce a CriticReview. Each `discipline_scores` entry MUST be one of:
preserve_core_engine, layered_evolution, unit_economics, explicit_dont_do,
moat_is_relationship. Include scores for ALL FIVE.
"""
    return client.structured(
        role="smart",
        system=system,
        user=user,
        schema=CriticReview,
        context={
            "company_name": profile.company.name,
            "evidence_ids": list(store.items.keys()),
        },
        reasoning_effort="high",
        max_tokens=5000,
    )


def _bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "(none)"


def _resolve_critic_client(default: LLMClient | None) -> LLMClient:
    """Return a client configured for the critic role.

    Selection rules:
      1. If MGT470_MODEL_CRITIC is set, build a fresh LLMClient whose
         `smart` role uses that model. This lets you point the critic at a
         different vendor / version (e.g., gpt-4o vs gpt-5.2, or even a
         non-OpenAI compatible endpoint via OPENAI_BASE_URL).
      2. Otherwise reuse the default client; we'll just bump
         reasoning_effort to "high" at call time.
    """
    override = os.getenv("MGT470_MODEL_CRITIC")
    if override:
        config = LLMConfig.from_env()
        return LLMClient(
            config=LLMConfig(
                fast=config.fast,
                smart=override,
                research=config.research,
                fast_effort=config.fast_effort,
                smart_effort="high",
                research_effort=config.research_effort,
                offline=config.offline,
            )
        )
    return default or get_default_client()
