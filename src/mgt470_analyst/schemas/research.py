from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel, Confidence

SourceType = Literal["website", "deck", "memo", "filing", "article", "user_input", "stub"]


class ResearchSource(ArtifactModel):
    id: str
    title: str
    url_or_path: str
    source_type: SourceType
    retrieved_at: str
    reliability: Confidence
    key_claims: list[str] = Field(default_factory=list)


class ResearchBrief(ArtifactModel):
    company_name: str
    research_summary: str
    sources: list[ResearchSource] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
