# MGT470 Business Decoupling Analyst

Local-first AI workflow for Teixeira-style business model, decoupling, and investment analysis.

The project takes incomplete company information (name, website, pitch deck, memo, filing, notes) and produces a reproducible analysis pipeline:

```text
raw input
  -> research brief             (OpenAI-backed)
  -> evidence store             (claims + sources, audit trail)
  -> normalized company profile
  -> lens fit (which strategic lens)
  -> customer value chain (rebuilt from evidence)
  -> value type diagnosis (create/erode/capture)
  -> weak link analysis
  -> decoupling strategy
  -> business model judgment
  -> competitive response + recoupling risk
  -> final judgment
  -> professional Markdown report (Obsidian-ready)
```

See [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) for the full architecture.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Install gpt-researcher

Phase 2 uses Austin's pinned GPT Researcher fork for live cited web research:

```bash
pip install \
  "gpt-researcher @ git+https://github.com/Austin-Li7/gpt-researcher.git@92bfc0388c5f7a03b6cb34eaf6ae14298a4b458e"
```

DuckDuckGo is the default search backend. Tavily is optional:

```bash
pip install "mgt470-analyst[research-tavily]"
export TAVILY_API_KEY=tvly-...
```

#### GPT Researcher pin policy

The dependency is pinned to Austin's fork because that fork carries project
fixes before they are upstreamed. To update it, edit this `pyproject.toml` line:
`"gpt-researcher @ git+https://github.com/Austin-Li7/gpt-researcher.git@<sha>",`.
Then reinstall the fork and package:

```bash
.venv/bin/pip install --force-reinstall \
  "gpt-researcher @ git+https://github.com/Austin-Li7/gpt-researcher.git@<sha>"
.venv/bin/pip install --force-reinstall --no-deps .
```

Before merging a pin bump, run `pytest -q`, `ruff check src tests`, and one live
Notion run; confirm `research_brief.json` still has at least 10 sources.

### Configure your OpenAI API key

Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY`:

```bash
cp .env.example .env
# then edit .env and replace sk-... with your real key
```

The CLI auto-loads `.env` on startup. `.env` is gitignored.

Alternatively, export it in your shell:

```bash
export OPENAI_API_KEY=sk-...
```

If no key is found, the pipeline falls back to **offline mode** (deterministic
fakes) so tests and dry runs still work — but the output will not contain real
analysis. Set `MGT470_OFFLINE=1` to force offline even with a key.

Research defaults to `MGT470_RESEARCH_BACKEND=gpt_researcher` when
`OPENAI_API_KEY` is set. Set `MGT470_RESEARCH_BACKEND=stub` to force the
pre-Phase-2 knowledge-only research adapter.

### Model routing

Three roles are routed to different models. Defaults below; override via env:

| Role | Default | Used by |
|---|---|---|
| `fast` | `gpt-4o-mini` | deck extractor, company profile, lens fit, value types |
| `smart` | `gpt-4o` | CVC, weak links, decoupling, business model, competitive, final judgment |
| `research` | `gpt-4o` | research adapter |

```bash
export MGT470_MODEL_FAST=gpt-4o-mini
export MGT470_MODEL_SMART=gpt-5
```

## Usage

```bash
mgt470 analyze \
  --company "Duolingo" \
  --ticker DUOL \
  --url https://www.duolingo.com \
  --file path/to/case.pdf \
  --mode investment
```

Outputs land in `runs/<slug>-<timestamp>/`:

```
runs/duolingo-20260508-014230/
  run.json                       # manifest
  research_brief.json
  deck_claims.json               # if a deck was supplied
  evidence_store.json            # global audit layer
  company_profile.json
  lens_fit.json
  cvc.json
  value_type_diagnosis.json
  weak_link_analysis.json
  decoupling_strategy.json
  business_model_analysis.json
  competitive_response.json
  final_judgment.json
  final_report.md                # the deliverable
```

## Testing

Tests run in offline mode automatically (no API key required):

```bash
pytest -q
```

To run the (currently empty) live smoke tests against a real API key:

```bash
MGT470_RUN_LIVE=1 pytest -m live
```
