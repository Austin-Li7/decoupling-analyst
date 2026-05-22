from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

VALUE_TYPE_STYLE = {
    "create": "create",
    "erode": "erode",
    "capture": "capture",
}


def load_portfolio_data(root: Path = ROOT) -> dict[str, Any]:
    scores = _read_json(root / "cases" / "calibration" / "SCORES.json")
    birchbox_dir = root / "cases" / "calibration" / "birchbox" / "system_run"
    weak_links = _read_json(birchbox_dir / "weak_link_analysis.json")["ranked_weak_links"]
    featured_case = {
        "slug": "birchbox",
        "company": "Birchbox",
        "score": _case_score(scores, "birchbox"),
        "cvc": _read_json(birchbox_dir / "cvc.json")["activities"],
        "values": _read_json(birchbox_dir / "value_type_diagnosis.json")["activities"],
        "top_weak_link": weak_links[0],
        "decoupling": _read_json(birchbox_dir / "decoupling_strategy.json"),
        "final_judgment": _read_json(birchbox_dir / "final_judgment.json"),
        "evidence_store": _read_json(birchbox_dir / "evidence_store.json"),
        "provenance": _read_json(birchbox_dir / "research_provenance.json"),
        "cost_summary": _read_json(birchbox_dir / "cost_summary.json"),
        "final_report": (birchbox_dir / "final_report.md").read_text(encoding="utf-8"),
        "final_report_zh": (birchbox_dir / "final_report_zh.md").read_text(encoding="utf-8"),
    }
    return {
        "aggregate": scores["aggregate"],
        "cases": scores["cases"],
        "featured_case": featured_case,
    }


def render_cvc_html(featured_case: dict[str, Any]) -> str:
    values = {
        item.get("activity_id"): item.get("value_type", "")
        for item in featured_case["values"]
    }
    highlight_id = featured_case["top_weak_link"]["activity_id"]
    activities = sorted(featured_case["cvc"], key=lambda item: item.get("step", 0))
    nodes: list[str] = []
    for activity in activities:
        value_class = VALUE_TYPE_STYLE.get(
            str(values.get(activity.get("id"), "")).lower(),
            "neutral",
        )
        weak_class = " weak" if activity.get("id") == highlight_id else ""
        nodes.append(
            f'<div class="flow-node {value_class}{weak_class}">'
            f'<div class="flow-step">Step {html.escape(str(activity.get("step", "?")))}</div>'
            f'<div class="flow-title">{html.escape(activity.get("activity", ""))}</div>'
            f'<div class="flow-provider">{html.escape(activity.get("current_provider", ""))}</div>'
            "</div>"
        )
    return '<div class="flow-scroller"><div class="flow">' + "".join(nodes) + "</div></div>"


def render_architecture_html() -> str:
    steps = [
        ("Input", "company, URL, ticker, PDF, notes"),
        ("Grounded retrieval", "Tavily search with visited source URLs"),
        ("Teixeira corpus RAG", "course notes and primary sources"),
        ("Grounding gate", "refuse empty retrieval before report writing"),
        ("14 typed modules", "Pydantic artifacts for each reasoning step"),
        ("Reports + audit files", "English/Chinese reports, evidence, provenance, cost"),
    ]
    cards = "".join(
        f'<div class="arch-card"><span>{html.escape(title)}</span>'
        f"<p>{html.escape(body)}</p></div>"
        for title, body in steps
    )
    return f'<div class="arch-flow">{cards}</div>'


