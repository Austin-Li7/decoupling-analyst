# MGT470 Business Analyst System Design

Status: Draft v0.1  
Date: 2026-05-07  
Primary user: Austin  
Project shape: Local-first CLI + Markdown report generator  

## 1. Purpose

`mgt470-business-analyst` is a reproducible AI workflow for commercial, investment, and startup judgment using Thales Teixeira's MGT470 Digital Disruption logic.

The system is not designed for classroom homework or generic case summaries. It is designed to help the user evaluate real companies, markets, pitch decks, public filings, websites, and incomplete business information through a stable, modular, evidence-grounded workflow.

The core question is:

> Given a company or business opportunity, where is the customer value chain weak, what can be decoupled, can AI or digital leverage make that decoupling stronger, and does the resulting business model deserve further attention?

## 2. Product Principles

| Principle | Meaning |
|---|---|
| Reproducible over clever | Every run produces structured checkpoints, not only prose. |
| Evidence-grounded | Every major claim should trace to a source, input file, or explicit assumption. |
| Modular | Research, CVC mapping, financial verification, decoupling, and report writing are separate modules. |
| Local-first | First version runs from the command line and writes files locally. |
| Obsidian-native output | Final report is Markdown with properties, callouts, tables, and reusable lessons. |
| Human owns final judgment | The system assists analysis; it does not provide investment advice or autonomous decisions. |

## 3. Initial Product Shape

The first version is a CLI workflow:

```bash
mgt470 analyze \
  --company "Duolingo" \
  --url "https://www.duolingo.com" \
  --files ./inputs/duolingo/deck.pdf \
  --mode investment \
  --output "/path/to/AustinObsidianVault/MGT470/Duolingo - MGT470 Analysis.md"
```

The CLI produces:

```text
runs/duolingo/run.json
runs/duolingo/research_brief.json
runs/duolingo/company_profile.json
runs/duolingo/analysis_state.json
runs/duolingo/financial_verification.json
runs/duolingo/final_report.md
```

Optionally, it also copies the final Markdown report into the Obsidian vault.

## 4. Why Not Start With a Web App

A web app is only an interface. The core product is the workflow engine.

Starting with CLI is better because:

- It is easier to test and reproduce.
- It keeps source files, intermediate JSON, and final Markdown visible.
- It is easier to push to GitHub.
- It avoids UI work before the analytical workflow is stable.
- It can later power a web app, Obsidian command, GitHub Action, or folder watcher.

Future interfaces can call the same core engine:

```text
CLI
Obsidian command
Local folder watcher
Streamlit / Gradio app
FastAPI endpoint
GitHub Action
```

## 5. External Projects to Reference or Integrate

### 5.1 Research Agent Candidates

The system needs a research agent that can take incomplete company information and gather enough structured evidence to fill the normalized input schema.

#### Recommended Default: GPT Researcher

Repository: https://github.com/assafelovic/gpt-researcher  
Website: https://gptr.dev/

Use it as the default research backend because it is mature, open-source, designed for web and local research, produces cited reports, and is intended to be embedded into other agent workflows.

Role in this project:

```text
Company name / URL / topic
  -> GPT Researcher
  -> cited research report + source list
  -> ResearchNormalizer
  -> research_brief.json
```

Why it fits:

- Mature open-source autonomous research agent.
- Supports web and local research.
- Designed to produce reports with citations.
- Can be customized for domain-specific research.
- Easier to integrate into a Python CLI than a platform-specific plugin.

#### Advanced Option: LangChain Open Deep Research

Repository: https://github.com/langchain-ai/open_deep_research

Use this later if the project adopts LangGraph as the orchestration layer. It is built around a structured supervisor/researcher architecture and supports multiple model providers, search tools, and MCP servers.

Role in this project:

```text
ResearchAdapter interface
  -> GPTResearcherAdapter initially
  -> OpenDeepResearchAdapter later
```

Decision:

