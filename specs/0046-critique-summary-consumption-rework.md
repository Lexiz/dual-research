---
spec: 0046
title: Critique panel + Summary tab + Consumption tab rework + design unification
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.44.0
created: 2026-05-17
pr: "https://github.com/Lexiz/dual-research/pull/47"
---

# Spec 0046 — Critique panel + Summary + Consumption rework + design unification

## Context

The big visual rework. Specs 0042 / 0043 / 0044 made the underlying
data honest (parser coverage, taxonomy, cross-round ledger, ghosted
detection, per-turn deltas). Spec 0046 redesigns the surfaces that
*display* that data so the user can actually navigate it without
the inconsistencies the original feedback flagged. Three surfaces,
one design language.

### 1. Critique panel rework

The Critique pane today (after specs 0040 / 0041 / 0042 / 0043 / 0044)
has a header showing the run-total count, a phase-tab strip, a filter-
chip strip, and a per-phase content area showing critique cards. The
user's original feedback hit four problems:

1.1 **"99 introduced · 15 open · 21 resolved"** in the header is
    visually heavy on the "99" total and the math is hard to follow.
    User wants the three buttons (`Phase 2`, `Phase 4`, `Summary`) as
    the primary header anchor, with the counts subordinate / to the
    right. Spec 0042 D11 phase-scoped the math but the layout still
    leads with "Critique · 99 introduced".

1.2 **Filter chip labels** are static (`All / Issues / Questions /
    Disagreements / Comments`) regardless of which phase tab is
    active. Phase 2 has no Issues; Phase 4 has no Claims; etc.
    Showing zero-count filter chips for kinds the phase doesn't emit
    is noise. User asked for per-phase context-aware labels.

1.3 **Phase 4 cards render cryptic identifier strings.** Each card
    today shows `**C-1** — open — ` style text in the headline,
    plus a `R1→R2` round-transition marker and an `I-c-r1-01`
    internal ID chip. The user's complaint: "It feels like the
    formatting is off, with duplication of information. Just make
    sure that it's clear at batches, descriptive. Don't show simple
    letters."

1.4 **Per-card ghosted-N-rounds annotation is missing.** Spec 0043
    defined `GhostedAnnotation` but left wiring to spec 0046 (the
    visual rework). When the ledger surfaces a `ghostedRounds > 0`
    entry, the user needs to see `⚠ ghosted 3r` adjacent to the
    card headline so they know the agent never explicitly addressed it.

### 2. Summary tab redesign

The Summary tab today (spec 0040 D5) shows a per-phase table with
one row per round and columns `Q raised / Q answered / Q still open
/ D raised / D resolved / D still open / I raised / I resolved / I
still open / C noted`. The user's complaint:

> "Most of this table is empty, and it's very readable. Models are
> not there. Just think of a much better UI to represent this."

Two problems:
2.1 **Most cells are zero / dashes.** Phase 2 never has Issues; Phase
    4 never has Questions / Disagreements (mostly). The table renders
    them anyway, padding the layout with empty columns.
2.2 **No per-model breakdown.** The user wants to see "Claude raised
    N · GPT raised M · Claude resolved X · GPT resolved Y" per
    round per kind. Currently rolled-up totals only.

### 3. Consumption tab rework

The Consumption tab today (spec 0035) shows per-turn token usage
laid out as a two-column grid (Claude lane | GPT lane) of phase
rows. Expanding a row reveals per-input piece breakdowns. The user's
complaints:

3.1 **"Everything is jumping left to right. It just looks absolutely
    bad."** The expanded-row content renders BELOW the row (full
    width) instead of inline within the lane it belongs to, so the
    visual flow keeps reorienting.
3.2 **"Not used in this turn: …" rows are noise.** Spec 0045 D3
    handles this for the input full-view; Consumption tab has the
    same problem and same fix.
3.3 **Web-search section is confusingly duplicated.** Today reads:
    "web searches: 4 · of which web search: $0.0400". The phrase
    "of which web search" doesn't fit anywhere — there's no parent
    total it's "of which" to. User wants: cost section shows total
    cost, web-search section shows the count + its dedicated cost,
    no awkward phrasing.

