#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

LIVENESS_RE = re.compile(r"URL liveness gate: kept (?P<kept>\d+)/(?P<total>\d+)")
SEVERITIES = ("high", "medium", "low")


def build_case(run_dir: Path, slug: str, cases_root: Path = Path("cases")) -> Path:
    run = _read_json(run_dir / "run.json")
    research = _read_json(run_dir / "research_brief.json")
    evidence = _read_json(run_dir / "evidence_store.json")
    critic = _read_json(run_dir / "critic_review.json")
    run_date = str(run["created_at"])[:10]
    case_dir = cases_root / "_archive" / f"{slug}-{run_date.replace('-', '')}"
    if case_dir.exists():
        raise FileExistsError(f"Case folder already exists: {case_dir}")

    (cases_root / "_archive").mkdir(parents=True, exist_ok=True)
    shutil.copytree(run_dir, case_dir / "run")
    _write_review(case_dir / "review.md", cases_root / "TEMPLATE_review.md", run, research)
    _write_json(
        case_dir / "baseline_metrics.json",
        _metrics(run_dir, run, research, evidence, critic),
    )
    return case_dir


def _metrics(
    run_dir: Path,
    run: dict[str, Any],
    research: dict[str, Any],
    evidence: dict[str, Any],
    critic: dict[str, Any],
) -> dict[str, Any]:
    kept = len(research.get("sources", []))
    total = _liveness_total(run_dir) or kept
    severity_counts = {severity: 0 for severity in SEVERITIES}
    for issue in critic.get("citation_issues", []):
        severity = issue.get("severity")
        if severity in severity_counts:
            severity_counts[severity] += 1
    return {
        "company_name": research.get("company_name") or run["input"]["company_name"],
        "run_id": run["run_id"],
        "run_date": str(run["created_at"])[:10],
        "sources_total": total,
        "sources_kept_after_liveness": kept,
        "liveness_pass_rate": round(kept / total, 3) if total else 0.0,
        "evidence_store_entries": len(evidence),
        "modules_completed": sum(
            1 for module in run.get("modules", []) if module.get("status") == "ok"
        ),
        "modules_with_conflicts_flagged": _modules_with_conflicts(run_dir),
        "critic_review_severity_counts": severity_counts,
        "research_backend": "gpt_researcher",
        "rag_enabled": True,
        "wall_clock_seconds": _wall_clock_seconds(run_dir),
    }


def _liveness_total(run_dir: Path) -> int | None:
    log_path = run_dir / "run.log"
    if not log_path.exists():
        return None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = LIVENESS_RE.search(line)
        if match:
            return int(match.group("total"))
    return None


def _modules_with_conflicts(run_dir: Path) -> int:
    count = 0
    for path in run_dir.glob("*.json"):
        if path.name in {"run.json", "evidence_store.json"}:
            continue
        data = _read_json(path)
        conflicts = data.get("conflicts")
        if isinstance(conflicts, list) and conflicts:
            count += 1
    return count


def _wall_clock_seconds(run_dir: Path) -> int:
    paths = [path for path in run_dir.iterdir() if path.is_file()]
    if not paths:
        return 0
    first = min(path.stat().st_mtime for path in paths)
    last = max(path.stat().st_mtime for path in paths)
    return max(0, round(last - first))


def _write_review(
    path: Path,
    template_path: Path,
    run: dict[str, Any],
    research: dict[str, Any],
) -> None:
    template = template_path.read_text(encoding="utf-8")
    headings = [line for line in template.splitlines() if line.startswith("## ")]
    if not headings:
        raise ValueError(f"No review section headings found in {template_path}")
    run_date = str(run["created_at"])[:10]
    lines = [
        f"# Case Review: {research.get('company_name') or run['input']['company_name']}",
        "",
        f"**Run ID:** {run['run_id']}",
        f"**Run date:** {run_date}",
        "**Reviewer:** ",
        "**Time spent reviewing (minutes):** ",
        "",
    ]
    for heading in headings:
        lines.extend([heading, ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an archived case study folder.")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("slug")
    parser.add_argument("--cases-root", type=Path, default=Path("cases"))
    args = parser.parse_args()
    case_dir = build_case(args.run_dir, args.slug, args.cases_root)
    print(case_dir)


if __name__ == "__main__":
    main()