Start with a research adapter abstraction. Implement GPT Researcher first. Keep Open Deep Research as a compatible future backend.

### 5.2 Financial Verification Candidates

Financial verification has two distinct jobs:

1. Retrieve and normalize financial facts.
2. Apply finance-specific analysis workflows.

These should not be collapsed into one prompt.

#### Data Layer: OpenBB Platform

Website: https://openbb.co/products/odp/  
Docs: https://docs.openbb.co/platform/usage/examples/financial_statements  
Reference: https://docs.openbb.co/odp/python/reference/equity/fundamental

Use OpenBB as the preferred public-company financial data layer.

Relevant capabilities:

- Income statement
- Balance sheet
- Cash flow
- Ratios
- Metrics
- Multiples
- Filings
- Earnings call transcripts
- Revenue by segment/geography where available

Role in this project:

```text
Ticker / company
  -> OpenBBFinancialsProvider
  -> standardized financial_facts.json
  -> FinancialVerificationModule
```

#### Finance Workflow Reference: Anthropic Financial Services

Repository: https://github.com/anthropics/financial-services  
Anthropic announcement: https://www.anthropic.com/news/finance-agents  
Claude for Financial Services: https://www.anthropic.com/news/claude-for-financial-services

This is the closest reference to the "Claude financial services GitHub project" mentioned by the user.

Important interpretation:

- It is not primarily a Python library for direct use.
- It is a file-based financial services workflow suite for Claude-oriented environments.
- It contains skills, commands, MCP connector definitions, and financial workflow patterns.
- It includes financial analysis, investment banking, equity research, private equity, and wealth management plugins.

Role in this project:

```text
Use as reference architecture and optional plugin compatibility layer,
not as the only financial data engine.
```

What to borrow:

- Plugin structure: skills + commands + connectors.
- Financial analysis commands such as comps, DCF, earnings updates, one-pagers, IC memos.
- MCP connector pattern.
- Report quality expectations and institutional workflow language.
- Finance-specific QA expectations.

What not to assume:

- Data connectors may require paid subscriptions.
- Claude plugin execution may not be portable to a local Python CLI.
- The plugin suite should not replace our own JSON schemas and validators.

#### Optional MCP/Data Tools

Candidate tools to evaluate later:

- `OctagonAI/octagon-mcp-server`: MCP server for filings, transcripts, financial metrics, private markets, and market intelligence.
- `wshobson/maverick-mcp`: personal stock analysis MCP server.
- SEC EDGAR APIs for filings.
- yfinance for lightweight market data.

Decision:

Use OpenBB as the first programmatic financial data layer. Use Anthropic financial-services as a workflow and skill reference. Add MCP providers later through adapter interfaces.

## 6. Architecture Overview

```text
Raw User Input
  |
  v
Input Parser
  |
  +--> Pitch Deck Claim Extractor (if deck present) --> deck_claims.json
  |
  v
Research Agent Adapter
  |
  v
Evidence Store (global)
  |
  v
Normalized Company Profile JSON
  |
  v
Lens Fit Classifier
  |   (decoupling | low-end | new-market | tech-substitution | business-model)
  |   --> labels the best analytical lens; does not terminate investment analysis
  |
  v
MGT470 Analysis Modules
  |
  +--> CVC Mapping  (rebuilt from evidence, not reused from company_profile)
  +--> Value Type Diagnosis
  +--> Weak Link Finder
  +--> Decoupling Strategy
  +--> Business Model Analysis
  +--> Competitive Response
  +--> Coupling Growth Path
  |
  v
Financial Verification Module
  |   (cross-checks deck_claims.json when present)
  |
  v
Per-Module Artifacts
  |
  v
Professional Markdown Report Renderer
```

State is **not** a single mutable JSON object. Each module writes its own
artifact under `runs/<run_id>/`. In the MVP, `run.json` records module
versions, prompt versions, input paths, output paths, status, token usage,
and errors. Content-addressed caching, `--resume`, and selective
`--rerun <module>` are Phase 2 features after the module boundaries stabilize.

