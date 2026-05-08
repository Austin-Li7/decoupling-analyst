from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel


class DeckClaim(ArtifactModel):
    id: str
    claim: str
    claim_type: Literal["metric", "qualitative", "forecast", "tam"]
    page: int | None = None
    verbatim: str
    verification_status: Literal["unverified", "verified", "conflicted"] = "unverified"
    evidence_id: str


class DeckClaims(ArtifactModel):
    source_file: str
    claims: list[DeckClaim] = Field(default_factory=list)
