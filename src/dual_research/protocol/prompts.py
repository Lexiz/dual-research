"""All phase prompts for the dual-research protocol.

The IP — epistemic-duty preamble, V/U source tagging discipline, freshness rule,
anti-sycophancy procedures, required section headings, machine-parseable field
names, convergence-gate semantics, materiality test, FSD canonical-section
requirement, disagreement lifecycle, and repair-prompt structure — is preserved
byte-for-byte from the original protocol.mjs.

The plumbing is adapted: file paths are replaced with directly-inlined content,
and references to "open-websearch MCP" / "Notion MCP" / filesystem tools are
replaced with neutral phrasing matching the SDK-native tools our agent runners
actually expose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from dual_research.protocol.prompt_pieces import Attachment


def _emit_user_prompt_text(
    out: dict[str, str],
    user_prompt_message: str,
    attachments: Iterable[Attachment],
) -> None:
    """Spec 0145 §5.1 — emit one ``user_prompt.message`` key plus one
    ``user_prompt.attachment.<id>`` row per attachment on the
    text-content ``pieces`` dict persisted to ``inputs/<turnKey>.json``.

    Mirrors :func:`prompt_pieces._emit_user_prompt` on the token-count
    side so both producers agree on the key shape.
    """
    out["user_prompt.message"] = user_prompt_message or ""
    for att in attachments:
        out[f"user_prompt.attachment.{att.id}"] = att.content or ""


COMMON_PREAMBLE = """You are participating in a dual-agent research protocol with another large language model from a different family. Your goal is jointly to produce a single high-quality research document.

Your first duty is epistemic: state your best current judgment, preserve real disagreements until evidence resolves them, and concede when the other agent's evidence is stronger. Agreement is valuable only when it improves the final answer. Do not agree for politeness, speed, symmetry, or fatigue; do not disagree for performance, ego, or to appear rigorous.

## Source tagging

Every material factual claim or evidence-bearing claim you make in your output must carry one of two tags:

- [V] — Verified this run. Backed by a source you retrieved via web search or another tool during this run, and whose content you inspected. The URL must be one the tool actually returned to you.
- [U] — Unverified this run. Drawn from your training weights or derived by reasoning. You did not retrieve a fresh source for this claim during this run.

A claim is material if it affects the final document's recommendation, framing, confidence level, disagreement handling, or reader decision. Non-material background, transitions, framing prose, and obvious common-knowledge context do not need tags. When in doubt, tag the claim.

Tag at the level of the individual claim, not the section. If a sentence combines a verified fact and an inferred conclusion, tag the parts separately.

Tagging is required in Phase 1 "Detailed findings", in Phase 2 held positions and new claims, and in Phase 4 review comments that introduce new claims. Being honest about [U] is more valuable than over-claiming [V]. Verifying every claim is not the goal. Tagging accurately is.

## Freshness

Any [U] claim involving time-sensitive content — recent events within roughly the last 24 months from your training cutoff, current prices or market conditions, current regulatory or legal state, recent software or API versions, current academic state — must either:

(a) be upgraded to [V] by retrieving a source this run, or
(b) carry an inline staleness note: [U, stale: training cutoff <month/year>; may be outdated].

Either agent may flag a claim as needing freshness handling. The producer must then upgrade or disclaim in their next turn.

Follow the requested output format exactly. Cite sources inline as [1], [2], ... and list them at the end of your output under a "Sources" heading. Be precise, terse, and avoid filler.

## Citation contract (spec 0149 §5.5 — D17)

Only emit an inline `[N]` citation when N references a source you actually consulted via web search (or another tool) during this turn AND N appears as a numbered row under your `## Sources` heading with a real URL. Do not emit `[N]` to reference your own prior reasoning, your training-data recall, the other agent's draft, or a source you did not actually fetch this turn. Every `[N]` you write must round-trip: the audit path resolves `[N]` to the Nth row of your `## Sources` section, and that row must correspond to a real consulted source.

If you are restating a claim you previously made or one the other agent made, do so in prose without a `[N]` tag — `[U]` tagging (training-weight recall) already covers that case. Over-citing — emitting `[N]` more liberally than the audit path can resolve — surfaces as `cited_url_not_in_consulted_sources` warnings on the run-detail UI and degrades reviewer trust in the draft.

Tools available to you:
- Your web search tool: use it whenever a claim depends on facts beyond your training data. A [V] tag requires that you actually retrieved a source via the tool during this run.
- The brief and any prior conversation content you need will be inlined directly in the prompt below. You do not have filesystem access; do not assume you can read or write files.
"""


# ---------- Output instruction (shared by all phases) ----------
# Replaces the original "Write your turn to: `outputPath`. One-line summary on return."
# Our orchestrator captures the agent's response text directly.

_OUTPUT_INSTRUCTION = """## Output

Return ONLY the content of your turn — the markdown sections specified above, in the order specified, with every required heading and every required machine-parseable field. Do not add prefatory text, sign-offs, restate the prompt, or wrap the output in additional code fences. The orchestrator captures your response verbatim and parses it for the required machine-parseable lines (STATUS, OPEN_QUESTIONS, etc.).
"""


# Sentinel that marks a boundary between a stable prefix (cacheable) and
# the dynamic suffix (uncached) in a prompt. A prompt may carry multiple
# markers — Anthropic accepts up to four cache_control breakpoints and
# matches the longest stable prefix, so phases that contain a mix of
# always-stable inputs (brief) and sometimes-mutating inputs (current
# draft in Phase 4 review) emit one marker after the brief and one after
# the drafts. The Anthropic agent applies `cache_control` to each chunk
# except the last. OpenAI's Responses API caches automatically and
# ignores this marker (it's stripped before the prompt is sent to
# either provider).
CACHE_BREAKPOINT = "<<<CACHE_BREAKPOINT>>>"


# ---------- Helpers for inlining content ----------


def _inline_section(label: str, body: str) -> str:
    body = (body or "").rstrip()
    return f"### {label}\n\n{body}\n\n---\n"


@dataclass(frozen=True)
class PriorTurn:
    """One agent turn from a prior round, used for inlining into later-phase prompts."""
    agent: str
    round: int
    content: str


def _inline_prior_turns(turns: Iterable[PriorTurn], header: str) -> str:
    items = list(turns)
    if not items:
        return f"### {header}\n\n(No prior turns yet.)\n\n---\n"
    parts = [f"### {header}\n"]
    for t in items:
        parts.append(
            f"#### Prior turn — {t.agent}, round {t.round}\n\n"
            + (t.content.rstrip() if t.content else "(empty)")
            + "\n"
        )
    parts.append("---\n")
    return "\n".join(parts)


# ---------- Phase 0 ----------


def preflight_prompt(*, brief_content: str, agent_name: str) -> str:
    return (
        COMMON_PREAMBLE
        + f"""
# Phase 0: brief preflight (one-shot, parallel, both agents)

You are agent "{agent_name}". You will read the research brief and produce a short critique BEFORE the actual research begins. The cost of this phase is small; the value is catching flawed briefs before both agents spend full Phase 1 cost inheriting the flaw.

## Inputs

"""
        + _inline_section("Brief", brief_content)
        + CACHE_BREAKPOINT
        + f"""
## Task
Produce a single short markdown response with these sections (headings verbatim):

## Brief clarity
A one-paragraph assessment of whether the brief is clear, internally consistent, and answerable. Quote the line(s) you find ambiguous, if any.

## Missing inputs
Numbered list. Each item: a specific input (file, prior research, definition, dataset, contact) that the brief implies you need but does not provide. Empty list is fine; do not pad.

## Framing concerns
Numbered list of framing flaws — leading questions, false dichotomies, assumed conclusions baked into the brief's structure. Empty list is fine.

## Proposed scope
One paragraph: what you intend to research given the brief as written, and what you intend to NOT research (and why). This is your declared scope; Phase 2 can negotiate over it.

## Status
A single line, EXACTLY one of:
- `STATUS: BRIEF_OK` — brief is clear enough to proceed without user input
- `STATUS: BRIEF_NEEDS_INPUT` — at least one missing input or framing concern is severe enough that you recommend the orchestrator pause for user input before Phase 1

After STATUS, on a single line:
- `BRIEF_ISSUES: <integer>` — total count of items in Missing inputs + Framing concerns.

"""
        + _OUTPUT_INSTRUCTION
    )


# ---------- Phase 1 ----------


def research_prompt(*, brief_content: str, agent_name: str) -> str:
    return (
        COMMON_PREAMBLE
        + f"""
# Phase 1: independent research

You are agent "{agent_name}". Another agent from a different model family is researching the same brief in parallel; you cannot see their output yet, and you should not pre-emptively defer to them. The next phase will only have substance to negotiate if you take a real position now — a sterile, balanced survey is the worst outcome.

## Inputs

"""
        + _inline_section("Brief", brief_content)
        + CACHE_BREAKPOINT
        + """
## Task
Produce your best, complete answer to the brief. Use web search aggressively for any factual claim. Required structure (use these headings verbatim):

1. **Summary** — 3–5 sentences capturing your core findings and your bottom-line thesis.
2. **My thesis** — 1–3 sentences stating the judgment you currently believe is most correct. If the brief is purely descriptive, state which findings you are most confident in and which you are least confident in, and why.
3. **Detailed findings** — the substance, organized as the brief requires. Where the brief asks evaluative or recommendation questions, answer them. Distinguish high-confidence claims from plausible but uncertain claims.
4. **Claims I expect the other agent might dispute** — numbered list of the most likely disagreement points, each with one sentence on why it matters and what evidence would resolve it.
5. **Open questions** — what you could not resolve and why. Each item must name (a) the specific factual or design question, (b) what evidence would resolve it, (c) why you could not get that evidence this round.
6. **Sources** — numbered list with URLs.

Do not hedge. Do not pre-emptively defer to the other agent. Write as if you are the sole author and will have to defend this draft in Phase 2.

Anti-hedging guardrail: every claim of the form "X may be better than Y" or "it depends" must be followed by your best guess at the right answer and the conditions under which that guess holds. If you literally cannot guess, move the item to "Open questions" and say so.

"""
        + _OUTPUT_INSTRUCTION
    )


# ---------- Phase 2 round 1 ----------


def negotiation_round1_prompt(
    *,
    brief_content: str,
    own_draft: str,
    other_draft: str,
    agent_name: str,
    other_name: str,
) -> str:
    return (
        COMMON_PREAMBLE
        + f"""
# Phase 2 round 1: difference inventory (parallel, both agents)

You are agent "{agent_name}". The other agent is "{other_name}". Round 1 is different from later rounds: you have not yet seen any negotiation turn from {other_name}, but you HAVE seen their Phase 1 draft. Your job this round is not to converge on or ratify a final plan; it is to surface real differences, research the gaps, and propose an initial plan to negotiate from in round 2+.

You should use web search this round. Without new research, this round is a wasted turn.

## Inputs

"""
        + _inline_section("Brief", brief_content)
        + CACHE_BREAKPOINT
        + _inline_section(f"Your Phase 1 draft ({agent_name})", own_draft)
        + _inline_section(f"{other_name}'s Phase 1 draft", other_draft)
        + CACHE_BREAKPOINT
        + f"""
## Task
Produce your round-1 turn with these sections (headings verbatim):

## Summary
3–5 sentences summarising your position at this round: the diff items you consider material, your updated thesis after research, what you're proposing as the initial plan, and who you propose as drafter. Keep it short and factual — the UI extracts this as the timeline-card TL;DR.

## Diff vs {other_name}'s Phase 1
Numbered list. For each material difference between your draft and theirs: state what you said, what they said, the type of difference (factual / interpretive / scope / framing), and whether it is substantive, minor, or already resolved by re-reading. Do not list trivial wording differences; only differences a reader would care about.

For each **substantive** diff item, assign a stable ID of the form D-1, D-2, … (starting from 1, in first-appearance order). These IDs persist through all subsequent Phase 2 rounds, Phase 3, and Phase 4. The other agent will reference and reconcile these IDs starting in round 2.

## Gaps I researched this round
Numbered list. For each: which diff item it addresses, what you searched / read, what you found, and how your position has shifted (or not) in light of it. Cite sources with [n] tags and add them to Sources.

## Updated position
5–10 sentences. State your current best answer to the brief, post-research. This may differ from your Phase 1 thesis. If it does, name the specific evidence that changed your mind.

## Open questions for {other_name}
Numbered list. Genuine, substantive questions whose resolution is needed before we can converge on a plan. Each must be one {other_name} can actually answer from their draft or from research they would plausibly do — not rhetorical.

Right under each numbered item, add ONE blockquote line anchoring the question to the prior content, in one of these two forms:

  > quote: <a verbatim ≤25-word span from {other_name}'s Phase 1 draft that this question is about>