## 7. Core Packages

```text
src/mgt470_analyst/
  cli.py
  config.py
  orchestrator.py
  schemas/
  adapters/
    research/
    financials/
    documents/
  modules/
    intake.py
    deck_extractor.py
    disruption_type.py
    cvc.py
    value_types.py
    weak_links.py
    decoupling.py
    ai_leverage.py
    business_model.py
    financial_verification.py
    competitive_response.py
    recoupling.py
    coupling.py
  evidence/
    store.py
    validator.py
  cache/
    content_addressed.py
  renderers/
    markdown.py
  validators/
    evidence.py
    schema.py
  prompts/
  templates/
```

## 8. Data Flow

### 8.1 Raw Input

Users may provide any combination of:

- Company name
- Website URL
- Ticker
- Pitch deck PDF
- Company memo
- Notes
- SEC filing
- Earnings transcript
- Article URLs
- A short natural-language prompt

Example:

```json
{
  "analysis_goal": "investment_judgment",
  "company_name": "Duolingo",
  "ticker": "DUOL",
  "website": "https://www.duolingo.com",
  "files": [],
  "urls": [],
  "user_question": "Is this a high-quality AI-leveraged business worth studying?",
  "output_style": "professional_obsidian_note",
  "include_financial_verification": true
}
```

### 8.2 Research Brief

Produced by the research agent and normalized by our system.

```json
{
  "company_name": "",
  "research_summary": "",
  "sources": [
    {
      "id": "S1",
      "title": "",
      "url_or_path": "",
      "source_type": "website",
      "retrieved_at": "2026-05-07",
      "reliability": "medium",
      "key_claims": []
    }
  ],
  "open_questions": [],
  "conflicts": []
}
```

### 8.3 Normalized Company Profile

```json
{
  "company": {
    "name": "",
    "website": "",
    "ticker": null,
    "public_or_private": "unknown",
    "industry": "",
    "geography": [],
    "stage": "",
    "description": ""
  },
  "customers": {
    "primary_user": "",
    "buyer": "",
    "payer": "",
    "segments": []
  },
  "business_model": {
    "value_proposition": "",
    "revenue_model": "",
    "pricing_model": "",
    "distribution_channels": [],
    "cost_drivers": []
  },
  "competition": {
    "incumbents": [],
    "direct_competitors": [],
    "substitutes": []
  },
  "evidence": []
}
```

### 8.4 Per-Module Artifacts and Run Manifest

There is no single shared state object. Each module writes a typed artifact:

```text
runs/<run_id>/
  run.json                     # manifest: inputs, module versions, hashes
  evidence_store.json          # global evidence layer (see 8.6)
  research_brief.json
  deck_claims.json             # only if a pitch deck was provided
  company_profile.json
  lens_fit.json                # strategic lens classifier
  cvc.json
  value_type_diagnosis.json
  weak_link_analysis.json
  decoupling_strategy.json
  ai_leverage.json
  business_model_analysis.json
  financial_verification.json
  competitive_response.json
  recoupling_vulnerability.json
  coupling_growth.json
  final_judgment.json
  final_report.md
```

`run.json` records, per module:

```json
{
  "module": "weak_link_finder",
  "module_version": "0.3.0",
  "prompt_version": "weak_link@2026-05-07",
  "input_hash": "sha256:...",
  "output_path": "weak_link_analysis.json",
  "status": "ok",
  "cost_usd": 0.42,
  "tokens": { "in": 8123, "out": 1402 }
}
```

The orchestrator reuses an artifact when `(module_version, prompt_version,
input_hash)` matches a prior entry. `mgt470 analyze --rerun decoupling`
invalidates that one module and everything downstream of it; everything
upstream is reused.

### 8.5 Evidence Store (global)

