# Path C Development Plan — Computable Methodology + Cases

> **For Claude Code (or any AI coding assistant) entering this repo cold.**
> Read this file first. Then execute phases in order. Each phase has files to
> touch, external deps to install, skills to invoke, and an acceptance test.

---

## Why this plan exists

The owner (Austin, MSBA student) is building this as a **portfolio + personal
analysis tool**, not as a SaaS or product. The end-state is a "computable
methodology" — a public artifact that combines:

1. A working Python tool that encodes Teixeira's MGT470 Digital Disruption
   framework as a 13-step LLM workflow with cross-pass critic.
2. A formal `METHODOLOGY.md` that maps every prompt design choice back to a
   Teixeira principle.
3. 10 real case studies (public + private mix) showing the tool applied
   end-to-end with human takeaways.
4. A plugin (MCP server) interface so any agent (Claude Code, Cursor) can
   call it.
5. A blog post launching the project publicly.

Distinguishing claim: **"I compiled an MBA course into 1,500 lines of Python
and tested it on 10 real companies."**

---

## Project state when this plan was written

- Repo: `/Users/lichenchangwen/Desktop/myprojects/mgt470-business-decoupling`
- Python 3.13, venv at `.venv/`
- 14 modules done, all LLM-driven (gpt-5-mini fast / gpt-5.2 smart)
- Critic cross-pass module (`modules/critic.py`) operational
- Mermaid renderers + Citation/Sources block done
- Tests: 16/16 passing, ruff clean
- Live-verified on: Duolingo, Apple, Flipkart (PDF), OLX (PDF), Trov (PDF),
  Birchbox (PDF), Zalora (PDF), Dropbox (PDF), Stripe
- `.env` has `OPENAI_API_KEY` set
- Models default: `MGT470_MODEL_FAST=gpt-5-mini`, `MGT470_MODEL_SMART=gpt-5.2`,
  `MGT470_MODEL_RESEARCH=gpt-5.2`, `MGT470_EFFORT_SMART=medium`
- No CI yet, no GitHub remote yet

### Known gotchas (must read before coding)

1. **macOS hidden `.pth` bug**: setuptools editable install creates a `.pth`
   file with the macOS `hidden` flag, which Python 3.13's `site.py` skips.
   **Fix**: install non-editable: `.venv/bin/pip install --force-reinstall --no-deps .`
   after every src/ change. NOT `pip install -e .`.
2. **Sandbox writes to `/tmp/mgt470-*`** for live test runs to avoid
   polluting `runs/` (which is gitignored anyway).
3. **`pyproject.toml` ruff config**: `select = ["E", "F", "I", "UP", "B"]`,
   line-length 100, py311 target — keep that, don't bump.
4. **Tests force offline mode** via `tests/conftest.py` autouse fixture;
   they never hit OpenAI. Don't break that contract.
5. **Schema discipline**: `extra = "forbid"` on every Pydantic schema.
   Adding new fields requires updating fakes (`src/mgt470_analyst/llm/fake.py`).

### Run quickly to confirm the baseline still works

```bash
cd /Users/lichenchangwen/Desktop/myprojects/mgt470-business-decoupling
.venv/bin/python -m pytest -q                    # expect 16 passed
.venv/bin/ruff check src tests                    # expect "All checks passed!"
.venv/bin/mgt470 analyze --company "Stripe" --runs-dir /tmp/mgt470-smoke
                                                  # expect ~5min, $0.30
```

If those don't all pass, **stop and debug before starting Phase 1**.

---

## Phase ladder (execute in order)

> **Sequencing principle**: build the knowledge layer → build the research
> layer → **validate against professor's published takeaways** → iterate
> prompts until alignment is solid → THEN run remaining cases. Don't
> batch-produce cases on an unvalidated framework.

