# Case Studies

Path-C grounded case count: **0/10**.

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
DuckDuckGo, and refuse to write reports when retrieval returns 0 visited URLs.
Future archived cases must include `research_provenance.json` so retrieval
health can be audited before any run counts toward the 10-case target.
