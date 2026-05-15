> Working notes from the live concurrent-run integration session that
> followed spec 0015. Captured BEFORE writing spec 0016; preserves the
> raw observations so the eventual spec(s) and the next handoff can cite
> them.

# Integration observations — concurrent live run

**Run:** `runs/20260515-163105-live-integration-test`
**Prompt:** "Compare SQLite vs Postgres for a single-tenant API serving 1-10M rows. Output: one-page memo."
**Models:** test tier (Haiku 4.5 + GPT-5-mini)
**Caps:** soft 3, hard 5
**Outcome:** APPROVED — exit 0 — $0.4228 — 12m 53s — draft v2
**Topology:** Phase 0 (16s) → 1 (1m 31s) → 2 (6m 42s, 4 rounds, soft cap hit @ r3, AGREED @ r4) → 3 (46s) → 4 (3m 34s, 3 rounds, 1 draft revision)

---

## What worked end-to-end

- The new run appeared in the All-runs list within the 3 s poll window.
- Click-through to detail view; connection pill flipped to `connected`.
- Phase strip advanced through 0 → 1 → 2 → 3 → 4 → 5 (`Done`) as expected.
- Current-turn bodies populated within ~5 s of each `TurnEnded`. SSE delivered every snapshot reliably; no disconnects across the 13-minute run.
- Stat chips updated as each Phase 2 / Phase 4 turn file landed on disk.
- Errors counter at top-right showed the right thing: `INVALID_TURN_FORMAT` for GPT round 3 and `SOFT_CAP_HIT` for round 3.
- On completion, status flipped to `completed` and the Phase 5 "Final document" card appeared.
- Cost roll-up tracked correctly: `$0.2425 Claude · $0.1803 GPT · $0.4228 total`.

## Issues observed (priority order)

### P0 — functionality is broken

#### I1. Phase 2 round enumeration is off-by-N

Phase 2 actually ran 4 rounds. The completed-run UI renders only **3 turn-card pairs** (rounds 1, 2, 3) under "Negotiate plan", with the phase-divider line reading `6m 42s · 3 rounds`. Mid-Phase-4 (round 2) the count was even worse — only round 1 of Phase 2 was visible.

Root cause: `live-data.jsx::buildLiveTimeline` uses `run.round.current` for the Phase 2 round enumeration loop. That field is global and reflects the **current** phase's round counter — it is overwritten when the orchestrator advances to Phase 4. The aggregator already stores per-phase round counts in `phaseStats.phase2` (keys `'1'..'4'`) and `phaseStats.phase4` — the JS just isn't reading from there.

```js
// live-data.jsx:289-298 (Phase 2 enumeration when phase ≥ 3)
} else if (ph >= 3 || st === 'completed' || st === 'deadlocked') {
  const maxRound = cur;           // <- cur = run.round.current, now reset
  for (let r = 1; r <= maxRound; r++) { ... }
}
```

Same shape for Phase 4 enumeration after the run completes (`ph === 5`). Fix: derive `maxRound` from `Object.keys(run.phaseStats?.[phaseKey] || {}).length`, or thread an explicit `phase2Rounds` / `phase4Rounds` count through the snapshot.

#### I2. Disagreement parser missed every D-N in this run

The Disagreement Explorer rendered `0 introduced · 0 open · 0 resolved` and "no disagreements in this phase" — for a run that had 5 well-tracked substantive disagreements (D-1..D-5) that successfully converged. `disagreements n=0` in the API snapshot too; not a render bug, the parser is returning empty.

Format census from this run's Phase 2 round files:

| Round | Agent  | Format observed                                               | Parsed?           |
|------:|--------|---------------------------------------------------------------|-------------------|
|     2 | claude | `### D-1: Label (qualifier)` (H3 heading)                     | no                |
|     2 | openai | `1) D-1: Label — open` (numbered, paren-close, no list dash)  | no                |
|     3 | claude | `(None remaining...)` then resolved entries in a *separate* `## Resolved or non-blocking differences` section | section not read |
|     3 | openai | `1) D-1: Label — resolved.`                                   | no                |
|     4 | claude | `- **D-1 (label):** \`resolved\` — note`                       | matches regex, but extracted from `## Resolved or non-blocking differences` which the parser does not read; the `## Substantive disagreements I'm holding` section in round 4 says "(None remaining.)" |
|     4 | openai | `1) D-1: Label — resolved. Status: resolved — Evidence: ...` | no                |

`disagreements.py::_D_LINE_RE` requires `^\s*-\s*` (a leading list-marker dash) — neither agent's preferred formats survive. And once an entry is resolved, Claude moves it out of `## Substantive disagreements I'm holding` into `## Resolved or non-blocking differences`, which the parser never reads.

Two angles of attack:
1. **Tighten the prompt.** `protocol/prompts.py::negotiation_*_prompt` could specify a single canonical D-N line format with a worked example, so both agents emit something parseable. Cheap, durable, and the test-tier models follow examples reliably.
2. **Broaden the parser.** Accept `### D-N: ...` headings and `N) D-N: ...` numbered forms; also walk a small allowlist of sibling sections (`Final-surfaced disagreements`, `Resolved or non-blocking differences`) so resolved entries don't disappear from the timeline.

