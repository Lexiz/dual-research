---
spec: 0137
title: Substantive-convergence escape valve — canonical-promote when both AGREED with terminal ledger but artifact hashes drift
type: new-feature
label: new-feature
version_bump: MINOR
status: ready
target-version: 1.8.3
created: 2026-05-21
pr: ""
---

# Spec 0137 — Substantive-convergence escape valve

> Ship bucket: **Phase 0 / 2 / 4 convergence loop fix.**
> Depends on: **0114** (Deep Research protocol — `_drive_interaction_phase` + three-gate `check_convergence`), **0032** (the equivalent escape in the legacy `phase2.py`, ported in concept), **0136** (HardCapHit emission predicate — clarifies the failure surface this spec replaces).
> Complexity: **S** — one new branch in `_drive_interaction_phase`, one new event type, one flag threaded through `PhaseRunResult` + `PhaseConverged`.
> Targeted version bump: **PATCH (1.8.2 → 1.8.3)** — bug fix. No protocol or wire-format changes; new event is purely additive.

---

## Context

Convergence in phases 0, 2, and 4 is gated by three conditions in
`check_convergence` ([orchestrator/closeout.py:276](src/dual_research/orchestrator/closeout.py)):
both agents emit `STATUS: AGREED`, the ledger has zero non-terminal items,
and the per-phase artifact hash matches across both agents. All three
must hold in the same round.

The third gate is brittle. The artifact body (AGREED_INTERPRETATION /
AGREED_PLAN / AGREED_DRAFT_ACCEPTANCE) is free-text the agents are
asked to copy verbatim from a designated proposer. Because both turns
in a round are emitted in parallel, neither agent reliably copies the
other — each writes its own version, and the prompt's "Adoption
procedure" assumption (proposer in round k, endorser in round k+1)
collapses. Production run `81cc`
(`20260520-170146-dvs-backend-language-choice`) is the latest
reproduction: by phase 2 round 5, every item is terminal; in rounds
6, 7, 8 both agents emit AGREED, both name `claude` as drafter, no
new items are raised — but the AGREED_PLAN hashes never match
(claude's body is ~19k normalised chars, openai's is ~14k normalised
chars; claude's hash even keeps thrashing micro-edits round-over-round).
The phase exits at hard cap with `converged=false drafter=null`,
wasting three rounds of LLM spend and blocking Phase 3.

The legacy `phase2.py` carried a Spec 0032 hash-drift escape valve
for exactly this: detect "substantive agreement + hash drift", fire a
force-verbatim repair turn for the non-drafter, canonical-promote on
second detection. The Deep Research orchestrator
([orchestrator/dr_run.py:164](src/dual_research/orchestrator/dr_run.py))
that replaced `phase2.py` did not port this escape. The closeout
mechanism handles "both AGREED + items still open"; the hard-cap
handles "ran out of rounds"; but the "both AGREED + items terminal +
hash drift" gap has no handler.

## Proposed change

Add a substantive-convergence escape valve to
`_drive_interaction_phase`. When both agents emit AGREED, the ledger
holds zero non-terminal items, and the round failed to converge
(meaning the artifact hash gate is the only remaining blocker),
declare convergence immediately via canonical-promotion. The downstream
post-loop code in `run_dr_phase{0,2,4}` already reads the canonical
artifact body from one specific agent's turn file (claude for phase 0;
the drafter for phase 2; the drafter for phase 4); the
non-drafter's emission of the artifact block is never consumed past
the convergence check. Trusting the agents' self-declared AGREED is
load-bearing; byte equality of the artifact block was a hopeful
structural assertion downstream did not actually need.

Concretely:

1. **New event** `ArtifactCanonicallyPromoted` in
   `src/dual_research/events/types.py`, exported from
   `src/dual_research/events/__init__.py`. Fires once per phase, with
   `phase` (`"phase0" | "phase2" | "phase4"`) and `round`.

2. **`PhaseRunResult.via_artifact_promotion: bool`** in
   `src/dual_research/orchestrator/deep_research.py`. Defaults to
   `False`; flipped by the new branch.

3. **`PhaseConverged.via_artifact_promotion: bool`** in
   `events/types.py`. Threaded through
   `DeepResearchPhase.build_phase_converged_event`. The four `via_*`
   flags now form an exhaustive partition of non-organic convergence
   paths.

