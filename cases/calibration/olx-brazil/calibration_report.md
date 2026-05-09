# OLX Brazil Calibration Report

**Run ID:** olx-brazil-20260509-034428
**Ground truth sources:** `MGT470-course material/DD Course (UCSD Winter 2026) Session 9.pdf`; `MGT470-course material/WI26MGT470-999016DigitalDisruptionTeixeira-PT_1089720730181398/WhereToGrowNextAtOnlineMarketplaceOLX.pdf`
**Calibrator:** Codex (mechanical comparison; human reviewer to verify)

## Side-by-side comparison

| Field | Teixeira's ground truth | System output | Match? | Notes |
|---|---|---|---|---|
| CVC step count | 6 supported marketplace steps | 6 | ✅ | Session 9 does not expose a labeled OLX CVC, but the system count matches the case-supported marketplace chain. |
| Weak link identified | The uncaptured adjacent transaction layer: financing, trust, escrow, payments, insurance, and related services | Arrange payment method and manage trust/safety risk | ✅ | Strong match to the adjacent-services opportunity. |
| Decoupling pattern | Growth by coupling after a decoupled classifieds beachhead | Further decoupling of trust/payment via "OLX Deal Protection" | ⚠️ | The activity is relevant, but the theory label is off. Session 9 is explicitly about coupling adjacent links. |
| Decoupled activity | Historically: classifieds matchmaking from offline classifieds; next move: couple adjacent transaction services | Trust/payment arrangement | ⚠️ | The system identifies a valid adjacent link but treats it as a fresh decoupling target rather than coupling. |
| Strategic takeaway | Prioritize, leverage strengths, protect the core, and use coupling to create customer-side synergies | Preserve classifieds matching engine and add trust/payment protection in sequence | ✅ | Good practical match, though less explicit about "not too many fronts." |
| Final case perspective (disruptor/incumbent/pivot) | Growth/transition after a beachhead; defend core while expanding | transitioning | ✅ | Direct match. |
| Lens fit | Coupling/growth-after-decoupling is the explicit Session 9 lens | decoupling, fit score 0.85, medium confidence | ❌ | The system lacks a coupling lens, so it overuses decoupling. |

## Score
- Matches: 4/7 fields
- Partial: 2/7 fields (semantic adjacent)
- Misses: 1/7 fields
- Fabrications detected: 1 (system claims that contradict Teixeira's published view)

## Where the system diverged from Teixeira

The decoupling-pattern row is partial. The system chooses a relevant transaction-adjacent move, but labels it as decoupling. Teixeira's Session 9 explicitly teaches "Growth by Coupling": after stealing one activity, add adjacent links to create customer-side synergies. The system claim is produced by `decoupling_strategy`. The likely cause is framework coverage: the pipeline has a strong decoupling module but no first-class coupling/growth-after-beachhead module.

The decoupled-activity row is partial for the same reason. "Trust/payment arrangement" is in the right neighborhood, but Teixeira frames it as coupling adjacent services to OLX's existing marketplace, not as peeling another activity away from an incumbent. The system's `weak_link_analysis` is practically useful but theory-misaligned.

The lens-fit row is a miss. The system reports primary lens `decoupling`, while the lecture's main tool is coupling adjacent activities after a beachhead. This is a framework-encoding gap, not a retrieval failure: the Session 9 materials clearly contain the coupling recipe and summary points.

Fabrication note: the system describes a specific "OLX Deal Protection" flow and current-market details as if they are the recommended next wedge. That is a plausible product concept, but it should have been labeled as a system proposal built from Teixeira's coupling logic, not as Teixeira's own published analysis.

## Confidence in this calibration

MEDIUM. The Session 9 slides clearly state the coupling lesson, but they do not provide a fully labeled OLX-specific CVC in extractable text. The OLX HBS case supplies the strategic options and adjacent-services opportunity, so the high-level comparison is reliable even if some CVC row details are inferred from the case narrative.
