import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from mgt470_analyst.adapters.research.base import ResearchAdapter
from mgt470_analyst.adapters.research.gpt_researcher_adapter import GPTResearcherAdapter
from mgt470_analyst.adapters.research.openai_research import OpenAIResearchAdapter
from mgt470_analyst.evidence.store import EvidenceStore
from mgt470_analyst.evidence.validator import validate_and_repair_evidence
from mgt470_analyst.hashing import stable_hash
from mgt470_analyst.io.json_artifacts import write_json_artifact
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import render_methodology_context
from mgt470_analyst.modules.business_model import analyze_business_model
from mgt470_analyst.modules.case_perspective import classify_case_perspective
from mgt470_analyst.modules.company_profile import build_company_profile
from mgt470_analyst.modules.competitive_response import assess_competitive_response
from mgt470_analyst.modules.critic import review_analysis
from mgt470_analyst.modules.cvc import map_customer_value_chain
from mgt470_analyst.modules.deck_extractor import extract_deck_claims
from mgt470_analyst.modules.decoupling import design_decoupling_strategy
from mgt470_analyst.modules.final_judgment import make_final_judgment
from mgt470_analyst.modules.lens_fit import classify_lens
from mgt470_analyst.modules.value_types import diagnose_value_types
from mgt470_analyst.modules.weak_links import score_weak_links
from mgt470_analyst.paths import ensure_run_dir
from mgt470_analyst.renderers.markdown import render_report
from mgt470_analyst.schemas.business_model import BusinessModelAnalysis
from mgt470_analyst.schemas.case_perspective import CasePerspective
from mgt470_analyst.schemas.company_profile import CompanyProfile
from mgt470_analyst.schemas.competitive_response import CompetitiveResponse
from mgt470_analyst.schemas.critic import CriticReview
from mgt470_analyst.schemas.cvc import CustomerValueChain
from mgt470_analyst.schemas.deck_claims import DeckClaims
from mgt470_analyst.schemas.decoupling import DecouplingStrategy
from mgt470_analyst.schemas.final_judgment import FinalJudgment
from mgt470_analyst.schemas.lens_fit import LensFit
from mgt470_analyst.schemas.raw_input import RawInput
from mgt470_analyst.schemas.run import ModuleRun, RunManifest
from mgt470_analyst.schemas.value_types import ValueTypeDiagnosis
from mgt470_analyst.schemas.weak_links import WeakLinkAnalysis

ARTIFACTS = {
    "research_brief": "research_brief.json",
    "evidence_store": "evidence_store.json",
    "company_profile": "company_profile.json",
    "lens_fit": "lens_fit.json",
    "case_perspective": "case_perspective.json",
    "cvc": "cvc.json",
    "value_type_diagnosis": "value_type_diagnosis.json",
    "weak_link_analysis": "weak_link_analysis.json",
    "decoupling_strategy": "decoupling_strategy.json",
    "business_model_analysis": "business_model_analysis.json",
    "competitive_response": "competitive_response.json",
    "final_judgment": "final_judgment.json",
    "critic_review": "critic_review.json",
    "final_report": "final_report.md",
}

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class AnalysisResult:
    run_dir: Path
    report_path: Path
    run_manifest: RunManifest


