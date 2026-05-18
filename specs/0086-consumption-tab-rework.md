---
spec: 0086
title: Consumption tab rework — phase headers above rows, single card per agent, no duplicate compact bar
label: refactoring
version-bump: PATCH
status: in-review
target-version: 0.69.10
created: 2026-05-18
pr: ""
---

# Spec 0086 — Consumption tab rework

## Context

The Consumption tab is the surface where the user reads how much token /
cost each agent burned per phase / round. The 2026-05-18 tweak-cycle
audit flagged two deltas as unshipped or only-partially-shipped:

- **Delta `20.14`** — [audit:2887](../../dual-research-automation/audits/2026-05-18-tweak-cycle-screenshot-audit.md:2887)
- **Delta `20.18`** — [audit:2974](../../dual-research-automation/audits/2026-05-18-tweak-cycle-screenshot-audit.md:2974)

Plus a **2026-05-18 follow-up** comment from the user during Spec 0085
review:

> "On the consumption tab, we have these overarching cards for each
> phase: Phase 1, Phase 2, and so on. In there, we show two additional
> cards for each of the models, which we're now going to streamline.
> I think that we are not making use of the horizontal space well,
> because the naming of the phases sits within the card. Phase 1 sits
> within the card on the left-hand side, and that eats up a lot of the
> available horizontal space for both of the model cards."

The user has provided this feedback several times across the audit, the
delta review, and now this follow-up. The previous attempt (Spec 0075,
delta 20.14 verdict) shipped *some* of the work — equal-height cards,
3-zone layout, cascade-on-expand, full-word vocabulary chips — but
deliberately kept the legacy `TokenLaneCell` compact-bar above each
expanded card, leaving a duplicated total-bar and the phase label
glued to the left edge of every row eating ~100 px of horizontal space
that the cards could use.

This spec finishes the job: **one card per agent per row** (no top-row
compact bar to duplicate it), **phase name lifted out of the row into
a group header above**, **round label compressed to a narrow leading
chip** only on phases that actually have rounds.

The five complaints in the original briefing, mapped to where they land
in this spec:

| User complaint | Status before this spec | Where addressed |
|---|---|---|
| Cards not equal height | Shipped (Spec 0075) | Preserved (§ B) |
| Group data points top, bars bottom | Shipped (Spec 0075) | Preserved (§ B) |
| Cascade-on-expand within same card | Shipped (Spec 0075) | Preserved (§ B) |
| Widen bars — reclaim slack between label and bar | **Not shipped** | § A + § B |
| Eliminate compact-bar / expanded-card duplication | **Not shipped** | § B |
| Phase name eats horizontal space (NEW feedback) | **Not addressed before** | § A |
| Multi-phase rhythmic consistency (delta 20.18) | Mostly shipped at collapsed level | § A + § C |

## Proposed change

### A. Lift phase name into a group header above the rows

Today every `<ConsumptionRow>` carries its own "Phase N · Name" label
inside its leftmost grid cell (only the first row per phase renders it,
but the **column persists across all rows** so the cards start at a
fixed x-offset of `var(--consumption-label-w) = 100px`). That column
is the horizontal space the user wants the cards to reclaim.

Refactor [`run-detail.jsx::ConsumptionView`](src/dual_research/ui/static/run-detail.jsx:1309)
to group its rows by `phase` and render each group as:

```jsx
<section className="consumption-phase-group">
  <header className="consumption-phase-header">
    <span className="consumption-phase-name">P2 Negotiate</span>
    <span className="consumption-phase-meta mono">17m 32s · 6 rounds</span>
  </header>
  <div className="consumption-phase-rows">
    <ConsumptionRow row={r1Row} ... />
    <ConsumptionRow row={r2Row} ... />
    ...
  </div>
</section>
```

`<ConsumptionPhaseHeader>` is a new small component. Visual treatment:
small uppercase mono name (`P2 NEGOTIATE`) + a faint right-anchored
meta line carrying duration + round count when present. The header is
NOT a clickable disclosure — it's purely informational, anchoring the
group of rows visually.

Drop the `showPhaseTitle` prop from `<ConsumptionRow>`; remove the
phase-name leg from the leftmost label cell.

### B. Single card per agent — no top-row compact bar

Today `<ConsumptionRow>` is a clickable `<button>` containing:

```
[ phase-label cell | TokenLaneCell (claude) | TokenLaneCell (gpt) | chevron ]
```

