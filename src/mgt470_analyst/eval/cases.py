from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SCORING_FIELDS: tuple[str, ...] = (
    "CVC step count",
    "Weak link identified",
    "Decoupling pattern",
    "Decoupled activity",
    "Strategic takeaway",
    "Final case perspective (disruptor/incumbent/pivot)",
    "Lens fit",
)


@dataclass(frozen=True)
class EvalCase:
    slug: str
    company: str
    ground_truth_path: Path
    calibration_report_path: Path
    system_run_path: Path
    scoring_fields: tuple[str, ...] = SCORING_FIELDS


def discover_eval_cases(calibration_dir: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for case_dir in sorted(path for path in calibration_dir.iterdir() if path.is_dir()):
        report_path = case_dir / "calibration_report.md"
        ground_truth_path = case_dir / "ground_truth.md"
        system_run_path = case_dir / "system_run"
        if not report_path.exists():
            continue
        cases.append(
            EvalCase(
                slug=case_dir.name,
                company=_company_name_from_slug_or_report(case_dir.name, report_path),
                ground_truth_path=ground_truth_path,
                calibration_report_path=report_path,
                system_run_path=system_run_path,
            )
        )
    return cases


def _company_name_from_slug_or_report(slug: str, report_path: Path) -> str:
    import re

    text = report_path.read_text(encoding="utf-8")
    match = re.search(r"^#\s+(.+?)\s+Calibration Report", text, flags=re.MULTILINE)
    if match:
        return match.group(1)
    return slug.replace("-", " ").title()
