from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel


class CustomerActivity(ArtifactModel):
    id: str
    step: int
    activity: str
    current_provider: str
    customer_goal: str
    evidence_ids: list[str]


class CustomerValueChain(ArtifactModel):
    customer_segment: str
    end_activity: str
    activities: list[CustomerActivity]
    profile_vs_cvc_conflicts: list[str] = Field(default_factory=list)