…and when expanded, `<ConsumptionRowExpanded>` inserts a SECOND grid
below that:

```
[ ConsumptionCard (claude) | ConsumptionCard (gpt) ]
```

The full card already shows the agent name + token stats + cost +
total bar + breakdown bars. The top-row `TokenLaneCell` shows the same
total bar a second time. The user has been clear that this is the
duplication they want gone:

> "the expanded card supersedes the top-row compact bar; there shouldn't
> be two copies of the same information."

**Rework**: collapse the two-tier structure into a single tier. The
row IS the pair of agent cards. The cards are click-to-expand surfaces
that disclose their breakdown bars internally — exactly like the
existing cascade-on-expand behaviour, but the OUTER wrapper goes away.

New `<ConsumptionRow>` shape:

```jsx
<div className="consumption-row" data-has-round={!!row.label}>
  {row.label && (
    <div className="consumption-round-chip">
      <span className="mono">{row.label}</span>
      {row.isRepair && <RepairChip />}
    </div>
  )}
  <ConsumptionCard
    usage={row.claude} agent="claude" phase={row.phase} run={run}
    scale={scale} reconcileReport={reconcileReport}
    expanded={expanded.has(row.id)}
    onToggle={() => toggleRow(row.id)}
  />
  <ConsumptionCard
    usage={row.gpt} agent="gpt" ...same shape (expanded + onToggle bound to row.id) />
</div>
```

`<ConsumptionCard>` gains two new props: `expanded` (bool, controlled
by the row) and `onToggle` (callback). When `expanded` is false, only
the data zone (header + cost-footer) + the total bar render; when
true, the breakdown bars + reuse overlay cascade below. The card's
clickable surface is the entire card chrome (a single `<button>`
wrapping the whole card body, identical to today's row-level button
but scoped to the card).

**Paired expansion (locked decision, 2026-05-18)** — both agent cards
in a row share a single `expanded` flag. Clicking either card toggles
both. Rationale: the user reviews Claude / GPT side-by-side at the
same round; opening one without the other adds visual asymmetry the
user explicitly chose against.

### C. Grid for the row — phase-dependent

Phases without rounds (0, 1, 3, 5 — single row per phase) need no
left chip; the cards span the full width:

```css
.consumption-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  align-items: stretch;
}
.consumption-row[data-has-round="true"] {
  grid-template-columns: var(--consumption-round-w) minmax(0, 1fr) minmax(0, 1fr);
}
```

New token in [`tokens.css`](src/dual_research/ui/static/tokens.css:137):

```css
--consumption-round-w: 64px;   /* enough for "Round 1" + RepairChip */
```

Drop or reduce the existing `--consumption-label-w: 100px` token (it's
no longer used by ConsumptionRow; keep it if any other surface
references it — `grep` first).

Visual outcome: Phase 0, 1, 3, 5 rows render with cards filling the
full pane width. Phase 2 / 4 rows render with a narrow 64px round
chip on the left, and the cards take the remaining ~95% of pane width.

### D. Card chrome — adapt to controlled disclosure

