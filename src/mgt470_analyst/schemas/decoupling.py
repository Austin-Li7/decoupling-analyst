from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel


class PrimaryDecoupling(ArtifactModel):
    activity_to_decouple: str
    from_incumbent_bundle: str
    customer_pain: str
    new_offering: str
    why_customer_switches: str
    cheaper_faster_easier: list[str]
    evidence_ids: list[str]


class DoNotDecouple(ArtifactModel):
    activity: str
    reason: str
    evidence_ids: list[str]


class DecouplingStrategy(ArtifactModel):
    primary_decoupling: PrimaryDecoupling
    do_not_decouple: list[DoNotDecouple] = Field(default_factory=list)
