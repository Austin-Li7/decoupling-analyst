from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

REPO_URL = "https://github.com/Austin-Li7/decoupling-analyst"
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs"


@dataclass(frozen=True)
class CalibrationSummary:
    slug: str
    company: str
    exact: int
    partial: int
    miss: int
    fabrications: int


@dataclass(frozen=True)
class CalibrationTotals:
    exact: int
    partial: int
    miss: int
    fabrications: int

    @property
    def scored_fields(self) -> int:
        return self.exact + self.partial + self.miss

    @property
    def exact_pct(self) -> int:
        return round(self.exact / self.scored_fields * 100) if self.scored_fields else 0

    @property
    def exact_or_partial_pct(self) -> int:
        if not self.scored_fields:
            return 0
        return round((self.exact + self.partial) / self.scored_fields * 100)


@dataclass(frozen=True)
class BirchboxSample:
    mermaid: str
    weak_link: str
    decoupling_pattern: str
    final_judgment: str


@dataclass(frozen=True)
class ShowcaseData:
    cases: list[CalibrationSummary]
    totals: CalibrationTotals
    birchbox: BirchboxSample


def parse_calibration_report(path: Path) -> CalibrationSummary:
    text = path.read_text(encoding="utf-8")
    exact = _extract_score(text, r"Matches:\s*(\d+)/")
    partial = _extract_score(text, r"Partial:\s*(\d+)/")
    miss = _extract_score(text, r"Misses:\s*(\d+)/")
    fabrications = _extract_score(text, r"Fabrications detected:\s*(\d+)")
    slug = path.parent.name
    company = _company_name_from_heading(text, slug)
    return CalibrationSummary(
        slug=slug,
        company=company,
        exact=exact,
        partial=partial,
        miss=miss,
        fabrications=fabrications,
    )


def load_showcase_data(repo_root: Path) -> ShowcaseData:
    calibration_dir = repo_root / "cases" / "calibration"
    cases = [
        parse_calibration_report(path)
        for path in sorted(calibration_dir.glob("*/calibration_report.md"))
    ]
    totals = CalibrationTotals(
        exact=sum(case.exact for case in cases),
        partial=sum(case.partial for case in cases),
        miss=sum(case.miss for case in cases),
        fabrications=sum(case.fabrications for case in cases),
    )
    return ShowcaseData(cases=cases, totals=totals, birchbox=_load_birchbox(repo_root))


