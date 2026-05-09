# Calibration Against Teixeira-Taught Cases

These calibration runs compare the system's current grounded pipeline against Teixeira's own published course/book analysis for three MGT470 cases. The comparison is mechanical: Codex extracted ground truth from the local course PDFs/book chapter, ran the system, and scored seven fields per case. A human reviewer should still verify the judgments.

## Aggregate Score Table

| Company | Exact matches | Partial matches | Misses | Fabrications detected | Calibration confidence | Headline |
|---|---:|---:|---:|---:|---|---|
| Birchbox | 5/7 | 2/7 | 0/7 | 0 | HIGH | Strong reproduction of Teixeira's testing/evaluation decoupling logic. |
| Trov | 3/7 | 1/7 | 3/7 | 1 | HIGH | Correct high-level lens, but wrong weak link and decoupled activity. |
| OLX Brazil | 4/7 | 2/7 | 1/7 | 1 | MEDIUM | Finds the right adjacent transaction layer, but mislabels coupling as decoupling. |
| **Total** | **12/21** | **5/21** | **4/21** | **2** | - | **57% exact match; 81% exact-or-partial match.** |

## Recurring Failure Modes

1. **Weak-link selection can drift toward generic operational pain.** Trov is the clearest miss: the system selected insurance comparison/research instead of Teixeira's value-charging single-item coverage wedge.
2. **The pipeline overuses decoupling when the lecture topic is coupling.** OLX Session 9 is about growth by coupling after an initial beachhead, but the system has no first-class coupling lens and forces the case back into decoupling.
3. **Current-company retrieval can overpower historical case logic.** Trov and OLX runs include plausible current-era moves that are useful business analysis but distract from the taught case dilemma.
4. **Value-type taxonomy is not always surfaced.** Birchbox is substantively right, but the output does not always name value-creating/value-eroding/value-charging explicitly.
5. **Report-only citation drift still matters for calibration.** Trov and OLX both had `report_only_url_ratio=1.00`; even though brief sources come from `research_sources`, the written report still invents or rewrites citations.

## Prioritized Phase 4 Fixes

1. Add a first-class **coupling / growth-after-beachhead** lens so OLX-style cases are not flattened into decoupling.
2. Require `weak_link_analysis` and `decoupling_strategy` to state the Teixeira value type explicitly: value-creating, value-eroding, or value-charging.
3. Add a "historical case mode" that privileges supplied course/case materials over live current-company retrieval when the analysis is a calibration or classroom case.
4. Add calibration examples to module prompts: Birchbox as correct value-creating decoupling, Trov as value-charging decoupling with weak unit economics, OLX as coupling after a beachhead.
5. Track report-citation provenance in final reports, not only `research_provenance.json`, so reviewers can see when report prose cites URLs that were not actually retrieved.