Every factual claim used by any analysis module must be backed by an entry
in the global evidence store. Modules reference evidence by `id`, never by
copying the underlying text.

```json
{
  "E1": {
    "id": "E1",
    "claim": "Duolingo had 31.4M DAU in Q1 2024",
    "source_id": "S3",
    "locator": "10-Q, p. 12",
    "claim_type": "metric | qualitative | management_claim | assumption",
    "confidence": "high | medium | low",
    "verified_against": ["financial_verification"],
    "used_by_modules": ["company_profile", "weak_link_finder"],
    "conflicts_with": []
  }
}
```

Rules:

- `claim_type = management_claim` is allowed but must stay flagged unverified
  unless `financial_verification` corroborates it.
- Any module output referencing an `evidence_id` not present in the store is
  a validation error. The orchestrator runs one structured repair pass that
  may either attach a valid evidence ID or explicitly mark the statement as
  an assumption. If the repaired output still has unresolved evidence IDs,
  the orchestrator writes an error artifact and stops downstream modules.
  Evidence integrity is a hard guarantee, but the workflow should not fail
  on the first missing citation without a repair attempt.
- `used_by_modules` is auto-maintained so the report renderer can show, for
  each major claim, the chain of modules that depended on it.

## 9. Module Design

### 9.1 Intake Module

Purpose:

Normalize raw user input and decide which workflow branches to run.

Inputs:

- CLI args
- Raw files
- URLs
- User question

Outputs:

- `run.json`
- workflow plan

Key decisions:

- Is this public or private?
- Is financial verification possible?
- Is research required?
- Is document extraction required?

### 9.2 Research Module

Purpose:

Gather external evidence and create a cited research brief.

Default backend:

- GPT Researcher

Future backend:

- Open Deep Research

Output:

- `research_brief.json`

Quality rules:

- Separate claims from sources.
- Mark reliability.
- Record conflicts.
- Record missing information.
- Never silently convert uncertain claims into facts.

### 9.3 Company Profile Module

Purpose:

Convert research and input materials into a normalized company profile.

Output:

- `company_profile.json`

This module creates the stable input for all MGT470 analysis modules.

### 9.3.1 Pitch Deck Claim Extractor

Purpose:

When the user provides a pitch deck or memo, extract management claims into
a structured artifact **before** they get blended into research evidence.
Private-company analyses are usually 80% deck-driven, and these claims must
stay separable so financial verification can score them.

Triggered when:

- `input.files` contains a deck/memo PDF or DOCX.

Output: `deck_claims.json`

```json
{
  "source_file": "inputs/duolingo/deck.pdf",
  "claims": [
    {
      "id": "DC1",
      "claim": "ARR grew 4x YoY in 2025",
      "claim_type": "metric | qualitative | forecast | tam",
      "page": 12,
      "verbatim": "...",
      "verification_status": "unverified",
      "evidence_id": "E27"
    }
  ]
}
```

Each `DC*` is also written into `evidence_store.json` as a
`management_claim`, so downstream modules cite via the global evidence
layer rather than re-reading the deck.

### 9.3.2 Lens Fit Classifier

Purpose:

Diagnose which strategic lens best fits the company before spending tokens
on full analysis. Teixeira's decoupling framework is the primary lens, but
the user's goal is commercial, investment, and startup judgment. Therefore,
the classifier should surface the fit and caveats instead of prematurely
terminating the workflow.

Output: `lens_fit.json`

```json
{
  "primary_type": "decoupling | low_end | new_market | tech_substitution | business_model | unclear",
  "secondary_types": [],
  "confidence": "high | medium | low",
  "reasoning": "",
  "evidence_ids": [],
  "decoupling_fit_score": 0.0,
  "recommended_report_mode": "full_decoupling | strategic_memo | financial_first",
  "caveats": []
}
```

Behavior:

- Low decoupling fit should not stop the run when the user asked for
  investment or startup judgment. It should change emphasis: the report may
  become a shorter strategic memo, but it should still provide useful
  analysis, missing data, and next research steps.