4. **The escape branch** in `_drive_interaction_phase`, placed
   immediately after `phase.process_round_end(...)` returns `rr` and
   before the closeout / hard-cap branches:

   ```python
   if (not rr.converged
       and rr.claude_status == "AGREED"
       and rr.openai_status == "AGREED"
       and not items_blocking_convergence(phase.state.item_views())):
       converged = True
       via_artifact_promotion = True
       final_round = round_no
       await event_bus.publish(ArtifactCanonicallyPromoted(
           phase=phase_label, round=round_no,
       ))
       ctx.transcript.write(
           "artifact_canonically_promoted",
           phase=phase_label, round=round_no,
       )
       break
   ```

   `items_blocking_convergence` is already imported transitively via
   `dual_research.orchestrator.closeout`; we add a direct import to
   `dr_run.py`.

5. **No prompt changes.** The branch fires at the end of the first
   round where both agents go AGREED with a terminal ledger, so
   subsequent rounds (which would have been the natural place to
   surface a "you're blocked on hash" warning) never happen. The
   existing prompt's verbatim-copy guidance stays in place for the
   common case where one agent does adopt the other's text.

## Out of scope

- **No force-verbatim repair turn.** The legacy Spec 0032 fix first
  fired a repair turn before promoting. That's an extra LLM call that
  produces text downstream code does not consume. We skip it.
- **No relaxation of `check_convergence`.** The strict three-gate rule
  stays as the canonical definition of organic convergence; the escape
  is an explicit, telemetered alternative path at the orchestrator
  level, not a quiet weakening of the protocol.
- **No prompt changes.** No new "convergence blocked on artifact" prompt
  section; no edit to the existing Adoption procedure prose. The branch
  fires before a follow-up round would need it.
- **No source-tag stripping inside the hash normaliser.** The `[U] / [V]`
  tag noise was one contributor to the 81cc drift; stripping it inside
  `_normalize_for_hash` would help organic convergence, but it's a
  protocol-semantics change and belongs in its own spec if we decide to
  do it. This spec only adds the escape valve.

## Test plan

- [ ] Unit test in `tests/orchestrator/test_dr_run.py` (new file or
  existing file under that directory): drive a fake `_drive_interaction_phase`
  end-to-end where both agents emit AGREED in round 2 with all ledger
  items resolved but mismatched artifact hashes. Assert:
  `result.converged is True`, `result.via_artifact_promotion is True`,
  `result.via_hard_cap is False`, `result.final_round == 2`, and an
  `ArtifactCanonicallyPromoted` event was published.
- [ ] Unit test: same scenario but with one non-terminal item left in
  the ledger at end of round. Assert the escape valve does **not**
  fire; closeout urge fires instead.
- [ ] Unit test: same scenario but only one agent AGREED. Assert the
  escape valve does not fire; the loop continues.
- [ ] Unit test: organic convergence (hashes match) still emits
  `PhaseConverged` with `via_artifact_promotion=False` and all other
  `via_*` flags also `False`.
- [ ] Regression: replay run `81cc`'s ledger shape (12 items in phase
  2, all resolved by round 5, both AGREED in round 6) and assert the
  loop terminates at round 6 with `via_artifact_promotion=True`.
- [ ] Manual: fire a fresh run with `/dual-research-run` on a brief
  known to produce hash drift in phase 2; confirm convergence at the
  natural-agreement round instead of running to hard cap.

## Risks

- **False-positive convergence**: the agents could in principle emit
  AGREED + zero items while substantively disagreeing on the plan
  contents. Mitigation: the protocol's AGREED definition forbids open
  questions / disagreements; an agent who wants to surface a remaining
  disagreement must keep at least one item non-terminal or emit
  IN_PROGRESS. The 81cc trace confirms agents respect this — no items
  raised in rounds 6 / 7 / 8 after both went AGREED in round 6. If
  this turns out to bite in production, the rollback is one event flag
  default flip (`via_artifact_promotion` default to never fire) plus a
  guard variable; we can also add a same-drafter cross-check before
  promoting (`extract_drafter_from_agreed_plan(claude) ==
  extract_drafter_from_agreed_plan(openai)` for phase 2) if false
  positives appear.
- **Telemetry interpretation**: an organic-look convergence that was
  actually a hash drift will now surface as
  `via_artifact_promotion=True` instead of getting lost in a hard-cap
  exit. The UI will need to render this branch; until it does, the
  badge falls back to a generic "converged" — which is correct.
