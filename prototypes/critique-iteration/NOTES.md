# Critique pane — iteration notes (2026-05-22)

> **What this is.** Running record of every visual change locked in during the dark/light side-by-side iteration session for the critique pane. Mirrors the structure of [`prototypes/timeline-iteration/NOTES.md`](../timeline-iteration/NOTES.md): each element captured as (a) current live state, (b) locked target state, (c) DS file changes, (d) live JSX/CSS changes.

---

## 0. Artifacts

| Artifact | Path | Purpose |
|---|---|---|
| Workshop wrapper | [`mockup.html`](./mockup.html) | Three-tab switcher: Iteration (dark + light side-by-side) / Live (verbatim) / Design system (verbatim §12 + §13 + §13b). Monitor-width toggle (Narrow / Wide) in header. |
| Proposed iteration | [`proposed.html`](./proposed.html) | Iteration sandbox — verbatim dumps with iter-1 overlays. Theme controllable via `?theme=light\|dark`. Width-mode via `body[data-width-mode="narrow\|wide"]`. Accumulates `<style id="iter-N-…">` blocks as we iterate. |
| Live snapshot | [`live.html`](./live.html) | Verbatim `.crit2` outerHTML dumps for all four phase states (P0 / P2 / P4 / Σ). Sourced from `localhost:6173/#/runs/20260521-010637-dvs-backend-language-choice`. Immutable reference. |
| Design-system snapshot | [`ds.html`](./ds.html) | Verbatim copy of `<section id="critique">` (§12, lines 744-997), `<section id="itemcard">` (§13, lines 1001-1306), `<section id="thread">` (§13b, lines 1309-1403) from [`design-system/assets/Design System v2.html`](../../design-system/assets/Design%20System%20v2.html). Immutable reference. |

Per-phase raw dumps preserved under `_dump-{p0,p2,p4,sigma}.html` (immutable).

Open the workshop at `http://localhost:6174/prototypes/critique-iteration/mockup.html`.

### 0.1 Approach taken

All four phase states inlined into `live.html` and `proposed.html` as `<section class="phase-state" data-phase="…">…</section>` blocks. A small click handler forwards `.phase-tab` clicks to the visibility toggle.

### 0.2 Workshop collapse affordances (not a design proposal)

| Element | Default state | Toggle attribute | Click target |
|---|---|---|---|
| `.crit-group` (Resolved / Drift section header) | faithful to dump (`data-collapsed="true"` for Resolved by default) | `data-collapsed` | `.crit-group__hd` |
| `.item-card` (per-item card) | `data-expanded="true"` (faithful to live impl where ItemCard is always rendered fully) | `data-expanded` | `.item-card__head` — a chevron `›` is added in the head's right edge to advertise the affordance |
| `.source-row` (per-evidence row) | `aria-expanded="false"` (faithful to live default) | `aria-expanded` (on `.source-row__head`) | `.source-row__head` |

The per-phase dumps were **re-captured with every source row expanded** so the `<div class="source-row__body">` markup is present in the static HTML. The wrapper resets all source rows to `aria-expanded="false"` at load so the default state matches the live impl, and CSS hides `__body` via the sibling selector `.source-row__head[aria-expanded="false"] ~ .source-row__body`.

### 0.3 Workshop monitor-width toggle (Narrow ↔ Wide)

The live app renders the critique pane as half of a 2-column `rdvc` grid (timeline left, critique right — `<main style="grid-template-columns: 1fr 1fr">`). The pane's chrome also responds to a viewport-driven `@media (max-width: 1799px)` split at [components.css:907](../../src/dual_research/ui/static/components.css#L907) — labels and `pname`s hide in narrow.

To make the workshop faithfully reproduce both effects, `live.html` and `proposed.html` host a **2-pane shell** that mirrors the live `rdvc` layout: a timeline stub on the left (verbatim `.tl__head` + `.tl__tabs` outerHTML dumped from the live app + a `TIMELINE BODY · STUB` placeholder) and the critique pane on the right. The iframe width = total viewport; the grid splits it 1fr / 1fr so the critique pane gets its actual half-width:

