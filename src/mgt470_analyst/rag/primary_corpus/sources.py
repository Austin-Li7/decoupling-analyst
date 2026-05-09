from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceSpec:
    kind: str
    title: str
    url: str
    source: str
    use_existing_captions: bool = True


@dataclass(frozen=True)
class PrimarySources:
    articles: list[SourceSpec]
    books: list[SourceSpec]
    talks: list[SourceSpec]

    @property
    def text_sources(self) -> list[SourceSpec]:
        return [*self.articles, *self.books]


def default_sources_path() -> Path:
    return Path(__file__).with_name("sources.yaml")


def load_sources(path: Path | str | None = None) -> PrimarySources:
    source_path = Path(path) if path else default_sources_path()
    data = _load_yaml(source_path)
    return PrimarySources(
        articles=_load_group(data, "articles", "article"),
        books=_load_group(data, "books", "book"),
        talks=_load_group(data, "talks", "talk"),
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"sources.yaml must contain a mapping at top level: {path}")
    return loaded


def _load_group(data: dict[str, Any], key: str, kind: str) -> list[SourceSpec]:
    raw_items = data.get(key) or []
    if not isinstance(raw_items, list):
        raise ValueError(f"{key} must be a list in sources.yaml")

    items: list[SourceSpec] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError(f"{key} entries must be mappings")
        title = str(raw.get("title") or "").strip()
        url = str(raw.get("url") or "").strip()
        if not title or not url:
            raise ValueError(f"{key} entries require title and url")
        items.append(
            SourceSpec(
                kind=kind,
                title=title,
                url=url,
                source=str(raw.get("source") or key).strip(),
                use_existing_captions=bool(raw.get("use_existing_captions", True)),
            )
        )
    return items
