# MGT470 Business Decoupling Analyst MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first local-first MVP: `mgt470 analyze` reads raw company inputs, runs a deterministic stub/basic analysis pipeline, writes per-module JSON artifacts, validates evidence IDs with one repair pass, and renders a professional Markdown report.

**Architecture:** Use plain Python orchestration with typed Pydantic schemas, small deterministic modules, adapter interfaces, and local run artifacts under `runs/<run_id>/`. The MVP intentionally avoids a web UI, real GPT Researcher calls, OpenBB, LangGraph, content-addressed caching, `--resume`, and `--rerun`.

**Tech Stack:** Python 3.11+, Typer CLI, Pydantic v2, pytest, Ruff, Markdown templates rendered with Python string builders.

---

## 1. Design Review And MVP Scope

`SYSTEM_DESIGN.md` is already aligned with the requested MVP. The implementation should follow section 18 as the source of truth, with these scope decisions:

| Area | MVP decision |
|---|---|
| CLI | Implement only `mgt470 analyze`; defer `analyze-folder`, `render`, and `validate`. |
| Research | Create `ResearchAdapter` interface and `StubGPTResearcherAdapter`; no network calls. |
| Financials | Do not implement OpenBB or financial verification as a module; financial claims remain evidence and can appear as unverified management claims. |
| AI leverage | Defer separate `ai_leverage.json`; mention obvious digital/AI leverage inside weak links and decoupling only when inferable. |
| Recoupling | Embed recoupling risk inside `competitive_response.json`; no separate `recoupling_vulnerability.json`. |
| Coupling growth | Defer `coupling_growth.json`. |
| Cache/resume | Defer content-addressed caching, `--resume`, and `--rerun`; still record simple input hashes in `run.json`. |
| Privacy | Keep `.env`, private inputs, course material, and `runs/` out of git. Existing `.gitignore` already covers these. |

The first walking skeleton should be deterministic. Given the same CLI input and fixture files, it should produce the same artifact shapes and stable Markdown sections.

## 2. Recommended Python Project Structure

```text
mgt470-business-decoupling/
  pyproject.toml
  README.md
  SYSTEM_DESIGN.md
  IMPLEMENTATION_PLAN.md
  src/
    mgt470_analyst/
      __init__.py
      cli.py
      config.py
      orchestrator.py
      paths.py
      hashing.py
      schemas/
        __init__.py
        base.py
        raw_input.py
        research.py
        evidence.py
        run.py
        deck_claims.py
        company_profile.py
        lens_fit.py
        cvc.py
        value_types.py
        weak_links.py
        decoupling.py
        business_model.py
        competitive_response.py
        final_judgment.py
      adapters/
        __init__.py
        research/
          __init__.py
          base.py
          stub_gpt_researcher.py
      evidence/
        __init__.py
        store.py
        validator.py
      modules/
        __init__.py
        intake.py
        deck_extractor.py
        company_profile.py
        lens_fit.py
        cvc.py
        value_types.py
        weak_links.py
        decoupling.py
        business_model.py
        competitive_response.py
        final_judgment.py
      renderers/
        __init__.py
        markdown.py
      io/
        __init__.py
        json_artifacts.py
      templates/
        report_sections.md
  tests/
    fixtures/
      inputs/
        duolingo_basic.json
        private_deck_basic.txt
    test_cli_analyze.py
    test_schemas.py
    test_evidence_validator.py
    test_orchestrator_happy_path.py
    test_markdown_renderer.py
```

## 3. JSON Schemas

Use Pydantic models for runtime validation and JSON schema generation. Each artifact model should expose `model_json_schema()` and be written with stable pretty JSON: `indent=2`, sorted keys disabled, UTF-8.

### 3.1 `raw_input.json`

