"""OpenAI-backed research adapter.

This adapter does NOT do live web search. It synthesizes a structured
research brief from whatever inputs the user provided (company name,
ticker, website URL, uploaded files) plus the model's own knowledge,
and explicitly flags what would need real research to verify.

Replace with a true web-research backend (GPT Researcher, Tavily, etc.)
in a later phase.
"""

from datetime import date

from mgt470_analyst.adapters.research.base import ResearchAdapter
from mgt470_analyst.llm.client import LLMClient, get_default_client
from mgt470_analyst.llm.prompts import MGT470_FRAMEWORK
from mgt470_analyst.schemas.raw_input import RawInput
from mgt470_analyst.schemas.research import ResearchBrief


class OpenAIResearchAdapter(ResearchAdapter):
    def __init__(self, client: LLMClient | None = None) -> None:
        self.client = client or get_default_client()

    def research(self, raw_input: RawInput) -> ResearchBrief:
        system = (
            MGT470_FRAMEWORK
            + "\n\nTask: produce a concise research brief about the target company."
            " You may rely on widely-known public facts, but flag anything you are"
            " not certain of as an open question. Do not invent specific financial"
            " metrics."
        )

        files_summary = (
            "\n".join(f"- {f}" for f in raw_input.files) if raw_input.files else "(none)"
        )
        urls_summary = "\n".join(f"- {u}" for u in raw_input.urls) if raw_input.urls else "(none)"

        user = f"""\
Target company: {raw_input.company_name}
Ticker: {raw_input.ticker or "(none)"}
Website: {raw_input.website or "(none)"}
Files supplied by user:
{files_summary}
URLs supplied by user:
{urls_summary}
User question: {raw_input.user_question or "(none)"}
Analysis goal: {raw_input.analysis_goal}

Produce a ResearchBrief with:
- A 3-6 sentence research_summary covering what the company does, who its
  customer is, and the strategic question worth analyzing through the MGT470
  decoupling lens.
- A `sources` list. Always include S0 (user_input). Include S1+ for the
  user-supplied website and any URLs. Use today's date ({date.today().isoformat()})
  as retrieved_at. Set source_type to one of: website, deck, memo, filing,
  article, user_input, stub.
- For each source, populate `key_claims` with 2-5 SPECIFIC factual statements
  about the company that downstream analysis can cite. NOT topic labels.
  Bad: "Pricing strategy". Good: "Duolingo Super sells at $6.99/month and
  drives the bulk of subscription revenue." Each key_claim must be a
  standalone sentence the next module can attach to evidence.
- Mark `reliability` honestly: "high" only for primary sources you are sure
  about; "medium" for general knowledge; "low" for inferred/uncertain.
- 3-6 specific `open_questions` that real research would need to answer.
- 0-3 `conflicts` between sources if any are apparent.
"""
        return self.client.structured(
            role="research",
            system=system,
            user=user,
            schema=ResearchBrief,
            context={"company_name": raw_input.company_name},
        )
