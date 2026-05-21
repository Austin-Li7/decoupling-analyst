from pathlib import Path

from scripts.build_showcase import build_showcase_html, load_showcase_data


def test_showcase_builder_parses_current_calibration_totals() -> None:
    data = load_showcase_data(Path("."))
    totals = data.totals

    assert totals.exact == 12
    assert totals.partial == 5
    assert totals.miss == 4
    assert totals.fabrications == 2


def test_showcase_html_contains_required_sections_without_secrets() -> None:
    html = build_showcase_html(load_showcase_data(Path(".")))

    assert "https://cdn.jsdelivr.net/npm/mermaid" in html
    assert "Birchbox" in html
    assert "<td>Total</td>" in html
    assert "12</td>" in html
    assert "5</td>" in html
    assert "4</td>" in html
    assert ".env" not in html
    assert "OPENAI_API_KEY" not in html