- The report renderer surfaces lens caveats near the top of the executive
  summary so the user understands where MGT470 is strong or weak for this
  company.

### 9.4 CVC Mapping Module

Purpose:

Map the customer value chain.

**Important constraint:** this module must rebuild the CVC from the
evidence store and the customer's *end activity*, not by reusing
`company_profile.customers`. The company profile's customer view is shaped
by how the company describes itself; the CVC must be shaped by how the
customer actually behaves. The prompt explicitly instructs the model to
ignore `company_profile.customers` during the first pass and only
cross-check it at the end. Mismatches between the two are recorded in
`cvc.json` under `profile_vs_cvc_conflicts` — these are often the most
interesting analytical signal.

Output:

```json
{
  "customer_segment": "",
  "end_activity": "",
  "activities": [
    {
      "step": 1,
      "activity": "",
      "current_provider": "",
      "customer_goal": "",
      "evidence_ids": []
    }
  ]
}
```

### 9.5 Value Type Diagnosis Module

Purpose:

Classify CVC activities as value creating, eroding, or capturing.

Output:

```json
{
  "activities": [
    {
      "activity_id": "",
      "value_type": "create",
      "reasoning": "",
      "money_cost": 1,
      "time_cost": 3,
      "effort_cost": 4,
      "satisfaction": 2,
      "evidence_ids": []
    }
  ]
}
```

### 9.6 Weak Link Finder

Purpose:

Score decoupling opportunities.

Formula:

```text
Opportunity Score
= Pain Intensity
x Frequency
x AI or Digital Leverage
x Willingness to Switch
x Value Capture Potential
/ Integration Dependency
```

Output:

```json
{
  "ranked_weak_links": [
    {
      "activity_id": "",
      "score": 0,
      "pain_intensity": 0,
      "frequency": 0,
      "ai_or_digital_leverage": 0,
      "willingness_to_switch": 0,
      "value_capture_potential": 0,
      "integration_dependency": 0,
      "rationale": ""
    }
  ]
}
```

### 9.7 Decoupling Strategy Module

Purpose:

Design the actual decoupling strategy.

Output:

```json
{
  "primary_decoupling": {
    "activity_to_decouple": "",
    "from_incumbent_bundle": "",
    "customer_pain": "",
    "new_offering": "",
    "why_customer_switches": "",
    "cheaper_faster_easier": [],
    "evidence_ids": []
  },
  "do_not_decouple": []
}
```

### 9.8 AI Leverage Module

Purpose:

Identify whether AI materially improves the decoupling strategy.

Output:

```json
{
  "ai_opportunities": [
    {
      "cvc_activity": "",
      "ai_role": "automation | generation | prediction | recommendation | agent_execution | analysis",
      "cost_reduced": "money | time | effort",
      "data_required": [],
      "human_review_required": true,
      "risk_if_wrong": "",
      "roi_metric": "",
      "confidence": "medium"
    }
  ]
}
```

### 9.9 Business Model Module

Purpose:

Determine whether the decoupling opportunity can become a business.

Output:

```json
{
  "value_creation": "",
  "value_capture": "",
  "value_erosion_remaining": "",
  "payer": "",
  "pricing_model": "",
  "cac_risks": [],
  "ltv_drivers": [],
  "unit_economics_concerns": []
}
```

### 9.10 Financial Verification Module

Purpose:

Validate financial claims and assess financial quality.

Triggered when:

- `include_financial_verification = true`
- Company has ticker
- Public filings exist
- Pitch deck includes financial claims
- User asks for investment judgment

Data providers:

- OpenBB first
- SEC filings later
- yfinance for lightweight market data
- Optional MCP providers later

Output:

```json
{
  "financial_data_available": true,
  "verified_metrics": [],
  "unverified_claims": [],
  "growth_quality": "",
  "margin_quality": "",
  "cash_efficiency": "",
  "unit_economics": "",
  "valuation_sanity": "",
  "red_flags": [],
  "missing_data": [],
  "confidence": "medium"
}
```

