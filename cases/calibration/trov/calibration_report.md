# Trov Calibration Report

**Run ID:** trov-20260509-033633
**Ground truth sources:** `MGT470-course material/DD Course (UCSD Winter 2026) Session 4.pdf`; `MGT470-course material/WI26MGT470-999016DigitalDisruptionTeixeira-PT_1089720730181398/MonetizingInsuranceAtTrov.pdf`
**Calibrator:** Codex (mechanical comparison; human reviewer to verify)

## Side-by-side comparison

| Field | Teixeira's ground truth | System output | Match? | Notes |
|---|---|---|---|---|
| CVC step count | 6 | 6 | ✅ | System count matches Exhibit 2, though labels are more modern/embedded-insurance oriented. |
| Weak link identified | Continuous/inflexible insurance coverage and payment, plus bureaucracy and lack of flexibility | Research and compare insurance options | ❌ | The system moved upstream to comparison instead of Trov's original on-demand coverage/payment wedge. |
| Decoupling pattern | Value-charging decoupling: pay only for the protection used; with some value-eroding friction reduction | Embedded "Coverage Explainer + Comparator" decoupling | ❌ | Wrong primary pattern and wrong activity. |
| Decoupled activity | Activate/pay for single-item coverage only when needed | Research and compare insurance options | ❌ | The system missed the single-item coverage activity that anchors the HBS case. |
| Strategic takeaway | Decoupling can create customer value but not guarantee a profitable business model; decide what to do with SIC | Preserve embedded-insurance capability and add a comparator SDK; later add transaction/claims tooling | ⚠️ | The system recognizes the pivot/partner logic but does not center the CAC/contribution-margin problem or SIC decision. |
| Final case perspective (disruptor/incumbent/pivot) | Transition/pivot case from DTC SIC toward partnerships/B2B products | transitioning | ✅ | Good high-level framing. |
| Lens fit | Decoupling, with business-model sustainability as the test | decoupling, fit score 0.90, medium confidence | ✅ | The lens is right, but the weak-link implementation is wrong. |

## Score
- Matches: 3/7 fields
- Partial: 1/7 fields (semantic adjacent)
- Misses: 3/7 fields
- Fabrications detected: 1 (system claims that contradict Teixeira's published view)

## Where the system diverged from Teixeira

The weak-link row is a miss. The system says the best weak link is researching and comparing insurance options. Teixeira's case anchors Trov in single-item coverage: customers can activate protection for a specific item and duration, paying only for the protection used. The system claim is produced by `weak_link_analysis`, then amplified by `decoupling_strategy`. The likely cause is prompt/framework drift toward generic insurance UX pain points rather than Teixeira's value-charging lens.

The decoupling-pattern row is a miss. Teixeira's Session 4 teaches three decoupling types and uses Trov to show that decoupling can fail economically; the relevant type is value-charging decoupling around payment/coverage. The system instead invents an embedded comparator SDK as the wedge. That is a plausible Phase 2026 product idea, but it is not Teixeira's published Trov analysis. The likely cause is retrieval/current-company bias and insufficient anchoring to the HBS case CVC.

The decoupled-activity row is a miss. The system's `decoupling_strategy` chooses "Research and compare insurance options"; Teixeira's activity is closer to "sign/pay/manage coverage only for the item/time needed." This divergence likely comes from the `weak_link_analysis` scoring function preferring high-friction information search over the value-capture/payment step.

The strategic-takeaway row is only partial. The system correctly sees Trov as a transitioning company, but it does not foreground the core case question: what should Trov do with single-item coverage given CAC, contribution margin, and lack of a clear alternative revenue source? The claim is produced by `final_judgment`. This suggests the final module needs stronger instructions to preserve case-level economic dilemmas when the CVC module drifts.

Fabrication note: the run's report cites a 2026-style continuing Trov platform story, but the Teixeira/HBS ground truth is a 2017-2019 SIC profitability dilemma. Some current-company assertions may be true or false externally, but for this calibration they function as noise because they displace the published framework logic.

## Confidence in this calibration

HIGH. The CVC exhibit and Session 4 summary make the Trov lesson explicit: decoupling is powerful, but by itself does not guarantee a profitable business model.
