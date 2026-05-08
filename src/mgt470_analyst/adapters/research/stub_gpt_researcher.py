from datetime import date

from mgt470_analyst.adapters.research.base import ResearchAdapter
from mgt470_analyst.schemas.raw_input import RawInput
from mgt470_analyst.schemas.research import ResearchBrief, ResearchSource


class StubGPTResearcherAdapter(ResearchAdapter):
    def research(self, raw_input: RawInput) -> ResearchBrief:
        sources: list[ResearchSource] = [
            ResearchSource(
                id="S0",
                title="User supplied CLI input",
                url_or_path="CLI input",
                source_type="user_input",
                retrieved_at=date.today().isoformat(),
                reliability="high",
                key_claims=[f"{raw_input.company_name} was supplied as the target company."],
            )
        ]
        if raw_input.website:
            sources.append(
                ResearchSource(
                    id="S1",
                    title="User supplied company website",
                    url_or_path=raw_input.website,
                    source_type="website",
                    retrieved_at=date.today().isoformat(),
                    reliability="medium",
                    key_claims=["Company website supplied by user."],
                )
            )
        for index, url in enumerate([u for u in raw_input.urls if u != raw_input.website], start=2):
            sources.append(
                ResearchSource(
                    id=f"S{index}",
                    title="User supplied URL",
                    url_or_path=url,
                    source_type="website",
                    retrieved_at=date.today().isoformat(),
                    reliability="medium",
                    key_claims=["Additional URL supplied by user."],
                )
            )

        return ResearchBrief(
            company_name=raw_input.company_name,
            research_summary=(
                "Stub research summary generated from local input. No network research or "
                "financial API verification was performed."
            ),
            sources=sources,
            open_questions=[
                "Replace stub research with cited backend research.",
                "Verify customer segment, revenue model, and willingness to switch.",
            ],
            conflicts=[],
        )
