from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel


class BusinessModelAnalysis(ArtifactModel):
    value_creation: str
    value_capture: str
    value_erosion_remaining: str
    payer: str
    pricing_model: str
    cac_risks: list[str] = Field(default_factory=list)
    ltv_drivers: list[str] = Field(default_factory=list)
    unit_economics_concerns: list[str] = Field(default_factory=list)
    evidence_ids: list[str]
