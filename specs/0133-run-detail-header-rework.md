---
spec: 0133
title: Run-detail surface rework — agent chips into Timeline pane, narrow critique compaction, M3 segmented phase progress, timeline card chip slim-down
label: new-feature
version-bump: MINOR
status: in-flight
target-version: 1.7.0
created: 2026-05-20
pr: "https://github.com/Lexiz/dual-research/pull/153"
---

# Spec 0133 — Run-detail surface rework: agent chips into Timeline pane + narrow critique compaction + M3 segmented phase progress + timeline card chip slim-down

> Ship bucket: **Frontend-only restructure of the run-detail page surface (spec 0107 chrome + spec 0119 / 0124 card heads).**
> Depends on: **0087** (`.as-timeline` width parity comment that anticipated this placement), **0107** (timeline + critique two-pane layout), **0112** (`.as-activity` ellipsis), **0119** (badge governance — `.chip` slot vocabulary), **0124** (critique filter row height parity + `.tl-card-head__right` cluster wrapper + responsive baseline), **0125** (existing `≤ 1499 px` kind-filter label collapse), and the **0127 → 0132 design-system v2 migration arc** (only v2 tokens — `--md-*` — appear below).
> Complexity: **M** — six coordinated changes in `run-detail.jsx`, `shared.jsx`, and `components.css`. No JS/contract/backend churn.
> Targeted version bump: **MINOR (1.6.12 → 1.7.0)** — the agent-bar row goes away as a visual element, the phase progress indicator is replaced, and timeline card category chips become substantially lighter. No behavior contract changes, but the run-detail surface shifts noticeably enough to warrant a minor bump.

> **Re-baseline note (2026-05-20).** The original draft of this spec was carried in tree across the 0127→0131 arc as `NNNN-…md` and filed in place by 0132. This revision rebases the spec onto the post-arc state: every CSS / JSX line reference below is verified against `main` after 0134 (`__version__ = "1.6.12"`); every token name is `--md-*` (no `--bg-*`, `--fg-*`, `--border-*`, `--r-*`, `--t-*`, `--mono`, `--sans`, `--serif` — those were retired by 0131); every font-weight is `--md-w-*` (no `--w-*` — those were retired by 0132); pill radius is `var(--md-shape-full)` (no literal `999px`); and the `.chip-pill` modifier referenced in the earlier draft is gone (0132 made pill the `.chip` default).

