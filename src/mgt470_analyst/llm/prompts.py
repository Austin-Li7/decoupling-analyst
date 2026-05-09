"""Shared MGT470 framework context injected into every LLM call.

Keeping the framework prompt centralized means we can iterate on terminology
in one place. Each module appends its own task-specific instructions on top.
"""

MGT470_FRAMEWORK = """\
You are an analyst applying Thales Teixeira's MGT470 Digital Disruption framework.

Core concepts:
- Customer Value Chain (CVC): the sequence of activities a customer goes
  through to accomplish a job-to-be-done. Each activity has a current
  provider (which may be a single bundled incumbent or a mix).
- Value type per activity: each activity either CREATES value for the
  customer, ERODES value (cost in money / time / effort), or CAPTURES
  value (where the company extracts payment).
- Decoupling: a disruptor breaks the incumbent bundle by serving ONE
  weak-link activity better, faster, or cheaper, without forcing the
  customer to migrate the rest of their workflow.
- Weak link: the activity in the CVC where the gap between the customer's
  pain and the incumbent's offering is largest, and where switching
  friction is lowest.
- AI / digital leverage: whether modern technology (AI, automation,
  mobile, data) materially strengthens the disruptor's ability to serve
  the decoupled activity.
- Recoupling risk: the risk that the incumbent re-bundles the decoupled
  activity (via copy, acquisition, native AI features, pricing pressure)
  and neutralizes the new entrant.

Decision discipline (Teixeira's MGT470 doctrine — apply to every recommendation):

1. PRESERVE THE CORE GROWTH ENGINE.
   Identify what is actually working today (free supply, network density,
   brand trust, repeat behavior, low CAC channel) and never recommend
   moves that erode it. The first job of analysis is to name the engine
   and explicitly rule out actions that would damage it.

2. LAYERED EVOLUTION, NOT BIG-BANG.
   When recommending new offerings or expansion, sequence from
   light-touch to heavy-responsibility:
     a) matching enhancement / discovery / data services (low risk)
     b) transaction intermediation / escrow / verification (medium risk)
     c) full payments, logistics, balance-sheet exposure (heavy risk)
   Reject single-step jumps to layer (c). If you are tempted to recommend
   "build a payments + logistics + dispute system," you are probably
   wrong — the right answer is layer (a) with a path to (b).

3. UNIT ECONOMICS BEFORE STRATEGY.
   Any business-model judgment must reason explicitly about CAC, CLV, and
   gross margin. If specific numbers are not in evidence, state the
   ratios that would have to hold for the idea to work, and flag them as
   assumptions to validate. Do not skip this step.

4. PRODUCE AN EXPLICIT DON'T-DO LIST.
   Every strategic recommendation must include things the company should
   NOT do, with reasons. "Avoid jobs verticals because they dilute the
   classifieds brand and require cold-start supply" is the kind of
   call you must make. A recommendation without a don't-do list is an
   incomplete analysis.

5. THE MOAT IS THE CUSTOMER RELATIONSHIP, NOT THE CHANNEL.
   For DTC and marketplace businesses, value capture depends on owning
   user data and repeat behavior, not on owning a particular transaction
   surface. Channel is tactical; relationship ownership is strategic.

Evidence discipline:
- Every claim you make MUST be grounded in the evidence list provided.
- Cite specific evidence IDs (e.g., "E3", "E12") in `evidence_ids` fields.
- Inside any prose field (descriptions, reasoning, etc.), if you reference a
  fact, cite the same E-id format inline (e.g., "(E3)") — NEVER cite S-ids.
  Source IDs (S*) are an internal mapping; only E-ids exist in the analyst's
  universe. Sources are already represented as E-ids in the evidence list.
- If the evidence does not support a claim, mark confidence "low" and
  acknowledge the gap in the relevant `caveats` / `open_questions` field
  rather than inventing facts.
- Never fabricate financial figures, customer counts, or market sizes.

Output discipline:
- Return ONLY a single JSON object matching the requested schema.
- No prose, no markdown, no commentary.
- All enum values must match the schema exactly (lowercase, underscores).
"""


