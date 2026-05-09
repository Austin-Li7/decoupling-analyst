"""Mermaid renderers for CVC, staged path, and recoupling 2x2.

These produce Mermaid code blocks that Obsidian renders natively and most
Markdown viewers (GitHub, MkDocs Material, VS Code preview) also support.
"""

from __future__ import annotations

import re
from typing import Any

VALUE_TYPE_STYLE = {
    "create": "fill:#d1f7c4,stroke:#1f8a3a,color:#0b3d18",
    "erode": "fill:#ffd6d6,stroke:#b22222,color:#5a0d0d",
    "capture": "fill:#d6e4ff,stroke:#1c4ed8,color:#0a1f5e",
}

STAGE_STYLE = {
    "preserve": "fill:#fff7d6,stroke:#a07b00,color:#3a2e00",
    "light": "fill:#d1f7c4,stroke:#1f8a3a,color:#0b3d18",
    "medium": "fill:#d6e4ff,stroke:#1c4ed8,color:#0a1f5e",
    "heavy": "fill:#ffd6d6,stroke:#b22222,color:#5a0d0d",
    "default": "fill:#eeeeee,stroke:#666,color:#222",
}


WEAK_LINK_STYLE = "fill:#ffedd5,stroke:#c2410c,stroke-width:4px,color:#431407"


def render_cvc_flowchart(
    cvc_activities: list[dict[str, Any]],
    values: list[dict[str, Any]],
    *,
    highlight_activity_id: str | None = None,
) -> str:
    """Left-to-right CVC flowchart, color-coded by value type."""
    if not cvc_activities:
        return ""

    value_by_id = {v.get("activity_id"): v.get("value_type", "") for v in values}

    lines = ["```mermaid", "flowchart LR"]
    style_lines: list[str] = []

    for activity in cvc_activities:
        node_id = _safe_id(activity.get("id", ""))
        step = activity.get("step", "?")
        label = _escape(activity.get("activity", ""))
        provider = _escape(activity.get("current_provider", ""))
        provider_line = f"<br/><i>{provider}</i>" if provider else ""
        lines.append(f'    {node_id}["<b>Step {step}</b><br/>{label}{provider_line}"]')
        vt = value_by_id.get(activity.get("id"), "").lower()
        if vt in VALUE_TYPE_STYLE:
            style_lines.append(f"    style {node_id} {VALUE_TYPE_STYLE[vt]}")
        if highlight_activity_id and activity.get("id") == highlight_activity_id:
            style_lines.append(f"    style {node_id} {WEAK_LINK_STYLE}")

    # Sequential edges step → step+1
    sorted_acts = sorted(cvc_activities, key=lambda a: a.get("step", 0))
    for prev, curr in zip(sorted_acts, sorted_acts[1:], strict=False):
        lines.append(
            f"    {_safe_id(prev.get('id', ''))} --> {_safe_id(curr.get('id', ''))}"
        )

    lines.extend(style_lines)
    lines.append("```")

    legend = (
        "\n_Legend: green = creates value · red = erodes value · blue = captures value._"
    )
    return "\n".join(lines) + legend


def render_staged_path_flowchart(staged_actions: list[str]) -> str:
    """Top-down staged-path flowchart, grouped by phase tag.

    `staged_actions` items typically begin with a phase tag like
    "PRESERVE (...)", "LIGHT (...)", "MEDIUM (...)", "HEAVY (...)".
    We parse the tag and color the node accordingly. Items without a
    recognized tag fall through to the default style.
    """
    if not staged_actions:
        return ""

    lines = ["```mermaid", "flowchart TD"]
    style_lines: list[str] = []
    node_ids: list[str] = []
    for index, raw in enumerate(staged_actions, start=1):
        node_id = f"S{index}"
        node_ids.append(node_id)
        phase = _parse_phase(raw)
        # Strip any leading "PRESERVE (xxx):" / "LIGHT (yyy):" / etc.
        body = re.sub(
            r"^\s*(PRESERVE|LIGHT|MEDIUM|HEAVY|RESTRUCTURE|Layer\s*\([abc]\))[^:]*:\s*",
            "",
            raw,
            flags=re.IGNORECASE,
        )
        body = _truncate(_escape(body), 240)
        label = f"<b>{phase.upper()}</b><br/>{body}" if phase != "default" else body
        lines.append(f'    {node_id}["{label}"]')
        style_lines.append(f"    style {node_id} {STAGE_STYLE.get(phase, STAGE_STYLE['default'])}")

    for prev, curr in zip(node_ids, node_ids[1:], strict=False):
        lines.append(f"    {prev} --> {curr}")

    lines.extend(style_lines)
    lines.append("```")

    legend = (
        "\n_Legend: yellow = preserve · green = light · blue = medium · red = heavy._"
    )
    return "\n".join(lines) + legend