### 4. Design unification

Across all three surfaces above (and the timeline pane's `Conversation
/ Consumption` tabs added in spec 0040), buttons use **three different
visual languages**:

- The phase tabs in Critique (`Phase 2 Negotiate · 26 Q · 10 D`)
- The Summary button (different border/background)
- The filter chips (`All / Issues / Questions / …`)
- The Conversation/Consumption pair (timeline pane toolbar)

The user explicitly called this out: "You need to find one uniform
design to do this so it looks clean."

Prior context:
- [Spec 0034](./0034-critique-navigation.md) — established the
  Critique pane shell.
- [Spec 0035](./0035-consumption-rework.md) — current Consumption
  tab layout.
- [Spec 0040](./0040-critique-rework.md) — compact critique cards,
  Summary tab introduction, Conversation/Consumption tab move.
- [Spec 0041](./0041-critique-classification-and-resilience.md) —
  Issue/Comment cards.
- [Spec 0042](./0042-critique-data-integrity.md) — phase-scoped
  `totalIntroduced`.
- [Spec 0043](./0043-cross-round-ledger-and-conservative-convergence.md) —
  ledger; `GhostedAnnotation` defined but not wired.
- [Spec 0044](./0044-turn-input-semantics-and-badge-redesign.md) —
  per-turn `+raised −resolved` chips (the design language this
  spec extends across the Critique pane).

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Critique pane header restructured: three primary buttons on the left, counts on the right.** | New layout: `[Phase 2] [Phase 4] [Summary]   ←——→   N introduced · X open · Y resolved`. The buttons are the top-level navigation; the count cluster is right-aligned. The "Critique" label moves to the pane's small chrome (or drops entirely if redundant). Math stays phase-scoped per spec 0042 D11. |
| D2  | **Per-phase context-aware filter chips.** | Active phase determines which kinds the filter strip shows. Phase 2 active → `[All \| Questions \| Disagreements \| Claims]`. Phase 4 active → `[All \| Issues \| Comments \| Disagreements]`. Summary active → no filter chips (the table renders all kinds in columns). Zero-count chips for kinds the phase doesn't have are suppressed even if the agent technically COULD emit them. |
| D3  | **Phase 4 (and Phase 2) cards render with human-readable headlines.** | Replace `**C-1** — open — Mutation testing gate lacks…` with `Issue C-1 · open · Mutation testing gate lacks a concrete enforcement mechanism`. The round-transition glyph `R1→R2` becomes part of an opt-in expanded view, not the always-visible headline. The internal `I-c-r1-01` ID moves to a hover-tooltip or the expanded body. Headlines are: `{Kind} {Public ID} · {status} · {body snippet}`. |
| D4  | **`GhostedAnnotation` wired into every critique card.** | When a card's corresponding ledger entry has `ghostedRounds > 0`, render `⚠ ghosted Nr` adjacent to the status pill. Tooltip explains the semantic ("Open for N rounds without an explicit addressing signal"). The `GhostedAnnotation` component already exists from spec 0043. |
| D5  | **Summary tab redesigned: per-round × per-model breakdown, no empty columns.** | Layout: per-phase section header (`Phase 2 — Negotiate` / `Phase 4 — Review`), per-phase table with rows = `(round, kind)` pairs and columns = `Claude raised / Claude resolved / GPT raised / GPT resolved / Open`. Kinds the phase doesn't have are excluded entirely (not rendered as zero rows). Per-round totals at the bottom. |
| D6  | **Consumption tab: single-row card with inline expand.** | Each phase-round row is one card; expanding it reveals per-piece breakdowns BELOW THE TOP BAR but INSIDE THE SAME CARD, not as a separate full-width section. Visual flow stays linear. |
| D7  | **Consumption tab: drop "not used in this turn" rows.** | Same fix as spec 0045 D3 for the input full-view. Empty pieces don't render at all. |
| D8  | **Consumption tab: web-search section restructured.** | Replace the duplicated "web searches: N · of which web search: $X" wording with a clean two-line structure: `Tokens: $A.AA  ·  Web search: $B.BB  ·  Total: $T.TT` (top line, costs) + `Searches: N  ·  Queries: M` (bottom line, counts). The "of which" phrasing is removed entirely. |
| D9  | **Uniform button design across panels.** | All toggle/tab/filter buttons in the Critique pane, the Summary surface, the Consumption tab toolbar, and the Conversation/Consumption pair use a single shared component (`PaneButton` or similar) with the same border, padding, font, hover/active states. Differences become semantic (active vs hover vs disabled) instead of cosmetic (one panel's border is 1px solid grey, another's is 1px dashed accent, etc.). |
| D10 | **No backend changes.** | All wire data is already exposed: `Run.phaseLedgers` (spec 0043), `Run.questions / disagreements / claims / issues / comments` (specs 0042+), per-turn token usage (spec 0029), web-search audit (spec 0036). Pure UI consumption. |

## Proposed change

### 1. Critique pane header — D1

`CritiqueExplorer` (in `run-detail.jsx`) currently renders:

```jsx
<PaneHeader
  title="Critique"
  count={`${totalIntroduced} introduced`}
  right={<><SmallStat label="open" .../> <SmallStat label="resolved" .../> <LedgerDriftChip .../></>}
/>
<PaneToolbar>
  {tabs.map(...)}
  {isTerminal && <CritiquePhaseTab tab={summaryTab} .../>}
</PaneToolbar>
```

After spec 0046:

```jsx
<PaneHeader
  // No title. The buttons ARE the navigation.
  left={
    <PhaseButtonGroup>
      <PaneButton active={selectedPhase===2} onClick={...}>Phase 2</PaneButton>
      <PaneButton active={selectedPhase===4} onClick={...}>Phase 4</PaneButton>
      {isTerminal && (
        <PaneButton active={selectedPhase==='summary'} onClick={...}>Summary</PaneButton>
      )}
    </PhaseButtonGroup>
  }
  right={
    <CountCluster>
      <SmallStat label="introduced" value={totalIntroduced} />
      <SmallStat label="open" value={totalOpen} color={...} />
      <SmallStat label="resolved" value={totalResolved} color={COLORS.ok} />
      <LedgerDriftChip drifts={run.drifts} phaseId={selectedPhase} />
    </CountCluster>
  }
/>
```

The `PaneToolbar` for filter chips drops to a second row below the
header, sharing the same vertical rhythm as the new toolbar in the
Summary / Consumption tabs.

### 2. Per-phase context-aware filter chips — D2

The filter chip strip already conditionally renders based on which
kinds have non-zero counts (the spec 0041 D5 + spec 0042 D5
combination). Tighten so that:

```js
function filterChipsFor(phaseId, run) {
  if (phaseId === 'summary') return [];
  const allowed = PHASE_CHIP_ALLOWLIST[phaseId] || [];
  const labels = {
    claims: 'Claims',
    questions: 'Questions',
    disagreements: 'Disagreements',
    issues: 'Issues',
    comments: 'Comments',
  };
  return ['all', ...allowed].map((k) => ({
    id: k,
    label: k === 'all' ? 'All' : labels[k],
  }));
}
```

Phase 2: `[All | Questions | Disagreements | Claims]`. Phase 4:
`[All | Issues | Comments | Disagreements]`.

### 3. Card headlines — D3

`QuestionCard`, `DisagreementCard`, `IssueCard`, `CommentCard`,
and the new `ClaimCard` (spec 0042) all currently render their
headline with the raw markdown body. Spec 0046:

```jsx
function CardHeadline({ kind, publicId, status, body, ghostedRounds }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span className="mono" style={{ color: 'var(--fg-3)', fontSize: 10.5 }}>
        {kindLabel(kind)} {publicId}
      </span>
      <span style={{ color: 'var(--fg-3)' }}>·</span>
      <StatusInline label={status} />
      <span style={{ color: 'var(--fg-3)' }}>·</span>
      <span style={{
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        flex: 1, color: 'var(--fg-0)',
      }}>
        {truncateBody(stripMarkdown(body), 70)}
      </span>
      {ghostedRounds > 0 && <GhostedAnnotation ghostedRounds={ghostedRounds} />}
    </div>
  );
}
```

`publicId` is the canonical short ID (`C-1`, `D-3`, `Q-c-r1-01`,
etc.); the internal `I-c-r1-01` etc. moves to the expanded body's
debug section.

`kindLabel`: `question → Question`, `disagreement → Disagreement`,
`issue → Issue`, `comment → Comment`, `claim → Claim`. Stop using
single-letter abbreviations in the visible headline.

`stripMarkdown(body)` removes the `**` markers and any leading
status prefix the agent included (so `**C-1** — \`open\` —
Mutation testing gate` doesn't render the prefix twice).

