---
spec: 0133
title: Run-detail header rework — agent chips into Timeline pane, narrow-view critique compaction, M3 segmented phase progress
label: new-feature
version-bump: MINOR
status: proposed
target-version: TBD
created: 2026-05-20
pr: ""
---

> **Status:** carried in tree across the 0127→0131 arc as `NNNN-…md`. Filed as 0133 (status: proposed) by spec 0132's Phase 6 to remove untracked-file pollution. Not implemented; awaiting greenlight.

# Spec 0133 — Run-detail header rework: agent chips into Timeline pane + narrow critique compaction + M3 segmented phase progress

> Ship bucket: **Frontend-only restructure of the run-detail header chrome (spec 0107 surface).**
> Depends on: **0087** (`.as-timeline` width parity comment that anticipated this placement), **0107** (timeline + critique two-pane layout), **0112** (`.as-activity` ellipsis), **0119** (badge governance — `.chip` slot vocabulary), **0124** (critique filter row height parity + narrow compaction baseline), **0125** (existing `≤ 1499 px` kind-filter label collapse).
> Complexity: **M** — five coordinated changes in `run-detail.jsx` and `components.css`. No JS/contract/backend churn.
> Targeted version bump: **MINOR (1.5.2 → 1.6.0)** — the agent-bar row goes away as a visual element and the phase progress indicator is replaced. No behavior contract changes, but the visual surface shifts noticeably enough to warrant a minor bump.

---

## 1. Context

A live-mockup iteration with the user (rendered at `/tmp/dr-mockup/` against the actual `tokens.css` / `base.css` / `theme.css` / `components.css`) converged on five coordinated changes to the run-detail header chrome. They fall into three groups:

1. **The dedicated agent-bar row consumes a full row of vertical real estate to display two strips of information that can ride inside the existing pane headers.** [`TimelineAgentBar`](src/dual_research/ui/static/run-detail.jsx) at `run-detail.jsx:184-191` renders two `<AgentStrip className="as-timeline">` cards side-by-side inside `<div className="agent-bar">`, occupying ~50 px between the RunDetailHeader and the two-pane grid. The screen would benefit from reclaiming that row. The comment block at [`components.css:299-310`](src/dual_research/ui/static/components.css) is explicit about the originally intended placement: *"`.as-timeline` forces a fixed outer width so the Claude + GPT pills on the run-detail header read at IDENTICAL outer widths regardless of agent-name / model-name string length. They **live in separate flex containers (Claude on PaneHeader row, GPT on PaneToolbar row)** so flex-grow can't equalize them naturally."* That intent was rolled back into a shared `.agent-bar` parent (spec 0105) and the width-parity comment was preserved but the row layout was not. This spec restores the originally-anticipated placement.

2. **At narrow desktop widths (≈ ≤ 1280 px effective column width) the critique-pane header bars break.** Bar 1 (`.crit2 .bar1`) carries the title + three phase tabs + three counters; with `flex-wrap: wrap` (inherited from the shared `.crit2 .bar1, .crit2 .bar2` rule at `components.css:1872`), the right-cluster counters wrap to a second row at narrow widths, growing the bar past the height of the left-pane `.tl__head` and breaking the centre-divider seam. Bar 2 (`.bar2.crit-filter-row`) is `nowrap` per SPEC-0125 but the existing narrow rule (`components.css:712-720`) only collapses kind-filter chip labels — the status (Open / Resolved / Drift) and agent (Claude / GPT) chip labels still render, pushing the row past the column edge where it gets clipped. SPEC-0125 sized for two-label visibility; the chip set has grown since.

3. **The current `PhaseDots` indicator (`run-detail.jsx:665-702`) doesn't follow the active M3 design language.** Six 6 × 6 px circles connected by 12 × 1 px segments, with conditional `border` / `background` swaps for state — a 2024-era treatment that pre-dates the M3 design-system canonicalisation (SPEC-0127). M3 prefers segmented linear progress (small filled rounded bar segments with hairline gaps) for discrete-step progress over circle-and-line steppers.

All three issues are CSS / JSX-only. There is no protocol, contract, scheduler, queue, or backend change.

---

## 2. Goals