def _truthy_env(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _select_research_adapter(client: LLMClient) -> ResearchAdapter:
    backend = os.getenv("MGT470_RESEARCH_BACKEND", "").strip().lower()
    offline = _truthy_env(os.getenv("MGT470_OFFLINE"))

    if offline or backend == "stub":
        return OpenAIResearchAdapter(client=client)

    if backend in {"gpt_researcher", "gpt-researcher"}:
        return GPTResearcherAdapter()

    if backend:
        raise ValueError(
            "Unsupported MGT470_RESEARCH_BACKEND. Use 'gpt_researcher' or 'stub'."
        )

    if os.getenv("OPENAI_API_KEY"):
        return GPTResearcherAdapter()

    return OpenAIResearchAdapter(client=client)


def run_analysis(
    raw_input: RawInput,
    runs_dir: Path | str,
    client: LLMClient | None = None,
    *,
    use_rag: bool = True,
) -> AnalysisResult:
    runs_path = Path(runs_dir)
    run_id, run_dir = ensure_run_dir(runs_path, raw_input.company_name)
    client = client or get_default_client()

    retriever = _build_retriever_or_none(use_rag=use_rag, client=client)

    def methodology_for(module_name: str, perspective: str | None = None) -> str:
        if retriever is None:
            return ""
        chunks = retriever.retrieve_for_module(
            module_name=module_name,
            company_name=raw_input.company_name,
            perspective=perspective,
        )
        return render_methodology_context(chunks)
    manifest = RunManifest(
        run_id=run_id,
        created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        input=raw_input,
        artifacts=ARTIFACTS.copy(),
    )

    def write_manifest() -> None:
        write_json_artifact(run_dir / "run.json", manifest)

    def record(
        module: str,
        output_path: str,
        module_input: Any,
        status: str = "ok",
        error: str | None = None,
    ) -> None:
        manifest.modules.append(
            ModuleRun(
                module=module,
                input_hash=stable_hash(module_input),
                output_path=output_path,
                status=status,  # type: ignore[arg-type]
                error=error,
            )
        )
        write_manifest()

    def validate(
        artifact: ModelT,
        model_type: type[ModelT],
        module_name: str,
        file_name: str,
    ) -> ModelT:
        repaired, result = validate_and_repair_evidence(artifact, store, module_name)
        if result.ok:
            return model_type.model_validate(repaired)
        error_path = f"{Path(file_name).stem}.error.json"
        write_json_artifact(
            run_dir / error_path,
            {"module": module_name, "missing_ids": result.missing_ids},
        )
        record(
            module_name,
            error_path,
            artifact,
            status="error",
            error=f"Invalid evidence IDs: {result.missing_ids}",
        )
        raise RuntimeError(f"{module_name} has invalid evidence IDs: {result.missing_ids}")

    def step(
        module_name: str,
        file_name: str,
        producer,
        schema: type[ModelT],
        input_for_hash: Any,
    ) -> ModelT:
        artifact = producer()
        validated = validate(artifact, schema, module_name, file_name)
        write_json_artifact(run_dir / file_name, validated)
        write_json_artifact(run_dir / "evidence_store.json", store.to_artifact())
        record(module_name, file_name, input_for_hash)
        return validated

    write_manifest()

    # --- Phase 1: build the evidence base ---
    store = EvidenceStore.from_raw_input(raw_input)

    deck_artifacts = extract_deck_claims(raw_input.files, store)
    for index, deck_artifact in enumerate(deck_artifacts, start=1):
        path = "deck_claims.json" if index == 1 else f"deck_claims_{index}.json"
        deck_artifact = validate(deck_artifact, DeckClaims, "deck_extractor", path)
        write_json_artifact(run_dir / path, deck_artifact)
        record("deck_extractor", path, raw_input.files)

    research = _select_research_adapter(client=client).research(raw_input)
    write_json_artifact(run_dir / "research_brief.json", research)
    record("research", "research_brief.json", raw_input)

    # Pipe each research-source key_claim into the evidence store so downstream
    # modules can cite them by E-id rather than dangling S-ids in prose.
    for source in research.sources:
        for claim_text in source.key_claims:
            store.add_claim(
                claim=claim_text,
                source_id=source.id,
                locator=f"{source.source_type}: {source.url_or_path}",
                claim_type="qualitative",
                confidence=source.reliability,
            )

    write_json_artifact(run_dir / "evidence_store.json", store.to_artifact())
    record("evidence_store", "evidence_store.json", {"raw": raw_input, "research": research})

    # --- Phase 2: framework analysis ---
    company_profile = step(
        "company_profile",
        "company_profile.json",
        lambda: build_company_profile(raw_input, research, store, client=client),
        CompanyProfile,
        {"raw_input": raw_input, "research": research},
    )

    lens_fit = step(
        "lens_fit",
        "lens_fit.json",
        lambda: classify_lens(company_profile, store, client=client),
        LensFit,
        company_profile,
    )

    case_perspective = step(
        "case_perspective",
        "case_perspective.json",
        lambda: classify_case_perspective(company_profile, lens_fit, store, client=client),
        CasePerspective,
        {"profile": company_profile, "lens_fit": lens_fit},
    )

    cvc = step(
        "cvc",
        "cvc.json",
        lambda: map_customer_value_chain(
            company_profile,
            store,
            perspective=case_perspective,
            client=client,
            methodology_context=methodology_for("cvc", case_perspective.perspective),
        ),
        CustomerValueChain,
        {"profile": company_profile, "perspective": case_perspective},
    )

    values = step(
        "value_types",
        "value_type_diagnosis.json",
        lambda: diagnose_value_types(cvc, store, client=client),
        ValueTypeDiagnosis,
        cvc,
    )

    weak_links = step(
        "weak_links",
        "weak_link_analysis.json",
        lambda: score_weak_links(
            cvc,
            values,
            store,
            perspective=case_perspective,
            client=client,
            methodology_context=methodology_for("weak_links", case_perspective.perspective),
        ),
        WeakLinkAnalysis,
        {"cvc": cvc, "values": values, "perspective": case_perspective},
    )

    decoupling = step(
        "decoupling",
        "decoupling_strategy.json",
        lambda: design_decoupling_strategy(
            cvc,
            weak_links,
            store,
            perspective=case_perspective,
            client=client,
            methodology_context=methodology_for("decoupling", case_perspective.perspective),
        ),
        DecouplingStrategy,
        {"cvc": cvc, "weak_links": weak_links, "perspective": case_perspective},
    )

    business_model = step(
        "business_model",
        "business_model_analysis.json",
        lambda: analyze_business_model(
            company_profile,
            decoupling,
            store,
            perspective=case_perspective,
            client=client,
            methodology_context=methodology_for("business_model", case_perspective.perspective),
        ),
        BusinessModelAnalysis,
        {"profile": company_profile, "decoupling": decoupling, "perspective": case_perspective},
    )

    competitive = step(
        "competitive_response",
        "competitive_response.json",
        lambda: assess_competitive_response(
            company_profile,
            decoupling,
            store,
            perspective=case_perspective,
            client=client,
            methodology_context=methodology_for(
                "competitive_response", case_perspective.perspective
            ),
        ),
        CompetitiveResponse,
        {"profile": company_profile, "decoupling": decoupling, "perspective": case_perspective},
    )

    final_judgment = step(
        "final_judgment",
        "final_judgment.json",
        lambda: make_final_judgment(
            company_profile,
            lens_fit,
            weak_links,
            decoupling,
            business_model,
            competitive,
            store,
            perspective=case_perspective,
            client=client,
            methodology_context=methodology_for("final_judgment", case_perspective.perspective),
        ),
        FinalJudgment,
        {
            "profile": company_profile,
            "weak_links": weak_links,
            "decoupling": decoupling,
            "business_model": business_model,
            "competitive": competitive,
        },
    )

    critic_review = step(
        "critic",
        "critic_review.json",
        lambda: review_analysis(
            company_profile,
            case_perspective,
            cvc,
            weak_links,
            decoupling,
            business_model,
            competitive,
            final_judgment,
            store,
            client=client,
        ),
        CriticReview,
        {"final_judgment": final_judgment},
    )

    # --- Phase 3: render ---
    report = render_report(
        {
            "company_name": raw_input.company_name,
            "lens_fit": lens_fit,
            "case_perspective": case_perspective,
            "final_judgment": final_judgment,
            "critic_review": critic_review,
            "evidence_store": store.to_artifact().model_dump(mode="json"),
            "weak_link": _weak_link_summary(weak_links, cvc),
            "decoupling": decoupling.primary_decoupling.new_offering,
            "business_model": business_model.value_creation,
            "competitive_response": competitive.likely_responses[0].description,
            "competitive": competitive,
            "recoupling": competitive.recoupling_vulnerability,
            "cvc": [activity.model_dump(mode="json") for activity in cvc.activities],
            "values": [v.model_dump(mode="json") for v in values.activities],
            "research": research,
        }
    )
    report_path = run_dir / "final_report.md"
    report_path.write_text(report, encoding="utf-8")
    record(
        "markdown_renderer",
        "final_report.md",
        {"final_judgment": final_judgment, "evidence_store": store.to_artifact()},
    )

    return AnalysisResult(run_dir=run_dir, report_path=report_path, run_manifest=manifest)


def _build_retriever_or_none(*, use_rag: bool, client: LLMClient):
    """Construct a MethodologyRetriever when RAG is enabled and the client
    has a real API key. Returns ``None`` otherwise so module calls receive
    an empty methodology context and behave identically to pre-RAG runs.

    RAG is gated on ``MGT470_RAG=1`` so the default behavior is unchanged
    until the user opts in via env var or by running ``mgt470 reindex``.
    Tests force offline mode, which trips the ``client.offline`` check.
    """
    if not use_rag:
        return None
    if os.environ.get("MGT470_RAG") != "1":
        return None
    if getattr(client, "offline", False):
        return None
    try:
        from mgt470_analyst.rag.retriever import MethodologyRetriever

        return MethodologyRetriever()
    except Exception:
        return None


def _weak_link_summary(weak_links: WeakLinkAnalysis, cvc: CustomerValueChain) -> str:
    top = weak_links.ranked_weak_links[0]
    activity = next((item for item in cvc.activities if item.id == top.activity_id), None)
    label = activity.activity if activity else top.activity_id
    return f"{label} scored {top.score:.1f}: {top.rationale}"
