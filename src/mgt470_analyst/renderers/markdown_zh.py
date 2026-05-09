from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from pydantic import BaseModel, Field

from mgt470_analyst.llm.client import LLMClient, get_default_client

LOGGER = logging.getLogger(__name__)

FENCED_BLOCK_RE = re.compile(r"```[\s\S]*?```")
NODE_LABEL_RE = re.compile(r'(\w+\[")([^"]+)("\])')


class MarkdownTranslation(BaseModel):
    markdown: str


class MermaidLabelTranslation(BaseModel):
    labels: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class ProtectedBlock:
    placeholder: str
    content: str


def render_report_zh(english_markdown: str, client: LLMClient | None = None) -> str:
    client = client or get_default_client()
    try:
        protected_markdown, blocks = _protect_fenced_blocks(english_markdown, client)
        translated = _translate_markdown_body(protected_markdown, client)
        restored = _restore_blocks(translated, blocks)
        return _set_frontmatter_language(restored).replace("…", "")
    except Exception as exc:
        LOGGER.warning("Chinese report translation failed; using English fallback: %s", exc)
        return _fallback_report(english_markdown)


def _protect_fenced_blocks(markdown: str, client: LLMClient) -> tuple[str, list[ProtectedBlock]]:
    blocks: list[ProtectedBlock] = []

    def replace(match: re.Match[str]) -> str:
        index = len(blocks)
        content = match.group(0)
        if content.startswith("```mermaid"):
            content = _translate_mermaid_labels(content, client)
        placeholder = f"<<<MERMAID_BLOCK_{index}>>>"
        if not content.startswith("```mermaid"):
            placeholder = f"<<<CODE_BLOCK_{index}>>>"
        blocks.append(ProtectedBlock(placeholder=placeholder, content=content))
        return placeholder

    return FENCED_BLOCK_RE.sub(replace, markdown), blocks


def _translate_markdown_body(markdown: str, client: LLMClient) -> str:
    prompt = (
        "You are translating a strategic analysis report from English to Simplified "
        "Chinese.\n"
        "Hard rules:\n"
        "1. Preserve ALL markdown structure verbatim: # / ## / ### levels, > callout "
        "markers, | table delimiters, <details> / <summary> tags, code fences (```), "
        "[!important] [!note] tags.\n"
        "2. DO NOT translate placeholder tokens like <<<MERMAID_BLOCK_0>>> or "
        "<<<CODE_BLOCK_0>>>.\n"
        "3. DO NOT translate URLs, file paths, evidence IDs (E1, E2, S0, S1, F1, F2), "
        "or technical identifiers; translate adjacent prose but keep identifiers in "
        "English in parentheses when helpful.\n"
        "4. Translate every prose sentence completely. Do not abbreviate, summarize, "
        "or use ellipsis (... or …). The output must be the same length-class as input.\n"
        "5. Keep numbers, percentages, and currency amounts as-is.\n"
        "6. Section heading translations should be natural Chinese, e.g. Executive "
        "Summary -> 执行摘要, Weak Link -> 薄弱环节, Decoupling Strategy -> 解构策略, "
        "Recoupling Risk -> 再耦合风险, Critic Review -> 批判性复审.\n"
        "Output the full translated markdown, nothing else: no preamble, no commentary.\n\n"
        "MARKDOWN:\n"
        f"{markdown}"
    )
    text_method = getattr(client, "text", None)
    if callable(text_method):
        translated = text_method(
            role="smart",
            system="Translate markdown reports into complete Simplified Chinese.",
            user=prompt,
            reasoning_effort="low",
            max_tokens=16000,
        )
        translated = _unwrap_markdown_payload(str(translated))
        if not translated.strip():
            raise RuntimeError("translation returned empty markdown")
        return translated
    result = client.structured(
        role="smart",
        system="Translate markdown reports into complete Simplified Chinese.",
        user=prompt,
        schema=MarkdownTranslation,
        reasoning_effort="low",
        max_tokens=16000,
        max_retries=0,
    )
    if not result.markdown.strip():
        raise RuntimeError("translation returned empty markdown")
    return result.markdown


def _translate_mermaid_labels(block: str, client: LLMClient) -> str:
    labels = [match.group(2) for match in NODE_LABEL_RE.finditer(block)]
    if not labels:
        return block
    prompt = (
        "Translate these Mermaid diagram node labels to concise Simplified Chinese. "
        "Preserve embedded HTML tags such as <b>, </b>, <br/>, and <i>. "
        "Do not translate node IDs, because they are not included here. "
        "Return JSON as {\"labels\": [ ... ]} with the same order and length.\n\n"
        + json.dumps(labels, ensure_ascii=False)
    )
    try:
        result = client.structured(
            role="smart",
            system="Translate Mermaid node labels while preserving label markup.",
            user=prompt,
            schema=MermaidLabelTranslation,
            max_tokens=2500,
            max_retries=0,
        )
    except Exception as exc:
        LOGGER.warning("Mermaid label translation failed; keeping English labels: %s", exc)
        return block
    if len(result.labels) != len(labels):
        LOGGER.warning(
            "Mermaid label translation count mismatch; keeping English labels: %s != %s",
            len(result.labels),
            len(labels),
        )
        return block
    translated_iter = iter(result.labels)
    return NODE_LABEL_RE.sub(
        lambda match: f'{match.group(1)}{next(translated_iter)}{match.group(3)}',
        block,
    )


def _restore_blocks(markdown: str, blocks: list[ProtectedBlock]) -> str:
    for block in blocks:
        markdown = markdown.replace(block.placeholder, block.content)
    return markdown


def _unwrap_markdown_payload(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("{"):
        return text
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return text
    if isinstance(payload, dict) and isinstance(payload.get("markdown"), str):
        return payload["markdown"]
    return text


def _set_frontmatter_language(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return f"---\nlanguage: zh\n---\n\n{markdown}"
    end = markdown.find("\n---", 4)
    if end == -1:
        return f"---\nlanguage: zh\n---\n\n{markdown}"
    frontmatter = markdown[4:end].splitlines()
    body = markdown[end + 4 :]
    replaced = False
    next_frontmatter: list[str] = []
    for line in frontmatter:
        if line.startswith("language:"):
            next_frontmatter.append("language: zh")
            replaced = True
        else:
            next_frontmatter.append(line)
    if not replaced:
        next_frontmatter.append("language: zh")
    return "---\n" + "\n".join(next_frontmatter).rstrip() + "\n---" + body


def _fallback_report(english_markdown: str) -> str:
    banner = (
        "> ⚠️ 自动翻译失败，以下为英文原文 "
        "(translation failed; English fallback)\n\n"
    )
    markdown = _set_frontmatter_language(english_markdown)
    if markdown.startswith("---\n"):
        end = markdown.find("\n---", 4)
        if end != -1:
            return markdown[: end + 4] + "\n\n" + banner + markdown[end + 4 :].lstrip()
    return banner + markdown
