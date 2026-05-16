---
spec: 0040
title: Critique rework — Phase 4 answer linkage fix, compact cards, summary tab, timeline-pane re-alignment
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.38.0
created: 2026-05-16
pr: "https://github.com/Lexiz/dual-research/pull/41"
---

# Spec 0040 — Critique rework

## Context

Six items from a single user pass over the critique side of the
run-detail view. They are grouped because they touch the same UI
surface (`CritiqueExplorer`, `QuestionCard`, `DisagreementCard`,
timeline badges, and the `Timeline` pane's toolbar) and ship cheaper
together than as six PRs.

1. **Phase 4 questions never transition to `answered`.** A real bug.
   The protocol uses two different section headings:
   - Phase 2 round R+1: `## Answers to {other}'s open questions`
   - Phase 4 round R+1: `## Answers to {other}'s prior comments`

   The regex at
   [`ui/questions.py:69-72`](../src/dual_research/ui/questions.py)
   only matches the Phase 2 form (`"open questions"`). On every
   Phase 4 turn file the section is named
   `"prior comments"` (see `protocol/prompts.py:591`) so the answer
   list always comes back empty — every Phase 4 question stays
   `open` regardless of whether the next round answered it. Visible
   on the partner-vetting run's `Phase 4 · Review` tab where 74
   questions render as open with 0 resolved.

2. **Question / disagreement cards are too tall.** The card shows the
   full `body` (often 80–400 chars, multi-line) up front. Even with
   60+ items on a tab, scrolling is slow and scanning the headline
   shape of the critique is hard. The body should be one line by
   default with click-to-expand revealing the full text plus the
   quote / after / answer anchors.

3. **Cross-link to timeline isn't reliable on questions.** Spec 0034
   wired `onCardClick → onHighlight([raisedTurnKey, …], variant)` for
   both cards, but in practice the Phase 4 highlight rarely fires
   because the question body click target is the whole card surface,
   and the `q.raisedTurnKey` / `q.answeredTurnKey` aren't always
   populated for Phase 4 (the answer-linkage bug above also blanks
   `answeredTurnKey`). Once D1 lands, ensure the same click that
   expands the card also highlights both endpoints on the timeline.

4. **Timeline plan/turn cards don't make answer activity legible.**
   Today the chip row shows `X Q · Y D`-shape numbers with the spec
   0034 round-over-round delta (`+1, -2`). The "answered N questions"
   count is implicit in the negative delta but a reviewer scanning the
   timeline can't quickly tell *how many of the prior round's
   questions this turn answered*. Add an explicit `answered N`
   annotation when the turn closed prior-round questions.

5. **No top-level summary view of the critique journey.** Today the
   right pane has `Phase 2 | Phase 4` tabs only. When the run is
   complete, a reviewer wants a one-screen overview: round-by-round
   counts of questions and disagreements (raised / answered / still
   open) across both phases. Add a `Summary` tab that appears once
   the run reaches a terminal state.

6. **`Conversation` / `Consumption` tabs are visually misplaced.**
   The Timeline pane has the title `Timeline · N artifacts` on the
   left of row 1 and the Claude pill on the right. Row 2 (the
   toolbar) currently has `[live-count] [flex] [Conversation |
   Consumption] [GPT pill]` — the tabs are right-aligned against the
   GPT pill, far from the "Timeline" label they belong to. Move them
   to the left edge of the toolbar so they sit directly under the
   "Timeline" title, where a reviewer naturally looks for them.

Prior context:
- [Spec 0034 — Critique navigation](./0034-critique-navigation.md):
  introduced first-class Questions parallel to Disagreements,
  cross-axis highlight wiring, the `CritiqueExplorer` rename.
- [Spec 0035 — Consumption rework + header-placement fix](./0035-consumption-rework.md):
  moved the Conversation/Consumption tabs back into the Timeline
  pane toolbar.
- [Spec 0038 — Web search audit UI + agent-pill alignment](./0038-web-search-audit-ui.md):
  flipped the GPT pill to the toolbar's right edge, which left the
  tabs awkwardly trapped against it.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Phase 4 question regex accepts both `"open questions"` and `"prior comments"`.** | The protocol uses two headings; the parser should recognise both. Fix is a 6-character regex change at `ui/questions.py:69-72`. No new data captured — the answers were always written; we just stopped reading them. |
| D2  | **Cards collapse to one-line headline by default.** | `QuestionCard` and `DisagreementCard` show the body clamped to `WebkitLineClamp: 1` in the header row. Click-to-expand reveals the full body plus the existing quote / after / answer block. Default state is collapsed; the active filter / phase tab change resets all cards to collapsed. |
| D3  | **Card click does two things: expand the card AND flash the timeline endpoints.** | Both behaviours run on the same click — no separate "highlight" affordance. Endpoints come from `raisedTurnKey` / `answeredTurnKey` (questions) and `raisedTurnKey` / `closedTurnKey` (disagreements). After D1, every Phase 4 answered question carries `answeredTurnKey` correctly. |
| D4  | **Timeline plan/turn chip row gains an `answered N` annotation.** | When `prevStats` has questions and the current turn answered some of them, the Q chip's tooltip surfaces the breakdown (`raised X · answered Y · still-open Z`) and the chip body adds a small `↩ N` glyph when N > 0. Renders only when the round-over-round delta is informative (round ≥ 2; round 1 has no prior to answer). |
| D5  | **`Summary` tab joins `Phase 2 \| Phase 4` once the run is complete.** | Visibility rule: `run.status === 'completed' \|\| 'deadlocked' \|\| 'errored'`. Body: a per-phase table laid out as one row per round, columns `[Round]` `[Questions raised]` `[Questions answered]` `[Still open]` `[Disagreements raised]` `[Resolved]` `[Still open]`. The tab is the rightmost of the three; clicking goes to the Summary view; existing per-phase content remains accessible via the other two tabs. |
| D6  | **Conversation / Consumption tabs move to the LEFT edge of the Timeline pane toolbar.** | New toolbar order: `[Conversation \| Consumption tabs] [live-count chip] [flex] [GPT pill]`. The tabs sit directly under the "Timeline · N artifacts" title in PaneHeader. No CSS additions; pure JSX re-order. |
| D7  | **Status filter survives the rework but is unchanged.** | The existing `All / Questions / Disagreements` filter strip stays on the right of the toolbar. No change needed. |
| D8  | **No data-model changes.** | Pure UI consumption of the existing `Run.questions` / `Run.disagreements` / `Run.phase_stats` shapes plus the bugfix path. The wire format gains nothing. |
| D9  | **No new tests on the UI side** (continues this repo's convention from spec 0033/0038). Backend tests cover the Phase 4 regex fix; the rest is manual UI verification. |

## Proposed change

### 1. Phase 4 answer-section regex — `src/dual_research/ui/questions.py`

```python
# Was:
r"^##\s+Answers to\s+" + re.escape(other_name) + r"['']?s open questions\b"

# Becomes (matches both Phase 2 and Phase 4 phrasings):
r"^##\s+Answers to\s+" + re.escape(other_name) + r"['']?s\s+(?:open questions|prior comments)\b"
```

No other change in `questions.py` — the answer-positional-matching, ID
shape, and `match='verbatim'/'positional'` quality signal all work
once the section is recognised.

### 2. Compact card layout — `run-detail.jsx::QuestionCard` + `DisagreementCard`

Header row (always visible):
- Type pill (`[Q]` info-blue or `[D-N]` warn-amber)
- Body clamped to one line (`WebkitLineClamp: 1`, `overflow: hidden`,
  `textOverflow: 'ellipsis'`)
- Status pill (`open` / `answered` / `resolved` / `held` / `escalated`)
- Round chip (`R{round}` or `R{open}→R{closed}` for closed disagreements)

Expanded body (revealed on click):
- Full `body` text, no clamp
- `quote:` block (if present)
- `after:` block (if present)
- `answer:` block (for answered questions only)
- Progression timeline (for disagreements only — already exists)

Both cards collapse on `phaseTab` change or `typeFilter` change (the
existing `useEffect` already resets `selectedPhase` and `typeFilter`
on `run.id` change; extend to reset card-open state via a `key` prop
that includes the phase + filter).

### 3. Click handlers — `run-detail.jsx`

Both cards already implement the dual-action pattern. Confirm:
- `QuestionCard` click → `onHighlight([raisedTurnKey, answeredTurnKey?], 'q')` AND `setOpen(o => !o)`
- `DisagreementCard` click → `onHighlight([raisedTurnKey?, closedTurnKey?], 'd')` AND `setOpen(o => !o)`

No code change needed beyond confirming behaviour after D1 lands —
the answered questions now carry `answeredTurnKey`, so the highlight
flashes BOTH cards instead of just the raised one.

### 4. Timeline chip annotations — `run-detail.jsx::StatsChips`

`StatsChips` currently renders `X Q (+a, -b)` style deltas. Extend
to surface an explicit `answered N` glyph:

```jsx
{prevQ && prevQ.open > 0 && (
  <span title={`raised ${stats.questions?.raised || 0} · answered ${answeredCount} · still-open ${stats.questions?.open || 0}`}
        style={{ color: 'var(--fg-3)', fontSize: 9.5, marginLeft: 4 }}>
    ↩ {answeredCount}
  </span>
)}
```

Compute `answeredCount = max(0, prevQ.open - (stats.questions?.openFromPrior || 0))`.
Where `openFromPrior` is the count of questions raised in PRIOR rounds
that are STILL open after this turn. The aggregator already exposes
the per-round question list via `run.questions` filtered by
`raisedRound < currentRound && answeredRound != currentRound &&
status === 'open'`.

### 5. CritiqueExplorer Summary tab — `run-detail.jsx::CritiqueExplorer`

New `SummaryTab` component renders only when
`run.status in {completed, deadlocked, errored}`. Tab strip becomes:

```
[Phase 2 · 26 Q · 10 D] [Phase 4 · 74 Q · 0 D] [Summary] ←── new, rightmost
```

`CritiquePhaseTab` already accepts `tab: { pid, label, …, pending,
active }`. Extend the renderer to handle a `pid: 'summary'` variant
that omits the Q/D counts and renders only the label.

`SummaryTab` body: a stacked table per phase.

```
Phase 2 — Negotiate
┌──────┬─────────┬──────────┬────────┬──────────┬──────────┬────────┐
│ Round│ Q raised│ Q answered│ Q open │ D raised │ D resolved│ D open │
├──────┼─────────┼──────────┼────────┼──────────┼──────────┼────────┤
│  1   │   12    │    —     │   12   │    4     │    —     │    4   │
│  2   │    8    │   10     │   10   │    3     │    2     │    5   │
│  …   │   …     │   …      │   …    │   …      │   …      │   …    │
└──────┴─────────┴──────────┴────────┴──────────┴──────────┴────────┘

Phase 4 — Review
[same shape]
```

Counts come from `run.questions` and `run.disagreements` filtered by
`(phase, round)`. `answered` is the count of questions whose
`answeredRound === round`; `resolved` is the count of disagreements
whose `closedRound === round`. Rounds with zero activity are omitted.

The Summary view's cards (one per row) are NOT clickable in v1 — the
aggregate view is informational; a reviewer who wants per-item detail
flips back to the Phase 2 / Phase 4 tab.

### 6. Timeline tabs alignment — `run-detail.jsx::Timeline`

```jsx
// Was (post-spec-0038):
<PaneToolbar>
  {liveCount > 0 && <LiveCountChip count={liveCount} />}
  <span style={{ flex: 1 }} />
  <TimelineTabs active={tab} onChange={setTab} prominent />
  <AgentStrip agent="gpt" run={run} />
</PaneToolbar>

// Becomes:
<PaneToolbar>
  <TimelineTabs active={tab} onChange={setTab} prominent />
  {liveCount > 0 && <LiveCountChip count={liveCount} />}
  <span style={{ flex: 1 }} />
  <AgentStrip agent="gpt" run={run} />
</PaneToolbar>
```

The tabs sit at the left edge of the toolbar, directly under
"Timeline · N artifacts" in the PaneHeader. GPT pill stays on the
right, vertically aligned with the Claude pill on row 1 (the spec
0038 alignment fix is preserved).

### 7. Tests

- `tests/ui/test_questions.py` — extend or add:
  - Phase 4 turn file with `## Answers to claude's prior comments`
    populated → reconstructed Question objects transition to
    `status='answered'` with `answeredTurnKey` populated.
  - Phase 2 turn file with `## Answers to claude's open questions`
    still works (regression guard).
- `tests/ui/test_aggregator_questions_and_anchors.py` — extend the
  existing Phase 4 happy-path test if it skips this check.
- No new frontend tests (project convention).

### 8. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.37.0 → 0.38.0.
- CHANGELOG.md: `## [0.38.0]` under `### Fixed / Added`.
- VERSION_NOTES entry at the top of `how-it-works.jsx` summarising
  the six bullets.

### 9. Files touched

Backend:
- `src/dual_research/ui/questions.py` — regex fix (D1).

Frontend:
- `src/dual_research/ui/static/run-detail.jsx`:
  - `QuestionCard` / `DisagreementCard` — compact-by-default layout (D2/D3).
  - `StatsChips` — `answered N` annotation (D4).
  - `CritiqueExplorer` — Summary tab + content (D5).
  - `Timeline` — toolbar re-order (D6).
- `src/dual_research/ui/static/how-it-works.jsx` — VERSION_NOTES.

Tests:
- `tests/ui/test_questions.py` (or equivalent) — Phase 4 answer
  recognition regression coverage.

## Out of scope

- **Restructuring the protocol prompts** to use a single section
  heading across phases. The current asymmetry was deliberate when
  spec 0028 introduced Phase 4 review (the "prior comments" framing
  is the right one for review-style feedback, not "open questions").
  Spec 0040 reads what's already written.
- **Auto-linking the Summary tab's row clicks back to the
  per-phase cards** (cross-tab navigation). The shipped pattern is:
  click Summary row → toast hint that says "open Phase 2 to see
  individual cards". v1 doesn't add deep links.
- **Saving the user's card-expanded state across phase-tab switches.**
  Default-collapsed on every switch is correct: when you switch from
  Phase 2 to Phase 4, the Phase 2 expansions don't carry meaning.
- **Showing the Summary tab during an in-flight run.** The numbers
  would shift each poll, and the value is the post-mortem overview.
  Wait until terminal state.
- **Phase 0 / Phase 1 critique surfaces.** Phase 0 has brief-critique
  responses, not structured questions. Phase 1 has independent
  drafts, no critique. The Summary tab is Phase 2 + Phase 4 only.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; D1 adds ≥1 Phase 4
      answer-recognition regression test.
- [ ] Manual: load the partner-vetting run. Phase 4 tab now shows
      a mix of `answered` and `open` (not all-open).
- [ ] Manual: click an answered Phase 4 question. The card expands
      AND both timeline cards (the raising turn + the answering
      turn) flash blue.
- [ ] Manual: open Phase 2 tab. Each card defaults to one-line
      headline; click expands. Toggle the type filter (`All /
      Questions / Disagreements`) — all cards reset to collapsed.
- [ ] Manual: load any pre-completion run (one in-flight) — the
      Summary tab is NOT visible.
- [ ] Manual: load a completed run (partner-vetting). Summary tab
      visible as the third tab. Click it: per-phase round-by-round
      table renders with Q raised / Q answered / Q open / D raised /
      D resolved / D open columns.
- [ ] Manual: on the Timeline pane, the `Conversation /
      Consumption` tabs sit on the LEFT of the toolbar row,
      directly under "Timeline · N artifacts". GPT pill remains on
      the right (vertically aligned with the Claude pill on row 1).
- [ ] Manual: on a Phase 2 turn card (e.g. round 3 Claude), the
      stats-chip row shows the Q chip with a small `↩ N` annotation
      indicating how many prior-round questions this turn answered.
      Tooltip on hover surfaces `raised X · answered Y · still-open Z`.
- [ ] Manual (replay safety): pre-0034 run with no `run.questions`
      data. Critique pane shows only Disagreements; Summary tab
      (if visible at all) renders only the D columns; no errors.

## Risks

- **D1 misses an edge case heading.** The regex now matches `"open
  questions"` and `"prior comments"`. If a future phase introduces a
  third phrasing the agent emits, it's a regex update. Mitigation:
  add a one-line comment near the regex naming both forms so a
  future maintainer adds new alternations in the right place.
- **Card collapse breaks the existing keyboard-walk pattern (j/k).**
  Currently the side-by-side review modals walk through cards via
  `j` / `k`. The CritiqueExplorer doesn't currently support keyboard
  walk; the rework doesn't add or remove that. Out of scope here.
- **Summary tab adds a third column to a narrow viewport.** The
  existing Phase 2 / Phase 4 tabs already wrap on ~720px viewports.
  Mitigation: `flex-wrap: wrap` on the tab container (carry
  forward from spec 0033). Verify at 1280px / 720px.
- **D4's `↩ N` annotation pollutes the chip row visually.** Each
  turn card's chip row is already dense. Mitigation: the annotation
  is a small (9.5px) subscript-style glyph only rendered when N > 0;
  rounds with no prior-round answer activity (round 1, refusals)
  stay unchanged.
- **The "completed run shows Summary" rule means a deadlocked or
  errored run still shows it.** Defensible — those runs DO have a
  critique journey worth summarising. Verified in D5's visibility
  rule (all three terminal states).

## Open questions

- Whether `answeredTurnKey` should preserve the round-on-round
  positional fallback when the verbatim-match heuristic fails. v1
  keeps the existing fallback (any positional match wins, with the
  `match: 'positional'` quality signal). If post-deploy review
  surfaces false-positive answer linkages, a tighter match rule
  (require ≥30% lexical overlap) is a follow-up spec.
- Whether the Summary tab should also be a printable / shareable
  surface (PDF export). Out of scope — the existing markdown render
  of `final.md` is the shareable artifact. The Summary tab is an
  in-app navigation aid.
