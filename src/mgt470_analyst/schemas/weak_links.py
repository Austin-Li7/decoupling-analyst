from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel


class WeakLink(ArtifactModel):
    activity_id: str
    score: float
    pain_intensity: int = Field(ge=1, le=5)
    frequency: int = Field(ge=1, le=5)
    ai_or_digital_leverage: int = Field(ge=1, le=5)
    willingness_to_switch: int = Field(ge=1, le=5)
    value_capture_potential: int = Field(ge=1, le=5)
    integration_dependency: int = Field(ge=1, le=5)
    rationale: str
    evidence_ids: list[str]


class WeakLinkAnalysis(ArtifactModel):
    ranked_weak_links: list[WeakLink]