### 9.11 Competitive Response Module

Purpose:

Predict incumbent response, including recoupling risk. In MVP, recoupling
is a scored subsection inside this module. It can be split into a dedicated
module later if real reports show that the logic is complex enough to earn
its own artifact.

Output:

```json
{
  "likely_responses": [
    {
      "response_type": "recouple | copy | block | subsidize | acquire | partner",
      "description": "",
      "severity": "high | medium | low",
      "defense": ""
    }
  ],
  "recoupling_vulnerability": {
    "vulnerability": "high | medium | low",
    "rationale": "",
    "incumbent_capability_to_recouple": "high | medium | low",
    "incumbent_incentive_to_recouple": "high | medium | low",
    "defenses": [],
    "evidence_ids": []
  }
}
```

### 9.11.1 Future Dedicated Recoupling Vulnerability Module

Purpose:

Score the risk that the incumbent successfully re-bundles the decoupled
activity, neutralizing the new entrant. This becomes a separate, dedicated
judgment in Phase 2 or Phase 3 if the MVP's embedded recoupling subsection
is insufficient.

Output: `recoupling_vulnerability.json`

```json
{
  "vulnerability": "high | medium | low",
  "rationale": "",
  "incumbent_capability_to_recouple": "high | medium | low",
  "incumbent_incentive_to_recouple": "high | medium | low",
  "switching_friction_against_recoupling": "high | medium | low",
  "triggers": [
    "incumbent ships native AI feature that closes the gap",
    "bundling pricing makes standalone uneconomic"
  ],
  "leading_indicators": [
    "incumbent hires in this domain",
    "incumbent acquisition of adjacent player",
    "platform API changes that disadvantage standalone"
  ],
  "defenses": [
    "data network effect",
    "switching cost on new side of decoupling",
    "regulatory or contractual lock"
  ],
  "evidence_ids": []
}
```

The final judgment module weights `recoupling_vulnerability.vulnerability`
heavily for `judgment = invest_watchlist` vs. `study_more`.

### 9.12 Coupling Growth Module

Purpose:

Identify post-decoupling growth paths.

Output:

```json
{
  "add_a_link": [],
  "add_a_chain": [],
  "reinforce_link_or_chain": [],
  "recommended_growth_sequence": []
}
```

### 9.13 Final Judgment Module

Purpose:

Create the user's actual decision output.

Output:

```json
{
  "judgment": "study_more | invest_watchlist | avoid | startup_opportunity | unclear",
  "one_sentence_thesis": "",
  "why_now": "",
  "strongest_argument": "",
  "biggest_risk": "",
  "next_research_steps": []
}
```

## 10. Financial Verification vs Basic Analysis

Basic MGT470 analysis answers:

- Who is the customer?
- What is the CVC?
- Which activities create, erode, or capture value?
- Where is the weak link?
- Can the business decouple that activity?
- Does AI strengthen the decoupling?
- Can the business capture value?

Financial verification answers:

- Are the company's growth claims credible?
- Are the financial metrics internally consistent?
- Does gross margin support the business model?
- Does CAC payback make sense?
- Is revenue quality high or low?
- Is valuation supported by fundamentals?
- Are there signs of accounting, retention, or cash-flow weakness?

The system should keep these separate because a company can have a strong decoupling idea but weak financial quality, or strong current financials but limited decoupling potential.

## 11. Report Renderer

The final Markdown report should look like a professional investment or financial analysis memo, not a generic AI essay.

Target style:

- Obsidian properties
- Executive summary
- Clear tables
- Evidence citations
- Callouts
- Final judgment
- Reusable lessons
- Missing information
- Next research steps

Template:

