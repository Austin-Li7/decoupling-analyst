from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel, Confidence


class LensFit(ArtifactModel):
    primary_type: Literal[
        "decoupling", "low_end", "new_market", "tech_substitution", "business_model", "unclear"
    ]
    secondary_types: list[str] = Field(default_factory=list)
    confidence: Confidence
    reasoning: str
    evidence_ids: list[str]
    decoupling_fit_score: float = Field(ge=0, le=1)
    recommended_report_mode: Literal["full_decoupling", "strategic_memo", "financial_first"]
    caveats: list[str] = Field(default_factory=list)