In [`run-detail.jsx::ConsumptionCard`](src/dual_research/ui/static/run-detail.jsx:1496),
wrap the existing card body in a `<button>` so the whole card is the
disclosure surface (same affordance as today's `<ConsumptionRow>`).
Add a chevron at the top-right of the card (small, 14 px) that
rotates when expanded — visually distinguishable from the existing
`<CardChevron>` row affordance.

The 3-zone layout stays exactly as it shipped in Spec 0075:

```
┌─ Zone 1: Data header ──────────────────── ▾ ─┐
│ ◆ Claude   86.5kt seen · 330.5kt billed     │
│ × 3.8 token reuse · (33.1% of 1M)  sort: ↓  │
├─ Zone 2: Cost row ──────────────────────────┤
│ Input $0.56 · Output $0.12 · Web $0.04      │
│ Total $0.72 · Searches: 4                   │
├─ Zone 3: Bars ──────────────────────────────┤
│ total input ▰▰▰▰▰▰▰▰▰▰▰▰▰  330.5kt           │
│   (if expanded:)                              │
│ User prompt ▰▰▰   70.1kt                     │
│ GPT P1 draft ▰     8.5kt                     │
│ ...                                          │
└─────────────────────────────────────────────┘
```

The cost row stays at top per Spec 0075 — the user accepted this in
the delta 20.14 audit. The `Searches: N` line stays.

### E. Repair siblings

Repair rows today get a slightly muted background + a `RepairChip` in
the label cell. After this spec the label cell is gone for repair
rows that don't carry a round (Phase 0 / 1 / 3 repairs) and the chip
needs a new home. Land it on the LEFT of the card's data-zone header
(a small chip just before the agent name) so the repair status is
still visually obvious. The muted background on the row stays.

For repair rows that DO carry a round (most repairs are Phase 2 /
Phase 4 retries), the round chip cell already exists — the
RepairChip renders next to the round label as it does today.

### F. Click-to-expand state shape

`ConsumptionView` keeps its existing `expanded: Set<rowId>` shape;
clicking either agent card in a row toggles the row-level flag and
both `<ConsumptionCard>`s in the row re-render with the same
`expanded` prop. No keying by agent.

```jsx
const [expanded, setExpanded] = React.useState(() => new Set());
const toggleRow = React.useCallback((rowId) => {
  setExpanded((prev) => {
    const next = new Set(prev);
    if (next.has(rowId)) next.delete(rowId);
    else next.add(rowId);
    return next;
  });
}, []);
```

No persistence to localStorage (matches today's behaviour — collapse
state resets on view change). Easy to add later.

### G. Phase header copy

`<ConsumptionPhaseHeader>` content per phase:

- **Phase 0** — `P0 PREFLIGHT · {duration}`
- **Phase 1** — `P1 RESEARCH · {duration}`
- **Phase 2** — `P2 NEGOTIATE · {duration} · {N} rounds`
- **Phase 3** — `P3 DRAFTING · {duration}`
- **Phase 4** — `P4 REVIEW · {duration} · {N} rounds`
- **Phase 5** — `P5 DONE · {duration}` (or `P5 FINAL` — match the
  Conversation tab's phase-strip label exactly)

Duration is derived from the row's per-agent `startedAt` / `endedAt`
timestamps (already present in `TurnTokenUsage` and surfaced on the
Conversation tab's phase strip; reuse the same helper). When a phase
hasn't started, omit the duration. When a phase has zero rounds (e.g.,
P2 / P4 that haven't started any rounds yet), omit the round count.

## Out of scope

- **Bar coloring** — output-slot colors (Spec 0051: `→ d1` blue,
  `→ hist` orange, etc.) stay exactly as they are.
- **Scale denominator caption** at the top of the tab — keep the
  existing "scale: Xkt · cap 1M · bars sized to the largest input in
  this run, not the full window" caption. Untouched.
- **Reconcile annotation** (`ProviderBilledLine`) — stays inside
  Zone 2 of `ConsumptionCard`. Untouched.
- **Comparison view** — if the Compare tab renders Consumption rows,
  it gets the same treatment via the shared component; verify but
  don't add per-Compare-tab styling.
- **Localisation of phase names** — English only, matching existing
  Conversation-tab labels.
- **Persisting expand state across navigation** — accepted as a
  follow-up.

## Test plan

- [ ] **Unit — phase grouping helper**: add a new test in
  [`tests/ui/test_consumption_view.py`](tests/ui/test_consumption_view.py)
  (create if absent) for a `groupRowsByPhase(rows)` helper that takes
  the existing `buildConsumptionRows` output and returns
  `[{phase, name, durationMs, rounds, rows}, …]`. Cover: a run with
  P0+P1+P2 (2 rounds)+P4 (3 rounds)+P5; a run that errored at P2 (no
  P3/P4/P5 groups); a run with a Phase 2 repair sibling.
- [ ] **Unit — round-chip presence flag**: assert that rows from
  Phase 0/1/3/5 have `label === ''` (no round chip in the new layout)
  and rows from Phase 2/4 have `label === 'Round N'`.
- [ ] **Manual — phase header above rows** (1440×900 + 2200×1300):
  partner-vetting `3a4a` → Consumption tab → each phase shows a
  group header line ABOVE the row(s), not inside the row. P2 Negotiate
  header reads `P2 NEGOTIATE · 17m 32s · 6 rounds` (or close — the
  duration and round count match the Conversation strip).
- [ ] **Manual — bars span full width**: P0, P1, P3, P5 rows now
  render with both agent cards filling the full pane width (no
  left phase-label gutter, no round chip). P2 / P4 rows render with
  a narrow 64 px `Round N` chip on the left and the cards taking the
  remaining width.
- [ ] **Manual — no duplicate total bar**: confirmed that each row's
  collapsed state renders the agent card with header + cost + total
  bar (only). There is NO separate top-row `TokenLaneCell` bar above
  the card. Click anywhere on the card → it expands and the
  breakdown bars cascade below the total bar within the same card.
- [ ] **Manual — independent per-agent expand**: click the Claude
  card on P2 R1 → only Claude expands (GPT stays collapsed beside
  it). Click GPT → both are expanded. Click Claude again → only GPT
  remains expanded. Heights still match (the row's
  `align-items: stretch` keeps both cards the same height; the
  shorter card has a bit of empty room below its total bar).
- [ ] **Manual — repair siblings**: a Phase 2 repair row renders
  with its `Round N` chip + `RepairChip` adjacent on the left (round
  label cell). A Phase 0 / 1 repair row (if any in the fixtures)
  renders the `RepairChip` inside the card's Zone 1 header, before
  the agent name. Muted row background still distinguishes it from
  the parent row.
- [ ] **Manual — "silent" agent**: any row where one agent didn't
  fire (e.g., Phase 5 GPT-only) shows the existing "silent this
  turn" dashed-border placeholder card in the missing-agent slot,
  same width as a real card. The row's other agent card stays at
  full size and doesn't try to fill the empty slot.
- [ ] **Manual — multi-phase rhythm (delta 20.18)**: scroll the
  Consumption tab top-to-bottom. Phase headers sit at consistent
  x=0 across every group; agent cards' left edges sit at consistent
  x within each group; total-input bars' left edges sit at
  consistent x within each card. No left-edge wobble across phases.
- [ ] **Manual — light + dark**: verify the phase header band
  styling reads in both themes (`--bg-2` background + `--fg-3`
  meta text). The chrome should be quieter than the rows, not
  louder.
- [ ] **Regression**: rerun `tests/` full suite (currently 800
  passing). Specifically `test_ui_jsx_syntax.py` should still pass
  after the `ConsumptionView` refactor.

## Risks

- **`align-items: stretch` interaction** with the new per-card
  disclosure. When only one of the two agent cards is expanded, the
  expanded card grows taller and `stretch` will scale the collapsed
  card to match. The user's spec calls for equal-height cards, so
  this is the expected behaviour — but the empty space below the
  collapsed card's total bar may feel awkward. Mitigation: confirm
  visually that the collapsed-but-stretched card has its content
  vertically centered or top-aligned (top-aligned is fine and matches
  the current behaviour).
- **`TokenLaneCell` orphan**. Once the top-row bar is gone, the
  `TokenLaneCell` component is only used by Compare (if at all) and
  potentially by the run-detail "summary" stats elsewhere. `grep` for
  references and delete the component if it's only used by the
  removed code path — otherwise leave it.
- **`--consumption-label-w` token**. Same — grep for references; if
  only `ConsumptionRow` used it, drop it from `tokens.css`.
- **Reconcile annotation positioning**. `<ProviderBilledLine>`
  renders inside `<ConsumptionCard>`'s Zone 2 today. Verify it
  still has enough horizontal room after the card widens; if it
  wraps awkwardly, consider moving it to its own row below Zone 2.
- **Compare tab regression**. If Compare uses `<ConsumptionRow>`
  directly (not just `buildConsumptionRows`), the API change will
  break it. Audit and update in this spec — don't ship a half-fix.

## Open questions

- ~~**Independent vs paired per-card expansion**~~ — **decided
  2026-05-18: paired**. Both cards in a row share one `expanded`
  flag; clicking either toggles both. Reflected in §B + §F above.
- **Phase header click behaviour**. Today the header is purely
  informational (no click). Should it be a "collapse all rows of
  this phase" affordance? Recommendation: skip for now; add only if
  the user asks for it after this lands.
- **Round-chip width 64 px**. Wide enough for "Round 1"
  (~52 px at 11 px mono) + a 6-px right padding. If repair rows pack
  `Round N` + `repair` together, the chip area may exceed 64. Bump
  to 80 px if needed during implementation.
- **Phase 0 and Phase 5 labelling**. Phase 0 currently shows
  "P0 Preflight"; Phase 5 currently shows just an empty label (the
  rows live under the `Σ Summary` tab's totals). Confirm the desired
  Phase 5 header copy during implementation — "P5 FINAL" feels
  better than "P5 DONE".
