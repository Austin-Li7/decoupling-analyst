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

VALUE_TYPE_LABEL = {
    "create": "Creates value",
    "erode": "Erodes value",
    "capture": "Captures value",
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
        value_key = str(values.get(activity.get("id"), "")).lower()
        value_class = VALUE_TYPE_STYLE.get(value_key, "neutral")
        is_weak = activity.get("id") == highlight_id
        weak_class = " weak" if is_weak else ""
        badge = '<div class="flow-tag">&#9889; Weak link</div>' if is_weak else ""
        vtype_label = VALUE_TYPE_LABEL.get(value_key, "")
        vtype = (
            f'<div class="flow-vtype {value_class}">{vtype_label}</div>'
            if vtype_label
            else ""
        )
        nodes.append(
            f'<div class="flow-node {value_class}{weak_class}">'
            f"{badge}"
            f'<div class="flow-step">Step {html.escape(str(activity.get("step", "?")))}</div>'
            f'<div class="flow-title">{html.escape(activity.get("activity", ""))}</div>'
            f"{vtype}"
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

    case_tab, report_tab, eval_tab, trust_tab, overview_tab = st.tabs(
        [
            "Birchbox Analysis",
            "Full Report",
            "Evaluation",
            "Trust Layer",
            "How it works",
        ]
    )
    with case_tab:
        _render_case(st, data["featured_case"])
    with report_tab:
        _render_reports(st, data["featured_case"])
    with eval_tab:
        _render_evaluation(st, data)
    with trust_tab:
        _render_trust(st, data["featured_case"])
    with overview_tab:
        _render_overview(st, data)


def _render_overview(st: Any, data: dict[str, Any]) -> None:
    st.markdown("### How the analysis is produced")
    left, right = st.columns([0.95, 1.05], gap="large")
    with left:
        st.markdown(
            """
            This page is not a live API demo. It reads the JSON and Markdown the
            workflow already committed, so a reviewer can inspect the full reasoning
            without paying for model calls or configuring secrets.

            The pipeline turns a company into a typed customer-value-chain analysis:
            grounded retrieval feeds 14 reasoning modules, each emitting a validated
            artifact, and the final memo cites every claim back to an evidence ID.
            """
        )
        st.markdown("**Calibration across taught cases**")
        _score_table(st, data["cases"])
    with right:
        st.markdown(render_architecture_html(), unsafe_allow_html=True)


JUDGMENT_LABELS = {
    "go": ("Go", "verdict-go"),
    "study_more": ("Study more", "verdict-study"),
    "no_go": ("No go", "verdict-stop"),
    "pass": ("Pass", "verdict-stop"),
}


def _render_case(st: Any, case: dict[str, Any]) -> None:
    top = case["top_weak_link"]
    decoupling = case["decoupling"]["primary_decoupling"]
    final = case["final_judgment"]
    label, verdict_class = JUDGMENT_LABELS.get(
        final["judgment"], (final["judgment"].replace("_", " ").title(), "verdict-study")
    )

    st.markdown(
        f"""
        <div class="verdict {verdict_class}">
          <div class="verdict-head">
            <span class="verdict-tag">Recommendation</span>
            <span class="verdict-badge">{html.escape(label)}</span>
          </div>
          <p class="verdict-thesis">{html.escape(final["one_sentence_thesis"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Customer value chain")
    st.caption(
        "Each step shows who currently owns it. Green creates value, blue captures it, "
        "and the highlighted step is the weak link Birchbox can pry loose."
    )
    st.markdown(render_cvc_html(case), unsafe_allow_html=True)

    weak_point = _lead_sentences(_clean_citations(top["rationale"]), 2)
    st.markdown("#### The weak link")
    st.markdown(
        f"""
        <div class="readout">
          <p class="readout-lead">
            <strong>Step {html.escape(str(top["activity_id"]))} &mdash;
            {html.escape(decoupling["activity_to_decouple"])}.</strong>
          </p>
          <p>{html.escape(weak_point)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Why this is the wedge")
    cols = st.columns(2, gap="large")
    cols[0].markdown(
        _info_card("Customer pain today", _clean_citations(decoupling["customer_pain"])),
        unsafe_allow_html=True,
    )
    cols[1].markdown(
        _info_card(
            "Why customers switch",
            _lead_sentences(_clean_citations(decoupling["why_customer_switches"]), 1),
        ),
        unsafe_allow_html=True,
    )

    st.markdown("#### What to do")
    st.markdown(
        _ordered_list([_action_headline(a) for a in final["staged_actions"]]),
        unsafe_allow_html=True,
    )

    do_col, risk_col = st.columns([1, 1], gap="large")
    with do_col:
        st.markdown("#### What not to do")
        st.markdown(
            _bullet_list([_headline(d, 26) for d in final["do_not_do"]], "dont"),
            unsafe_allow_html=True,
        )
    with risk_col:
        st.markdown("#### Biggest risk")
        st.markdown(
            f'<div class="readout readout-risk"><p>'
            f'{html.escape(_lead_sentences(_clean_citations(final["biggest_risk"]), 1))}'
            "</p></div>",
            unsafe_allow_html=True,
        )


def _ordered_list(items: list[tuple[str, str]]) -> str:
    rows = ""
    for i, (label, text) in enumerate(items, start=1):
        label_html = (
            f'<span class="a-label">{html.escape(label)}</span>' if label else ""
        )
        rows += (
            f'<li><span class="num">{i}</span>'
            f'<span class="a-body">{label_html}'
            f'<span class="a-text">{html.escape(text)}</span></span></li>'
        )
    return f'<ol class="action-list">{rows}</ol>'


def _bullet_list(items: list[str], variant: str) -> str:
    rows = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f'<ul class="bullet-list {variant}">{rows}</ul>'


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
    head, action = st.columns([3, 1], gap="large")
    with head:
        st.markdown(
            f"""
            <div class="memo-header">
              <span class="memo-eyebrow">Analyst memo &middot; {html.escape(case["company"])}</span>
              <h2>The decision memo, unabridged</h2>
              <p>
                The full report exactly as the workflow committed it &mdash; verdict,
                customer value chain, the decoupling wedge, the staged strategy, and an
                evidence base where every claim is traced back to a numbered source.
              </p>
              <div class="memo-meta">
                <span>Every claim cited to an evidence ID</span>
                <span>English &amp; 中文</span>
                <span>Download as Markdown</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    lang = action.segmented_control(
        "Language", ["English", "中文"], default="English", label_visibility="collapsed"
    )
    report_key = "final_report" if lang == "English" else "final_report_zh"
    report_text = case[report_key]
    action.download_button(
        "Download .md",
        data=report_text,
        file_name=f"birchbox_{report_key}.md",
        mime="text/markdown",
        width="stretch",
    )
    with st.container(border=True):
        st.markdown(_clean_report_markdown(report_text), unsafe_allow_html=True)


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
    rows = "".join(
        f"<tr>"
        f'<td class="case-name">{html.escape(case["company"])}</td>'
        f'<td class="num v-exact">{case["exact"]}</td>'
        f'<td class="num v-partial">{case["partial"]}</td>'
        f'<td class="num v-miss">{case["miss"]}</td>'
        f'<td class="num v-fab">{case["fabrications"]}</td>'
        f"</tr>"
        for case in cases
    )
    st.markdown(
        '<table class="score-table">'
        "<thead><tr>"
        "<th>Case</th>"
        '<th class="num">Exact</th>'
        '<th class="num">Partial</th>'
        '<th class="num">Miss</th>'
        '<th class="num">Fabrications</th>'
        "</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>",
        unsafe_allow_html=True,
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
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

          :root {
            --surface: #ffffff;
            --surface-soft: #f6f8fb;
            --border: #e2e8f0;
            --border-bright: #cbd5e1;
            --text: #1e293b;
            --heading: #0f172a;
            --muted: #64748b;
            --faint: #94a3b8;
            --teal: #0d9488;
            --teal-soft: #f0fdfa;
          }

          html, body, [class*="css"], .stMarkdown, .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
          }
          .block-container { max-width: 1080px; padding-top: 2.4rem; }

          .hero { padding: .6rem 0 .4rem; }
          .eyebrow {
            display: inline-block;
            color: var(--teal); font-size: 0.76rem; font-weight: 700;
            letter-spacing: .12em; text-transform: uppercase; margin: 0 0 .85rem;
            padding: .3rem .75rem; border-radius: 999px;
            background: var(--teal-soft); border: 1px solid #99f6e4;
          }
          .hero h1 {
            font-size: clamp(2.4rem, 6vw, 4.2rem);
            line-height: 1.03; margin: 0; font-weight: 850; letter-spacing: -.025em;
            color: var(--heading);
          }
          .lede {
            max-width: 760px; color: var(--muted); font-size: 1.12rem;
            line-height: 1.6; margin-top: .9rem; font-weight: 400;
          }

          .metric-card {
            position: relative; overflow: hidden; padding: 1.1rem 1.25rem;
            min-height: 100%; border: 1px solid var(--border); border-radius: 12px;
            background: var(--surface);
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            transition: box-shadow .2s ease, transform .2s ease;
          }
          .metric-card::before {
            content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
            background: var(--teal);
          }
          .metric-card:hover { box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08); transform: translateY(-2px); }
          .metric-value { font-size: 1.95rem; font-weight: 800; letter-spacing: -.02em; color: var(--teal); }
          .metric-label { color: var(--muted); font-size: .85rem; margin-top: .2rem; font-weight: 500; }

          .verdict {
            border: 1px solid var(--border); border-left: 5px solid var(--teal);
            border-radius: 12px; background: var(--surface);
            padding: 1.3rem 1.5rem; margin: .4rem 0 1.6rem;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
          }
          .verdict-go { border-left-color: #16a34a; }
          .verdict-study { border-left-color: #d97706; }
          .verdict-stop { border-left-color: #dc2626; }
          .verdict-head { display: flex; align-items: center; gap: .8rem; margin-bottom: .7rem; }
          .verdict-tag {
            color: var(--muted); font-size: .72rem; font-weight: 700;
            letter-spacing: .1em; text-transform: uppercase;
          }
          .verdict-badge {
            font-size: .82rem; font-weight: 800; letter-spacing: .03em;
            padding: .22rem .7rem; border-radius: 999px; text-transform: uppercase;
          }
          .verdict-go .verdict-badge { background: #dcfce7; color: #15803d; }
          .verdict-study .verdict-badge { background: #fef3c7; color: #b45309; }
          .verdict-stop .verdict-badge { background: #fee2e2; color: #b91c1c; }
          .verdict-thesis { color: var(--heading); font-size: 1.15rem; line-height: 1.65; margin: 0; font-weight: 500; }

          .info-card {
            padding: 1.05rem 1.2rem; min-height: 100%;
            border: 1px solid var(--border); border-radius: 12px; background: var(--surface-soft);
          }
          .info-card span {
            display: block; color: var(--teal); font-size: .72rem; font-weight: 700;
            letter-spacing: .06em; text-transform: uppercase; margin-bottom: .5rem;
          }
          .info-card p { color: var(--text); font-weight: 400; margin: 0; line-height: 1.6; }

          .readout {
            border: 1px solid var(--border); border-radius: 12px; background: var(--surface);
            padding: 1.15rem 1.35rem; margin: .3rem 0 1rem; line-height: 1.7;
          }
          .readout p { margin: 0 0 .4rem; color: var(--text); }
          .readout p:last-child { margin-bottom: 0; }
          .readout-lead strong { color: var(--heading); }
          .readout-risk { border-left: 4px solid #f59e0b; background: #fffbeb; }

          .action-list { list-style: none; margin: .2rem 0 1rem; padding: 0; counter-reset: none; }
          .action-list li {
            display: flex; gap: .8rem; align-items: flex-start;
            padding: .85rem 1.1rem; margin-bottom: .55rem; line-height: 1.6;
            border: 1px solid var(--border); border-radius: 10px; background: var(--surface);
            color: var(--text);
          }
          .action-list .num {
            flex: 0 0 auto; width: 1.6rem; height: 1.6rem; border-radius: 50%;
            background: var(--teal); color: #fff; font-weight: 700; font-size: .82rem;
            display: flex; align-items: center; justify-content: center; margin-top: .05rem;
          }
          .action-list .a-body { display: flex; flex-direction: column; gap: .25rem; }
          .action-list .a-label {
            align-self: flex-start; color: var(--teal); background: var(--teal-soft);
            border: 1px solid #99f6e4; font-size: .66rem; font-weight: 700;
            letter-spacing: .04em; text-transform: uppercase; padding: .12rem .5rem;
            border-radius: 999px;
          }
          .action-list .a-text { color: var(--heading); font-weight: 550; font-size: 1rem; }
          .bullet-list { margin: .2rem 0 1rem; padding-left: 0; list-style: none; }
          .bullet-list li {
            position: relative; padding: .55rem 0 .55rem 1.4rem; line-height: 1.6;
            color: var(--text); border-bottom: 1px solid var(--border);
          }
          .bullet-list li:last-child { border-bottom: none; }
          .bullet-list.dont li::before {
            content: "\\2715"; position: absolute; left: 0; top: .55rem;
            color: #dc2626; font-weight: 700; font-size: .85rem;
          }

          .field-row {
            padding: .95rem 1.1rem; margin: .55rem 0;
            border: 1px solid var(--border); border-radius: 10px; background: var(--surface);
          }
          .field-row strong { color: var(--heading); font-weight: 600; }
          .field-row p { margin: .35rem 0 0; color: var(--muted); line-height: 1.6; }

          .flow-scroller { overflow-x: auto; padding: .5rem 0 1rem; margin-bottom: 1rem; }
          .flow {
            display: grid; grid-auto-flow: column; grid-auto-columns: minmax(200px, 1fr);
            gap: 1.25rem; min-width: 1060px; align-items: stretch;
          }
          .flow-node {
            position: relative; min-height: 180px; padding: 1rem 1rem 1.05rem;
            border: 1px solid var(--border); border-top: 3px solid var(--border-bright);
            border-radius: 10px; background: var(--surface);
          }
          .flow-node:not(:last-child)::after {
            content: "→"; position: absolute; right: -1rem; top: 50%;
            transform: translateY(-50%); color: var(--faint); font-weight: 800;
            font-size: 1.05rem; z-index: 2;
          }
          .flow-node.create { border-top-color: #22c55e; }
          .flow-node.erode  { border-top-color: #ef4444; }
          .flow-node.capture{ border-top-color: #3b82f6; }
          .flow-node.weak {
            border: 2px solid #f97316; border-top: 3px solid #f97316;
            background: #fff7ed;
            box-shadow: 0 8px 22px rgba(249, 115, 22, 0.22);
            transform: translateY(-6px);
          }
          .flow-tag {
            display: inline-block; background: #ea580c; color: #fff;
            font-size: .62rem; font-weight: 800; letter-spacing: .06em;
            text-transform: uppercase; padding: .2rem .55rem; border-radius: 999px;
            margin-bottom: .55rem;
          }
          .flow-step {
            color: var(--faint); font-size: .7rem; font-weight: 800;
            letter-spacing: .06em; text-transform: uppercase; margin-bottom: .4rem;
          }
          .flow-node.weak .flow-step { color: #ea580c; }
          .flow-title { color: var(--heading); font-weight: 650; line-height: 1.3; font-size: .98rem; }
          .flow-vtype { font-size: .72rem; font-weight: 700; margin-top: .6rem; }
          .flow-vtype.create { color: #16a34a; }
          .flow-vtype.erode  { color: #dc2626; }
          .flow-vtype.capture{ color: #2563eb; }
          .flow-provider { color: var(--muted); font-size: .78rem; margin-top: .45rem; line-height: 1.45; }

          .arch-flow { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem; }
          .arch-card {
            padding: 1rem 1.15rem; border: 1px solid var(--border); border-radius: 12px;
            background: var(--surface);
          }
          .arch-card span { color: var(--teal); display: block; font-weight: 700; margin-bottom: .35rem; }
          .arch-card p { color: var(--muted); margin: 0; line-height: 1.5; font-size: .9rem; }

          .pill {
            display: inline-block; border-radius: 999px; padding: .18rem .6rem;
            margin-right: .6rem; font-size: .68rem; font-weight: 700;
            letter-spacing: .04em; text-transform: uppercase;
          }
          .status-exact   { background: #dcfce7; color: #15803d; }
          .status-partial { background: #fef3c7; color: #b45309; }
          .status-miss    { background: #fee2e2; color: #b91c1c; }

          .score-table {
            width: 100%; border-collapse: separate; border-spacing: 0;
            border: 1px solid var(--border); border-radius: 12px; overflow: hidden;
            background: var(--surface); margin: .3rem 0 1rem;
          }
          .score-table th {
            text-align: left; padding: .75rem 1rem; font-size: .72rem; font-weight: 700;
            letter-spacing: .05em; text-transform: uppercase; color: var(--muted);
            background: var(--surface-soft); border-bottom: 1px solid var(--border);
          }
          .score-table th.num, .score-table td.num { text-align: right; }
          .score-table td { padding: .75rem 1rem; color: var(--text); font-size: .94rem; border-bottom: 1px solid var(--border); }
          .score-table tr:last-child td { border-bottom: none; }
          .score-table tbody tr:hover td { background: var(--surface-soft); }
          .score-table .case-name { font-weight: 600; color: var(--heading); }
          .score-table .v-exact { color: #15803d; font-weight: 600; }
          .score-table .v-partial { color: #b45309; font-weight: 600; }
          .score-table .v-miss { color: #b91c1c; font-weight: 600; }
          .score-table .v-fab { color: #dc2626; font-weight: 600; }

          .stMarkdown h3 { color: var(--heading); font-weight: 750; letter-spacing: -.01em; }
          .stMarkdown h4 { color: var(--heading); font-weight: 700; margin-top: 1.2rem; }
          div[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 10px; }
          .stTabs [data-baseweb="tab-list"] { gap: .3rem; }
          .stTabs [data-baseweb="tab"] { font-weight: 600; }

          /* full memo reading view */
          .memo-scope { line-height: 1.7; }
          .memo-header { padding: .2rem 0 .3rem; }
          .memo-eyebrow {
            color: var(--teal); font-size: .74rem; font-weight: 700;
            letter-spacing: .1em; text-transform: uppercase;
          }
          .memo-header h2 {
            color: var(--heading); font-size: 1.85rem; font-weight: 800;
            letter-spacing: -.02em; margin: .35rem 0 .5rem; line-height: 1.15;
          }
          .memo-header p { color: var(--muted); font-size: 1.02rem; line-height: 1.6; margin: 0; max-width: 640px; }
          .memo-meta { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
          .memo-meta span {
            color: var(--text); background: var(--surface-soft);
            border: 1px solid var(--border); border-radius: 999px;
            font-size: .76rem; font-weight: 600; padding: .28rem .7rem;
          }
          .memo-meta span::before { content: "\\2713  "; color: var(--teal); font-weight: 800; }

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


_PATH_CITE = re.compile(r"\s*\((?:books|talks|docs|src)/[^)]*\)")
_EVID_CITE = re.compile(r"\s*\((?:E\d+)(?:\s*,\s*E\d+)*\)")


def _clean_citations(text: str) -> str:
    """Strip inline source citations that add noise to the readable view.

    The full citations are preserved verbatim in the Full Report tab; this only
    declutters the at-a-glance Analysis tab.
    """
    cleaned = _PATH_CITE.sub("", text or "")
    cleaned = _EVID_CITE.sub("", cleaned)
    cleaned = re.sub(r"\s+([.,;])", r"\1", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def _lead_sentences(text: str, count: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:count]).strip()


_HEADLINE_BREAK = re.compile(r"[:;]| so | so that | \(e\.g| to test| to validate|, positioning")


def _headline(text: str, max_words: int = 16) -> str:
    """Reduce a long recommendation to its core directive."""
    body = _clean_citations(text)
    body = _HEADLINE_BREAK.split(body, maxsplit=1)[0].strip().rstrip(",;:")
    words = body.split()
    if len(words) > max_words:
        body = " ".join(words[:max_words]).rstrip(",;:") + "…"
    return body


def _action_headline(text: str) -> tuple[str, str]:
    """Split a staged action into a short stage label and a one-line directive."""
    match = re.match(r"\s*\((.*?)\)\s*(.*)", text, re.DOTALL)
    label_raw, body = (match.group(1), match.group(2)) if match else ("", text)
    if "—" in label_raw:  # em dash: keep the descriptive half
        label = label_raw.split("—", 1)[1].strip()
    else:
        label = label_raw.split(",", 1)[0].strip()
    return label, _headline(body)


def _clean_report_markdown(text: str) -> str:
    """Strip YAML frontmatter and mermaid code fences so the memo renders cleanly.

    The CVC diagram is already shown as HTML in the Analysis tab, so the raw
    mermaid block (which Streamlit cannot render) would only show as code noise.
    """
    body = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    body = re.sub(r"```mermaid.*?```\n?", "", body, flags=re.DOTALL)
    return body.strip()


if __name__ == "__main__":
    main()
