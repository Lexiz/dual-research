# Timeline pane — locked iteration notes (2026-05-22)

> **What this is.** A complete record of every visual change locked in during the dark/light side-by-side iteration session on 2026-05-22. **Not a spec** — these are working notes you can mine for specs later. Each element below is described in (a) its current live state, (b) the locked target state, (c) the changes needed in the design system, (d) the changes needed in the live JSX/CSS.
>
> **What this is not.** A formal acceptance criteria document, a migration plan, or a versioning declaration. There are no "shall" / "must" / risks / test-plan sections. Use this to draft those documents when ready.

---

## 0. Artifacts

| Artifact | Path | Purpose |
|---|---|---|
| Workshop wrapper | [`prototypes/timeline-iteration/mockup.html`](./mockup.html) | Three-tab switcher: Proposed (dark + light side-by-side) / Live (verbatim) / DS (verbatim §16) |
| Proposed iteration | [`prototypes/timeline-iteration/proposed.html`](./proposed.html) | The locked target state — verbatim live HTML + 12 stacked iteration stylesheets (`<style id="iter-1-…">` through `<style id="iter-12-…">`) |
| Live snapshot | [`prototypes/timeline-iteration/live.html`](./live.html) | Verbatim `.rdvc__pane` outerHTML dumped from `localhost:6173/#/runs/20260521-010637-dvs-backend-language-choice` (modal closed, 5 phases, 41 turn cards). Immutable reference. |
| Design-system snapshot | [`prototypes/timeline-iteration/ds.html`](./ds.html) | Verbatim `<section id="timeline">` copied from `design-system/assets/Design System v2.html` lines 1685–1793. Immutable reference. |

Open the workshop at `http://localhost:6174/prototypes/timeline-iteration/mockup.html` (via the `prototype-mockup` Claude-Preview server config).

---

## 1. Iteration summary

| Iter | One-line change | Element touched |
|---|---|---|
| 1 | `P{N}` → `Phase {N}` in the marker label | Phase header |
| 2 | Removed redundant `.tl-phase__pcode` (`PHASE 0` after the chevron) | Phase header |
| 3 | Added a `System` identity chip + human-readable Error chip for agentless cards | Turn cards (brief + render-error) |
| 4 | M3 timeline-card chrome — filled card, outline, hover elev-1, expanded elev-2 | Turn cards (both states) |
| 4b | Side-by-side dark/light rendering in the workshop | Mockup wrapper only |
| 5 | 16 px horizontal pane gutter + bumped card surface to `surface-container-high` + outline to `outline-variant` | Phase body + turn card chrome |
| 6 | Identity-chip background bumped to ~30% color-mix (Claude / GPT / System) | Turn card head |
| 7 | Softer System chip (idle @ 20%) + explicit dark Claude/GPT text in light mode | Turn card head |
| 8 | Provider-tinted header strips (sable/sage @ 8%) + 2 px provider left-stripe on each card + radius `--md-shape-lg` (16dp) | Header strips + turn cards |
| 9 | Category bubbles in phase-header chips dimmed to 70% alpha | Phase-header chip cluster |
| 10 | Activity chip bumped to `surface-container-highest` + cost rounded to 2 decimals | Turn card head + expanded actions |
| 11 | Activated spec 0138 §5.1 sweep animation by setting `.is-live` on the Claude header strip; activity dot pulse + phrase updated to "negotiating · round 4" | Header strips |
| 12 | `box-shadow: var(--md-elev-2)` added to `.as.in-header.is-live` | Header strips (live state only) |

---

# 2. Per-element specification

Each element below is in the same fixed format:

> **Now** — what the live app renders today
> **After** — the locked target state
> **DS change** — design-system files + sections that change
> **Live change** — live code files + locations that change

---

## 2.1 Phase header

Anchor in current live DOM: `.tl-phase > .tl-phase__hd`

### 2.1.1 Marker (left of chevron)

**Now.** A 10 px colored dot + a `.lbl` span reading `P0` / `P1` / `P2` / `P3` / `P4`. Class state `.is-done` / `.is-current` controls dot color. The full markup ([components.css:2369–2386](../../src/dual_research/ui/static/components.css)):
```html
<span class="tl-phase__marker is-done" aria-hidden="true">
  <span class="dot"></span>
  <span class="lbl">P0</span>
</span>
```

**After.** Same dot, same state classes — but the label reads the full phase ordinal: `Phase 0` / `Phase 1` / etc.

```html
<span class="tl-phase__marker is-done" aria-hidden="true">
  <span class="dot"></span>
  <span class="lbl">Phase 0</span>
</span>
```

CSS `.tl-phase__marker .lbl` already has `text-transform: none` (verified in computed styles), so the literal mixed-case "Phase 0" renders correctly. The marker box auto-expands to fit the longer label.

