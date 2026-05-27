---
spec: 0091
title: Phase 4 drafter-engagement gate (close the round-1 sycophantic-APPROVED loophole)
label: new-feature
version-bump: MINOR
status: proposed
target-version: 0.72.0
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0091 — Phase 4 drafter-engagement gate

## Context

Run `27de` (`20260518-083618-backend-language-choice`) surfaced a
class of failure that only became clearly visible after spec 0090
fixed the parser blindness: **Claude as drafter emits `STATUS:
APPROVED` with `OPEN_ISSUES: 0` on round 1 of Phase 4**, before
reading any reviewer (GPT) feedback at all. He then re-emits
`APPROVED/0` every round he writes successfully (r2, r4) — never
engaging with GPT's 5+ open issues from round 1.

Concretely from `27de` Phase 4 with the post-spec-0090 parser:

```
P4 r1: claude=APPROVED/oi=0   openai=REVIEWING/oi=5   approved=False
P4 r2: claude=APPROVED/oi=0   openai=REVIEWING/oi=5   approved=False
P4 r3: claude=None/oi=None    openai=REVIEWING/oi=2   approved=False
P4 r4: claude=APPROVED/oi=0   openai=REVIEWING/oi=3   approved=False
P4 r5: claude=None/oi=None    openai=REVIEWING/oi=3   approved=False
```

Claude's r1 Issue ledger reads, verbatim:

> "(No prior issues. No new issues raised this round — the draft is
> the product of consensus reached in Phase 2, and this is the first
> Phase 4 review turn.) **Issue ledger: 0 open items.**"

That reasoning is plausible — there ARE no prior P4 issues in r1, and
the draft did come out of a Phase 2 agreed plan — but in practice it
becomes a structural license for the drafter to disengage from review
entirely. Phase 4 exists to catch what Phase 2 didn't; if the drafter
treats the agreed plan as a license to approve sight-unseen, that
defeats the cross-review.

The mirror case in Phase 2 is already prevented structurally: the
convergence module's `assert_well_formed_round1_turn` exempts round 1
from the strict-plan-turn check precisely because **round 1 cannot
agree** ([convergence.py:51-52](../src/dual_research/protocol/convergence.py)).
The orchestrator's convergence checks only run for `r > 1`. Phase 4
has no equivalent rule — round 1 can terminate as APPROVED, and the
test data shows the drafter exploits this.

This is NOT the reviewer's failure (GPT correctly opens issues from
r1) and NOT a parser failure (spec 0090 confirmed the ledger
correctly counts). It's a drafter behaviour failure that the
protocol structure currently permits.

### Why the existing anti-sycophancy text isn't enough

`review_turn_prompt` already carries a `Anti-sycophancy procedure`
block ([prompts.py:599-601](../src/dual_research/protocol/prompts.py)):

> 1. Before you decide whether to approve, write — privately, in your
>    reasoning — your strongest objection to the current draft if you
>    were arguing the opposite position. If you cannot articulate any
>    objection, that is evidence you may be acquiescing.
> 2. Before you concede a held comment, name the specific change in
>    the draft (or the specific drafter argument) that resolved it.

The procedure is a "before you decide" check. It's soft language.
Claude in 27de's r1 didn't follow it. Soft language has a known
adherence rate; structural prevention has 100%.

Phase 2 demonstrates the pattern: it pairs a strong prompt
(anti-sycophancy + format requirements) with a STRUCTURAL gate
(round 1 cannot agree). Phase 4 should do the same.

## Proposed change

Two coordinated mechanisms — prompt nudge plus orchestrator gate —
so the fix is robust against prompt-adherence drift.

### § A — Phase 4 round-1 cannot-approve gate (orchestrator)

Add a one-line gate to [`orchestrator/phase4.py`](../src/dual_research/orchestrator/phase4.py)'s
convergence-check site (around line 360-368):

```python
try:
    approved = is_review_approved(
        claude_text, openai_text,
        round=r,
        ledger_open_count=ledger_open_p4,
    )
except ProtocolParseError:
    approved = False

# Spec 0091 § A — Phase 4 cannot terminate on round 1.
# Mirrors the Phase 2 "round 1 cannot agree" rule. Prevents the
# drafter from emitting APPROVED before either side has had a chance
# to engage with the draft in this phase.
if r == 1 and approved:
    approved = False
    print(
        "[phase 4] round 1: ignoring APPROVED — round 1 cannot "
        "terminate Phase 4 (spec 0091 § A). Loop continues.",
        flush=True,
    )
```

