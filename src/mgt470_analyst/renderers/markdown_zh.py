from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.renderers.mermaid import render_cvc_flowchart

LOGGER = logging.getLogger(__name__)

SHORT_TRANSLATIONS = {
    "business_model": "商业模式",
    "capture": "价值捕获",
    "create": "价值创造",
    "decoupling": "解构",
    "disruptor": "颠覆者",
    "erode": "价值侵蚀",
    "full_decoupling": "完整解构",
    "high": "高",
    "incumbent": "在位者",
    "low": "低",
    "low_end": "低端切入",
    "medium": "中等",
    "new_market": "新市场",
    "strategic_memo": "战略备忘录",
    "study_more": "继续研究",
    "tech_substitution": "技术替代",
    "transitioning": "转型中",
    "unclear": "不明确",
}


class TranslationBatch(BaseModel):
    translations: dict[str, str] = Field(default_factory=dict)


def render_report_zh(context: dict[str, Any], client: LLMClient | None = None) -> str:
    company = str(context.get("company_name") or "Unknown Company")
    final = _as_dict(context.get("final_judgment"))
    lens = _as_dict(context.get("lens_fit"))
    perspective = _as_dict(context.get("case_perspective"))
    decoupling = _as_dict(context.get("decoupling_strategy"))
    primary = _as_dict(decoupling.get("primary_decoupling"))
    critic = _as_dict(context.get("critic_review"))
    cvc = [_as_dict(item) for item in context.get("cvc", [])]
    values = [_as_dict(item) for item in context.get("values", [])]
    weak_link = _top_weak_link(context)
    weak_activity = _activity_for_id(cvc, weak_link.get("activity_id"))

    fields = _translation_fields(final, primary, critic, weak_link, cvc)
    translations = _translate_fields(fields, client=client)
    zh_cvc = []
    for activity in cvc:
        translated_activity = translations.get(
            f"activity_{activity.get('id')}",
            activity.get("activity", ""),
        )
        zh_cvc.append(
            {**activity, "activity": _clip(translated_activity, 24), "current_provider": ""}
        )
    diagram = render_cvc_flowchart(
        zh_cvc,
        values,
        highlight_activity_id=weak_link.get("activity_id"),
    )
    high_issues = _high_issues(critic)
    while len(high_issues) < 3:
        high_issues.append("（暂无更多高严重度缺口）")

    lens_name = _short(lens.get("primary_type"))
    lens_confidence = _short(lens.get("confidence"))
    perspective_name = _short(perspective.get("perspective"))
    perspective_confidence = _short(perspective.get("confidence"))
    fit_score = lens.get("decoupling_fit_score", "?")
    weak_step = weak_activity.get("step", "?")
    weak_activity_zh = translations.get(
        f"activity_{weak_activity.get('id')}",
        weak_activity.get("activity", "未知活动"),
    )
    weak_activity_zh = _clip(weak_activity_zh, 28)
    falsifiable = translations.get("falsifiable_claim") or "（无明确可证伪主张）"
    weak_rationale = translations.get("weak_link_rationale") or weak_link.get("rationale", "")
    wedge_rationale = translations.get("wedge_rationale") or primary.get(
        "why_customer_switches",
        "",
    )

    return f"""---
company: {company}
language: zh
---

# {company} 数字解构分析摘要

> [!important] 一句话结论
> {_clip(translations.get("recommended_action") or final.get("one_sentence_thesis", ""), 120)}

## 镜头判断
- **主透镜**：{lens_name} （置信度：{lens_confidence}，契合度：{fit_score}）
- **案例视角**：{perspective_name} （置信度：{perspective_confidence}）

## 客户价值链与弱链

{diagram}

**弱链定位**：第 {weak_step} 步「{weak_activity_zh}」—— {_clip(weak_rationale, 110)}

## 推荐切入点（The Wedge）

- **切什么**：{translations.get("activity_to_decouple") or primary.get("activity_to_decouple", "")}
- **为什么**：{_clip(wedge_rationale, 150)}
- **最大风险**：{_clip(translations.get("biggest_risk") or final.get("biggest_risk", ""), 110)}

## 信心 & 关键缺口

- **整体置信度**：{lens_confidence}；最终判断为「{_short(final.get("judgment"))}」。
- **关键缺口**：
  1. {_clip(translations.get("critic_1") or high_issues[0], 90)}
  2. {_clip(translations.get("critic_2") or high_issues[1], 90)}
  3. {_clip(translations.get("critic_3") or high_issues[2], 90)}

## 6 个月后可回看的具体主张

{falsifiable}

---
完整英文报告见 [`final_report.md`](final_report.md)
"""


def _translation_fields(
    final: dict[str, Any],
    primary: dict[str, Any],
    critic: dict[str, Any],
    weak_link: dict[str, Any],
    cvc: list[dict[str, Any]],
) -> dict[str, str]:
    issues = _high_issues(critic)
    fields = {
        "recommended_action": final.get("recommended_action")
        or final.get("one_sentence_thesis", ""),
        "weak_link_rationale": weak_link.get("rationale", ""),
        "activity_to_decouple": primary.get("activity_to_decouple", ""),
        "wedge_rationale": primary.get("why_customer_switches")
        or primary.get("new_offering", ""),
        "biggest_risk": final.get("biggest_risk", ""),
        "falsifiable_claim": _falsifiable_claim(final),
    }
    for index, issue in enumerate(issues[:3], start=1):
        fields[f"critic_{index}"] = issue
    for activity in cvc:
        activity_id = activity.get("id")
        if activity_id:
            fields[f"activity_{activity_id}"] = activity.get("activity", "")
    return {key: str(value) for key, value in fields.items() if value}


def _translate_fields(fields: dict[str, str], client: LLMClient | None = None) -> dict[str, str]:
    if not fields:
        return {}
    client = client or get_default_client()
    prompt = (
        "Translate this JSON object from English to concise business Chinese. "
        "Keep the same keys. Return JSON as {\"translations\": {...}}. "
        "Do not add explanation.\n\n"
        + json.dumps(fields, ensure_ascii=False)
    )
    try:
        batch = client.structured(
            role="smart",
            system="You translate executive strategy prose into concise Simplified Chinese.",
            user=prompt,
            schema=TranslationBatch,
            max_tokens=1500,
            max_retries=0,
        )
        return batch.translations
    except Exception as exc:
        LOGGER.warning("Chinese digest translation failed; using English fallback: %s", exc)
        return {}


def _short(value: Any) -> str:
    text = str(value or "")
    return SHORT_TRANSLATIONS.get(text, text or "未知")


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {}


def _top_weak_link(context: dict[str, Any]) -> dict[str, Any]:
    weak_links = _as_dict(context.get("weak_links"))
    ranked = weak_links.get("ranked_weak_links")
    if isinstance(ranked, list) and ranked:
        return _as_dict(ranked[0])
    return {"rationale": str(context.get("weak_link") or "")}


def _activity_for_id(cvc: list[dict[str, Any]], activity_id: str | None) -> dict[str, Any]:
    if not activity_id:
        return {}
    return next((item for item in cvc if item.get("id") == activity_id), {})


def _high_issues(critic: dict[str, Any]) -> list[str]:
    return [
        str(issue.get("issue", ""))
        for issue in critic.get("citation_issues", [])
        if issue.get("severity") == "high" and issue.get("issue")
    ]


def _falsifiable_claim(final: dict[str, Any]) -> str:
    actions = final.get("staged_actions") or []
    if actions:
        return f"到 2026-11-09，{actions[0]}"
    return "（无明确可证伪主张）"


def _clip(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