```markdown
---
title:
tags:
created:
status:
company:
ticker:
industry:
analysis_type:
confidence:
sources_count:
---

# Company - MGT470 Business Analysis

> [!important] Final Judgment
> One sentence thesis.

## 1. Executive Summary

## 2. Company Snapshot

## 3. Evidence Base

## 4. Business Model

## 5. Customer Value Chain

## 6. Value Creation / Erosion / Capture

## 7. Weak Link

## 8. Decoupling Strategy

## 9. AI Leverage

## 10. Financial Verification

## 11. Competitive Response

## 12. Coupling Growth Path

## 13. Risks, Red Flags, Missing Data

## 14. Final Recommendation

## 15. Reusable Lessons
```

## 12. CLI Commands

### Analyze one company

```bash
mgt470 analyze --company "Duolingo" --ticker DUOL --mode investment
```

### Analyze from folder

```bash
mgt470 analyze-folder ./inputs/duolingo
```

Folder format:

```text
inputs/duolingo/
  input.json
  files/
    deck.pdf
    transcript.pdf
  urls.txt
```

### Render from existing state

```bash
mgt470 render --state runs/duolingo/analysis_state.json
```

### Validate a run

```bash
mgt470 validate runs/duolingo/analysis_state.json
```

## 13. Configuration

```yaml
research:
  backend: gpt_researcher
  max_sources: 20
  require_citations: true

financials:
  provider: openbb
  fallback_provider: yfinance
  verify_public_companies: true

output:
  format: obsidian_markdown
  vault_path: "/Users/lichenchangwen/Library/Mobile Documents/iCloud~md~obsidian/Documents/AustinObsidianVault"
  default_folder: "MGT470"

models:
  default: "gpt-5.5"
  research: "gpt-5.5"
  extraction: "gpt-5.4-mini"
  report: "gpt-5.5"
```

## 14. Error Handling

| Problem | Behavior |
|---|---|
| Company cannot be found | Produce a minimal report with missing info and next steps. |
| Research sources conflict | Keep both claims and mark conflict. |
| Financial data unavailable | Skip financial verification and explain why. |
| JSON validation fails | Retry module once, then write error artifact. |
| Source has low reliability | Include but downgrade confidence. |
| Pitch deck claims cannot be verified | Mark as unverified management claim. |

## 15. Testing Strategy

### Unit Tests

- Schema validation
- Module input/output shape
- Report rendering
- Evidence ID integrity
- Financial metric calculations

### Golden Test Cases

Use a small set of known companies/cases:

- Public SaaS company
- Marketplace company
- DTC company
- AI startup with only a website
- Pitch deck-only private company

Each golden case should include:

```text
input.json
expected_schema_shapes
snapshot_report.md
known_red_flags
```

### Evaluation Criteria

| Criterion | Requirement |
|---|---|
| Reproducibility | Same input produces same JSON structure. |
| Evidence coverage | Major claims cite evidence or assumption. |
| MGT470 fidelity | CVC, value type, weak link, decoupling are always present. |
| Financial discipline | Financial claims are separated from strategic claims. |
| Report usefulness | Final Markdown is readable and decision-oriented. |

## 16. Security and Privacy

- Treat all user-uploaded decks and private notes as sensitive.
- Do not send private files to external services unless explicitly configured.
- Store run artifacts locally by default.
- Keep API keys in environment variables or local config ignored by git.
- Never commit private input files or generated private reports by default.
- Add `.gitignore` for `runs/`, `.env`, and `inputs/private/`.

## 17. Repository Plan

Initial repo structure:

```text
mgt470-business-analyst/
  README.md
  SYSTEM_DESIGN.md
  pyproject.toml
  .gitignore
  src/mgt470_analyst/
  schemas/
  prompts/
  templates/
  examples/
  tests/
```

The Obsidian vault copy of this design can exist as a working note, but the GitHub repo should contain the canonical `SYSTEM_DESIGN.md`.

## 18. MVP Scope

The MVP should include:

