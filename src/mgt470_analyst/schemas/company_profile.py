from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel


class CompanyInfo(ArtifactModel):
    name: str
    website: str = ""
    ticker: str = ""
    public_or_private: Literal["public", "private", "unknown"] = "unknown"
    industry: str = "unknown"
    geography: list[str] = Field(default_factory=list)
    stage: str = "unknown"
    description: str = "Company profile normalized from user input and stub research."


class CustomersInfo(ArtifactModel):
    primary_user: str = "unknown"
    buyer: str = "unknown"
    payer: str = "unknown"
    segments: list[str] = Field(default_factory=list)


class BusinessModelInfo(ArtifactModel):
    value_proposition: str = "unknown"
    revenue_model: str = "unknown"
    pricing_model: str = "unknown"
    distribution_channels: list[str] = Field(default_factory=list)
    cost_drivers: list[str] = Field(default_factory=list)


class CompetitionInfo(ArtifactModel):
    incumbents: list[str] = Field(default_factory=list)
    direct_competitors: list[str] = Field(default_factory=list)
    substitutes: list[str] = Field(default_factory=list)


class CompanyProfile(ArtifactModel):
    company: CompanyInfo
    customers: CustomersInfo = Field(default_factory=CustomersInfo)
    business_model: BusinessModelInfo = Field(default_factory=BusinessModelInfo)
    competition: CompetitionInfo = Field(default_factory=CompetitionInfo)
    evidence_ids: list[str]
