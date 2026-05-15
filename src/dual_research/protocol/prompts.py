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
        + _inline_section(f"Your Phase 1 draft ({agent_name})", own_draft)
        + _inline_section(f"{other_name}'s Phase 1 draft", other_draft)
        + f"""
## Task
Produce your round-1 turn with these sections (headings verbatim):

## Diff vs {other_name}'s Phase 1
Numbered list. For each material difference between your draft and theirs: state what you said, what they said, the type of difference (factual / interpretive / scope / framing), and whether it is substantive, minor, or already resolved by re-reading. Do not list trivial wording differences; only differences a reader would care about.

For each **substantive** diff item, assign a stable ID of the form D-1, D-2, … (starting from 1, in first-appearance order). These IDs persist through all subsequent Phase 2 rounds, Phase 3, and Phase 4. The other agent will reference and reconcile these IDs starting in round 2.

## Gaps I researched this round
Numbered list. For each: which diff item it addresses, what you searched / read, what you found, and how your position has shifted (or not) in light of it. Cite sources with [n] tags and add them to Sources.

## Updated position
5–10 sentences. State your current best answer to the brief, post-research. This may differ from your Phase 1 thesis. If it does, name the specific evidence that changed your mind.

## Open questions for {other_name}
Numbered list. Genuine, substantive questions whose resolution is needed before we can converge on a plan. Each must be one {other_name} can actually answer from their draft or from research they would plausibly do — not rhetorical.

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
) -> str:
    return (
        COMMON_PREAMBLE
        + f"""
# Phase 2 round {round}: plan negotiation (soft cap {soft_cap}, hard cap {hard_cap})

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
        + _inline_section(f"Your Phase 1 draft ({agent_name})", own_draft)
        + _inline_section(f"{other_name}'s Phase 1 draft", other_draft)
        + _inline_prior_turns(prior_turns, "Prior Phase 2 conversation turns (in order)")
        + f"""
## Task
Produce your turn for round {round} with these sections (headings verbatim):

## Answers to {other_name}'s open questions
Address every numbered question {other_name} listed in their most recent turn. If their last turn had none, write "(none)".

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

## Plan as I currently propose it
Bullet list of sections the final document should contain. Incorporate {other_name}'s good points from prior rounds; hold the line only where evidence supports it.

## Substantive disagreements I'm holding
Numbered list. Use stable D-N IDs assigned in round 1 (or introduced in this round if genuinely new). For each entry with status `open`:
- (a) D-N ID and short title, (b) your position, (c) {other_name}'s position, (d) why you are not yet conceding (cite specific evidence or argument), (e) materiality — one sentence on how this disagreement would change the final document. If you cannot state (e), drop the item as immaterial.

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
        + _inline_section(f"Your Phase 1 draft ({agent_name})", own_draft)
        + _inline_section(f"{other_name}'s Phase 1 draft", other_draft)
        + plan_block_section
        + fsd_section
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
) -> str:
    role = "DRAFTER" if agent_name == drafter_name else "REVIEWER"
    return (
        COMMON_PREAMBLE
        + f"""
# Phase 4 round {round}: review (soft cap {soft_cap}, hard cap {hard_cap})

You are agent "{agent_name}", in your role as {role} (drafter or reviewer). The drafter ({drafter_name}) wrote the current draft. You and "{other_name}" are converging on a final version. The loop ends when both of you emit `STATUS: APPROVED` with `OPEN_ISSUES: 0` in the same round.

Two failure modes — equally bad:
- **Sycophancy:** approving because the loop has gone on long enough, not because the draft is right. By round 3+ you are jointly invested in the draft and the natural pull is toward agreement. Resist this. The user does not benefit from a draft you secretly think is flawed.
- **Adversarialism / scope creep:** demanding restructures and new sections that were not in the agreed plan. Phase 2 produced the plan; Phase 4 reviews execution against it, not the plan itself. Unless a clear flaw emerged that the plan did not anticipate, do not relitigate the plan here.

Anti-sycophancy procedure (apply before every turn; recommended structural mitigation, not yet directly validated for this exact configuration):
1. Before you decide whether to approve, write — privately, in your reasoning — your strongest objection to the current draft if you were arguing the opposite position. If you cannot articulate any objection, that is evidence you may be acquiescing.
2. Before you concede a held comment, name the specific change in the draft (or the specific drafter argument) that resolved it.

## Inputs

"""
        + _inline_section("Brief", brief_content)
        + _inline_section("Current draft", draft_content)
        + _inline_prior_turns(prior_turns, "Prior Phase 4 review turns (in order)")
        + f"""
## Task
Produce your turn for round {round} with these sections (headings verbatim):

## Answers to {other_name}'s prior comments
Address every comment/question {other_name} raised in their most recent turn. "(none — first round)" if applicable.

## Issue ledger (delta + currently open)
Numbered list. Include (a) all currently open issues with stable IDs and current status, (b) new issues raised this round with stable IDs assigned by the agent who raises them, (c) status changes for previously raised issues — status one of `open` / `accepted` / `rejected` / `resolved`, each with a one-sentence reason. Resolved historical issues can be referenced by ID rather than re-emitted in full. The DRAFTER must answer every prior `open` issue this round as accepted / rejected / resolved / still-open; silent skipping is not allowed.

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

## Disagreement carryover audit
Required in round 1 and in any turn emitting STATUS: APPROVED. Optional in other rounds.

- Final-surfaced disagreements from Phase 2: for each FSD-N ID — state present in draft / missing / distorted (one sentence).
- Resolved disagreements that re-emerged: list of D-N IDs the reviewer believes were resolved in Phase 2 but appear unresolved or distorted in the draft, or "(none)".
- New disagreements raised during review: list of new D-N IDs introduced since Phase 2, with status, or "(none)".

## Substantive disagreements I'm holding
Numbered list. For each: your position, {other_name}'s position, why you are holding, and one-sentence materiality test (how would this change the final document?). If you cannot state materiality, drop the item.

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