### 4. `GhostedAnnotation` wiring — D4

Already-defined component from spec 0043. Add the prop-flow:

```js
function findLedgerEntry(run, phaseId, itemId) {
  const entries = (run?.phaseLedgers && run.phaseLedgers[phaseId]) || [];
  return entries.find((e) => e.id === itemId);
}

// Inside each card render:
const ledgerEntry = findLedgerEntry(run, phaseId, item.id);
const ghostedRounds = ledgerEntry?.ghostedRounds || 0;
<CardHeadline ... ghostedRounds={ghostedRounds} />
```

### 5. Summary tab — D5

`SummaryContent` rewrite:

```jsx
function SummaryContent({ run, phaseId }) {
  // For each phase the user can see (2 and/or 4), render a section:
  return (
    <div>
      <SummarySection phase={2} run={run} kinds={['question', 'disagreement', 'claim']} />
      <SummarySection phase={4} run={run} kinds={['issue', 'comment']} />
    </div>
  );
}

function SummarySection({ phase, run, kinds }) {
  // Group ledger entries by round + kind + raiser.
  // Render table with columns: Round | Kind | Claude raised |
  // Claude resolved | GPT raised | GPT resolved | Open.
  // Kinds the phase doesn't have are excluded.
  ...
}
```

Empty rounds + kinds are excluded. The per-round totals at the
bottom of each section give the at-a-glance "this phase had 26
questions raised, 11 answered, 15 open".