File: `src/mgt470_analyst/schemas/raw_input.py`

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
  "include_financial_verification": false
}
```

Required fields: `analysis_goal`, `company_name`. Optional fields default to empty strings, empty lists, or `false`.

### 3.2 `run.json`

File: `src/mgt470_analyst/schemas/run.py`

```json
{
  "run_id": "duolingo-20260507-215500",
  "created_at": "2026-05-07T21:55:00-07:00",
  "input": {
    "analysis_goal": "investment_judgment",
    "company_name": "Duolingo",
    "ticker": "DUOL",
    "website": "https://www.duolingo.com",
    "files": [],
    "urls": [],
    "user_question": "",
    "output_style": "professional_obsidian_note",
    "include_financial_verification": false
  },
  "artifacts": {
    "research_brief": "research_brief.json",
    "evidence_store": "evidence_store.json",
    "company_profile": "company_profile.json",
    "lens_fit": "lens_fit.json",
    "cvc": "cvc.json",
    "value_type_diagnosis": "value_type_diagnosis.json",
    "weak_link_analysis": "weak_link_analysis.json",
    "decoupling_strategy": "decoupling_strategy.json",
    "business_model_analysis": "business_model_analysis.json",
    "competitive_response": "competitive_response.json",
    "final_judgment": "final_judgment.json",
    "final_report": "final_report.md"
  },
  "modules": [
    {
      "module": "research",
      "module_version": "0.1.0",
      "input_hash": "sha256:...",
      "output_path": "research_brief.json",
      "status": "ok",
      "error": null
    }
  ]
}
```

### 3.3 `research_brief.json`

File: `src/mgt470_analyst/schemas/research.py`

```json
{
  "company_name": "Duolingo",
  "research_summary": "Stub research summary generated from local input.",
  "sources": [
    {
      "id": "S1",
      "title": "User supplied company website",
      "url_or_path": "https://www.duolingo.com",
      "source_type": "website",
      "retrieved_at": "2026-05-07",
      "reliability": "medium",
      "key_claims": ["Company website supplied by user."]
    }
  ],
  "open_questions": ["Replace stub research with cited backend research."],
  "conflicts": []
}
```

Allowed `source_type`: `website`, `deck`, `memo`, `filing`, `article`, `user_input`, `stub`. Allowed `reliability`: `high`, `medium`, `low`.

### 3.4 `evidence_store.json`

File: `src/mgt470_analyst/schemas/evidence.py`

```json
{
  "E1": {
    "id": "E1",
    "claim": "Duolingo was provided as the target company by the user.",
    "source_id": "S0",
    "locator": "CLI input",
    "claim_type": "assumption",
    "confidence": "high",
    "verified_against": [],
    "used_by_modules": ["company_profile"],
    "conflicts_with": []
  }
}
```

Allowed `claim_type`: `metric`, `qualitative`, `management_claim`, `assumption`. Allowed `confidence`: `high`, `medium`, `low`.

### 3.5 `deck_claims.json`

File: `src/mgt470_analyst/schemas/deck_claims.py`

```json
{
  "source_file": "inputs/example/deck.txt",
  "claims": [
    {
      "id": "DC1",
      "claim": "ARR grew 4x YoY in 2025",
      "claim_type": "metric",
      "page": null,
      "verbatim": "ARR grew 4x YoY in 2025",
      "verification_status": "unverified",
      "evidence_id": "E4"
    }
  ]
}
```

Allowed `claim_type`: `metric`, `qualitative`, `forecast`, `tam`. Allowed `verification_status`: `unverified`, `verified`, `conflicted`.

MVP extractor accepts `.txt`, `.md`, and basic PDF/DOCX placeholders. For unsupported binary extraction, it creates an empty claims list and records an open question instead of failing the run.

### 3.6 `company_profile.json`

File: `src/mgt470_analyst/schemas/company_profile.py`

```json
{
  "company": {
    "name": "Duolingo",
    "website": "https://www.duolingo.com",
    "ticker": "DUOL",
    "public_or_private": "public",
    "industry": "unknown",
    "geography": [],
    "stage": "unknown",
    "description": "Company profile normalized from user input and stub research."
  },
  "customers": {
    "primary_user": "unknown",
    "buyer": "unknown",
    "payer": "unknown",
    "segments": []
  },
  "business_model": {
    "value_proposition": "unknown",
    "revenue_model": "unknown",
    "pricing_model": "unknown",
    "distribution_channels": [],
    "cost_drivers": []
  },
  "competition": {
    "incumbents": [],
    "direct_competitors": [],
    "substitutes": []
  },
  "evidence_ids": ["E1"]
}
```

### 3.7 `lens_fit.json`

File: `src/mgt470_analyst/schemas/lens_fit.py`

```json
{
  "primary_type": "decoupling",
  "secondary_types": ["business_model"],
  "confidence": "low",
  "reasoning": "MVP classifier defaults to decoupling lens when customer activity data is sparse.",
  "evidence_ids": ["E1"],
  "decoupling_fit_score": 0.5,
  "recommended_report_mode": "full_decoupling",
  "caveats": ["Replace stub classifier with evidence-weighted logic."]
}
```

Allowed `primary_type`: `decoupling`, `low_end`, `new_market`, `tech_substitution`, `business_model`, `unclear`. Allowed `recommended_report_mode`: `full_decoupling`, `strategic_memo`, `financial_first`.

### 3.8 `cvc.json`

File: `src/mgt470_analyst/schemas/cvc.py`

```json
{
  "customer_segment": "unknown",
  "end_activity": "achieve the customer goal served by the company",
  "activities": [
    {
      "id": "A1",
      "step": 1,
      "activity": "Discover available options",
      "current_provider": "incumbent bundle or existing behavior",
      "customer_goal": "Find a viable way to solve the job",
      "evidence_ids": ["E1"]
    }
  ],
  "profile_vs_cvc_conflicts": []
}
```

### 3.9 `value_type_diagnosis.json`

File: `src/mgt470_analyst/schemas/value_types.py`

```json
{
  "activities": [
    {
      "activity_id": "A1",
      "value_type": "create",
      "reasoning": "Discovery helps the customer begin the job but may still create friction.",
      "money_cost": 1,
      "time_cost": 3,
      "effort_cost": 3,
      "satisfaction": 2,
      "evidence_ids": ["E1"]
    }
  ]
}
```

Allowed `value_type`: `create`, `erode`, `capture`. Cost and satisfaction fields are integers from 1 to 5.

### 3.10 `weak_link_analysis.json`

File: `src/mgt470_analyst/schemas/weak_links.py`

```json
{
  "ranked_weak_links": [
    {
      "activity_id": "A2",
      "score": 24.0,
      "pain_intensity": 3,
      "frequency": 3,
      "ai_or_digital_leverage": 4,
      "willingness_to_switch": 3,
      "value_capture_potential": 3,
      "integration_dependency": 4,
      "rationale": "Stub scoring favors activities with high effort and time cost.",
      "evidence_ids": ["E1"]
    }
  ]
}
```

Score formula:

```text
score = pain_intensity * frequency * ai_or_digital_leverage * willingness_to_switch * value_capture_potential / max(integration_dependency, 1)
```

### 3.11 `decoupling_strategy.json`

File: `src/mgt470_analyst/schemas/decoupling.py`

```json
{
  "primary_decoupling": {
    "activity_to_decouple": "Compare and choose among options",
    "from_incumbent_bundle": "existing customer workflow",
    "customer_pain": "time and effort friction",
    "new_offering": "Focused product that makes this activity cheaper, faster, or easier",
    "why_customer_switches": "The standalone activity removes a painful step without requiring full workflow migration.",
    "cheaper_faster_easier": ["faster", "easier"],
    "evidence_ids": ["E1"]
  },
  "do_not_decouple": [
    {
      "activity": "Payment or commitment",
      "reason": "High integration dependency in MVP scoring.",
      "evidence_ids": ["E1"]
    }
  ]
}
```

### 3.12 `business_model_analysis.json`

File: `src/mgt470_analyst/schemas/business_model.py`

```json
{
  "value_creation": "The offering creates value by reducing customer time and effort in the weak-link activity.",
  "value_capture": "MVP analysis cannot confirm pricing power without real research.",
  "value_erosion_remaining": "Integration and switching friction may remain.",
  "payer": "unknown",
  "pricing_model": "unknown",
  "cac_risks": ["Channel costs are unknown."],
  "ltv_drivers": ["Frequency of the decoupled activity."],
  "unit_economics_concerns": ["No financial backend in MVP."],
  "evidence_ids": ["E1"]
}
```

### 3.13 `competitive_response.json`

File: `src/mgt470_analyst/schemas/competitive_response.py`

```json
{
  "likely_responses": [
    {
      "response_type": "copy",
      "description": "Incumbents may add the decoupled feature to their bundle.",
      "severity": "medium",
      "defense": "Build workflow depth, data advantage, or switching cost around the decoupled activity.",
      "evidence_ids": ["E1"]
    }
  ],
  "recoupling_vulnerability": {
    "vulnerability": "medium",
    "rationale": "MVP defaults to medium when incumbent capabilities are unknown.",
    "incumbent_capability_to_recouple": "medium",
    "incumbent_incentive_to_recouple": "medium",
    "defenses": ["Narrow focus", "workflow data", "customer habit"],
    "evidence_ids": ["E1"]
  }
}
```

Allowed `response_type`: `recouple`, `copy`, `block`, `subsidize`, `acquire`, `partner`. Allowed severity/vulnerability values: `high`, `medium`, `low`.

### 3.14 `final_judgment.json`

File: `src/mgt470_analyst/schemas/final_judgment.py`

```json
{
  "judgment": "study_more",
  "one_sentence_thesis": "The company is worth studying, but MVP stub research is insufficient for a strong investment judgment.",
  "why_now": "The workflow found a plausible weak link but needs real evidence.",
  "strongest_argument": "A focused decoupling can reduce customer effort.",
  "biggest_risk": "Evidence is incomplete because the MVP uses a stub research adapter.",
  "next_research_steps": ["Run real cited research.", "Verify customer segment and willingness to switch."],
  "evidence_ids": ["E1"]
}
```

Allowed `judgment`: `study_more`, `invest_watchlist`, `avoid`, `startup_opportunity`, `unclear`.

## 4. Module Inputs And Outputs

| Module | File | Inputs | Outputs |
|---|---|---|---|
| Intake | `src/mgt470_analyst/modules/intake.py` | CLI args | `RawInput`, run directory, initial `run.json` |
| Research adapter | `src/mgt470_analyst/adapters/research/stub_gpt_researcher.py` | `RawInput` | `ResearchBrief` |
| Evidence store | `src/mgt470_analyst/evidence/store.py` | `RawInput`, `ResearchBrief`, optional deck claims | `evidence_store.json`, generated `E*` IDs |
| Deck extractor | `src/mgt470_analyst/modules/deck_extractor.py` | `RawInput.files` | optional `deck_claims.json`, management-claim evidence |
| Company profile | `src/mgt470_analyst/modules/company_profile.py` | `RawInput`, `ResearchBrief`, `EvidenceStore` | `company_profile.json` |
| Lens fit | `src/mgt470_analyst/modules/lens_fit.py` | `CompanyProfile`, `EvidenceStore` | `lens_fit.json` |
| CVC mapping | `src/mgt470_analyst/modules/cvc.py` | `EvidenceStore`, `CompanyProfile` for cross-check only | `cvc.json` |
| Value types | `src/mgt470_analyst/modules/value_types.py` | `cvc.json`, `EvidenceStore` | `value_type_diagnosis.json` |
| Weak links | `src/mgt470_analyst/modules/weak_links.py` | `cvc.json`, `value_type_diagnosis.json`, `EvidenceStore` | `weak_link_analysis.json` |
| Decoupling | `src/mgt470_analyst/modules/decoupling.py` | `weak_link_analysis.json`, `cvc.json`, `EvidenceStore` | `decoupling_strategy.json` |
| Business model | `src/mgt470_analyst/modules/business_model.py` | `company_profile.json`, `decoupling_strategy.json`, `EvidenceStore` | `business_model_analysis.json` |
| Competitive response | `src/mgt470_analyst/modules/competitive_response.py` | `decoupling_strategy.json`, `company_profile.json`, `EvidenceStore` | `competitive_response.json` |
| Final judgment | `src/mgt470_analyst/modules/final_judgment.py` | all analysis artifacts | `final_judgment.json` |
| Markdown renderer | `src/mgt470_analyst/renderers/markdown.py` | all artifacts | `final_report.md` |
| Evidence validator | `src/mgt470_analyst/evidence/validator.py` | each module artifact, `EvidenceStore` | validated artifact or repaired artifact |

## 5. CLI Calling Convention

Implement a Typer app with one command:

```bash
mgt470 analyze \
  --company "Duolingo" \
  --ticker DUOL \
  --url "https://www.duolingo.com" \
  --mode investment \
  --question "Is this a high-quality AI-leveraged business worth studying?" \
  --file ./inputs/public/duolingo-notes.md \
  --runs-dir ./runs