If the question is about MISSING content (something that should be there but isn't), use this form instead:

  > after: <verbatim section heading the missing content should follow, copied without the leading "## ">

The anchor is one line, a markdown blockquote, immediately under the numbered item. Skip the anchor when no specific span is being critiqued — un-anchored items are fine. The UI uses these anchors to scroll the prior draft into view next to your comment.

## Initial plan proposal
Bullet list of sections the final document should contain, with one-line key content per section. This is a *first* proposal; rounds 2+ will negotiate it.

## Drafter recommendation
- `DRAFTER: {agent_name}` (one sentence why) OR `DRAFTER: {other_name}` (one sentence why)
- `DOMAIN_FIT_SELF: <1-5>` — your self-rated fit on this brief
- `DOMAIN_FIT_OTHER: <1-5>` — your rating of {other_name}'s fit on this brief

## Status
A single line: `STATUS: NEGOTIATING` (round 1 cannot agree).
Followed by: `OPEN_QUESTIONS: <integer>` — count of items in your Open questions section.

## Sources
Numbered, with URLs.

## Empty-turn invariant (spec 0149 §5.4 — D04)
Every turn in this phase MUST contain at least one ledger operation block — `### RAISE`, `### ADDRESS`, `### RESOLVE`, `### ACKNOWLEDGE`, `### WITHDRAW`, or `### REQUEST_EVIDENCE`. A turn that emits only narrative sections with no operation block is structurally invalid and is recorded as a protocol violation. Round 1 cannot terminate the phase, so you must surface at least one `### RAISE` block (questions or disagreements) — if you genuinely have nothing material, raise that observation explicitly as a `### RAISE` with `kind: comment` rather than emitting a no-op turn.

"""
        + _OUTPUT_INSTRUCTION
    )


# ---------- Phase 2 rounds 2+ ----------


def negotiation_turn_prompt(
    *,
    brief_content: str,
    own_draft: str,
    other_draft: str,
    prior_turns: Iterable[PriorTurn],
    agent_name: str,
    other_name: str,
    round: int,
    soft_cap: int,
    hard_cap: int,
    standing_items: str = "",
    blocked_warning: str = "",
) -> str:
    return (
        COMMON_PREAMBLE
        + f"""
# Phase 2: plan negotiation

You are agent "{agent_name}". The other agent is "{other_name}". You are negotiating two things: (a) the plan for the unified final document, (b) which of you drafts it. The loop ends when both of you emit `STATUS: AGREED`, with matching `DRAFTER:`, an `AGREED_PLAN` block whose normalized hash matches {other_name}'s, `OPEN_QUESTIONS: 0`, `BLOCKING_DISAGREEMENTS: 0`, and matching `FINAL_SURFACED_DISAGREEMENTS: <N>` in the same round.

Two failure modes — equally bad:
- **Sycophancy:** agreeing because disagreeing is awkward. This phase exists to prevent this. Do not flip to AGREED to end the loop.
- **Adversarialism for its own sake:** manufacturing or re-litigating differences that do not materially change the final document. Concede when the other side's evidence is stronger; the goal is the best document, not the longest debate.

Anti-sycophancy procedure (apply before every turn; recommended structural mitigation, not yet directly validated for this exact heterogeneous file-mediated two-agent configuration):
1. Before you decide whether to agree, write — privately, in your reasoning — your strongest objection to the current plan if you were arguing the opposite position. If you cannot articulate any objection, that is itself evidence you may be acquiescing.
2. Before you concede a held disagreement, name the specific piece of {other_name}'s evidence that moved you. If you cannot name it, do not concede.

## Inputs

"""
        + _inline_section("Brief", brief_content)
        + CACHE_BREAKPOINT
        + _inline_section(f"Your Phase 1 draft ({agent_name})", own_draft)
        + _inline_section(f"{other_name}'s Phase 1 draft", other_draft)
        + CACHE_BREAKPOINT
        + f"""
This is **round {round}** of Phase 2 (soft cap {soft_cap}, hard cap {hard_cap}).

"""
        + _inline_prior_turns(prior_turns, "Prior Phase 2 conversation turns (in order)")
        # Spec 0089 § C — high-salience warning when the prior round emitted
        # AGREED but the ledger cross-check blocked convergence. Rendered
        # BEFORE the standing-items section so the agent reads the
        # explanation, then the concrete item list right after.
        + (("\n" + blocked_warning + "\n") if blocked_warning else "")
        + (("\n" + standing_items + "\n") if standing_items else "")
        + f"""
## Task
Produce your turn for round {round} with these sections (headings verbatim):

## Summary
3–5 sentences summarising your position in THIS round: what you've held onto, what you've conceded or updated this round, whether you're agreeing or still negotiating, and (if agreeing) whom you propose as drafter. Keep it short and factual — the UI extracts this as the timeline-card TL;DR.

## Answers to {other_name}'s open questions
Address every open question from {other_name} — both the ones in their most recent turn AND any prior-round questions still listed in the standing-items section below. One answer block per question.

**Format requirement (spec 0090):** the first line of each answer block MUST start with the question's protocol ID (e.g. `Q-g-r1-01`) so the system can link your answer back to the originating question. The recommended format is a numbered list with the ID inside the bold label:

```
1. **Q-g-r1-01 — short title:** your answer body…
2. **Q-g-r1-02 — short title:** your answer body…
```

Bold-header form is also accepted as long as the ID is in the head:

```
**Q-g-r1-03 — short title**

your answer body…
```

If {other_name} had no open questions in their last turn AND the standing-items section is empty, write "(none)". Otherwise, leaving a question unaddressed marks it as ghosted in the UI and continues to block convergence.

## What I researched since the last round
Numbered list, may be empty in late rounds. Each item: what you searched / read, what you found, how your position has updated. This phase is supposed to surface evidence, not just exchange opinions.

If the other agent's prior turn contains any [U]-tagged claim that you consider material to the final document, you must perform an independent search and report the result using this structure per claim:

- Claim: <quote, ≤25 words>
- Tag from other agent: [U]
- Independent search: <one line on what was searched>
- Signal: CORROBORATED | UNCORROBORATED | CONTRADICTED
- Sources found: <list with one-line quality note per source>
- My take: <one or two sentences on whether this changes your position>

CORROBORATED means independent sources support the claim. UNCORROBORATED means you could find neither confirmation nor contradiction. CONTRADICTED means you found one or more sources contradicting it — note that this does not auto-kill the claim; your "My take" must state whether the contradicting source is itself reliable enough to override the original.

A [V] tag means the producing agent retrieved and inspected a source during this run. It does not mean the claim is independently corroborated. The receiving agent does not need to independently re-check every [V] claim. However, if a [V] claim is central to the final recommendation, central to a final-surfaced disagreement, or used to justify a major revision to the agreed plan, the receiving agent should either: (1) independently corroborate it and assign CORROBORATED, (2) report that it could not independently confirm or contradict it and assign UNCORROBORATED, or (3) report contradicting evidence and assign CONTRADICTED. Use the same per-claim structure as above. For ordinary sourced claims that are not central to the final recommendation, normal citation review is enough.

Scope discipline: corroboration applies only to claims you consider material (v3 materiality test applies). For [V] claims, only the narrower "central" set triggers corroboration. If you find yourself running more than 5 corroboration reports this turn, you are over-applying — tighten materiality.

## Open questions for {other_name}
Numbered list. Genuine, substantive questions whose resolution is needed before agreement. Empty list is acceptable only if you genuinely have no open questions — see anti-sycophancy procedure above.

Right under each numbered item, add ONE blockquote line anchoring the question to the prior content (either {other_name}'s most recent Phase 2 turn or their Phase 1 draft):

  > quote: <a verbatim ≤25-word span from the prior content this question is about>

If the question is about MISSING content, use:

  > after: <verbatim section heading the missing content should follow, without the leading "## ">

The anchor is one line, a markdown blockquote, immediately under the numbered item. Skip it when no specific span is being critiqued — un-anchored items are fine. The UI uses these anchors to scroll the prior content into view next to your comment.

## Plan as I currently propose it
Bullet list of sections the final document should contain. Incorporate {other_name}'s good points from prior rounds; hold the line only where evidence supports it.

## Substantive disagreements I'm holding
Numbered list. Use stable D-N IDs assigned in round 1 (or introduced in this round if genuinely new). For each entry with status `open`:
- (a) D-N ID and short title, (b) your position, (c) {other_name}'s position, (d) why you are not yet conceding (cite specific evidence or argument), (e) materiality — one sentence on how this disagreement would change the final document. If you cannot state (e), drop the item as immaterial.

The anchor line for each entry MUST follow one of these two exact shapes (with a leading "-" list marker — not a numbered list, not a heading):

- Open form (verbatim): ``- D-N: <short label> — status: open``
- Terminal form (verbatim): ``- **D-N (<short label>):** `<terminal-state>` — <one-line note>``

(Terminal-state is one of: resolved, non_blocking_limitation, conceded, accepted.) The (a)–(e) sub-items hang off the open-form anchor line as `- (a) ...` bullets.

For each open-form D-N entry, add ONE additional blockquote sub-item that anchors the disagreement to a specific span on the prior content:

- ``> quote: <a verbatim ≤25-word span from {other_name}'s most recent turn or Phase 1 draft that this disagreement is about>``

or, for disagreements about MISSING content:

- ``> after: <verbatim section heading the missing content should follow, without the leading "## ">``

The anchor sub-item is one blockquote line, indented under the D-N anchor line alongside the (a)–(e) bullets. Skip it when no specific span is being critiqued. Un-anchored entries are fine; the UI just won't auto-scroll the left pane when the user clicks them.

For entries with status `final_surfaced`: list them here and also in the ## Final-surfaced disagreements section below.

## Final-surfaced disagreements
Include this section only if FINAL_SURFACED_DISAGREEMENTS > 0. For each FSD-N entry — using IDs from the D-N ledger, renaming D-N → FSD-N at first final-surfacing — use this exact structure:

```
### FSD-<N>: <short title>

- Claude position:
- GPT position:
- Evidence for Claude position:
- Evidence for GPT position:
- Why this could not or should not be resolved within this run:
- Why this is still material to the final document:
- Exact final-document treatment:
- Does this affect the final recommendation? yes / no
```

IDs are stable once assigned. A disagreement may only be marked for final surfacing if both agents can state how resolving it one way versus the other would materially change the final document's recommendation, framing, confidence level, or reader decision. If that material effect cannot be stated, the disagreement must be resolved, dropped as immaterial, or moved into non-blocking limitations. Final-surfacing is not an escape hatch for hard work — the default expectation remains resolution.

## Resolved or non-blocking differences
Numbered list of D-N entries no longer blocking, with their final status and one sentence explaining why:
- `resolved` — both now agree; cite the evidence that resolved it.
- `non_blocking_limitation` — real difference, not material enough to block or surface.
- `dropped_as_immaterial` — the agent who raised it no longer considers it worth holding; one sentence on why.

## Agreement check
If you are not ready to agree, write "(not ready)" and one sentence naming the blocker.
If you are ready to agree, all five lines are required:
- `ENDORSEMENT:` one sentence explaining why the proposed plan is now better than your initial plan.
- `MIND_CHANGED:` one sentence naming the most important point you changed or refined, OR "none, because my initial position survived review."
- `REMAINING_UNCERTAINTY:` one sentence naming any uncertainty that should be disclosed in the final document but does not block drafting.
- `STRONGEST_REMAINING_OBJECTION:` one sentence — the strongest objection you can still articulate against this plan.
- `WHY_NON_BLOCKING:` one sentence — why that objection does not block your endorsement.

If any of these five lines is missing or empty AND you intend to emit AGREED, emit NEGOTIATING instead. AGREED without all five populated is a parse error.

## AGREED_PLAN
If and only if you intend to emit `STATUS: AGREED`, provide the final agreed plan as a fenced markdown block with stable field keys: a numbered list of sections, each with a `Title:` line and a `Key claims:` sub-list. If FINAL_SURFACED_DISAGREEMENTS > 0, the block MUST also include a `## Final-surfaced disagreements (canonical)` section with one `### FSD-N: <title>` subsection per FSD ID in this exact format:

```
## Final-surfaced disagreements (canonical)

### FSD-<N>: <short title>

- Claude position:
- GPT position:
- Exact final-document treatment:
- Affects final recommendation? yes / no
```

This canonical section is the single source of truth consumed by Phase 3. It must be byte-equal between the two converging turns (because the AGREED_PLAN block is hash-matched). Phase 3 does not read the free-form ## Final-surfaced disagreements sections.

This block MUST hash-match {other_name}'s `AGREED_PLAN` under the orchestrator's normalization pass (whitespace collapse, line-ending normalize, heading-case normalize, list-marker normalize, trailing-punctuation trim). If you are still negotiating, write "(not agreed)".

**Adoption procedure (because turns are written in parallel each round, you cannot newly coordinate exact wording in the same round):**
1. In some round k, one agent (the proposer) writes a complete `AGREED_PLAN` block they would commit to. They emit `STATUS: NEGOTIATING` if not yet ready to agree, or `STATUS: AGREED` if they are.
2. In round k+1, if the other agent endorses the plan, they copy that block VERBATIM into their own turn under the `## AGREED_PLAN` heading and emit `STATUS: AGREED`. The original proposer must REPEAT the same canonical block in this same round k+1 (also under `## AGREED_PLAN`, also `STATUS: AGREED`).
3. The orchestrator declares Phase 2 converged only when both turns in the latest round contain the same `AGREED_PLAN` block under normalization AND both emit `STATUS: AGREED`. Same-round AGREED with mismatched plans is a parse error and triggers a repair turn.
4. If the other agent wants to amend the proposer's block, they may do so in round k+1, but in that case neither agent emits `STATUS: AGREED` that round — the amended block becomes the new proposal and the cycle restarts at step 1 in round k+2.

## Drafter recommendation
A single line, one of:
- `DRAFTER: {agent_name}` (one sentence why)
- `DRAFTER: {other_name}` (one sentence why)

Plus, on separate lines:
- `DOMAIN_FIT_SELF: <1-5>` — your self-rated fit on this brief
- `DOMAIN_FIT_OTHER: <1-5>` — your rating of {other_name}'s fit on this brief

If you and {other_name} disagree on the drafter across rounds, the orchestrator will apply the structured tiebreak chain (DOMAIN_FIT scores → draft fit with AGREED_PLAN → hash-of-brief-content), surface a warning to the operator if disagreement persists past round 3, and never default to a named model.

## Status
A single line, EXACTLY one of:
- `STATUS: NEGOTIATING` (still working; default)
- `STATUS: AGREED` (only if: Open questions empty AND Substantive disagreements empty AND Agreement check is complete AND AGREED_PLAN is populated AND you are confident about plan and drafter)

After STATUS, on separate lines:
- `OPEN_QUESTIONS: <integer>` — count of items in your Open questions section
- `BLOCKING_DISAGREEMENTS: <integer>` — count of D-N entries with status `open`
- `FINAL_SURFACED_DISAGREEMENTS: <integer>` — count of FSD-N entries (0 if none)

## Empty-turn invariant (spec 0149 §5.4 — D04)
Every turn in this phase MUST contain at least one ledger operation block — `### RAISE`, `### ADDRESS`, `### RESOLVE`, `### ACKNOWLEDGE`, `### WITHDRAW`, or `### REQUEST_EVIDENCE` — OR a top-level `STATUS: AGREED` line that concludes the phase under the convergence gates above. A turn that emits only narrative sections with no operation block and no terminal status is structurally invalid and is recorded as a protocol violation. If you have genuinely nothing to add and the convergence gates are met, prefer `STATUS: AGREED` explicitly over producing a no-op turn.

"""
        + _OUTPUT_INSTRUCTION
    )


# ---------- Phase 3 ----------


def _format_fsd_items(items: Iterable[object]) -> str:
    items_list = list(items)
    if not items_list:
        return "(none — Phase 2 reached full consensus)"
    formatted: list[str] = []
    for i in items_list:
        formatted.append(
            f"### {i.id}: {i.title}\n\n"
            f"- Claude position: {i.claude_position}\n"
            f"- GPT position: {i.gpt_position}\n"
            f"- Exact final-document treatment: {i.final_document_treatment}\n"
            f"- Affects final recommendation? {i.affects_recommendation}"
        )
    return "\n\n".join(formatted)


def drafting_prompt(
    *,
    brief_content: str,
    own_draft: str,
    other_draft: str,
    prior_turns: Iterable[PriorTurn],
    agent_name: str,
    other_name: str,
    agreed_plan_block: str | None,
    final_surfaced_disagreements: Iterable[object],
) -> str:
    plan_block_section = (
        _inline_section("Agreed plan (verbatim from the last Phase 2 round, hash-verified)", agreed_plan_block)
        if agreed_plan_block
        else _inline_section(
            "Agreed plan",
            "(not available — fall back to reading the agreed plan from the Phase 2 conversation below)",
        )
    )
    fsd_text = _format_fsd_items(final_surfaced_disagreements)
    fsd_section = _inline_section(
        "Final-surfaced disagreements (canonical, from hash-verified AGREED_PLAN)",
        fsd_text,
    )

    return (
        COMMON_PREAMBLE
        + f"""
# Phase 3: drafting

You are agent "{agent_name}". You and "{other_name}" agreed in Phase 2 that you would draft the final document. The orchestrator has verified that both agents' final `AGREED_PLAN` blocks hash-match under the normalization pass.

## Inputs

"""
        + _inline_section("Brief", brief_content)
        + CACHE_BREAKPOINT
        + _inline_section(f"Your Phase 1 draft ({agent_name})", own_draft)
        + _inline_section(f"{other_name}'s Phase 1 draft", other_draft)
        + plan_block_section
        + fsd_section
        + CACHE_BREAKPOINT
        + _inline_prior_turns(prior_turns, "Full Phase 2 conversation")
        + """
## Task
Write the unified final document, following the agreed plan exactly in section order and section topics. Required structure:

1. **Summary** — 3–5 sentences.
2. **Findings** — the merged substance, following the agreed plan section by section.
3. **Disagreements left open** — structure depends on what Phase 2 surfaced:
   - If `FINAL_SURFACED_DISAGREEMENTS > 0`: include one subsection per FSD-N ID, labelled exactly `### FSD-N: <title>`, containing both positions and the agreed final-document treatment from the canonical plan section above. Every FSD-N must appear — you may not omit one silently. If you believe a final-surfaced disagreement should not appear, raise it as a comment in Phase 4.
   - `resolved` and `non_blocking_limitation` disagreements may be referenced briefly but need not be enumerated.
   - `dropped_as_immaterial` entries do not appear.
4. **Open questions** — what neither of you could answer; what input would resolve them.
5. **Sources** — merged numbered list with URLs. Reconcile duplicate citations across the two drafts.
6. **Confidence ledger** — a table listing every material claim in the draft alongside its source tag and corroboration signal:

| Claim | Tag | Signal | Source notes |
|---|---|---|---|
| <short form of the claim> | [V] or [U] | CORROBORATED / UNCORROBORATED / CONTRADICTED / — | One sentence on what was found. |

Material claims for the ledger are those flagged in Phase 2 corroboration reports, those tied to FSD entries, and any other claim that materially affects the final recommendation. Non-material claims should usually be omitted. Use "—" in the Signal column only for exceptional cases where a lower-materiality [U] claim is included for transparency. Body prose stays clean — do not scatter [V]/[U] tags through the running text. The ledger is where confidence information lives.

Favour the position with stronger evidence regardless of whose draft it came from. Where the two Phase 1 drafts differ on a claim and Phase 2 did not resolve which is correct, surface the disagreement in section 3 rather than silently picking one. Preserve important uncertainty; do not smooth it away to make the document sound more settled than it is.

"""
        + _OUTPUT_INSTRUCTION
    )


# ---------- Phase 4 ----------


def review_turn_prompt(
    *,
    brief_content: str,
    draft_content: str,
    prior_turns: Iterable[PriorTurn],
    agent_name: str,
    other_name: str,
    drafter_name: str,
    round: int,
    soft_cap: int,
    hard_cap: int,
    standing_items: str = "",
    blocked_warning: str = "",
) -> str:
    role = "DRAFTER" if agent_name == drafter_name else "REVIEWER"
    return (
        COMMON_PREAMBLE
        + f"""
# Phase 4: review

You are agent "{agent_name}", in your role as {role} (drafter or reviewer). The drafter ({drafter_name}) wrote the current draft. You and "{other_name}" are converging on a final version. The loop ends when both of you emit `STATUS: APPROVED` with `OPEN_ISSUES: 0` in the same round.

Two failure modes — equally bad:
- **Sycophancy:** approving because the loop has gone on long enough, not because the draft is right. By round 3+ you are jointly invested in the draft and the natural pull is toward agreement. Resist this. The user does not benefit from a draft you secretly think is flawed.
- **Adversarialism / scope creep:** demanding restructures and new sections that were not in the agreed plan. Phase 2 produced the plan; Phase 4 reviews execution against it, not the plan itself. Unless a clear flaw emerged that the plan did not anticipate, do not relitigate the plan here.

Anti-sycophancy procedure (apply before every turn; recommended structural mitigation, not yet directly validated for this exact configuration):
1. Before you decide whether to approve, write — privately, in your reasoning — your strongest objection to the current draft if you were arguing the opposite position. If you cannot articulate any objection, that is evidence you may be acquiescing.
2. Before you concede a held comment, name the specific change in the draft (or the specific drafter argument) that resolved it.

**Drafter engagement requirement (spec 0091):**

If you are the DRAFTER ({drafter_name}), you may NOT emit `STATUS: APPROVED` in round 1. Round 1 is for engagement, not termination. Specifically:

- In round 1 of Phase 4 you must emit `STATUS: REVIEWING` with at least one entry in your `## Issue ledger` — either accepting / rejecting / resolving an open issue raised by {other_name} in their round-1 turn, OR raising a new issue you identified on your own re-read of the draft.
- A round-1 turn that says "(no prior issues, no new issues, 0 open)" then emits APPROVED will be rejected by the orchestrator and the round will be replayed. The first round of Phase 4 must demonstrate the drafter has actually engaged with the draft from the reviewer's perspective.
- From round 2 onward APPROVED becomes available, subject to the same Approval-check fields required by the rest of this protocol.

This rule applies symmetrically to whichever agent is the drafter — Phase 2 already prevents round-1 agreement on the same principle ("round 1 cannot agree"). Phase 4 brings the same structural protection.

## Inputs

"""
        + _inline_section("Brief", brief_content)
        + CACHE_BREAKPOINT
        + _inline_section("Current draft", draft_content)
        + CACHE_BREAKPOINT
        + f"""
This is **round {round}** of Phase 4 (soft cap {soft_cap}, hard cap {hard_cap}).

"""
        + _inline_prior_turns(prior_turns, "Prior Phase 4 review turns (in order)")
        # Spec 0089 § C — high-salience warning when the prior review round
        # emitted APPROVED but the ledger cross-check blocked convergence.
        + (("\n" + blocked_warning + "\n") if blocked_warning else "")
        + (("\n" + standing_items + "\n") if standing_items else "")
        + f"""
## Task
Produce your turn for round {round} with these sections (headings verbatim):

## Answers to {other_name}'s prior comments
Address every comment {other_name} raised in their most recent turn — both new ones and any standing-items section entries below. "(none — first round)" if applicable.

**Format requirement (spec 0090):** the first line of each answer block MUST start with the comment's protocol ID (e.g. `C-3` for one of {other_name}'s prior comments, or `OAI-P4-1` / `[I-g-r1-01]` when referencing the cross-round system ID) so the system can link your answer back. Recommended format is a numbered list with the ID inside the bold label:

```
1. **C-1 — short title:** your answer body…
2. **C-2 — short title:** your answer body…
```

Bold-header form is also accepted when the ID is in the head.

## Issue ledger (delta + currently open)
Numbered list. Include (a) all currently open issues with stable IDs and current status, (b) new issues raised this round with stable IDs assigned by the agent who raises them, (c) status changes for previously raised issues — status one of `open` / `accepted` / `rejected` / `resolved`, each with a one-sentence reason. Resolved historical issues can be referenced by ID rather than re-emitted in full. The DRAFTER must answer every prior `open` issue this round as accepted / rejected / resolved / still-open; silent skipping is not allowed.

**Format requirement (spec 0090):** each ledger entry's first line MUST contain the issue's stable ID followed by its current status marker. Recommended format:

```
1. **OAI-P4-1 — resolved:** Inline [V]/[U] tags added throughout the round-2 revised draft.
2. **OAI-P4-2 — open:** Process artifacts still present in the title block.
3. **[I-g-r1-03] — resolved:** PgBouncer text rewritten in round-2 draft.
```

Both your own IDs (e.g., `OAI-1`, `C-7`, `D-5`) and the cross-round system IDs (e.g., `I-g-r1-01`) are accepted. Without an ID in the head, the system can't dedupe the entry across rounds and the issue will appear repeatedly in the UI.

For each `open` issue, add ONE blockquote line right under the numbered item anchoring the issue to a specific span on the current draft:

  > quote: <a verbatim ≤25-word span from the current draft this issue is about>

If the issue is about MISSING content, use:

  > after: <verbatim section heading the missing content should follow, without the leading "## ">

The anchor is one line, a markdown blockquote, immediately under the item. Skip it when no specific span is being critiqued. Un-anchored issues are fine; the UI just won't auto-scroll the draft when the user clicks them.

## Evidence checked this round
Required every round. Use these exact sub-fields:
- New research performed: <list with inline source citations, or "(none)">
- Claims checked against existing sources: <list, or "(none)">
- Factual issues found: <list, or "(none)">
- No new research because: <one sentence reason, or "(n/a — new research was performed)">
- Corroboration on the other agent's claims:
  - Material [U] claims: <use the per-claim structure from the Source tagging preamble, or "(none)">
  - Central [V] claims: <use the per-claim structure from the Source tagging preamble, or "(none)">

The "No new research because:" field cannot be blank when the other research fields are "(none)" — you must explicitly justify a research-free turn. Corroboration scope: material [U] claims from the other agent; central [V] claims (those driving the final recommendation, an FSD, or a major revision) only. Keep to ≤5 corroboration reports per turn.

Evidence discipline rule: if you raise a factual, citation, market, legal, technical, or time-sensitive objection in this turn, you must either (a) cite new evidence from web search or another tool, or (b) explicitly tie the objection to an existing source already cited in the draft or a prior conversation turn. Bare assertions of factual error without evidence linkage are out of scope and the other agent is entitled to disregard them.

## Comments on the current draft
Numbered list of new or still-open comments. For each: (a) location in the draft (section name and quoted line if possible), (b) the issue, (c) the specific change you want. Structure, clarity, framing, citation completeness, and rhetorical framing are ALL in scope — for a research document, structure is substance when it affects the document's correctness, completeness, or usefulness. Word-choice quibbles that do not affect any of those are out of scope.

Right under each numbered comment, add ONE blockquote line anchoring the comment to the current draft:

  > quote: <a verbatim ≤25-word span from the current draft this comment is about>

If the comment is about MISSING content, use:

  > after: <verbatim section heading the missing content should follow, without the leading "## ">

The anchor is one line, a markdown blockquote, immediately under the numbered item. The (a) sub-bullet may already paraphrase a location — the blockquote anchor is the machine-readable form the UI uses to scroll the draft into view. Skip the anchor when no specific span is being critiqued.

## Disagreement carryover audit
Required in round 1 and in any turn emitting STATUS: APPROVED. Optional in other rounds.

- Final-surfaced disagreements from Phase 2: for each FSD-N ID — state present in draft / missing / distorted (one sentence).
- Resolved disagreements that re-emerged: list of D-N IDs the reviewer believes were resolved in Phase 2 but appear unresolved or distorted in the draft, or "(none)".
- New disagreements raised during review: list of new D-N IDs introduced since Phase 2, with status, or "(none)".

## Substantive disagreements I'm holding
Numbered list. For each: your position, {other_name}'s position, why you are holding, and one-sentence materiality test (how would this change the final document?). If you cannot state materiality, drop the item.

For each entry, optionally add ONE blockquote line anchoring the disagreement to the current draft:

  > quote: <a verbatim ≤25-word span from the current draft this disagreement is about>

or, for disagreements about MISSING content:

  > after: <verbatim section heading the missing content should follow, without the leading "## ">

The anchor is one line, a markdown blockquote, immediately under the numbered item. Un-anchored entries are fine.

## Drafter revision note
If you are the DRAFTER ({drafter_name}), for every comment from {other_name}'s prior turn state:
- (a) what you changed and where (section + the specific edit you made),
- (b) what you considered and rejected, and why,
- (c) any comment you have not yet acted on, and why,
- (d) any Confidence ledger changes: newly added rows, updated corroboration signals, or removed claims.

If you are the DRAFTER and {other_name} raised valid points, emit a REVISED DRAFT in this turn under a separate `## Revised draft` heading, containing the full updated draft text (all six sections — Summary, Findings, Disagreements left open, Open questions, Sources, Confidence ledger). The orchestrator detects the revised draft and advances the draft version. The REVIEWER never modifies the draft, only comments.

If you are the REVIEWER, write "(reviewer — no draft edits)".

## Approval check
If you are not ready to approve, write "(not ready)" and one sentence naming the blocker.
If you are ready to approve, all four lines are required:
- `ENDORSEMENT:` one sentence explaining why the current draft satisfies the brief.
- `NON_BLOCKING_LIMITATIONS:` one sentence naming any residual limitation that should not block approval.
- `STRONGEST_REMAINING_OBJECTION:` one sentence — the strongest objection you can still articulate against this draft.
- `WHY_NON_BLOCKING:` one sentence — why that objection does not block your approval.

If APPROVED is emitted without all four fields populated, the orchestrator treats the round as REVIEWING.

## Status
A single line, EXACTLY one of:
- `STATUS: REVIEWING` (still working; default)
- `STATUS: APPROVED` (only if: Comments section lists no items you consider unresolved AND Substantive disagreements is empty AND Issue ledger has no `open` items AND Approval check is complete)

After STATUS, on a single line:
- `OPEN_ISSUES: <integer>` — count of unresolved `open` items in the Issue ledger and Comments sections. You MUST emit this line; a missing value will be treated as failure-to-converge by the orchestrator, not as zero.

## Empty-turn invariant (spec 0149 §5.4 — D04)
Every turn in this phase MUST contain at least one ledger operation block — `### RAISE`, `### ADDRESS`, `### RESOLVE`, `### ACKNOWLEDGE`, `### WITHDRAW`, or `### REQUEST_EVIDENCE` — OR a top-level `STATUS: APPROVED` line that concludes the phase under the gates above. A turn that emits only narrative sections with no operation block and no terminal status is structurally invalid and is recorded as a protocol violation. The DRAFTER's round-1 turn additionally cannot emit `STATUS: APPROVED`; that turn must surface at least one ledger block (typically `### RAISE` of a self-identified issue or `### ADDRESS` of one of the reviewer's round-1 issues).