def build_showcase_html(data: ShowcaseData) -> str:
    architecture = """flowchart LR
    A["Raw input<br/>company, URL, ticker, PDF, notes"]
    B["Tavily grounded search"]
    C["Teixeira corpus RAG"]
    D["Grounding gate<br/>refuse empty retrieval"]
    E["14 Pydantic typed modules"]
    F["Reports<br/>final_report.md + final_report_zh.md"]
    G["Audit files<br/>evidence, provenance, cost"]
    A --> B
    A --> C
    B --> D
    C --> E
    D --> E
    E --> F
    E --> G"""
    totals = data.totals
    rows = "\n".join(
        "              "
        + "".join(
            [
                f"<tr><td>{html.escape(case.company)}</td>",
                f"<td>{case.exact}</td>",
                f"<td>{case.partial}</td>",
                f"<td>{case.miss}</td>",
                f"<td>{case.fabrications}</td></tr>",
            ]
        )
        for case in data.cases
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Decoupling Analyst Showcase</title>
    <style>
      :root {{
        color-scheme: light;
        --ink: #172033;
        --muted: #5f6b7a;
        --line: #d8dee8;
        --panel: #f6f8fb;
        --accent: #0f766e;
        --accent-2: #b45309;
        --danger: #b91c1c;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
        background: #ffffff;
        line-height: 1.55;
      }}
      main {{
        width: min(1120px, calc(100% - 32px));
        margin: 0 auto;
        padding: 44px 0 56px;
      }}
      h1, h2, h3 {{ line-height: 1.15; letter-spacing: 0; }}
      h1 {{ margin: 0 0 14px; font-size: clamp(2rem, 6vw, 4rem); }}
      h2 {{ margin: 44px 0 14px; font-size: clamp(1.45rem, 4vw, 2.2rem); }}
      h3 {{ margin: 24px 0 8px; font-size: 1.1rem; }}
      p {{ margin: 0 0 14px; }}
      a {{ color: var(--accent); font-weight: 650; }}
      .lede {{ max-width: 780px; color: var(--muted); font-size: 1.18rem; }}
      .strip {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 28px 0 8px;
      }}
      .metric {{
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px;
        background: var(--panel);
      }}
      .metric strong {{ display: block; font-size: 1.55rem; color: var(--accent); }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
        font-size: 0.96rem;
      }}
      th, td {{ border-bottom: 1px solid var(--line); padding: 11px 10px; text-align: left; }}
      th {{ background: var(--panel); font-weight: 750; }}
      td:not(:first-child), th:not(:first-child) {{ text-align: right; }}
      .total-row td {{ font-weight: 800; color: var(--accent); }}
      .sample {{
        display: grid;
        grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
        gap: 24px;
        align-items: start;
      }}
      .notes {{
        border-left: 4px solid var(--accent-2);
        padding: 2px 0 2px 18px;
      }}
      .notes dt {{ color: var(--muted); font-size: 0.82rem; text-transform: uppercase; }}
      .notes dd {{ margin: 0 0 18px; font-weight: 650; }}
      .mermaid {{
        overflow-x: auto;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 18px;
        background: #ffffff;
      }}
      .links {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 16px;
      }}
      .links a {{
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 10px 12px;
        text-decoration: none;
      }}
      @media (max-width: 760px) {{
        main {{ width: min(100% - 24px, 1120px); padding-top: 28px; }}
        .strip, .sample {{ grid-template-columns: 1fr; }}
        table {{ font-size: 0.88rem; }}
        th, td {{ padding: 9px 7px; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>Decoupling Analyst</h1>
        <p class="lede">
          A local-first AI strategy workflow that turns company inputs into Teixeira-style
          customer value chain analysis, grounded recommendations, bilingual reports, and
          auditable evidence artifacts.
        </p>
        <section class="strip" aria-label="Project proof points">
          <div class="metric">
            <strong>$0.30/run</strong><span>observed grounded run cost</span>
          </div>
          <div class="metric">
            <strong>14 modules</strong><span>Pydantic-typed analysis pipeline</span>
          </div>
          <div class="metric">
            <strong>Grounding gate</strong><span>fails loud on empty retrieval</span>
          </div>
        </section>
      </header>

      <section>
        <h2>Calibration Against Teixeira Cases</h2>
        <p>
          These numbers are parsed from the human-reviewed calibration reports in
          <code>cases/calibration/</code>.
        </p>
        <table>
          <thead>
            <tr><th>Case</th><th>Exact</th><th>Partial</th><th>Miss</th><th>Fabrications</th></tr>
          </thead>
          <tbody>
{rows}
            <tr class="total-row">
              <td>Total</td><td>{totals.exact}</td><td>{totals.partial}</td>
              <td>{totals.miss}</td><td>{totals.fabrications}</td>
            </tr>
          </tbody>
        </table>
        <p>
          Aggregate: <strong>{totals.exact_pct}% exact</strong> and
          <strong>{totals.exact_or_partial_pct}% exact-or-partial</strong>
          across {totals.scored_fields} scored fields.
        </p>
      </section>

      <section>
        <h2>Complete Example: Birchbox</h2>
        <div class="sample">
          <pre class="mermaid">{html.escape(data.birchbox.mermaid)}</pre>
          <dl class="notes">
            <dt>Weak link</dt>
            <dd>{html.escape(data.birchbox.weak_link)}</dd>
            <dt>Decoupling pattern</dt>
            <dd>{html.escape(data.birchbox.decoupling_pattern)}</dd>
            <dt>Final judgment</dt>
            <dd>{html.escape(data.birchbox.final_judgment)}</dd>
          </dl>
        </div>
      </section>

      <section>
        <h2>Architecture</h2>
        <pre class="mermaid">{html.escape(architecture)}</pre>
      </section>

      <section>
        <h2>Explore The Project</h2>
        <div class="links">
          <a href="{REPO_URL}">GitHub repository</a>
          <a href="{REPO_URL}/blob/main/SYSTEM_DESIGN.md">System design</a>
          <a href="{REPO_URL}/tree/main/cases">Case artifacts</a>
        </div>
      </section>
    </main>
    <script type="module">
      import mermaid from '{MERMAID_CDN}';
      mermaid.initialize({{ startOnLoad: true, securityLevel: 'loose' }});
    </script>
  </body>
</html>
"""


def write_showcase(repo_root: Path, output_path: Path | None = None) -> Path:
    output = output_path or repo_root / "docs" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_showcase_html(load_showcase_data(repo_root)), encoding="utf-8")
    return output


def _load_birchbox(repo_root: Path) -> BirchboxSample:
    from mgt470_analyst.renderers.mermaid import render_cvc_flowchart

    run_dir = repo_root / "cases" / "calibration" / "birchbox" / "system_run"
    cvc = _read_json(run_dir / "cvc.json")["activities"]
    values = _read_json(run_dir / "value_type_diagnosis.json")["activities"]
    weak_links = _read_json(run_dir / "weak_link_analysis.json")["ranked_weak_links"]
    decoupling = _read_json(run_dir / "decoupling_strategy.json")["primary_decoupling"]
    final = _read_json(run_dir / "final_judgment.json")
    top_weak_link = weak_links[0]
    mermaid = _strip_mermaid_fence(
        render_cvc_flowchart(cvc, values, highlight_activity_id=top_weak_link["activity_id"])
    )
    return BirchboxSample(
        mermaid=mermaid,
        weak_link=top_weak_link["rationale"],
        decoupling_pattern=decoupling["activity_to_decouple"],
        final_judgment=f'{final["judgment"]}: {final["one_sentence_thesis"]}',
    )


def _extract_score(text: str, pattern: str) -> int:
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Could not parse calibration score with pattern: {pattern}")
    return int(match.group(1))


def _company_name_from_heading(text: str, slug: str) -> str:
    match = re.search(r"^#\s+(.+?)\s+Calibration Report", text, flags=re.MULTILINE)
    if match:
        return match.group(1)
    return slug.replace("-", " ").title()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_mermaid_fence(markdown: str) -> str:
    lines = markdown.splitlines()
    if lines and lines[0].strip() == "```mermaid":
        lines = lines[1:]
    if "```" in lines:
        lines = lines[: lines.index("```")]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static Decoupling Analyst showcase.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = write_showcase(args.repo_root.resolve(), args.output)
    print(f"Wrote showcase: {output}")


if __name__ == "__main__":
    main()
