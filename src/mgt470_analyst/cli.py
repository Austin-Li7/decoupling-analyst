from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv

from mgt470_analyst.orchestrator import run_analysis
from mgt470_analyst.schemas.raw_input import RawInput

# Load .env from the current working directory so users can put OPENAI_API_KEY
# there instead of exporting it every time.
load_dotenv()

app = typer.Typer(help="MGT470 decoupling analyst workflow engine.")


@app.callback()
def main() -> None:
    """Run local MGT470 analysis workflows."""


@app.command()
def analyze(
    company: Annotated[str, typer.Option("--company", help="Target company name.")],
    ticker: Annotated[str, typer.Option("--ticker", help="Optional public ticker.")] = "",
    url: Annotated[
        list[str] | None,
        typer.Option("--url", help="Company or research URL. Can be passed multiple times."),
    ] = None,
    file: Annotated[
        list[str] | None,
        typer.Option("--file", help="Local input file. Can be passed multiple times."),
    ] = None,
    mode: Annotated[str, typer.Option("--mode", help="Analysis mode.")] = "investment",
    question: Annotated[str, typer.Option("--question", help="Free-form analysis question.")] = "",
    output: Annotated[
        Path | None, typer.Option("--output", help="Optional copy destination for final Markdown.")
    ] = None,
    runs_dir: Annotated[
        Path,
        typer.Option("--runs-dir", help="Directory for run artifacts."),
    ] = Path("./runs"),
    include_financial_verification: Annotated[
        bool,
        typer.Option(
            "--include-financial-verification",
            help="Accepted for compatibility; full verification is deferred in MVP.",
        ),
    ] = False,
) -> None:
    urls = url or []
    raw_input = RawInput(
        analysis_goal=_map_mode(mode),
        company_name=company,
        ticker=ticker,
        website=urls[0] if urls else "",
        urls=urls,
        files=file or [],
        user_question=question,
        include_financial_verification=include_financial_verification,
    )
    result = run_analysis(raw_input, runs_dir=runs_dir)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.report_path.read_text(encoding="utf-8"), encoding="utf-8")
    typer.echo(f"Run complete: {result.run_dir}")
    typer.echo(f"Report: {result.report_path}")


def _map_mode(mode: str) -> str:
    if mode == "investment":
        return "investment_judgment"
    if mode in {"startup", "startup_opportunity"}:
        return "startup_opportunity"
    if mode in {"commercial", "strategy", "commercial_strategy"}:
        return "commercial_strategy"
    return "investment_judgment"