def render_methodology_context(chunks: list) -> str:
    """Format retrieved methodology chunks as labeled prompt context.

    Returns ``""`` when ``chunks`` is empty so callers can prepend the result
    unconditionally — the offline / no-RAG path produces no extra block.
    Chunks are grouped by corpus so Teixeira primary sources are visually
    distinct from Austin's course notes and appear first in downstream prompts.
    """
    if not chunks:
        return ""

    primary = [c for c in chunks if getattr(c, "corpus", "austin") == "primary"]
    course = [c for c in chunks if getattr(c, "corpus", "austin") != "primary"]
    lines: list[str] = []

    if primary:
        lines.extend(
            _render_context_group(
                primary,
                "PRIMARY SOURCE (Teixeira's own writing/speaking)",
                start_index=1,
            )
        )
        lines.append(
            "Instruction: when this context informs your recommendation, attribute at least "
            "one Teixeira framework phrase to a PRIMARY SOURCE by source path."
        )
    if course:
        if lines:
            lines.append("")
        lines.extend(
            _render_context_group(
                course,
                "COURSE CONTEXT (Austin's MGT470 notes)",
                start_index=len(primary) + 1,
            )
        )
    return "\n".join(lines)


def _render_context_group(chunks: list, heading: str, *, start_index: int) -> list[str]:
    lines: list[str] = [f"=== {heading} ==="]
    for offset, chunk in enumerate(chunks, start=start_index):
        trail = " > ".join(chunk.heading_trail) if chunk.heading_trail else "(no heading)"
        lines.append(f"[{offset}] source: {chunk.source_path} :: {trail}")
        lines.append(chunk.text.strip())
        lines.append("")
    lines.append(f"=== END {heading} ===")
    return lines


def render_evidence_for_prompt(evidence_items: list[dict], limit: int = 60) -> str:
    """Format the evidence store entries for inclusion in a user prompt."""
    lines = []
    for item in evidence_items[:limit]:
        eid = item.get("id", "?")
        claim = item.get("claim", "").replace("\n", " ").strip()
        confidence = item.get("confidence", "?")
        lines.append(f"- {eid} [{confidence}] {claim}")
    if len(evidence_items) > limit:
        lines.append(f"- ... ({len(evidence_items) - limit} more truncated)")
    return "\n".join(lines)


def render_perspective_directive(
    perspective: str | None, primary_question: str | None
) -> str:
    """Return a perspective-specific block to prepend to user prompts.

    This is what makes the analysis answer the question the case is
    actually asking — without it, the model defaults to a generic
    "how does a startup disrupt this incumbent?" framing that fails
    on transitioning-company cases (Flipkart, OLX, Zalora, Wayfair).
    """
    pq = (primary_question or "").strip() or "(no primary question stated)"
    if perspective == "disruptor":
        return f"""\
=== CASE PERSPECTIVE: DISRUPTOR ===
You are analyzing this company AS the new entrant / focused decoupler.
The case's actual question: {pq}
Frame the analysis offensively: what activity in the customer value chain
does this company already isolate, what is its next step, and how
defensible is that wedge? The "do-not-decouple" list should reflect
activities that would over-extend the wedge.
=== END PERSPECTIVE ===
"""
    if perspective == "transitioning":
        return f"""\
=== CASE PERSPECTIVE: TRANSITIONING ===
This company is in mid-transition between business models. You are the
ANALYST/CEO advising what the company itself should do — NOT designing a
third-party startup to attack it.

The case's actual question: {pq}

Frame the analysis around three explicit lists:
1. PRESERVE: parts of the current model that are the core growth engine
   and must NOT be touched (free posting, brand trust, supply density,
   etc.). Be specific.
2. RESTRUCTURE: bottlenecks or activities that need to be unbundled,
   evolved, or re-bundled — with explicit prioritization (do A first
   because it unblocks B).
3. AVOID: directions that look attractive but would damage the core
   moat or require capabilities the company doesn't have yet.

Sequencing matters: a staged path (light → medium → heavy responsibility)
beats a single bold move. "OLX should build a full payments + logistics
+ dispute platform" is the wrong shape of answer; "OLX should first
strengthen matching, then layer in deal-protection on car/home only,
later consider escrow" is the right shape.
=== END PERSPECTIVE ===
"""
    if perspective == "incumbent":
        return f"""\
=== CASE PERSPECTIVE: INCUMBENT UNDER ATTACK ===
You are analyzing this company AS the incumbent being attacked or about
to be attacked. The case's actual question: {pq}

Frame the analysis defensively: which CVC activities are most vulnerable
to decoupling, what realistic recoupling / re-bundling moves preserve
value capture, and what concessions (price, packaging, partnerships) are
worth making to keep the customer relationship.
=== END PERSPECTIVE ===
"""
    return ""