1. **Agent chips inside the Timeline pane headers — wide view.** Render the existing `AgentStrip` for Claude inside `<header className="tl__head">` and the one for GPT inside `<div className="tl__tabs">`, in both cases right-aligned via `margin-left: auto`. The right edges of the two chips share the same x-coordinate (the column's right-padding boundary). Both chips render at an identical outer width regardless of model-name length difference (`claude-sonnet-4-6` vs `gpt-5.5`). The dedicated `<div className="agent-bar">` row is removed from the DOM.

2. **Agent chip wide-view content.** Each chip renders `[logo] [model] · [tokens] · [cost] · [● activity phrase]`. The two trims relative to the live agent-bar are:
   - **Drop the agent name** ("Claude" / "GPT") — the logo carries identity and the model name disambiguates further.
   - **Cost to 2 decimals** — `$0.7099` becomes `$0.71`. The longest live activity phrase (`composeAgentActivity` in `run-detail.jsx:53-92`) is 22 characters (`drafting parallel plan` / `drafting converged doc` / `negotiating · round NN`); the chip's `min-width` is sized to fit it without truncation.

3. **Agent chip narrow view.** Below the same `1499 px` narrow-desktop breakpoint already in use (SPEC-0125), each chip drops the tokens and cost (and their separators) and keeps `[logo] [model] · [● activity phrase]`. Both chips lock to the same `width` (Claude's natural content width with the longest activity phrase, ≈ 380 px) so they remain visually equal-sized despite different content lengths. The Conversation / Consumption segmented control in `.tl__tabs` collapses to icons-only at the same breakpoint so the wider GPT chip has room alongside it.

4. **Critique-pane narrow compaction — Bar 1 (`.crit2 .bar1`).** Force `flex-wrap: nowrap` to prevent the counter cluster from wrapping. Hide phase-tab textual labels (`.pname`) so each tab is just its P-code (`P2` / `P4` / `Σ`). Hide counter textual labels (`.crit-totals .lbl`) so the right cluster is just three numbers. Tighten `gap` and `padding`. The bar must keep its `min-height: 53 px` and remain aligned with `.tl__head` across the centre divider.

5. **Critique-pane narrow compaction — Bar 2 (`.bar2.crit-filter-row`).** Extend SPEC-0125's kind-filter label collapse to the status filter cluster (Open / Resolved / Drift — identified by `.chip-dot` slot) and the agent filter cluster (Claude / GPT — identified by `.chip-leading-icon` slot). The dot color + agent icon already carry the identity; the text is redundant signal at narrow width.

6. **M3 segmented linear phase-progress indicator.** Replace the existing `PhaseDots` markup with a `.phase-progress` element containing N `<span className="phase-progress__seg">` cells (one per phase, currently five — P0 Preflight through P4 Review). Each cell is a 26 × 4 px rounded bar (border-radius 2 px) with a 3 px gap between cells. Cell state drives its background color via existing palette tokens: `--md-outline-variant` (track / pending), `--p-ok` (done), `--p-info` (current), `--p-err` (errored), `--p-warn` (deadlocked / drift). Replaces both the visual treatment and the imperative-style inline-styled JSX construction.

7. **`<Chip>` auto-dot collision fix (mockup parity → live JSX-or-CSS parity).** The upgraded `Chip` primitive (SPEC-0119, `shared.jsx:738`) auto-adds `.no-dot` whenever any slot prop is used so the `::before` auto-dot doesn't double up with `.cat-bubble` / `.chip-dot` / `.chip-leading-icon`. This is honored in the live JSX. The mockup work surfaced one location where the auto-dot still collides — the phase header's Q/D stat chips in `TlPhaseHeadChips` and the chips inside `tl-card-head` — both of which are constructed with `categoryBubble` props that the primitive should be suppressing. Audit those call sites; either confirm `no-dot` is being applied, or add a CSS-level safety net via `:has()` (Section 5.7).

All eight goals are visible in the side-by-side mockup at `/tmp/dr-mockup/index.html` served from `http://127.0.0.1:8765/`.

---

## 3. Non-goals

- **No change to `RunDetailHeader`** (`run-detail.jsx:117-139`) — topic + cost badge + reconcile chip + run-search summary + status-errors badge + phase-dots row. Those stay in place; this spec replaces only the agent-bar row immediately below and the phase-dots indicator within.
- **No change to the `<AgentStrip>` primitive** (`shared.jsx:884-914`) or to the `.as` / `.as-left` / `.as-right` / `.as-name` / `.as-model` / `.as-activity` base CSS in `components.css:279-326`. The relocation is achieved by adding a new `.as.in-header` modifier class that overrides only what's needed (no name display, tighter padding, content-natural sizing in narrow). The live agent-bar continues to use plain `.as.as-timeline` until removed.
- **No change to `composeAgentActivity`** (`run-detail.jsx:53-92`) — the phrase logic stays. The relocated chip continues to consume `phrase` + `live` via the `right` prop unchanged.
- **No new chip primitive variants in `shared.jsx`.** The narrow-view chip-label collapse is a CSS modifier gated by a `@media` rule, not a new `<Chip compact>` prop. Same pattern as SPEC-0125.
- **No change to `.tl__head` / `.tl__tabs` height contract.** They keep `min-height: 53 px` / `55 px` respectively per `components.css:2026 / 2039`. The relocated chip must fit within those heights — `align-self: center` and tight vertical padding on `.as.in-header` ensure it doesn't push them taller.
- **No change to filter chip click handlers, ordering, count semantics, hover tooltips, dim/active states, or keyboard focus order.** Only the visual presentation (label visibility) changes at narrow widths.
- **No change to the timeline turn cards (`.tl-card-head` / `TlTurnRow`)** or to the critique-pane card heads (`.crit-card-head`). SPEC-0124 governs those.
- **No change to the phase definitions** (PHASES const in `run-detail.jsx`) or to the phase progress *logic* — `phase`, `status`, `completed`, `current`, `failed` continue to drive cell state. Only the *visual treatment* swaps from circles-and-lines to filled bar segments.
- **No new breakpoint.** Reuse the existing `1499 px` narrow-desktop breakpoint already in use at `components.css:712` (SPEC-0125 kind-filter collapse) and `components.css:902` (`.agent-input` grid collapse). One breakpoint, one mental model.
- **No mobile / sub-900 px treatment.** The run-detail screen is desktop-only. A future spec can add a sub-900 px mode if needed.
- **No PhaseRail change** (`run-detail.jsx:712-731`). That component is a separate modal indicator and stays in its M3 cell-with-labels treatment.

---

## 4. Current-state audit

### 4.1 — The agent-bar row (Goal 1, 2, 3)

| Element | File | Lines | Current state |
|---|---|---|---|
| `<TimelineAgentBar>` JSX | [run-detail.jsx:184-191](src/dual_research/ui/static/run-detail.jsx) | 184–191 | `<div className="agent-bar">` wrapping two `<TimelineAgentPill agent="claude" />` / `agent="gpt"` |
| `<TimelineAgentPill>` JSX | [run-detail.jsx:146-181](src/dual_research/ui/static/run-detail.jsx) | 146–181 | Reads `run.agents[agent]`, composes activity, renders `<AgentStrip className="as-timeline" right={activityRight} />` |
| Render site of agent-bar | [run-detail.jsx:7234](src/dual_research/ui/static/run-detail.jsx) | 7234 | `<TimelineAgentBar run={run} />` sits between `<RunDetailHeader>` and `<main>` (the two-pane grid) |
| `.agent-bar` CSS | [components.css:2869-2875](src/dual_research/ui/static/components.css) | 2869–2875 | `display: flex; gap: var(--md-sp-6); padding: 8px 20px; background: var(--md-surface-container); border-bottom: 1px solid var(--md-outline-hair);` |
| `.as.as-timeline` CSS | [components.css:299-311](src/dual_research/ui/static/components.css) | 299–311 | `min-width: 460px; max-width: 720px; flex: 1 1 460px;` — sized for two-side-by-side agent-bar placement |
| `.tl__head` CSS | [components.css:2018-2025](src/dual_research/ui/static/components.css) | 2018–2025 | `display: flex; align-items: center; gap: 16px; padding: 10px 20px; background: var(--md-surface-container-high); border-bottom: 1px solid var(--md-outline-hair); min-height: 53px; flex-shrink: 0;` |
| `.tl__tabs` CSS | [components.css:2030-2038](src/dual_research/ui/static/components.css) | 2030–2038 | Same shape, `min-height: 55px`, `background: var(--md-surface-container)` |
| `composeAgentActivity` phrase set | [run-detail.jsx:53-92](src/dual_research/ui/static/run-detail.jsx) | 53–92 | Returns one of: `done`, `errored`, `deadlocked`, `waiting for {name}`, `waiting · phase N`, `idle`, `critiquing the brief`, `drafting parallel plan`, `drafting converged doc`, `negotiating · round N`, `reviewing · round N`, `finalising` |

Longest live phrase: 22 characters — `drafting parallel plan` / `drafting converged doc` / `negotiating · round NN`. The relocated chip's `min-width` is sized for that worst case.

### 4.2 — Cost formatting

| Element | File | Lines | Current state |
|---|---|---|---|
| `fmt.cost` helper | `src/dual_research/ui/static/shared.jsx` | grep `fmt = {` | Returns 4-decimal USD (e.g. `$0.7099`) |
| Call site (CostBadge) | [run-detail.jsx:595](src/dual_research/ui/static/run-detail.jsx) | 595 | `<span className="num">{fmt.cost(cost)}</span>` |
| Call site (AgentStrip → relocated) | [shared.jsx:903-907](src/dual_research/ui/static/shared.jsx) | 903–907 | Same `fmt.cost(cost)` |

This spec keeps `fmt.cost` at 4 decimals for the top-bar `CostBadge` and reconcile chip (where precision matters at the run-total level) and adds a per-agent rendering that uses 2 decimals (where the figure is already an approximation of provider billing and 4 decimals creates noise).

### 4.3 — Critique pane Bar 1 (Goal 4)

| Element | File | Lines | Current state |
|---|---|---|---|
| `<header className="bar1">` JSX | [run-detail.jsx:6086-6113](src/dual_research/ui/static/run-detail.jsx) | 6086–6113 | `<span className="ttl">Critique</span>` + `<span className="vbar"></span>` + `<div className="phase-tabs">` (3× `<button className="phase-tab">` with `<span className="pcode">` + `<span className="pname">`) + `<div className="right">` containing `<span className="crit-totals">` (3× `<span><span className="n">N</span><span className="lbl">label</span></span>`) |
| Shared `.bar1, .bar2` CSS | [components.css:1872-1876](src/dual_research/ui/static/components.css) | 1872–1876 | `display: flex; align-items: center; gap: 16px; padding: 10px 20px; flex-wrap: wrap;` |
| `.bar1` specifics | [components.css:1877-1880](src/dual_research/ui/static/components.css) | 1877–1880 | `background: var(--md-surface-container-high); border-bottom: 1px solid var(--md-outline-hair);` |
| `.crit2 .right` CSS | [components.css:1886](src/dual_research/ui/static/components.css) | 1886 | `margin-left: auto; display: inline-flex; gap: 16px; align-items: center; flex-wrap: wrap;` |
| `.crit-totals .n / .lbl` CSS | [components.css:1902-1903](src/dual_research/ui/static/components.css) | 1902–1903 | `.n` is 18 px semi-bold tabular; `.lbl` is 10 px uppercase, 0.08 em tracking, faint color |
| `.phase-tab` CSS | [components.css:1759-1786](src/dual_research/ui/static/components.css) | 1759–1786 | Pill-shaped, M3 state-layer, with `.pcode` + `.pname` slots |

The `flex-wrap: wrap` on both `.bar1` and `.right` is what makes Bar 1 grow to two rows at narrow widths.

### 4.4 — Critique pane Bar 2 (Goal 5)

| Element | File | Lines | Current state |
|---|---|---|---|
| `<header className="bar2 crit-filter-row">` JSX | [run-detail.jsx:6127-6197](src/dual_research/ui/static/run-detail.jsx) | 6127–6197 | 10 chips + 2 `<span className="crit-filter-spacer">` separators: Q / D / I / C (each `categoryBubble` + `value`), All (`value`), Open (`leadingDot` + `value`), Resolved (`leadingDot` + `value`), Drift (`leadingDot`), Claude (`leadingIcon` + label), GPT (`leadingIcon` + label) |
| `.crit-filter-row` base CSS | [components.css:693-699](src/dual_research/ui/static/components.css) | 693–699 | `flex-wrap: nowrap; padding: 10px 14px; min-height: 55px; gap: 8px;` |
| SPEC-0125 narrow rule | [components.css:712-720](src/dual_research/ui/static/components.css) | 712–720 | `@media (max-width: 1499px)` collapses kind-filter chip labels only via `data-kind-filter` attribute |
| `.chip` auto-dot | [components.css:169-180](src/dual_research/ui/static/components.css) | 169–180 | `.chip.tone-info/.tone-ok/.tone-warn/.tone-err/.tone-idle/.tone-muted::before` renders a 6 × 6 px dot; `.chip.no-dot::before { display: none }` suppresses it; the live `<Chip>` primitive auto-adds `.no-dot` when any slot is used (`shared.jsx:738`) |

The Open / Resolved / Drift chips use `leadingDot` → `.chip-dot`. The Claude / GPT chips use `leadingIcon` → `.chip-leading-icon`. Neither cluster has a CSS rule that collapses their labels at narrow widths — only the kind cluster does. The combined natural row width exceeds the column at narrow viewports, and `flex-wrap: nowrap` forces overflow → clip.

### 4.5 — Phase progress indicator (Goal 6)

| Element | File | Lines | Current state |
|---|---|---|---|
| `<PhaseDots>` JSX | [run-detail.jsx:665-702](src/dual_research/ui/static/run-detail.jsx) | 665–702 | `<div style={{ display: 'flex' }}>` with `{PHASES.map(p => <React.Fragment>{circle}{connector}</React.Fragment>)}` — each circle is a 6 × 6 px inline-styled span with conditional `background` / `border`, each connector a 12 × 1 px span |
| Render site | [run-detail.jsx:261](src/dual_research/ui/static/run-detail.jsx) | 261 | `<PhaseDots run={run} />` inside `<PhaseDotsRow>` immediately below the title |
| PHASES const | `src/dual_research/ui/static/run-detail.jsx` | grep `const PHASES =` | Array of phase definitions: P0 Preflight, P1 Parallel draft, P2 Negotiate, P3 Drafting, P4 Review, (P5 Reconcile — excluded from PhaseRail but included in PhaseDots — confirm during implementation) |

The component composes its style entirely via inline `style={{ ... }}` props. Replacement uses class-based styling for design-system parity.

### 4.6 — `<Chip>` auto-dot suppression audit (Goal 7)

| Element | File | Lines | Current state |
|---|---|---|---|
| `usesNewSlots` heuristic | [shared.jsx:738-744](src/dual_research/ui/static/shared.jsx) | 738–744 | `leadingDot != null \|\| leadingIcon != null \|\| categoryBubble != null \|\| iconOnly \|\| value != null \|\| add != null \|\| sub != null \|\| trailingSuffix != null \|\| dim \|\| mono \|\| label != null` |
| `.no-dot` class application | [shared.jsx:756](src/dual_research/ui/static/shared.jsx) | 756 | `suppressAutoDot && 'no-dot'` |
| Auto-dot CSS | [components.css:169-180](src/dual_research/ui/static/components.css) | 169–180 | See 4.4 above |

The live `Chip` should already suppress the auto-dot for every chip with a slot, but the mockup work surfaced visible double-dots in a few places (the phase header Q/D stat chips; the chips inside `tl-card-head`) suggesting either a call site is bypassing the `Chip` primitive or the `usesNewSlots` heuristic misses a slot variant. Implementation step: ten-minute audit of every `tone-info / tone-warn / tone-err / tone-idle / tone-muted` callsite to confirm the slot props are being passed (vs. children-only) — if any callsite passes `<Chip tone="info">{children}</Chip>` with no explicit slot, the auto-dot survives. If the audit finds none, the mockup-only `:has()` safety net in 5.7 is not needed in the live app and can be dropped from the spec.

---

## 5. Proposed change

### 5.1 — Relocate agent strips into Timeline pane headers (`run-detail.jsx`)

**Remove `<TimelineAgentBar>` render site** at [run-detail.jsx:7234](src/dual_research/ui/static/run-detail.jsx). The `<TimelineAgentBar>` and `<TimelineAgentPill>` function components stay defined (or get inlined — implementer's call) but the `agent-bar` parent and its row layout go away.

**Inside `<Timeline>` (around `run-detail.jsx:797`)** render the Claude pill inside `<header className="tl__head">` and the GPT pill inside `<div className="tl__tabs">`:

```jsx
<header className="tl__head">
  <span className="ttl">Timeline</span>
  <span className="ct">{artifactCount} artifacts</span>
  <TimelineAgentPill agent="claude" run={run} className="as in-header is-a" />
</header>

<div className="tl__tabs">
  <div className="tl__tabs-inner">
    <button … >Conversation</button>
    <button … >Consumption</button>
  </div>
  <TimelineAgentPill agent="gpt" run={run} className="as in-header is-b" />
</div>
```

The `className="as in-header is-a"` / `is-b` is the override knob: the same `<AgentStrip>` markup as today, just with an additional modifier class that the CSS layer (5.2) consumes to swap the layout from "two-side-by-side in agent-bar" to "one-per-row inside pane header".

`TimelineAgentPill` already passes a `className` prop to `<AgentStrip>` via spread, so the call-site `className` propagates. If the propagation isn't already in place, add a single-line change.

### 5.2 — `.as.in-header` modifier (`components.css`)

Append to the agent-strip block (after `components.css:326`, just below `.as-activity`):

```css
/* Spec NNNN — `.as.in-header` relocates the AgentStrip into a Timeline
   pane header (`.tl__head` for Claude, `.tl__tabs` for GPT). Relative
   to `.as-timeline` (the agent-bar placement), the chip:
   - Drops the agent name (logo + model carry identity).
   - Uses tight vertical padding so it never grows .tl__head / .tl__tabs
     past their `min-height` contract.
   - Right-aligns inside the row via `margin-left: auto`.
   - Sizes its `min-width` to fit the longest activity phrase
     (`drafting parallel plan` / `drafting converged doc` /
     `negotiating · round NN`) without truncation in wide mode.
   - Both chips share an identical wide-mode min-width so they appear
     equal-sized despite different model-name lengths. */
.as.in-header {
  min-width: 600px;
  max-width: 100%;
  flex: 0 0 auto;
  margin-left: auto;
  padding: 4px 24px;
  gap: 18px;
  border-radius: 999px;
  font-size: 13px;
  align-self: center;
}
.as.in-header .as-left  { gap: 16px; }
.as.in-header .as-right { gap: 16px; font-size: 13px; }
.as.in-header .as-name  { display: none; }      /* logo carries identity */
.as.in-header .as-model { font-size: 13px; }
.as.in-header .num      { font-size: 13px; }
```

### 5.3 — Narrow-view agent chip (`components.css`)

Append, gated on the same `1499 px` breakpoint as SPEC-0125:

```css
/* Spec NNNN — narrow-view AgentStrip compaction.
   Drop the tokens + cost slots (they read at the run-total level via
   CostBadge in the top bar); keep logo + model + activity. Both chips
   lock to the same `width` (Claude's natural content width with the
   longest activity phrase) so they remain visually equal-sized despite
   "gpt-5.5" being much shorter than "claude-sonnet-4-6". */
@media (max-width: 1499px) {
  .as.in-header {
    width: 380px;
    min-width: 0;
    max-width: none;
    padding: 4px 14px;
    gap: 10px;
  }
  .as.in-header .as-left  { gap: 10px; }
  .as.in-header .as-right { gap: 8px; }
  /* Hide every child of .as-right except the activity span (the last
     child). The .as-right contents are tokens, sep, cost, sep, activity
     — in that order — per AgentStrip's render in shared.jsx:891-913.
     The activity is always the last `right` slot, so :not(:last-child)
     hits the four token/cost-related children and leaves the activity
     visible. */
  .as.in-header .as-right > *:not(:last-child) {
    display: none;
  }

  /* The Conversation / Consumption segmented control labels can't share
     the .tl__tabs row with a 380 px chip — collapse to icons-only at
     the same breakpoint. `font-size: 0` collapses the text node next to
     the icon span; the icon span re-asserts its own font-size so the
     glyph remains visible. No HTML change needed. */
  .tl__tab {
    font-size: 0;
    gap: 0;
    padding: 0 10px;
  }
  .tl__tab .ms {
    font-size: 18px;
  }

  /* Bring the chip closer to the right edge — the shared .tl__head /
     .tl__tabs `padding: 10px 20px` is too generous in narrow when the
     chip is the dominant element on the right. */
  .tl__head,
  .tl__tabs {
    padding-right: 10px;
  }
}
```

### 5.4 — Cost formatting in the relocated chip

Two implementation options; recommend Option A.

**Option A (recommended) — local fmt at the call site.** Add a `formatCostShort` helper alongside `fmt` in `shared.jsx`:

```js
fmt.costShort = (n) => `$${Number(n || 0).toFixed(2)}`;
```

Use it inside `TimelineAgentPill` only:

```jsx
<AgentStrip
  …
  cost={cost}
  costFormatter={fmt.costShort}
  …
/>
```

This requires adding an optional `costFormatter` prop to `<AgentStrip>` that defaults to `fmt.cost` (the current 4-decimal behavior). Every other call site (CostBadge, ReconcileChip, etc.) remains unaffected.

**Option B — flag on AgentStrip.** Add a `<AgentStrip compactCost>` boolean prop and switch on it. Slightly less flexible than A but smaller surface area. Either is fine; A is closer in spirit to SPEC-0119's "primitive stays single-purpose, behavior is configured at the call site".

### 5.5 — Critique Bar 1 narrow compaction (`components.css`)

Append, same `@media (max-width: 1499px)` block:

```css
/* Spec NNNN — Critique Bar 1 narrow compaction.
   The shared `.bar1, .bar2 { flex-wrap: wrap }` rule wraps Bar 1's right
   cluster onto a second row at narrow viewports, blowing the height match
   with .tl__head. Force nowrap and drop redundant labels so the bar stays
   single-row at the same `min-height` as .tl__head. */
@media (max-width: 1499px) {
  .crit2 .bar1 {
    flex-wrap: nowrap;
    gap: 10px;
    padding: 10px 14px;
  }
  /* Phase tabs lose their textual label — the P-code / Σ glyph reads
     on its own and the active-tab tint disambiguates Negotiate vs Review
     vs Summary. */
  .crit2 .bar1 .phase-tab .pname {
    display: none;
  }
  /* Counter labels (uppercase "INTRODUCED / OPEN / RESOLVED") are signal
     at wide widths but redundant alongside the colored number; drop them
     in narrow, keep just the three numerals. */
  .crit2 .bar1 .crit-totals .lbl {
    display: none;
  }
  /* Prevent the right cluster itself from wrapping its three counters. */
  .crit2 .right {
    flex-wrap: nowrap;
    gap: 12px;
  }
}
```

### 5.6 — Critique Bar 2 narrow compaction (`components.css`)

Extend the existing SPEC-0125 narrow block at `components.css:712-720`:

```css
@media (max-width: 1499px) {
  /* … existing SPEC-0125 rules: gap 4px, padding 10px 10px,
     `.chip[data-kind-filter] .chip-label { display: none }` … */

  /* Spec NNNN — extend the kind-filter collapse to the status filter
     cluster (Open / Resolved / Drift) and the agent filter cluster
     (Claude / GPT). The dot color + agent icon carry the identity at
     this width; the text is redundant. */
  .crit2 .bar2.crit-filter-row .chip:has(.chip-dot) .chip-label,
  .crit2 .bar2.crit-filter-row .chip:has(.chip-leading-icon) .chip-label {
    display: none;
  }
}
```

`:has()` is widely supported (Chromium 105+, Safari 15.4+, Firefox 121+). The browser support floor for the live app is set elsewhere; confirm during implementation that `:has()` falls inside it. If not, switch to the `data-status-filter` / `data-agent-filter` attribute pattern (mirroring SPEC-0125's `data-kind-filter`) and key the rule off those — a one-line JSX change per chip.

### 5.7 — `<Chip>` auto-dot collision (audit + optional CSS safety net)

**Audit first.** Walk every `<Chip tone="info" | "ok" | "warn" | "err" | "idle" | "muted">` call site in `run-detail.jsx` and `shared.jsx` and confirm that the `Chip` primitive is being entered (not bypassed via raw markup) and that `usesNewSlots` at `shared.jsx:738` evaluates `true` for chips that should suppress the auto-dot. Specifically check `TlPhaseHeadChips` (`run-detail.jsx`, grep) and the chip array inside `tl-card-head` (`run-detail.jsx:1096-1159`).

**If the audit finds a gap**, the simplest fix is a CSS-level safety net that mirrors the JSX heuristic via `:has()`:

```css
/* Spec NNNN — safety net for the auto-dot vs slot collision.
   Mirrors shared.jsx:738 `usesNewSlots = leadingDot || leadingIcon ||
   categoryBubble || value || label || …`. Active even when a callsite
   bypasses the Chip primitive (which it shouldn't, but spec 0119
   governance allows). */
.chip:has(.chip-label)::before,
.chip:has(.chip-value)::before,
.chip:has(.chip-dot)::before,
.chip:has(.cat-bubble)::before,
.chip:has(.chip-leading-icon)::before {
  display: none;
}
```

If the audit finds no gap, drop 5.7 from the spec. Either way, the user-visible result is no double-dot anywhere on the run-detail screen.

### 5.8 — M3 segmented phase-progress indicator (`run-detail.jsx` + `components.css`)

**CSS — append to `components.css` near the timeline / critique chrome rules:**

```css
/* Spec NNNN — M3 segmented linear phase-progress indicator.
   Replaces the legacy <PhaseDots> circles-and-lines treatment. One
   segment per PHASES entry; the segment's state class drives its
   color via the existing palette tokens. The current segment may carry
   the `.pulse-info` animation already defined in base.css if a subtle
   live-state cue is desired. */
.phase-progress {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
}
.phase-progress__seg {
  width: 26px;
  height: 4px;
  border-radius: 2px;
  background: var(--md-outline-variant);
  transition: background var(--m-base) var(--ease);
}
.phase-progress__seg.is-done    { background: var(--p-ok); }
.phase-progress__seg.is-current { background: var(--p-info); }
.phase-progress__seg.is-error   { background: var(--p-err); }
.phase-progress__seg.is-warn    { background: var(--p-warn); }
```

**JSX — replace `<PhaseDots>` at `run-detail.jsx:665-702`:**

```jsx
function PhaseDots({ run }) {
  const { phase, status } = run;
  return (
    <div className="phase-progress" aria-label="Run progress">
      {PHASES.map((p) => {
        const completed = p.id < phase || (status === 'completed' && p.id <= 5);
        const current   = p.id === phase && status !== 'completed';
        const failed    = (status === 'errored' || status === 'deadlocked') && p.id === phase;
        const cls = ['phase-progress__seg'];
        if (failed && status === 'errored')    cls.push('is-error');
        else if (failed && status === 'deadlocked') cls.push('is-warn');
        else if (current)                       cls.push('is-current');
        else if (completed)                     cls.push('is-done');
        return (
          <span
            key={p.id}
            className={cls.join(' ')}
            title={`${p.short} ${p.label}${
              completed ? ' · done' :
              current   ? ' · in progress' :
              failed    ? ` · ${status}` :
              ' · pending'
            }`}
          />
        );
      })}
    </div>
  );
}
```

Note that the same state-machine logic from the old `PhaseDots` (`completed`, `current`, `failed`) is preserved — only the rendering changes.

### 5.9 — Cache bust

Bump the static-asset query string in `app.jsx` from the current `?v=0127a` to `?v=NNNNa` so the new CSS lands without users having to hard-reload. Standard close-out step (SPEC-0124 §5.4).

---

## 6. Visual references

The user-facing visual spec is the side-by-side mockup at:

- **Live preview (interactive):** `http://127.0.0.1:8765/` (served from `/tmp/dr-mockup/` via `python3 -m http.server 8765`). The directory contains a verbatim copy of `tokens.css` / `base.css` / `theme.css` / `components.css` from `src/dual_research/ui/static/`, plus an `index.html` that uses the real class names from `run-detail.jsx` so the mockup is rendered by the production CSS.
- **Switcher states:** `Before · faithful to live app` shows the current `.agent-bar` placement and current `<PhaseDots>` treatment. `After · wide` shows the relocated chips + new phase indicator. `After · narrow` shows the same with the narrow compaction applied (segmented control icons-only, chip tokens/cost dropped, Bar 1 + Bar 2 collapsed, both chips locked to 380 px).

The implementer should produce side-by-side before/after screenshots (wide and narrow viewports, light and dark mode) and attach them to the PR per SPEC-0124's precedent.

---

## 7. Out of scope (additions to §3)

- The `composeAgentActivity` phrase set. If a longer phrase is ever added that pushes past 22 characters, this spec's `min-width: 600px` becomes a lie. A future addition to the phrase set must either fit within 22 chars or bump that `min-width`. Note added inline at the CSS rule.
- The `Footer` component below `<main>` in `RunDetailView` (`run-detail.jsx:7254`). Untouched.
- The errored / running state pill styling (`md-status--errored`, etc.). The activity phrase + dot replaces the SB call in `TimelineAgentPill` via the `right` prop, which already overrides the SB default — see `shared.jsx:910`. The SB styles stay for other call sites.
- The drafter callout pill (`<DrafterCalloutPill>` in `run-detail.jsx:288-298`). Rendered inside `<PhaseDotsRow>`, sits adjacent to the new `.phase-progress` element. Unchanged.

---

## 8. Test plan

- [ ] Open a recent run with errored mid-run state (the pv-backend-language-brief run from the originating screenshots). Viewport ≥ 1500 px:
  - [ ] Visually confirm `<div className="agent-bar">` is gone from the DOM (no row between RunDetailHeader and the two-pane grid).
  - [ ] Visually confirm the Claude chip renders inside `.tl__head`, right-aligned, content = `[logo] claude-sonnet-4-6 · 164.9k · $0.71 · ● drafting parallel plan` (or whatever the live activity is).
  - [ ] Visually confirm the GPT chip renders inside `.tl__tabs`, right-aligned, content shape identical to Claude's.
  - [ ] Visually confirm both chips' right edges align with each other and with the right padding boundary of `.rdvc__pane`.
  - [ ] DevTools: confirm both chips render at identical `width` (`min-width: 600px` enforces parity).
  - [ ] Confirm the activity phrase animates / updates as the live run progresses (existing pulse / pulse-a animation continues to render).
- [ ] Resize to ≤ 1499 px (MacBook-13 width):
  - [ ] Visually confirm tokens + cost disappear from both chips; content collapses to `[logo] model · ● activity`.
  - [ ] Visually confirm both chips lock to `width: 380px` (DevTools).
  - [ ] Visually confirm the Conversation / Consumption segmented control buttons show icons only.
  - [ ] Visually confirm both chips' right edges still align at the same x.
  - [ ] Visually confirm Bar 1 stays a single row: title + `P2` / `P4` / `Σ` (no `.pname`) + three numeric counters (no `.lbl`).
  - [ ] Visually confirm Bar 2 stays a single row: kind chips collapsed (already per SPEC-0125), status chips collapsed to `dot + count`, agent chips collapsed to `icon`-only.
  - [ ] DevTools: confirm Bar 1 and Bar 2 still match `.tl__head` / `.tl__tabs` heights respectively across the centre divider.
- [ ] Resize back ≥ 1500 px and confirm everything reverts: tokens + cost reappear, segmented control labels reappear, Bar 1 / Bar 2 labels reappear.
- [ ] Confirm the M3 segmented phase progress renders correctly across run states:
  - [ ] Fresh run (status: running, phase 0): segment 0 is `--p-info`; segments 1-4 are track color.
  - [ ] Mid-run (status: running, phase 2): segments 0-1 are `--p-ok`; segment 2 is `--p-info`; segments 3-4 are track color.
  - [ ] Errored (status: errored, phase 1): segment 0 is `--p-ok`; segment 1 is `--p-err`; segments 2-4 are track color.
  - [ ] Completed (status: completed): all 5 segments are `--p-ok`.
  - [ ] Deadlocked (status: deadlocked, phase N): segments 0..N-1 are `--p-ok`; segment N is `--p-warn`.
- [ ] Hover each phase segment and confirm the title tooltip reads `Pn label · state`.
- [ ] No double-dot anywhere on the screen (confirms 5.7 audit or safety net is in place). Visually scan: phase header Q/D stat chips, timeline turn-card chips, critique-pane filter chips.
- [ ] Light-mode and dark-mode parity check on every visual change above.
- [ ] Click handlers: chip clicks (kind / status / agent filters), phase tab clicks, segmented control clicks, agent chip click (if any), turn card expand. All unchanged.
- [ ] Keyboard: tab through the run-detail header, the relocated chips, the segmented control, Bar 1 / Bar 2 chips. Confirm focus order reads naturally and no element is unreachable.
- [ ] Reduced-motion check (`prefers-reduced-motion: reduce`): segmented phase progress doesn't animate, agent chip dot doesn't pulse. Existing `base.css:122-131` rule handles this.
- [ ] Regression scan: Compare page, Search page, How-It-Works page, run list, modals (turn modal, draft review). Confirm no incidental visual change (CSS scope is `.as.in-header`, `.tl__head`, `.tl__tabs`, `.crit2 .bar1 / .bar2`, `.phase-progress`, plus the `:has()` safety net if added — should be inert elsewhere).
- [ ] Run the in-repo screenshot suite (`scripts/screenshot.sh` or whatever the standard is) and update the README / changelog screenshots where the run-detail header appears.

---

## 9. Risks

- **`flex-wrap: nowrap` + Bar 1 compaction not aggressive enough at some viewport sizes.** If the title + three P-codes + three numerals + counters still overflow at e.g. 1024 px, the test plan catches it; the fix is either a tighter `gap` or a slightly more conservative breakpoint. The user has two effective viewport sizes (wide monitor and MacBook), so the practical width range to test is narrow.
- **`:has()` browser support.** The safety net in 5.7 and the chip-label collapse in 5.6 both use `:has()`. Confirm during implementation that the project's browser support floor includes Chromium 105+ / Safari 15.4+ / Firefox 121+. If a lower floor is required, switch to attribute-based selectors (`data-status-filter` / `data-agent-filter` on the chips) — a one-line JSX change per chip in `run-detail.jsx:6127-6197`.
- **`.as-timeline` becomes dead code.** Once `<TimelineAgentBar>` is no longer rendered, `.as.as-timeline` (`components.css:299-311`) has no callers. Either delete it as part of this spec or leave it for a future cleanup spec. Recommend leaving it for the version after this — keeps this diff focused on the new placement, avoids accidentally breaking a different downstream surface that the implementer hasn't seen.
- **Activity phrase truncation in narrow.** At `width: 380px` and a 22-char activity phrase, the chip is sized for Claude's `claude-sonnet-4-6` content. If a future model id is longer, the activity phrase truncates first (via `.as-activity` ellipsis, SPEC-0112). Acceptable. If the model id ever exceeds ~18 chars, revisit.
- **PhaseDots state-machine drift.** The new `.phase-progress` implementation copies the `completed` / `current` / `failed` logic from the old `<PhaseDots>` verbatim. If the existing logic has bugs (e.g. status='completed' edge cases), they propagate. Acceptable — out of scope for a visual rework. A future spec can audit the state derivation.
- **Cache busting forgotten.** Implementer must remember to bump `?v=` in `app.jsx`; without it users see stale CSS. Test plan covers it.

---

## 10. Open questions

- **§5.4 cost format implementation:** Option A (`costFormatter` prop on AgentStrip) vs Option B (`compactCost` flag). Recommend A. Final call at implementation time.
- **§5.7 auto-dot fix:** confirm audit needs a CSS safety net or whether the JSX path covers it. Resolve before opening the PR.
- **§5.8 current-segment animation:** is the `.pulse-info` halo cue worth adding to `.phase-progress__seg.is-current`? Mockup currently omits it for compactness; M3 reference designs typically include a subtle indicator. Could be a one-line follow-up rather than part of this spec.
- **Phase count:** confirm `PHASES.length` is 5 (P0 Preflight through P4 Review) or 6 (including P5 Reconcile). The mockup uses 5. If 6, add a sixth `.phase-progress__seg` to the test plan's render checks.