### 6. Consumption tab single-row card — D6

`ConsumptionRow` rewrite. Today the row renders the per-lane bars
inline + opens a separate `<details>` element below for the per-
piece breakdown. After spec 0046:

```jsx
function ConsumptionRow({ row }) {
  const [expanded, setExpanded] = React.useState(false);
  return (
    <div style={{
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-2)',
      background: 'var(--bg-0)',
      padding: '12px 14px',
    }}>
      {/* Top bar: phase + round + lane bars (always visible) */}
      <ConsumptionRowTopBar row={row} expanded={expanded} onToggle={setExpanded} />
      {/* Expanded: per-lane piece breakdowns INSIDE the same card */}
      {expanded && <ConsumptionRowDetail row={row} />}
    </div>
  );
}
```

The detail content renders within the card's padded area (same width
as the top bar, no width jump). Per-lane breakdowns stack vertically
inside the card so the eye reads top-to-bottom in one column instead
of jumping left-right between separate panels.

### 7. Consumption tab "not used" + web-search restructure — D7, D8

`ConsumptionRowDetail` content changes:

```jsx
function ConsumptionRowDetail({ row }) {
  const piecesPresent = ['brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp']
    .map((key) => ({ key, label: PIECE_LABEL[key], tokens: row.pieces?.[key] || 0 }))
    .filter((p) => p.tokens > 0);  // D7

  return (
    <div>
      {piecesPresent.map((p) => <PieceBar key={p.key} {...p} />)}
      {/* D8 — costs cluster */}
      <CostsCluster
        tokens={row.tokenCost}
        searches={row.searchCount}
        searchCost={row.searchCost}
        total={row.cost}
      />
    </div>
  );
}

function CostsCluster({ tokens, searches, searchCost, total }) {
  return (
    <div className="mono" style={{ fontSize: 11, color: 'var(--fg-2)' }}>
      <div>Tokens: ${tokens.toFixed(2)} · Web search: ${searchCost.toFixed(2)} · Total: ${total.toFixed(2)}</div>
      <div>Searches: {searches} · Queries: {row.searchQueries || '—'}</div>
    </div>
  );
}
```