def render_recoupling_quadrant(
    likely_responses: list[dict[str, Any]], recoupling: dict[str, Any]
) -> str:
    """2x2 quadrant chart of incumbent capability vs incentive to recouple.

    The composite recoupling vulnerability point is plotted as 'Recoupling
    Risk', and each likely-response is plotted by inferred capability /
    severity-as-incentive.
    """
    cap_to_xy = {"high": 0.85, "medium": 0.5, "low": 0.15}

    lines = ["```mermaid", "quadrantChart"]
    lines.append("    title Incumbent Capability vs Incentive to Recouple")
    lines.append("    x-axis Low capability --> High capability")
    lines.append("    y-axis Low incentive --> High incentive")
    lines.append("    quadrant-1 High threat (capable + motivated)")
    lines.append("    quadrant-2 Motivated but blocked")
    lines.append("    quadrant-3 Slow / unlikely")
    lines.append("    quadrant-4 Capable but uninterested")

    cap = (recoupling.get("incumbent_capability_to_recouple") or "medium").lower()
    inc = (recoupling.get("incumbent_incentive_to_recouple") or "medium").lower()
    lines.append(
        f"    \"Recoupling Risk\": [{cap_to_xy.get(cap, 0.5):.2f}, {cap_to_xy.get(inc, 0.5):.2f}]"
    )

    seen: dict[str, int] = {}
    for response in likely_responses[:6]:
        rtype = (response.get("response_type") or "?").lower()
        severity = (response.get("severity") or "medium").lower()
        # Capability is implied by response type; rough heuristic mapping.
        capability_proxy = {
            "recouple": "high",
            "copy": "high",
            "acquire": "medium",
            "block": "medium",
            "subsidize": "high",
            "partner": "low",
        }.get(rtype, "medium")
        x = cap_to_xy.get(capability_proxy, 0.5)
        y = cap_to_xy.get(severity, 0.5)
        # Avoid identical labels (mermaid quadrantChart can't dedupe).
        seen[rtype] = seen.get(rtype, 0) + 1
        suffix = "" if seen[rtype] == 1 else f" ({seen[rtype]})"
        lines.append(f'    "{rtype}{suffix}": [{x:.2f}, {y:.2f}]')

    lines.append("```")
    return "\n".join(lines)


def _safe_id(value: str) -> str:
    """Mermaid node IDs must avoid spaces and special chars."""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "", value)
    return cleaned or "N"


def _escape(text: str) -> str:
    """Escape characters that break Mermaid node labels."""
    return (
        text.replace('"', "''")
        .replace("[", "(")
        .replace("]", ")")
        .replace("|", "/")
        .replace("\n", " ")
    )


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _parse_phase(text: str) -> str:
    head = text[:80].lower()
    for phase in ("preserve", "light", "medium", "heavy"):
        if phase in head:
            return phase
    if "restructure" in head:
        return "medium"
    if "layer (a)" in head or "layer a" in head:
        return "light"
    if "layer (b)" in head or "layer b" in head:
        return "medium"
    if "layer (c)" in head or "layer c" in head:
        return "heavy"
    return "default"