```

Options:

| Option | Required | Behavior |
|---|---:|---|
| `--company` | yes | Sets `RawInput.company_name`. |
| `--ticker` | no | Sets ticker and infers public company when present. |
| `--url` | no | Can be passed multiple times or once; first URL also becomes `website`. |
| `--file` | no | Can be passed multiple times. |
| `--mode` | no | Defaults to `investment`; maps to `analysis_goal`. |
| `--question` | no | Free-form user question. |
| `--output` | no | Optional final Markdown destination; artifact copy remains in run directory. |
| `--runs-dir` | no | Defaults to `./runs`. |
| `--include-financial-verification` | no | Accepted for schema compatibility but logs that full verification is deferred in MVP. |

Console output should end with:

```text
Run complete: runs/duolingo-20260507-215500
Report: runs/duolingo-20260507-215500/final_report.md
```

## 6. Evidence Validation And One Repair Pass

Every module artifact with factual reasoning must expose evidence references under fields named `evidence_ids` or nested `evidence_id`.

Validation rules:

1. Collect every evidence ID from the artifact.
2. Confirm each ID exists in `evidence_store.json`.
3. Add the module name to `used_by_modules` for every valid referenced evidence item.
4. If missing IDs exist, run one repair pass:
   - If the artifact contains the same claim text as an existing evidence claim, replace the missing ID with that evidence ID.
   - Otherwise add a new evidence entry with `claim_type = "assumption"`, `confidence = "low"`, `source_id = "S0"`, and `locator = "repair pass"`.
5. Validate again.
6. If invalid IDs remain, write `<artifact>.error.json`, mark the module as `error` in `run.json`, and stop downstream modules.

MVP repair is deterministic Python logic, not an LLM retry.

## 7. Implementation Tasks

### Task 1: Project Packaging And CLI Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/mgt470_analyst/__init__.py`
- Create: `src/mgt470_analyst/cli.py`
- Create: `tests/test_cli_analyze.py`

