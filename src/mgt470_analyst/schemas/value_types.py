from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel


class ValueTypeActivity(ArtifactModel):
    activity_id: str
    value_type: Literal["create", "erode", "capture"]
    reasoning: str
    money_cost: int = Field(ge=1, le=5)
    time_cost: int = Field(ge=1, le=5)
    effort_cost: int = Field(ge=1, le=5)
    satisfaction: int = Field(ge=1, le=5)
    evidence_ids: list[str]


class ValueTypeDiagnosis(ArtifactModel):
    activities: list[ValueTypeActivity]
