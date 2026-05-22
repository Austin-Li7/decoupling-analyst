from pathlib import Path

import streamlit_app


def test_load_portfolio_data_uses_existing_artifacts() -> None:
    data = streamlit_app.load_portfolio_data(Path("."))

    assert data["aggregate"]["exact_pct"] == 57
    assert data["aggregate"]["exact_or_partial_pct"] == 81
    assert data["featured_case"]["company"] == "Birchbox"
    assert data["featured_case"]["top_weak_link"]["activity_id"] == "A3"
    assert "study_more" in data["featured_case"]["final_judgment"]["judgment"]


def test_render_cvc_html_highlights_featured_weak_link() -> None:
    data = streamlit_app.load_portfolio_data(Path("."))
    diagram = streamlit_app.render_cvc_html(data["featured_case"])

    assert "weak" in diagram
    assert "Step 3" in diagram
    assert "Evaluate products" in diagram


def test_architecture_html_contains_pipeline_steps() -> None:
    diagram = streamlit_app.render_architecture_html()

    assert "Grounded retrieval" in diagram
    assert "Grounding gate" in diagram
    assert "14 typed modules" in diagram


def test_deployment_files_exist() -> None:
    assert Path("streamlit_app.py").exists()
    assert Path("requirements.txt").read_text(encoding="utf-8").strip().startswith(
        "streamlit"
    )
