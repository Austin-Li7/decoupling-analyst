from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel

AnalysisGoal = Literal["investment_judgment", "startup_opportunity", "commercial_strategy"]


class RawInput(ArtifactModel):
    analysis_goal: AnalysisGoal = "investment_judgment"
    company_name: str
    ticker: str = ""
    website: str = ""
    files: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    user_question: str = ""
    output_style: str = "professional_obsidian_note"
    include_financial_verification: bool = False
