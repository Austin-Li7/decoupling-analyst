from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel, Confidence

CasePerspectiveType = Literal["disruptor", "transitioning", "incumbent", "unclear"]


class CasePerspective(ArtifactModel):
    """Identifies whose seat the analyst is sitting in for this case.

    Teixeira-style MGT470 cases ask different questions depending on the
    company's situation:
      - disruptor: how should this new entrant decouple further?
      - transitioning: this company is mid-pivot — what to preserve, what
        to evolve, in what order?
      - incumbent: how to defend / recouple under attack?

    Misreading the perspective causes the analysis to answer the wrong
    question (e.g., proposing a third-party startup to disrupt Flipkart
    when the case is actually asking what Flipkart itself should do).
    """

    perspective: CasePerspectiveType
    confidence: Confidence
    reasoning: str
    primary_question: str = Field(
        description=(
            "The actual strategic question the case is asking about THIS "
            "company. One sentence."
        )
    )
    evidence_ids: list[str]
