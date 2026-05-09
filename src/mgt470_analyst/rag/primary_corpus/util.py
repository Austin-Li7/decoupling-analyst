from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_text(text: str, *, max_length: int = 80) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return (slug[:max_length].strip("-") or "source")


def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.removeprefix("www.")
    path = parsed.path.strip("/")
    bits = [host]
    if path:
        bits.append(path)
    query = parse_qs(parsed.query)
    if "v" in query and query["v"]:
        bits.append(query["v"][0])
    return slugify_text("-".join(bits))


def write_markdown(path: Path, *, title: str, url: str, source: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""\
---
title: {title}
url: {url}
source: {source}
corpus: primary
---

# {title}

Source: {url}

{body.strip()}
"""
    path.write_text(text, encoding="utf-8")
