from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel, Severity


class CompetitiveResponseItem(ArtifactModel):
    response_type: Literal["recouple", "copy", "block", "subsidize", "acquire", "partner"]
    description: str
    severity: Severity
    defense: str
    evidence_ids: list[str]


class RecouplingVulnerability(ArtifactModel):
    vulnerability: Severity
    rationale: str
    incumbent_capability_to_recouple: Severity
    incumbent_incentive_to_recouple: Severity
    defenses: list[str] = Field(default_factory=list)
    evidence_ids: list[str]


class CompetitiveResponse(ArtifactModel):
    likely_responses: list[CompetitiveResponseItem]
    recoupling_vulnerability: RecouplingVulnerability
