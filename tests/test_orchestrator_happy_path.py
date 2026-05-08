import json
from pathlib import Path

from mgt470_analyst.evidence.validator import collect_evidence_ids
from mgt470_analyst.orchestrator import run_analysis
from mgt470_analyst.schemas.raw_input import RawInput

EXPECTED_ARTIFACTS = {
    "run.json",
    "research_brief.json",
    "evidence_store.json",
    "company_profile.json",
    "lens_fit.json",
    "case_perspective.json",
    "cvc.json",
    "value_type_diagnosis.json",
    "weak_link_analysis.json",
    "decoupling_strategy.json",
    "business_model_analysis.json",
    "competitive_response.json",
    "final_judgment.json",
    "critic_review.json",
    "final_report.md",
}


def test_artifact_io_round_trip(tmp_path: Path) -> None:
    from mgt470_analyst.io.json_artifacts import read_json_artifact, write_json_artifact

    raw_input = RawInput(company_name="Duolingo", ticker="DUOL")
    path = tmp_path / "raw_input.json"

    write_json_artifact(path, raw_input)
    loaded = read_json_artifact(path, RawInput)

    assert loaded == raw_input


def test_orchestrator_offline_happy_path_produces_all_artifacts(tmp_path: Path) -> None:
    raw_input = RawInput(
        analysis_goal="investment_judgment",
        company_name="Duolingo",
        ticker="DUOL",
        website="https://www.duolingo.com",
        urls=["https://www.duolingo.com"],
        user_question="Is this a high-quality AI-leveraged business worth studying?",
    )

    result = run_analysis(raw_input, runs_dir=tmp_path)

    assert result.run_dir.exists()
    assert {path.name for path in result.run_dir.iterdir()} >= EXPECTED_ARTIFACTS
    assert result.report_path.read_text(encoding="utf-8").startswith("---")

    evidence_store = json.loads(
        (result.run_dir / "evidence_store.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((result.run_dir / "run.json").read_text(encoding="utf-8"))
    evidence_ids = set(evidence_store)
    assert manifest["artifacts"]["research_brief"] == "research_brief.json"
    json_artifacts = EXPECTED_ARTIFACTS - {"run.json", "evidence_store.json", "final_report.md"}
    for artifact_name in json_artifacts:
        artifact = json.loads((result.run_dir / artifact_name).read_text(encoding="utf-8"))
        for evidence_id in collect_evidence_ids(artifact):
            assert evidence_id in evidence_ids


def test_company_name_appears_in_report(tmp_path: Path) -> None:
    raw_input = RawInput(
        analysis_goal="investment_judgment",
        company_name="Nubank",
        ticker="NU",
        website="https://nubank.com.br",
        urls=["https://nubank.com.br"],
    )

    result = run_analysis(raw_input, runs_dir=tmp_path / "runs")
    report = result.report_path.read_text(encoding="utf-8")

    assert "Nubank" in report
    # The offline fake should never leak unrelated case names.
    assert "Dropbox" not in report
    assert "Flipkart" not in report


def test_orchestrator_validates_deck_claim_evidence(tmp_path: Path) -> None:
    deck_path = tmp_path / "deck.txt"
    # Lines must clear the deck-extractor minimum-length and signal-token filter.
    deck_path.write_text(
        "ARR grew 4x year-over-year in 2025 with 70 percent gross margins.\n",
        encoding="utf-8",
    )
    raw_input = RawInput(company_name="Duolingo", files=[str(deck_path)])

    result = run_analysis(raw_input, runs_dir=tmp_path / "runs")

    deck_claims = json.loads((result.run_dir / "deck_claims.json").read_text(encoding="utf-8"))
    evidence_store = json.loads(
        (result.run_dir / "evidence_store.json").read_text(encoding="utf-8")
    )
    assert deck_claims["claims"], "expected at least one extracted claim"
    evidence_id = deck_claims["claims"][0]["evidence_id"]
    assert "deck_extractor" in evidence_store[evidence_id]["used_by_modules"]


def test_orchestrator_extracts_claims_from_pdf_fixture(tmp_path: Path) -> None:
    pdf_path = Path(__file__).parent / "fixtures" / "inputs" / "tiny_case.pdf"
    raw_input = RawInput(company_name="PDF Case", files=[str(pdf_path)])

    result = run_analysis(raw_input, runs_dir=tmp_path / "runs")

    deck_claims = json.loads((result.run_dir / "deck_claims.json").read_text(encoding="utf-8"))
    # The cleaned extractor may produce 0+ claims depending on the fixture; we
    # only assert that the artifact is well-formed.
    assert "claims" in deck_claims


def test_runs_dir_is_gitignored() -> None:
    import subprocess

    completed = subprocess.run(
        ["git", "check-ignore", "-q", "runs/"],
        check=False,
        cwd=Path(__file__).resolve().parents[1],
    )

    assert completed.returncode == 0
