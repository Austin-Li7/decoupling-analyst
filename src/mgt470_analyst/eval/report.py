from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from mgt470_analyst.eval.scorer import CaseScore


@dataclass(frozen=True)
class AggregateScore:
    exact: int
    partial: int
    miss: int
    fabrications: int

    @property
    def total_fields(self) -> int:
        return self.exact + self.partial + self.miss

    @property
    def exact_pct(self) -> int:
        return round(self.exact / self.total_fields * 100) if self.total_fields else 0

    @property
    def exact_or_partial_pct(self) -> int:
        if not self.total_fields:
            return 0
        return round((self.exact + self.partial) / self.total_fields * 100)

    def to_json(self) -> dict:
        return {
            **asdict(self),
            "total_fields": self.total_fields,
            "exact_pct": self.exact_pct,
            "exact_or_partial_pct": self.exact_or_partial_pct,
        }


def aggregate_scores(scores: list[CaseScore]) -> AggregateScore:
    return AggregateScore(
        exact=sum(score.exact for score in scores),
        partial=sum(score.partial for score in scores),
        miss=sum(score.miss for score in scores),
        fabrications=sum(score.fabrications for score in scores),
    )


def scores_to_json(scores: list[CaseScore]) -> dict:
    aggregate = aggregate_scores(scores)
    return {
        "source": "human-reviewed calibration_report.md files",
        "aggregate": aggregate.to_json(),
        "cases": [score.to_json() for score in scores],
    }


def render_markdown_summary(scores: list[CaseScore]) -> str:
    aggregate = aggregate_scores(scores)
    rows = [
        "| Company | Exact | Partial | Miss | Fabrications |",
        "|---|---:|---:|---:|---:|",
    ]
    for score in scores:
        rows.append(
            f"| {score.company} | {score.exact} | {score.partial} | "
            f"{score.miss} | {score.fabrications} |"
        )
    rows.append(
        f"| **Total** | **{aggregate.exact}** | **{aggregate.partial}** | "
        f"**{aggregate.miss}** | **{aggregate.fabrications}** |"
    )
    return (
        "# Calibration Summary\n\n"
        "Generated from the human-reviewed `calibration_report.md` files. "
        "This is a deterministic offline regression artifact, not a live LLM judge.\n\n"
        + "\n".join(rows)
        + "\n\n"
        f"Across {aggregate.total_fields} scored fields: "
        f"**{aggregate.exact_pct}% exact** and "
        f"**{aggregate.exact_or_partial_pct}% exact-or-partial**.\n"
    )


def write_json_report(scores: list[CaseScore], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(scores_to_json(scores), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_markdown_summary(scores: list[CaseScore], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown_summary(scores), encoding="utf-8")