The "of which" phrasing is gone. Cost breakdown reads clean.

### 8. Uniform button design — D9

New shared component:

```js
function PaneButton({ active, hover, onClick, children, variant = 'default' }) {
  const [isHover, setHover] = React.useState(false);
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        appearance: 'none',
        border: `1px solid ${active ? 'var(--border-3)' : 'var(--border-1)'}`,
        background: active ? 'var(--bg-3)' : isHover ? 'var(--bg-2)' : 'var(--bg-1)',
        color: active ? 'var(--fg-0)' : 'var(--fg-2)',
        fontSize: 11,
        fontWeight: active ? 600 : 500,
        padding: '4px 12px',
        borderRadius: 'var(--r-2)',
        cursor: 'pointer',
        fontFamily: 'inherit',
      }}
    >
      {children}
    </button>
  );
}
```

Used by:
- Critique pane phase buttons (D1)
- Filter chips (D2)
- Conversation/Consumption tab pair (spec 0040)
- Summary tab (when active)

Replaces the disparate styling each currently has.

### 9. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.43.0 → 0.44.0.
- `CHANGELOG.md`: `## [0.44.0]` heading.
- `VERSION_NOTES` entry at the top of `how-it-works.jsx`:
  > **0.44.0 — Critique panel + Summary + Consumption rework + design
  > unification.** Critique pane header restructured with primary
  > phase buttons on the left and count cluster on the right.
  > Filter chips become per-phase context-aware (Phase 2 doesn't
  > show Issues, etc.). Critique cards render human-readable
  > headlines (`Issue C-1 · open · Mutation testing gate…`) with
  > the cryptic internal IDs moved to the expanded body. Ghosted-
  > rounds annotation surfaces on cards whose ledger entries
  > accumulated unaddressed-round count. Summary tab redesigned
  > as per-round × per-model breakdown with empty columns removed.
  > Consumption tab rebuilt as single-row cards with inline
  > expand; "not used in this turn" rows removed; web-search
  > section's confusing "of which" phrasing replaced with a clean
  > costs/counts cluster. All toggle / tab / filter buttons across
  > Critique, Summary, Consumption, and Conversation/Consumption
  > use one shared `PaneButton` component for visual consistency.

### 10. Files touched

Frontend:
- `src/dual_research/ui/static/run-detail.jsx` —
  - D1: `CritiqueExplorer` header rewrite
  - D2: `filterChipsFor` per-phase context
  - D3: `CardHeadline` shared component + per-card adoption
    (`QuestionCard`, `DisagreementCard`, `IssueCard`, `CommentCard`,
    `ClaimCard`)
  - D4: `GhostedAnnotation` wired via `findLedgerEntry`
  - D5: `SummaryContent` rewrite + new `SummarySection`
  - D6: `ConsumptionRow` rewrite (inline expand)
  - D7/D8: `ConsumptionRowDetail` + `CostsCluster`
  - D9: `PaneButton` shared component + adoption across surfaces
- `src/dual_research/ui/static/how-it-works.jsx` — VERSION_NOTES.

Backend:
- No changes.

Tests:
- Frontend-only; manual verification + 1-2 Python regression
  guards on the wire-format fields the new code reads (e.g. the
  Summary tab depends on `ledger.statusHistory[].round` being
  populated; assert in `tests/ui/test_aggregator_ledger.py`).

## Out of scope

- **A real "user prompt" field separate from the brief.** Spec
  0045 D4 + this spec both treat the brief as the user prompt.
- **Drift event drill-down UI.** Spec 0043's `⚠ drift` chip +
  tooltip remain the surface. If drift events become common
  enough to warrant a dedicated inspector, future spec.
