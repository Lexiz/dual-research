---
spec: 0088
title: Stop hiding Phase 3 / Phase 4 timeline rows on errored & deadlocked runs
label: bug
version-bump: PATCH
status: proposed
target-version: 0.69.14
created: 2026-05-18
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0088 — Timeline phase-omission on errored / deadlocked runs

## Context

The run-detail Timeline (left pane) silently drops Phase 3 and Phase 4
artifacts whenever the per-run-detail endpoint reports `status:
'errored'` or `status: 'deadlocked'` — even when those phases
actually executed and wrote files to disk. The Critique pane (right
pane) reads from a different code path (`phaseLedgers`,
`phaseReviewItems`, `phaseStats`) which does not have this gate, so
the two panes disagree about what the run did.

Reproduction case is run `27de` =
`20260518-083618-backend-language-choice` (currently in the production
Supabase, pulled to local for inspection). Per-run endpoint reports
`phase: 4, status: 'errored', drafter: 'claude', phaseTimings: {0:20,
1:161, 2:742, 3:208, 4:2089}`. The run hit a Phase 4 parse-failure on
Claude's r6 output (`exit_code: 52`), but six Phase 4 review rounds did
complete, with 106 issues + 27 comments + 30 questions surfaced. The
Critique pane shows all of that. The Timeline shows nothing past
PHASE 2 — DOM `[data-phase-id]` returns `['0', '1', '2']`.

The cause is two gates in
[live-data.jsx](../src/dual_research/ui/static/live-data.jsx) at
lines 593 and 613:

```js
if (ph >= 3 && st !== 'errored' && st !== 'deadlocked') {  // phase 3
if (ph >= 4 && st !== 'errored' && st !== 'deadlocked') {  // phase 4
```

The intent was reasonable: a run that died at Phase 2 shouldn't have
phantom "Phase 3" / "Phase 4" sections in its timeline. But the gate
keys on overall run status instead of on whether the phase actually
produced any artifacts, so it also strips real content from runs that
made it past Phase 2 before failing.

Phase 2 already does this correctly — its gate is `ph >= 2` (no
status clause), and the live-vs-completed-vs-past branching inside
that block handles all four termination states explicitly (running /
deadlocked / errored / completed). Phase 3 and Phase 4 just need the
same treatment.

The 3a4a canonical fixture is unaffected because its per-run-detail
endpoint reports `status: 'completed'` (final.md was emitted, even
though the run-list summary shows it as "errored" — that's a separate
status-derivation inconsistency tracked elsewhere). The bug only
manifests when the per-run-detail call returns `errored` or
`deadlocked` AND the run reached at least Phase 3 on disk.

## Proposed change

Mirror the Phase 2 branching pattern in the Phase 3 + Phase 4 blocks
of `buildLiveTimeline()` ([live-data.jsx:469-688](../src/dual_research/ui/static/live-data.jsx)).
Three small edits.

### Change 1 — Phase 3 gate (`live-data.jsx:593-611`)

Drop the status clause from the outer gate. Move the live-only
condition (drafter currently streaming) onto a dedicated
`st === 'running'` check so an errored-in-Phase-3 run still surfaces
the on-disk draft file as a completed card.

```diff
- if (ph >= 3 && st !== 'errored' && st !== 'deadlocked') {
+ if (ph >= 3) {
    items.push({ id: 'phase-3', kind: 'phase-divider', phaseId: 3, duration: run.phaseTimings?.['3'] });
-   if (ph === 3 && run.drafter) {
+   if (ph === 3 && st === 'running' && run.drafter) {
      items.push({
        id: 'doc-live', kind: 'doc-live', agent: run.drafter, live: true,
        status: run.agents?.[run.drafter]?.status,
        body: run.agents?.[run.drafter]?.currentTurn?.body || '',
        filePath: 'phase3/draft-v1.md',
        turnKey: `phase3_${run.drafter}`,
      });
    } else if (run.drafter) {
      items.push({
        id: 'doc-converged', kind: 'doc', agent: run.drafter,
        summary: `Converged document drafted by ${run.drafter}.`,
        filePath: 'phase3/draft-v1.md',
        turnKey: `phase3_${run.drafter}`,
      });
    }
  }
```

The `run.drafter` guard already handles the case where a deadlock-at-
Phase-2 run technically reports `ph === 2` (so `ph >= 3` is false →
nothing pushed; no regression). For a run that died IN Phase 3 with a
drafter assigned but no draft on disk yet, the completed-card branch
will still fire and the `<ArtifactCard>` renders a graceful
file-not-found state via the existing `/files/...` fetch path.

### Change 2 — Phase 4 gate (`live-data.jsx:613-662`) + round-count hardening on both Phase 2 and Phase 4

Same shape as Change 1. Drop the status clause from the outer gate;
mirror Phase 2's three-way branching for the live / stopped-in-phase /
past-phase states.