- [ ] Add package metadata, dependencies, and a console script named `mgt470`.
- [ ] Implement a Typer app with `analyze` options but return a clear "orchestrator not wired yet" message in the first test step.
- [ ] Add a CLI smoke test with Typer's `CliRunner`.
- [ ] Run `pytest tests/test_cli_analyze.py -v`.

### Task 2: Core Schemas

**Files:**
- Create: every file under `src/mgt470_analyst/schemas/`
- Create: `tests/test_schemas.py`

- [ ] Define Pydantic models for every artifact listed in section 3.
- [ ] Use enums or literals for constrained fields.
- [ ] Add schema tests that instantiate the example payloads in section 3.
- [ ] Add tests that reject unknown evidence confidence, invalid value type, and out-of-range cost scores.
- [ ] Run `pytest tests/test_schemas.py -v`.

### Task 3: Artifact IO, Paths, And Hashing

**Files:**
- Create: `src/mgt470_analyst/io/json_artifacts.py`
- Create: `src/mgt470_analyst/paths.py`
- Create: `src/mgt470_analyst/hashing.py`
- Create: `tests/test_orchestrator_happy_path.py`

- [ ] Implement slugified run IDs: `<company-slug>-<YYYYMMDD-HHMMSS>`.
- [ ] Implement `write_json_artifact(path, model)` and `read_json_artifact(path, model_type)`.
- [ ] Implement stable SHA-256 hashing for input dictionaries.
- [ ] Test that artifacts are written under a temporary `runs_dir` and can be read back.

