import json
from pathlib import Path

from typer.testing import CliRunner

from mgt470_analyst.cli import app
from mgt470_analyst.eval.cases import discover_eval_cases
from mgt470_analyst.eval.report import aggregate_scores, render_markdown_summary
from mgt470_analyst.eval.scorer import score_case


def test_eval_scorer_matches_current_human_reviewed_baseline() -> None:
    cases = discover_eval_cases(Path("cases/calibration"))
    scores = [score_case(case) for case in cases]
    aggregate = aggregate_scores(scores)

    assert [score.case_slug for score in scores] == ["birchbox", "olx-brazil", "trov"]
    assert aggregate.exact == 12
    assert aggregate.partial == 5
    assert aggregate.miss == 4
    assert aggregate.fabrications == 2
    assert aggregate.exact_pct == 57
    assert aggregate.exact_or_partial_pct == 81


def test_eval_report_renders_markdown_summary() -> None:
    scores = [score_case(case) for case in discover_eval_cases(Path("cases/calibration"))]
    markdown = render_markdown_summary(scores)

    assert "# Calibration Summary" in markdown
    assert "| Birchbox | 5 | 2 | 0 | 0 |" in markdown
    assert "| **Total** | **12** | **5** | **4** | **2** |" in markdown
    assert "57% exact" in markdown
    assert "81% exact-or-partial" in markdown


def test_calibrate_cli_writes_json_and_markdown_outputs(tmp_path: Path) -> None:
    json_output = tmp_path / "SCORES.json"
    markdown_output = tmp_path / "SUMMARY.md"

    result = CliRunner().invoke(
        app,
        [
            "calibrate",
            "--calibration-dir",
            "cases/calibration",
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
        ],
    )

    assert result.exit_code == 0
    assert "Calibration complete:" in result.output
    assert json_output.exists()
    assert markdown_output.exists()

    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["aggregate"]["exact"] == 12
    assert payload["aggregate"]["exact_pct"] == 57
    assert payload["aggregate"]["exact_or_partial_pct"] == 81
    assert payload["aggregate"]["fabrications"] == 2