- **Narrow** (1280px iframe) → each pane ~640px wide · narrow `@media` fires naturally · matches typical laptop critique width.
- **Wide** (1920px iframe) → each pane ~960px wide · wide `@media` does NOT fire · matches ultrawide / 4K critique width.

The workshop header has a **Narrow / Wide** toggle that sets the iframe's CSS width. `main.wsh__stage` has `overflow: auto` so the wide iframe scrolls horizontally inside the workshop chrome.

The earlier `body[data-width-mode]` CSS override hack is gone — natural viewport-based media query firing handles it now.

---

## 1. Iteration summary

| Iter | One-line change | Element touched |
|---|---|---|
| 1 | Right cluster of bar2 follows DS §12: agent + status chips wrapped in `.tab-group-solid` segmented controls; explicit "All" prepended to each segment; reorder so agent precedes status. Drift-chip slot added to bar1 `.right` (muted at count=0). **Kind chips (Q/D/I/C/All) kept as live `.chip` + `.cat-bubble` — same primitive as `.tl-phase__chips` in the timeline pane.** | bar1 + bar2 right cluster |
| 1.1 | Agent segment uses the live brand icons (Claude sunburst + OpenAI rosette in their tinted squares) — restored from the dot substitute. | bar2 agent segment |
| 1.2 | Every segmented-control option carries a phase-scoped `(N)` count alongside the label — `All (13) · Claude (6) · GPT (7)` / `All (13) · Open (0) · Resolved (13) · Drift (0)`. Drift count backfilled to `(0)` (drift 3.K — live impl skips the chip-value span when count is 0). | bar2 agent + status segments |
| 2 | bar2 fits on **one row at wide** (960px critique pane). Drop the explicit "All" button from both segmented controls (the kind cluster's `All (13)` is the global reset; click an active segmented option to deselect = "no filter = show all"). Tighten `.tab-solid` h-padding `12→10`, bar2 column-gap `12→8`, bar2 h-padding `16→12`. Total content 918px fits in 936px inner. | bar2 agent + status segments |
| 2.1 | bar2 stays one row when Resolved unfolds. **Constrain workshop iframe html+body to viewport** (`html, body { height: 100%; overflow: hidden }`) so `.crit2__body`'s own `overflow: auto` becomes the scroll container instead of the iframe page. Without this, the iframe page scrollbar steals ~5px from the pane width when body content grows, which was just enough to wrap bar2 to two rows. The live impl already has `.crit2__body { overflow: auto }` — this is a workshop wrapper fix, not a design proposal. | workshop iframe wrapper |
| 3 | Drop the "All" chip from the kind cluster too — same convention as agent + status. Kind cluster is now four chips: `Questions [N] · Disagreements [N] · Issues [N] · Comments [N]`. No chip active = "show all categories". Click an active kind chip to deselect. The bar1 run-wide totals (`13 / 0 / 13`) still surface the global counts. | bar2 kind cluster |
| 4 | Default: **Resolved unfolds, cards collapsed**. Apply timeline NOTES §2.4.1 frame to `.item-card`: `surface-container-high` bg, `outline-variant` border, `--md-shape-lg` (16dp) radius, **2px left stripe** per provider (sable Claude / sage GPT / idle System) via `data-raised-by` attribute. Hover lifts to `surface-container-highest` + `outline` + `elev-1`. 6px gap between cards via `.crit-group__body` flex column. | item-card frame (all states) |
| 5 | Catch-up from timeline NOTES §3.A (light-mode tokens drift) + §2.4.2.a (identity-chip background opacities). Scoped to `.item-card__head`: Claude chip `--p-sable @ 30%`, GPT chip `--p-sage @ 30%`, System chip `--p-idle @ 20%` + `color: --md-on-surface`. Light-mode text override: Claude label `#3b2810`, GPT label `#0a322d` (since live `tokens.css` is missing the `body.light` overrides for `--md-on-primary-container` / `--md-on-secondary-container`). **Invisible in the workshop until iter 7 injects the provider chip markup — verified via test-chip injection that the rules fire correctly for all three presets in both themes.** | preemptive `.item-card__head` chip rules |
| 6 | **Hide the kind chip** (`Question` / `Disagreement` / `Issue` / `Comment`) from the card head per card-design brief §1. Each head chip first tagged with `data-chip-role` (id / kind / state / raised-by / round / sources) via JS for robust targeting; `[data-chip-role="kind"]` is then `display: none`. Kind is conveyed by which filter / section the card sits in, not by an in-card badge. | item-card__head |
| 7 | **Rebuild head to match timeline turn-card pattern.** Reverts iter-6 (kind chip is back in). Card head is wiped + rebuilt by JS as: `[provider chip with brand SVG · tone-claude/gpt/neutral] [round chip · mono neutral · "round N"] [kind chip · tone-coloured: Q=info / D=warn / I=err / C=idle]` left-aligned, `[state chip]` right-aligned via `margin-left: auto`. **ID chip + sources chip dropped entirely** ("cryptic" per user direction). Provider chip's brand SVG cloned from the bar2 agent chip (Claude/GPT) or inlined (System gear). | item-card__head (rebuilt) |
| 7.1 | Match timeline card height + spacing **exactly**. Override live `.item-card` defaults: `padding: 0` (was `12px 14px`), `margin: 0` (was `8px 0`); head `padding: 6px 12px` (was `8px 12px`), no min-height. Resulting collapsed card height **36px** (was 64), head height 34px, 6px flex gap between cards via `.crit-group__body` — identical to timeline `.tl-thread` measurements. | item-card frame |
| 7.2 | **bar2 cannot break under any state.** Add `flex-wrap: nowrap` on `.bar2.crit-filter-row` as a backstop so the header is single-row at every width regardless of whether Resolved is unfolded. Also `flex-wrap: nowrap` on `.kind-tabs` so the kind cluster doesn't wrap internally. | bar2 layout |
| 7.3 | **Restore segmented-control labels at every width** ("Claude", "GPT", "Open", "Resolved", "Drift") — icon-only was too cryptic. At narrow (≤1799px viewport, fires naturally), drop the `(N)` count in segmented controls only so the kind cluster reclaims ~100px of horizontal room and bar2 stays single-row. At wide, both labels + counts are shown. Kind chips already lose their text labels at narrow per the live `@media` rule, so identity at narrow is: kind = colored bubble + count, segmented = label + icon (no count). | bar2 segmented control labels |
| 8 | **Round + state chips carry the round annotation.** Round chip: `raised · R1` (was just `round 1`). State chip: `resolved · R2` / `capped · R4` — terminal round parsed from `.item-card__lifecycle-footer` text ("✓ resolved at round 2 · 2 turns to converge") with fallback to the last `.item-card__transition` meta. Subtle middle-dot separator inside each chip via `.chip-sep` span (opacity 0.4, 4px margin) so the two tokens read as one unit with a clear inner divide. | item-card__head round + state chips |
| 8.1 | Capitalize the leading word in the round + state chips: `Raised · R1`, `Resolved · R3`, `Capped · R4`. Via CSS `text-transform: capitalize` on `[data-chip-role="round"] .chip-label` + `[data-chip-role="state"] .chip-label`. The `R<N>` suffix is unaffected (already uppercase). Vocabulary covered: Raised, Resolved, Capped, Acknowledged, Withdrawn, Addressed, Open, Drift — any state from spec 0119 §9.5. | item-card__head round + state chip labels |
| 9 | **Evidence-needed → icon chip with hover tooltip.** Detects `.item-card__evidence-needed` per card; injects a tiny `.chip.tone-info.chip-icon-only.no-dot.evidence-chip` after the kind chip carrying a Material `link` icon and the full sentence (`"Evidence needed — addresses must cite consulted sources."`) as the `title` attribute (native browser tooltip on hover) + `aria-label`. The original `.item-card__evidence-needed` body line is `display: none` so the card height never breaks. 28px wide chip, doesn't disturb the 36px row height. | item-card__head (between kind and state) |
| 10 | **Resolver logo inside the state chip.** State chip is now `<state> · [actor icon] · R<N>`. Actor parsed from the last `.item-card__transition-meta`'s `by X` suffix (Claude / GPT / Orchestrator / System). The 12×12 brand square is reused from the provider chip's `chip-leading-icon` markup. **Orchestrator / System are skipped** (they cap, don't resolve in the agent sense) — when the resolver is the orchestrator the chip falls back to `Capped · R<N>` without an icon. Makes self-resolution legible: Claude-raised items that Claude itself resolves stand out from those GPT resolved. | item-card__head state chip label |
| 11 | **Expanded card view — v1 (superseded by iter 12).** Tinted-row layout with meta + reason. | item-card body + timeline + transitions + footer |
| 12 | **Expanded view rebuilt per user screenshot.** Replaces iter-11 entirely. JS wipes the original body + timeline DOM (display: none) and injects an `.item-card__lifecycle.iter12` section after the head. Layout: `LIFECYCLE` label + sequence of `.lc-row` items, each with a chip cluster (`[provider · round · verb · modifier?]`) on top and an italic-serif `.lc-row-quote` below. Synthetic first row uses `verb="raised"` with item-body text as the quote and the head's data-raised-by + round as the actor. Subsequent rows parsed from `.item-card__transition` entries: `parseTransition` extracts round + verb + modifier (e.g., `hard_cap`, `ghost_cap`) + actor. **Orchestrator/system transitions skip the provider chip** per screenshot (`[round 5] [capped] [via hard cap]`). Verb tone map: raised=info / addressed=warn / resolved=ok / capped=err / acknowledged=warn / withdrawn=idle / ghosted=warn / drift=err. Provider chip backgrounds match the head's 30%/30%/20% color-mix opacities. Lifecycle footer below shows `✓ resolved at round 3 · 2 turns to converge` with state-toned color. Sources segment styled with `SOURCES (N)` overline header, collapsible source-rows: head row carries chevron + title + host + optional `⚠ unverified` chip; body reveals fields in a 130px-label / 1fr-value grid (URL / SEARCH QUERY / FETCHED / UNVERIFIED REASON) + an italic-serif excerpt at the bottom in a tinted recess. | item-card[data-expanded="true"] — body + timeline replaced by .item-card__lifecycle |
| 13 | **Source attribution badges.** Three pieces: (a) `[🔗 source requested]` extra chip on the raised row when the card has `.item-card__evidence-needed`; (b) `[🔗 source provided]` extra chip on the first Claude/GPT transition when the card has `.item-card__sources`; (c) per-source meta chip `[provider icon · R<N>]` injected into each `.source-row__head` showing which round + agent provided that source (extracted from the first Claude/GPT transition's actor + round). The `source requested` chip is tone-info, `source provided` is tone-ok, and the per-source meta chip is mono neutral. Tooltip on the meta chip ("Provided by GPT in round 2"). | item-card lifecycle rows + source-row heads |
| 14 | (a) **Phase-section collapse affordance** strengthened: `.crit-group__hd` gets `cursor: pointer` + hover/active background tint so the click feedback is unmistakable (verified DOM toggling already worked — this is for UX visibility). (b) **Pre-expand first source-row per card**: in `initCollapseState`, after setting all source rows to collapsed, the first row inside each `.item-card__sources` is set back to `aria-expanded="true"`. Result: when you open a card with 2+ sources, you see the expanded view AND the collapsed view stacked. Cards with 1 source open expanded. (c) Source-row meta chip pushed to right edge via `margin-left: auto` so it's always visible next to (or before) the unverified chip. Title `max-width: 280px` with ellipsis to give the meta chip room. | crit-group hover + source-row default state + meta chip position |
| 15 | (a) **Item-card head clickable in both states**: explicit `cursor: pointer` + hover/active background tint on `.item-card__head` regardless of `data-expanded`. The toggle handler always worked at the DOM level (verified — `data-expanded` flips on every click), but the expanded state lacked a visible hover affordance. (b) **Auto-expand first card with sources per phase**: each `.phase-state` finds the first `.item-card` whose subtree contains an `.item-card__sources` segment and sets `data-expanded="true"` on it. Result: opening the workshop shows one fully demo'd card per phase with `source requested → source provided` lifecycle + the actual sources segment visible at the bottom — no clicks required. Other cards stay collapsed for comparison. | .item-card__head hover + auto-expand first sources card |

---

## 2. Per-element specification

### 2.1 Bar 1 — phase tabs + run-wide totals + drift chip

Anchor: `.crit2 > header.bar1`.

#### 2.1.1 Phase tabs

**Now / After.** No change. Live `.phase-tab` markup already matches DS `.phase-tab` shape (32px height, tertiary-container active state). Divergence from DS §12: live has `P0 Brief` tab, DS only documents three (P2 / P4 / Σ). See drift 3.A.

**DS change.**
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §12 — add `P0 Brief` to each of states A/B/C.
- [`SPEC.md`](../../design-system/SPEC.md) §4.1 — update phase-tab description.

**Live change.** None.

#### 2.1.2 Run-wide totals (`.crit-totals`)

**Now / After.** No change. The Σ Summary state bug where totals reset to `0/0/0` is **drift 3.F** — not part of this iteration.

#### 2.1.3 Drift chip — NEW slot

**Now.** Bar 1 has no drift indicator at all. The Drift status filter chip in bar 2 carries filter intent but no run-wide visible-from-the-top signal exists.

**After.** A `<span class="drift-chip">⚠ {count} drift</span>` in `.bar1 > .right`, after `.crit-totals`. Styling from DS [`v2-m3-page.css:722-731`](../../design-system/assets/styles/v2-m3-page.css#L722): 28px full-radius pill, `color-mix(--p-err 18%, transparent)` bg, `--p-err` color, triangle ⚠ icon + "N drift" label.

When `drift_count === 0`, render muted (`color-mix(on-surface 6%, transparent)` bg + `on-surface-faint` color + 0.55 opacity). Slot stays present so chrome doesn't reflow if drift appears mid-run.

**DS change.** SPEC.md §4.1 already documents bar-1 drift chip. DS §12 state A renders it. Add a count=0 muted-variant example.

**Live change.**
- [`run-detail.jsx`](../../src/dual_research/ui/static/run-detail.jsx) — bar-1 render: add `<DriftChip count={runTotals.drift} />` after `<crit-totals>` in the `.right` cluster.
- [`components.css`](../../src/dual_research/ui/static/components.css) — add `.drift-chip` rules (source: iter-1 stylesheet block).

---

### 2.2 Bar 2 — kind cluster (Q / D / I / C / All)

Anchor: `.crit2 > header.bar2.crit-filter-row > .kind-tabs > .chip[data-kind-filter]`.

**Now / After.** **No visual change to the chips themselves.** Live renders five chips as `<button class="chip tone-X no-dot" data-kind-filter="true"><span class="cat-bubble">Q</span><span class="chip-label">Questions</span><span class="chip-value">8</span></button>`. Iter-1 wraps these in a `<div class="kind-tabs">` flex group (no styling) so the segmented controls can sit on the right via `margin-right: auto`.

Rationale for keeping live: the `.cat-bubble` + `.chip` primitive is the same one used by `.tl-phase__chips` (timeline phase header chip cluster — see timeline NOTES §2.1.4). Visual consistency across panes outweighs the DS §12 flat `.kind-tab` prescription. The DS §12 pattern was drawn before the timeline / critique chip alignment landed; the DS needs to come into line, not the live impl.

**DS change.**
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §12 — replace the `.kind-tabs > .kind-tab` markup with the live `.chip[data-kind-filter]` markup. Update [`v2-m3-page.css`](../../design-system/assets/styles/v2-m3-page.css#L734) to match (or remove the `.kind-tab` rules and reuse `.chip[data-kind-filter]`).
- [`SPEC.md`](../../design-system/SPEC.md) §4.1 + §9.6 — codify that critique bar-2 kind filters use the same chip + cat-bubble primitive as `.tl-phase__chips`; the letter-bubble carries kind identity (Q / D / I / C) across panes.

**Live change.** None.

#### 2.2.1 Order

Live: `Q / D / I / C / All`. DS / SPEC: `All / I / C / Q / D`. **Iter-1 keeps live order** (see drift 3.B). To be revisited.

---

### 2.3 Bar 2 — agent + status segmented controls

Anchor: `.crit2 > header.bar2.crit-filter-row > .tab-group-solid[data-group="agent"|"status"]`.

**Now.** Live renders agent and status as individual `<button class="chip tone-neutral no-dot">` chips — three for status, two for agent — separated by `<span class="crit-filter-spacer">` dividers. No explicit "All" button (the absence of selection is implicit).

**After.** Two `<div class="tab-group-solid">` segmented-control pills per DS §12.
- `agent`: `[All (13)]` · `[🟧 Claude (6)]` · `[🟢 GPT (7)]` — explicit "All" first; live brand icons (Claude sunburst in sable square, OpenAI rosette in sage square) retained from the live impl. Every option carries a `(N)` phase-scoped count.
- `status`: `[All (13)]` · `[Open (0)]` · `[Resolved (13)]` · `[Drift (0)]` — explicit "All" first; counts on every option (Drift always shows even when 0, fixing drift 3.K).

Active state: `var(--md-surface)` background + `elev-1` per DS [`v2-m3-page.css:781`](../../design-system/assets/styles/v2-m3-page.css#L781) (lifted-tile pattern).

**Count slot.** Rendered as parens `(N)` next to the label — small, muted, monospace. Reuses the live `.chip-value` span so we don't introduce a new primitive: just restyled inside `.tab-group-solid .chip` to drop the tinted-pill background and add `::before/::after` paren content. Agent/All counts injected by the iter-1 script (live impl doesn't carry them); status counts pre-exist on Open/Resolved chips in the dump; Drift is backfilled.

**Layout.** Right cluster carries agent THEN status (DS §12 state-A markup at lines 786-797). `.crit-filter-spacer` dividers removed — the segmented-control pills provide visual grouping. `.bar2.crit-filter-row` gains `flex-wrap: wrap` so the right cluster drops to a second row at typical pane widths.

**DS change.** Already matches DS.

**Live change.**
- [`run-detail.jsx`](../../src/dual_research/ui/static/run-detail.jsx) — wrap status and agent chip clusters in `<div class="tab-group-solid">`. Add explicit "All" `<button class="tab-solid">` to each segment. Replace `chip-leading-icon` brand-mark squares with `<span class="dot" style="background: var(--p-sable|sage)">` colored dots.
- [`components.css`](../../src/dual_research/ui/static/components.css) — add `.tab-group-solid` + `.tab-solid` rules (source: iter-1 stylesheet block + [DS v2-m3-page.css:766-782](../../design-system/assets/styles/v2-m3-page.css#L766)).
- Drop `.crit-filter-spacer` element entirely.

---

## 3. Drift surfaced during bootstrap

These are bugs / inconsistencies between live, DS, and SPEC that surfaced while building the verbatim wrappers and counting cards.

### 3.0 Anchor run lacks open / drift items

All 38 critique items in the chosen run are in terminal states (`resolved` / `acknowledged` / `capped`). The `Open · new this round`, `Open · carried over`, and `Drift` group templates cannot be visually verified against the live impl from this dump. May need a second-run dump.

### 3.A DS phase-tab set does not match live

Live: P0 / P2 / P4 / Σ. DS §12 + SPEC.md §4.1: only P2 / P4 / Σ. P0 Brief was added later. Fix in DS + SPEC.

### 3.B Bar-2 kind-tab order disagrees between DS, SPEC, and live

SPEC.md = DS = `All / I / C / Q / D`. Live = `Q / D / I / C / All`. Iter-1 doesn't lock order; open question.

### 3.C DS §13 uses `.crit-card` markup; live uses `.item-card`

DS §13 renders cards as `<article class="crit-card">` with `.crit-card-head` / `.crit-card-body` / `.crit-card-id` etc. Live uses `<article class="item-card">` with `.item-card__head` / `.item-card__body` / `.item-card__timeline` / `.item-card__lifecycle-footer` / `.item-card__sources` (BEM). Promote live BEM into DS.

### 3.D ID rendering inconsistency

Live renders item id as the **first chip** in the header (per SPEC.md §4.8). DS renders it as a separate text line below the body (`.crit-card-id`). DS contradicts the spec it documents. Fix DS.

### 3.E "Resolved" group title misrepresents terminal-state mix

P0 has 11 resolved + 2 capped under "Resolved 13". P4 has 11 resolved + 1 acknowledged under "Resolved 12". Group partitions by `isTerminal(state)`, not `state === 'resolved'`. Suggest splitting into per-state groups (Resolved / Acknowledged / Capped / Withdrawn) per spec 0144 §6.3.d enumeration.

### 3.F Σ Summary bar-1 totals reset to zero

When the Σ tab is active, bar-1 shows `0 introduced · 0 open · 0 resolved`. Run has 38 items. Totals likely derived from active-phase items array (empty on Σ) instead of run-wide aggregate. Make bar-1 totals tab-invariant.

### 3.G Σ Summary uses inline styles instead of CSS classes

`.crit2__body` on Σ Summary has ~25 inline `style="…"` attributes per element. Promote into `components.css` classes (e.g. `.crit-summary__table`, `.crit-summary__phase-section`).

### 3.H DS Σ Summary body diverges from live Σ Summary body

DS shows three prose call-outs ("Highest-leverage open thread", "Hottest disagreement", "Drift"). Live shows per-phase per-kind round-by-round tables. Neither is locked in SPEC.md §4.1.

### 3.I Cards in live impl have no card-level collapse state

ItemCard renders fully always. The "collapsed vs expanded" mental model carried over from the legacy `.qthread`. Decide whether ItemCard should gain a collapsed state.

### 3.J Sources segment always rendered; `aria-expanded="false"` on every source row

`.source-row__body` is conditionally rendered (not just CSS-hidden) — workshop re-dumped with everything expanded so the body markup is in the static HTML for toggling.

### 3.K Bar-2 "Drift" chip has no count slot when count=0

Open and Resolved show `0`; Drift skips the `.chip-value` span entirely. Always render the count span.

---

## 4. Verification reference (bootstrap)

| Phase | Cards | Card kinds | Sources rows | Cards w/ Evidence-needed | Anchors | Sources chips | bar1 totals | bar2 visible |
|---|---|---|---|---|---|---|---|---|
| P0 | 13 | 11 resolved · 2 capped | 3 | 0 | 13 | 1 | `13 / 0 / 13` | yes |
| P2 | 13 | 13 resolved | 13 | 7 | 11 | 6 | `13 / 0 / 13` | yes |
| P4 | 12 | 11 resolved · 1 acknowledged | 14 | 6 | 11 | 7 | `12 / 0 / 12` | yes |
| Σ Summary | 0 | — | 0 | — | 0 | — | `0 / 0 / 0` *(drift 3.F)* | **no** |

All counts match the live app readouts taken before the dump. Source-row totals reflect cards with sources — re-dumped with every row expanded so the workshop can toggle their body visibility.