### Task 4: Research Adapter Interface And Stub GPT Researcher

**Files:**
- Create: `src/mgt470_analyst/adapters/research/base.py`
- Create: `src/mgt470_analyst/adapters/research/stub_gpt_researcher.py`

- [ ] Define `ResearchAdapter.research(raw_input: RawInput) -> ResearchBrief`.
- [ ] Implement `StubGPTResearcherAdapter` that converts CLI company, website, URLs, and files into stub sources and open questions.
- [ ] Ensure no network access occurs.
- [ ] Add schema-backed tests through the orchestrator happy path.

### Task 5: Evidence Store And Validator

**Files:**
- Create: `src/mgt470_analyst/evidence/store.py`
- Create: `src/mgt470_analyst/evidence/validator.py`
- Create: `tests/test_evidence_validator.py`

- [ ] Implement `EvidenceStore.add_claim(...) -> EvidenceItem`.
- [ ] Seed `S0` as the user-input source and create at least one `E*` claim from the raw input.
- [ ] Implement recursive evidence ID collection for Pydantic models, dictionaries, and lists.
- [ ] Implement the one repair pass described in section 6.
- [ ] Test valid IDs, missing IDs repaired as assumptions, and `used_by_modules` updates.

### Task 6: Deck Claim Extractor Stub

