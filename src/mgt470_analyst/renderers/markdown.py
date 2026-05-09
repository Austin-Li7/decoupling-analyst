from typing import Any

from pydantic import BaseModel

from mgt470_analyst.renderers.mermaid import (
    render_cvc_flowchart,
    render_recoupling_quadrant,
    render_staged_path_flowchart,
)


def _dump(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _evidence_table(evidence_store: dict[str, Any], limit: int = 30) -> str:
    rows = [
        "| ID | Claim | Source | Locator | Confidence | Used By |",
        "|---|---|---|---|---|---|",
    ]
    items = list(evidence_store.items())
    for evidence_id, item in items[:limit]:
        claim = (item.get("claim") or "").replace("|", "\\|").replace("\n", " ")
        source_id = item.get("source_id", "")
        locator = (item.get("locator") or "").replace("|", "\\|")
        # If the locator already contains a URL, render it as a Markdown link.
        url = _extract_url(locator)
        locator_cell = f"[{locator}]({url})" if url else locator
        confidence = item.get("confidence", "")
        used_by = ", ".join(item.get("used_by_modules", []))
        rows.append(
            f"| {evidence_id} | {claim} | {source_id} | {locator_cell} |"
            f" {confidence} | {used_by} |"
        )
    if len(items) > limit:
        rows.append(f"| ... | ({len(items) - limit} more truncated) | | | | |")
    return "\n".join(rows)


def _extract_url(text: str) -> str | None:
    import re

    m = re.search(r"https?://\S+", text)
    return m.group(0).rstrip(".,;)") if m else None


def _sources_block(research: dict[str, Any], evidence_store: dict[str, Any]) -> str:
    """Render a Sources index covering every source_id referenced by evidence.

    Combines:
      - research_brief.sources (S0/S1/...) which carry url_or_path + reliability
      - synthetic file sources (F1/F2/...) minted by the deck extractor
    """
    research_sources = {s.get("id"): s for s in research.get("sources", []) if s.get("id")}
    used_source_ids: dict[str, int] = {}
    locator_for_source: dict[str, str] = {}
    for item in evidence_store.values():
        sid = item.get("source_id")
        if not sid:
            continue
        used_source_ids[sid] = used_source_ids.get(sid, 0) + 1
        if sid not in locator_for_source:
            locator_for_source[sid] = item.get("locator") or ""

    rows = [
        "| Source | Title | URL / Path | Reliability | Evidence count |",
        "|---|---|---|---|---:|",
    ]
    if not used_source_ids:
        return "_(no sources)_"

    for sid in sorted(used_source_ids):
        source = research_sources.get(sid, {})
        title = source.get("title") or _infer_title_for_synthetic_source(
            sid, locator_for_source.get(sid, "")
        )
        url_or_path = source.get("url_or_path") or _infer_url_for_synthetic_source(
            locator_for_source.get(sid, "")
        )
        reliability = source.get("reliability") or "medium"
        url_link = (
            f"[{url_or_path}]({url_or_path})"
            if url_or_path.startswith("http")
            else url_or_path or "—"
        )
        rows.append(
            f"| {sid} | {title} | {url_link} | {reliability} | {used_source_ids[sid]} |"
        )
    return "\n".join(rows)


def _infer_title_for_synthetic_source(source_id: str, locator: str) -> str:
    if source_id.startswith("F"):
        return "Local file (deck / case PDF / memo)"
    if locator:
        return locator.split(":")[0].strip()
    return f"Source {source_id}"


def _critic_block(critic: dict[str, Any]) -> str:
    if not critic:
        return "_(critic review not available)_"
    overall = critic.get("overall_score", "?")
    weakest = critic.get("weakest_aspect", "")
    rows = ["| Discipline | Score | Rationale |", "|---|---:|---|"]
    pipe_escape = "\\|"
    for d in critic.get("discipline_scores", []):
        rationale = (d.get("rationale") or "").replace("|", pipe_escape).replace("\n", " ")
        rows.append(
            f"| {d.get('discipline', '?')} | {d.get('score', '?')}/5 | {rationale} |"
        )

    citation_lines = ""
    issues = critic.get("citation_issues", [])
    if issues:
        citation_lines = "\n\n**Citation issues:**\n" + "\n".join(
            f"- _{i.get('severity', '?')}_: {i.get('issue', '')}"
            f" (cited: {', '.join(i.get('cited_evidence_ids', []))} at {i.get('location', '')})"
            for i in issues
        )

    revisions = critic.get("revision_suggestions", [])
    revision_lines = (
        "\n\n**Revision suggestions:**\n" + "\n".join(f"- {r}" for r in revisions)
        if revisions
        else ""
    )

    disagreement = critic.get("disagreement_summary", "")
    if critic.get("would_disagree_with_thesis"):
        disagree_flag = "⚠️ would disagree"
    else:
        disagree_flag = "✅ defensible"

    return (
        f"**Overall: {overall}/5** — {disagree_flag}\n\n"
        f"Weakest aspect: {weakest}\n\n"
        + "\n".join(rows)
        + citation_lines
        + revision_lines
        + (f"\n\n**Disagreement / defense note:** {disagreement}" if disagreement else "")
    )


def _infer_url_for_synthetic_source(locator: str) -> str:
    url = _extract_url(locator)
    if url:
        return url
    if ":" in locator:
        return locator.split(":", 1)[1].strip()
    return locator


def _paragraphs(text: str, limit: int | None = None) -> str:
    chunks = [chunk.strip() for chunk in str(text or "").split("\n\n") if chunk.strip()]
    if limit is not None:
        chunks = chunks[:limit]
    return "\n\n".join(chunks) if chunks else "_No text produced._"


def _first_paragraph(text: str) -> str:
    return _paragraphs(text, limit=1)


def _bullet_lines(items: list[Any], fallback: str = "- (none)") -> str:
    if not items:
        return fallback
    return "\n".join(f"- {item}" for item in items)


def _top_weak_link(context: dict[str, Any]) -> dict[str, Any]:
    weak_links = _dump(context.get("weak_links") or {})
    ranked = weak_links.get("ranked_weak_links") if isinstance(weak_links, dict) else None
    if isinstance(ranked, list) and ranked:
        return _dump(ranked[0])
    for activity in context.get("cvc", []) or []:
        if activity.get("id"):
            return {"activity_id": activity.get("id"), "rationale": context.get("weak_link", "")}
    return {}


def _activity_for_id(cvc: list[dict[str, Any]], activity_id: str | None) -> dict[str, Any]:
    if not activity_id:
        return {}
    return next((item for item in cvc if item.get("id") == activity_id), {})


def _company_snapshot_lines(company_profile: dict[str, Any], company: str) -> str:
    company_info = company_profile.get("company") or {}
    business = company_profile.get("business_model") or {}
    customers = company_profile.get("customers") or {}
    rows = [
        f"- **Company:** {company_info.get('name') or company}",
        f"- **Sector:** {company_info.get('industry') or 'unknown'}",
        f"- **Stage / geography:** {company_info.get('stage') or 'unknown'}; "
        f"{', '.join(company_info.get('geography') or []) or 'unknown'}",
        f"- **Website / ticker:** {company_info.get('website') or 'unknown'}; "
        f"{company_info.get('ticker') or 'n/a'}",
        f"- **Revenue / pricing:** {business.get('revenue_model') or 'unknown'}; "
        f"{business.get('pricing_model') or 'unknown'}",
        f"- **Primary user:** {customers.get('primary_user') or 'unknown'}",
    ]
    return "\n".join(rows)


def _raw_research_details(research: dict[str, Any]) -> str:
    summary = research.get("research_summary") or ""
    if not summary.strip():
        return "_No raw GPT Researcher narrative available._"
    indented = "\n".join(f"    {line}" for line in summary.splitlines())
    return (
        "<details>\n"
        "<summary>Raw GPT Researcher narrative (unparsed)</summary>\n\n"
        f"{indented}\n\n"
        "</details>"
    )


def _high_severity_issues(critic: dict[str, Any], limit: int = 3) -> list[str]:
    issues = [
        str(issue.get("issue", ""))
        for issue in critic.get("citation_issues", [])
        if issue.get("severity") == "high" and issue.get("issue")
    ]
    return issues[:limit]


def _cvc_rows(cvc: list[dict[str, Any]]) -> str:
    rows = ["| Step | Activity | Current Provider | Evidence |", "|---:|---|---|---|"]
    for item in cvc:
        rows.append(
            f"| {item.get('step', '')} | {item.get('activity', '')} |"
            f" {item.get('current_provider', '')} |"
            f" {', '.join(item.get('evidence_ids', []))} |"
        )
    return "\n".join(rows)


def _value_rows(values: list[dict[str, Any]]) -> str:
    rows = [
        "| Activity | Type | Money | Time | Effort | Satisfaction | Reasoning |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for v in values:
        rows.append(
            f"| {v.get('activity_id', '')} | {v.get('value_type', '')} |"
            f" {v.get('money_cost', '')} | {v.get('time_cost', '')} |"
            f" {v.get('effort_cost', '')} | {v.get('satisfaction', '')} |"
            f" {v.get('reasoning', '')} |"
        )
    return "\n".join(rows)


def _lens_block(lens_fit: dict[str, Any]) -> str:
    return (
        f"Primary lens: **{lens_fit.get('primary_type', '?')}** "
        f"(confidence: {lens_fit.get('confidence', '?')}, "
        f"fit score: {lens_fit.get('decoupling_fit_score', '?')}, "
        f"mode: {lens_fit.get('recommended_report_mode', '?')})\n\n"
        f"{lens_fit.get('reasoning', '')}"
    )


def _perspective_block(perspective: dict[str, Any]) -> str:
    return (
        f"Case perspective: **{perspective.get('perspective', '?')}** "
        f"(confidence: {perspective.get('confidence', '?')})\n\n"
        f"Primary question: {perspective.get('primary_question', '?')}\n\n"
        f"{perspective.get('reasoning', '')}"
    )


def _recoupling_block(recoupling: dict[str, Any]) -> str:
    return (
        f"**Vulnerability**: {recoupling.get('vulnerability', '?')} | "
        f"capability {recoupling.get('incumbent_capability_to_recouple', '?')}, "
        f"incentive {recoupling.get('incumbent_incentive_to_recouple', '?')}\n\n"
        f"{recoupling.get('rationale', '')}\n\n"
        f"Defenses: {', '.join(recoupling.get('defenses', []))}"
    )


def _decoupling_for_context(context: dict[str, Any]) -> dict[str, Any]:
    strategy = _dump(context.get("decoupling_strategy") or {})
    if strategy:
        return strategy
    return {
        "primary_decoupling": {
            "new_offering": context.get("decoupling", ""),
            "activity_to_decouple": "",
            "customer_pain": "",
            "why_customer_switches": "",
        }
    }


def render_report(context: dict[str, Any]) -> str:
    final = _dump(context["final_judgment"])
    lens_fit = _dump(context.get("lens_fit") or {})
    perspective = _dump(context.get("case_perspective") or {})
    critic = _dump(context.get("critic_review") or {})
    recoupling = _dump(context.get("recoupling") or {})
    research = _dump(context.get("research") or {})
    company_profile = _dump(context.get("company_profile") or {})
    decoupling_strategy = _decoupling_for_context(context)
    primary_decoupling = decoupling_strategy.get("primary_decoupling") or {}
    company = context.get("company_name", "Unknown Company")
    evidence_store = context.get("evidence_store", {})
    weak_link = context.get("weak_link", "Unknown weak link")
    decoupling = context.get("decoupling", "Focused decoupling strategy requires more evidence.")
    business_model = context.get("business_model", "Business model requires real research.")
    competitive_response = context.get(
        "competitive_response",
        "Incumbents may copy or recouple the decoupled activity.",
    )
    cvc = context.get("cvc", [])
    values = context.get("values", [])
    top_weak_link = _top_weak_link(context)
    weak_link_activity = _activity_for_id(cvc, top_weak_link.get("activity_id"))
    weak_link_id = top_weak_link.get("activity_id")

    cvc_diagram = render_cvc_flowchart(cvc, values, highlight_activity_id=weak_link_id)

    likely_responses = []
    if isinstance(context.get("competitive"), dict):
        likely_responses = context["competitive"].get("likely_responses", [])
    elif isinstance(context.get("competitive"), BaseModel):
        likely_responses = [
            r.model_dump(mode="json")
            for r in getattr(context["competitive"], "likely_responses", [])
        ]
    recoupling_diagram = render_recoupling_quadrant(likely_responses, recoupling)

    staged_diagram = render_staged_path_flowchart(final.get("staged_actions") or [])

    critic_block = _critic_block(critic)

    open_questions = research.get("open_questions") or []
    open_q_block = _bullet_lines(open_questions)

    staged_actions = final.get("staged_actions") or []
    do_not_do = final.get("do_not_do") or []
    staged_block = (
        "\n".join(f"{i}. {step}" for i, step in enumerate(staged_actions, start=1))
        if staged_actions
        else "_No staged actions produced._"
    )
    dnd_block = (
        "\n".join(f"- {item}" for item in do_not_do)
        if do_not_do
        else "_No don't-do items produced._"
    )
    high_issues = _high_severity_issues(critic)
    high_issue_block = _bullet_lines(high_issues, fallback="- No high-severity critic issues.")
    weak_label = weak_link_activity.get("activity") or weak_link_id or "Unknown activity"
    weak_step = weak_link_activity.get("step", "?")
    wedge_rationale = primary_decoupling.get("why_customer_switches") or decoupling
    next_steps = _bullet_lines(final.get("next_research_steps", []))
    tldr = final.get("recommended_action") or final.get("one_sentence_thesis", "")

    return f"""---
company: {company}
workflow: mgt470_analyst
---

# {company} MGT470 Decoupling Memo

## TL;DR

> [!important] Final Judgment
> **{final.get("judgment", "study_more")}**: {tldr}

## Key Diagram

{cvc_diagram}

_Weak link highlighted: Step {weak_step}, **{weak_label}**._

## The Wedge

{_company_snapshot_lines(company_profile, company)}

**What to decouple:** {primary_decoupling.get("activity_to_decouple") or weak_label}

**Why this wedge:** {_first_paragraph(wedge_rationale)}

**Why now:** {_first_paragraph(final.get("why_now", ""))}

**Biggest risk:** {_first_paragraph(final.get("biggest_risk", ""))}

## Confidence & Open Questions

Lens fit: **{lens_fit.get("primary_type", "?")}** with **{lens_fit.get("confidence", "?")}**
confidence and fit score **{lens_fit.get("decoupling_fit_score", "?")}**.

Top high-severity critic findings:

{high_issue_block}

Open questions:

{open_q_block}

<details>
<summary>📚 Appendix: full module outputs (click to expand)</summary>

### Lens Fit

{_lens_block(lens_fit)}

### Case Perspective

{_perspective_block(perspective)}

### Company Snapshot

{_company_snapshot_lines(company_profile, company)}

{_raw_research_details(research)}

### Customer Value Chain

{cvc_diagram}

{_cvc_rows(cvc)}

### Value Creation, Erosion, And Capture

{_value_rows(values)}

### Weak Link

{weak_link}

### Decoupling Strategy

{decoupling}

{staged_diagram}

{staged_block}

### Business Model

{business_model}

### Competitive Response

{competitive_response}

### Recoupling Risk

{recoupling_diagram}

{_recoupling_block(recoupling)}

### Critic Review

{critic_block}

### Sources

{_sources_block(research, evidence_store)}

### Evidence Base

{_evidence_table(evidence_store)}

### Final Recommendation

**{final.get("judgment", "study_more")}**: {final.get("one_sentence_thesis", "")}

Evidence: {", ".join(final.get("evidence_ids", []))}.

#### Do-Not-Do List

{dnd_block}

#### Next Research Steps

{next_steps}

</details>
"""