| # | Phase | Time est | Cost est | New deps |
|---|---|---|---|---|
| 1 | RAG over MGT470 notes (Austin's writeups) | 1-2 days | ~$0.10 (one-time embed) | chromadb, openai (already) |
| 1.5 | RAG over Teixeira public corpus (book / blog / talks) | 1-2 days | ~$0.50 (embed + transcribe) | yt-dlp, openai-whisper, beautifulsoup4 |
| 2 | GPT Researcher integration (Austin's fork) + DuckDuckGo / Tavily backend | 1-2 days | $0 free DDG / $0 Tavily free tier | git+Austin-Li7/gpt-researcher fork, tavily-python (optional) |
| 3 | **VALIDATION** — iterate prompts on 4 anchor cases (OLX/Flipkart/Trov/Birchbox) until alignment with professor's takeaways scores ≥4/5 on average | 3-5 days | ~$5-15 in iteration tokens | none |
| 4 | MCP wrapper | half day | $0 | mcp |
| 5 | Run 6 new case studies (post-validation) + write human takeaways | 3-4 days | ~$5-8 | none |
| 6 | METHODOLOGY.md | 2-3 days | $0 | none |
| 7 | Blog post + README polish | 1-2 days | $0 | none |
| 8 | GitHub publish | half day | $0 | none |
| | **Total** | **3-4 weeks part-time** | **~$25-30** | |

Don't try to do all phases in one session. Each phase is a clean
checkpoint — commit after each, optionally invoke `engineering:code-review`
skill before merging.

**Phase 3 (Validation) is non-negotiable**. Skipping it means the 6 new
case studies in Phase 5 will be running on an unvalidated framework, and
mediocre case studies are worse than fewer high-quality ones for portfolio
purposes.

---

## Phase 1 — RAG over MGT470 notes

### Goal

Make the tool actually use Austin's existing course notes, case write-ups,
and methodology breakdowns when analyzing companies. Today every run starts
from zero — after this, every run can pull "OLX case takeaway" or "Teixeira
on layered evolution" verbatim from his notes.

### Why this is highest leverage

The single largest gap between "generic AI MGT470 analyst" and "Austin's
personal MGT470 analyst" is whether the model has seen Austin's accumulated
understanding. Without RAG, every analysis re-derives the framework. With
RAG, every analysis stands on the previous 10 weeks of class.

### Source corpus to index

```
MGT470/                              ← high-priority (Austin's own writeups)
  MGT470 Decoupling + AI 杠杆复用框架.md
  MGT470 全课知识串联与商业判断框架.md
  MGT470-chatgpt/                   ← case-specific analyses
    MGT470 - OLX Brazil Case 分析.md
    MGT470 - Birchbox.md
    MGT470 - Monetizing Insurance Trov.md
    MGT470 - Tower paddle board & Amazon Case.md
    MGT470 - Wayfair Q1.md
    MGT470 - Zalora PH 盈利分析.md
    MGT470 - Zulily Case Analysis.md
    MGT470 - 深入理解Dropbox案例.md
    MGT470 - Iva Teixeira 解析.md
    MGT470 - Rental Deposit Protection.md
    MGT470 - 商业模型拆解创新方法.md
    MGT470 - 捕鲸权利争议.md
    Etsy  Uber first thousand customers.md
    MGT470 - Pitch与Proposal区别.md
    MGT470 - Assignment Case 分析.md

MGT470-course material/              ← lower-priority (raw PDFs, big)
  MGT470_Decoupling_AI_Reusable_Framework.md  ← include this one
```

Skip the raw PDFs in `MGT470-course material/` for now; they're already
extracted by `deck_extractor` when the user passes `--file`.

### Tech choices

- **Vector store**: `chromadb` (local persistent, no server needed). Stored
  at `~/.cache/mgt470-analyst/notes_index/`.
- **Embedding model**: `text-embedding-3-small` (OpenAI, $0.02 / 1M tokens —
  the whole corpus is < $0.10 to embed).
- **Chunking**: split by Markdown header (h2/h3); fall back to ~600-token
  chunks. Each chunk keeps source path + heading trail as metadata.
- **Retrieval**: top-5 chunks per query, with re-ranking by simple keyword
  overlap on company name to surface case-specific notes when applicable.

### Files to create

```
src/mgt470_analyst/
  rag/
    __init__.py
    indexer.py           # build the chroma index from MGT470/ folder
    retriever.py         # query interface used by modules
    chunker.py           # Markdown-aware chunking
```

### Files to touch

- `pyproject.toml`: add `chromadb>=0.5`, `markdown-it-py>=3` to dependencies
- `src/mgt470_analyst/llm/prompts.py`: add `render_methodology_context()`
  that takes retriever results and renders them into a prompt block
- Each downstream module (cvc, weak_links, decoupling, business_model,
  competitive_response, final_judgment) — accept a `methodology_context`
  string and prepend it to the user prompt
- `src/mgt470_analyst/orchestrator.py`: instantiate retriever once per run,
  call `retrieve_for_module(company_name, module_name, perspective)` before
  each LLM-driven step, pass result down
- `src/mgt470_analyst/cli.py`: add `mgt470 reindex` command that rebuilds
  the notes index from disk

### CLI additions

```bash
mgt470 reindex                                    # rebuild notes index
mgt470 reindex --notes-dir /custom/path          # override source dir
mgt470 analyze --company X --no-rag              # disable RAG (for ablation)
```

### Step-by-step

1. **Read** `MGT470/MGT470 全课知识串联与商业判断框架.md` cover to cover so
   you understand what's in the corpus. The framework prompt should mirror
   its structure.
2. **Add deps**: `chromadb>=0.5`, `markdown-it-py>=3`. Reinstall.
3. **Implement `chunker.py`**: parse Markdown, emit chunks with metadata
   `{source_path, heading_trail, chunk_index, text}`. Keep chunks 200-800
   tokens.
4. **Implement `indexer.py`**: walk the MGT470 directories, chunk each file,
   embed with `text-embedding-3-small`, persist to ChromaDB at
   `~/.cache/mgt470-analyst/notes_index/`. Idempotent — only re-embeds if
   file mtime changed.
5. **Implement `retriever.py`**:
   ```python
   class MethodologyRetriever:
       def retrieve_for_module(
           self,
           module_name: str,
           company_name: str,
           perspective: str | None = None,
           top_k: int = 5,
       ) -> list[Chunk]: ...
   ```
   The query string should combine: module-specific framing + company name
   + perspective hint. Example for `decoupling` module:
   `"decoupling strategy {company} {perspective} weak link Teixeira"`.
6. **Update prompts**: in `llm/prompts.py` add:
   ```python
   def render_methodology_context(chunks: list[Chunk]) -> str:
       """Format retrieved notes as a 'Course context' block."""
   ```
   Each module prepends this to its user prompt under a heading like:
   ```
   === COURSE CONTEXT (Austin's MGT470 notes) ===
   [chunk 1 with source attribution]
   [chunk 2 ...]
   === END COURSE CONTEXT ===
   ```
7. **Wire through orchestrator**: instantiate `MethodologyRetriever` once,
   pass to each module call. Modules accept `methodology_context: str = ""`
   parameter (default empty for backwards compat / offline mode).
8. **Update tests**:
   - `tests/conftest.py`: monkey-patch `MethodologyRetriever` to return
     empty list in offline mode.
   - Or: gate the indexer behind an env var `MGT470_RAG=1`, default off.
   - Add a test that confirms retriever stub returns empty when disabled.
9. **Run live**: `mgt470 reindex && mgt470 analyze --company "OLX Brazil"
   --file MGT470-course\ material/.../OLX.pdf`. Compare to v3 run from
   `/tmp/mgt470-v3/olx-brazil-*` — the new output should cite Austin's own
   "避免 jobs 垂直" insight, not just rederive it.

### Acceptance criteria

- `pytest -q` still 16+/16+ passing
- `ruff check` clean
- `mgt470 reindex` produces a `~/.cache/mgt470-analyst/notes_index/` of
  reasonable size (~5-20 MB)
- Live OLX run shows at least 2 of Austin's note quotes in the output
  (search for distinctive phrases like "供给密度战" or "守住核心")
- `mgt470 analyze --no-rag` produces output identical to pre-RAG version
  (ablation works)

### Skills to invoke

- **`engineering:debug`** if chromadb installation has issues on macOS arm64
  (it sometimes needs sqlite version tweaks)
- **`engineering:code-review`** before committing the new `rag/` module
- **`simplify`** after Phase 1 lands — the chunker is the kind of module
  that grows hair if you let it

### Commit message template

```
feat(rag): inject MGT470 course notes via local ChromaDB index

- Add rag/ module: chunker, indexer, retriever
- Each LLM module receives top-5 relevant note chunks per call
- New CLI command: mgt470 reindex
- Backwards compat: --no-rag flag and offline mode skip retriever
```

---

## Phase 1.5 — RAG over Teixeira's public corpus

### Goal

Add Thales Teixeira's own published writing and talks as a SECOND layer
in the RAG index. This gives the model access to "primary source" material
(in Teixeira's own voice) on top of Austin's notes (secondary
interpretation).

### Why

Austin's notes are excellent but condensed and translated. The model
should also see Teixeira's exact phrasing for terms like "decoupling,"
"value-erosion," and "layered evolution." When the analyst-LLM cites
"per Teixeira's framework, X is a value-eroding activity," it should
ideally be quoting from primary source, not paraphrasing a paraphrase.

### Sources to harvest

| Source | Type | How to fetch |
|---|---|---|
| `decoupling.io` (his consulting site) | HTML articles | beautifulsoup4 scrape, save as Markdown |
| `Unlocking the Customer Value Chain` book | Book chapters / excerpts on web | Search excerpts on Google Books, archive.org, his site |
| HBR articles by Thales Teixeira | Articles | URLs from HBR site (some paywalled — use abstracts) |
| YouTube talks (HBR, Stanford, podcasts) | Video → transcript | yt-dlp + openai-whisper, OR use existing transcripts (some videos have CC) |
| LinkedIn posts | Public posts | Manual copy or LinkedIn API (requires auth) |
| Conference talks (Mind the Bridge, etc.) | Slides / video | Manual collection |
| Twitter / X posts | Manual | Manual collection (low priority) |

### Files to create

```
src/mgt470_analyst/rag/
  primary_corpus/
    fetch_decoupling_io.py        # scrape his consulting site
    fetch_youtube_transcripts.py  # yt-dlp + whisper for 5-10 talks
    sources.yaml                  # canonical list of URLs to fetch
  primary_index_builder.py        # builds a separate ChromaDB collection
                                  # tagged "primary_teixeira" for higher weight
```

```
data/
  teixeira_corpus/                # gitignored; raw fetched content
    decoupling_io/
      *.md
    talks/
      *.md   (transcripts)
    books/
      unlocking_cvc_excerpts.md
```

### Files to touch

- `pyproject.toml`: add `yt-dlp`, `openai-whisper`, `beautifulsoup4`,
  `httpx` (some may already be transitive)
- `src/mgt470_analyst/rag/retriever.py`: support **two collections**
  (austin_notes + primary_teixeira) and weight primary 1.5x in the merged
  result
- `.gitignore`: add `data/teixeira_corpus/`

### Step-by-step

1. **Compile `sources.yaml`** — list every URL/video to fetch. Start with
   ~5-10 highest-signal items:
   ```yaml
   articles:
     - https://decoupling.io/article/...
     - https://hbr.org/2019/...
   books:
     - title: Unlocking the Customer Value Chain
       excerpts: [URL_to_chapter_1_preview, URL_to_amazon_look_inside]
   talks:
     - title: "Thales Teixeira on Decoupling"
       url: https://youtube.com/watch?v=...
       use_existing_captions: true
   ```
2. **Implement `fetch_decoupling_io.py`**:
   - Use beautifulsoup4 to crawl decoupling.io article pages
   - Extract h1, h2, body text → Markdown
   - Save to `data/teixeira_corpus/decoupling_io/<slug>.md`
3. **Implement `fetch_youtube_transcripts.py`**:
   - For each video URL: try `yt-dlp --write-auto-sub --skip-download` first
     (fast, free, decent quality)
   - If no captions: download audio with `yt-dlp -x` and transcribe with
     `whisper` (slower, ~$0 if local model)
   - Save as `data/teixeira_corpus/talks/<title-slug>.md` with metadata
     header (title, URL, date, source)
4. **Update indexer**: index this corpus into a separate ChromaDB collection
   tagged `primary_teixeira`. Use the same chunker.
5. **Update retriever**: when both collections are available, retrieve
   top-3 from primary + top-3 from austin_notes, merge with primary
   chunks slightly preferred (1.5x score boost).
6. **Update `render_methodology_context`**: format primary chunks under a
   distinct heading "Primary source (Teixeira)" so the LLM can cite them
   correctly.

### Acceptance criteria

- `data/teixeira_corpus/` has at least 8-15 documents (5+ articles + 3+
  talk transcripts + book excerpts)
- `mgt470 reindex` builds 2 ChromaDB collections without errors
- Live OLX run: at least 1 quote/paraphrase in the report attributed to
  primary Teixeira source (not just Austin's notes)
- Primary corpus is gitignored (don't commit copyrighted content)

### Skills to invoke

- **`engineering:debug`** when yt-dlp / whisper inevitably has macOS
  audio-codec issues
- **`general-purpose`** Agent (the parent skill) — this is a good
  candidate for delegating the "find and harvest 10 Teixeira sources"
  task in one shot, since it's bounded and parallelizable

### Commit message template

```
feat(rag): add Teixeira primary-source corpus to knowledge index

- New rag/primary_corpus/ harvesters: decoupling.io scraper + YouTube
  transcript fetcher (yt-dlp + whisper fallback)
- Indexed into separate ChromaDB collection 'primary_teixeira'
- Retriever merges austin_notes + primary_teixeira with 1.5x weight
  on primary
- Corpus gitignored under data/
```

---

## Phase 2 — GPT Researcher integration (using Austin's fork)

### Goal

Replace the "model uses its training-cutoff knowledge" research adapter
with a real autonomous research agent (GPT Researcher) that runs
multi-query iterative research and produces cited reports. Use Austin's
own fork at https://github.com/Austin-Li7/gpt-researcher so domain-
specific prompt customizations can be merged in over time.

### Why GPT Researcher (and not just Tavily directly)

GPT Researcher and Tavily are NOT alternatives — gpt-researcher is an
agent ON TOP OF a search backend. Pipeline:

```
mgt470 research_module
    ↓
GPTResearcher (multi-query orchestrator + ranking + citations)
    ↓
Tavily / DuckDuckGo / Bing  ← pick one as the underlying search API
```

Reasons to use Austin's gpt-researcher fork:

1. **He's already forked it** — has skin in the game and can customize
   research prompts to MGT470 angles (e.g., "research this company
   from a Teixeira decoupling perspective" not "research this company")
2. **Multi-query autonomy** — it self-decomposes into sub-queries
   (financial, competitive, recent news) without us hand-coding it
3. **Native citations** — output already has source URLs attached
4. **Bounded agent in module is fine** — the workflow stays
   deterministic; only the research module is "agent-shaped"
5. **Pluggable search backend** — start with DuckDuckGo (free), add
   Tavily (free 1000/mo) when DDG quality lags

### Tech choices

- **Orchestrator**: gpt-researcher from Austin's fork
- **Search backend**:
  - **Default**: DuckDuckGo (free, no signup)
  - **Optional upgrade**: Tavily (sign up at tavily.com, free 1000/mo)
- **LLM backend for gpt-researcher itself**: same OpenAI key we already have

### Files to create

```
src/mgt470_analyst/adapters/research/
  gpt_researcher_adapter.py    # wraps GPTResearcher into our adapter interface
```

### Files to touch

- `pyproject.toml`:
  - Replace any `tavily-python` direct dep with:
    `gpt-researcher @ git+https://github.com/Austin-Li7/gpt-researcher.git`
  - Optional: also add `tavily-python>=0.5` if user wants Tavily backend
- `src/mgt470_analyst/adapters/research/__init__.py`: export new adapter
- `src/mgt470_analyst/orchestrator.py`: select adapter by env var:
  - `MGT470_RESEARCH_BACKEND=gpt_researcher` → GPTResearcherAdapter
    (default if `OPENAI_API_KEY` is set)
  - `MGT470_RESEARCH_BACKEND=stub` → keep current `OpenAIResearchAdapter`
    (knowledge-only fallback, used in offline mode)
- `.env.example`: document `TAVILY_API_KEY` (optional) and
  `MGT470_RESEARCH_BACKEND`
- `README.md`: install instructions for gpt-researcher fork

### Step-by-step

1. **Install gpt-researcher from Austin's fork**:
   ```bash
   .venv/bin/pip install \
       git+https://github.com/Austin-Li7/gpt-researcher.git
   ```
2. **Verify import** works:
   ```python
   from gpt_researcher import GPTResearcher
   ```
3. **Read gpt-researcher's README** in the fork — note the env vars it
   expects (`OPENAI_API_KEY`, optional `TAVILY_API_KEY`). It can use
   DuckDuckGo by default if no Tavily key.
4. **Implement `GPTResearcherAdapter`**:
   ```python
   from gpt_researcher import GPTResearcher

   class GPTResearcherAdapter(ResearchAdapter):
       async def _research_async(self, raw_input):
           query = self._build_query(raw_input)
           researcher = GPTResearcher(
               query=query,
               report_type="research_report",  # or "outline_report"
               config_path=None,
           )
           await researcher.conduct_research()
           report = await researcher.write_report()
           sources = researcher.get_source_urls()
           return self._normalize(report, sources, raw_input)

       def research(self, raw_input):
           import asyncio
           return asyncio.run(self._research_async(raw_input))

       def _build_query(self, raw_input):
           # MGT470-specific framing: ask the agent to research
           # Teixeira-relevant facts, not generic facts.
           return (
               f"Research {raw_input.company_name} for a Teixeira-style "
               f"MGT470 digital disruption analysis. Focus on: "
               f"customer value chain (who's the customer, what's the job, "
               f"where's the friction); current monetization and unit "
               f"economics if disclosed; main competitors and their bundle "
               f"vs this company's; signs of decoupling already happening; "
               f"any reported pain points from customers; recent (last 12 "
               f"months) strategic moves."
           )

       def _normalize(self, report, sources, raw_input):
           # Map gpt-researcher output into our ResearchBrief schema
           ...
   ```
5. **Customize the research prompt** in Austin's fork (optional, advanced):
   if vanilla gpt-researcher's queries are too generic, edit the
   sub-query generation prompt in his fork to add MGT470 framing. This
   is why having his own fork matters.
6. **Update orchestrator** to select adapter by env var, default to
   `gpt_researcher` when `OPENAI_API_KEY` is set, fall back to stub in
   offline mode.
7. **Add cost guardrail**: cap gpt-researcher's query depth via its
   `max_iterations` config so a single run doesn't blow $5+ in API
   calls. Target: ≤ $1 for the research phase.
8. **Run live**: `mgt470 analyze --company "Notion"`. Compare the
   research_brief.json before/after — should now have 10-20 cited
   sources with real URLs vs the previous 3-5 model-knowledge sources.

### Acceptance criteria

- `pytest -q` still passing (tests force offline mode → stub adapter)
- Live Notion run shows ≥10 sources in research_brief.json with real
  URLs that resolve in browser
- Evidence store has E* entries with locators pointing to real web pages
- Research phase cost ≤ $1 per run (verify by counting tokens or
  estimating from gpt-researcher logs)
- Both `MGT470_RESEARCH_BACKEND=stub` and `=gpt_researcher` paths work

### Skills to invoke

- **`engineering:debug`** — gpt-researcher is async-heavy and has its
  own quirks; expect to debug
- **`engineering:code-review`** before merging
- **`simplify`** after — the adapter wrapper is the kind of code that
  grows duplicated normalization

### Commit message template

```
feat(research): integrate GPT Researcher (Austin's fork) as default adapter

- pip install from git+Austin-Li7/gpt-researcher
- New GPTResearcherAdapter normalizes its output to our ResearchBrief
- MGT470-framed query template (Teixeira angle, not generic)
- DuckDuckGo backend by default; optional Tavily upgrade
- Stub adapter retained as fallback for offline mode and CI
```

---

## Phase 3 — VALIDATION (iterate prompts on 4 anchor cases)

### Goal

Before running any new case studies, prove the framework actually
captures Teixeira's thinking. Re-run the 4 cases with published
professor takeaways (OLX / Flipkart / Trov / Birchbox), score the
output against the takeaways, and **iterate on prompts until average
fidelity ≥ 4/5**.

### Why this is non-negotiable

If the framework drifts from Teixeira's actual thinking, every
subsequent case study (Phase 5) compounds the drift. Better to spend
3-5 days here making the prompts truly Teixeira-faithful than to
ship 10 mediocre cases.

This is also the phase where the **value of RAG and primary corpus
gets proven**. If after Phase 1 + 1.5 + 2 the OLX run still doesn't
quote Austin's note "避免 jobs 垂直" or fails to recommend "守住核心
+ 分层服务化," something is wrong upstream.

### 4 anchor cases + their published takeaways

| Case | Source for ground truth | Key takeaways the AI MUST capture |
|---|---|---|
| OLX Brazil | `MGT470/MGT470-chatgpt/MGT470 - OLX Brazil Case 分析.md` | (1) preserve free posting + local discovery; (2) layered services from matching → intermediation → only later payments; (3) avoid jobs vertical; (4) Brazil logistics fit drives classifieds model |
| Flipkart | `MGT470/MGT470 全课知识串联与商业判断框架.md` §5.3 | (1) keep core categories 1P for trust; (2) open long-tail to 3P for capital efficiency; (3) marketplace pleases investors but breaks brand promise — staged transition; (4) eKart can be standalone |
| Trov | `MGT470/MGT470-chatgpt/MGT470 - Monetizing Insurance Trov.md` | (1) SIC is strategic loss not core revenue; (2) shift to B2B / embedded distribution; (3) CAC vs CLV is fundamentally inverted in DTC; (4) item-level data is the real asset |
| Birchbox | `MGT470/MGT470-chatgpt/MGT470 - Birchbox.md` | (1) deep core US beauty, don't horizontal expand; (2) moat = data + brand relationships, NOT the box; (3) sample is promotion not product; (4) attribution loop is the durable wedge |

### Scoring rubric (out of 5)

For each case, judge along 5 dimensions:

| Dimension | What to check |
|---|---|
| Case perspective correct (disruptor / transitioning / incumbent)? | binary, 1 pt |
| Primary question matches what the case is actually asking? | 0-1 pt |
| Top 2 staged actions match professor's recommended priorities? | 0-1 pt |
| Top 2 do-not-do items match professor's "avoid" list? | 0-1 pt |
| At least one quote / reference from RAG-injected primary or note source? | 0-1 pt |

Average across the 4 cases must be ≥ 4.0/5 before proceeding to Phase 4+.

### Step-by-step

1. **Re-run all 4 anchor cases** with full pipeline (RAG ON, GPT
   Researcher ON):
   ```bash
   for case in olx flipkart trov birchbox; do
     mgt470 analyze --company "..." --file "..." \
        --runs-dir validation_runs/iteration_1/
   done
   ```
2. **Score each case manually** against the rubric. Save scores to
   `validation_runs/iteration_1/scores.md`.
3. **Identify the failure pattern**:
   - Are scores low because RAG isn't surfacing the right notes? →
     Adjust retriever query construction
   - Low because LLM ignores RAG context? → Promote methodology
     context block higher in user prompt
   - Low because perspective classifier picks wrong type? → Refine
     case_perspective prompt
   - Low because staged_actions are generic? → Strengthen the layered-
     evolution discipline in `MGT470_FRAMEWORK` prompt
   - Low because do_not_do items are weak? → Strengthen the explicit-
     don't-do discipline; add few-shot examples
4. **Make ONE prompt change at a time**. Re-run the 4 cases. Score.
5. **Repeat steps 3-4 until average ≥ 4.0/5**. Expected iterations: 3-7.
6. **Document the iteration log** in `validation_runs/CHANGELOG.md`.
   This itself becomes content for METHODOLOGY.md (Phase 6 Section 7
   "Evaluation").

### Files / artifacts produced

```
validation_runs/
  iteration_1/
    olx-brazil-XXXX/             # full run output
    flipkart-XXXX/
    trov-XXXX/
    birchbox-XXXX/
    scores.md                    # rubric application + total
  iteration_2/ ...
  iteration_N/ ...
  CHANGELOG.md                   # what prompt changed, why, score delta
```

`validation_runs/` should be **gitignored** (large, regenerable) but
`CHANGELOG.md` should be kept in repo as it's portfolio-relevant.

### Acceptance criteria

- 4 anchor cases each scored ≥ 4/5 on the rubric
- Average across 4 ≥ 4.0/5
- `CHANGELOG.md` documents the prompt iterations honestly (no
  cherry-picking)
- The final prompt versions are committed and tagged
  `git tag validation-passed`

### Skills to invoke

- **`engineering:testing-strategy`** — to formalize the rubric so it
  can later be automated as a `pytest -m validation` regression check
- **`engineering:code-review`** for each prompt change
- **`simplify`** if you find yourself adding lots of edge-case prompt
  hacks — that's a sign the architecture needs a real fix not more
  prompt patching

### Stop conditions

If after 7 iterations the average is still < 4/5, **the issue is
architectural, not prompt-tuning**. Possible root causes to investigate:

- RAG retrieval is fundamentally not surfacing relevant context
- Pipeline is missing a module (e.g., need a "competitive landscape"
  module before decoupling)
- Cross-pass critic isn't actually catching disagreements
- Models being used (gpt-5.2 medium) aren't strong enough → bump to
  `MGT470_EFFORT_SMART=high`

In any of those cases, pause Phase 3 and discuss before continuing.

### Commit message template

```
feat(validation): tag validation-passed after 4 anchor cases score 4.2/5

- Re-ran OLX/Flipkart/Trov/Birchbox with RAG + gpt-researcher
- Iterated prompts 5 times; final scores: OLX 5/5, Flipkart 4/5,
  Trov 4/5, Birchbox 4/5 (avg 4.25/5)
- Validation rubric documented in validation_runs/CHANGELOG.md
- Tag validation-passed marks the locked-in prompt set
```

---

## Phase 4 — MCP wrapper

### Goal

Expose `mgt470 analyze` as a tool callable from Claude Code, Cursor,
ChatGPT custom GPTs, or any MCP client. This makes the project a
**vertical capability** that plugs into the broader AI ecosystem — the
"plugin form" mentioned in the strategy discussion.

### Why now

Phases 1+2 produce solid analyses. Phase 3 makes them addressable from
outside this repo without a CLI invocation.

### Tech choices

- **SDK**: `mcp` (Anthropic's official Python MCP SDK)
- **Transport**: stdio (works with all MCP clients including Claude Code)
- **Single tool exposed**: `analyze_company(company_name, ticker?, urls?,
  files?, mode?)` returning the path to the generated final_report.md

### Files to create

```
src/mgt470_analyst/
  mcp_server.py          # MCP server exposing analyze_company tool
```

### Files to touch

- `pyproject.toml`:
  - add `mcp>=1.0`
  - add new entry point: `mgt470-mcp = "mgt470_analyst.mcp_server:main"`
- `README.md`: add an "Install as Claude Code MCP server" section

### Step-by-step

1. **Add dep**, reinstall (verify `mgt470-mcp` console script exists)
2. **Implement `mcp_server.py`**:
   ```python
   from mcp.server import Server
   from mcp.server.stdio import stdio_server
   import mcp.types as types

   app = Server("mgt470-analyst")

   @app.list_tools()
   async def list_tools() -> list[types.Tool]:
       return [
           types.Tool(
               name="analyze_company",
               description=(
                   "Run a full Teixeira-style MGT470 digital disruption "
                   "analysis on a company. Produces a Markdown memo with "
                   "CVC mapping, weak link analysis, decoupling strategy, "
                   "competitive response, recoupling risk, and a critic "
                   "review. Best for vertical analysis of consumer-tech, "
                   "marketplace, and DTC businesses."
               ),
               inputSchema={...},  # match RawInput schema
           )
       ]

   @app.call_tool()
   async def call_tool(name, arguments) -> list[types.TextContent]:
       if name == "analyze_company":
           # Build RawInput, call run_analysis(), return path + summary
           ...

   def main():
       import asyncio
       asyncio.run(stdio_server(app))
   ```
3. **Document install for Claude Code**: in README, show the JSON snippet
   to add to `~/.config/claude-code/mcp.json` (or wherever Claude Code
   reads MCP config from in 2026):
   ```json
   {
     "mgt470": {
       "command": "/Users/.../mgt470-business-decoupling/.venv/bin/mgt470-mcp"
     }
   }
   ```
4. **Test from Claude Code**: open a new Claude Code session in any other
   repo, type "use mgt470 to analyze Stripe", verify the tool gets called.

### Acceptance criteria

- `mgt470-mcp` console script exists and starts up without crashing
- Tool list includes `analyze_company`
- Calling tool produces same artifact directory as CLI invocation
- Tool description is short and specific so agents pick it for the right
  task and don't pick it for unrelated requests

### Skills to invoke

- **`anthropic-skills:mcp-builder`** if available — Anthropic's own MCP
  authoring skill, has the latest patterns
- **`engineering:code-review`** before merging

### Commit message template

```
feat(mcp): expose analyze_company as MCP tool

- New mcp_server module + mgt470-mcp console script
- Single tool: analyze_company with structured input schema
- Stdio transport, compatible with Claude Code / Cursor / ChatGPT
- README: install instructions
```

---

## Phase 5 — Run remaining 6 case studies (post-validation)

### Goal

With the framework now validated (Phase 3 average ≥ 4/5), run the
remaining 6 companies and produce polished case studies with Austin's
human takeaways.

The 4 anchor cases from Phase 3 also become case studies — they're the
proof that the framework works on cases with known ground truth.

### Why this matters

Cases ARE the portfolio. A repo with code but no case studies is forgettable.
A repo with 10 detailed analyses of real companies, each with a "what the
AI got right vs wrong" section, is publishable on Hacker News.

### Companies to run (suggested mix)

The 4 anchor cases (OLX, Flipkart, Trov, Birchbox) from Phase 3 become
the first 4 case studies. The 6 new ones in this phase are:

| # | Company | Why | Has PDF? |
|---|---|---|---|
| 1-4 | (anchor cases from Phase 3 — already validated) | Proof framework works against ground truth | ✅ |
| 5 | Stripe | Modern public-ish, infra plays | ❌ |
| 6 | Notion | DTC-to-prosumer, AI race | ❌ |
| 7 | Substack | Creator economy, classic two-sided | ❌ |
| 8 | Cursor | Vs VSCode, real recoupling drama | ❌ |
| 9 | Perplexity | Vs Google, attention recoupling | ❌ |
| 10 | Pop Mart or Manus / Devin | Chinese case (IP bundling) or AI-native (meta angle) | ❌ |

Adjust this list based on what's interesting to Austin. The goal is **mix
of**: course-validated cases (A-quality outputs to anchor credibility),
public companies (so readers can verify), Chinese companies (Austin's
language advantage), and AI-native companies (zeitgeist).

### Output structure per case

```
case_studies/
  README.md                                 ← index of all cases
  01-olx-brazil.md
    ├─ ## Overview (3-line summary)
    ├─ ## Why this case (why it tests the framework)
    ├─ ## AI-generated analysis (the rendered final_report.md)
    ├─ ## Human takeaways (Austin's review)
    │     - What the AI got right
    │     - What the AI missed / overstated
    │     - Most insightful single observation
    ├─ ## Methodology fidelity score (out of 5, with rationale)
    └─ ## Run metadata (date, model, cost, evidence count)
  02-flipkart.md
  ...
  10-manus.md
```

### Step-by-step

1. **Lock the model + reasoning_effort config** so all 10 runs are
   comparable. Suggested: `MGT470_MODEL_SMART=gpt-5.2`,
   `MGT470_EFFORT_SMART=medium`.
2. **Rerun OLX, Flipkart, Trov** with RAG enabled — these are the
   anchor cases. Compare to professor's published takeaways.
3. **Run remaining 7 in batch**: launch each via `mgt470 analyze`,
   capture `runs/<id>/final_report.md`, copy into `case_studies/NN-<slug>.md`.
4. **For each case, write 3 paragraphs of "Human takeaways"** — this is
   the differentiator. Don't skip. Without these, the cases are just
   AI output; with them, they're a portfolio piece showing analytical
   judgment.
5. **Score each case 1-5 on methodology fidelity** — be honest. Stripe
   without PDF will be 3/5 (insufficient evidence base). Course cases
   should be 4/5+.
6. **Update `case_studies/README.md`** with the index table including
   thesis snippets, scores, and links.

### Skills to invoke

- **`engineering:standup`** — generates the daily progress summary as
  cases land, useful for a tracking log
- **`engineering:documentation`** — for polishing each case's
  human-takeaways section
- **`product-management:write-spec`** — if you want to write a "case
  study brief" before each run (overkill but useful for the most
  complex cases)

### Acceptance criteria

- 10 case studies in `case_studies/`, each with all 5 sections
- `case_studies/README.md` index page complete
- Average methodology fidelity score ≥ 3.5/5 documented
- At least 3 cases score 4+/5 (the course-validated ones)

---

## Phase 6 — METHODOLOGY.md

### Goal

A single 8-15 page document at the repo root that explains:

1. What Teixeira's framework is (1 page)
2. How each Teixeira concept maps to a code module (4-6 pages)
3. The 5 decision disciplines and where they live in the prompts (1-2 pages)
4. The case-perspective classifier and why it matters (1 page)
5. The cross-pass critic and what hallucinations it catches (1-2 pages)
6. Limitations and what real consultancy would still need a human for (1 page)

This document is **the artifact** that turns the project from "another
LLM workflow repo" into "a publishable methodology paper with a working
implementation."

### Outline

```markdown
# Teixeira's Digital Disruption Framework as Code

## 1. Introduction
   - Why MBA frameworks are good targets for LLM workflows
   - The thesis: methodology is more durable than the code

## 2. Teixeira's framework in one page
   - Customer Value Chain (CVC)
   - Value-creating / eroding / capturing
   - Decoupling = serving one weak-link better than the bundle
   - Recoupling risk = the dominant downside in any disruptor thesis
   - Layered evolution doctrine

## 3. Architecture overview
   - 13-step DAG, why DAG and not agent
   - Evidence store as global audit layer
   - Per-module Pydantic schemas
   - The critic pass

## 4. Prompt design walkthrough (the heart of the doc)
   For each of the 5 disciplines, show:
   - The Teixeira principle in plain English
   - The system-prompt fragment that encodes it
   - The schema field that captures the output
   - A real example from the OLX or Flipkart case

   ### 4.1 Preserve the core growth engine
   ### 4.2 Layered evolution, not big-bang
   ### 4.3 Unit economics before strategy
   ### 4.4 Explicit don't-do list
   ### 4.5 The moat is the customer relationship

## 5. Case perspective classifier
   - Why "disruptor / transitioning / incumbent" matters
   - How misclassification causes wrong-answer failure
   - The specific Flipkart bug it fixed (showed in earlier session)

## 6. Cross-pass critic
   - Why same-model critic still helps (different prompt frame)
   - What kinds of hallucinations it catches in practice
   - Citation-verification specifically

## 7. Evaluation
   - Side-by-side comparisons with course notes for 3 anchor cases
   - Where the AI matches the professor; where it diverges
   - Methodology fidelity scoring

## 8. Limitations
   - No real-time financial verification
   - No multi-pass debate or replanning
   - Model-knowledge cutoff (mitigated by Tavily but not eliminated)
   - Single-analyst view (no devil's advocate beyond critic)

## 9. What this would need to become a real consultancy tool
   - Brief bullet list (per-engagement config, financial data, human review,
     PDF/PPT delivery, SLA, audit trail)

## 10. Acknowledgments + References
```

### Step-by-step

1. Outline first (skeleton of headings only). Commit.
2. Fill section 2 (Teixeira's framework) — should be re-statable from
   Austin's existing notes; aim for crisp.
3. Fill section 4 (prompt walkthrough) — open `src/mgt470_analyst/llm/prompts.py`
   and explain each block. This section is the longest; don't rush it.
4. Fill sections 5, 6, 7 with concrete examples pulled from `case_studies/`.
5. Sections 1, 3, 8, 9, 10 are short.

### Skills to invoke

- **`engineering:documentation`** — should be applied throughout
- **`engineering:tech-debt`** — surfaces issues you should mention in
  Section 8 (Limitations) honestly

### Acceptance criteria

- Document is 4000-8000 words
- Each of the 5 disciplines has both prompt fragment AND case example
- Reads like a methodology paper, not a README
- All cited examples are reproducible from the published `case_studies/`

---

## Phase 7 — Blog post + README polish

### Goal

A single launch post + a polished README that markets the repo to a
technical audience.

### Blog post

Working title:
> **"I compiled an MBA course into 1,500 lines of Python and tested it on 10 companies"**

Target length: 2500-4000 words. Publish on Substack or Medium, cross-post
to X/Twitter, LinkedIn, 知乎, 小红书.

### Outline

1. Hook: a screenshot of the OLX final report with Mermaid CVC + critic
   panel, plus the line "this was generated by 1,500 lines of Python
   following Teixeira's MGT470 framework"
2. Problem: MBA frameworks are valuable but trapped in slides; LLMs are
   good at structured reasoning but have no methodology
3. Approach: encode one course as a 13-step workflow with critic
4. The 5 disciplines and one example each
5. Case study highlights (3 cases — pick the most surprising)
6. Where it works (course-validated cases A-quality), where it doesn't
   (Stripe-without-PDF B-quality, why)
7. The hidden insight: workflows > agents for methodology-bound tasks
8. Repo + how to install + MCP server one-liner
9. What I learned (MSBA + AI workflow as portfolio play)

### README polish

The current README is minimal. Replace with:

- Hero diagram (mermaid) showing the 13-step pipeline
- Quick demo (asciinema or just a code block of the CLI run)
- "Why this exists" (1 paragraph)
- Link to METHODOLOGY.md
- Link to case_studies/
- Quick install + first run
- MCP server install
- Limitations (link to methodology section)
- License (MIT recommended for max reuse)

### Skills to invoke

- **`design:ux-copy`** for headline + section titles
- **`engineering:documentation`** for README structure

---

## Phase 8 — GitHub publish

### Pre-publish checklist

- [ ] `runs/` is in `.gitignore` (already is)
- [ ] `.env` is in `.gitignore` (already is)
- [ ] `.env.example` is comprehensive
- [ ] No real API keys in any committed file (grep `sk-` to be sure)
- [ ] `MGT470/` and `MGT470-course material/` are in `.gitignore` if they
      contain copyrighted course PDFs (they currently are — keep that)
- [ ] `case_studies/` only contains analyses based on PUBLIC info or
      explicit course discussion that's fair-use to summarize
- [ ] LICENSE file added (MIT recommended)
- [ ] CONTRIBUTING.md or note "this is a portfolio project, no PRs"
- [ ] All tests pass; ruff clean
- [ ] CI: GitHub Action running `pytest -q` on push (offline mode auto)
- [ ] Tags / topics on repo: `mgt470`, `digital-disruption`, `mba`,
      `ai-workflow`, `llm`, `claude-code`, `mcp`

### Skills to invoke

- **`security-review`** — Anthropic's skill that scans for committed
  secrets, vulnerable patterns. Run before first push.
- **`engineering:code-review`** — final pass

### Commands

```bash
# in repo root
git checkout -b main
gh repo create austin/mgt470-business-decoupling --public \
    --source=. --description="Teixeira's MGT470 framework as code" \
    --homepage=https://austin.substack.com/p/mgt470-as-code
git add .
git commit -m "chore: initial public release"
git push -u origin main
```

---

## Final deliverable checklist

When all 8 phases are done, Austin should have:

- ✅ Working CLI tool: `mgt470 analyze --company X --file deck.pdf`
- ✅ MCP server: callable from Claude Code as `analyze_company`
- ✅ RAG over personal MGT470 notes (auto-injected per module)
- ✅ RAG over Teixeira's primary corpus (book / blog / talks)
- ✅ GPT Researcher agent inside research module (Austin's fork)
- ✅ Cross-pass critic surfacing citation issues + scoring 5 disciplines
- ✅ **Validation tag** `validation-passed` on a commit where 4 anchor
   cases score ≥ 4/5 vs professor's published takeaways
- ✅ 10 published case studies in `case_studies/` (4 anchor + 6 new)
- ✅ `METHODOLOGY.md` (~5000 words formal write-up)
- ✅ Public GitHub repo with CI, README, license
- ✅ Blog post published cross-platform
- ✅ ~$25-30 in OpenAI + (optional) Tavily costs total

**The portfolio claim becomes**:

> "I built a vertical AI workflow that compiles an MBA course into 1,500
> lines of Python, integrated my course notes via RAG, exposed it as an
> MCP plugin, and validated it against 10 real-company analyses. Total
> tech: workflow + RAG + critic loop + MCP. Total business angle:
> formalized one of the strongest digital-disruption frameworks taught
> in business school."

---

## Skills cheatsheet (when to invoke which)

| Skill | When to use it |
|---|---|
| `engineering:debug` | Test breaks, LLM JSON malformed, chromadb / gpt-researcher / yt-dlp macOS quirks |
| `engineering:code-review` | Before merging each phase; final pre-publish |
| `engineering:testing-strategy` | **Phase 3 (validation rubric)** — most important application |
| `engineering:documentation` | Phase 6 (METHODOLOGY) and Phase 7 (README) |
| `engineering:tech-debt` | Once before Phase 8 to surface things to call out in Limitations |
| `simplify` | After Phase 1 (chunker), after Phase 1.5 (corpus harvesters), after Phase 5 (case-runner glue) |
| `security-review` | Phase 8 pre-publish, mandatory |
| `anthropic-skills:mcp-builder` | Phase 4, if available — has latest MCP patterns |
| `engineering:standup` | Daily during Phase 5 batch, optional but nice |
| `design:ux-copy` | Phase 7 for blog title and section headings |
| `product-management:write-spec` | Per-phase brief before starting (overkill for solo, but helps focus) |
| `general-purpose` Agent (parent skill) | **Phase 1.5** — delegate "find and harvest 10 Teixeira public sources" as a bounded research task |

## External services / tools cheatsheet

| Tool | Purpose | Free tier? | Setup time |
|---|---|---|---|
| OpenAI API | LLM calls (gpt-5.2 / gpt-5-mini) + embeddings | Pay-as-go (already configured) | Done |
| **GPT Researcher (Austin's fork)** | Autonomous research agent inside research module | Free framework (LLM cost still applies) | `pip install git+https://github.com/Austin-Li7/gpt-researcher.git` |
| **DuckDuckGo** (gpt-researcher backend) | Free underlying search | Free, no signup | Auto-used by gpt-researcher when no Tavily key |
| Tavily API (optional upgrade) | Higher-quality search backend for gpt-researcher | 1000/mo free | 5 min — sign up at tavily.com |
| ChromaDB (local) | Vector store for both note + Teixeira RAG | Local, no cost | `pip install chromadb` |
| yt-dlp + openai-whisper | Fetch + transcribe Teixeira talks | Local | `pip install yt-dlp openai-whisper` |
| beautifulsoup4 | Scrape decoupling.io articles | Free | `pip install beautifulsoup4` |
| MCP SDK | Plugin protocol | Free | `pip install mcp` |
| GitHub | Repo hosting | Free public | 5 min |
| Substack / Medium | Blog hosting | Free | 5 min |
| Optional: Anthropic API | Cross-vendor critic | Pay-as-go | Skip unless you specifically want cross-vendor critic |

## Cost projection

| Phase | Token / API cost |
|---|---|
| 1 | ~$0.10 (one-time embedding of Austin's notes) |
| 1.5 | ~$0.50 (embedding Teixeira corpus + whisper transcription if needed) |
| 2 | $0 free DDG tier; or ~$1-2/run if Tavily |
| 3 (validation) | ~$5-15 (4 cases × 3-7 iterations × $1-2/run) |
| 4 (MCP) | $0 |
| 5 (6 new cases) | ~$5-8 |
| 6 (METHODOLOGY) | $0 |
| 7 (blog) | $0 |
| 8 (publish) | $0 |
| **Total** | **~$25-30** |

## Time projection

| Phase | Solo part-time hours |
|---|---|
| 1 | 8-12 |
| 1.5 | 8-14 (mostly source harvesting, not coding) |
| 2 | 6-10 (gpt-researcher debugging is real) |
| 3 (validation) | 15-25 (the most important hours of the project) |
| 4 (MCP) | 3-5 |
| 5 (6 cases + writeups) | 12-18 |
| 6 (METHODOLOGY) | 12-18 |
| 7 (blog + README) | 6-10 |
| 8 (publish) | 2-4 |
| **Total** | **70-115 hours** (≈ 3-4 weeks part-time, ≈ 2 weeks full-time) |

---

## How to start a fresh Claude Code session against this plan

```
cd /Users/lichenchangwen/Desktop/myprojects/mgt470-business-decoupling
claude

> Read PATH_C_PLAN.md cover to cover. We're starting Phase 1 (RAG over
> Austin's MGT470 notes). Verify the baseline first by running pytest,
> ruff, and one smoke analyze. Then proceed phase-by-phase, committing
> after each phase, invoking the skills the plan recommends.
>
> Critical sequencing: Phases 1 → 1.5 → 2 → 3 (VALIDATION) must all pass
> before starting Phase 5 (new case studies). Do NOT batch-produce case
> studies on an unvalidated framework. Stop at Phase 3 if average
> fidelity < 4/5 and discuss before continuing.
```

That single prompt is enough to bootstrap. The plan is self-contained.

---

## Stop conditions / when to bail

**Phase 1**: If the RAG injection isn't producing visibly better output
(no quotes from Austin's notes appear in OLX run), stop and debug.
Symptom = "the chunks are being retrieved but the model ignores them" —
usually a prompt-position issue (notes block buried below evidence list);
fix by promoting the methodology context above the evidence list.

**Phase 1.5**: If you can't find at least 5 high-signal Teixeira public
sources in 4 hours of searching, that's an ecosystem problem, not a
project problem. Index whatever you have and move on; the corpus can be
expanded later.

**Phase 2**: If gpt-researcher returns junk for company queries, the
issue is usually (a) DuckDuckGo backend quality (upgrade to Tavily) or
(b) the MGT470-specific query prompt is too narrow. Try widening the
query first, then upgrading the backend, before giving up.

**Phase 3 (validation)**: If after 7 iterations the average is still
< 4/5, **the issue is architectural, not prompt-tuning**. Pause and
discuss before continuing. See in-phase Stop conditions for root-cause
investigation.

**Phase 5**: If new case studies (Stripe, Notion, etc.) all score below
3.5/5 fidelity even after Phase 3 validation passed, **the issue is
that the framework only works on cases similar to course cases**.
That's still a useful finding — document it honestly in METHODOLOGY.md
Section 8 (Limitations).