**Files:**
- Create: `src/mgt470_analyst/modules/deck_extractor.py`
- Add fixture: `tests/fixtures/inputs/private_deck_basic.txt`

- [ ] Detect `.txt` and `.md` files and extract lines containing simple claim signals: `%`, `$`, `ARR`, `revenue`, `growth`, `TAM`, `YoY`.
- [ ] Write extracted claims as `deck_claims.json`.
- [ ] Add each deck claim to the evidence store as `management_claim`.
- [ ] For `.pdf`, `.docx`, and unsupported files, record no claims in MVP and keep the run alive.

### Task 7: Deterministic Analysis Modules

**Files:**
- Create: all files under `src/mgt470_analyst/modules/` listed in section 4.

- [ ] Implement company profile normalizer from raw input and research brief.
- [ ] Implement lens fit classifier with conservative heuristic defaults.
- [ ] Implement CVC mapper with 4 generic activities: discover options, compare options, choose/commit, use/renew.
- [ ] Implement value type diagnosis based on activity role.
- [ ] Implement weak link scoring with the MVP formula.
- [ ] Implement decoupling strategy from the top weak link.
- [ ] Implement lightweight business model analysis from profile and decoupling output.
- [ ] Implement competitive response with embedded recoupling risk.
- [ ] Implement final judgment with `study_more` default when evidence remains stubbed or sparse.

### Task 8: Orchestrator

**Files:**
- Create: `src/mgt470_analyst/orchestrator.py`
- Modify: `src/mgt470_analyst/cli.py`
- Extend: `tests/test_orchestrator_happy_path.py`

- [ ] Wire modules in this order: intake, research, deck extractor, evidence store write, company profile, lens fit, CVC, value types, weak links, decoupling, business model, competitive response, final judgment, markdown render.
- [ ] After each module writes an artifact, validate evidence IDs and update `used_by_modules`.
- [ ] Update `run.json` after every module with status, input hash, and output path.
- [ ] Stop downstream modules only if the second validation pass still fails.
- [ ] Return run directory and report path to the CLI.

