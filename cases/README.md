# Case Studies

Cases completed toward 10-case target: 3 / 10

## Grounded baselines (path-C cases 1–3)

| Company | Sector | Run date | Sources kept | Most surprising finding (1 line) | Confidence (1-5) | Total cost (USD) | Link to folder |
|---|---|---:|---:|---|---:|---:|---|
| Notion | US B2B/prosumer SaaS | 2026-05-09 | 11/13 | Grounded baseline kept 11 Tavily-retrieved sources; human review still pending. | _ | $0.46 | [_archive/notion-grounded-20260509/](_archive/notion-grounded-20260509/) |
| Liquid Death | US consumer brand | 2026-05-09 | 13/14 | Grounded baseline kept 13 retrieved sources for a consumer-brand case; human review still pending. | _ | $0.38 | [_archive/liquid-death-grounded-20260509/](_archive/liquid-death-grounded-20260509/) |
| Nubank | Brazilian fintech | 2026-05-09 | 9/11 | Grounded baseline kept 9 retrieved sources in a non-US fintech case; human review still pending. | _ | $0.42 | [_archive/nubank-grounded-20260509/](_archive/nubank-grounded-20260509/) |

## v0 — ungrounded baselines (do not count toward path-C 10-case target)

| Company | Sector | Run date | Sources kept | Most surprising finding (1 line) | Confidence (1-5) | Link to folder |
|---|---|---:|---:|---|---:|---|
| ⚠️ Notion (ungrounded v0) | US B2B/prosumer SaaS | 2026-05-08 | 8/11 | Invalid baseline: retriever returned 0 visited URLs; citations were not grounded evidence. | _ | [_archive/notion-20260508/](_archive/notion-20260508/) |
| ⚠️ Liquid Death (ungrounded v0) | US consumer brand | 2026-05-08 | 7/18 | Invalid baseline: retriever returned 0 visited URLs; citations were not grounded evidence. | _ | [_archive/liquid-death-20260508/](_archive/liquid-death-20260508/) |
| ⚠️ Nubank (ungrounded v0) | Brazilian fintech | 2026-05-08 | 2/10 | Invalid baseline: retriever returned 0 visited URLs; citations were not grounded evidence. | _ | [_archive/nubank-20260508/](_archive/nubank-20260508/) |

## Post-mortem: ungrounded v0 baselines

The first three baseline case studies are retained as failure artifacts, not
counted cases. The symptom was a wildly low URL liveness pass rate, followed by
provenance diagnostics showing GPT Researcher's `visited_urls` was empty. The
root cause was the DuckDuckGo retriever returning 0 URLs across sub-queries in
this environment, while the report writer still produced citation-shaped URLs
from model priors. The fix is to make Tavily the default retriever whenever
`TAVILY_API_KEY` is set, require an explicit ungrounded escape hatch for
DuckDuckGo, and refuse to write reports when retrieval returns 0 grounded
research sources.
Future archived cases must include `research_provenance.json` so retrieval
health can be audited before any run counts toward the 10-case target.
Resolved in Phase 3 step 4.3 (commit 14aae6e); first grounded baselines archived
in cases 1–3 above.