"""
        + _OUTPUT_INSTRUCTION
    )


# ---------- Repair prompt ----------


def repair_prompt(
    *,
    agent_name: str,
    phase: int,
    errors: list[str],
    malformed_content: str,
) -> str:
    if phase == 2:
        phase_fields = [
            "`STATUS: NEGOTIATING|AGREED`",
            "`DRAFTER: claude|openai`",
            "`OPEN_QUESTIONS: <integer>`",
            "`BLOCKING_DISAGREEMENTS: <integer>`",
            "`FINAL_SURFACED_DISAGREEMENTS: <integer>`",
            "(when STATUS: AGREED) populated `AGREED_PLAN` block, `STRONGEST_REMAINING_OBJECTION:`, `WHY_NON_BLOCKING:`",
        ]
    else:
        phase_fields = [
            "`STATUS: REVIEWING|APPROVED`",
            "`OPEN_ISSUES: <integer>`",
            "`## Evidence checked this round` section heading",
            "(round 1 or STATUS: APPROVED) `## Disagreement carryover audit` section heading",
            "(when STATUS: APPROVED) `STRONGEST_REMAINING_OBJECTION:`, `WHY_NON_BLOCKING:`",
        ]

    errors_block = "\n".join(f"- {e}" for e in errors)
    fields_block = "\n".join(phase_fields)

    return (
        COMMON_PREAMBLE
        + f"""