### Task 9: Markdown Renderer

**Files:**
- Create: `src/mgt470_analyst/renderers/markdown.py`
- Create: `tests/test_markdown_renderer.py`

- [ ] Render Obsidian-friendly frontmatter.
- [ ] Render these sections: executive summary, company snapshot, evidence base, business model, CVC, value creation/erosion/capture, weak link, decoupling strategy, competitive response and recoupling risk, risks/missing data, final recommendation, reusable lessons.
- [ ] Include evidence IDs inline in tables or bullets.
- [ ] Test that the report contains the company name, final judgment callout, weak link section, and evidence base.

### Task 10: Happy Path Fixture And End-To-End Test

**Files:**
- Create: `tests/fixtures/inputs/duolingo_basic.json`
- Extend: `tests/test_orchestrator_happy_path.py`

- [ ] Build a test raw input for Duolingo with company, ticker, website, and one question.
- [ ] Run the full orchestrator in a temporary directory.
- [ ] Assert that all MVP artifacts exist:
  - `run.json`
  - `research_brief.json`
  - `evidence_store.json`
  - `company_profile.json`
  - `lens_fit.json`
  - `cvc.json`
  - `value_type_diagnosis.json`
  - `weak_link_analysis.json`
  - `decoupling_strategy.json`
  - `business_model_analysis.json`
  - `competitive_response.json`
  - `final_judgment.json`
  - `final_report.md`
- [ ] Assert that all evidence references in artifacts are valid after repair.
- [ ] Assert that `runs/` remains gitignored.

## 8. Testing Strategy

Run focused tests as each task lands:

```bash
pytest tests/test_schemas.py -v
pytest tests/test_evidence_validator.py -v
pytest tests/test_markdown_renderer.py -v
pytest tests/test_orchestrator_happy_path.py -v
pytest tests/test_cli_analyze.py -v
```

Before considering MVP complete:

```bash
ruff check .
pytest -v
mgt470 analyze --company "Duolingo" --ticker DUOL --url "https://www.duolingo.com" --mode investment --runs-dir ./runs
```

Expected manual verification:

- All artifacts are present under one run directory.
- `run.json` shows every module as `ok`.
- `evidence_store.json` includes `used_by_modules`.
- `final_report.md` is readable in GitHub and Obsidian.
- No private files, course materials, `.env`, or `runs/` files appear in `git status --short`.

## 9. First Happy Path Example

Command:

```bash
mgt470 analyze \
  --company "Duolingo" \
  --ticker DUOL \
  --url "https://www.duolingo.com" \
  --mode investment \
  --question "Is this a high-quality AI-leveraged business worth studying?" \
  --runs-dir ./runs
```

Expected run directory:

```text
runs/duolingo-20260507-215500/
  run.json
  research_brief.json
  evidence_store.json
  company_profile.json
  lens_fit.json
  cvc.json
  value_type_diagnosis.json
  weak_link_analysis.json
  decoupling_strategy.json
  business_model_analysis.json
  competitive_response.json
  final_judgment.json
  final_report.md
```

Expected report thesis:

```markdown
> [!important] Final Judgment
> The company is worth studying, but MVP stub research is insufficient for a strong investment judgment.
```

This example is intentionally evidence-light. Its purpose is to prove that the local pipeline, schemas, artifacts, evidence validation, and Markdown renderer work before connecting real research or financial data.

## 10. Out Of Scope Until After MVP Skeleton

- Real GPT Researcher integration.
- OpenBB, SEC, yfinance, or paid financial connectors.
- Web UI, Streamlit, Gradio, or FastAPI.
- LangGraph orchestration.
- Batch screening.
- Obsidian vault writer.
- Full pitch deck PDF/DOCX extraction beyond a safe stub.
- Dedicated `ai_leverage.json`, `financial_verification.json`, `recoupling_vulnerability.json`, or `coupling_growth.json`.
- Content-addressed cache, `--resume`, and `--rerun`.

