---
spec: 0089
title: Convergence escape hatches for stuck-AGREED loops (canonical-FSD synthesis, stuck-AGREED escape valve, hard ledger feedback)
label: new-feature
version-bump: MINOR
status: proposed
target-version: 0.70.0
created: 2026-05-18
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0089 — Convergence escape hatches for stuck-AGREED loops

## Context

Two real production runs from the 2026-05-18 audit surfaced a class
of failure where **both agents emit `STATUS: AGREED` for many
consecutive rounds, yet the orchestrator never exits the
negotiation loop**. The agents are done; the orchestrator's
secondary convergence gates are not satisfied. Neither side has a
feedback channel that surfaces the disagreement, so the loop burns
to the hard cap.

**Run `2c4f`** (`20260518-065852-…-briefing-for-dual-research`):
Phase 2 ran 12 rounds and **deadlocked at the hard cap with both
agents in mutual `AGREED` for 10 consecutive rounds** (rounds 3
through 12). Across every one of those rounds: `OPEN_QUESTIONS: 0`,
`BLOCKING_DISAGREEMENTS: 0`, `FINAL_SURFACED_DISAGREEMENTS: 1`,
matching drafter (`claude`), matching normalised plan hash
(`307c96a4…` from r4 onward), matching FSD IDs (`['FSD-1']`). The
single failing gate: the AGREED_PLAN block lacked the required
`## Final-surfaced disagreements (canonical)` sub-section. The
existing escape hatches (`all_substantive_gates_pass_except_drafter`,
`all_substantive_gates_pass_except_plan_hash`) didn't fire because
drafters MATCHED and hashes MATCHED. There's no third escape for
"matched everything except the canonical sub-section." Cost: 12
turn pairs × prod-tier models = $5.23 burned on a deadlock that
should have been a 3-round agreement.

**Run `27de`** (`20260518-083618-backend-language-choice`): Phase 2
got mutual `AGREED` at round 4, hit a hash-drift escape (spec 0032)
that fired its repair, the repair produced an aligned plan, then
**ran two more rounds (r5, r6) before exiting** via spec-0032's
second-detection canonical-promotion. Root cause for the extra
rounds: the ledger cross-check (spec 0043 D7) blocked convergence
because the system-derived ledger reported 10 still-open questions
even though the agents self-reported `OPEN_QUESTIONS: 0`. The
agents had no way to learn what the orchestrator was unhappy about
— the existing standing-items section (`build_standing_items_section`)
explicitly describes itself as "informational, not output-required"
and uses soft language ("Address each in your reply"). The agents
re-emitted identical AGREED messages.

**Common pattern (the framing for this spec):** when agents
self-report `AGREED` with all surface signals aligned, the
orchestrator's secondary gates (canonical FSD section presence;
ledger cross-check) are designed to be conservative — they reject
agreement when the system has *additional* evidence the agents are
glossing over something. The problem isn't that the conservatism is
wrong in principle; it's that:

1. There's no escape hatch when one secondary gate is the *only*
   thing failing and the failure is structurally fixable from
   existing on-disk content (the canonical-FSD case).
2. There's no escape hatch when the secondary gate keeps firing
   round after round but the agents won't change their behaviour
   (the ledger-mismatch case).
3. The agents aren't told what the secondary gates are checking, so
   they can't adapt even when they would.

This spec adds escape hatches for cases (1) and (2) and tightens
the agent-facing prompt for case (3). All three are scoped to
Phase 2 and Phase 4 symmetrically (the same convergence shape
applies in both phases).

