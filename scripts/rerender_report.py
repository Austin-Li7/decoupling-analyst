#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

from mgt470_analyst.llm.client import (
    finish_llm_cost_tracking,
    get_default_client,
    start_llm_cost_tracking,
    use_llm_module,
)
from mgt470_analyst.renderers.markdown import render_report
from mgt470_analyst.renderers.markdown_zh import render_report_zh


def rerender(run_dir: Path) -> tuple[Path, Path | None]:
    context = _load_context(run_dir)
    report_path = run_dir / "final_report.md"
    report_path.write_text(render_report(context), encoding="utf-8")

    zh_path: Path | None = None
    if _generate_zh_digest():
        zh_path = run_dir / "final_report_zh.md"
        temp_cost_path = run_dir / ".final_report_zh_cost.json"
        start_llm_cost_tracking(
            run_id=_run_id(run_dir, context),
            company_name=str(context["company_name"]),
            artifact_path=temp_cost_path,
        )
        client = get_default_client()
        zh_path.write_text(
            _render_zh_with_cost(context, client),
            encoding="utf-8",
        )
        finish_llm_cost_tracking()
        _merge_zh_cost(run_dir / "cost_summary.json", temp_cost_path)
        temp_cost_path.unlink(missing_ok=True)
    return report_path, zh_path


def _render_zh_with_cost(context: dict[str, Any], client: Any) -> str:
    with use_llm_module("final_report_zh"):
        return render_report_zh(render_report(context), client=client)


def _run_id(run_dir: Path, context: dict[str, Any]) -> str:
    run_path = run_dir / "run.json"
    if run_path.exists():
        return str(_read_json(run_path).get("run_id") or run_dir.name)
    return str(context.get("run_id") or run_dir.name)


def _merge_zh_cost(cost_summary_path: Path, zh_cost_path: Path) -> None:
    if not zh_cost_path.exists():
        return
    zh_cost = _read_json(zh_cost_path)
    zh_bucket = zh_cost.get("by_module", {}).get("final_report_zh")
    if not zh_bucket:
        return
    if cost_summary_path.exists():
        summary = _read_json(cost_summary_path)
    else:
        summary = {
            "run_id": zh_cost.get("run_id", ""),
            "company_name": zh_cost.get("company_name", ""),
            "by_module": {},
            "notes": [],
        }
    summary.setdefault("by_module", {})["final_report_zh"] = zh_bucket
    buckets = summary["by_module"].values()
    summary["total_input_tokens"] = sum(int(bucket.get("input_tokens") or 0) for bucket in buckets)
    summary["total_output_tokens"] = sum(
        int(bucket.get("output_tokens") or 0) for bucket in summary["by_module"].values()
    )
    summary["total_cost_usd"] = round(
        sum(float(bucket.get("cost_usd") or 0.0) for bucket in summary["by_module"].values()),
        6,
    )
    notes = summary.setdefault("notes", [])
    note = "final_report_zh cost added by scripts/rerender_report.py."
    if note not in notes:
        notes.append(note)
    cost_summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def _load_context(run_dir: Path) -> dict[str, Any]:
    run = _read_json(run_dir / "run.json")
    research = _read_json(run_dir / "research_brief.json")
    company_profile = _read_json(run_dir / "company_profile.json")
    lens_fit = _read_json(run_dir / "lens_fit.json")
    case_perspective = _read_json(run_dir / "case_perspective.json")
    cvc_artifact = _read_json(run_dir / "cvc.json")
    values_artifact = _read_json(run_dir / "value_type_diagnosis.json")
    weak_links = _read_json(run_dir / "weak_link_analysis.json")
    decoupling = _read_json(run_dir / "decoupling_strategy.json")
    business_model = _read_json(run_dir / "business_model_analysis.json")
    competitive = _read_json(run_dir / "competitive_response.json")
    final_judgment = _read_json(run_dir / "final_judgment.json")
    critic = _read_json(run_dir / "critic_review.json")
    evidence_store = _read_json(run_dir / "evidence_store.json")

    cvc = cvc_artifact.get("activities", [])
    values = values_artifact.get("activities", [])
    likely_responses = competitive.get("likely_responses", [])
    return {
        "company_name": research.get("company_name")
        or company_profile.get("company", {}).get("name")
        or run.get("input", {}).get("company_name")
        or "Unknown Company",
        "company_profile": company_profile,
        "lens_fit": lens_fit,
        "case_perspective": case_perspective,
        "final_judgment": final_judgment,
        "critic_review": critic,
        "evidence_store": evidence_store,
        "weak_link": _weak_link_summary(weak_links, cvc),
        "weak_links": weak_links,
        "decoupling": decoupling.get("primary_decoupling", {}).get("new_offering", ""),
        "decoupling_strategy": decoupling,
        "business_model": business_model.get("value_creation", ""),
        "competitive_response": (
            likely_responses[0].get("description", "") if likely_responses else ""
        ),
        "competitive": competitive,
        "recoupling": competitive.get("recoupling_vulnerability", {}),
        "cvc": cvc,
        "values": values,
        "research": research,
    }


def _weak_link_summary(weak_links: dict[str, Any], cvc: list[dict[str, Any]]) -> str:
    ranked = weak_links.get("ranked_weak_links") or []
    if not ranked:
        return "Unknown weak link"
    top = ranked[0]
    activity = next((item for item in cvc if item.get("id") == top.get("activity_id")), {})
    label = activity.get("activity") or top.get("activity_id") or "Unknown activity"
    score = top.get("score", "?")
    return f"{label} scored {score}: {top.get('rationale', '')}"


def _generate_zh_digest() -> bool:
    return os.getenv("MGT470_GENERATE_ZH_DIGEST", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    load_dotenv()
    if len(sys.argv) != 2:
        raise SystemExit("Usage: scripts/rerender_report.py <run_dir>")
    report_path, zh_path = rerender(Path(sys.argv[1]))
    print(report_path)
    if zh_path is not None:
        print(zh_path)


if __name__ == "__main__":
    main()
