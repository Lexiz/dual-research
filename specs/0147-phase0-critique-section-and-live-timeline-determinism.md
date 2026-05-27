---
spec: 0147
title: Phase 0 critique section grouping + live timeline rendering determinism
label: bug
version-bump: PATCH
status: ready
target-version: 1.12.1
created: 2026-05-21
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0147 — Phase 0 critique section + live timeline determinism

> Ship bucket: **Critique-panel + live-timeline UX polish.**
> Depends on: **0135** (Phase 0 multi-round negotiation that produces the
> Phase 0 critique items B01 wants surfaced), **0124** (critique-filter
> header parity — same `phase-tabs` row the new P0 tab joins),
> **0111** (critique-card bucket structure: openNew / openCarried /
> resolved / drift — the buckets the new P0 tab reuses verbatim),
> **0099** (timeline pane M3 rework — the polling-based "snapshot
> overwrite" model B04 lives inside).
> Complexity: **S** — one new tab in `CritiqueExplorer`, one allow-list
> entry, one rendering-contract comment block + a deterministic
> "round-completed-through" floor in `buildLiveTimeline`.
> Targeted version bump: **PATCH (1.12.0 → 1.12.1)** — no protocol or
> wire-format changes; one additive UI tab, one tightening of an
> existing branch.

---

## Context

Two small UX issues in the critique-adjacent surfaces, merged because
they both touch `CritiqueExplorer` / `buildLiveTimeline` and the visual
changes need to ship together to keep "Phase 0 is a first-class
negotiated phase" coherent.

**B01 — Phase 0 section missing from the Critique panel.** The
critique pane already has dedicated phase tabs for Phase 2 (Negotiate)
and Phase 4 (Review). Since spec 0135 promoted Phase 0 to a full
multi-round negotiation that emits questions + disagreements (the same
item kinds Phase 2 emits), the Critique pane should now have a Phase 0
tab too. Currently a finished run that surfaced Phase 0 critique items
has nowhere to view them in the Critique pane — they only show up
inline on the timeline turn cards. Acceptance (from the backlog): a
finished run with Phase 0 critique items shows a Phase 0 tab in the
Critique pane listing every Phase 0 question + disagreement.

**B04 — Live timeline rendering is non-deterministic.** While a run is
in flight, the timeline sometimes surfaces each round's per-turn card
as it lands, and sometimes appears stuck until the phase ends — at
which point the Critique pane suddenly fills with category cards "in
bulk". The contract isn't documented and isn't enforced. Root cause is
the poll-snapshot model: `useLiveRun` polls `/api/runs/<id>` every 5 s
and overwrites the local `run` state wholesale; whether a given poll
catches `phase: 2, round.current: 3` vs `phase: 3, round.current: 1`
depends on race between the aggregator's `phaseStats[phase2][3]` write
and the per-phase transition. `buildLiveTimeline` then renders
`Math.max(0, cur - 1)` completed rounds, which is correct in the
steady state but produces a visible flicker on the phase-completion
poll where `cur` has already advanced past the just-finished round.

Decide and enforce a single rendering contract — **per-turn cards
become visible as soon as `phaseStats[phaseX][round]` is non-empty for
that (round, agent) pair, and the phase header advances only after
every round of the previous phase is materialised** — and apply it
uniformly across Phase 0, Phase 2, and Phase 4.

## Current-state audit

### Critique-pane phase grouping (B01)

| File | Line | Role |
|---|---|---|
| `src/dual_research/ui/static/run-detail.jsx` | 5976–5980 | `CritiqueExplorer.initial` picks `selectedPhase` from `{2, 4}` only; Phase 0 is unrepresented in the initial-tab logic. |
| `src/dual_research/ui/static/run-detail.jsx` | 6254–6272 | The phase-tabs row inside `<header className="bar1">` renders exactly two phase buttons (P2, P4) + a Summary tab. No P0. |
| `src/dual_research/ui/static/run-detail.jsx` | 3698–3705 | `PHASE_CHIP_ALLOWLIST[0] = []` — Phase 0 is allow-listed as having **no** chip kinds. Stale post-0135. |
| `src/dual_research/ui/static/run-detail.jsx` | 6024–6028 | `CritiquePhaseContent` filters questions / disagreements / issues / comments by `it.phase === selectedPhase`. The backend already emits `phase: 0` items for spec-0135 negotiated briefs — the rendering branch is just gated out by the missing tab + empty allow-list. |
| `src/dual_research/ui/static/run-detail.jsx` | 6539 | `CritiquePhaseContent` early-returns a "pending" placeholder when `run.phase < phaseId`; current text "Negotiation hasn't started yet" assumes phaseId === 2 — needs a Phase 0 branch too. |

The plumbing already works: `_normalizeToThread` (run-detail.jsx
:6419), `findLedgerEntry`, `findLedgerGhostRounds` all key off
`it.phase` agnostically. The missing pieces are purely the entry-point
trio (tab button + allow-list + initial-tab guard + pending-text
branch).

### Live-timeline render path + non-determinism source (B04)

| File | Line | Role |
|---|---|---|
| `src/dual_research/ui/static/live-data.jsx` | 50 | `DETAIL_POLL_MS = 5000` — the wholesale-snapshot poll cadence. |
| `src/dual_research/ui/static/live-data.jsx` | 70–142 | `useLiveRun` — polls `/api/runs/<id>` and overwrites `run` on every successful tick. Replaces SSE. |
| `src/dual_research/ui/static/live-data.jsx` | 96–98 | `setRun(data)` — snapshot overwrite. No event ordering, no diff. |
| `src/dual_research/ui/static/live-data.jsx` | 469–796 | `buildLiveTimeline(run)` — derives the timeline items from the snapshot. |
| `src/dual_research/ui/static/live-data.jsx` | 504–544 | Phase 0 live branch: `completedThrough = st === 'running' ? Math.max(0, cur - 1) : Math.max(cur, p0StatsRoundCount)`. Note the asymmetry: when running, it trusts `cur - 1`; when stopped, it tops up with `phaseStats` round count. |
| `src/dual_research/ui/static/live-data.jsx` | 625–657 | Phase 2 live branch with the **same** `Math.max(0, cur - 1)` while-running rule. |
| `src/dual_research/ui/static/live-data.jsx` | 725–758 | Phase 4 live branch, same rule. |
| `src/dual_research/ui/static/live-data.jsx` | 802–878 | `attachItemStats` — runs after the timeline is built, walks items, hangs `item.stats` off `run.phaseStats`. Critique items themselves are not gated on `phaseStats`; they ride along on `run.questions` / `run.disagreements`. |

The non-determinism source is the `cur - 1` floor: it trusts
`run.round.current` as the source of truth for "how many rounds have
completed". On the phase-completion poll, the aggregator advances
`run.phase` (0 → 1, 2 → 3, 4 → 5) and resets `run.round.current` to
the next phase's round 1 in the same snapshot. The timeline for the
just-finished phase then has to fall back to the
`phaseStats[phaseX]`-keyed round count (the `else if (ph >= 3 || st
=== 'completed' || st === 'deadlocked')` branch — live-data.jsx:658),
which is correct but visually different from the in-flight branch.
Meanwhile `run.questions` / `run.disagreements` for the just-finished
phase land in the same snapshot, populating the Critique pane in a
batch. The user sees "nothing surfaces until the phase ends, then
everything appears at once."

## Proposed change

### 5.1 Phase 0 critique section grouping (B01)

Three small JSX edits in `src/dual_research/ui/static/run-detail.jsx`,
plus one allow-list update:

1. **Add P0 to the phase-tabs row** (run-detail.jsx:6253–6272):

   ```jsx
   <div className="phase-tabs">
     <button
       className={`phase-tab${selectedPhase === 0 ? ' is-active' : ''}`}
       onClick={() => setSelectedPhase(0)}>
       <span className="pcode">P0</span><span className="pname">Brief</span>
     </button>
     <button
       className={`phase-tab${selectedPhase === 2 ? ' is-active' : ''}`}
       onClick={() => setSelectedPhase(2)}>
       <span className="pcode">P2</span><span className="pname">Negotiate</span>
     </button>
     <button
       className={`phase-tab${selectedPhase === 4 ? ' is-active' : ''}`}
       onClick={() => setSelectedPhase(4)}>
       <span className="pcode">P4</span><span className="pname">Review</span>
     </button>
     …Summary…
   </div>
   ```

   No new CSS — `.phase-tab` is already a generic chip in
   `components.css`. The P0 button reuses the exact same style.

2. **Update the chip allow-list** (run-detail.jsx:3698):

   ```js
   const PHASE_CHIP_ALLOWLIST = {
     0: ['questions', 'disagreements'],  // spec 0135 + 0147
     1: ['questions'],
     2: ['questions', 'disagreements'],
     3: [],
     4: ['issues', 'comments', 'disagreements'],
     5: [],
   };
   ```

   Same kinds as Phase 2 (Phase 0 is a brief negotiation, structurally
   identical). Filter-row chips, status filters, and `_normalizeToThread`
   then "just work" for Phase 0.

3. **Default-tab guard** (run-detail.jsx:5974–5980):

   ```js
   const initial = (run.phase === 4 || run.phase === 2 || run.phase === 0) ? run.phase
                  : haveAny(4) ? 4
                  : haveAny(2) ? 2
                  : haveAny(0) ? 0
                  : 2;
   ```

   While a run is in Phase 0, the critique pane defaults to P0. After
   the run advances, the existing precedence (latest active > earliest
   has-items) takes over.

4. **Pending-text branch for Phase 0** (run-detail.jsx:6539–6557):

   ```js
   if (pending) {
     return (
       <div className="crit2__body" …>
         {phaseId === 0 ? <>Phase 0 hasn't started yet. The brief negotiation begins on run start.</>
         : phaseId === 2 ? <>…existing P2 text…</>
         : <>…existing P4 text…</>}
       </div>
     );
   }
   ```

   In practice `phaseId === 0` pending fires only in the half-second
   between "run created" and "Phase 0 round 1 begins"; the branch is
   defensive.

No design-system token additions. No new components. The new tab uses
the same `.phase-tab` class as P2 / P4; `<CritiquePhaseContent>` is
called with `phaseId={0}` and renders the four buckets verbatim.

### 5.2 Live timeline determinism (B04)

The rendering contract: **a per-turn card is visible iff its
`(phaseStats[phaseX][round], agent)` pair is non-empty.** The phase
header's "N rounds" badge counts only materialised rounds. Critique
items remain ride-along — they land in the same poll as the
`phaseStats` entries that emit the turn cards, so when the rounds
appear the items appear with them.

Concretely, in `buildLiveTimeline` (live-data.jsx:469):

1. **Replace the `cur - 1` floor with a `phaseStats`-derived floor.**
   For Phase 0 / 2 / 4, change the live-branch `completedThrough`
   computation from:

   ```js
   const completedThrough = st === 'running'
     ? Math.max(0, cur - 1)
     : Math.max(cur, pXStatsCount);
   ```

   to:

   ```js
   const completedThrough = st === 'running'
     ? Math.max(0, cur - 1, pXStatsCount - (pXHasInFlight(cur) ? 1 : 0))
     : Math.max(cur, pXStatsCount);
   ```

   where `pXHasInFlight(cur)` returns `true` iff the current round's
   slot in `phaseStats[phaseX][cur]` is partially populated (one agent
   present, not both, or `status: 'running'`). This means: rounds
   1..N-1 surface as soon as their `phaseStats` entries land,
   independent of `run.round.current` racing the snapshot.

2. **Live-card gating uses the same predicate.** A `turn-live` card
   for `(round = cur, agent)` is emitted only when
   `pXHasInFlight(cur)` is true AND the per-agent `phaseStats` slot
   for `(cur, agent)` is not yet "complete" (presence of `status:
   'AGREED' | 'NEGOTIATING'`-style terminal markers from the
   aggregator). When both agents complete, the live card flips to a
   completed `kind: 'turn'` on the next poll. This kills the flicker
   where `cur` advances and the live card briefly shows the wrong
   round.

3. **Phase-header badge** (live-data.jsx:511, 623, 723) — change the
   `extra: ` `${pXRounds} round${…}`` count to use the same
   "materialised rounds" count, so the header doesn't claim "3 rounds"
   while only 2 round cards have surfaced.

4. **Documented contract comment** at the top of `buildLiveTimeline`
   (live-data.jsx:464–468) — replace the current short comment with:

   ```js
   // ─────────────────── Live timeline builder ───────────────────
   //
   // RENDERING CONTRACT (spec 0147):
   //   - A per-turn card for (phase, round, agent) is visible iff
   //     run.phaseStats[phaseN][round][agent] exists.
   //   - A turn-live placeholder is emitted only for the in-flight
   //     (round, agent) pair: phaseStats slot is partial.
   //   - The phase-header "N rounds" badge counts only materialised
   //     rounds (the same predicate above).
   //   - Critique items (run.questions / run.disagreements / …)
   //     ride along in the same snapshot as the phaseStats entries
   //     that emit the turn cards: when the rounds appear, the items
   //     appear with them.
   //
   // This contract is enforced uniformly across Phase 0, Phase 2,
   // Phase 4 (the three multi-round phases). Phase 1 + Phase 3 are
   // single-shot per-agent renders, no rounds, no contract needed.
   ```

5. **Stable React keys** — verify that all `items.push({ id: 'pX-rR-AGENT', … })`
   ids are deterministic functions of `(phase, round, agent)` (they
   already are — see live-data.jsx:518, 522, 633, 636, 734, 737). No
   change here, just a confirming note in the contract comment that
   the keys are stable so React reconciles cards across polls
   correctly (the contract above relies on this — a flicker'd live
   card flipping to a completed card without remounting the DOM
   subtree).

The fix is one helper (`pXHasInFlight`), three call-site updates (P0,
P2, P4 live branches), and a comment block. No event-protocol change,
no SSE protocol change, no aggregator change.

## Out of scope

- **No broader critique-panel rework.** No changes to the bucket
  structure, the filter row, or the Summary view. Only the addition of
  the P0 tab + allow-list entry.
- **No SSE protocol change.** B04 is fixed inside the existing
  poll-snapshot model. We're not switching back to SSE, not adding an
  event-diff layer, not introducing a Redux-style reducer.
- **No design-system token additions.** The P0 tab reuses `.phase-tab`
  verbatim. No new colour, no new chip variant.
- **No backend change.** The aggregator already emits `phaseStats[phase0]`
  round-keyed entries (spec 0135). The contract is purely a UI-side
  reading discipline.
- **No change to Phase 1 / Phase 3 rendering.** They're single-shot
  per-agent renders; the determinism contract is vacuous for them.

## Test plan

- [ ] **Visual regression** (`tests/ui/test_critique_pane_phase0_tab.py`
  or equivalent under the existing UI test harness): load a finished
  run with Phase 0 critique items; assert (a) the P0 tab is present in
  `.phase-tabs`, (b) clicking it surfaces both questions and
  disagreements filtered to `phase === 0`, (c) the bucket structure
  (openNew / openCarried / resolved / drift) renders.
- [ ] **Deterministic-replay test** for `buildLiveTimeline`: a fixture
  array of three consecutive `run` snapshots representing
  poll-frame-1 (P2 r1 in flight), poll-frame-2 (P2 r1 complete, r2 in
  flight), poll-frame-3 (P2 r2 complete, P3 just started). Assert the
  rendered `items` array is monotonic — every card present in frame K
  has the same `id` and same `(round, agent)` attribution in frame K+1
  (no flicker). Assert specifically that the phase-2-r2 card does not
  disappear when `run.phase` advances to 3.
- [ ] **Same-input determinism**: build the timeline twice from the
  same `run` snapshot; assert byte-identical item arrays.
- [ ] **Empty-allow-list regression**: assert that
  `PHASE_CHIP_ALLOWLIST[0]` is `['questions', 'disagreements']` (not
  `[]`); a unit test on the module-level constant guards against an
  accidental revert.
- [ ] **Default-tab guard**: build `CritiqueExplorer` against a run in
  Phase 0; assert `selectedPhase === 0`. Against a Phase 2 run, assert
  `selectedPhase === 2`. Against a completed run with only Phase 0
  items, assert the fallback chain picks `0`.
- [ ] **Manual smoke**: fire a fresh `/dual-research-run` on a brief
  known to provoke Phase 0 disagreements; watch the timeline + critique
  pane in real time; confirm (a) per-turn cards appear in real time,
  one per agent per round, (b) the critique pane's P0 tab fills in
  parallel with the cards (no bulk-load-on-phase-end), (c) the phase
  header's round count never claims a round that has no card.

## Risks

- **Regression on other critique-pane sections.** Adding a P0 tab
  shifts the visual centre of gravity of `.phase-tabs`. CSS for the
  P2 / P4 buttons assumes a 2-tab + optional-summary layout; the new
  3-tab + optional-summary needs to not overflow the `.bar1` header on
  narrow viewports. Mitigation: P0 / P2 / P4 are 2-char codes + short
  names ("Brief" / "Negotiate" / "Review") — the row fits at the same
  min-width as today. A snapshot test at 1280 / 1024 / 800px viewport
  catches overflow.
- **SSE reconnection edge cases.** B04's fix is independent of
  reconnection — we already moved off SSE to polling (live-data.jsx:48).
  The poll-snapshot model is reconnection-safe by construction: a
  resumed poll just reads the next snapshot. The deterministic-replay
  test fixture should include a "skipped frame" case (frames 1 and 3
  without frame 2) to confirm no flicker.
- **Phase 0 items routing to the wrong tab.** Backend already emits
  `phase: 0` for spec-0135 items; pre-0135 transcripts emit
  `phase: 0` for legacy preflight critique only. The P0 tab will
  surface both kinds; an old transcript with `phase === 0` issues
  raised via the legacy single-shot path will appear here too. This
  is correct — historical runs benefit from the same surface. If it
  turns out to look noisy on very old runs, the per-tab item filter
  can extra-gate on `it.kind`.
- **Aggregator emit-order race.** The contract assumes `phaseStats`
  and `questions` / `disagreements` for a given phase land in the same
  snapshot. If the aggregator splits them across snapshots (one writes
  `phaseStats[phase2][3]` in frame K, the other writes
  `questions[X].phase = 2` in frame K+1), the user sees turn cards
  appear in frame K with no critique items, then items in frame K+1.
  Pre-empt with a one-poll-cycle assertion in the manual smoke: if the
  gap is reproducible, file a follow-up on the aggregator.

## Open questions

- None. The contract maps cleanly onto existing data shapes; the new
  P0 tab reuses the existing P2 codepath verbatim.
