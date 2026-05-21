from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Literal

from pydantic import BaseModel, Field

from mgt470_analyst.eval.cases import EvalCase
from mgt470_analyst.llm.client import LLMClient, get_default_client

ScoreStatus = Literal["exact", "partial", "miss"]

REQUIRED_ARTIFACTS = (
    "cvc.json",
    "weak_link_analysis.json",
    "decoupling_strategy.json",
    "final_judgment.json",
    "lens_fit.json",
    "case_perspective.json",
)


class SemanticJudgeResult(BaseModel):
    status: ScoreStatus
    rationale: str = Field(min_length=1)


@dataclass(frozen=True)
class FieldScore:
    field: str
    status: ScoreStatus
    ground_truth: str
    system_output: str
    rationale: str
    observed_value: str = ""

    def to_json(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CaseScore:
    case_slug: str
    company: str
    fields: list[FieldScore]
    fabrications: int
    cvc_step_count_observed: int

    @property
    def exact(self) -> int:
        return sum(1 for field in self.fields if field.status == "exact")

    @property
    def partial(self) -> int:
        return sum(1 for field in self.fields if field.status == "partial")

    @property
    def miss(self) -> int:
        return sum(1 for field in self.fields if field.status == "miss")

    @property
    def total_fields(self) -> int:
        return len(self.fields)

    def to_json(self) -> dict:
        return {
            "case_slug": self.case_slug,
            "company": self.company,
            "exact": self.exact,
            "partial": self.partial,
            "miss": self.miss,
            "fabrications": self.fabrications,
            "cvc_step_count_observed": self.cvc_step_count_observed,
            "fields": [field.to_json() for field in self.fields],
        }


def score_case(case: EvalCase, client: LLMClient | None = None) -> CaseScore:
    _validate_case_files(case)
    table_rows = _parse_side_by_side_table(case.calibration_report_path.read_text(encoding="utf-8"))
    cvc_step_count = _read_cvc_step_count(case)
    fields: list[FieldScore] = []
    for field_name in case.scoring_fields:
        row = table_rows[field_name]
        observed = str(cvc_step_count) if field_name == "CVC step count" else ""
        fields.append(
            FieldScore(
                field=field_name,
                status=_score_status(row["match"], row, client),
                ground_truth=row["ground_truth"],
                system_output=row["system_output"],
                rationale=row["notes"],
                observed_value=observed,
            )
        )
    fabrications = _parse_fabrications(case.calibration_report_path.read_text(encoding="utf-8"))
    return CaseScore(
        case_slug=case.slug,
        company=case.company,
        fields=fields,
        fabrications=fabrications,
        cvc_step_count_observed=cvc_step_count,
    )


def _validate_case_files(case: EvalCase) -> None:
    if not case.ground_truth_path.exists():
        raise FileNotFoundError(case.ground_truth_path)
    if not case.system_run_path.exists():
        raise FileNotFoundError(case.system_run_path)
    for artifact in REQUIRED_ARTIFACTS:
        path = case.system_run_path / artifact
        if not path.exists():
            raise FileNotFoundError(path)


def _parse_side_by_side_table(text: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Field |"):
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("|---"):
            continue
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            raise ValueError(f"Unexpected calibration table row: {line}")
        field, ground_truth, system_output, match, notes = cells
        rows[field] = {
            "ground_truth": ground_truth,
            "system_output": system_output,
            "match": match,
            "notes": notes,
        }
    return rows


def _score_status(
    match_cell: str,
    row: dict[str, str],
    client: LLMClient | None,
) -> ScoreStatus:
    if _truthy(os.getenv("MGT470_EVAL_LLM_JUDGE")) and not _truthy(
        os.getenv("MGT470_OFFLINE")
    ):
        return _llm_judge(row, client or get_default_client()).status
    if "✅" in match_cell:
        return "exact"
    if "⚠️" in match_cell:
        return "partial"
    if "❌" in match_cell:
        return "miss"
    raise ValueError(f"Unknown match marker: {match_cell}")


def _llm_judge(row: dict[str, str], client: LLMClient) -> SemanticJudgeResult:
    return client.structured(
        role="smart",
        system="Judge whether a system strategy-analysis field matches ground truth.",
        user=(
            "Score this field as exact, partial, or miss. Preserve the human report "
            "rationale if it is already decisive.\n\n"
            f"Ground truth: {row['ground_truth']}\n"
            f"System output: {row['system_output']}\n"
            f"Human notes: {row['notes']}"
        ),
        schema=SemanticJudgeResult,
        reasoning_effort="low",
        max_tokens=800,
    )


def _parse_fabrications(text: str) -> int:
    match = re.search(r"Fabrications detected:\s*(\d+)", text)
    if not match:
        raise ValueError("Could not parse fabrication count")
    return int(match.group(1))


def _read_cvc_step_count(case: EvalCase) -> int:
    payload = json.loads((case.system_run_path / "cvc.json").read_text(encoding="utf-8"))
    return len(payload.get("activities", []))


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}