# Format repair

Your most recent turn (agent "{agent_name}", phase {phase}) could not be parsed. The following required machine-parseable fields were missing or invalid:

{errors_block}

## Inputs

"""
        + _inline_section("Your previous (malformed) turn", malformed_content)
        + f"""
## Task

Re-emit your turn with the substantive content unchanged. Only fix the formatting of required fields. Ensure the following appear on their own lines, in plain text (no surrounding backticks or emphasis), near the end of your turn:

{fields_block}

If your STATUS line is missing or malformed, infer the correct status from your turn's content. For phase {phase}: if open questions/issues count to 0 and you have no substantive disagreements, you may emit AGREED/APPROVED; otherwise emit NEGOTIATING/REVIEWING.

"""
        + _OUTPUT_INSTRUCTION
    )


# ---------- Spec 0032 — Phase 2 hash-drift escape ----------


def force_verbatim_copy_prompt(
    *,
    agent_name: str,
    other_name: str,
    drafter_name: str,
    canonical_plan: str,
    round: int,
) -> str:
    """Spec 0032 — special Phase 2 repair prompt for the hash-drift case.

    Fires when both agents have emitted ``STATUS: AGREED`` with matching
    drafter / OQ / BD / FSD, but their ``AGREED_PLAN`` blocks don't
    hash-match (the model paraphrased instead of copying verbatim per the
    protocol). Hands the recipient the canonical plan block (from the
    named drafter's turn) and demands byte-for-byte reproduction.

    The recipient is always the NON-drafter — if drafter == "claude" we
    repair openai, and vice versa.
    """
    return (
        COMMON_PREAMBLE
        + f"""
# Phase 2 — verbatim-copy repair (round {round})

You are agent "{agent_name}". The other agent is "{other_name}". The
orchestrator detected that both of you emitted `STATUS: AGREED` in
round {round} with matching DRAFTER, OPEN_QUESTIONS=0,
BLOCKING_DISAGREEMENTS=0, and matching FINAL_SURFACED_DISAGREEMENTS —
but your `AGREED_PLAN` blocks do NOT hash-match. Per the protocol:

> Same-round AGREED with mismatched plans is a parse error and
> triggers a repair turn.

The drafter ({drafter_name}) wrote the canonical `AGREED_PLAN`
block below. Your task this turn: re-emit your round-{round} turn
**reusing this exact `AGREED_PLAN` block, byte-for-byte**. Do not
paraphrase, do not reorder sections, do not "improve" wording. The
hash check normalises whitespace, list markers, heading case, and
trailing punctuation — so minor formatting differences are fine —
but the substantive content of each line must match exactly.

## Canonical AGREED_PLAN (from {drafter_name})

```
{canonical_plan}
```

## Task

Re-emit your full round-{round} Phase 2 turn with every required
section: `## Summary`, `## Answers to {other_name}'s open questions`,
`## What I researched since the last round`, `## Open questions for
{other_name}`, `## Plan as I currently propose it`, `## Substantive
disagreements I'm holding`, `## Resolved or non-blocking differences`,
`## Agreement check`, `## AGREED_PLAN`, `## Drafter recommendation`,
`## Status`. The `## AGREED_PLAN` section MUST contain the canonical
block above, byte-for-byte.

For every other section you may carry over the substantive content
from your previous round-{round} turn — they are not under dispute.
Keep them, but you must still emit them. In `## Status` write:

- `STATUS: AGREED`
- `OPEN_QUESTIONS: 0`
- `BLOCKING_DISAGREEMENTS: 0`
- `FINAL_SURFACED_DISAGREEMENTS: <same count as before>`

In `## Drafter recommendation` write `DRAFTER: {drafter_name}` with
the same one-sentence justification you used previously.

The orchestrator's hash check will run again. If your `AGREED_PLAN`
block still doesn't match, Phase 2 will escape via canonical
promotion — your plan version will be discarded — so just copy.

"""
        + _OUTPUT_INSTRUCTION
    )


# ---------- Spec 0033 — input bundles for the UI Input tab ----------
#
# Each phase's prompt is built from a static template (instructions,
# section structure, anti-sycophancy reminders, output schema) plus a
# small set of inlined content strings (the brief, the agents' Phase 1
# drafts, the AGREED_PLAN block, the current draft, prior-round
# transcripts). The UI's per-turn Input tab renders these as
# independently collapsible sections so the user can audit *what
# actually went into the model* at this turn.
#
# The vocabulary matches the spec-0030 Tk keys exactly
# (`brief`, `d1`, `d2`, `plan`, `hist`, `draft`, `histp`) plus a fixed
# `system` key for the static instruction template. Empty pieces are
# returned as empty strings (not omitted) so the UI can render a
# "(not used in this turn)" stub uniformly.
#
# Implementation choice: each `*_input_bundle()` builds the `system`
# value by calling the corresponding `*_prompt()` with a
# `_placeholder("<label>")` string in place of each inlined content
# argument and then stripping the `CACHE_BREAKPOINT` sentinel. This
# means the system text is byte-equal to the prompt template by
# construction — any drift between prompt and bundle is impossible.


_BUNDLE_PLACEHOLDER_PREFIX = "[see the "
_BUNDLE_PLACEHOLDER_SUFFIX = ' section below in this Input tab]'


def _placeholder(label: str) -> str:
    """The string substituted for inline content in the rendered system template."""
    return f'{_BUNDLE_PLACEHOLDER_PREFIX}"{label}"{_BUNDLE_PLACEHOLDER_SUFFIX}'


def _strip_cache_marker(text: str) -> str:
    """Remove the cache-control sentinel from system text destined for human view."""
    # Also collapse the doubled-blank-line that often sits around the marker.
    return text.replace(CACHE_BREAKPOINT, "").replace("\n\n\n", "\n\n")


def _placeholder_prior_turns(label: str) -> "list[PriorTurn]":
    """A single-element PriorTurn list carrying a placeholder string.

    Threads a placeholder through `_inline_prior_turns` so the system
    template still shows the heading + structure that prior-turn inlining
    produces, without dumping any actual transcript content.
    """
    return [PriorTurn(agent="<placeholder>", round=0, content=_placeholder(label))]


def preflight_input_bundle(
    *,
    brief: str,
    attachments: Iterable[Attachment] = (),
    agent_name: str = "<agent>",
) -> dict[str, str]:
    """Spec 0145 — Phase 0 preflight input bundle.

    Emits canonical-ID keys: ``system.task.input``,
    ``user_prompt.message``, plus one ``user_prompt.attachment.<id>``
    row per attachment. Legacy short-key vocabulary
    (``brief``/``d1``/``d2``/...) is replaced; historical bundles are
    translated on the read path via the JS shim in
    ``artifact-display.js``.
    """
    system_text = _strip_cache_marker(
        preflight_prompt(
            brief_content=_placeholder("brief"),
            agent_name=agent_name,
        )
    )
    out: dict[str, str] = {"system.task.input": system_text}
    _emit_user_prompt_text(out, brief, attachments)
    return out


def research_input_bundle(
    *,
    brief: str,
    attachments: Iterable[Attachment] = (),
    agent_name: str = "<agent>",
) -> dict[str, str]:
    """Spec 0145 — Phase 1 research input bundle.

    Canonical keys: ``system.task.research_plan``, ``user_prompt.message``,
    plus per-attachment rows.
    """
    system_text = _strip_cache_marker(
        research_prompt(
            brief_content=_placeholder("brief"),
            agent_name=agent_name,
        )
    )
    out: dict[str, str] = {"system.task.research_plan": system_text}
    _emit_user_prompt_text(out, brief, attachments)
    return out


def negotiation_round1_input_bundle(
    *,
    brief: str,
    claude_draft: str,
    openai_draft: str,
    attachments: Iterable[Attachment] = (),
    agent_name: str = "<agent>",
    other_name: str = "<other>",
) -> dict[str, str]:
    """Spec 0145 — Phase 2 round 1 input bundle.

    Canonical keys: ``system.task.plan_negotiation``,
    ``user_prompt.message``, per-attachment rows, ``phase1.claude``,
    ``phase1.openai``.
    """
    system_text = _strip_cache_marker(
        negotiation_round1_prompt(
            brief_content=_placeholder("brief"),
            own_draft=_placeholder("d1"),
            other_draft=_placeholder("d2"),
            agent_name=agent_name,
            other_name=other_name,
        )
    )
    out: dict[str, str] = {"system.task.plan_negotiation": system_text}
    _emit_user_prompt_text(out, brief, attachments)
    out["phase1.claude"] = claude_draft or ""
    out["phase1.openai"] = openai_draft or ""
    return out


def negotiation_turn_input_bundle(
    *,
    brief: str,
    claude_draft: str,
    openai_draft: str,
    prior_turns: Iterable[PriorTurn],
    attachments: Iterable[Attachment] = (),
    agent_name: str = "<agent>",
    other_name: str = "<other>",
    round: int = 0,
    soft_cap: int = 0,
    hard_cap: int = 0,
) -> dict[str, str]:
    """Spec 0145 — Phase 2 rounds 2+ input bundle.

    Canonical keys: ``system.task.plan_negotiation``,
    ``user_prompt.message``, per-attachment rows, ``phase1.claude``,
    ``phase1.openai``, ``prior_turns.phase2`` (the inlined transcript
    of accumulated rounds).
    """
    system_text = _strip_cache_marker(
        negotiation_turn_prompt(
            brief_content=_placeholder("brief"),
            own_draft=_placeholder("d1"),
            other_draft=_placeholder("d2"),
            prior_turns=_placeholder_prior_turns("hist"),
            agent_name=agent_name,
            other_name=other_name,
            round=round,
            soft_cap=soft_cap,
            hard_cap=hard_cap,
        )
    )
    hist_text = _inline_prior_turns(prior_turns, "Prior Phase 2 conversation turns (in order)")
    out: dict[str, str] = {"system.task.plan_negotiation": system_text}
    _emit_user_prompt_text(out, brief, attachments)
    out["phase1.claude"] = claude_draft or ""
    out["phase1.openai"] = openai_draft or ""
    out["prior_turns.phase2"] = hist_text
    return out


def drafting_input_bundle(
    *,
    brief: str,
    claude_draft: str,
    openai_draft: str,
    plan: str | None,
    prior_turns: Iterable[PriorTurn],
    attachments: Iterable[Attachment] = (),
    agent_name: str = "<agent>",
    other_name: str = "<other>",
) -> dict[str, str]:
    """Spec 0145 — Phase 3 drafting input bundle.

    Canonical keys: ``system.task.drafting``, ``user_prompt.message``,
    per-attachment rows, ``phase1.claude``, ``phase1.openai``,
    ``phase2.agreement.plan``, ``prior_turns.phase2``.
    """
    system_text = _strip_cache_marker(
        drafting_prompt(
            brief_content=_placeholder("brief"),
            own_draft=_placeholder("d1"),
            other_draft=_placeholder("d2"),
            prior_turns=_placeholder_prior_turns("hist"),
            agent_name=agent_name,
            other_name=other_name,
            agreed_plan_block=_placeholder("plan"),
            final_surfaced_disagreements=[],
        )
    )
    hist_text = _inline_prior_turns(prior_turns, "Full Phase 2 conversation")
    out: dict[str, str] = {"system.task.drafting": system_text}
    _emit_user_prompt_text(out, brief, attachments)
    out["phase1.claude"] = claude_draft or ""
    out["phase1.openai"] = openai_draft or ""
    out["phase2.agreement.plan"] = plan or ""
    out["prior_turns.phase2"] = hist_text
    return out


def review_input_bundle(
    *,
    brief: str,
    draft: str,
    prior_turns: Iterable[PriorTurn],
    attachments: Iterable[Attachment] = (),
    agent_name: str = "<agent>",
    other_name: str = "<other>",
    drafter_name: str = "<drafter>",
    round: int = 0,
    soft_cap: int = 0,
    hard_cap: int = 0,
) -> dict[str, str]:
    """Spec 0145 — Phase 4 review input bundle.

    Canonical keys: ``system.task.review``, ``user_prompt.message``,
    per-attachment rows, ``current_draft``, ``prior_turns.phase4``.
    """
    system_text = _strip_cache_marker(
        review_turn_prompt(
            brief_content=_placeholder("brief"),
            draft_content=_placeholder("draft"),
            prior_turns=_placeholder_prior_turns("histp"),
            agent_name=agent_name,
            other_name=other_name,
            drafter_name=drafter_name,
            round=round,
            soft_cap=soft_cap,
            hard_cap=hard_cap,
        )
    )
    histp_text = _inline_prior_turns(prior_turns, "Prior Phase 4 review turns (in order)")
    out: dict[str, str] = {"system.task.review": system_text}
    _emit_user_prompt_text(out, brief, attachments)
    out["current_draft"] = draft or ""
    out["prior_turns.phase4"] = histp_text
    return out


def repair_input_bundle(
    *,
    agent_name: str = "<agent>",
    phase: int = 0,
    errors: "list[str] | None" = None,
    malformed_content: str = "",
) -> dict[str, str]:
    """Spec 0145 — repair input bundle.

    Repair turns retry a malformed parse; they don't carry per-phase
    context. The bundle emits ``system.task.input`` (best-effort
    canonical fallback) and inlines the malformed turn under the
    closest matching phase's ``prior_turns.*`` key, so the read shim
    can render it inline with other turn history. Per spec 0145 §3,
    repair siblings do not get per-attachment decomposition this
    release.
    """
    system_text = _strip_cache_marker(
        repair_prompt(
            agent_name=agent_name,
            phase=phase,
            errors=errors or ["<placeholder>"],
            malformed_content=_placeholder("hist"),
        )
    )
    if phase == 0:
        prior_key = "prior_turns.phase0"
    elif phase == 4:
        prior_key = "prior_turns.phase4"
    else:
        prior_key = "prior_turns.phase2"
    return {
        "system.task.input": system_text,
        prior_key: malformed_content or "",
    }


def force_verbatim_copy_input_bundle(
    *,
    agent_name: str = "<agent>",
    other_name: str = "<other>",
    drafter_name: str = "<drafter>",
    canonical_plan: str = "",
    round: int = 0,
) -> dict[str, str]:
    """Spec 0145 — force-verbatim-copy (Phase 2 hash-drift repair) input bundle.

    Canonical keys: ``system.task.plan_negotiation``, ``phase2.agreement.plan``.
    """
    system_text = _strip_cache_marker(
        force_verbatim_copy_prompt(
            agent_name=agent_name,
            other_name=other_name,
            drafter_name=drafter_name,
            canonical_plan=_placeholder("plan"),
            round=round,
        )
    )
    return {
        "system.task.plan_negotiation": system_text,
        "phase2.agreement.plan": canonical_plan or "",
    }


# ─── Spec 0114 — Deep Research protocol prompts ───────────────────────
#
# New prompts for the canonical Deep Research methodology. These coexist
# with the legacy prompt functions above; the orchestrator wires the new
# functions in step 6 of the migration plan. Old prompts remain
# available for legacy code paths until spec 0115's shim removal.


DEEP_RESEARCH_PREAMBLE = """\
You are participating in a Deep Research run with another large language
model from a different family. Your shared goal is to critically improve
the input — research it, surface disagreements, resolve them with
evidence, and converge on a single document that is better than what
either of you could produce alone.

Two failure modes — equally bad:

- Sycophancy: agreeing because disagreement is awkward, or because the
  conversation has gone on long enough. Your job is not to be pleasant;
  it is to be useful. Do not flip to AGREED to end the loop. If you
  cannot articulate why you accept the other side's argument, do not
  accept it.

- Adversarialism: manufacturing or re-litigating differences that do
  not materially change the final document. Concede when the other
  side's evidence is stronger. The goal is the best document, not the
  longest debate. If you raise a disagreement, you must be able to
  state in one sentence how resolving it one way versus the other would
  change the final document; if you can't, drop it.

Before every turn, write — privately, in your reasoning — your strongest
objection to your own current position if you were arguing the opposite.
If you cannot articulate one, that is itself a signal you may be
acquiescing.

## Source tagging

Every material factual claim in your body prose must carry one of:

- [V] — Verified this run. Backed by a source you retrieved this run
  via web search or another tool. The URL must be one the tool returned.
- [U] — Unverified this run. From your training weights or by reasoning;
  you did not retrieve a source this run.

Being honest about [U] is more valuable than over-claiming [V]. Tagging
accurately is the goal — tagging every claim is not.

## Tracked items

You and the other agent track items across rounds. There are four
canonical categories:

- question — something you need to know that you believe the other
  agent can answer or research.
- disagreement — a substantive position where you and the other agent
  differ on what is true or what should be done.
- issue — (review phase only) a defect in the drafted document.
- comment — (review phase only) a non-defect suggestion on the drafted
  document.

Each item has a stable ID (e.g. Q-plan-c-04, D-input-g-02). The
orchestrator assigns the ID when you raise the item; you do not pick
the sequence number. Once assigned, the ID is permanent — across
rounds, across phases, across resolution.

Every item lives in one of these states:

- open — you raised it; the other agent has not responded.
- addressed — the other agent responded; you have not ratified.
- resolved — you (the raiser) accepted the response. Terminal.
- acknowledged — both of you agreed the item cannot be resolved within
  this run. Terminal. Reached by both emitting an ACKNOWLEDGE block for
  the same item in consecutive turns.
- withdrawn — you retracted it. Terminal.
- capped — the orchestrator force-closed it (you ran out of rounds or
  ran out of closeout budget). Terminal.

Every state transition you trigger must carry a non-empty reason. The
reason is required, not optional. The system rejects turns with empty
rationales.

## Evidence

When you raise an item, you declare evidence_required: true | false.
When you address an item with evidence_required: true, your response
must include one or more structured EVIDENCE records, each tied to a
real tool call you made this turn (its event_id), with the source URL,
the search query you used, and a ≥200-character excerpt of the actual
page content you consulted. The system validates each evidence record
against the turn's tool-call audit; fabricated evidence makes your
ADDRESS operation invalid.

## Output protocol

Your turn must follow the structured output protocol exactly. See the
phase-specific instructions below for the section template and the
operation block formats. Failure to follow the protocol causes the
turn to be rejected.
"""


# Canonical operation-block reference text — included in the body of
# every interaction-phase prompt so the agent has the shape of each
# block in front of it.
_OPERATION_BLOCK_REFERENCE = """\
### Operation block formats (reference)

```
### RAISE
kind: question | disagreement | issue | comment
body: |
  <the question / argument / defect / comment text>
anchor_type: quote | after | none
anchor_text: <verbatim ≤25-word span, section heading, or "">
evidence_required: true | false
> quote: <verbatim ≤25-word span when anchor_type is quote>
```

```
### ADDRESS <item-id>
response: |
  <your answer / counter-argument / acknowledgment + fix description>
evidence:
  - url: <full URL>
    title: <page title>
    search_query: <the query you used>
    fetched_at: <ISO-8601 UTC timestamp>
    evidence_event_id: <tool_call_id from this turn's tool calls>
    content_excerpt: |
      <≥200-char excerpt of the actual page body you consulted>
proposes_status: addressed | acknowledged_proposed
```

```
### RESOLVE <item-id>
reason: |
  <why you accept this resolution>
```

```
### ACKNOWLEDGE <item-id>
reason: |
  <why this item cannot be resolved within the current run>
```

```
### WITHDRAW <item-id>
reason: |
  <why you are retracting>
```

```
### REQUEST_EVIDENCE <item-id>
reason: |
  <which claim in <item-id> needs evidence and why the request is material>
```

REQUEST_EVIDENCE (spec 0149 §5.5, D08) is a mid-run response op: instead
of immediately ADDRESSing an item the other agent raised, you ask the
original author to supply evidence first. You cannot REQUEST_EVIDENCE on
your own item, and the target ``<item-id>`` must reference an item
already on the ledger.
"""


# Spec 0257 §2.2 — standing role-contract callout for the SYMMETRIC phase-2
# axis. Rendered inline immediately above the `## Status` block in both
# phase-2 round prompts (round 1 + round N). The narrative protocol body
# never named the ADDRESS/RESOLVE role split; run 20260530-175809 emitted
# 50 phase-2 ownership violations (raiser_self_address /
# resolve_from_non_addressed / agreed_with_open_addressed_items) because
# the agents disagreed about who owns/addresses/closes each ledger item.
# This one paragraph states the contract the orchestrator already enforces.
_ADDRESS_RESOLVE_ROLE_CALLOUT = (
    "**Who may ADDRESS vs RESOLVE (item-ownership contract).** The agent that "
    "RAISED an item never ADDRESSes it and never RESOLVEs it while it is "
    "`open`. The OTHER agent — the addressee — ADDRESSes it (`open → "
    "addressed`). Only then may the raiser RESOLVE / ACKNOWLEDGE / WITHDRAW "
    "it. You may NOT declare `STATUS: AGREED` while any item raised against "
    "you is still `open` and unaddressed."
)

# Spec 0257 §2.2 — phase 4 is NOT the same axis (cowork correction 3). Phase 4
# has a fixed DRAFTER = addressee, REVIEWER = raiser — an asymmetric,
# role-fixed split, unlike phase-2's symmetric raise-and-address. The phase-2
# raiser/addressee paragraph must NOT be reused verbatim here; this callout is
# framed in drafter/reviewer terms. Shipping the correct wording is
# unconditional; whether it alone zeroes the phase-4 raiser_self_address count
# is measured (§6.2), not assumed.
_ADDRESS_RESOLVE_ROLE_CALLOUT_PHASE4 = (
    "**Who may ADDRESS vs RESOLVE (drafter/reviewer contract).** The REVIEWER "
    "raises issues, disagreements, and comments against the draft; the DRAFTER "
    "ADDRESSes each one via the revision (`open → addressed`); the REVIEWER "
    "alone ratifies (RESOLVE / ACKNOWLEDGE / WITHDRAW). The DRAFTER never "
    "ADDRESSes its own surfaced items, and never RESOLVEs an item while it is "
    "`open`. Do not declare `STATUS: AGREED` while any item raised against you "
    "is still `open` and unaddressed."
)


# Spec 0217.1 §3.3 — STATUS array contract callout. The STATUS action arrays
# are the canonical ledger-op channel; the reconstructor's STATUS-pass at
# src/dual_research/ui/disagreements.py canonicalizes IDs and silently drops
# anything that isn't an ID. The wording below appears inline above every
# round-1 / round-N `## Status` block so agents stop substituting descriptive
# strings for canonical IDs (the round-01-openai descriptive-string fixture
# captured at tests/fixtures/spec_0217/phase2/round-01-openai.md:81 is the
# canonical counter-example).
_STATUS_ARRAY_CONTRACT_CALLOUT = (
    "The STATUS action arrays carry **canonical IDs only** — `D-<slug>` for "
    "disagreements and `Q-<slug>` for questions, exactly as they appear in "
    "the `### RAISE` / `### ADDRESS` / `### RESOLVE` blocks elsewhere in this "
    "turn. Do NOT substitute descriptive prose, quoted strings, or multi-line "
    "natural-language descriptions for IDs. The orchestrator parses these "
    "arrays as the canonical ledger-op channel; non-ID entries are silently "
    "dropped."
)

# Round-1 variant — agents in round 1 raise items for the first time, so the
# orchestrator assigns canonical IDs based on the `### RAISE` blocks above
# rather than the agent picking them. Same core rule, plus a one-sentence
# clarification on the surrounding prose (per spec 0217.1 §3.3).
_STATUS_ARRAY_CONTRACT_CALLOUT_ROUND1 = (
    _STATUS_ARRAY_CONTRACT_CALLOUT
    + " (In round 1 the orchestrator assigns canonical IDs based on your "
    "`### RAISE` blocks above; emit those IDs in `RAISED_THIS_TURN`.)"
)


# Spec 0218 §3.1 — STATUS-first ordering callout. Rendered in the lead-in
# prose of every negotiation / review prompt above the section list, so the
# agents understand WHY STATUS sits near the top rather than the end. STATUS
# is the smallest, most load-bearing block in the response; everything else
# is recoverable from priors if the wire truncates.
_STATUS_FIRST_ORDERING_CALLOUT = (
    "The `## Status` block sits near the top of your turn — immediately "
    "after `## Stance` — so that it always lands even if your revised "
    "draft or your raises run long. Treat it as a hard pre-commit: "
    "populate the action arrays with the canonical IDs (or planned IDs, "
    "in round 1) for everything you are about to RAISE, ADDRESS, RESOLVE, "
    "ACKNOWLEDGE, or WITHDRAW in the body below."
)


_REVIEWER_REVISION_NOTE = (
    "The REVIEWER never modifies the draft — OMIT the `## Revised draft`\n"
    "section entirely from your output. The drafter alone proposes draft\n"
    "edits via the `### REPLACE_SECTION` / `### EDIT_SECTION` /\n"
    "`### APPEND_SECTION` / `### DELETE_SECTION` /\n"
    "`### REPLACE_DRAFT_FULL` delta-op grammar (spec 0219 §3.1)."
)


def _drafter_resync_banner(errors: list[str] | None) -> str:
    """Spec 0256 §2.2 — the drafter-resync banner.

    Prepended to the next-round DRAFTER prompt when the drafter's previous
    revision no-op'd (a parse-step or apply-step fallback fired). Without it
    the drafter keeps issuing EDIT_SECTION anchors against content it
    *believed* it wrote last round — content that never landed on disk — and
    the anchors diverge round-over-round. The banner forces a re-anchor
    against the real on-disk draft inlined below.
    """
    detail = ""
    if errors:
        joined = "; ".join(errors)
        detail = f"\n\nReason the previous revision was dropped: {joined}"
    return (
        "\n\n⚠ RESYNC — YOUR PREVIOUS REVISION DID NOT APPLY. It failed to "
        "parse, or its EDIT_SECTION anchors did not match the current draft, "
        "so it was dropped. The draft inlined below is the **current on-disk "
        "draft** — it does NOT contain your last round's intended edits. "
        "Re-issue your edits against THIS exact text; do not assume any prior "
        "revision landed. Anchor only on substrings you can see verbatim in "
        "the draft below." + detail + "\n"
    )


def _drafter_revision_doctrine_v2(*, draft_headings: list[str]) -> str:
    """Spec 0219 §3.1/§3.3/§3.4/§3.5 — drafter-only section-delta doctrine
    for the phase-4 ``review_round_n`` prompt.

    Renders the literal current-draft section headings (§3.3), the four
    delta-op kinds plus the new ``### EDIT_SECTION`` surgical op (§3.5),
    the "default to EDIT_SECTION" + ``reason:``-required-on-REPLACE_SECTION
    doctrine (§3.5), and the hard-fail-on-unknown-heading rule (§3.4).
    The REVIEWER never invokes this helper; the reviewer's call site
    substitutes ``_REVIEWER_REVISION_NOTE`` instead (§3.1).
    """
    headings = list(draft_headings)
    capped = headings[:20]
    overflow = len(headings) - len(capped)
    overflow_line = f"\n- … (+{overflow} more — list truncated)" if overflow > 0 else ""
    if capped:
        headings_block = "\n".join(f"- ## {h}" for h in capped) + overflow_line
    else:
        headings_block = "- (none — the current draft has no `## ` headings yet)"
    return f"""If you are the DRAFTER and the other agent's prior turn raised
substantive items, you may revise the draft in this turn by emitting
a `## Revised draft` section in the Output below.

**The current draft's literal section headings (use ONLY these — verbatim):**

{headings_block}

Each delta op MUST target a heading from this list — taken verbatim,
no paraphrase, no renumbering, no substring drift. A
`### REPLACE_SECTION` or `### EDIT_SECTION` against an unknown heading
is a hard parse failure that consumes a repair attempt (spec 0219 §3.4).

Spec 0218 §3.2 / spec 0219 §3.5 — the revised-draft body is a sequence
of **delta operation blocks**, not a full inline re-emit. Inside the
`Revised draft` section, use:

    ### EDIT_SECTION <heading>
        ANCHOR: <a SHORT, single-line, structurally-unique substring>
        REPLACE_WITH: <new content>
    (multiple ANCHOR:/REPLACE_WITH: pairs allowed per block; applied
     in document order. Each ANCHOR must match the section's body
     exactly once — `0` matches or `>1` matches consume a repair
     attempt.)

    **Anchor contract (spec 0256 §2.3 — load-bearing):** an ANCHOR must be
    a SHORT, SINGLE-LINE, structurally-unique handle — a subsection heading
    line (e.g. `### Section 3 — Tier 2 Scoring: …`) or one distinctive
    sentence / identifier copied verbatim from the section body. Do NOT use
    multi-line bodies, table rows, or long prose blocks as anchors: a long
    literal fails silently the moment one character drifts, whereas a short
    structural handle either matches uniquely or fires a loud `>1`-match
    ambiguity error. Matching tolerates inner-whitespace runs, smart-vs-
    straight quotes, and a trailing `.`/`,`/`:`/`;`, but is otherwise exact
    — it is NOT fuzzy, so a similar-but-different anchor will NOT match. If
    a whole subsection needs rewriting, use `### REPLACE_SECTION` instead.

    ### REPLACE_SECTION <heading>
        reason: <one sentence — why a surgical EDIT_SECTION was not enough>
        <new body for the matching `## <heading>` section in the current draft>

    ### APPEND_SECTION <heading>
        <new section body to append at the end of the draft>

    ### DELETE_SECTION <heading>

    ### REPLACE_DRAFT_FULL
        <full new draft body — escape hatch for structural rewrites that
         touch more than half the sections>

**Hard rules — load-bearing:**

1. **Default to `### EDIT_SECTION`.** A 5-line typo fix is ~100 output
   tokens with EDIT_SECTION vs ~2000 with REPLACE_SECTION. The 16K
   per-turn output cap can hold several EDIT_SECTIONs but only two or
   three REPLACE_SECTIONs.
2. **Use `### REPLACE_SECTION` only when rewriting > 50% of a section,**
   and include a `reason:` line on the first non-blank line under the
   heading explaining why a surgical EDIT_SECTION was not enough.
   Missing `reason:` is a hard parse failure.
3. **`### REPLACE_DRAFT_FULL` is the only path that allows a full draft
   re-emit.** Use it only when a structural rewrite genuinely touches
   more than half the sections.
4. **OMIT the `Revised draft` section entirely** on any round where
   the prior round did not contain substantive reviewer feedback you
   intend to address by editing the draft. Re-emitting an unchanged
   draft (or restating the same content under a fresh `REPLACE_SECTION`)
   is a protocol violation.
5. Plain prose under `Revised draft` (no `### EDIT_SECTION` /
   `### REPLACE_SECTION` / `### APPEND_SECTION` / `### DELETE_SECTION` /
   `### REPLACE_DRAFT_FULL` sub-heading) is rejected as a malformed turn
   and routed to repair.

The orchestrator applies the deltas against the current `draft-vN.md`
on disk to produce `draft-v(N+1).md`. Heading match is case-insensitive
trim-equal against the literal headings listed above; any delta op
referencing a heading not present in that list is rejected as
`replace_section_unknown_heading` / `edit_section_unknown_heading`
and routed to repair (spec 0219 §3.4)."""


_DRAFTER_REVISED_DRAFT_OUTPUT_TEMPLATE = """## Revised draft         ← drafter only, if any revisions
(Delta operation blocks per spec 0218 §3.2 / spec 0219 §3.5 — default to
 `### EDIT_SECTION` for surgical edits; `### REPLACE_SECTION` with a
 `reason:` line for >50%-section rewrites; `### APPEND_SECTION` /
 `### DELETE_SECTION` for structural shape changes;
 `### REPLACE_DRAFT_FULL` as the escape hatch for full rewrites.
 OMIT this section entirely if you have no substantive draft edits
 this round.)
"""


def _status_footer_for_phase(phase: int) -> str:
    """Return the canonical status-footer template for ``phase``.

    Phase 4 includes OPEN_ISSUES / OPEN_COMMENTS / ADDRESSED_ISSUES /
    ADDRESSED_COMMENTS; phases 0 and 2 do not.
    """
    base = [
        "STATUS: IN_PROGRESS | AGREED",
        "RAISED_THIS_TURN: [<canonical-id>, ...]",
        "ADDRESSED_THIS_TURN: [<canonical-id>, ...]",
        "RESOLVED_THIS_TURN: [<canonical-id>, ...]",
        "ACKNOWLEDGED_THIS_TURN: [<canonical-id>, ...]",
        "WITHDRAWN_THIS_TURN: [<canonical-id>, ...]",
        "OPEN_QUESTIONS: <int>",
        "OPEN_DISAGREEMENTS: <int>",
    ]
    if phase == 4:
        base.extend([
            "OPEN_ISSUES: <int>",
            "OPEN_COMMENTS: <int>",
        ])
    base.extend([
        "ADDRESSED_QUESTIONS: <int>",
        "ADDRESSED_DISAGREEMENTS: <int>",
    ])
    if phase == 4:
        base.extend([
            "ADDRESSED_ISSUES: <int>",
            "ADDRESSED_COMMENTS: <int>",
        ])
    return "\n".join(base) + "\n"


def closeout_request_section(
    *,
    items: "list",
    agent_name: str,
    remaining_budget: int,
    addressed_at_me_items: "list | None" = None,
) -> str:
    """Render the ``## Closeout request`` section for a closeout-round prompt.

    ``items`` is the list of items the agent owns (raiser == agent) — the
    pre-spec-0229 surface. ``addressed_at_me_items`` (spec 0229 §2.1) is
    items the OTHER agent raised that are still ``open`` — the agent
    must emit ADDRESS blocks for each before declaring AGREED
    (addressee-obligation invariant). Both lists tolerate dicts or
    objects with ``id`` / ``kind`` / ``body`` / ``current_state``
    attributes.
    """
    def _row(it) -> str:
        if isinstance(it, dict):
            iid = it.get("id", "?")
            kind = it.get("kind", "?")
            body = it.get("body", "")
            state = it.get("current_state", "?")
            addr = it.get("addressed_by", "")
        else:
            iid = getattr(it, "id", "?")
            kind = getattr(it, "kind", "?")
            body = getattr(it, "body", "")
            state = getattr(it, "current_state", "?")
            addr = getattr(it, "addressed_by", "")
        excerpt = (body or "").strip().replace("\n", " ")[:200]
        return (
            f"- [{iid}] ({kind}, state: {state}"
            + (f", addressed by {addr}" if addr else "")
            + f"): {excerpt}"
        )

    items_listing = (
        "\n".join(_row(it) for it in items) if items else "(none — see below)"
    )

    addressed_at_me_block = ""
    addressed_at_me_items = addressed_at_me_items or []
    if addressed_at_me_items:
        addressed_listing = "\n".join(_row(it) for it in addressed_at_me_items)
        addressed_at_me_block = f"""

Addressee-obligation — items the other agent raised that you have not
yet ADDRESSed. You must emit ADDRESS blocks for each of these items
before declaring AGREED:

{addressed_listing}
"""

    return f"""\
## Closeout request

You and the other agent both emitted STATUS: AGREED in the previous
round, but the system detected non-terminal items still in the ledger.
The phase cannot converge while items are non-terminal. This is a
**closeout round** — you have a constrained job:

Items that need ratification from you ({agent_name}):

{items_listing}
{addressed_at_me_block}
Your operations this round must be only:
- RESOLVE — if you accept the response or position
- ACKNOWLEDGE — if you and the other agent should agree this is
  irreconcilable (the orchestrator transitions the item to terminal
  acknowledged only when the other agent's ACKNOWLEDGE for the same
  item lands in their next turn)
- WITHDRAW — if you no longer hold the item
- counter-argument — if the response did not move you and you want to
  flip the item back to open with rationale

You may NOT raise new items in this round. RAISE blocks will be
silently dropped and recorded as a closeout violation.

You have **{remaining_budget}** closeout rounds remaining in your
budget. If you exhaust your budget without bringing your items to
terminal state, the orchestrator will auto-cap the remaining items
(state: capped, via: ghost_cap) and the phase will converge with the
items recorded as orchestrator-forced.
"""


# ─── Phase-specific prompt builders ───────────────────────────────────


def preflight_prompt_v2(
    *,
    brief_content: str,
    agent_name: str,
    other_name: str,
) -> str:
    """Phase 0 (input) round 1 — brief critique, first pass."""
    return DEEP_RESEARCH_PREAMBLE + f"""

# Phase 0 (input): brief critique — round 1

You are agent "{agent_name}". The other agent is "{other_name}". You are
both reading the brief for the first time. Your job this round:

1. Read the brief carefully.
2. State your interpretation of what the brief is asking for — scope,
   approach, key questions. (Do not start the actual research yet; this
   phase is about agreeing on the task, not doing it.)
3. Raise any questions you have about the brief that need clarification
   (kind: question, raised in phase 0).
4. Raise any disagreements you have with how the brief is framed,
   what's in/out of scope, missing inputs, or framing flaws (kind:
   disagreement, raised in phase 0).