1. CLI command `mgt470 analyze`
2. Raw input schema
3. Pitch deck claim extractor (when deck is provided)
4. Research adapter interface
5. Stub or basic GPT Researcher adapter
6. Evidence store + evidence ID validator with one repair pass
7. Simple run manifest and per-module artifacts
8. Company profile normalizer
9. Lens fit classifier (no hard short-circuit for investment analysis)
10. CVC mapping module (rebuild-from-evidence pass + profile cross-check)
11. Value type diagnosis module
12. Weak link finder
13. Decoupling strategy module
14. Lightweight business model analysis
15. Competitive response with embedded recoupling risk
16. Markdown renderer
17. JSON artifacts for each run

Deferred to Phase 2: full AI leverage analysis, OpenBB financial
verification, coupling growth, content-addressed module cache, and a
dedicated recoupling vulnerability module. The first end-to-end walking
skeleton should preserve the core Teixeira method before adding advanced
engineering features.

MVP does not need:

- Web UI
- Full LangGraph orchestration
- Paid MCP financial connectors
- Full DCF or comps model
- Batch company screener
- Content-addressed cache
- Dedicated recoupling artifact

## 19. Phase 2 Scope

Add:

1. OpenBB financial verification provider
2. Public company financial quality module
3. Pitch deck metric extraction
4. Evidence quality scoring
5. Obsidian vault writer
6. `analyze-folder` command
7. Golden test cases

## 20. Phase 3 Scope

Add:

1. Open Deep Research adapter
2. LangGraph orchestration option
3. Batch screening mode
4. MCP data connector support
5. Anthropic financial-services-plugin compatibility notes
6. Local web UI
7. GitHub Action workflow

## 21. Key Design Decision

This project should be a workflow engine with skills, not merely a skill pack.

Skills alone are not enough because they do not guarantee:

- Stable module ordering
- JSON validation
- Intermediate checkpoints
- Financial calculations
- Source auditability
- Repeatable reports

The correct design is:

```text
Workflow engine
  + schemas
  + validators
  + adapters
  + skills/prompts
  + report templates
```

GStack and Anthropic's financial-services project show that role-based skills and commands are powerful. GPT Researcher and Open Deep Research show how research agents gather evidence. OpenBB shows how financial data can be standardized. This project combines those patterns around one opinionated analytical framework: Teixeira-style decoupling and business model judgment.

## 22. Open Questions

1. Should the first implementation use plain Python orchestration or LangGraph from day one?
2. Should GPT Researcher be vendored as a dependency or called through a subprocess/API wrapper?
3. Should financial verification be limited to public companies in MVP?
4. Should the output report be optimized first for Obsidian or for GitHub readability?
5. Should the repo include example analyses, or keep examples synthetic to avoid copyright/private data issues?

Recommended answers for MVP:

1. Start with plain Python orchestration.
2. Use a clean adapter wrapper around GPT Researcher.
3. Defer full financial verification to Phase 2; when added, limit it first to public companies and explicit deck metrics.
4. Optimize for Obsidian while keeping Markdown GitHub-readable.
5. Use synthetic or public company examples only.

## 23. Agentic Development Workflow

This project can be built with Codex, Claude Code, or another agentic coding
environment. Runtime logic must not depend on any one assistant's private
skill system. The MGT470 analytical logic lives inside
`src/mgt470_analyst/` as versioned prompts, schemas, validators, and tests,
so it is reproducible, diff-able, and runnable outside a chat session.

Recommended cadence per module:

```text
1. Write a short module spec and JSON schema.
2. Add schema validation tests and one golden fixture.
3. Implement the module with deterministic input/output boundaries.
4. Run tests and render a sample Markdown report.
5. Review for evidence leaks, schema drift, and over-engineering.
6. Commit the module before starting the next one.
```

Assistant-specific skills can accelerate this process, but they are
author-time aids only. They should live in `CLAUDE.md`, `AGENTS.md`, or
developer notes, not in the canonical system design unless they affect the
runtime architecture.
