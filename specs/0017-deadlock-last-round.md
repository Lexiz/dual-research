---
spec: 0017
title: Render the last round in deadlocked / errored phase-2 timelines
label: bug
version-bump: PATCH
status: merged
target-version: 0.16.2
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/17"
---

# Spec 0017 — Render the last round in deadlocked / errored phase-2 timelines

## Context

The integration session that produced spec 0016 ran a second live test-tier
job (`What is the best way to present a library of web components ...`)
to verify the v0.16.1 fixes against a real in-flight run. That second run
**deadlocked** at the Phase 2 hard cap (claude AGREED for four straight
rounds; openai NEGOTIATING with no open questions or blocking
disagreements but never flipping to AGREED). Exit 51, $0.47.

The deadlocked detail view rendered almost everything correctly — status
pill `deadlocked`, `hard cap reached · 5/5` header, `HARD_CAP_REACHED`
deadlock card, every per-turn `negotiating` / `agreed` pill — but only **4
of the 5 turn-card pairs**. The Phase 2 divider correctly says "5 rounds"
(derived from `phaseStats.phase2` keys per spec 0016) yet the turn-card
loop renders rounds 1-4 only. The fifth round's files are on disk and
`phaseStats.phase2['5']` is populated; they just never enter `items[]`.

Root cause is in the same branch spec 0016 touched. In
`buildLiveTimeline` for `ph === 2`:

```js
if (ph === 2 && (st === 'running' || st === 'deadlocked' || st === 'errored')) {
  const completedThrough = Math.max(0, cur - 1);
  for (let r = 1; r <= completedThrough; r++) { /* static turn cards */ }
  if (cur > 0 && st === 'running') {
    /* live turn cards for round `cur` */
  }
}
```

`completedThrough = cur - 1` assumes the `cur` round is the in-flight one
covered by the live branch. The live branch only fires when
`st === 'running'`. For `deadlocked` / `errored`, the `cur` round is on
disk and complete, but neither branch picks it up.

Same shape applies to Phase 4 (`errored` mid-review) but the existing
fixture set hasn't exercised it; the fix is symmetric.

## Proposed change

`src/dual_research/ui/static/live-data.jsx::buildLiveTimeline` — when
`st !== 'running'` (i.e. `deadlocked` or `errored`), include `cur` in the
static-card loop. Two-line change:

```js
const completedThrough = st === 'running' ? Math.max(0, cur - 1) : cur;
for (let r = 1; r <= completedThrough; r++) { /* static turn cards */ }
if (cur > 0 && st === 'running') { /* live cards (unchanged) */ }
```

Only the Phase 2 branch needs the fix. The Phase 4 block's outer guard
already excludes `deadlocked` / `errored` statuses (`ph >= 4 && st !==
'errored' && st !== 'deadlocked'`), so the live-mid-phase branch is
never reachable in those states — a Phase 4 deadlock wouldn't render
the Phase 4 timeline at all today, but that's a separate edge case
without a fixture run to test against and is left out of scope.

## Out of scope

- Anything else from `handoffs/integration-observations.md`. The P2
  cosmetic cluster (I6, I8, I9, I10) and I11 (`ErrorCard` crash) all stay
  in their own follow-ups.
- The downstream reason claude / openai never converged on this prompt.
  That's an agent-behaviour question, not a UI one.

## Test plan

- [ ] **Unit test in `tests/ui/test_aggregator.py`** — synthetic session with `state.json` `phase: phase2` and a `hard_cap_hit` event; assert `phaseStats.phase2` has all rounds.
- [ ] **Live verify** — open the new fixture run `20260515-171500-live-verify-webcomp-catalogue` in the UI and count the turn-card pairs (should be 5; previously 4).

## Risks

Trivial. The branch is small, only changes the `completedThrough`
calculation. No new code paths.