You will see {other_name}'s first-round critique starting in round 2,
at which point the negotiation begins — you address each other's items,
ratify your own that get addressed, and converge on a shared
AGREED_INTERPRETATION block.

{_OPERATION_BLOCK_REFERENCE}

## Inputs

""" + _inline_section("Brief", brief_content) + f"""

## Output

Produce a turn with the canonical section structure (see preamble).
{_STATUS_FIRST_ORDERING_CALLOUT}

Section breakdown for THIS round:

## Stance
(2–4 sentences: your reading of the task and the posture you're taking.)

{_STATUS_ARRAY_CONTRACT_CALLOUT_ROUND1}

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: [<canonical-id>, ...]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: <int>
OPEN_DISAGREEMENTS: <int>
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0

## Addressing items raised against me
(none — first round)

## Ratifying my own items
(none — first round)

## New items I'm raising
(RAISE blocks for each question and disagreement you have about the
 brief. Be specific, anchor with > quote: when possible.)

(No phase artifact block at round 1 — phase 0 cannot converge in round 1.)
"""


def input_negotiation_prompt_v2(
    *,
    brief_content: str,
    prior_turns: Iterable[PriorTurn],
    standing_items: str,
    agent_name: str,
    other_name: str,
    round: int,
    soft_cap: int,
    hard_cap: int,
    is_closeout_round: bool = False,
    closeout_request: str = "",
) -> str:
    """Phase 0 (input) round N≥2 — brief negotiation."""
    closeout_block = (
        ("\n" + closeout_request + "\n") if (is_closeout_round and closeout_request) else ""
    )
    return DEEP_RESEARCH_PREAMBLE + f"""

# Phase 0 (input): brief critique — round {round}

You are agent "{agent_name}". This is round {round} of phase 0
(soft cap {soft_cap}, hard cap {hard_cap}). Phase 0 converges when both
of you emit STATUS: AGREED in the same round, all items are terminal,
and your AGREED_INTERPRETATION blocks hash-match.

{_OPERATION_BLOCK_REFERENCE}

## Inputs

""" + _inline_section("Brief", brief_content) \
    + _inline_section("Standing items", standing_items or "(none)") \
    + _inline_prior_turns(prior_turns, header="Prior turns") \
    + closeout_block + f"""

## Output

Produce a turn with the canonical section structure.
{_STATUS_FIRST_ORDERING_CALLOUT}

## Stance
(2–4 sentences summarizing your position this round.)

{_STATUS_ARRAY_CONTRACT_CALLOUT}

## Status
{_status_footer_for_phase(0)}

## Addressing items raised against me
(ADDRESS block per currently-open item from {other_name} pointed at you.
 Each addresses with response body + evidence if required +
 proposes_status. ACKNOWLEDGE blocks here when you see no path
 to resolution.)

## Ratifying my own items
(For every one of your raised items currently in `addressed` state,
 emit RESOLVE, ACKNOWLEDGE, WITHDRAW, or a counter-argument that flips
 it back to open. Silent skipping is rejected. Do NOT use ADDRESS here;
 ADDRESS is reserved for the other agent's items in the "Addressing
 items raised against me" section above.)

## New items I'm raising
(RAISE blocks for genuinely new questions or disagreements. Do not
 re-raise items that are already in the ledger.)

## Phase artifact         ← only when emitting STATUS: AGREED

### AGREED_INTERPRETATION

#### Scope
- In scope:
  - <bullet>
- Out of scope:
  - <bullet>

#### Approach
<paragraph: how the research will be conducted, what stance the agents
 take, what weightings apply, what posture toward source materials>

#### Carry-forward items
- [<id>] <terminal-state>: <body> — <one-line rationale for carrying forward>
(or "(none)")
"""


def research_plan_prompt_v2(
    *,
    brief_content: str,
    agreed_interpretation: str,
    agent_name: str,
) -> str:
    """Phase 1 (research-plan) — single-shot parallel plan + thesis."""
    return DEEP_RESEARCH_PREAMBLE + f"""

# Phase 1 (research-plan): produce your research plan and initial thesis

You are agent "{agent_name}". You have completed phase 0 jointly with
the other agent and you both agreed on the AGREED_INTERPRETATION block
below. Your job in this phase is single-shot and parallel — the other
agent is producing their own plan + thesis at the same time, and you
will not see theirs until phase 2.

This is a PRODUCTION phase. You do not raise tracked items in this
phase. You do not address items. You do not emit the operation blocks
(RAISE / ADDRESS / RESOLVE / ACKNOWLEDGE / WITHDRAW). Phase 1's only
output is the plan + thesis as prose.

You will, however, continue to use inline [V] and [U] tags on material
factual claims in your body prose.

## Inputs

""" + _inline_section("Brief", brief_content) \
    + _inline_section("Agreed interpretation (from phase 0)", agreed_interpretation) + """

## Output

Produce a single markdown document with these sections (headings
verbatim):

## 1. Summary
3–5 sentences capturing your core findings and bottom-line thesis.

## 2. My thesis
1–3 sentences stating the judgment you currently believe is most
correct. If the brief is purely descriptive, state which findings you
are most confident in and which you are least confident in.

## 3. Detailed findings
The substance — organized according to the agreed scope and approach.
This is where the bulk of your phase 1 work goes. Cite sources inline.

## 4. Sources
Numbered list with URLs.

Do not include "Claims I expect the other agent might dispute" or
"Open questions" sections — those are NOT part of the new phase 1
output. Disagreements and questions are raised in phase 2, not here.
Phase 1 is your independent draft; the negotiation comes next.
"""


def plan_negotiation_round1_prompt_v2(
    *,
    brief_content: str,
    agreed_interpretation: str,
    own_plan: str,
    other_plan: str,
    agent_name: str,
    other_name: str,
) -> str:
    """Phase 2 (negotiate-plan) round 1 — raise items only."""
    return DEEP_RESEARCH_PREAMBLE + f"""

# Phase 2 (negotiate-plan): plan negotiation — round 1

You are agent "{agent_name}". The other agent is "{other_name}". You
have both produced your phase 1 plans + theses independently. Now you
read each other's work and begin the negotiation.

Round 1 is for raising items, not converging. STATUS: AGREED is not
allowed in round 1; it will be rejected.

Your job this round:

1. Read {other_name}'s phase 1 plan carefully.
2. Compare it to your own.
3. Raise questions where you need clarification about {other_name}'s
   claims, methodology, or scope (kind: question).
4. Raise disagreements where you and {other_name} take materially
   different positions on substance or framing (kind: disagreement).
5. Each raised item must have an anchor (> quote: or > after:) where
   appropriate.
6. Flag evidence_required: true on items whose resolution turns on
   factual claims that need an external source.

{_OPERATION_BLOCK_REFERENCE}

## Inputs

""" + _inline_section("Brief", brief_content) \
    + _inline_section("Agreed interpretation (from phase 0)", agreed_interpretation) \
    + _inline_section(f"{agent_name}'s phase 1 plan", own_plan) \
    + _inline_section(f"{other_name}'s phase 1 plan", other_plan) + f"""

## Output

Produce a turn with the canonical section structure.
{_STATUS_FIRST_ORDERING_CALLOUT}

## Stance
(2–4 sentences: where you and {other_name} agree, where you differ,
 what you think the biggest open questions are.)

{_STATUS_ARRAY_CONTRACT_CALLOUT_ROUND1}

{_ADDRESS_RESOLVE_ROLE_CALLOUT}

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: [<canonical-id>, ...]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: <int>
OPEN_DISAGREEMENTS: <int>
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0

## Addressing items raised against me
(none — first round)

## Ratifying my own items
(none — first round)

## New items I'm raising
(RAISE blocks. Do not flood; raise items that materially affect the
 final document, not every wording quibble. If you cannot state how
 resolving an item would change the final document, drop it.)
"""


def plan_negotiation_round_n_prompt_v2(
    *,
    brief_content: str,
    agreed_interpretation: str,
    own_plan: str,
    other_plan: str,
    prior_turns: Iterable[PriorTurn],
    standing_items: str,
    agent_name: str,
    other_name: str,
    round: int,
    soft_cap: int,
    hard_cap: int,
    is_closeout_round: bool = False,
    closeout_request: str = "",
) -> str:
    """Phase 2 (negotiate-plan) round N≥2."""
    closeout_block = (
        ("\n" + closeout_request + "\n") if (is_closeout_round and closeout_request) else ""
    )
    return DEEP_RESEARCH_PREAMBLE + f"""

# Phase 2 (negotiate-plan): plan negotiation — round {round}

You are agent "{agent_name}". This is round {round} of phase 2
(soft cap {soft_cap}, hard cap {hard_cap}). Phase 2 converges when
both of you emit STATUS: AGREED in the same round, all items are
terminal, your AGREED_PLAN blocks hash-match, and you both name the
same DRAFTER.

{_OPERATION_BLOCK_REFERENCE}

## Inputs

""" + _inline_section("Brief", brief_content) \
    + _inline_section("Agreed interpretation (from phase 0)", agreed_interpretation) \
    + _inline_section(f"{agent_name}'s phase 1 plan", own_plan) \
    + _inline_section(f"{other_name}'s phase 1 plan", other_plan) \
    + _inline_section("Standing items", standing_items or "(none)") \
    + _inline_prior_turns(prior_turns, header="Prior turns") \
    + closeout_block + f"""

## Output

Produce a turn with the canonical section structure.
{_STATUS_FIRST_ORDERING_CALLOUT}

## Stance

{_STATUS_ARRAY_CONTRACT_CALLOUT}

{_ADDRESS_RESOLVE_ROLE_CALLOUT}

## Status
{_status_footer_for_phase(2)}

## Addressing items raised against me
(ADDRESS blocks for every {other_name} item pointed at you in `open`
 state. Include evidence records when evidence_required: true. If you
 see no path to resolution, ACKNOWLEDGE in this section.)

## Ratifying my own items
(For every item you raised that's in `addressed` state: RESOLVE,
 ACKNOWLEDGE, WITHDRAW, or counter-argument. No silent skips. Do NOT
 use ADDRESS here; ADDRESS is reserved for the other agent's items in
 the "Addressing items raised against me" section above.)

## New items I'm raising
(Only genuinely new items.)

## Phase artifact         ← only when emitting STATUS: AGREED

### AGREED_PLAN

#### Sections
1. Title: <section title>
   Key claims:
   - <claim>
   - <claim>
2. ...

#### Carry-forward items (from phase 2)
- [<id>] <terminal-state>: <body> — <where this appears in the final document>
(or "(none)")

#### Drafter
DRAFTER: claude | openai
"""


def drafting_prompt_v2(
    *,
    brief_content: str,
    agreed_interpretation: str,
    own_plan: str,
    other_plan: str,
    agreed_plan: str,
    carry_forward_items: "list",
    prior_phase2_turns: Iterable[PriorTurn],
    agent_name: str,
    other_name: str,
) -> str:
    """Phase 3 (draft) — single-shot unified document by the drafter."""
    def _fmt_cf(items: "list") -> str:
        rows: list[str] = []
        for it in items or []:
            if isinstance(it, dict):
                iid = it.get("id", "?")
                state = it.get("current_state", "?")
                body = it.get("body", "")
                kind = it.get("kind", "?")
            else:
                iid = getattr(it, "id", "?")
                state = getattr(it, "current_state", "?")
                body = getattr(it, "body", "")
                kind = getattr(it, "kind", "?")
            rows.append(f"- [{iid}] ({kind}, state: {state}): {body}")
        return "\n".join(rows) if rows else "(none)"

    return DEEP_RESEARCH_PREAMBLE + f"""

# Phase 3 (draft): produce the unified document

You are agent "{agent_name}", chosen as the drafter at the conclusion of
phase 2. Your job is single-shot: produce the unified document
following the AGREED_PLAN exactly in section order and topic.

This is a PRODUCTION phase. You do not raise tracked items here. You
do not emit operation blocks. The other agent does not run this phase.

The carry-forward items from phase 2 (terminal-not-resolved questions
and disagreements that need to appear in the final document) must each
be rendered in the appropriate section of your output:

- terminal `acknowledged` disagreements → "## Disagreements left open"
  section, one subsection per item (`### <id>: <short title>`) with
  both positions and the agreed treatment in the final document.
- terminal `acknowledged` questions → "## Open questions" section,
  enumerated.
- terminal `capped` items → same sections as `acknowledged`, marked as
  such with the orchestrator-generated rationale.

## Inputs

""" + _inline_section("Brief", brief_content) \
    + _inline_section("Agreed interpretation (from phase 0)", agreed_interpretation) \
    + _inline_section(f"{agent_name}'s phase 1 plan", own_plan) \
    + _inline_section(f"{other_name}'s phase 1 plan", other_plan) \
    + _inline_section("AGREED_PLAN (hash-verified, verbatim from phase 2)", agreed_plan) \
    + _inline_section("Carry-forward items (from phase 2)", _fmt_cf(carry_forward_items)) \
    + _inline_prior_turns(prior_phase2_turns, header="Prior phase 2 turns") + """

## Output

Produce a single markdown document following the agreed plan section
order. Required structure:

## 1. Summary
3–5 sentences.

## 2. Findings
The merged substance — follow the agreed plan section by section.

## 3. Disagreements left open
One subsection per carry-forward disagreement (### <id>: <title>),
containing the canonical treatment from the agreed plan's
carry-forward items list.

## 4. Open questions
Numbered list of carry-forward questions with their IDs.

## 5. Sources
Merged numbered list with URLs. Reconcile duplicate citations across
the two phase 1 plans.

## 6. Confidence ledger
| Claim | Tag | Signal | Source notes |

Material claims for the ledger are those tied to FSD entries, those
flagged in phase 2 evidence reports, and any other claim that
materially affects the final recommendation. Non-material claims are
omitted.

Favour positions with stronger evidence regardless of which agent
held them. Preserve uncertainty honestly — do not smooth it away to
make the document sound more settled than it is.
"""


def review_round1_prompt_v2(
    *,
    brief_content: str,
    draft_content: str,
    drafter_name: str,
    agent_name: str,
    other_name: str,
) -> str:
    """Phase 4 (review-draft) round 1 — raise items only."""
    role = "DRAFTER" if agent_name == drafter_name else "REVIEWER"
    return DEEP_RESEARCH_PREAMBLE + f"""

# Phase 4 (review-draft): cross-review — round 1

You are agent "{agent_name}", acting as {role} in this phase. The draft
is by {drafter_name}. You are both reading the draft for the first time
in the review phase.

Round 1 is for raising items, not converging. STATUS: AGREED is not
allowed in round 1 and will be rejected.

Allowed categories in this phase: question, disagreement, issue,
comment. Raise items you genuinely consider material:

- question — clarification needs about the draft.
- disagreement — substantive points where you disagree with the draft's
  framing or position.
- issue — defects in the draft (incorrect claim, missing required
  section, broken reasoning, etc.).
- comment — non-defect suggestions (could be clearer, could be
  reorganized, etc.).

{_OPERATION_BLOCK_REFERENCE}

## Inputs

""" + _inline_section("Brief", brief_content) \
    + _inline_section("Draft (current version)", draft_content) + """

## Output

Produce a turn with the canonical section structure.
""" + _STATUS_FIRST_ORDERING_CALLOUT + """

## Stance
(2–4 sentences: your overall reaction to the draft. The UI uses this
 as the timeline-card TL;DR.)

""" + _STATUS_ARRAY_CONTRACT_CALLOUT_ROUND1 + "\n\n" + _ADDRESS_RESOLVE_ROLE_CALLOUT_PHASE4 + """

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: [<canonical-id>, ...]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: <int>
OPEN_DISAGREEMENTS: <int>
OPEN_ISSUES: <int>
OPEN_COMMENTS: <int>
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
ADDRESSED_ISSUES: 0
ADDRESSED_COMMENTS: 0

## Addressing items raised against me
(none — first round of this phase)

## Ratifying my own items
(none — first round)

## New items I'm raising
(RAISE blocks. Anchor with > quote: or > after: when applicable.
 evidence_required flag per item.)
"""


def review_round_n_prompt_v2(
    *,
    brief_content: str,
    draft_content: str,
    drafter_name: str,
    prior_turns: Iterable[PriorTurn],
    standing_items: str,
    agent_name: str,
    other_name: str,
    round: int,
    soft_cap: int,
    hard_cap: int,
    draft_version: int,
    is_closeout_round: bool = False,
    closeout_request: str = "",
    draft_headings: list[str] | None = None,
    prior_revision_noop: bool = False,
    prior_revision_noop_errors: list[str] | None = None,
) -> str:
    """Phase 4 (review-draft) round N≥2.

    Spec 0219 §3.1/§3.3 — ``draft_headings`` is the literal list of
    ``## `` headings (without the ``## `` prefix) from the current
    on-disk draft. The drafter sees them inlined in the doctrine so
    every delta op targets a real heading; the reviewer never sees
    the doctrine block (the reviewer is told to OMIT the ``## Revised
    draft`` section entirely).

    Spec 0256 §2.2 — when ``prior_revision_noop`` is set (DRAFTER only),
    a banner is prepended telling the drafter its previous revision did
    NOT apply, so it re-anchors against the real on-disk draft below
    rather than the draft it believed it produced.
    """
    role = "DRAFTER" if agent_name == drafter_name else "REVIEWER"
    closeout_block = (
        ("\n" + closeout_request + "\n") if (is_closeout_round and closeout_request) else ""
    )
    if role == "DRAFTER":
        revision_doctrine = _drafter_revision_doctrine_v2(
            draft_headings=list(draft_headings or [])
        )
        revision_output_template = _DRAFTER_REVISED_DRAFT_OUTPUT_TEMPLATE
    else:
        revision_doctrine = _REVIEWER_REVISION_NOTE
        revision_output_template = ""
    resync_banner = (
        _drafter_resync_banner(prior_revision_noop_errors)
        if (role == "DRAFTER" and prior_revision_noop)
        else ""
    )
    return DEEP_RESEARCH_PREAMBLE + resync_banner + f"""

# Phase 4 (review-draft): cross-review — round {round}

You are agent "{agent_name}", acting as {role}. The draft is by
{drafter_name}, currently at version v{draft_version}. This is round
{round} (soft cap {soft_cap}, hard cap {hard_cap}).

Phase 4 converges when both of you emit STATUS: AGREED in the same
round, all items are terminal, your AGREED_DRAFT_ACCEPTANCE blocks
agree on the same draft_version (the orchestrator anchors the version
pointer to the on-disk draft), and the drafter has not revised the
draft in this round.

{revision_doctrine}

{_OPERATION_BLOCK_REFERENCE}

## Inputs

""" + _inline_section("Brief", brief_content) \
    + _inline_section(f"Draft (v{draft_version})", draft_content) \
    + _inline_section("Standing items", standing_items or "(none)") \
    + _inline_prior_turns(prior_turns, header="Prior turns") \
    + closeout_block + f"""

## Output

Produce a turn with the canonical section structure.
{_STATUS_FIRST_ORDERING_CALLOUT}

## Stance

{_STATUS_ARRAY_CONTRACT_CALLOUT}

{_ADDRESS_RESOLVE_ROLE_CALLOUT_PHASE4}

## Status
{_status_footer_for_phase(4)}

## Addressing items raised against me
(ADDRESS blocks for every {other_name} item in `open` state pointed at
 you. Include evidence records when evidence_required: true. ACKNOWLEDGE
 in this section if you see no path. ADDRESS targets ONLY {other_name}'s
 items — NEVER your own. You cannot ADDRESS an item you raised; doing so
 is dropped as a self-address protocol violation.)

## Ratifying my own items
(For your OWN items in `addressed` state, emit RESOLVE / ACKNOWLEDGE /
 WITHDRAW / counter-argument — NOT ADDRESS. ADDRESS is reserved for
 {other_name}'s items in the "Addressing items raised against me" section
 above; to act on an item you raised, use one of RESOLVE / ACKNOWLEDGE /
 WITHDRAW here.)

## New items I'm raising
(Only genuinely new items.)

{revision_output_template}
## Phase artifact         ← only when emitting STATUS: AGREED

### AGREED_DRAFT_ACCEPTANCE

draft_version: v<N>
endorsement: |
  <one sentence on why this draft satisfies the brief>
"""
