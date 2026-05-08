from typing import Literal

from pydantic import Field

from mgt470_analyst.schemas.base import ArtifactModel

DisciplineName = Literal[
    "preserve_core_engine",
    "layered_evolution",
    "unit_economics",
    "explicit_dont_do",
    "moat_is_relationship",
]


class DisciplineScore(ArtifactModel):
    discipline: DisciplineName
    score: int = Field(ge=0, le=5)
    rationale: str


class CitationIssue(ArtifactModel):
    """Specific evidence-citation problems flagged by the critic."""

    location: str = Field(
        description="Where in the analysis the issue was found (module + brief quote)."
    )
    cited_evidence_ids: list[str]
    issue: str = Field(
        description=(
            "Why the citation is weak: e.g., 'evidence does not actually support the "
            "claim', 'cited E5 is HBS boilerplate not a fact', 'overgeneralizes from "
            "single data point'."
        )
    )
    severity: Literal["high", "medium", "low"]


class CriticReview(ArtifactModel):
    """Cross-model audit of the analysis pipeline output.

    Run after final_judgment using either a different model (cross-vendor /
    cross-version) or the same model with much higher reasoning_effort, to
    surface flaws the original analyst missed.
    """

    overall_score: float = Field(ge=0, le=5)
    discipline_scores: list[DisciplineScore]
    weakest_aspect: str
    citation_issues: list[CitationIssue] = Field(default_factory=list)
    revision_suggestions: list[str] = Field(default_factory=list)
    would_disagree_with_thesis: bool = Field(
        description=(
            "Set true if the critic, given the same evidence, would reach a "
            "materially different conclusion than the analyst's final thesis."
        )
    )
    disagreement_summary: str = Field(
        description=(
            "If would_disagree_with_thesis is true, summarize the alternative "
            "thesis. Otherwise, leave a short note on what made the existing "
            "thesis defensible."
        )
    )
    evidence_ids: list[str]