**Out of scope** (called out explicitly so this spec doesn't grow):
the Phase 4 "Claude approves on round 1 while GPT genuinely finds
issues" pattern surfaced by the same investigation is a different
failure mode (sycophancy + downstream parse-failure cascade) and
gets its own spec. Run `27de`'s `exit_code: 52` is from that
pattern, not from the stuck-AGREED loop addressed here.

## Proposed change

Three additions, in dependency order. Each is self-contained and
gated independently so they can be evaluated in isolation.

### § A — Canonical-FSD synthesis escape (closes the 2c4f deadlock)

**Bug:** when both agents emit AGREED + matching drafter + matching
plan hash + matching FSD IDs but neither agent includes the required
`## Final-surfaced disagreements (canonical)` sub-section inside
their AGREED_PLAN block, `is_plan_agreed` returns False forever and
no existing escape hatch fires.

**Insight:** the canonical sub-section is a strict subset of the
standalone `## Final-surfaced disagreements` section that both
agents DO emit (4 fields vs 8 fields per FSD-N; see
`prompts.py:374-388` vs `prompts.py:410-421`). We can synthesize
the canonical section deterministically from the standalone — no
extra LLM call required.

**Changes:**

1. **New helper** `all_substantive_gates_pass_except_canonical_fsd(claude_turn, openai_turn)` in [`protocol/convergence.py`](../src/dual_research/protocol/convergence.py):

   ```python
   @dataclass(frozen=True)
   class CanonicalFsdMissing:
       detected: bool
       drafter: str | None = None
       canonical_plan: str | None = None       # drafter's plan with synth'd canonical block
       synthesized_section: str | None = None  # the inserted ## … (canonical) section
       fsd_ids: tuple[str, ...] = ()

   def all_substantive_gates_pass_except_canonical_fsd(
       claude_turn: str, openai_turn: str
   ) -> CanonicalFsdMissing:
       """Detect 'agreed except missing canonical FSD sub-section'.

       Returns CanonicalFsdMissing(detected=True, ...) when:
         - both AGREED
         - drafter matches + non-None
         - OQ == BD == 0 on both sides
         - FSD count matches and is > 0 (= 0 case never trips this gate
           because the canonical sub-section is only required when FSD > 0)
         - both have a populated AGREED_PLAN block
         - normalized plan hashes MATCH
         - both have a populated standalone Final-surfaced section
         - standalone FSD IDs match
         - canonical sub-section is MISSING from at least one AGREED_PLAN
       """
   ```

2. **New synthesis function** `synthesize_canonical_fsd_section(standalone_fsd_text: str, fsd_ids: Iterable[str]) -> str`:

   - Parses each `### FSD-<N>: <title>` entry in the standalone section.
   - Re-emits each as a canonical entry with the 4 required fields
     (`Claude position`, `GPT position`, `Exact final-document treatment`,
     `Affects final recommendation? yes / no`) by copying field
     values from the standalone entry.
   - Returns the full `## Final-surfaced disagreements (canonical)\n\n…`
     markdown block ready to splice into an AGREED_PLAN.
   - Raises a clear exception if any required field is missing from
     the standalone (defensive — the standalone section is also
     required by the protocol so this should be rare; if it happens,
     the orchestrator falls through to the next round normally).

3. **Orchestrator wiring** in [`orchestrator/phase2.py`](../src/dual_research/orchestrator/phase2.py),
   immediately *after* the existing spec-0032 hash-drift escape
   block (around line 624, before the final fall-through). Mirror
   the spec-0032 canonical-promotion shape:

   ```python
   # Spec 0089 § A — canonical-FSD synthesis escape
   if r > 1:
       fsd_gap = all_substantive_gates_pass_except_canonical_fsd(
           claude_text, openai_text
       )
       if fsd_gap.detected:
           try:
               synthesized = synthesize_canonical_fsd_section_from_standalone(...)
               new_plan = splice_canonical_into_agreed_plan(
                   fsd_gap.canonical_plan, synthesized
               )
           except CanonicalFsdSynthesisError as e:
               # Standalone section is also malformed — let the loop continue.
               print(f"[phase 2] FSD synthesis failed: {e}. Continuing.")
               # fall through
           else:
               ctx.state.drafter = fsd_gap.drafter
               ctx.state.agreed_plan = new_plan
               fsd_items = extract_canonical_fsd_items(new_plan)
               ctx.state.final_surfaced_disagreements = [asdict(i) for i in fsd_items]
               converged = True
               await event_bus.publish(CanonicalFsdSynthesized(
                   round=r, drafter=fsd_gap.drafter, fsd_ids=list(fsd_gap.fsd_ids),
               ))
               ctx.transcript.write("canonical_fsd_synthesized",
                   round=r, drafter=fsd_gap.drafter, fsd_ids=list(fsd_gap.fsd_ids))
               break
   ```

4. **New event** `CanonicalFsdSynthesized` in [`events/types.py`](../src/dual_research/events/types.py),
   plus transcript writing.

5. **Phase 4 symmetry:** `is_review_approved` doesn't reference
   FSDs (Phase 4 is about open ISSUES not FSDs), so this escape is
   Phase 2 only. Documented in convergence.py docstring.

**Splice helper** `splice_canonical_into_agreed_plan(plan_text, canonical_section)`:
inserts the synthesized section into the AGREED_PLAN markdown at
the end (before any closing fence). Pure function. Idempotent: if
the canonical section is already present, returns plan unchanged.

### § B — Stuck-AGREED escape valve (closes the 27de extra rounds + general safety net)

**Bug:** even after the canonical-FSD escape lands, the ledger
cross-check (spec 0043 D7) can keep agents stuck in a loop with no
recovery path when the system-derived ledger persistently disagrees
with the agents' self-report. Spec 0032's canonical-promotion only
fires on hash drift; the ledger-mismatch case has no symmetric
escape.

**Insight:** if agents emit substantively-equivalent AGREED for
**two consecutive rounds** while only the ledger cross-check
blocks, we should accept their judgment. The ledger has had its
chance to push back through the standing-items section (§ C below);
if agents persist in claiming AGREED, that IS the convergence
signal.

**Changes:**

1. **New helper** `is_plan_agreed_lenient(claude_turn, openai_turn)` in [`protocol/convergence.py`](../src/dual_research/protocol/convergence.py):
   identical to `is_plan_agreed` *minus* the `ledger_open_count`
   parameter and ledger gate. Captures the "agents fully aligned;
   ledger may or may not agree" state.

2. **Orchestrator state addition** in [`orchestrator/phase2.py`](../src/dual_research/orchestrator/phase2.py):

   ```python
   # Spec 0089 § B — track consecutive rounds where agents fully agreed
   # but the strict (ledger-aware) check rejected. After STUCK_AGREED_K
   # such rounds in a row, accept the lenient convergence.
   STUCK_AGREED_K = 2
   stuck_agreed_streak = 0
   ```

   At the convergence check site (around line 322):

   ```python
   strict_agreed = is_plan_agreed(claude_text, openai_text, ledger_open_count=ledger_open)
   lenient_agreed = False
   if not strict_agreed:
       try:
           lenient_agreed = is_plan_agreed_lenient(claude_text, openai_text)
       except ProtocolParseError:
           lenient_agreed = False

   if lenient_agreed and not strict_agreed:
       stuck_agreed_streak += 1
   else:
       stuck_agreed_streak = 0

   agreed = strict_agreed
   stuck_promote = (
       lenient_agreed and not strict_agreed
       and stuck_agreed_streak >= STUCK_AGREED_K
   )
   ```

   At the convergence-action site (after the canonical-promotion
   block from § A but before the spec-0032 hash-drift block):

   ```python
   if stuck_promote:
       # Both agents fully aligned across K consecutive rounds;
       # only the ledger cross-check is blocking. Accept agent
       # judgment.
       ctx.state.drafter = claude_parsed.drafter
       ctx.state.agreed_plan = claude_parsed.agreed_plan
       fsd_items = extract_canonical_fsd_items(claude_parsed.agreed_plan)
       ctx.state.final_surfaced_disagreements = [asdict(i) for i in fsd_items]
       converged = True
       await event_bus.publish(StuckAgreedPromoted(
           round=r, streak=stuck_agreed_streak,
           ledger_open_count=ledger_open or 0,
       ))
       ctx.transcript.write("stuck_agreed_promoted",
           round=r, streak=stuck_agreed_streak,
           ledger_open_count=ledger_open or 0)
       break
   ```

3. **K = 2** rationale (NOT K = 1):
   - K = 1 would fire on the very first round where lenient passes
     but strict fails, leaving no breathing room for the standing-
     items prompt (§ C) to convince the agents to address open
     items.
   - K = 2 means "two consecutive blocked rounds" — sufficient
     evidence that the agents won't change behaviour, while still
     giving the ledger one round of nudging.
   - For 2c4f Phase 2 the canonical-FSD escape (§ A) handles it
     directly; this valve is the backstop.
   - For 27de Phase 2, exit would have happened at round 5 instead
     of round 6 (same as today, just via this path instead of
     spec-0032's second-detection).
   - For future runs where neither § A nor spec-0032 covers the
     stuck state, this is the universal safety net.

4. **New event** `StuckAgreedPromoted` (with `streak`, `ledger_open_count`),
   transcript-written.

5. **Phase 4 symmetry:** Add `is_review_approved_lenient` (mirrors
   the existing `is_review_approved` minus the ledger param), and
   apply the same `STUCK_AGREED_K` machinery in [`orchestrator/phase4.py`](../src/dual_research/orchestrator/phase4.py)
   at the convergence-check sites (around line 124 and line 335).

### § C — Strengthened agent-facing ledger feedback (reduces how often § B has to fire)

**Bug:** the existing `build_standing_items_section` (spec 0043 D6,
in [`ledger/prompt.py`](../src/dual_research/ledger/prompt.py))
prefixes its instruction with "Address each in your reply" but its
docstring explicitly says "The instruction is intentionally soft —
the section is informational, not output-required." Agents emit
AGREED while leaving items unaddressed because they don't know
the orchestrator will block them.

**Changes:**

1. **Stronger instruction text** in [`ledger/prompt.py:22-28`](../src/dual_research/ledger/prompt.py):

   ```python
   _INSTRUCTION = (
       "These items were raised in earlier rounds and remain open as of "
       "this point. **Convergence will be blocked while any item below "
       "is still open**, even if you emit `OPEN_QUESTIONS: 0` / "
       "`BLOCKING_DISAGREEMENTS: 0`. To make progress this round, either:\n"
       "  (a) **Answer or address** the item directly in your reply "
       "(answer the question, resolve or hold the disagreement, "
       "incorporate the fix), OR\n"
       "  (b) **Explicitly close it out** by listing the item ID in the "
       "`Resolved or non-blocking differences` section with a brief "
       "rationale.\n"
       "Items left silent will be flagged to the user as ghosted and "
       "will continue to block convergence."
   )
   ```

   Plus update the module-level docstring to drop the "intentionally
   soft" / "informational, not output-required" framing.

2. **New helper** `build_blocked_convergence_warning(...)` in [`ledger/prompt.py`](../src/dual_research/ledger/prompt.py):

   ```python
   def build_blocked_convergence_warning(
       *,
       prior_round_was_blocked: bool,
       ledger_open_count: int,
       agent_self_reported_zero: bool,
   ) -> str:
       """Return a prominent warning section when the prior round emitted
       AGREED with OPEN_QUESTIONS: 0 but the ledger still showed open items.

       Empty string when there's no mismatch to flag.
       """
   ```

   Output shape:

   ```
   ## ⚠ Convergence blocked in prior round

   Last round you and the other agent both emitted `STATUS: AGREED`
   with `OPEN_QUESTIONS: 0`, but the system-derived ledger reported
   {N} items still open. Convergence was blocked.

   The standing-items section below lists every open item. To
   converge this round, address or explicitly close out every item
   on that list. Repeating an AGREED turn without addressing them
   will continue to block convergence.
   ```

3. **Wire into round prompts** in [`orchestrator/phase2.py`](../src/dual_research/orchestrator/phase2.py)
   (and symmetrically in phase4.py) — compute the warning section
   from the prior round's parsed turns + the ledger, pass into
   `negotiation_turn_prompt` (new optional kwarg `blocked_warning`).
   Empty string when no mismatch in the prior round.

4. **Prompt template change** in [`protocol/prompts.py`](../src/dual_research/protocol/prompts.py):
   `negotiation_turn_prompt` and `review_turn_prompt` accept the new
   `blocked_warning` kwarg, render it just before the
   `standing_items` block so it has high salience.

### § D — Cache-bust + version bump

- `?v=0090` → `?v=0091` across `index.html` (defensive; this spec
  doesn't directly change static assets but if any new event types
  surface in the UI we want fresh JS).
- Version `0.69.14` → `0.70.0` (MINOR per the `new-feature` label).

## Out of scope

- **Phase 4 sycophancy** — the "Claude approves on r1 with 0
  issues while GPT genuinely has 2-5 issues" pattern from run 27de
  is a *separate* failure class. Different fix: tighten Claude's
  Phase 4 prompt to require explicit per-issue acknowledgment
  before APPROVED, or add a "minimum review rounds before
  APPROVED is honoured" gate. Will need its own spec after
  this one lands.
- **Phase 4 parse-failure cascade.** Run 27de's `exit_code: 52`
  came from Claude emitting malformed output at r3/r5/r6 after the
  parse-with-repair retries exhausted. The parse-repair flow is
  already in place; the failure is upstream (Claude's outputs
  degraded). Out of scope here — a model-prompting concern.
- **Backfilling past failed runs.** 2c4f and 27de stay in the
  database as-is. Future runs benefit from the fixes; we don't
  re-replay history.
- **Lowering `STUCK_AGREED_K` below 2** without a strong signal.
  Future spec if data shows K=2 is still leaving rounds on the
  table.
- **Surfacing new convergence-path events in the UI.** The
  CanonicalFsdSynthesized + StuckAgreedPromoted events get written
  to the transcript and surfaced in the existing critique pane's
  "deadlock / error" footer treatment, but no new dedicated UI
  widget. Cloud Design's upcoming APR can address surfacing
  policy.
- **Changes to spec-0032's existing first/second-detection split.**
  The spec-0032 hash-drift escape stays unchanged; this spec adds
  *adjacent* escapes that don't compete with it.

## Test plan

### Unit

- [ ] `tests/test_protocol_convergence.py` —
  `TestSpec0089AllSubstantiveGatesPassExceptCanonicalFsd`:
  - Returns detected=False when nothing matches.
  - Returns detected=False when canonical sub-section IS present.
  - Returns detected=True with correct `drafter` / `fsd_ids`
    populated when canonical is missing but standalone matches.
  - Returns detected=False when FSD count is 0 (canonical not
    required → not a missing-canonical case).
  - Returns detected=False when standalone FSD IDs don't match
    across agents.
  - Returns detected=False when normalised plan hashes differ
    (that's a different escape, spec 0032's territory).
- [ ] `tests/test_protocol_convergence.py` —
  `TestSpec0089SynthesizeCanonicalFsdFromStandalone`:
  - Synthesises a single FSD correctly (all 4 canonical fields
    populated from the corresponding 4 standalone fields).
  - Synthesises multiple FSDs preserving order.
  - Raises `CanonicalFsdSynthesisError` when a required field is
    missing from standalone.
  - Idempotent: synthesise(synthesise(X)) == synthesise(X).
- [ ] `tests/test_protocol_convergence.py` —
  `TestSpec0089SpliceCanonicalIntoAgreedPlan`:
  - Splices into a plan with no existing canonical section.
  - Idempotent: if canonical already present, returns input
    unchanged.
  - Preserves all existing AGREED_PLAN content (numbered list,
    titles, key claims).
- [ ] `tests/test_protocol_convergence.py` —
  `TestSpec0089IsPlanAgreedLenient`:
  - Returns True for the same input where `is_plan_agreed(...,
    ledger_open_count=10)` returns False.
  - Returns False for genuinely-different drafters / hashes / FSDs
    (the "real disagreement" cases that lenient should still
    reject).
- [ ] `tests/test_ledger_prompt.py` — new test for
  `build_blocked_convergence_warning`:
  - Empty string when prior round wasn't blocked.
  - Renders correct N-items-still-open count when there's a
    mismatch.
- [ ] `tests/test_ledger_prompt.py` — `_INSTRUCTION` text change
  is detected by a snapshot test (existing test file likely needs
  a one-line update).

### Integration / replay

- [ ] **2c4f replay test:** new `tests/test_phase2_stuck_loop_replay.py`
  that materialises the on-disk turns from `2c4f` rounds 1-3 into a
  tmp session dir, runs the convergence check with the spec 0089
  helpers, and asserts that round 3 (or round 4 — whichever is the
  first where the standalone FSD section is well-formed on both
  sides) triggers `CanonicalFsdSynthesized`. The 12-round transcript
  becomes a regression fixture.
- [ ] **27de replay test:** new `tests/test_phase2_ledger_block_replay.py`
  that materialises rounds 4-5 from `27de` and asserts that round 5
  triggers `StuckAgreedPromoted` (the `STUCK_AGREED_K=2` threshold
  is met). The 6-round transcript becomes a regression fixture.

### Live smoke

- [ ] Fire a fresh `dual-research run` via the `dual-research-run`
  skill on a topic likely to involve FSDs (e.g., a tradeoff-heavy
  brief). Observe Phase 2 + Phase 4 convergence. Verify in the
  hosted UI that neither the canonical-FSD escape nor the stuck-
  AGREED escape fires on a happy-path run (regression check).
- [ ] Manually craft a small synthetic test that mimics 2c4f's
  failure mode (matching FSD IDs in standalone, no canonical
  sub-section); confirm the orchestrator exits Phase 2 at round 3
  via canonical-FSD synthesis.

### Existing suite

- [ ] `uv run pytest tests/ -q` — current 800 still pass; new
  tests bring total to ~830.
- [ ] `fly deploy` from merged main; `/api/health` reports
  `0.70.0`; no error logs from the new helpers in the first hour.

## Risks

- **§ A — Synthesis-from-standalone produces a non-canonical
  byte representation that breaks downstream parsing.** Mitigation:
  the synthesized section uses the exact field format documented in
  `prompts.py:415-421`; `extract_canonical_fsd_items` is the only
  consumer and it's regex-based on field names; we test the
  round-trip in the unit suite. If a downstream consumer is added
  later that's stricter, we add a normalisation pass.
- **§ A — Drafter's standalone FSD section disagrees with the
  non-drafter's standalone FSD section in subtle ways.** The
  spec-0032 hash check covers the AGREED_PLAN block but NOT the
  standalone Final-surfaced disagreements section. Mitigation: § A
  only checks that FSD *IDs* match across agents; the drafter's
  standalone is canonical (same as spec 0032's drafter-as-canonical
  rule). If GPT's standalone has different field values, those are
  discarded — same as spec 0032 discards GPT's plan when claude is
  the drafter.
- **§ B — Stuck-AGREED escape fires on a real bug.** Two
  consecutive rounds of substantively-equivalent AGREED is a strong
  signal, but the ledger cross-check exists for a reason — when
  it disagrees with agent self-report, there's usually something
  the agents are glossing over. Mitigation: (a) the strengthened
  prompt in § C reduces how often this fires; (b) the
  `stuck_agreed_promoted` event is logged distinctly so we can
  audit how often it triggers in practice; (c) `K=2` is
  configurable via a module-level constant so we can tighten or
  loosen with a one-line change after observing live behaviour.
- **§ C — Prompt change confuses agents and degrades convergence
  on currently-working runs.** Mitigation: the wording is purely
  *additive* — it tells agents what was already true (the ledger
  *would have* blocked them); it doesn't change any protocol field
  formats. The live smoke test above is the primary regression
  guard.
- **§ C — The blocked-convergence warning shows up on the very
  first AGREED-but-blocked round, which would have advanced
  naturally via § B next round anyway.** That's fine; the warning
  gives agents one more chance to fix it themselves, and the § B
  escape valve catches the case where they don't.
- **Inter-spec ordering** with the design-system bootstrap (#89)
  and the timeline fix (#90, spec 0088). All three touch
  independent surfaces (spec 0088 = JSX only; spec 0089 = Python
  protocol/orchestrator/prompts only; design-system = docs). No
  merge conflict risk.

## Open questions

- **Should `STUCK_AGREED_K` be 1 or 2?** Spec proposes 2. K=1 saves
  one round per stuck case but reduces the standing-items prompt's
  chance to nudge agents. Recommend shipping K=2 and revisiting
  after a week of live data if we see K=1 cases that fired the §
  C warning, the agents didn't change, and we waited one more
  round for nothing.
- **Should we add a `DR_STUCK_AGREED_DISABLE=1` env flag** to
  let users force the old behaviour during incident response? Lean
  toward yes for the canonical-FSD escape (§ A is purely additive
  and shouldn't need a kill switch), no for the stuck-AGREED
  valve (§ B). Tentative answer: ship without flags; add only if
  we see a real need.
- **Phase 4 specifics:** Phase 4 review turns don't have FSDs
  (FSDs are P2 concepts), so § A is Phase 2 only. § B and § C
  both apply symmetrically — confirmed by reading
  `is_review_approved` in [`protocol/convergence.py:176-198`](../src/dual_research/protocol/convergence.py)
  and the matching round-prompt flow in
  [`orchestrator/phase4.py:140-185`](../src/dual_research/orchestrator/phase4.py).
