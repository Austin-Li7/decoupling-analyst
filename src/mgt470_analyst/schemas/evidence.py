from typing import Literal

from pydantic import Field, RootModel

from mgt470_analyst.schemas.base import ArtifactModel, Confidence

ClaimType = Literal["metric", "qualitative", "management_claim", "assumption"]


class EvidenceItem(ArtifactModel):
    id: str
    claim: str
    source_id: str
    locator: str
    claim_type: ClaimType
    confidence: Confidence
    verified_against: list[str] = Field(default_factory=list)
    used_by_modules: list[str] = Field(default_factory=list)
    conflicts_with: list[str] = Field(default_factory=list)


class EvidenceStoreArtifact(RootModel[dict[str, EvidenceItem]]):
    pass