> **Follow-up note (post-ship, v1.7.1).** The narrow-mode breakpoint was originally set at `1499 px` to match the existing SPEC-0125 rule. Post-deploy validation surfaced that the actual content threshold is higher: a 1600–1799 px viewport (e.g. MacBook Pro 16" = 1728 px) leaves each two-pane column at ~800–900 px, which can't comfortably hold the wide-mode pill (logo + model + tokens + cost + activity ≈ 700+ px) alongside the Conversation/Consumption segmented control in `.tl__tabs`. The shared breakpoint inside `components.css:763` was bumped from `1499 → 1799 px` so MacBook Pro 14"/16" and half-screen browser windows on 27" displays correctly receive narrow rules. The `.agent-input` and `.resp-grid` breakpoints elsewhere in `components.css` stay at 1499 — they govern unrelated layouts. References to "1499 px" below are historical; the live CSS authority is 1799 px.

---

## 1. Context

A live-mockup iteration with the user (rendered at `/tmp/dr-mockup/` against verbatim copies of the production `tokens.css` / `base.css` / `theme.css` / `components.css`) converged on six coordinated changes to the run-detail page. They fall into four groups:

1. **The dedicated agent-bar row consumes a full row of vertical real estate to display two strips of information that can ride inside the existing pane headers.** [`TimelineAgentBar`](src/dual_research/ui/static/run-detail.jsx) at `run-detail.jsx:184-191` renders two `<AgentStrip className="as-timeline">` cards side-by-side inside `<div className="agent-bar">`, occupying ~50 px between the RunDetailHeader and the two-pane grid. The screen would benefit from reclaiming that row. The comment block at [`components.css:283-294`](src/dual_research/ui/static/components.css) is explicit about the originally-intended placement: *"`.as-timeline` forces a fixed outer width so the Claude + GPT pills on the run-detail header read at IDENTICAL outer widths regardless of agent-name / model-name string length. They **live in separate flex containers (Claude on PaneHeader row, GPT on PaneToolbar row)** so flex-grow can't equalize them naturally."* That intent was rolled back into a shared `.agent-bar` parent (spec 0105) and the width-parity comment was preserved but the row layout was not. This spec restores the originally-anticipated placement.

2. **At narrow desktop widths (≈ ≤ 1499 px viewport, ≈ ≤ 700 px effective column) the critique-pane header bars break.** Bar 1 (`.crit2 .bar1`) carries the title + three phase tabs + three counters; with `flex-wrap: wrap` (inherited from the shared `.crit2 .bar1, .crit2 .bar2` rule at `components.css:1848-1852`), the right-cluster counters wrap to a second row at narrow widths, growing the bar past the height of the left-pane `.tl__head` and breaking the centre-divider seam. Bar 2 (`.bar2.crit-filter-row`) is `nowrap` per SPEC-0125 but the existing narrow rule (`components.css:695-706`) only collapses kind-filter chip labels — the status (Open / Resolved / Drift) and agent (Claude / GPT) chip labels still render, pushing the row past the column edge where it gets clipped. SPEC-0125 sized for two-label visibility; the chip set has grown since (the Claude / GPT agent filter cluster was added in spec 0119).

3. **The current `PhaseDots` indicator (`run-detail.jsx:665-702`) doesn't follow the M3 design language that became canonical with spec 0127.** Six 6 × 6 px circles connected by 12 × 1 px segments, with conditional `border` / `background` swaps for state — a pre-M3 treatment composed entirely via inline `style={{ … }}` props. M3 prefers a segmented linear progress indicator (small filled rounded bar segments with hairline gaps) for discrete-step progress over circle-and-line steppers. SPEC-0127 § 5.1 calls out that pre-M3 inline-styled JSX is one of the cleanup targets; PhaseDots survived the 0128 token sweep because its inline values were geometric (px) rather than v1 tokens, but it's still anti-pattern relative to the design system.

4. **Timeline turn-card category chips are visually heavy.** Each card renders four Q / D / I / C chips (`TlTurnRow` at `run-detail.jsx:1132-1152`) carrying `categoryBubble` + `value` (standing) + `add` (raised) + `sub` (closed) + `trailingSuffix` (capped). That's five slots per chip, four chips per card, dozens of cards per run — the timeline reads as a noisy grid of bubble + total + delta. The information that actually matters per card (and the only thing that changes between cards in the same column) is the per-round delta — how many were *raised* and *closed* in that round. Standing totals are signal at the phase-header level (where `TlPhaseHeadChips` aggregates per-phase) but redundant on every turn card. Drop bubble + standing-total from the turn-card chips; keep `+add` and `−sub` with a subtle separator between them. The card chips become a thin per-round Δ-pair, the column scans cleanly, and the category-bubble grammar is preserved at the phase-header level where it carries the most weight.

All four groups are CSS / JSX-only. No protocol, contract, scheduler, queue, or backend change.

---

## 2. Goals

1. **Agent chips inside the Timeline pane headers — wide view.** Render the existing `AgentStrip` for Claude inside `<header className="tl__head">` and the one for GPT inside `<div className="tl__tabs">`, in both cases right-aligned via `margin-left: auto`. The right edges of the two chips share the same x-coordinate (the column's right-padding boundary). Both chips render at an identical outer width regardless of model-name length difference (`claude-sonnet-4-6` vs `gpt-5.5`). The dedicated `<div className="agent-bar">` row is removed from the DOM.

2. **Agent chip wide-view content.** Each chip renders `[logo] [model] · [tokens] · [cost] · [● activity phrase]`. Two trims relative to the live agent-bar:
   - **Drop the agent name** ("Claude" / "GPT") — the logo carries identity and the model name disambiguates further.
   - **Cost to 2 decimals** — `$0.7099` becomes `$0.71`. Use the existing `fmt.costShort` helper (`shared.jsx:586`); no new helper required.
   The longest live activity phrase (`composeAgentActivity` at `run-detail.jsx:53-92`) is 22 characters — `drafting parallel plan` / `drafting converged doc` / `negotiating · round NN`. The chip's `min-width` is sized to fit it without truncation.

3. **Agent chip narrow view.** Below the same `1499 px` narrow-desktop breakpoint already in use (SPEC-0125), each chip drops the tokens and cost (and their separators) and keeps `[logo] [model] · [● activity phrase]`. Both chips lock to the same `width` (Claude's natural content width with the longest activity phrase, ≈ 380 px) so they remain visually equal-sized despite different content lengths. The Conversation / Consumption segmented control in `.tl__tabs` collapses to icons-only at the same breakpoint so the wider GPT chip has room alongside it.

4. **Critique-pane narrow compaction — Bar 1 (`.crit2 .bar1`).** Force `flex-wrap: nowrap` to prevent the counter cluster from wrapping. Hide phase-tab textual labels (`.pname`) so each tab is just its P-code (`P2` / `P4` / `Σ`). Hide counter textual labels (`.crit-totals .lbl`) so the right cluster is just three numbers. Tighten `gap` and `padding`. The bar must keep its `min-height: 53 px` and remain aligned with `.tl__head` across the centre divider.

5. **Critique-pane narrow compaction — Bar 2 (`.bar2.crit-filter-row`).** Extend SPEC-0125's kind-filter label collapse to the status filter cluster (Open / Resolved / Drift — identified by `.chip-dot` slot) and the agent filter cluster (Claude / GPT — identified by `.chip-leading-icon` slot). The dot color + agent icon already carry the identity; the text is redundant signal at narrow width.

6. **M3 segmented linear phase-progress indicator.** Replace the existing `PhaseDots` markup with a `.phase-progress` element containing N `<span className="phase-progress__seg">` cells (one per phase in `PHASES`). Each cell is a 26 × 4 px rounded bar (`border-radius: 2px`) with a 3 px gap between cells. Cell state drives its background color via existing palette tokens: `var(--md-outline-variant)` (track / pending), `var(--p-ok)` (done), `var(--p-info)` (current), `var(--p-err)` (errored), `var(--p-warn)` (deadlocked / drift). Replaces both the visual treatment and the imperative inline-styled JSX construction.

7. **`<Chip>` auto-dot collision audit.** The upgraded `Chip` primitive (SPEC-0119, `shared.jsx:768-774`) auto-adds `.no-dot` whenever any slot prop is set so the `::before` auto-dot doesn't double up with `.cat-bubble` / `.chip-dot` / `.chip-leading-icon`. The mockup work surfaced visible double-dots in places where the user expects a single indicator (the new Open / Resolved / Drift narrow collapse from Goal 5 is one). Either confirm `usesNewSlots` at `shared.jsx:768` covers every call site, or add a CSS-level safety net via `:has()` (§ 5.7). Net: zero double-dots anywhere on the run-detail surface after this spec.

8. **Timeline turn-card category chips — slim Δ-pair.** In every `TlTurnRow` card across every phase (P0 brief + preflight, P1 plan, P2/P4 negotiate / review turns, P3 drafting, P5 reconcile), simplify the per-round Q / D / I / C category chips to just `+raised` and `−closed` with a subtle separator between them. Drop the `categoryBubble` (`Q` / `D` / `I` / `C` bubble glyph) and `value` (standing total) slots; rely on the existing `CATEGORY_TONE` color (`info` / `warn` / `err` / `idle`) + fixed Q→D→I→C order to disambiguate categories. `dim` (no-activity zero state), `trailingSuffix` (capped `⊘ N` indicator), `tone`, `ariaLabel`, and `onClick` are all preserved. `TlPhaseHeadChips` (the phase header chips, `run-detail.jsx:943-992`) is **explicitly out of scope** — those keep the full bubble + value + add + sub presentation because they aggregate per-phase and the bubble + standing total carries meaning at that level.

All eight goals are visible in the side-by-side mockup at `/tmp/dr-mockup/index.html` (re-launch via `cd /tmp/dr-mockup && python3 -m http.server 8765` if the file tree still exists, otherwise re-spin from the design-system v2 CSS files — the mockup is a static HTML harness against verbatim CSS).

---

## 3. Non-goals

- **No change to `RunDetailHeader`** (`run-detail.jsx:117-139`) — topic + cost badge + reconcile chip + run-search summary + status-errors badge + phase-dots row. Those stay in place; this spec replaces only the agent-bar row immediately below and the phase-dots indicator within.
- **No change to the `<AgentStrip>` primitive** structure (`shared.jsx:885-913`) — the relocation is achieved by adding a new `.as.in-header` modifier class that overrides only what's needed (no name display, tighter padding, content-natural sizing in narrow). The live agent-bar continues to use plain `.as.as-timeline` until removed.
- **No change to `composeAgentActivity`** (`run-detail.jsx:53-92`) — the phrase logic stays. The relocated chip continues to consume `phrase` + `live` via the `right` prop unchanged.
- **No new chip primitive variants in `shared.jsx`.** The narrow-view chip-label collapse is a CSS modifier gated by a `@media` rule, not a new `<Chip compact>` prop. The card-chip slim-down is also pure call-site (drop props) — the `Chip` primitive's existing slot semantics already render what we want. Same pattern as SPEC-0125.
- **No change to `.tl__head` / `.tl__tabs` height contract.** They keep `min-height: 53 px / 55 px` respectively (`components.css:1994-2030`). The relocated chip must fit within those heights — `align-self: center` and tight vertical padding on `.as.in-header` ensure it doesn't push them taller.
- **No change to filter chip click handlers, ordering, count semantics, hover tooltips, dim/active states, or keyboard focus order.** Only the visual presentation (label visibility, narrow-view) changes.
- **No change to the timeline turn-card header layout** (`.tl-card-head` / `.tl-card-head__right`). SPEC-0124 already moved category chips into the right cluster; this spec only changes which slots those chips render via prop drops at the `TlTurnRow` call site.
- **No change to `TlPhaseHeadChips`** (`run-detail.jsx:943-992`). Phase-header chips keep `categoryBubble` + `value` + `add` + `sub` because the bubble + standing total carries meaningful aggregate signal at the phase-header level. Slim-down is card-only.
- **No change to the critique-pane card heads (`.crit-card-head`).** SPEC-0119 §8.4 governs those.
- **No change to the phase definitions** (PHASES const in `run-detail.jsx`) or to the phase progress *logic* — `phase`, `status`, `completed`, `current`, `failed` continue to drive cell state. Only the *visual treatment* swaps from circles-and-lines to filled bar segments.
- **No new breakpoint.** Reuse the existing `1499 px` narrow-desktop breakpoint already in use at `components.css:695` (SPEC-0125 kind-filter collapse), `components.css:919` (`.agent-input` grid collapse), and `components.css:2834` (`.resp-grid` collapse). One breakpoint, one mental model.
- **No mobile / sub-900 px treatment.** The run-detail screen is desktop-only.
- **No `PhaseRail` change** (`run-detail.jsx:712-731`). That component is a separate modal indicator and stays in its M3 cell-with-labels treatment.

---

## 4. Current-state audit

### 4.1 — The agent-bar row (Goals 1, 2, 3)

| Element | File | Lines | Current state |
|---|---|---|---|
| `<TimelineAgentBar>` JSX | [run-detail.jsx:184-191](src/dual_research/ui/static/run-detail.jsx) | 184–191 | `<div className="agent-bar">` wrapping two `<TimelineAgentPill agent="claude" />` / `agent="gpt"` |
| `<TimelineAgentPill>` JSX | [run-detail.jsx:146-181](src/dual_research/ui/static/run-detail.jsx) | 146–181 | Reads `run.agents[agent]`, composes activity, renders `<AgentStrip className="as-timeline" right={activityRight} />` |
| Render site of agent-bar | [run-detail.jsx:7234](src/dual_research/ui/static/run-detail.jsx) | 7234 | `<TimelineAgentBar run={run} />` sits between `<RunDetailHeader>` and `<main>` (the two-pane grid) |
| `.agent-bar` CSS | [components.css:2845-2851](src/dual_research/ui/static/components.css) | 2845–2851 | `display: flex; gap: var(--md-sp-6); padding: 8px var(--md-sp-5); background: var(--md-surface-container); border-bottom: 1px solid var(--md-outline-hair);` |
| `.as.as-timeline` CSS | [components.css:283-295](src/dual_research/ui/static/components.css) | 283–295 | `min-width: 460px; max-width: 720px; flex: 1 1 460px;` — sized for two-side-by-side agent-bar placement; comment block (lines 283-294) is the SPEC-0087 §E "Claude on PaneHeader row, GPT on PaneToolbar row" intent quoted in § 1 |
| `.tl__head` CSS | [components.css:1994-2004](src/dual_research/ui/static/components.css) | 1994–2004 | `display: flex; align-items: center; gap: 16px; padding: 10px 20px; background: var(--md-surface-container-high); border-bottom: 1px solid var(--md-outline-hair); min-height: 53px; flex-shrink: 0;` |
| `.tl__tabs` CSS | [components.css:2006-2014](src/dual_research/ui/static/components.css) | 2006–2014 | Same shape, `min-height: 55px`, `background: var(--md-surface-container)` |
| `composeAgentActivity` phrases | [run-detail.jsx:53-92](src/dual_research/ui/static/run-detail.jsx) | 53–92 | Set: `done`, `errored`, `deadlocked`, `waiting for {name}`, `waiting · phase N`, `idle`, `critiquing the brief`, `drafting parallel plan`, `drafting converged doc`, `negotiating · round N`, `reviewing · round N`, `finalising` |

Longest live phrase: 22 characters — `drafting parallel plan` / `drafting converged doc` / `negotiating · round NN`. The relocated chip's `min-width` is sized for that worst case.

### 4.2 — Cost formatting

| Element | File | Lines | Current state |
|---|---|---|---|
| `fmt.cost` / `fmt.costShort` helpers | [shared.jsx:584-599](src/dual_research/ui/static/shared.jsx) | 585–586 | `fmt.cost: (n) => $${n.toFixed(4)}` and `fmt.costShort: (n) => $${n.toFixed(2)}` — **both already defined**. No new helper required. |
| Top-bar CostBadge call site | [run-detail.jsx:595](src/dual_research/ui/static/run-detail.jsx) | 595 | `<span className="num">{fmt.cost(cost)}</span>` — stays at 4 decimals (run-total precision matters). |
| AgentStrip cost render | [shared.jsx:903-907](src/dual_research/ui/static/shared.jsx) | 903–907 | Currently hard-coded to `fmt.cost(cost)`. § 5.4 below threads a `costFormatter` prop through so `TimelineAgentPill` can opt into `fmt.costShort` without affecting other AgentStrip consumers. |

### 4.3 — Critique pane Bar 1 (Goal 4)

| Element | File | Lines | Current state |
|---|---|---|---|
| `<header className="bar1">` JSX | [run-detail.jsx:6086-6113](src/dual_research/ui/static/run-detail.jsx) | 6086–6113 | `<span className="ttl">Critique</span>` + `<span className="vbar"></span>` + `<div className="phase-tabs">` (3× `<button className="phase-tab">` with `<span className="pcode">` + `<span className="pname">`) + `<div className="right">` containing `<span className="crit-totals">` (3× `<span><span className="n">N</span><span className="lbl">label</span></span>`) |
| Shared `.bar1, .bar2` CSS | [components.css:1848-1852](src/dual_research/ui/static/components.css) | 1848–1852 | `display: flex; align-items: center; gap: 16px; padding: 10px 20px; flex-wrap: wrap;` |
| `.bar1` specifics | [components.css:1853-1856](src/dual_research/ui/static/components.css) | 1853–1856 | `background: var(--md-surface-container-high); border-bottom: 1px solid var(--md-outline-hair);` |
| `.crit2 .right` CSS | [components.css:1862](src/dual_research/ui/static/components.css) | 1862 | `margin-left: auto; display: inline-flex; gap: 16px; align-items: center; flex-wrap: wrap;` |
| `.crit-totals .n / .lbl` CSS | [components.css:1878-1879](src/dual_research/ui/static/components.css) | 1878–1879 | `.n { font: var(--md-w-semi) 18px/1 var(--md-font-data); color: var(--md-on-surface); }` and `.lbl { font: var(--md-w-medium) 10px/1 var(--md-font-plain); letter-spacing: 0.08em; text-transform: uppercase; color: var(--md-on-surface-faint); margin-top: 4px; }` |
| `.phase-tab` CSS | [components.css:1734-1762](src/dual_research/ui/static/components.css) | 1734–1762 | Pill-shaped, M3 state-layer, with `.pcode` + `.pname` slots |

The `flex-wrap: wrap` on both `.bar1` and `.right` is what makes Bar 1 grow to two rows at narrow widths.

### 4.4 — Critique pane Bar 2 (Goal 5)

| Element | File | Lines | Current state |
|---|---|---|---|
| `<header className="bar2 crit-filter-row">` JSX | [run-detail.jsx:6127-6197](src/dual_research/ui/static/run-detail.jsx) | 6127–6197 | 10 chips + 2 `<span className="crit-filter-spacer">` separators: Q / D / I / C (each `categoryBubble` + `value`), All (`value`), Open (`leadingDot` + `value`), Resolved (`leadingDot` + `value`), Drift (`leadingDot`), Claude (`leadingIcon` + label), GPT (`leadingIcon` + label) |
| `.crit-filter-row` base CSS | [components.css:676-682](src/dual_research/ui/static/components.css) | 676–682 | `flex-wrap: nowrap; padding: 10px 14px; min-height: 55px; gap: 8px;` |
| SPEC-0125 narrow rule | [components.css:695-706](src/dual_research/ui/static/components.css) | 695–706 | `@media (max-width: 1499px)` collapses kind-filter chip labels only via `data-kind-filter` attribute; shrinks `.crit-filter-spacer` to 6 px |
| `.chip` auto-dot | [components.css:153-163](src/dual_research/ui/static/components.css) | 153–163 | `.chip.tone-info/.tone-ok/.tone-warn/.tone-err/.tone-idle/.tone-muted::before` renders a 6 × 6 px dot in `currentColor`; `.chip.no-dot::before { display: none }` suppresses it; the live `<Chip>` primitive auto-adds `.no-dot` when any slot is used (`shared.jsx:773` — `suppressAutoDot = noDot || usesNewSlots`) |

The Open / Resolved / Drift chips use `leadingDot` → `.chip-dot`. The Claude / GPT chips use `leadingIcon` → `.chip-leading-icon`. Neither cluster has a CSS rule that collapses their labels at narrow widths — only the kind cluster does. The combined natural row width exceeds the column at narrow viewports, and `flex-wrap: nowrap` forces overflow → clip.

### 4.5 — Phase progress indicator (Goal 6)

| Element | File | Lines | Current state |
|---|---|---|---|
| `<PhaseDots>` JSX | [run-detail.jsx:665-702](src/dual_research/ui/static/run-detail.jsx) | 665–702 | `<div style={{ display: 'flex' }}>` with `{PHASES.map(p => <React.Fragment>{circle}{connector}</React.Fragment>)}` — each circle is a 6 × 6 px inline-styled span with conditional `background` / `border`, each connector a 12 × 1 px span. Composed entirely via inline `style={{ … }}` props; geometric so survived the 0128 token sweep, but still anti-pattern relative to the design system. |
| Render site | [run-detail.jsx:261](src/dual_research/ui/static/run-detail.jsx) | 261 | `<PhaseDots run={run} />` inside `<PhaseDotsRow>` at line 255, immediately below the title |
| `PHASES` const | `src/dual_research/ui/static/run-detail.jsx` | grep `const PHASES =` | Confirm count at execution (5 — P0..P4 — or 6 — P0..P5 including Reconcile). The breadcrumb beneath in PhaseDotsRow reads `preflight · drafts · negotiate · drafting · review` (5 labels), so the rendered cell count must match the breadcrumb. |

### 4.6 — `<Chip>` auto-dot suppression audit (Goal 7)

| Element | File | Lines | Current state |
|---|---|---|---|
| `usesNewSlots` heuristic | [shared.jsx:768-772](src/dual_research/ui/static/shared.jsx) | 768–772 | `leadingDot != null \|\| leadingIcon != null \|\| categoryBubble != null \|\| iconOnly \|\| value != null \|\| add != null \|\| sub != null \|\| trailingSuffix != null \|\| dim \|\| mono \|\| label != null` |
| `.no-dot` class application | [shared.jsx:773-786](src/dual_research/ui/static/shared.jsx) | 773–786 | `suppressAutoDot = noDot || usesNewSlots`; applied to the chip element's `className` |
| Auto-dot CSS | [components.css:153-163](src/dual_research/ui/static/components.css) | 153–163 | See § 4.4 |

The live `Chip` should already suppress the auto-dot for every chip with a slot. The mockup work surfaced visible double-dots in two contexts: (a) chip variants composed without going through the `Chip` primitive (raw `<button className="chip tone-info">` markup), if any; (b) the narrow-view chips after Goal 5 collapses Open / Resolved / Drift labels — the leading-dot remains and the auto-dot might re-emerge if the suppression heuristic depends on a slot prop that the narrow CSS hides rather than the JSX dropping. Verify both during implementation; § 5.7 ships a CSS-level `:has()` safety net if needed.

### 4.7 — Timeline turn-card category chips (Goal 8)

| Element | File | Lines | Current state |
|---|---|---|---|
| `TlTurnRow` category chip call site | [run-detail.jsx:1129-1153](src/dual_research/ui/static/run-detail.jsx) | 1129–1153 | Inside `<div className="tl-card-head__right">` (post-0124 right cluster); `chipCategories.map((cat) => <Chip tone={CATEGORY_TONE[cat]} categoryBubble={CATEGORY_BUBBLE[cat]} value={c.standing} add={c.raised} sub={c.closed} trailingSuffix={c.capped > 0 ? '⊘ N' : null} dim={noActivity} … />)` |
| `CATEGORY_TONE` / `CATEGORY_BUBBLE` / `CATEGORY_LABEL_PLURAL` | [run-detail.jsx:894-917](src/dual_research/ui/static/run-detail.jsx) | 894–917 | Q→info, D→warn, I→err, C→idle (tones); Q/D/I/C bubble glyphs; full plural labels for a11y |
| `.tl-card-head__right` wrapper | [components.css:647-650](src/dual_research/ui/static/components.css) | 647–650 | `display: inline-flex; align-items: center; gap: 4px; margin-left: auto;` — introduced by spec 0124 §5.3 |
| `.chip .chip-add` / `.chip-sub` CSS | [components.css:198-209](src/dual_research/ui/static/components.css) | 198–209 | `.chip-add { font-variant-numeric: tabular-nums; font-weight: 600; font-size: 11px; color: var(--ok); }` and `.chip-sub { … color: var(--err); }`; dim variants drop to `var(--md-on-surface-faint)`. No separator between them today. |
| `Chip` primitive slot order | [shared.jsx:736-844](src/dual_research/ui/static/shared.jsx) | 736–844 | Render order inside `.chip`: `chip-dot` → `chip-leading-icon` → `cat-bubble` → `.ico` (Mdi icon) → `chip-label` → `chip-value` → `chip-add` → `chip-sub` → `chip-suffix` → children |
| `TlPhaseHeadChips` (out of scope for Goal 8) | [run-detail.jsx:943-992](src/dual_research/ui/static/run-detail.jsx) | 943–992 | Same chip-construction pattern but on the phase header. Keep as-is; full bubble + standing + add + sub remains meaningful at the phase-aggregate level. |

The slot grammar means dropping just `categoryBubble` + `value` at the call site removes the leading bubble + standing-total slots; `add` + `sub` continue to render in their current positions. The slim-down is a pure call-site change at line 1129-1153 plus a CSS rule for the inter-Δ separator.

---

## 5. Proposed change

### 5.1 — Relocate agent strips into Timeline pane headers (`run-detail.jsx`)

**Remove `<TimelineAgentBar>` render site** at [run-detail.jsx:7234](src/dual_research/ui/static/run-detail.jsx). The `<TimelineAgentBar>` and `<TimelineAgentPill>` function definitions stay (or get inlined — implementer's call) but the `agent-bar` parent and its row layout go away.

**Inside `<Timeline>` (around `run-detail.jsx:797`)** render the Claude pill inside `<header className="tl__head">` and the GPT pill inside `<div className="tl__tabs">`. The relocated pill carries a new `in-header` modifier class so § 5.2 CSS can scope:

```jsx
<header className="tl__head">
  <span className="ttl">Timeline</span>
  <span className="ct">{artifactCount} artifacts</span>
  <TimelineAgentPill agent="claude" run={run} className="in-header" />
</header>

<div className="tl__tabs">
  <div className="tl__tabs-inner">
    <button … >Conversation</button>
    <button … >Consumption</button>
  </div>
  <TimelineAgentPill agent="gpt" run={run} className="in-header" />
</div>
```

`TimelineAgentPill` already passes its `className` prop into `AgentStrip` (`run-detail.jsx:178`); the wrapper `.as` element receives `as is-a in-header` / `as is-b in-header`.

### 5.2 — `.as.in-header` modifier (`components.css`)

Append to the agent-strip block (after `components.css:326` — just below `.as-activity`):

```css
/* Spec 0133 — `.as.in-header` relocates the AgentStrip into a Timeline
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
  border-radius: var(--md-shape-full);
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

Append, gated on the same `1499 px` breakpoint as SPEC-0125 (extend the existing media block at lines 695-706, or open a new one — implementer's choice; one block is preferable):

```css
@media (max-width: 1499px) {
  /* Spec 0133 — narrow-view AgentStrip compaction.
     Drop the tokens + cost slots (they read at the run-total level via
     CostBadge in the top bar); keep logo + model + activity. Both chips
     lock to the same `width` (Claude's natural content width with the
     longest activity phrase) so they remain visually equal-sized despite
     "gpt-5.5" being much shorter than "claude-sonnet-4-6". */
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
     — in that order — per AgentStrip's render in shared.jsx:896-909.
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

**Option A (recommended) — `costFormatter` prop on `AgentStrip`.** Add an optional `costFormatter` prop to `<AgentStrip>` (`shared.jsx:885`) that defaults to `fmt.cost`. `TimelineAgentPill` (`run-detail.jsx:146-181`) passes `fmt.costShort` (already defined at `shared.jsx:586` — no new helper required). Every other AgentStrip consumer stays on the default 4-decimal format.

```jsx
// shared.jsx — AgentStrip
function AgentStrip({ agent, name, model, tokens, cost, status, live, right,
                     className, costFormatter = fmt.cost }) {
  // …
  {cost != null && (
    <>
      <span className="num v">{costFormatter(cost)}</span>
      <span className="sep">·</span>
    </>
  )}
  // …
}

// run-detail.jsx — TimelineAgentPill
<AgentStrip
  agent={slot}
  name={meta.name}
  model={modelId}
  tokens={totalTokens}
  cost={cost}
  costFormatter={fmt.costShort}
  right={activityRight}
  className="as-timeline"  // <-- replaced with "in-header" per § 5.1
/>
```

**Option B — `<AgentStrip compactCost>` boolean prop.** Switches the internal `fmt.cost` call to `fmt.costShort`. Slightly less flexible than A but smaller surface area. Either is fine; A is closer in spirit to SPEC-0119's "primitive stays single-purpose, behavior is configured at the call site".

### 5.5 — Critique Bar 1 narrow compaction (`components.css`)

Inside the same `@media (max-width: 1499px)` block:

```css
@media (max-width: 1499px) {
  /* Spec 0133 — Critique Bar 1 narrow compaction.
     The shared `.bar1, .bar2 { flex-wrap: wrap }` rule wraps Bar 1's right
     cluster onto a second row at narrow viewports, blowing the height match
     with .tl__head. Force nowrap and drop redundant labels so the bar stays
     single-row at the same `min-height` as .tl__head. */
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

Extend the existing SPEC-0125 narrow block at `components.css:695-706`:

```css
@media (max-width: 1499px) {
  /* … existing SPEC-0125 rules: gap 4px, padding 10px 10px,
     `.chip[data-kind-filter] .chip-label { display: none }`,
     `.crit-filter-spacer { width: 6px; flex: 0 0 6px }` … */

  /* Spec 0133 — extend the kind-filter collapse to the status filter
     cluster (Open / Resolved / Drift) and the agent filter cluster
     (Claude / GPT). The dot color + agent icon carry the identity at
     this width; the text is redundant. */
  .crit2 .bar2.crit-filter-row .chip:has(.chip-dot) .chip-label,
  .crit2 .bar2.crit-filter-row .chip:has(.chip-leading-icon) .chip-label {
    display: none;
  }
}
```

`:has()` is widely supported (Chromium 105+, Safari 15.4+, Firefox 121+). The project already ships features that assume modern browsers; confirm during implementation that `:has()` falls within the support floor. If not, switch to the `data-status-filter` / `data-agent-filter` attribute pattern (mirroring SPEC-0125's `data-kind-filter`) and key the rule off those — a one-line JSX change per chip in `run-detail.jsx:6127-6197`.

### 5.7 — `<Chip>` auto-dot collision (audit + optional CSS safety net)

**Audit first.** Walk every `<Chip tone="info" | "ok" | "warn" | "err" | "idle" | "muted">` call site in `run-detail.jsx` and `shared.jsx` and confirm that the `Chip` primitive is being entered (not bypassed via raw `<button className="chip …">` markup) and that `usesNewSlots` at `shared.jsx:768` evaluates `true` for chips that should suppress the auto-dot. Also confirm that the narrow-view label collapse from § 5.6 doesn't re-expose the auto-dot — `.no-dot` is applied at JSX render time based on slot **props**, so hiding the slot **DOM** later doesn't re-enable the auto-dot. Sanity-check this in DevTools after Goal 5 lands.

**If the audit finds a gap**, ship the CSS-level safety net (mirrors the JSX heuristic via `:has()`):

```css
/* Spec 0133 — safety net for the auto-dot vs slot collision.
   Mirrors shared.jsx:768 `usesNewSlots = leadingDot || leadingIcon ||
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

If the audit finds no gap, drop § 5.7 from the spec. Either way, the user-visible result is no double-dot anywhere on the run-detail screen.

### 5.8 — M3 segmented phase-progress indicator (`run-detail.jsx` + `components.css`)

**CSS — append to `components.css` near the timeline / critique chrome rules:**

```css
/* Spec 0133 — M3 segmented linear phase-progress indicator.
   Replaces the legacy <PhaseDots> circles-and-lines treatment. One
   segment per PHASES entry; the segment's state class drives its
   color via the existing palette tokens. The current segment may
   carry the `.pulse-info` animation already defined in base.css if
   a subtle live-state cue is desired (open question § 10). */
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
  transition: background var(--md-dur-short-4) var(--md-easing-standard);
}
.phase-progress__seg.is-done    { background: var(--p-ok); }
.phase-progress__seg.is-current { background: var(--p-info); }
.phase-progress__seg.is-error   { background: var(--p-err); }
.phase-progress__seg.is-warn    { background: var(--p-warn); }
```

(Use M3 motion tokens — `--md-dur-short-4` / `--md-easing-standard` — instead of the deprecated `--m-base` / `--ease`. Both still exist post-0131 but the M3 vocabulary is canonical.)

**JSX — replace `<PhaseDots>` at `run-detail.jsx:665-702`:**

```jsx
function PhaseDots({ run }) {
  const { phase, status } = run;
  return (
    <div className="phase-progress" aria-label="Run progress">
      {PHASES.map((p) => {
        const completed = p.id < phase || (status === 'completed' && p.id <= PHASES.length - 1);
        const current   = p.id === phase && status !== 'completed';
        const failed    = (status === 'errored' || status === 'deadlocked') && p.id === phase;
        const cls = ['phase-progress__seg'];
        if (failed && status === 'errored')         cls.push('is-error');
        else if (failed && status === 'deadlocked') cls.push('is-warn');
        else if (current)                            cls.push('is-current');
        else if (completed)                          cls.push('is-done');
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

The same state derivation from the old `<PhaseDots>` (`completed` / `current` / `failed`) is preserved; only the rendering changes.

### 5.9 — Timeline turn-card category-chip slim-down (Goal 8)

**JSX change at `run-detail.jsx:1132-1152`** — drop `categoryBubble` and `value` props from the per-category chip inside `TlTurnRow`:

```jsx
{showCategoryChips && chipCategories.map((cat) => {
  const c = categories[cat] || { standing: 0, raised: 0, closed: 0, capped: 0 };
  const noActivity = (c.raised + c.closed) === 0;
  return (
    <Chip
      key={cat}
      tone={CATEGORY_TONE[cat]}
      // categoryBubble dropped — color + Q→D→I→C order carry the category
      // value dropped — standing total reads at the phase-header level instead
      add={c.raised}
      sub={c.closed}
      trailingSuffix={c.capped > 0 ? `⊘ ${c.capped}` : null}
      dim={noActivity}
      ariaLabel={`${CATEGORY_LABEL_PLURAL[cat]} this round: ${c.raised} raised, ${c.closed} closed${c.capped > 0 ? `, ${c.capped} capped` : ''}`}
      onClick={(e) => {
        e.stopPropagation();
        dispatchCritiqueJump({ category: cat, round: item.round, phase });
      }}
    />
  );
})}
```

Notes:
- The `tone` + fixed Q→D→I→C order (set by `chipCategories`) are now the only category identifiers per chip — no glyph. The `ariaLabel` still names the category for screen readers.
- `dim` and `trailingSuffix` (capped `⊘ N`) survive — both still meaningful on the slim chip.
- `onClick` semantics unchanged — click still jumps the critique pane to `{ category, round, phase }`.
- The wrapper `.tl-card-head__right` (spec 0124 §5.3) keeps the right-aligned cluster shape.
- `TlPhaseHeadChips` (`run-detail.jsx:943-992`) is **not** touched — phase-header chips keep the full bubble + value + add + sub. (Mentioned in § 3 non-goals; reaffirmed here.)

**CSS — append to `components.css` near the `.chip .chip-add` / `.chip-sub` block (lines 198-209):**

```css
/* Spec 0133 — subtle vertical separator between `.chip-add` and
   `.chip-sub` when they sit adjacent. The slim Δ-pair presentation
   used by timeline turn-card category chips (after Goal 8) reads
   "+raised | −closed" — without a separator the two figures bleed
   into each other and a column of cards becomes unreadable. The
   separator is universal (applies to any chip with both add+sub
   slots, including the unchanged TlPhaseHeadChips) so the design
   language stays consistent across surfaces. */
.chip .chip-add + .chip-sub {
  position: relative;
  padding-left: 8px;
  margin-left: 2px;
}
.chip .chip-add + .chip-sub::before {
  content: "";
  position: absolute;
  left: 0;
  top: 22%;
  bottom: 22%;
  width: 1px;
  background: currentColor;
  opacity: 0.28;
}
```

Alternative (lighter touch): replace the pseudo-element with a middle-dot character:

```css
.chip .chip-add + .chip-sub::before {
  content: "·";
  color: var(--md-on-surface-faint);
  margin-right: 4px;
  margin-left: -2px;
  font-weight: 400;
}
```

Recommend the vertical-line variant — it reads as a structural divider rather than as another piece of content, which fits the "lighter for the eye" intent better.

### 5.10 — Cache bust

Bump the static-asset query string in `app.jsx` from the current `?v=0134a` (post-0134) to `?v=0133a` (this spec's letter — implementer chooses the convention; SPEC-0124 §5.4 sets the precedent). Standard close-out step.

---

## 6. Visual references

The visual spec is the live mockup at `/tmp/dr-mockup/`. The harness is a static HTML page that links to verbatim copies of `tokens.css` / `base.css` / `theme.css` / `components.css` from `src/dual_research/ui/static/`, with HTML written against the real production class names so the mockup renders through the production CSS.

**Re-launch the mockup** (the background server from the original session was killed at session end):

```bash
cd /tmp/dr-mockup && python3 -m http.server 8765 --bind 127.0.0.1
# open http://127.0.0.1:8765/
```

If `/tmp/dr-mockup/` no longer exists, re-spin it by:
1. Copying `tokens.css`, `base.css`, `theme.css`, `components.css` from `src/dual_research/ui/static/` into `/tmp/dr-mockup/`.
2. Writing an `index.html` that uses the run-detail class names (the original is referenced inline below — switcher with three states: *Before · faithful to live app*, *After · wide*, *After · narrow*).
3. Adding the §5 CSS overrides as a `<style>` block above the production CSS so the mockup can preview the proposed state alongside the current state.

The implementer should produce side-by-side before/after screenshots (wide + narrow viewports, light + dark mode) and attach them to the PR per SPEC-0124's precedent.

---

## 7. Out of scope (additions to §3)

- The `composeAgentActivity` phrase set (`run-detail.jsx:53-92`). If a longer phrase is ever added that pushes past 22 characters, this spec's `min-width: 600px` becomes a lie. A future addition to the phrase set must either fit within 22 chars or bump that `min-width`. Note added inline at the CSS rule.
- The `Footer` component below `<main>` in `RunDetailView` (`run-detail.jsx:7254`). Untouched.
- The errored / running state pill styling (`md-status--errored`, etc.). The activity phrase + dot replaces the SB call in `TimelineAgentPill` via the `right` prop, which already overrides the SB default — see `shared.jsx:909`. The SB styles stay for other call sites.
- The drafter callout pill (`<DrafterCalloutPill>` in `run-detail.jsx:288-298`). Rendered inside `<PhaseDotsRow>`, sits adjacent to the new `.phase-progress` element. Unchanged.
- `TlPhaseHeadChips` (`run-detail.jsx:943-992`) keeps its full chip shape. The slim-down in Goal 8 is card-only.

---

## 8. Test plan

- [ ] Open a recent run with errored mid-run state. Viewport ≥ 1500 px:
  - [ ] Visually confirm `<div className="agent-bar">` is gone from the DOM (no row between RunDetailHeader and the two-pane grid).
  - [ ] Visually confirm the Claude chip renders inside `.tl__head`, right-aligned, content = `[logo] claude-sonnet-4-6 · 164.9k · $0.71 · ● drafting parallel plan` (or whatever the live activity is) at 2-decimal precision.
  - [ ] Visually confirm the GPT chip renders inside `.tl__tabs`, right-aligned, content shape identical to Claude's.
  - [ ] Visually confirm both chips' right edges align with each other and with the right padding boundary of `.rdvc__pane`.
  - [ ] DevTools: confirm both chips render at identical `width` (`min-width: 600px` enforces parity).
  - [ ] Confirm the activity phrase animates / updates as the live run progresses (existing `pulse-a` animation continues to render).
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
  - [ ] Fresh run (status: running, phase 0): segment 0 is `--p-info`; remaining segments are track color (`--md-outline-variant`).
  - [ ] Mid-run (status: running, phase 2): segments 0-1 are `--p-ok`; segment 2 is `--p-info`; remaining segments are track color.
  - [ ] Errored (status: errored, phase 1): segment 0 is `--p-ok`; segment 1 is `--p-err`; remaining segments are track color.
  - [ ] Completed (status: completed): all segments are `--p-ok`.
  - [ ] Deadlocked (status: deadlocked, phase N): segments 0..N-1 are `--p-ok`; segment N is `--p-warn`.
- [ ] Hover each phase segment and confirm the title tooltip reads `Pn label · state`.
- [ ] **Goal 8 — timeline card category chips.** Open a run that's past P2 round 1 (so per-round Δ activity exists):
  - [ ] Every turn card in P0 / P1 / P2 / P3 / P4 / P5 with category activity renders Q / D / I / C chips as `+raised | −closed` only — no bubble glyph, no standing-total figure.
  - [ ] The vertical separator between `+` and `−` is visible but subtle (≈ 28% opacity of `currentColor`, 1 px wide, vertically centered).
  - [ ] Chip tone color (info / warn / err / idle) reads correctly per category, in fixed Q→D→I→C order.
  - [ ] Capped chips (`c.capped > 0`) still render the `⊘ N` trailing suffix.
  - [ ] Zero-activity chips (no raised, no closed) render dim at `opacity: 0.55` — `+0 | −0`.
  - [ ] Clicking a chip still dispatches `dispatchCritiqueJump({ category, round, phase })` and the critique pane scrolls / filters as before.
  - [ ] Screen reader: `aria-label` reads `Questions this round: 3 raised, 2 closed` (or analogous).
  - [ ] `TlPhaseHeadChips` (phase-header chips) still render full bubble + value + add + sub — unchanged.
- [ ] No double-dot anywhere on the screen (confirms § 5.7 audit or safety net is in place). Visually scan: phase header Q/D stat chips, timeline turn-card chips, critique-pane filter chips.
- [ ] Light-mode and dark-mode parity check on every visual change above.
- [ ] Click handlers: chip clicks (kind / status / agent filters), phase tab clicks, segmented control clicks, agent chip click (if any), turn card expand, category chip click → critique pane jump. All unchanged.
- [ ] Keyboard: tab through the run-detail header, the relocated chips, the segmented control, Bar 1 / Bar 2 chips, and a turn card's category chips. Confirm focus order reads naturally and no element is unreachable.
- [ ] Reduced-motion check (`prefers-reduced-motion: reduce`): segmented phase progress doesn't animate, agent chip dot doesn't pulse. Existing `base.css` rule handles this.
- [ ] Regression scan: Compare page, Search page, How-It-Works page, run list, modals (turn modal, draft review). Confirm no incidental visual change (CSS scope is `.as.in-header`, `.tl__head`, `.tl__tabs`, `.crit2 .bar1 / .bar2`, `.phase-progress`, `.chip-add + .chip-sub`, plus the optional `:has()` safety net — should be inert elsewhere).
- [ ] Pytest suite (`uv run pytest tests/ -q`) passes.
- [ ] Update the changelog screenshots (`src/dual_research/ui/static/changelog-shots/`) where the run-detail header appears.

---

## 9. Risks

- **`flex-wrap: nowrap` + Bar 1 compaction not aggressive enough at some viewport sizes.** If the title + three P-codes + three numerals + counters still overflow at e.g. 1024 px, the test plan catches it; the fix is either a tighter `gap` or a slightly more conservative breakpoint. The user has two effective viewport sizes (wide monitor and MacBook), so the practical width range to test is narrow.
- **`:has()` browser support.** § 5.6 and § 5.7 both use `:has()`. Chromium 105+ / Safari 15.4+ / Firefox 121+. Confirm the project's browser floor; if a lower floor is required, switch to attribute-based selectors (`data-status-filter` / `data-agent-filter`) — a one-line JSX change per chip.
- **`.as-timeline` becomes dead code.** Once `<TimelineAgentBar>` is no longer rendered, `.as.as-timeline` (`components.css:283-295`) has no callers. Either delete it as part of this spec or leave it for a future cleanup spec. Recommend leaving it for the version after this — keeps this diff focused on the new placement, avoids accidentally breaking a different downstream surface that the implementer hasn't seen.
- **Activity phrase truncation in narrow.** At `width: 380px` and a 22-char activity phrase, the chip is sized for Claude's `claude-sonnet-4-6` content. If a future model id is longer, the activity phrase truncates first (via `.as-activity` ellipsis, SPEC-0112). Acceptable. If the model id ever exceeds ~18 chars, revisit.
- **PhaseDots state-machine drift.** The new `.phase-progress` implementation copies the `completed` / `current` / `failed` logic from the old `<PhaseDots>` verbatim. If the existing logic has bugs (e.g. status='completed' edge cases), they propagate. Acceptable — out of scope for a visual rework. A future spec can audit the state derivation.
- **Goal 8 category disambiguation by color alone.** Without the `Q` / `D` / `I` / `C` bubble glyph, identifying which chip is which relies on tone color (`info` / `warn` / `err` / `idle`) + fixed Q→D→I→C order. For colorblind users, the order is the fallback signal. The `aria-label` carries the explicit category name. Acceptable. If user feedback surfaces confusion, revisit by re-adding a tone-colored leading rule (`border-left: 2px solid currentColor`) on the slim chip instead of the full bubble.
- **The chip-add + chip-sub separator applies to TlPhaseHeadChips too.** TlPhaseHeadChips currently renders `bubble + value + add + sub` and the new separator (§ 5.9 CSS) will appear there too — a small visual change to a chip we're nominally not modifying. Acceptable (in fact, slightly improves readability) but worth a glance during review.
- **Cache busting forgotten.** Implementer must remember to bump `?v=` in `app.jsx`; without it users see stale CSS. Test plan covers it.

---

## 10. Open questions

- **§5.4 cost format implementation:** Option A (`costFormatter` prop on AgentStrip) vs Option B (`compactCost` flag). Recommend A. Final call at implementation time.
- **§5.7 auto-dot fix:** confirm audit needs a CSS safety net or whether the JSX path covers it. Resolve before opening the PR.
- **§5.8 current-segment animation:** is the `.pulse-info` halo cue worth adding to `.phase-progress__seg.is-current`? Mockup currently omits it for compactness; M3 reference designs typically include a subtle indicator. Could be a one-line follow-up rather than part of this spec.
- **§5.9 chip-add + chip-sub separator style:** vertical-line variant (recommended) vs middle-dot character. Final call at implementation time.
- **Phase count:** confirm `PHASES.length` is 5 (P0 Preflight through P4 Review) or 6 (including P5 Reconcile). The breadcrumb beneath PhaseDotsRow reads `preflight · drafts · negotiate · drafting · review` (5 labels) so the rendered cell count should match the breadcrumb. If `PHASES` actually carries 6, either trim the rendered cells or extend the breadcrumb in the same PR.
- **Goal 8 + TlPhaseHeadChips visual coherence:** the spec deliberately keeps `TlPhaseHeadChips` on the full bubble + value + add + sub presentation while card chips slim down to add + sub only. The user explicitly asked for cards-only. If the visual mix (phase header heavy, cards light) reads inconsistent in practice, a follow-up could either slim the phase headers too or thicken card chips back up — but that's a follow-up, not in this spec.