def main() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="Decoupling Analyst",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    data = load_portfolio_data(ROOT)
    _inject_css(st)

    st.markdown(
        """
        <section class="hero">
          <p class="eyebrow">AI + Strategy Analysis Portfolio</p>
          <h1>Decoupling Analyst</h1>
          <p class="lede">
            Evidence-grounded customer value chain analysis, encoded as a local-first
            LLM workflow with typed artifacts, calibration, and provenance.
          </p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    aggregate = data["aggregate"]
    _metric_row(
        st,
        [
            ("14", "typed analysis modules"),
            ("$0.30", "observed grounded run cost"),
            (f"{aggregate['exact_or_partial_pct']}%", "exact-or-partial calibration"),
            (str(aggregate["fabrications"]), "visible fabrications"),
        ],
    )

    overview_tab, case_tab, eval_tab, trust_tab, report_tab = st.tabs(
        ["Overview", "Birchbox Case", "Evaluation", "Trust Layer", "Reports"]
    )
    with overview_tab:
        _render_overview(st, data)
    with case_tab:
        _render_case(st, data["featured_case"])
    with eval_tab:
        _render_evaluation(st, data)
    with trust_tab:
        _render_trust(st, data["featured_case"])
    with report_tab:
        _render_reports(st, data["featured_case"])


def _render_overview(st: Any, data: dict[str, Any]) -> None:
    st.markdown("### What this demonstrates")
    left, right = st.columns([0.95, 1.05], gap="large")
    with left:
        st.markdown(
            """
            This is not a live API demo. It is a portfolio-grade artifact explorer:
            the page reads committed JSON and Markdown outputs so reviewers can inspect
            the system without paying for model calls or configuring secrets.

            The strongest claim is evaluation discipline: every calibration number below
            comes from Teixeira-taught cases, then gets written into structured score files.
            """
        )
        _score_table(st, data["cases"])
    with right:
        st.markdown(render_architecture_html(), unsafe_allow_html=True)


def _render_case(st: Any, case: dict[str, Any]) -> None:
    top = case["top_weak_link"]
    decoupling = case["decoupling"]["primary_decoupling"]
    final = case["final_judgment"]
    st.markdown("### Birchbox walkthrough")
    st.markdown(render_cvc_html(case), unsafe_allow_html=True)
    cols = st.columns(3, gap="large")
    cols[0].markdown(
        _info_card("Weak link", f"Step {top['activity_id']}: {top['rationale'][:520]}...")
    )
    cols[1].markdown(
        _info_card("Decoupling wedge", decoupling["activity_to_decouple"])
    )
    cols[2].markdown(
        _info_card("Final judgment", f"{final['judgment']}: {final['one_sentence_thesis']}")
    )


def _render_evaluation(st: Any, data: dict[str, Any]) -> None:
    st.markdown("### Calibration evidence")
    _score_table(st, data["cases"])
    selected = st.selectbox(
        "Inspect scored fields",
        [case["company"] for case in data["cases"]],
        index=0,
    )
    case = next(case for case in data["cases"] if case["company"] == selected)
    for field in case["fields"]:
        status_class = f"status-{field['status']}"
        st.markdown(
            f"""
            <div class="field-row">
              <span class="pill {status_class}">{field['status']}</span>
              <strong>{html.escape(field['field'])}</strong>
              <p>{html.escape(field['rationale'])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_trust(st: Any, case: dict[str, Any]) -> None:
    provenance = case["provenance"]
    cost = case["cost_summary"]
    evidence = case["evidence_store"]
    st.markdown("### Audit layer")
    _metric_row(
        st,
        [
            (str(len(evidence)), "evidence records"),
            (str(len(provenance.get("retrieved_urls", []))), "retrieved URLs"),
            (str(len(provenance.get("report_only_urls", []))), "report-only URLs"),
            (f"${cost.get('total_cost_usd', 0):.2f}", "run cost"),
        ],
    )
    st.markdown(
        """
        The workflow writes evidence, provenance, and cost files for every run. Report-only
        references are intentionally surfaced instead of silently blending into grounded
        evidence.
        """
    )
    sample_rows = list(evidence.items())[:8]
    st.dataframe(
        [
            {
                "id": key,
                "claim": value.get("claim", ""),
                "source": value.get("source_id", ""),
                "confidence": value.get("confidence", ""),
            }
            for key, value in sample_rows
        ],
        width="stretch",
        hide_index=True,
    )


def _render_reports(st: Any, case: dict[str, Any]) -> None:
    st.markdown("### Report artifacts")
    lang = st.segmented_control("Report language", ["English", "Chinese"], default="English")
    report_key = "final_report" if lang == "English" else "final_report_zh"
    report_text = case[report_key]
    st.download_button(
        f"Download {lang} Markdown",
        data=report_text,
        file_name=f"birchbox_{report_key}.md",
        mime="text/markdown",
    )
    with st.expander("Preview report Markdown", expanded=True):
        st.code(report_text[:12000], language="markdown")


def _metric_row(st: Any, metrics: list[tuple[str, str]]) -> None:
    cols = st.columns(len(metrics), gap="medium")
    for col, (value, label) in zip(cols, metrics, strict=False):
        col.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-value">{html.escape(value)}</div>
              <div class="metric-label">{html.escape(label)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _score_table(st: Any, cases: list[dict[str, Any]]) -> None:
    st.dataframe(
        [
            {
                "Case": case["company"],
                "Exact": case["exact"],
                "Partial": case["partial"],
                "Miss": case["miss"],
                "Fabrications": case["fabrications"],
            }
            for case in cases
        ],
        width="stretch",
        hide_index=True,
    )


def _info_card(title: str, body: str) -> str:
    return (
        '<div class="info-card">'
        f"<span>{html.escape(title)}</span>"
        f"<p>{html.escape(body)}</p>"
        "</div>"
    )


def _inject_css(st: Any) -> None:
    st.markdown(
        """
        <style>
          .block-container { max-width: 1180px; padding-top: 2rem; }
          .hero { padding: 1.2rem 0 0.4rem; }
          .eyebrow {
            color: #0f766e; font-size: 0.8rem; font-weight: 750;
            letter-spacing: .08em; text-transform: uppercase; margin: 0 0 .45rem;
          }
          .hero h1 {
            font-size: clamp(2.5rem, 7vw, 5rem);
            line-height: 1.02; margin: 0; color: #172033;
          }
          .lede {
            max-width: 760px; color: #5f6b7a; font-size: 1.15rem;
            margin-top: .8rem;
          }
          .metric-card, .info-card, .field-row {
            border: 1px solid #d8dee8; border-radius: 8px; background: #f7f9fc;
            padding: 1rem; min-height: 100%;
          }
          .metric-value { color: #0f766e; font-size: 1.85rem; font-weight: 800; }
          .metric-label { color: #334155; font-size: .92rem; margin-top: .15rem; }
          .info-card span {
            display: block; color: #64748b; font-size: .76rem; font-weight: 800;
            text-transform: uppercase; margin-bottom: .45rem;
          }
          .info-card p { color: #172033; font-weight: 620; margin: 0; }
          .field-row { margin: .7rem 0; }
          .field-row p { margin: .35rem 0 0; color: #475569; }
          .flow-scroller {
            overflow-x: auto; padding: .2rem 0 1rem; margin-bottom: 1rem;
          }
          .flow {
            display: grid; grid-auto-flow: column; grid-auto-columns: minmax(210px, 1fr);
            gap: .85rem; min-width: 1180px; align-items: stretch;
          }
          .flow-node {
            position: relative; min-height: 190px; border: 1px solid #d8dee8;
            border-radius: 8px; padding: .95rem; background: #f8fafc;
          }
          .flow-node:not(:last-child)::after {
            content: "→"; position: absolute; right: -.72rem; top: 50%;
            transform: translateY(-50%); color: #64748b; font-weight: 800;
          }
          .flow-node.create { background: #f0fdf4; border-color: #86efac; }
          .flow-node.erode { background: #fff1f2; border-color: #fca5a5; }
          .flow-node.capture { background: #eff6ff; border-color: #93c5fd; }
          .flow-node.weak {
            background: #ffedd5; border-color: #c2410c; box-shadow: inset 0 0 0 2px #c2410c;
          }
          .flow-step {
            color: #0f766e; font-size: .76rem; font-weight: 850;
            text-transform: uppercase; margin-bottom: .55rem;
          }
          .flow-title { color: #172033; font-weight: 760; line-height: 1.25; }
          .flow-provider { color: #64748b; font-size: .82rem; margin-top: .65rem; }
          .arch-flow {
            display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: .75rem;
          }
          .arch-card {
            border: 1px solid #d8dee8; border-radius: 8px; padding: .95rem;
            background: #ffffff;
          }
          .arch-card span {
            color: #0f766e; display: block; font-weight: 850; margin-bottom: .3rem;
          }
          .arch-card p { color: #475569; margin: 0; }
          .pill {
            display: inline-block; border-radius: 999px; padding: .18rem .55rem;
            margin-right: .5rem; font-size: .74rem; font-weight: 800;
            text-transform: uppercase;
          }
          .status-exact { background: #dcfce7; color: #166534; }
          .status-partial { background: #fef3c7; color: #92400e; }
          .status-miss { background: #fee2e2; color: #991b1b; }
          div[data-testid="stDataFrame"] { border: 1px solid #d8dee8; border-radius: 8px; }
          @media (max-width: 760px) {
            .arch-flow { grid-template-columns: 1fr; }
            .flow { grid-auto-columns: 220px; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _case_score(scores: dict[str, Any], slug: str) -> dict[str, Any]:
    return next(case for case in scores["cases"] if case["case_slug"] == slug)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "", value)
    return cleaned or "N"


def _escape_mermaid(text: str) -> str:
    return (
        str(text or "")
        .replace('"', "''")
        .replace("[", "(")
        .replace("]", ")")
        .replace("|", "/")
        .replace("\n", " ")
    )


if __name__ == "__main__":
    main()