While verifying the fix against `27de`, surfaced a second adjacent
bug: when ph === 4 and the run died after a round completed but
before `round.current` advanced, `cur` lags behind disk reality. For
`27de`: `round.current = 5` but `phaseStats.phase4` has keys `'1'..'6'`
and `phase4/round-06-claude.md` + `phase4/round-06-openai.md` exist on
disk. The original `p4Rounds = cur` formula would silently truncate
round 6 from the Timeline. Apply the same fix to both phases for
symmetry (Phase 2 would have the same bug pattern under
ph === 2 + errored/deadlocked + late state-update kill):

```js
const p2StatsCount = Object.keys(run.phaseStats?.phase2 || {}).length;
const p2Rounds = ph === 2
  ? (st === 'running' ? cur : Math.max(cur, p2StatsCount))
  : p2StatsCount;
// …same for p4Rounds…

const completedThrough = st === 'running'
  ? Math.max(0, cur - 1)
  : Math.max(cur, p2StatsCount);   // or p4StatsCount in the P4 block
```

`phaseStats[phase{N}]` is keyed by round number and is populated
incrementally as `phase{2,4}_round_complete` events land; trusting its
key count over `cur` whenever the run is stopped gives us the actual
disk reality without a second I/O round-trip.

```diff
- if (ph >= 4 && st !== 'errored' && st !== 'deadlocked') {
+ if (ph >= 4) {
    const cur = run.round?.current ?? 0;
    const p4Rounds = ph === 4 ? cur : Object.keys(run.phaseStats?.phase4 || {}).length;
    items.push({
      id: 'phase-4', kind: 'phase-divider', phaseId: 4,
      duration: run.phaseTimings?.['4'],
      extra: `${p4Rounds} review round${p4Rounds === 1 ? '' : 's'}`,
    });
-   if (ph === 4) {
-     const completedThrough = Math.max(0, cur - 1);
+   if (ph === 4 && (st === 'running' || st === 'deadlocked' || st === 'errored')) {
+     // Mirror the Phase 2 pattern: when stopped in this phase, treat `cur` as
+     // the last completed round; when still running, treat `cur` as in-flight.
+     const completedThrough = st === 'running' ? Math.max(0, cur - 1) : cur;
      for (let r = 1; r <= completedThrough; r++) {
        items.push({ id: `p4-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: `rev-${r}`,
                     filePath: fileForRound(4, r, 'claude'),
                     turnKey: `phase4_round${r}_claude` });
        items.push({ id: `p4-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: `rev-${r}`,
                     filePath: fileForRound(4, r, 'gpt'),
                     turnKey: `phase4_round${r}_gpt`    });
      }
-     if (cur > 0) {
+     if (cur > 0 && st === 'running') {
        items.push({
          id: `p4-r${cur}-claude-live`, kind: 'turn-live', agent: 'claude',
          /* …existing live-turn payload… */
        });
        items.push({
          id: `p4-r${cur}-gpt-live`, kind: 'turn-live', agent: 'gpt',
          /* …existing live-turn payload… */
        });
      }
    } else if (ph === 5 || st === 'completed') {
      for (let r = 1; r <= p4Rounds; r++) {
        /* …existing completed-rounds enumeration… */
      }
    }
  }
```

### Change 3 — cache-bust

`?v=0089` → `?v=0090` across the `<script>` and `<link>` tags in
[index.html](../src/dual_research/ui/static/index.html) so browsers
pick up the new `live-data.jsx`. (The 0088 → 0089 bump was already
spent by the design-system bootstrap commit `921a3a5`, so this spec
takes the next available marker.) Same pattern as every prior spec
that touches static assets.

### Behaviour after the fix (table)

| Run shape | `ph` | `st` | drafter | Before this spec | After this spec |
|---|---|---|---|---|---|
| Errored at P4 (27de) | 4 | errored | claude | P0/P1/P2 (Phase 2 capped at r5 if `cur` lagged) | P0/P1/P2 (rounds 1..max(cur, statsCount)) + **P3 doc card + P4 rounds 1..6** |
| Deadlocked at P2 (2c4f) | 2 | deadlocked | null | P0/P1/P2 only | P0/P1/P2 only (unchanged) |
| Completed run (3a4a) | 5 | completed | claude | P0..P5 ✓ | P0..P5 ✓ (unchanged) |
| Mid-run, in P3, streaming | 3 | running | claude | P0/P1/P2 + live doc | P0/P1/P2 + live doc (unchanged) |
| Mid-run, in P4 r3, streaming | 4 | running | claude | P0..P3 + P4 r1/r2 + live r3 | P0..P3 + P4 r1/r2 + live r3 (unchanged) |
| Died IN P3 (rare) | 3 | errored | claude | P0/P1/P2 only | P0/P1/P2 + **P3 completed-doc card** |
| Died IN P4 mid-round | 4 | errored | claude | P0/P1/P2 only | P0/P1/P2 + **P3 doc + P4 rounds 1..cur** |

## Out of scope

- **Convergence escape hatches for the stuck-AGREED loop.** Same
  investigation surfaced two bugs; per agreement with the user this
  spec is the small UI fix, and the convergence work lives in a
  separate forthcoming spec (likely 0089 or 0090). The two issues
  share a debugging story but not a fix surface.
- **Status-derivation inconsistency between run-list and run-detail.**
  3a4a renders as "errored" in the run-list chip but its per-run
  endpoint says "completed", which is part of why the bug is hard to
  spot from the list view. Out of scope here; that's a separate
  derivation question.
- **Backfill / "rerender historic runs" UI affordance.** All existing
  affected runs (just 27de in the current dataset) will pick up the
  fix automatically on next visit — no migration needed.
- **Documenting the live-vs-completed-vs-past pattern as a reusable
  helper.** The three blocks (Phase 2, Phase 3, Phase 4) all encode
  the same state machine inline. Extracting a `buildPhaseRows(phase,
  cur, p_rounds, st, drafter)` helper would clean this up, but
  that's a refactoring spec, not part of the bug fix.

## Test plan

- [ ] **Manual — `27de`:** load
      `http://127.0.0.1:6173/#/runs/20260518-083618-backend-language-choice`
      at 2200×1300. Timeline shows PHASE 3 (with the converged-doc
      card pointing at `phase3/draft-v1.md`) and PHASE 4 (with 6
      review-round pairs, including the r6 pair that completed before
      the parse-failure kill). Phase rail dot for P3 stays
      `is-completed`, P4 stays `is-failed`.
- [ ] **Manual — `2c4f`:** load
      `http://127.0.0.1:6173/#/runs/20260518-065852-backend-language-choice-briefing-for-dual-research`
      at 2200×1300. Timeline ends after PHASE 2 round 12 + deadlock
      card. No phantom PHASE 3 or PHASE 4 divider. Phase rail dots
      for P3/P4 stay empty.
- [ ] **Manual — canonical fixture `3a4a`:** load
      `http://127.0.0.1:6173/#/runs/20260516-035048-partner-vetting-arch-critique`
      at 2200×1300. Timeline matches the existing baseline — all
      six dividers (PHASE 0..PHASE 5) plus their content. No
      regression on the happy-path view.
- [ ] **DOM cross-check:** in the dev console on each of the three
      runs above, `[...document.querySelectorAll('[data-phase-id]')]
      .map(el => el.getAttribute('data-phase-id'))` returns the
      expected ID set per the table above.
- [ ] **Live-running smoke:** kick off a small `dual-research run`
      (any topic) and watch the Timeline through Phase 3 and Phase 4
      transitions. The live cards still appear during streaming and
      transition to completed cards at phase-exit. (Mirrors the
      Phase 2 live behaviour which is unchanged.)
- [ ] **`uv run pytest`:** existing 800 still pass; no new tests
      added (no JSX test harness in this repo — same as specs 0083,
      0084, 0085, 0086, 0087 which were also pure JSX changes).
- [ ] **`fly deploy`** from the merged branch; hit
      `https://dual-research-alex.fly.dev/#/runs/20260518-083618-backend-language-choice`
      and confirm production picks up the fix.

## Risks

- **Phase 3 / Phase 4 completed cards on a partially-written disk
  state.** If a run died mid-round-write, the per-round file may be
  missing while `cur` already reflects the new round number. The
  resulting `<ArtifactCard>` would fail its `/files/...` fetch and
  render the existing "file not found" empty state, same as it does
  today for any other broken-file case. Manual verification on 27de
  covers this — all 6 P4 round files are on disk.
- **Phase 3 doc-card on a run with `ph === 3, drafter set, no
  draft-v1.md on disk yet`.** This is an artifact of the
  errored-at-Phase-3 case the old gate suppressed. The new code
  renders a completed-card variant that fetches the missing file →
  empty state. Acceptable; the alternative (hiding the whole phase)
  is what we're fixing.
- **Live-streaming regression.** The Phase 4 `if (cur > 0)` block
  used to push live turns unconditionally; the new code gates it on
  `st === 'running'`. If `cur > 0` ever holds when status is NOT
  running (e.g., during the brief moment between `phase_exited` and
  the next status flip), the live cards would disappear one tick
  earlier than today. In practice the SSE push that sets the new
  phase + status arrives in the same event batch, so this should be
  invisible. Watching for it in the live-running smoke test above.
- **Cache-bust marker.** Bumped to `v=0090` (the design-system
  bootstrap had already taken `v=0089`). The marker is decoupled
  from spec numbers and PR numbers; the only invariant is that it
  must increase whenever a static asset changes.

## Open questions

None — the diff is mechanical and the visual outcome on the three
verification runs (27de, 2c4f, 3a4a) covers every relevant
combination of `(phase, status)`.