When this fires, the orchestrator simply continues to round 2. The
agent's turn file is preserved on disk (no rewrite), the round-
complete event is still published with `approved=False`, and the
loop carries on.

This is the structural protection. It can't be bypassed by prompt
non-adherence because it lives in the orchestrator, not the
prompt.

### § B — Drafter-engagement prompt requirement (prompts)

Add a new section to [`review_turn_prompt`](../src/dual_research/protocol/prompts.py)
inserted between the existing `Anti-sycophancy procedure` block and
the `## Inputs` section:

```
Drafter engagement requirement (drafter only; spec 0091):
If you are the DRAFTER, you may NOT emit `STATUS: APPROVED` until you
have written at least ONE round whose `## Issue ledger` section
contains a non-trivial entry — either accepting / rejecting / resolving
an open issue raised by {other_name}, OR raising a new issue you
identified on your own re-read of the draft. A round-1 turn that says
"(no prior issues, no new issues, 0 open)" is structurally invalid as
an APPROVED turn — the orchestrator will reject it and you'll be
asked to take the round again. The first round of Phase 4 is for
engagement, not approval.

Even when you genuinely believe the draft is ready, the round-1
expectation is to demonstrate engagement: re-read the draft from
{other_name}'s perspective, list at least one issue you'd hold
against it, then explain in your turn body why it resolves to
non-blocking. APPROVED becomes available from round 2 onward.
```

This is the prompt-level nudge. It tells the agent what's expected
before they get rejected by the orchestrator gate, reducing wasted
turns.

### § C — Validator strengthening (dropped during implementation)

Originally proposed: extend `assert_well_formed_review_turn` to raise
`ProtocolParseError` on `(round=1, status=APPROVED)`, so parse-with-
repair fires its retry loop and the agent gets one explicit chance
to revise before the orchestrator's § A backstop fires.

**Dropped during implementation** — it conflicted with § A. The
existing orchestrator catches `ProtocolParseError` and BREAKS the
loop with `parse_failure = True`. A stubborn agent that re-emits
APPROVED on retry would trigger parse-failure abort instead of
falling through to § A's silent downgrade. Net effect: § C made
the failure mode WORSE for non-compliant agents.

§ A alone covers the case cleanly: r1 APPROVED is downgraded, the
loop continues, the prompt's § B nudge has done its job ahead of
time. The cost of dropping § C is one extra LLM round when the
agent emits r1 APPROVED (vs an earlier retry catching it within
the same round). That cost is acceptable; the avoided abort-on-
stubborn-agent is more important than a one-round speedup.

### § D — Cache-bust + version bump

- `?v=0092` → `?v=0093` across `index.html` (defensive; no static
  asset changes here).
- Version `0.71.0` → `0.72.0` (MINOR per the `new-feature` label).

## Out of scope

- **Phase 4 parse-failure cascade.** Claude's r3 and r5 outputs on
  27de were malformed (parse-failures). That's a separate failure
  class — the parse-with-repair loop already exists for it; the
  question is why Claude regressed mid-phase. Out of scope here;
  needs its own investigation once new post-spec-0091 runs accumulate.
- **Reviewer sycophancy.** GPT's behaviour in 27de's Phase 4 was
  appropriate (continued to surface issues). No evidence of mirror-
  sycophancy from the reviewer side. If post-spec-0091 data shows
  the REVIEWER approving prematurely, that's a separate gate.
- **`STUCK_AGREED_K` tightening.** Defer per the spec-0090 follow-up
  analysis. With the parser fixed and § A landed, the K=2 default
  remains appropriate.
- **Backfilling 27de's deadlock with a re-run.** The agents and the
  underlying model versions are external; we don't replay. Future
  runs benefit from the fix.
- **Mandatory drafter pause / cool-down.** Some systems gate
  agreement on time-elapsed-since-draft. Out of scope; the round-
  count gate is the simpler structural mechanism.

## Test plan

### Unit

- [ ] `tests/orchestrator/test_phase4_round1_gate.py` (new) — call
      the convergence-check branch with `r=1` and a mock pair where
      `is_review_approved` returns True; assert `approved` is set
      to False after the gate and `phase4_round_complete` is
      published with `approved=False`.
- [ ] `tests/orchestrator/test_phase4_round1_gate.py` — call with
      `r=2` and same input; assert `approved=True` (gate doesn't
      fire past r1).
- [ ] `tests/protocol/test_review_turn_prompt_drafter_engagement.py`
      (new) — render `review_turn_prompt` with `drafter_name ==
      agent_name`; assert the "Drafter engagement requirement"
      paragraph is present. Render with `drafter_name !=
      agent_name`; same paragraph still present (the rule is
      visible to both — the drafter to follow it, the reviewer to
      know it exists).
- [ ] If § C lands: `tests/protocol/test_convergence_validator.py`
      — `assert_well_formed_review_turn` raises
      `ProtocolParseError` for `(round=1, status=APPROVED)`;
      passes for `(round=2, status=APPROVED)` and any
      `STATUS: REVIEWING`.

### Replay

- [ ] `tests/orchestrator/test_27de_phase4_replay.py` (new) —
      materialize 27de Phase 4 round 1 turn files into a tmp
      session; run the orchestrator's convergence-check path
      manually (not the full orchestrator — would need agent
      mocks). Assert `approved=False` even though Claude's r1
      file has `STATUS: APPROVED`.

### Live smoke (post-deploy)

- [ ] Fire a fresh `dual-research run` via the `dual-research-run`
      skill. Watch the Phase 4 sequence. Confirm:
  - Round 1 never terminates the loop, regardless of what either
    agent emits.
  - From round 2 onward, agents can converge normally.
  - The strengthened prompt is visible in the round-1 input bundle
    when inspected via the UI's Agent Input panel.
- [ ] On the same fresh run, manually inspect the drafter's r1
      turn body: it should NOT contain "(no issues, 0 open)"
      shape — the prompt nudge should have moved them to engage.

### Existing suite

- [ ] `uv run pytest tests/ -q` — current 889 + new tests, all green.
- [ ] `fly deploy` from merged main; `/api/health` reports 0.72.0.

## Risks

- **§ A delays a genuinely-ready draft by one round.** True. The
  cost is one extra review round (~1-2 minutes of agent time, single-
  digit cents of model cost). The benefit is closing a structural
  loophole that produced a $9.86 deadlock on 27de. Net: trivially
  positive.
- **§ B prompt text is verbose.** Adds ~10 lines to the review
  prompt. Token cost is negligible relative to the rest of the
  prompt (~4-8 KB).
- **§ C validator might be over-zealous on first-round legitimate
  REVIEWING turns that happen to also pass the APPROVED structural
  check.** Mitigation: the validator only rejects when STATUS is
  explicitly APPROVED. REVIEWING turns are unaffected. And the
  retry loop gives the agent one chance to fix it.
- **Future variation: Phase 4 with very small drafts where round
  1 review is genuinely thorough and concludes APPROVED honestly.**
  Possible but unobserved. The structural gate is conservative; the
  one-round cost is small enough not to warrant a complex
  "minimum-engagement-quality" heuristic. Revisit if production
  shows persistent one-round approvals on small drafts.
- **Interaction with the Phase 4 resume-replay path.** When the
  orchestrator resumes a run mid-Phase-4 and both round-1 files
  already exist with APPROVED, the existing replay code at
  [phase4.py:124-138](../src/dual_research/orchestrator/phase4.py)
  checks `is_review_approved` and breaks if true. Spec 0091 § A
  needs to apply there too — add the `r == 1 and approved → False`
  gate to both code paths.

## Open questions

- **Should the round-1 gate also apply to REVIEWING turns that
  happen to have OPEN_ISSUES: 0?** Recommend no — the issue is
  APPROVED specifically, since that's what terminates the loop.
  A REVIEWING turn with no issues is honest (and rare); it just
  forces the next round.
- **Should § C land in this spec or wait?** Recommend land it.
  The 3-line cost is low; the cost-saving from earlier rejection
  is real; it's defense in depth.
- **Phase 4 minimum-rounds-for-APPROVED beyond just rejecting
  round 1.** Could go further: require at least one prior round
  where the drafter raised at least one issue. Out of scope here;
  the round-1 gate is the minimal structural fix.
- **What about Phase 2 mirroring this back?** Phase 2 already has
  "round 1 cannot agree" baked into `assert_well_formed_round1_turn`.
  This spec brings Phase 4 to parity.