- **Critique pane navigation history / breadcrumbs.** v1 stays
  flat: phase tab → filter chip → cards.
- **Inline editing of critique items.** Read-only view; agents
  generate the items.
- **Mobile responsive tightening.** The desktop layout is the
  v1 target. Mobile-specific tightening (column stacking,
  collapsed buttons) is a future spec.
- **A per-card "jump to ledger transition" affordance.** The
  ledger's `statusHistory` is on the wire (spec 0043); a UI for
  walking it round-by-round on a single card is a follow-up.
- **Cost reconciliation against provider invoices.** Spec 0039
  noted this as a future "cost reconciliation harness" spec;
  unaffected by spec 0046.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec adds 1-2 wire-
      format regression-guard tests.
- [ ] Manual: critique pane header reads `[Phase 2] [Phase 4]
      [Summary]   ←→   N introduced · X open · Y resolved`. Phase
      tabs are visually consistent with filter chips and with the
      Conversation/Consumption pair.
- [ ] Manual: Phase 2 active → filter chips read `[All | Questions
      | Disagreements | Claims]` (no Issues, no Comments). Phase 4
      active → `[All | Issues | Comments | Disagreements]`.
- [ ] Manual: Phase 4 cards render with headlines like `Issue C-1
      · open · Mutation testing gate lacks a concrete enforcement…`
      instead of `**C-1** — open — …`. The internal `I-c-r1-01`
      ID is in the expanded body / hover, not the headline.
- [ ] Manual: a card whose ledger entry has `ghostedRounds > 0`
      shows `⚠ ghosted 3r` (or appropriate count) on the headline.
- [ ] Manual: Summary tab renders per-round × per-model tables.
      Phase 2 section shows Questions / Disagreements / Claims;
      Phase 4 section shows Issues / Comments. No empty columns.
- [ ] Manual: Consumption tab — each row is one card. Click to
      expand: detail content appears INSIDE the card, no width
      jump, no separate full-width panel. Pieces with zero tokens
      are not rendered. Cost line reads `Tokens: $… · Web search:
      $… · Total: $…`. Below: `Searches: N · Queries: M`.
- [ ] Preview-verified at `localhost:6173`.

## Risks

- **D3's "human-readable headline" change touches every critique
  card type.** A mis-applied `stripMarkdown` could double-strip
  formatting or eat actual content. Mitigation: add a Python
  regression test that calls the headline-cleaner on known card
  bodies and asserts the output shape.
- **D5's per-round × per-model Summary table can grow tall** on
  long runs (10+ rounds × 3 kinds × 2 agents per phase). Mitigation:
  collapse zero-activity rounds entirely; the existing pagination
  pattern stays.
- **D6's inline-expand Consumption rows change the existing
  click-target behaviour.** Users used to clicking the row label
  to expand may need to re-learn. Mitigation: the whole top bar
  becomes clickable; the chevron stays visible.
- **D9's uniform `PaneButton` may not fit every existing usage.**
  Some surfaces have icon-only buttons, others have count-bearing
  buttons. Mitigation: `PaneButton` accepts `children` (anything)
  + a `variant` prop for layout tweaks (icon-only padding, etc.).
- **D1's "drop the Critique title" risks the pane reading as
  unowned** — pane labels help users navigate. Mitigation: keep a
  small `Critique` label at the pane's top-left chrome (where the
  spec-0029 `PaneTitle` lives for other panes), separate from the
  in-pane button group.

## Open questions

- Whether the Summary tab should default-open on completed runs
  (currently it's a tab you click into). Some users want it as
  the landing page once a run is terminal; others want the
  Critique cards. Defer the default-tab decision to v1 user
  feedback.
- Whether to support a per-card "expand all" / "collapse all"
  control on the critique surface. v1 stays per-card; a bulk
  control adds complexity for an uncertain win.
- Whether to surface the per-card ghosted annotation as a filter
  ("show only ghosted items"). v1 surfaces it but doesn't filter
  on it. If real-run experience shows ghosting is common enough,
  add the filter.
