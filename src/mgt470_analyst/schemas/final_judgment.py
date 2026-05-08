from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel


class FinalJudgment(ArtifactModel):
    judgment: Literal["study_more", "invest_watchlist", "avoid", "startup_opportunity", "unclear"]
    one_sentence_thesis: str
    why_now: str
    strongest_argument: str
    biggest_risk: str
    staged_actions: list[str] = Field(
        default_factory=list,
        description=(
            "Sequenced execution steps in priority order. For transitioning "
            "companies, this is the layered-evolution path. Prefer 3-6 steps "
            "where step N+1 depends on step N landing first."
        ),
    )
    do_not_do: list[str] = Field(
        default_factory=list,
        description=(
            "Explicit don't-do list. Each item names an attractive-looking "
            "action the company should NOT take and the reason it would "
            "damage the core moat or violate unit economics."
        ),
    )
    next_research_steps: list[str]
    evidence_ids: list[str]
