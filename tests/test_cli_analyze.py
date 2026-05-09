from pathlib import Path

from typer.testing import CliRunner

from mgt470_analyst.cli import app


def test_cli_analyze_runs_workflow(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "analyze",
            "--company",
            "Duolingo",
            "--ticker",
            "DUOL",
            "--url",
            "https://www.duolingo.com",
            "--mode",
            "investment",
            "--runs-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Run complete:" in result.output
    assert "Report:" in result.output
    run_dirs = list(tmp_path.iterdir())
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "final_report.md").exists()
    assert (run_dirs[0] / "final_report_zh.md").exists()