**DS change.**
- [`design-system/assets/Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §16 anatomy block has no `.tl-phase__marker` example today. Add one — the spec currently shows only the 4-col phase header (chev · pcode · name · meta); the live impl has the 6-col with marker + chips. The DS rendered reference needs to catch up.
- [`design-system/SPEC.md`](../../design-system/SPEC.md) §4.4 Timeline pane — add a bullet documenting the marker (state classes, dot + full-word label).

**Live change.**
- [`src/dual_research/ui/static/run-detail.jsx`](../../src/dual_research/ui/static/run-detail.jsx) — find the `<span className="lbl">` inside the `.tl-phase__marker` render and change `P{vp.pid}` → `Phase {vp.pid}`. The marker render lives near line 909.
- No CSS change needed — text-transform is already `none`.

---

### 2.1.2 Phase code (`.tl-phase__pcode`)

**Now.** Renders `PHASE 0` (uppercase, letter-spaced 10 px data font, faint color) immediately after the chevron. With iter 1's marker change, it duplicates information already conveyed by the marker.

```html
<span class="tl-phase__pcode">PHASE 0</span>
```

**After.** Deleted. The marker label carries the phase identity now; the pcode is redundant.

**DS change.**
- [`design-system/SPEC.md`](../../design-system/SPEC.md) §4.4 — remove any reference to `.tl-phase__pcode`.
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §16 anatomy card — drop the `<span class="tl-phase__pcode">PHASE 2</span>` from the example markup.
- [`composed-components.css`](../../design-system/assets/styles/composed-components.css) — remove the `.tl-phase__pcode` style rule.

**Live change.**
- `run-detail.jsx` — remove the `<span className="tl-phase__pcode">PHASE {vp.pid}</span>` element from the phase-header render (~line 914).
- [`components.css`](../../src/dual_research/ui/static/components.css) — remove the `.tl-phase__pcode` rule.
- The grid columns on `.tl-phase__hd` drop from 6 columns (`auto 20px auto auto 1fr auto`) to 5 columns (`auto 20px auto 1fr auto`) — update the rule.

---

### 2.1.3 Phase name + meta

**Now / After.** No change. `.tl-phase__name` continues to show the human phase name ("Preflight", "Parallel draft", "Negotiate plan", "Cross-review"), `.tl-phase__meta` shows duration + round count.

---

### 2.1.4 Phase-header chip cluster

Anchor: `.tl-phase__hd > .tl-phase__chips`

**Now.** A flex-wrap cluster of category counter chips (Q, D, I, C as relevant per phase) plus an optional `⚠ ledger drift` chip. Each category chip is a button with 5 slots:
```html
<button class="chip tone-info no-dot" aria-label="Questions: 0 standing, 8 raised, 8 closed, 1 capped">
  <span class="cat-bubble">Q</span>
  <span class="chip-value">0</span>
  <span class="chip-add">+8</span>
  <span class="chip-sub">−8</span>
  <span class="chip-suffix">⊘ 1</span>
</button>
```

The `.cat-bubble` is a 14 px filled circle in the brand-tone color (info blue / warn amber / err red / idle grey) with a knockout-white letter. Currently rendered at 100% saturation.

**After.**
- **Bubble background dimmed to 70% alpha.** `color-mix(in srgb, var(--p-X) 70%, transparent)` where X is `info` / `warn` / `err` / `idle`. The bubble is still distinctly brighter than the chip's 18%-tinted background, but the 100% saturation no longer dominates the phase header.
- **Knockout-white letter preserved** — readable on all four tones at 70% alpha.
- **Slot order, sizes, font weights, letter typography — all unchanged.**

**DS change.**
- [`SPEC.md`](../../design-system/SPEC.md) §9.6 — clarify that the "filled circle with knockout-white letter" rule allows alpha-modulated fills as long as the brand hue remains dominant. Add a one-line note: *"On phase-header chip clusters the bubble may be rendered at 70% alpha; the brand color must remain the dominant hue."*
- [`composed-components.css`](../../design-system/assets/styles/composed-components.css) — add scoped overrides for `.tl-phase__chips .chip.tone-{info,warn,err,idle} .cat-bubble`. Source for the iteration is the iter-9 stylesheet block in `proposed.html`.
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §16 — the rendered anatomy doesn't show this chip cluster today (the live impl has it, the DS doesn't). Add a phase-header example with at least Q + D chips.

**Live change.**
- [`components.css`](../../src/dual_research/ui/static/components.css) — add the scoped `.tl-phase__chips .chip.tone-X .cat-bubble { background: color-mix(...); }` rules. Do **not** touch the global `.chip .cat-bubble` rule (the critique-pane chips need to keep 100% saturation — different surface, different visual budget).
- No JSX change.

---

## 2.2 Header agent strips

Anchor: `.rdvc__pane > .tl__head .as.is-a.in-header` (Claude) and `.tl__tabs .as.is-b.in-header` (GPT).

### 2.2.1 Provider-tinted background

**Now.** `.as.in-header` background is `var(--md-surface-container)` (flat). Identity comes from the 2 px left-border (sable / sage) plus the brand mark icon inside.

**After.** The strip background carries a subtle 8% tonal mix matching the provider:
- `.as.is-a.in-header` → `color-mix(in srgb, var(--p-sable) 8%, var(--md-surface-container))`
- `.as.is-b.in-header` → `color-mix(in srgb, var(--p-sage) 8%, var(--md-surface-container))`

The 2 px left-stripe stays. The brand mark icon stays.

**DS change.**
- [`SPEC.md`](../../design-system/SPEC.md) §3 AgentStrip primitive entry — add a note: *"Inside `.tl__head` / `.tl__tabs` (the `in-header` variant), the strip carries an 8% color-mix tonal background matching the provider."*
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) — currently no AgentStrip example renders in §16 with the in-header variant. Add a rendered example showing the tint.

**Live change.**
- [`components.css`](../../src/dual_research/ui/static/components.css) line ~407 (the `.as.in-header` rule) — add `background: color-mix(in srgb, var(--agent-rgb-a/b) 8%, var(--md-surface-container));` via the existing `.is-a` / `.is-b` selectors at lines 364–365. Or add two new rules: `.as.is-a.in-header` / `.as.is-b.in-header` with the color-mix backgrounds.

### 2.2.2 Live-state animation (already exists in live CSS)

**Now.** Spec 0138 §5.1 added a `.as.in-header.is-live::before` gradient-sweep pseudo-element ([components.css:429–491](../../src/dual_research/ui/static/components.css)) that runs `@keyframes as-pulse-sweep` for 3.2 s ease-in-out infinite, 18%-alpha agent-tinted gradient peak sweeping 100% → 0% → 100% on background-position. GPT gets `animation-delay: -1.6s`. `prefers-reduced-motion: reduce` falls back to a static tint.

The CSS is already correct. The animation triggers when the JSX sets the `is-live` class on the strip.

**After.** Same animation. Adopt the existing spec 0138 implementation as-is.

**DS change.** None — the animation already lives in `components.css` and is documented in spec 0138.

**Live change.** Confirm the JSX sets `.is-live` correctly on the strip whose agent is currently doing work this round. If you're unsure where that derivation happens today, search for `is-live` in `run-detail.jsx`.

### 2.2.3 Activity dot + phrase (right side of strip)

**Now.** A 6 px dot + activity phrase. When the run is idle / deadlocked, the dot is `var(--md-outline)` (neutral grey) and the phrase reads "deadlocked" / "idle" etc.

**After.** When the strip is `.is-live`:
- Dot color → `var(--p-info)` (info blue, signaling running)
- Dot has a slow halo pulse (`box-shadow` keyframes, ~2 s ease-in-out infinite)
- Activity phrase reads the actual phase-and-round context: `"negotiating · round 4"` / `"reviewing · round 2"` / `"drafting"` / etc.

When the strip is **not** `.is-live` (idle / completed / deadlocked):
- Dot color → `var(--md-outline)` (or `var(--p-err)` for deadlocked, `var(--p-ok)` for completed — same as today)
- No pulse
- Phrase reflects the static state

**DS change.**
- [`SPEC.md`](../../design-system/SPEC.md) §4.4 — add a brief note documenting the live-state pulse on the activity dot (separate from the strip-level sweep animation).

**Live change.**
- [`components.css`](../../src/dual_research/ui/static/components.css) — add the dot-pulse keyframes and apply them via `.as.in-header.is-live .activity-dot { animation: pulse-info 2s ease-in-out infinite; }` (or whatever the activity-dot class is in the live JSX).
- `run-detail.jsx` — make sure the activity-phrase derivation picks up the live phase + round rather than the terminal state.

### 2.2.4 Elevation on the live strip

**Now.** `.as.in-header` has no `box-shadow` at any state. The live state is signaled only by the sweep + dot.

**After.** `.as.in-header.is-live { box-shadow: var(--md-elev-2); transition: box-shadow 150ms standard-easing; }`. The lift is the fourth reinforcing signal alongside the sweep, the dot pulse, and the activity phrase.

**DS change.**
- [`SPEC.md`](../../design-system/SPEC.md) §4.4 — add: *"The live-state agent strip carries `--md-elev-2`."*
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §16 — render an `.is-live` example for visual reference.

**Live change.**
- [`components.css`](../../src/dual_research/ui/static/components.css) — add the `.as.in-header.is-live { box-shadow: var(--md-elev-2); transition: box-shadow 150ms var(--md-easing-standard); }` rule.

---

## 2.3 Phase body — gutter

Anchor: `.tl-phase__body` (the flex column inside each phase that holds the turn cards).

**Now.** `.tl-phase__body` has `padding: 4px 0 8px` — zero horizontal padding. Turn cards extend flush to the pane's left + right edges, and the card borders sit directly against the pane's container.

**After.**
- `.tl-phase__hd { padding: 12px 16px; }` (was `10px 8px`) — phase headers are inset 16 px from pane edges.
- `.tl-phase__body { padding: 8px 16px 12px; gap: 6px; }` — phase body matches the same 16 px horizontal gutter. Cards sit inside the gutter.

**DS change.**
- [`composed-components.css`](../../design-system/assets/styles/composed-components.css) — update the `.tl-phase__hd` and `.tl-phase__body` padding values.
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §16 — re-render the anatomy example to show the inset.

**Live change.**
- [`components.css`](../../src/dual_research/ui/static/components.css) — update the same two selectors.
- No JSX change.

---

## 2.4 Turn card — collapsed state

Anchor: `<article class="qthread tl-thread is-{status}">` containing a `<header class="tl-card-head">`. Below describes the LOCKED structure for a card in its default (non-expanded) state.

### 2.4.1 Frame

**Now.**
- Background: `var(--md-surface-container)` (`#14171c` dark / `#f0ede4` light)
- Border: `1px solid var(--md-outline-hair)` (`#1c1f24` dark)
- Border-radius: not explicitly set on `.tl-thread` (inherits transparent default)
- Padding: 0 (head owns padding)
- Margin: depends on phase body
- Card surface is the SAME as the page background tier above it, so cards blend visually.

**After.**
- Background: `var(--md-surface-container-high)` (one tier brighter — `#191c21` dark / `#e9e5d9` light)
- Border: `1px solid var(--md-outline-variant)` (one tier more visible — `#262a31` dark)
- **Border-left: `2px solid <provider>`** where `<provider>` is `var(--p-sable)` for Claude, `var(--p-sage)` for GPT, `var(--p-idle)` for System
- Border-radius: `var(--md-shape-lg)` (16 dp — M3-Expressive card radius)
- Padding: 0 (head owns padding)
- Margin: 0 (gap is controlled by parent `.tl-phase__body { gap: 6px; }`)
- Overflow: hidden (so the expanded body's rounded corners clip properly)
- Transition: `background`, `box-shadow`, `border-color` — 150 ms standard easing

**Hover state:**
- Background: `var(--md-surface-container-highest)` (`#21252b` dark / `#e3decf` light)
- Border: `1px solid var(--md-outline)`
- `box-shadow: var(--md-elev-1)` (resting → hover lift)

**Selector for the provider stripe.** Uses CSS `:has()`:
```css
.tl-thread:has(.tl-card-head > .chip.tone-claude)            { border-left: 2px solid var(--p-sable); }
.tl-thread:has(.tl-card-head > .chip.tone-gpt)               { border-left: 2px solid var(--p-sage); }
.tl-thread:has(.tl-card-head > .chip.tone-neutral:not(.mono)) { border-left: 2px solid var(--p-idle); }
```

`:has()` is supported in Chrome 105+ / Safari 15.4+ / Firefox 121+. If a fallback is needed for older browsers, add a `data-provider="claude|gpt|system"` attribute in JSX and select on that.

**DS change.**
- [`SPEC.md`](../../design-system/SPEC.md) §3 — add a new primitive entry: *"Timeline card (`.tl-thread`) — filled card on `surface-container-high`, `outline-variant` border, **2 px left-stripe per provider** (sable / sage / idle), `--md-shape-lg` (16 dp), hover lifts to `surface-container-highest` + `outline` + `elev-1`."*
- [`composed-components.css`](../../design-system/assets/styles/composed-components.css) — add the full `.tl-thread` rule block + the `:has()` provider stripes. Source: iter-4, iter-5, iter-8 in `proposed.html`.
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §16 — replace the current `.tl-turn` 5-col-grid examples with a rendered example showing the M3 card. Show all three provider variants (Claude / GPT / System).

**Live change.**
- [`components.css`](../../src/dual_research/ui/static/components.css) — replace the current `.tl-thread` rules (which are probably minimal — most styling lives in `.tl-card-head` today) with the full card chrome block. Add the `:has()` provider stripes.
- [`run-detail.jsx`](../../src/dual_research/ui/static/run-detail.jsx) — no change needed if `:has()` selector is acceptable. If you prefer a `data-provider` attribute (cleaner / older-browser safe), add it to the `<article>` opening tag in the turn-card render (~line 1202).

### 2.4.2 Card head — chip composition

Anchor: `<header class="tl-card-head">` (always 36 px tall after these changes).

The card head renders a **left cluster** (identity + activity) and a **right cluster** (categories + violations + status + chevron, all inside `.tl-card-head__right` which has `margin-left: auto`).

**Render order, left to right:**

#### 2.4.2.a Identity chip (FIRST, always present)

One of three:

**Claude turn card** — `.chip.tone-claude.no-dot`
- `chip-leading-icon` slot containing the Anthropic sunburst SVG in a `--p-sable` colored 12×12 square (`border-radius: 3px`, `color: var(--on-accent)`)
- `chip-label` slot reading "Claude"

**GPT turn card** — `.chip.tone-gpt.no-dot`
- Same anatomy but OpenAI hexagonal rosette SVG in a `--p-sage` square
- Label "GPT"

**System card** (brief, render errors, anything agentless) — `.chip.tone-neutral.no-dot` (NO `.mono` modifier)
- `chip-leading-icon` containing a Material "settings" SVG inside a `--p-idle` 12×12 square
- Label "System"
- See §2.5 for the System chip primitive spec.

**Background on all three:**
- Claude: `color-mix(in srgb, var(--p-sable) 30%, transparent)`
- GPT:    `color-mix(in srgb, var(--p-sage)  30%, transparent)`
- System: `color-mix(in srgb, var(--p-idle)  20%, transparent)`

**Text color:**
- Claude: `var(--md-on-primary-container)` in dark (light cream `#f3deca`); `#3b2810` (deep brown) in light. The light value is currently **missing** from live `tokens.css` — see drift fix 3.A.
- GPT:    `var(--md-on-secondary-container)` in dark (`#cfece6`); `#0a322d` (deep teal) in light. Same drift.
- System: `var(--md-on-surface)` in both themes.

#### 2.4.2.b Activity chip (SECOND, always present)

`.chip.tone-neutral.mono.no-dot` containing only a `chip-label` slot.

**Label vocabulary** (lowercase, no abbreviation):
- "brief" — for the P0 input card
- "preflight" — for P0 agent turns
- "plan" — for P1 research plans
- "turn N" — for P2 / P4 negotiation turns
- "draft" — when applicable

**Background:** `var(--md-surface-container-highest)` — one tier brighter than the card surface. Without this bump, the chip and the card share the same color and the chip becomes invisible. **This is a load-bearing change** — drop it and you lose the activity badge.

**Text color:** `var(--md-on-surface-variant)`. Font: `var(--md-font-data)`, 10.5 px.

#### 2.4.2.c Right cluster — categories + violations + status + chevron

Wrapped in `<div class="tl-card-head__right">` with `margin-left: auto`. Renders in this fixed order:

**Category counter chips** (only when `showCategoryChips === true` — turn cards + preflight, NOT brief / plan).

Per spec 0133 §5.9, the turn-card variant of the category chip is the **slim Δ-pair**:
- Bubble dropped
- Standing-total dropped
- Only `chip-add` (+N raised this round) and `chip-sub` (−N closed this round)
- Tone color carries category identity (info=Q, warn=D, err=I, idle=C)
- Q → D → I → C order, fixed

Render order: always Q D for P0/P2 (Issues + Comments don't surface there). All four (Q D I C) for P4.

When `raised + closed === 0`, add `dim` modifier (0.55 opacity) so the chip stays present and columns align across rounds.

`aria-label` carries the full meaning: `"Questions this round: 2 raised, 0 closed"`.

**Violation chips** (only when `cardViolations` non-empty). `tone-warn` chip with leading dot + label + expand-chevron. Click to expand inline.

**Status chip** (always present, never bare):
- Running: `.chip.tone-info` with leading dot + label "running"
- Agreed: `.chip.tone-ok` with leading check glyph + label "agreed"
- Terminal (no AGREED): `.chip.tone-ok.chip-icon-only` with check glyph only (no label)
- Queued: `.chip.tone-idle` with leading dot + label "queued"

**Chevron** (`<span class="tl-card-chev">`): 24×24 wrapper with a 12×12 chevron SVG inside. Opacity 0.25 at rest, 0.6 on hover, rotates 90° via `data-open="true"` when card is expanded.

**DS change.**
- [`SPEC.md`](../../design-system/SPEC.md) §4.4 (Timeline pane) — codify the card-head composition: `[identity] [activity] [right cluster: categories · violations · status · chevron]`. Add a forbidden-pattern list (e.g., "no bare status chip", "no public-ID chip in the card head").
- [`SPEC.md`](../../design-system/SPEC.md) §9 (Badge governance) — already says provider FIRST, activity SECOND, categories THIRD, status RIGHT-ALIGNED. No change needed; this iteration confirms it.
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §16 — replace the `.tl-turn` examples (which show `avatar + name + lbl + deltas + round`) with the actual `.tl-card-head` structure including the brand-mark SVGs and the slim Δ-pair category chips.

**Live change.**
- [`run-detail.jsx`](../../src/dual_research/ui/static/run-detail.jsx) — the turn-card render at ~line 1211 is already structurally correct. The changes are mostly CSS-side (chip backgrounds, activity chip surface tier).
- [`components.css`](../../src/dual_research/ui/static/components.css) — update:
  - `.tl-card-head .chip.tone-claude { background: color-mix(in srgb, var(--p-sable) 30%, transparent); }`
  - `.tl-card-head .chip.tone-gpt    { background: color-mix(in srgb, var(--p-sage)  30%, transparent); }`
  - `.tl-card-head .chip.tone-neutral:not(.mono) { background: color-mix(in srgb, var(--p-idle) 20%, transparent); color: var(--md-on-surface); }` (System)
  - `.tl-card-head .chip.tone-neutral.mono { background: var(--md-surface-container-highest); }` (activity)

---

## 2.5 System chip — NEW primitive

The System chip is the leading identity chip on cards that have no agent (brief, render errors, future system-emitted entries). It mirrors the Claude / GPT identity chip structure exactly.

**Markup:**
```html
<span class="chip tone-neutral no-dot">
  <span class="chip-leading-icon" aria-hidden="true">
    <span style="display: inline-flex; align-items: center; justify-content: center;
                 width: 12px; height: 12px; border-radius: 3px;
                 background: var(--p-idle); color: #ffffff;
                 flex-shrink: 0; line-height: 1;">
      <svg viewBox="0 0 24 24" width="8" height="8" aria-hidden="true">
        <!-- Material Icons "settings" gear path -->
        <path d="M19.14,12.94c…[full settings-gear path]…" fill="currentColor"></path>
      </svg>
    </span>
  </span>
  <span class="chip-label">System</span>
</span>
```

(Full SVG path in [`proposed.html`](./proposed.html) iter-3 stylesheet.)

**Styling:**
- `background: color-mix(in srgb, var(--p-idle) 20%, transparent)`
- `color: var(--md-on-surface)` (white in dark, near-black in light)
- Inherits all `.chip` primitive geometry (22 px height, pill radius, `font: 500 11px/1 var(--md-font-plain)`, letter-spacing 0.04em)

**DS change.**
- [`SPEC.md`](../../design-system/SPEC.md) §3 Primitives — add a "System chip" row alongside the existing identity chips. Document the icon (Material settings gear), the `--p-idle` color square, the label vocabulary ("System"), and the 20% color-mix background.
- [`SPEC.md`](../../design-system/SPEC.md) §9.2 — extend the canonical-kinds table with a "System" identity kind alongside Claude and GPT.
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §9 — render an example.

**Live change.**
- [`shared.jsx`](../../src/dual_research/ui/static/shared.jsx) — add a `SystemChip` component (or extend the existing identity-chip helper to accept `agent="system"` and emit the settings-gear glyph + idle-colored square).
- [`run-detail.jsx`](../../src/dual_research/ui/static/run-detail.jsx) — the existing render at line ~1223 already has the `!agent && item.kind === 'input'` branch for the brief; replace its `<Chip tone="neutral" leadingIcon={<Icon.FileDocument size={12} />} label="brief" />` with two chips: `<SystemChip />` + `<Chip tone="neutral" mono label="brief" />`. Same pattern for any other agentless item kinds (errors, future system messages).

---

## 2.6 Error chip — NEW primitive

When a turn fails to render (today: stringified `turn [object object]`), the card should render as `[System chip] + [Error chip]` with a human-readable label.

**Markup:**
```html
<span class="chip tone-err no-dot" aria-label="Could not render this turn">
  <span class="chip-leading-icon" aria-hidden="true">
    <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"
         style="width:12px; height:12px; color: currentcolor;">
      <!-- Material Icons "error" filled-circle path -->
      <path d="M12,2C6.48,2 2,6.48 2,12s4.48,10 10,10s10-4.48 10-10S17.52,2 12,2z M13,17h-2v-2h2V17z M13,13h-2V7h2V13z" fill="currentColor"></path>
    </svg>
  </span>
  <span class="chip-label">Could not render this turn</span>
</span>
```

**Styling:** inherits `.chip.tone-err` (err-color background and text). Label varies per error condition — always **human-readable**, never a raw error code.

**Vocabulary suggestions:**
- "Could not render this turn"
- "Turn data missing"
- "Agent timed out"
- "Empty turn received"

Each error label gets its own canonical phrase. If the system has an error code, the label is the human translation of that code, not the code itself.

**DS change.**
- [`SPEC.md`](../../design-system/SPEC.md) §3 — add an Error chip primitive.
- [`SPEC.md`](../../design-system/SPEC.md) §9.5 vocabulary table — add a new row for "Error" with the allowed human-readable phrases.

**Live change.**
- [`shared.jsx`](../../src/dual_research/ui/static/shared.jsx) — add an `ErrorChip` helper or extend the existing Chip primitive to accept an error variant.
- [`run-detail.jsx`](../../src/dual_research/ui/static/run-detail.jsx) — find the JS template that produces `turn ${turnNumber}` and add a defensive check: if the value is an object or undefined, render `[SystemChip] [ErrorChip label="Could not render this turn"]` instead of stringifying. **The underlying `[object object]` bug should also be fixed at the data layer** — see drift fix 3.F.

---

## 2.7 Turn card — expanded state

Anchor: `<article class="qthread tl-thread is-{status} is-open-expanded">` (or `.tl-turn--open` in the DS reference).

### 2.7.1 Body

**Now.** `.tl-thread__body` directly below the card head, with `padding: 12px 14px 14px`, italic serif (`var(--md-font-brand)`), `color: var(--md-on-surface-variant)`, dashed top divider.

**After.** Unchanged. The body is M3-correct.

### 2.7.2 Actions row

**Now.** `.tl-thread__actions` below the body with:
- `Open full view` button (`.md-btn--tonal .md-btn--sm`)
- A spacer
- Token + cost chips (`.md-chip .md-chip--sm`)

The cost chip currently shows 4-decimal precision (e.g. `$0.0312`).

**After.**
- Same layout.
- **Cost chip rounds to 2 decimals**: `$0.03`, `$13.51`, `$2.40` (always with the trailing zero).
- For cost values that round to zero (e.g. `$0.0034`), display `<$0.01` rather than `$0.00`.

This applies to the **timeline expanded-card action chips only**. The run-detail footer aggregate ([SPEC.md](../../design-system/SPEC.md) §4.3) keeps its higher precision as the audit number.

**DS change.**
- [`SPEC.md`](../../design-system/SPEC.md) §4.4 — add a sentence: *"Cost chips in the expanded turn-card actions row use 2-decimal precision (`fmtCost2`). Values under 1 cent render as `<$0.01`. The run-detail footer aggregate keeps its 4-decimal audit precision."*
- [`Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §16 — update the expanded-turn example's cost chip from `$0.0566` to `$0.06` (or similar).

**Live change.**
- [`run-detail.jsx`](../../src/dual_research/ui/static/run-detail.jsx) — find the cost-rendering call in the expanded-card actions block (search for `tl-thread__actions` or the existing `fmtCost` helper). Either:
  - Introduce a `fmtCost2(value)` helper that returns `<$0.01` for values under 0.01 and `$0.XX` otherwise.
  - Or pass a precision argument to the existing helper.

---

## 2.8 Workshop wrapper (not for production)

The `mockup.html` 3-tab switcher, the side-by-side dark/light iframes, the iter-N banners — **none of this ships to production**. It's a workshop artifact and stays in `prototypes/timeline-iteration/`.

If you want a similar side-by-side capability in the design-system showcase later, that's a separate decision (and would target `Design System v2.html`'s existing theme toggle, not a new iframe split).

---

# 3. Drift fixes uncovered along the way

These aren't part of the visual proposal — they're bugs / inconsistencies that surfaced while iterating, and which need fixing for the proposal to land cleanly.

### 3.A Light-mode on-container tokens missing from live `tokens.css`

**Symptom.** In light mode, Claude / GPT chip text renders as washed-out sable / sage (computed color: `rgb(212, 165, 116)` for Claude) instead of the dark brown / teal the design system mandates.

**Cause.** [`src/dual_research/ui/static/tokens.css`](../../src/dual_research/ui/static/tokens.css) does not override `--md-on-primary-container` / `--md-on-secondary-container` in its `body.light` block. They fall through to the dark-mode values (`#f3deca` light cream / `#cfece6` light mint), which are designed to be light text on a dark surface — unreadable on cream.

**Reference values** (from [`design-system/assets/styles/tokens-and-primitives.css`](../../design-system/assets/styles/tokens-and-primitives.css), the canonical token source):
```css
body.light {
  --md-on-primary-container:   #3b2810;
  --md-on-secondary-container: #0a322d;
}
```

**Fix.** Add these two overrides to live `tokens.css` `body.light` block. Affects every Claude / GPT chip everywhere — not just the timeline. Verify other surfaces look correct in light mode after this lands.

### 3.B Identity-chip background too subtle by default

**Symptom.** The Claude / GPT chips on timeline cards are barely visible against the card surface in both themes.

**Cause.** The `.chip.tone-claude` / `.tone-gpt` rules use `var(--md-primary-container)` / `var(--md-secondary-container)`, which is 18%-tinted in dark and 26%-tinted in light. Against a `surface-container-high` card surface this reads as essentially no chip background.

**Fix.** Scoped override in `components.css` for `.tl-card-head .chip.tone-claude` / `.tone-gpt` → `color-mix(in srgb, var(--p-X) 30%, transparent)`. **Do not** touch the token; other surfaces (critique cards, etc.) may need to keep the 18% / 26% values.

### 3.C Activity chip = card surface (invisible after iter 5)

**Symptom.** After bumping card surface to `surface-container-high` (iter 5), the activity chip (`.chip.tone-neutral.mono`) — which uses `surface-container-high` as its bg — becomes invisible.

**Cause.** Two surfaces at the same tier with the same fill.

**Fix.** Scoped override: `.tl-card-head .chip.tone-neutral.mono { background: var(--md-surface-container-highest); }`. One tier brighter than the card.

### 3.D Phase header pcode is redundant with the marker

**Symptom.** After iter 1 promoted the marker label to "Phase 0", the post-chevron `.tl-phase__pcode` "PHASE 0" duplicates the information.

**Cause.** Pre-iter-1 the marker said `P0` (short) and the pcode said `PHASE 0` (full). The marker was a compact identifier; the pcode was the full label. Iter 1 made the marker carry the full label, leaving the pcode as redundant.

**Fix.** Delete `.tl-phase__pcode` JSX render + CSS rule. (See §2.1.2.)

### 3.E Cost precision drift

**Symptom.** Timeline expanded-card action chips show `$0.0312` (4 decimals). The design system §4.3 says consumption-row cost displays use 1-decimal precision (`$0.2`). The footer aggregate keeps 4 decimals.

**Cause.** The current `fmtCost` helper used for the action chips doesn't apply the consumption-row precision rule, because the action chips weren't part of spec 0146.

**Fix.** Either reuse `fmtCost1` (1 decimal — `$0.0`) or introduce `fmtCost2` (2 decimals — `$0.03`). 2 decimals reads cleaner for sub-dollar values and matches the natural "cents" rounding the user expects. **Decision needed:** confirm the precision before shipping.

### 3.F `turn [object object]` rendering bug

**Symptom.** A turn card in P4 Cross-review renders the activity chip as `turn [object object]`.

**Cause.** Somewhere in `run-detail.jsx`, a template like ``turn ${turnNumber}`` receives an object (probably the whole `Turn` record, not its index) and JS stringifies it.

**Fix.**
- (Behavioral) Find the offending template and use the correct field (likely `turn.index` or `turn.round`).
- (Defensive) When the activity label can't be derived, render `[SystemChip] [ErrorChip]` instead — see §2.6.

The defensive UI is a backstop; the underlying data-layer bug should still be fixed.

### 3.G `Design System v2.html` §16 doesn't reflect the live timeline at all

**Symptom.** The DS §16 anatomy renders a 4-col phase header (`chev · pcode · name · meta`) with no marker and no chips. The live impl has 6 columns including marker and a chip cluster. They are completely out of sync.

**Cause.** §16 predates the spec-0099 marker addition, the spec-0119 phase-chip cluster, and various other timeline-pane additions. The DS reference HTML was never updated.

**Fix.** Re-render §16 from scratch with the locked anatomy from this notes file. Include:
- The 6-col (or 5-col after pcode deletion) phase header with marker + chip cluster
- The provider-tinted header agent strip with the brand-mark SVG
- The M3 turn card with provider stripe, brighter surface, 16dp radius
- The expanded-card body + actions row with 2-decimal cost
- A live-state example showing the elev-2 lift + sweep animation note

---

# 4. Implementation order (suggested)

Independent change groups (each can ship as its own spec):

| Group | Changes | Depends on |
|---|---|---|
| **A — Token drift** | 3.A (light-mode on-container) | None |
| **B — Phase header simplification** | 2.1.1 (marker label) + 2.1.2 (delete pcode) | None |
| **C — Pane gutter** | 2.3 | None |
| **D — Turn card chrome** | 2.4.1 (frame + surface + outline + radius + provider stripe) | C lands cleaner first |
| **E — Chip backgrounds** | 2.4.2.a (identity chips at 30% / 20%) + 2.4.2.b (activity chip at -highest) | A, D |
| **F — System + Error primitives** | 2.5 (System chip) + 2.6 (Error chip) + 3.F (data-layer bug) | None — but lands cleanest after E |
| **G — Phase-chip bubble dim** | 2.1.4 | None |
| **H — Agent-strip polish** | 2.2.1 (tint) + 2.2.3 (dot pulse + phrase) + 2.2.4 (elev-2) | None |
| **I — Cost precision** | 2.7.2 + 3.E | None |
| **J — DS HTML §16 catch-up** | 3.G | All of A–I lands first |

A, B, C, G, H, I can ship in parallel — they don't conflict.
D and E are tightly coupled and should ship together.
F can ship anytime after the bug fix is decided.
J is best last so the DS reference is the locked target snapshot.

---

# 5. Reference — proposed.html stylesheet blocks (in source order)

Each block is wrapped in its own `<style id="iter-N-…">` tag inside `proposed.html`. Pull the rules verbatim when drafting the spec:

| Block ID | Lives at line ~ | Covers |
|---|---|---|
| `iter-9-cat-bubble-softer` | top of `<head>` | §2.1.4 phase-chip bubble dim |
| `iter-12-live-strip-elev` | (top) | §2.2.4 elev-2 on live strip |
| `iter-11-live-dot-pulse` | (top) | §2.2.3 activity-dot pulse keyframe |
| `iter-10-activity-chip-bump` | (top) | §2.4.2.b activity-chip surface bump |
| `iter-8-agent-tint-and-stripes` | (top) | §2.2.1 strip tint + §2.4.1 card provider stripe + radius |
| `iter-7-chip-polish` | (top) | §2.4.2.a System tone-down + light Claude/GPT text |
| `iter-5-m3-card` | bottom | §2.3 gutter + §2.4.1 base card chrome + hover |

The iter-1/2/3 changes are inline modifications to the dumped DOM (not stylesheets) — they show up as:
- Iter 1: every `<span class="lbl">P{N}</span>` → `<span class="lbl">Phase {N}</span>`
- Iter 2: every `<span class="tl-phase__pcode">PHASE {N}</span>` removed
- Iter 3: brief card and `[object object]` card head replaced with [System chip] + [activity/error chip]
- Iter 4 inline: live HTML annotation banner (cosmetic)
- Iter 11 inline: Claude header strip `is-live` class added + activity phrase updated

---

# 6. Open questions to resolve before spec drafting

These weren't covered explicitly during iteration — flagging for when you draft specs:

1. **Reduced-motion fallback for the dot pulse.** The strip-level sweep already has a `prefers-reduced-motion: reduce` fallback in spec 0138. The new dot pulse (§2.2.3) needs the same — confirm acceptable degradation (static dot, no halo).
2. **Cost precision choice.** 1 decimal (matches consumption-row spec) or 2 decimal (more accurate for sub-dollar values). Decide.
3. **System chip beyond brief + render-error.** Future agentless entries (system notifications, orchestrator status messages) should reuse the System chip — but the catalog of "what counts as System" isn't enumerated. Worth a quick inventory before spec.
4. **Provider stripe via `:has()` vs `data-provider`.** `:has()` works in all modern browsers but adds runtime style-selector cost. A `data-provider="claude|gpt|system"` attribute on the `<article>` is slightly faster and works on older browsers. Pick one before spec.
5. **Activity-chip text in dark vs light.** Currently both themes use `var(--md-on-surface-variant)`. Confirm contrast against the new `surface-container-highest` background is AA in both themes.

---

*End of notes. Generated 2026-05-22 from the iteration session in `prototypes/timeline-iteration/`.*