Both probably want to ship. Prompt is the strategic fix; parser tolerance is the safety net.

### P1 — confusing or wrong

#### I3. Completed turn cards drop their terminal-status pill

Phase 2 turn cards (after the round has finished writing) render `4 questions · r1` with **no** `agreed` / `negotiating` / `disagreed` pill. The data is in `phaseStats.phase2.{round}.{agent}.status`. The pill renders only when `status === 'AGREED'` (in Phase 2) or `status === 'APPROVED' / 'NOT_APPROVED'` (in Phase 4). Mid-state values (`NEGOTIATING`, `REVIEWING`) are silently dropped — so a turn that read "claude AGREED, openai NEGOTIATING, agreed=False" shows `agreed` on Claude's card and **nothing** on GPT's card. The user can't tell whether the round agreed by reading the timeline.

Fix: render every per-turn terminal-protocol status as a pill (`negotiating`, `reviewing`, `disagreed` as muted-grey; `agreed` / `approved` as green; `not approved` as amber).

#### I4. Phase 0 "needs input · N" chip sums brief_issues across agents

For this run: claude `BRIEF_OK` with `BRIEF_ISSUES: 4`, openai `BRIEF_NEEDS_INPUT` with `BRIEF_ISSUES: 12`. The chip renders `needs input · 16`. The lists overlap substantially — adding them together is meaningless and misleads the reader into thinking the brief has 16 distinct problems.

Better behaviours:
- Show `needs input` with no count (simplest).
- Show `needs input · max(4, 12) = 12`.
- Show per-agent: `needs input · claude 4 · gpt 12`.

#### I5. Disagreement Explorer is silent when the parser fails

When `disagreements n=0`, the right pane renders empty (`no disagreements in this phase`). There is no visual distinction between "parser found nothing" and "agents legitimately had no disagreements." Given how frequently the parser misses (see I2), a fallback that says "couldn't reconstruct disagreements from this run's round files — open the round files directly" would be honest.

### P2 — cosmetic / minor

#### I6. Stale runs show as `running` indefinitely

5 of 10 runs in the All-runs list display status `running`. They are 4-hour-old fixtures whose orchestrator processes have been dead since the day they were captured. The `labels.py` status state machine treats any non-completed session as `running`, with no liveness probe.

Fix: classify a run as `abandoned` (or `stale`) when its transcript has not been appended to in the last ~10 minutes and no `RunCompleted` / `RunFailed` event is present. The All-runs filter chips already include a slot that can carry this state.

#### I7. Phase 1 chip parser misses H1 ("# Open questions") variant

Claude's Phase 1 draft in this run used `# Open questions` and `# Claims I expect the other agent might dispute` (single-hash H1). `turn_stats.extract_phase1_stats` only matches `## H2` or numbered top-level — so Claude's chip didn't render at all, while GPT's showed `0 questions`. Result: visually uneven row. Adding H1 to the format census closes the gap.

#### I8. `agents.{agent}.currentTurn.body` is never cleared

After the run completes, `agents.gpt.currentTurn` still holds the entire Phase 3 final-doc text (~10 KB) plus a `kind: 'doc-draft', index: 0` stub. That body has already been written to disk; it should be cleared on `PhaseExited` (or on the next `TurnStarted`) so SSE snapshots don't carry duplicated payload for the rest of the run.

#### I9. Connection pill says `connected · localhost · 6173` on the All-runs view

There is no SSE connection on the All-runs view — it's a 3 s polling fetch. The same pill, same chrome, same green dot is reused unchanged. Either gate the "connected" pill to detail-view-only, or relabel ("polling 3 s") on the list view.

#### I10. final.md metadata header reports wrong duration

The header in `final.md` shows `Total time | 17m 51s (21 model calls)`, but the run actually took 12m 53s (UI elapsed counter agrees; `metrics.json` agrees; `RunCompleted.duration_ms` agrees). `finalize.py` is computing this from somewhere else. Pure backend; doesn't affect the live UI but visible in the artifact.

## Discovered while implementing 0016 — pre-existing bug

- **I11. `ErrorCard` crashes on `errored` runs.** Opening
  `#/runs/20260515-120623-prod-postgres-vs-sqlite` (a rate-limit-aborted
  Phase 2 run) blanks the entire detail view. React error boundary
  reports an exception inside `ErrorCard` at `run-detail.jsx:827`. The
  run's `error` field is well-formed (`{when, where, code, detail}`); the
  crash reproduces on `main` (verified by `git checkout main` round-trip
  during 0016 implementation). Not introduced by 0016. Out of scope; log
  as a follow-up — likely a one-line fix to the `<pre>` content rendering
  or to how `item.error` is destructured. Worth a small spec on its own.

## What I'm NOT proposing to change

- The `currentTurn.body` not streaming per-token. Section 11 of `frontend-state.md` already flagged this; it's a structural backend change (server-sent token deltas instead of file-watching) and is well beyond the spec-0016 scope.
- The SSE reconnect cadence. It didn't drop once across this run; the browser default is fine.
- The phase-0 chip's overall design — only the count behaviour.
- Anything cosmetic about palette / typography / brand marks (spec 0012 territory).

---

*Generated 2026-05-15 during integration testing. Companion to spec 0016.*
