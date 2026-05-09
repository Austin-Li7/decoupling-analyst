from __future__ import annotations

from pathlib import Path

from mgt470_analyst.rag.primary_corpus.sources import load_sources
from mgt470_analyst.rag.primary_corpus.util import slugify_url


def test_load_sources_yaml_parses_articles_books_and_talks(tmp_path: Path):
    sources_yaml = tmp_path / "sources.yaml"
    sources_yaml.write_text(
        """\
articles:
  - title: Decoupling and the Customer Value Chain
    url: https://www.decoupling.co/p/decoupling-and-the-customer-value-chain
    source: decoupling-io
books:
  - title: Unlocking the Customer Value Chain
    url: https://books.google.com/books?id=abc
    source: google-books
talks:
  - title: Thales Teixeira on Decoupling
    url: https://www.youtube.com/watch?v=abc123
    source: youtube
    use_existing_captions: true
""",
        encoding="utf-8",
    )

    sources = load_sources(sources_yaml)

    assert [s.title for s in sources.articles] == ["Decoupling and the Customer Value Chain"]
    assert sources.articles[0].kind == "article"
    assert sources.books[0].source == "google-books"
    assert sources.talks[0].use_existing_captions is True


def test_slugify_url_uses_meaningful_path_before_query():
    slug = slugify_url("https://www.youtube.com/watch?v=abc123&feature=share")

    assert slug == "youtube-com-watch-abc123"
