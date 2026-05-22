---
kind: dev
spec: "0168"
slug: critique-pane-item-card-refresh
title: Critique pane — item-card frame + head rebuild + expanded lifecycle view + source attribution + affordances
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
queue_position: 2
depends_on: ["0164", "0165"]
complexity: L
created: 2026-05-22
queued_at: "2026-05-22T17:08:41Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: critique-iteration-2026-05-22
promoted_from_draft: "004"
---

# Spec 0168 — Critique pane item-card refresh (frame + head + expanded lifecycle + sources + affordances)

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** 0164 (M3 card chrome on `.tl-thread` — same primitive applied to `.item-card` here), 0165 (light-mode token drift + identity-chip background opacities — same scope applies to `.item-card__head`)
> **Bump:** MINOR — visible refresh of every critique-card render on every run-detail page. No event-store / data-shape changes.

This is part 2 of the critique-pane refresh. Part 1 (spec 0167) handles the bar1 + bar2 chrome.

---

## 1. Context

The critique pane renders items grouped by status (`Open · new` / `Open · carried` / `Resolved` / `Drift`) inside each phase tab (P0 / P2 / P4 / Σ). Each item is one `.item-card`. After this spec lands, every card uses the M3 card-chrome language locked in for the timeline pane (spec 0164) plus a coordinated set of head-rebuild, expanded-view, source-attribution, and affordance changes.

Eight gaps in the current state:

1. **Item-card frame uses pre-M3 chrome.** Live `.item-card` renders with `var(--md-surface-container)` (same as pane), `1px solid var(--md-outline-hair)` border, no explicit radius (inherits default), and 12 px 14 px padding directly on the card. No provider stripe. No hover state. No transition. Cards visually blend with the pane.
2. **Card head is cluttered with low-value chips.** The live head carries an ID chip first, then various provider/round/kind/state chips, then a sources chip. The ID is cryptic (`Q7`-style) — useful for cross-references but visually noisy. The sources chip is redundant with the in-card `SOURCES (N)` overline.
3. **Round chip lacks state-transition context.** The round chip reads `round 1` — flat, no semantic. The state chip reads `resolved` — flat, no anchor to which round resolved. Reading "raised in r1, resolved in r3" requires hopping between elements.
4. **Evidence-needed banner takes a full row.** The `.item-card__evidence-needed` element renders as a body line ("Evidence needed — addresses must cite consulted sources."). Cards with evidence requirements are visually taller and break the 36 px row rhythm.
5. **Resolved state has no resolver identity.** When a card is resolved, the state chip shows "Resolved · R3" — but doesn't show *who* resolved it. Knowing Claude vs. GPT resolution is high-signal context that's currently buried in the transitions list.
6. **Expanded view layout doesn't tell the lifecycle story.** Live expanded layout shows body text, then a transitions list, then a footer, then sources — but the relationships between provider, round, action, and consequence aren't visually scaffolded. Each transition row reads as discrete metadata; the "raise → respond → resolve" arc isn't legible.
7. **Sources segment has no provenance.** When a card has sources, they're listed as plain rows with title / URL / search-query / fetched / excerpt. There's no per-source attribution showing which agent provided the source in which round. The "source requested" / "source provided" lifecycle isn't surfaced on the lifecycle row that owns it.
8. **No card-level collapse affordance.** Every `.item-card` renders fully always (body + timeline + footer + sources). Cards with sources occupy 200+ px of vertical space each. There's no per-card collapse to scan the phase view.

DS / SPEC drift to resolve in this spec:

- **3.C — DS / SPEC use `.crit-card` while live uses `.item-card` (BEM).** `design-system/assets/Design System v2.html` §13 renders cards as `<article class="crit-card">` with `.crit-card-head` / `.crit-card-body` / etc. Live uses `<article class="item-card">` with `.item-card__head` / `.item-card__body` / etc. (BEM). Promote the live BEM names into DS.
- **3.D — ID rendering inconsistency.** Live renders the item ID as the first chip in the head (per `design-system/SPEC.md` §4.8). DS renders it as a separate text line below the body. After this spec, neither renders — see §2.3 below for the rationale (the ID is dropped from the card display; URL hash + cross-ref UIs are unchanged).
- **3.I — No card-level collapse state.** `data-expanded="true|false"` is added per card; default state is collapsed, head only.
- **3.J — Sources always rendered with `aria-expanded="false"`.** `.source-row__body` is always present in the DOM and toggled via CSS based on `aria-expanded` on `.source-row__head`. Default per-card: first source row in each card is pre-expanded so the card demonstrates the expanded source view; remaining rows collapsed.

## 2. Proposed change

### 2.1 Item-card frame — M3 chrome catch-up

**Now.** `.item-card` ([`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css), search `\.item-card`) — `background: var(--md-surface-container)`, `border: 1px solid var(--md-outline-hair)`, `padding: 12px 14px`, `margin: 8px 0`, no radius, no hover, no transition. Cards run flush against the pane surface.

**After.** Adopt the M3 card chrome language from spec 0164 `.tl-thread`. The chrome is identical; only the selector scope is different. Card chrome uses `[data-raised-by]` attribute for the provider stripe instead of a `:has()` selector — the critique card has a dedicated DOM attribute for the raising agent already.

CSS (lands in both `design-system/assets/styles/composed-components.css` and `src/dual_research/ui/static/components.css`):

```css
/* Card frame */
.crit2 .item-card {
  background: var(--md-surface-container-high);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-shape-lg);     /* 16 dp */
  padding: 0;                             /* head owns its own padding */
  margin: 0;                              /* gap controlled by .crit-group__body */
  overflow: hidden;
  transition: background     var(--md-dur-short-3) var(--md-easing-standard),
              box-shadow     var(--md-dur-short-3) var(--md-easing-standard),
              border-color   var(--md-dur-short-3) var(--md-easing-standard);
}

/* 6 px gap between cards inside the status group */
.crit2 .crit-group__body { display: flex; flex-direction: column; gap: 6px; }

/* Provider left-stripe via data-raised-by attribute */
.crit2 .item-card[data-raised-by="claude"] { border-left: 2px solid var(--p-sable); }
.crit2 .item-card[data-raised-by="gpt"]    { border-left: 2px solid var(--p-sage); }
.crit2 .item-card[data-raised-by="system"] { border-left: 2px solid var(--p-idle); }

/* Hover (only when collapsed — expanded state has its own elevation) */
.crit2 .item-card[data-expanded="false"]:hover {
  background: var(--md-surface-container-highest);
  border-color: var(--md-outline);
  box-shadow: var(--md-elev-1);
}

/* Card head — 36 px tall to match the timeline turn card */
.crit2 .item-card__head {
  padding: 6px 12px;
  cursor: pointer;
  transition: background var(--md-dur-short-3) var(--md-easing-standard);
}
.crit2 .item-card__head:hover {
  background: color-mix(in srgb, var(--md-on-surface) 4%, transparent);
}
.crit2 .item-card__head:active {
  background: color-mix(in srgb, var(--md-on-surface) 8%, transparent);
}
```

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — emit `data-raised-by="{claude|gpt|system}"` on the `<article class="item-card">` element. Add `data-expanded` (default `"false"`) and a click handler on `.item-card__head` that toggles it.
- `src/dual_research/ui/static/components.css` — replace existing `.item-card` rules with the chrome block above.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §4.7 (CritiqueCard / ItemCard primitive — rename if needed per drift 3.C below).
- `design-system/assets/Design System v2.html` §13 — re-render the card examples with the new chrome.

### 2.2 BEM rename — DS catches up with live (drift 3.C)

**Now.** `design-system/SPEC.md` §4.7 and `design-system/assets/Design System v2.html` §13 document the card as `.crit-card` with `.crit-card-head` / `.crit-card-body` / `.crit-card-id` / `.crit-card-meta`. Live uses BEM: `.item-card` with `.item-card__head` / `.item-card__body` / `.item-card__timeline` / `.item-card__lifecycle-footer` / `.item-card__sources`. DS contradicts live.

**After.** DS adopts the live BEM names. `.crit-card` → `.item-card`. All sub-element selectors switch to BEM (`__head`, `__body`, `__lifecycle`, `__sources`, etc.).

**Files to change.**
- `design-system/SPEC.md` §4.7 — rename `.crit-card` to `.item-card`; rewrite sub-element class names in BEM.
- `design-system/assets/Design System v2.html` §13 — replace `<article class="crit-card">` markup with `<article class="item-card">` BEM markup. Apply the new chrome from §2.1.
- `design-system/assets/styles/composed-components.css` — wherever `.crit-card` selectors exist, switch to `.item-card`. If there's an alias rule (`/* @deprecated */` `.crit-card { /* same as .item-card */ }`), drop it — DS is now canonical.

### 2.3 Card head rebuild — `[provider] [round] [kind] [evidence?] [state]`

**Now.** Card head is a flex row of chips assembled in JSX. Order (live): `[ID chip] [provider chip] [round chip] [kind chip] [other meta chips] [state chip]`. The ID chip is the first chip; sources chip appears somewhere in the middle.

**After.** The card head is rebuilt to the canonical composition:

- **Left cluster** (in fixed left-to-right order):
  1. **Provider chip** — same primitive as the timeline `[Claude]` / `[GPT]` / `[System]` identity chip (introduced by spec 0166 §2.1). 12×12 brand-mark square + label. `data-chip-role="provider"`.
  2. **Round chip** — `.chip.tone-neutral.mono` reading `Raised · R1` (where R1 = round number when raised). The leading word ("Raised") is capitalised via CSS `text-transform: capitalize` on `.chip-label`; the `R{N}` suffix is uppercase as-is. A subtle middle-dot separator (`.chip-sep` span with `opacity: 0.4`, `margin: 0 4px`) divides the two tokens. `data-chip-role="round"`.
  3. **Kind chip** — `.chip` with `data-chip-role="kind"`. Tone per kind: Q=info / D=warn / I=err / C=idle. Carries a `.cat-bubble` (14 px filled circle, 70 % alpha per spec 0165 §2.4, knockout-white letter) + `.chip-label` ("Questions" / "Disagreements" / "Issues" / "Comments").
  4. **Evidence-needed chip (when applicable)** — `.chip.tone-info.chip-icon-only.no-dot.evidence-chip` carrying a Material Icons `link` glyph at 12×12. Width 28 px (icon-only). The full sentence (`"Evidence needed — addresses must cite consulted sources."`) is the native `title` attribute (hover tooltip) and the `aria-label`. The original `.item-card__evidence-needed` body line is `display: none` so the 36 px head row never breaks. `data-chip-role="evidence"`. See §2.4 below for the full rule.

- **Right cluster** (right-aligned via `.item-card__head__right { margin-left: auto }`):
  5. **State chip** — see §2.5 for the resolver-icon variant and §2.3.1 for the basic format.

**ID chip + sources chip — dropped (drift 3.D).** The ID chip is removed from the card head. The sources chip (which previously announced the count and jumped to the segment) is also dropped — the in-card `SOURCES (N)` overline (§2.7) carries the count instead.

The ID itself is preserved in the URL hash (anchor IDs are unchanged), in the DOM `id` attribute on the `<article>` element, in cross-reference UIs that may surface elsewhere — only the visible head chip is dropped. The cards are identified visually by their position in the phase view + their state + their content.

**`.chip-sep` CSS** (used for the Raised · R1 separator and elsewhere):

```css
.crit2 .item-card__head .chip .chip-sep {
  opacity: 0.4;
  margin: 0 4px;
}

.crit2 .item-card__head [data-chip-role="round"] .chip-label,
.crit2 .item-card__head [data-chip-role="state"] .chip-label {
  text-transform: capitalize;
}
```

#### 2.3.1 State chip — round + resolver

**Now.** State chip reads a single word (`resolved` / `capped` / `acknowledged` / `withdrawn` / `addressed` / `open` / `drift`). No round annotation. No resolver identity.

**After.** State chip extended to `<state> · [resolver icon] · R<N>`. The resolver is parsed from the last `.item-card__transition-meta`'s `by X` suffix (Claude / GPT / Orchestrator / System). The 12×12 brand-mark square is the same primitive used by the provider chip. When the resolver is the Orchestrator or System (i.e., the card was capped or auto-resolved by infrastructure, not by an agent), the resolver icon is skipped and the chip reads `Capped · R<N>` or `Acknowledged · R<N>` plainly.

The terminal round is parsed from the `.item-card__lifecycle-footer` text (`"✓ resolved at round 2 · 2 turns to converge"` — the round number after "round"). Fallback to the last `.item-card__transition` meta if the footer is absent.

State vocabulary covered (per `design-system/SPEC.md` §9.5): Raised, Resolved, Capped, Acknowledged, Withdrawn, Addressed, Open, Drift. All vocabulary capitalised via the same `text-transform: capitalize` rule. The `R<N>` suffix uppercase.

Resolver icon is wrapped in a `.chip-sep` middle-dot pattern: `[state] · [icon] · R<N>`.

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — restructure the card-head render to emit chips in the canonical order with `data-chip-role` attributes. Parse the round + resolver from the existing `.item-card__transition-meta` / `.item-card__lifecycle-footer` markup.
- `src/dual_research/ui/static/components.css` — add `.chip-sep` rule + the `text-transform: capitalize` rules.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §4.7 — codify the card-head composition. Note the explicit forbidden patterns: "no bare state chip", "no ID chip in the card head".
- `design-system/SPEC.md` §4.8 — update the ID-display rule to scope to URL hash / anchor / cross-reference contexts only; explicitly note that the ID does NOT render as an in-card head chip.

### 2.4 Evidence-needed chip — icon with hover tooltip

**Now.** `.item-card__evidence-needed` element renders a body line `"Evidence needed — addresses must cite consulted sources."` inside the card body. The element pushes the card body height by ~24 px on every card that has evidence requirements.

**After.** A 28 px `.chip.tone-info.chip-icon-only.no-dot.evidence-chip` is injected into the card head between the kind chip and the right cluster. Markup:

```html
<span class="chip tone-info chip-icon-only no-dot evidence-chip"
      data-chip-role="evidence"
      title="Evidence needed — addresses must cite consulted sources."
      aria-label="Evidence needed — addresses must cite consulted sources.">
  <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
    <!-- Material Icons "link" path -->
    <path d="M3.9,12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76,0-5,2.24-5,5s2.24,5 5,5h4v-1.9H7C5.29,15.1 3.9,13.71 3.9,12z M8,13h8v-2H8V13z M17,7h-4v1.9h4c1.71,0 3.1,1.39 3.1,3.1s-1.39,3.1-3.1,3.1h-4V17h4c2.76,0 5-2.24 5-5S19.76,7 17,7z"
          fill="currentColor" />
  </svg>
</span>
```

The original body line is hidden:

```css
.crit2 .item-card__evidence-needed { display: none; }
```

The chip's native `title` attribute provides the hover tooltip (no custom JS — browser-native behaviour). `aria-label` provides the same phrase for screen readers.

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — when `item.evidenceNeeded === true`, inject the evidence chip into the head after the kind chip.
- `src/dual_research/ui/static/components.css` — `.evidence-chip` (28 px width override + the body-line hide rule).
- `design-system/assets/styles/composed-components.css` — same.

### 2.5 Resolver icon inside state chip

(Covered by §2.3.1 above — the state chip composition.)

### 2.6 Card head — overall CSS

```css
.crit2 .item-card__head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  min-height: 0;  /* explicitly no 32 px min — chip heights set the row */
}
.crit2 .item-card__head__right {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
```

Collapsed card height should be 36 px (matches timeline `.tl-thread` head height after spec 0164). Achieved with 6 px top/bottom head padding + chip height of 22 px (`.chip` primitive's intrinsic height) + 1 px border + 1 px buffer.

### 2.7 Expanded view — `.item-card__lifecycle` layout

**Now.** Live expanded layout: `.item-card__head` + `.item-card__body` (the question / disagreement text) + `.item-card__timeline` (transitions list) + `.item-card__lifecycle-footer` (terminal annotation) + `.item-card__sources` (when present). Each region is a discrete vertical block; no visual scaffolding showing the lifecycle arc.

**After.** When the card is expanded (`data-expanded="true"`), the existing `.item-card__body` and `.item-card__timeline` are hidden (`display: none`) and a new `.item-card__lifecycle` block is injected after the head. The lifecycle block is the single source of truth for the card's narrative.

Markup structure:

```html
<section class="item-card__lifecycle">
  <div class="item-card__lifecycle-overline">LIFECYCLE</div>

  <div class="lc-row">
    <div class="lc-row-chips">
      [provider chip · round chip · verb chip · modifier chip?]
    </div>
    <blockquote class="lc-row-quote">
      <!-- The item body text — raised at this row -->
    </blockquote>
  </div>

  <div class="lc-row">
    <div class="lc-row-chips">
      [provider chip · round chip · verb chip · modifier chip?]
    </div>
    <blockquote class="lc-row-quote">
      <!-- The transition reason / response text -->
    </blockquote>
  </div>

  <!-- … one .lc-row per .item-card__transition entry, in chronological order … -->
</section>

<div class="item-card__lifecycle-footer">
  ✓ resolved at round 3 · 2 turns to converge
</div>

<!-- Sources segment, when present (see §2.8) -->
```

**Synthetic first row.** The first `.lc-row` is always the raising. Synthesized from the head's `data-raised-by` + round + the item body text:
- Provider chip = the raising agent
- Round chip = `R1` (or whatever round it was raised in)
- Verb chip = "raised" (info tone)
- Quote = the item body text (italic serif)

**Subsequent rows.** Parsed from `.item-card__transition` entries via a `parseTransition()` helper. Each transition has:
- `actor` — who took the action (Claude / GPT / Orchestrator / System)
- `round` — which round
- `verb` — `addressed` / `resolved` / `capped` / `acknowledged` / `withdrawn` / `ghosted` / `drift`
- `modifier` — optional, e.g. `via hard_cap` / `via ghost_cap`
- `reason` — the transition reason text (becomes the quote)

**Orchestrator / System rows.** When the actor is Orchestrator or System, the provider chip is skipped from the row. The row reads `[round chip] [verb] [modifier?]` and the quote describes the auto-action.

**Verb tone map**: raised=info / addressed=warn / resolved=ok / capped=err / acknowledged=warn / withdrawn=idle / ghosted=warn / drift=err.

**CSS** (both files):

```css
.crit2 .item-card__lifecycle {
  padding: 8px 16px 12px;
  background: var(--md-surface-container-low);
  border-top: 1px solid var(--md-outline-hair);
}
.crit2 .item-card__lifecycle-overline {
  font: var(--md-w-medium) 10px/1 var(--md-font-data);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--md-on-surface-faint);
  margin-bottom: 8px;
}
.crit2 .lc-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 0;
  border-bottom: 1px dashed var(--md-outline-hair);
}
.crit2 .lc-row:last-child { border-bottom: none; }
.crit2 .lc-row-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.crit2 .lc-row-quote {
  margin: 0;
  padding: 0 0 0 12px;
  font: 400 13px/1.45 var(--md-font-brand);
  font-style: italic;
  color: var(--md-on-surface-variant);
  border-left: 2px solid var(--md-outline-hair);
}

/* Hide the existing body + timeline when the lifecycle layout is active */
.crit2 .item-card[data-expanded="true"] > .item-card__body,
.crit2 .item-card[data-expanded="true"] > .item-card__timeline {
  display: none;
}

/* Expanded-state chrome — surface drop + elev-2 lift */
.crit2 .item-card[data-expanded="true"] {
  background: var(--md-surface-container-low);
  border-color: var(--md-outline-variant);
  box-shadow: var(--md-elev-2);
}
.crit2 .item-card[data-expanded="true"] > .item-card__head {
  background: var(--md-surface-container-high);
  border-bottom: 1px solid var(--md-outline-hair);
}

/* Lifecycle footer */
.crit2 .item-card__lifecycle-footer {
  padding: 6px 16px 10px;
  font: var(--md-w-medium) 11px/1.35 var(--md-font-data);
  color: var(--md-on-surface-variant);
}
```

The provider chip backgrounds inside `.lc-row-chips` match the head's 30 % / 30 % / 20 % color-mix opacities established in spec 0165 §2.2 (scope extends from `.item-card__head` to `.item-card__lifecycle .lc-row-chips`):

```css
.crit2 .item-card__lifecycle .lc-row-chips .chip.tone-claude {
  background: color-mix(in srgb, var(--p-sable) 30%, transparent);
}
.crit2 .item-card__lifecycle .lc-row-chips .chip.tone-gpt {
  background: color-mix(in srgb, var(--p-sage) 30%, transparent);
}
.crit2 .item-card__lifecycle .lc-row-chips .chip.tone-neutral:not(.mono) {
  background: color-mix(in srgb, var(--p-idle) 20%, transparent);
  color: var(--md-on-surface);
}
```

### 2.8 Sources segment — overline + collapsible rows (drift 3.J)

**Now.** When `item.sources.length > 0`, the `.item-card__sources` segment renders inline below the lifecycle footer. Each source row carries head + body, but in live the body is conditionally rendered (not just CSS-hidden). Default `aria-expanded="false"` on the row head.

**After.** Segment always renders the source row body in the DOM; `.source-row__body { display: none }` is applied via the sibling selector `.source-row__head[aria-expanded="false"] ~ .source-row__body` based on the head's aria-expanded state. Toggle on head click.

Segment structure:

```html
<section class="item-card__sources">
  <div class="item-card__sources-overline">SOURCES (3)</div>
  <div class="source-row" data-source-index="0">
    <div class="source-row__head" aria-expanded="true" role="button" tabindex="0">
      <span class="source-row__chev">›</span>
      <span class="source-row__title">{title — max-width 280 px ellipsis}</span>
      <span class="source-row__host">{host}</span>
      <span class="source-row__meta chip tone-neutral mono">
        <span class="chip-leading-icon" aria-hidden="true">{provider 12×12 square}</span>
        R{N}
      </span>
      <!-- optional unverified chip if applicable -->
    </div>
    <div class="source-row__body">
      <dl class="source-row__fields">
        <dt>URL</dt>          <dd>{url}</dd>
        <dt>SEARCH QUERY</dt>  <dd>{query}</dd>
        <dt>FETCHED</dt>       <dd>{timestamp}</dd>
        <dt>UNVERIFIED REASON</dt><dd>{when applicable}</dd>
      </dl>
      <blockquote class="source-row__excerpt">{italic-serif excerpt}</blockquote>
    </div>
  </div>
  <!-- … one .source-row per source … -->
</section>
```

CSS:

```css
.crit2 .item-card__sources {
  padding: 8px 16px 12px;
  border-top: 1px dashed var(--md-outline-hair);
}
.crit2 .item-card__sources-overline {
  font: var(--md-w-medium) 10px/1 var(--md-font-data);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--md-on-surface-variant);
  margin-bottom: 8px;
}
.crit2 .source-row { padding: 4px 0; }
.crit2 .source-row__head {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.crit2 .source-row__chev {
  font-size: 14px;
  line-height: 1;
  color: var(--md-on-surface-faint);
  transition: transform 120ms ease;
}
.crit2 .source-row__head[aria-expanded="true"] .source-row__chev { transform: rotate(90deg); }
.crit2 .source-row__title {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font: var(--md-w-medium) 12px/1.2 var(--md-font-plain);
  color: var(--md-on-surface);
}
.crit2 .source-row__host {
  font: var(--md-w-regular) 11px/1 var(--md-font-data);
  color: var(--md-on-surface-faint);
}
.crit2 .source-row__meta { margin-left: auto; }
.crit2 .source-row__head[aria-expanded="false"] ~ .source-row__body { display: none; }

.crit2 .source-row__body {
  padding: 8px 0 8px 22px;  /* indent past the chev gutter */
}
.crit2 .source-row__fields {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 4px 12px;
  margin: 0 0 8px;
}
.crit2 .source-row__fields dt {
  font: var(--md-w-medium) 10px/1.2 var(--md-font-data);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--md-on-surface-faint);
}
.crit2 .source-row__fields dd {
  margin: 0;
  font: var(--md-w-regular) 11.5px/1.4 var(--md-font-plain);
  color: var(--md-on-surface);
  overflow-wrap: break-word;
}
.crit2 .source-row__excerpt {
  margin: 0;
  padding: 8px 12px;
  background: color-mix(in srgb, var(--md-on-surface) 4%, transparent);
  border-radius: var(--md-shape-sm);
  font: 400 12.5px/1.45 var(--md-font-brand);
  font-style: italic;
  color: var(--md-on-surface-variant);
}
```

The `.source-row__meta` chip carries `[provider 12×12 square] R<N>` showing which agent provided the source in which round (extracted from the first Claude/GPT transition's actor + round). Tooltip on hover (`title` attribute) reads "Provided by GPT in round 2" (or equivalent).

### 2.9 Source attribution badges on lifecycle rows (iter 13)

**Now.** Lifecycle rows have no source-attribution chips. The cards-with-sources signal is buried.

**After.** When `item.evidenceNeeded === true`, the synthetic raised row gets an extra chip `[🔗 source requested]` (`.chip.tone-info.no-dot`, link icon, label "source requested"). When `item.sources.length > 0`, the first agent transition row (the first Claude or GPT row after raised) gets an extra chip `[🔗 source provided]` (`.chip.tone-ok.no-dot`, link icon, label "source provided"). These chips sit at the end of `.lc-row-chips`.

The per-source meta chip on each `.source-row__head` (covered in §2.8) is the third piece — shows which agent + round provided that specific source.

### 2.10 Affordances — collapse + pre-expand + hover (iters 14 + 15)

**Now.** No collapse affordance on cards. No auto-expand of any card. Source rows all collapsed by default.

**After.**

1. **Cards start collapsed.** Default `data-expanded="false"` on every `.item-card`. Click `.item-card__head` to toggle. The toggle is bidirectional: a click while expanded collapses, a click while collapsed expands. No keyboard binding required (future spec may add `Enter` / `Space` on the head's `role="button"` semantic).
2. **Phase-section groups start UNFOLDED by default.** Default `data-collapsed="false"` on every `.crit-group`. The prior live default may be different per status group (Open vs Resolved vs Drift); this spec normalises all groups to start unfolded so the user sees every card immediately upon opening a phase tab. Click `.crit-group__hd` to toggle.
3. **Phase-section header click affordance strengthened.** `.crit-group__hd` (the "Resolved 13" / "Open · new" / "Drift" group header) gets `cursor: pointer` + a hover/active background tint. The collapse toggle on `.crit-group` (already wired in live) becomes visibly clickable. CSS:

```css
.crit2 .crit-group {
  /* default state — explicit on the JSX render so the implementer doesn't
     rely on absence of attribute meaning unfolded; the CSS keys off the
     attribute to set chevron rotation */
}
.crit2 .crit-group__hd {
  cursor: pointer;
  transition: background var(--md-dur-short-3) var(--md-easing-standard);
}
.crit2 .crit-group__hd:hover {
  background: color-mix(in srgb, var(--md-on-surface) 4%, transparent);
}
.crit2 .crit-group__hd:active {
  background: color-mix(in srgb, var(--md-on-surface) 8%, transparent);
}

/* Chevron rotation — points DOWN when unfolded, RIGHT when collapsed.
   Uses `expand_more` Material Symbol as the base glyph (a downward V).
   - data-collapsed="false" (default): no transform → V points down
   - data-collapsed="true": rotate -90deg → V points left (chevron-left)
     If the design preference is chevron-right (more conventional for
     "click to expand"), use rotate(90deg) here instead. The implementer
     should match the timeline pane's existing `.tl-phase__chev` direction
     for consistency across panes. */
.crit2 .crit-group__chev {
  transition: transform var(--md-dur-short-3) var(--md-easing-standard);
}
.crit2 .crit-group[data-collapsed="true"] .crit-group__chev {
  transform: rotate(-90deg);
}
```

4. **Card-head chevron rotation.** The `.item-card__head::after` chevron (introduced in §2.1) rotates to signal state: points down when expanded (`data-expanded="true"`), points right when collapsed (`data-expanded="false"`). Uses CSS `transform: rotate()` keyed off `data-expanded`. Implementation:

```css
.crit2 .item-card__head::after {
  content: '›';
  margin-left: 0;
  transition: transform var(--md-dur-short-3) var(--md-easing-standard);
}
.crit2 .item-card[data-expanded="false"] .item-card__head::after {
  transform: rotate(0);     /* › points right — "click to expand" */
}
.crit2 .item-card[data-expanded="true"] .item-card__head::after {
  transform: rotate(90deg); /* › rotated 90° → points down — "click to collapse" */
}
```

5. **Pre-expand first source-row per card.** When a card with sources renders, the first source row's head is set to `aria-expanded="true"`. Subsequent rows stay collapsed (`aria-expanded="false"`). This means opening a card with 2+ sources shows the first source fully expanded alongside collapsed siblings — the user immediately sees both visualisations of a source row without clicking.
6. **Auto-expand first card with sources per phase.** When a phase tab is rendered, the first `.item-card` whose subtree contains a non-empty `.item-card__sources` segment is set to `data-expanded="true"` automatically. Other cards stay collapsed. This shows one fully demonstrated card per phase tab without requiring a click. If no card in the phase has sources, all cards stay collapsed (no fallback expansion).
7. **`.item-card__head` is clickable in both states.** Hover / active background tint applies regardless of `data-expanded` (covered in §2.1's `.item-card__head:hover` rule). The cursor is `pointer` always. Hover tint colour: 4% on-surface (`color-mix`) on hover, 8% on active (mousedown).

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — set `data-collapsed="false"` on every `.crit-group` render. Implement the auto-expand-first-with-sources logic per phase tab on render. Implement the pre-expand-first-source-row-per-card logic. Wire `data-expanded` toggle on `.item-card__head` click. Wire the existing `.crit-group` collapse toggle on `.crit-group__hd` click. Add the chevron rotation CSS keyed on `data-expanded`.
- `src/dual_research/ui/static/components.css` — add the chevron rotation rules + the data-collapsed chevron rotation rule (if not already present).
- `design-system/assets/styles/composed-components.css` — same.

## 3. UX / behaviour

After this spec lands:

- **Card visual structure (collapsed).** Each `.item-card` is a 36 px-tall row: provider chip (Claude / GPT / System), round chip (e.g. `Raised · R1`), kind chip (Q / D / I / C with letter bubble and label), optional evidence-needed icon chip, and on the right the state chip with resolver icon (e.g. `Resolved · [Claude icon] · R3`). 16 dp radius. 2 px provider stripe in sable / sage / idle on the left edge. 1 px outline-variant border. Cards sit 6 px apart vertically inside `.crit-group__body`.
- **Card visual structure (expanded).** Same head row at the top with a darker `surface-container-high` background and a hairline bottom border. Below: the LIFECYCLE overline + a chronologically-ordered series of `.lc-row` entries. Each row shows `[provider chip] [round chip] [verb chip] [modifier chip?]` followed by an italic-serif quote of the relevant text (item body for the raised row; transition reason for subsequent rows). Orchestrator / System transitions skip the provider chip. The terminal annotation (`✓ resolved at round 3 · 2 turns to converge`) sits below the lifecycle. Sources segment (when N > 0) follows with the `SOURCES (N)` overline + collapsible rows.
- **Source attribution.** On the raised row of any card with `evidenceNeeded`, an extra `[🔗 source requested]` chip. On the first agent transition row of any card with sources, `[🔗 source provided]` chip. Each source row's head carries a `[provider icon · R<N>]` meta chip showing the source's provenance.
- **Default state per phase.** Phase tabs open with the first card that has sources pre-expanded (one card per phase). Inside an expanded card, the first source row is pre-expanded; remaining source rows are collapsed.
- **Click affordances.** Hovering a `.item-card__head` or `.crit-group__hd` shows a subtle background tint signalling clickability. Active state (mousedown) shows a slightly stronger tint.
- **Identity tracking.** Cards no longer display their internal ID (the cryptic `Q7` / `D2`-style label). The ID is preserved in URL hash anchors, in DOM `id` attributes on `<article>` elements, and in cross-reference UIs elsewhere. Card identity in the pane view comes from position + state + content.

Pre-existing runs render identically except for the chrome changes — no data shape changes. The new lifecycle parser is defensive: if a card has no transitions, the lifecycle section shows only the synthetic raised row.

## 4. Data / schema deltas

None. The lifecycle layout (§2.7) is a re-render of existing `.item-card__transition` markup; no new data fields are introduced. The source-attribution chips (§2.9) are derived from existing `item.sources` and `item.evidenceNeeded` data. The auto-expand logic (§2.10) is a client-side derivation; no persisted "expanded" state.

## 5. Out of scope

- **Bar 1 / bar 2 chrome (segmented controls + drift chip + DS phase-tab + kind-cluster order)** — covered by spec 0167 (this spec is the part 2; 0167 ships independently).
- **M3 card-chrome primitive on `.tl-thread`** — delivered by spec 0164.
- **Identity-chip backgrounds + light-mode token drift + activity-chip surface bump** — delivered by spec 0165. This spec reuses those rules scoped to `.item-card__head` and `.item-card__lifecycle .lc-row-chips`.
- **System + Error chip primitives** — delivered by spec 0166. This spec consumes the SystemChip from `shared.jsx`.
- **Σ Summary tab body (bar-1 totals reset bug, inline-style cleanup, DS divergence)** — drift 3.F / 3.G / 3.H in the critique iteration notes. Separate concern; out of scope.
- **Resolved group title — split into per-state groups** (drift 3.E). Separate concern; out of scope.
- **New event-store fields or schema migrations.** Lifecycle parsing reads existing markup; no backend changes.
- **Existing critique-pane keyboard navigation.** The new click affordances are pointer-only; keyboard tabbing through cards is unchanged. Future spec may add keyboard collapse toggles.

## 6. Design-system gate

Cited DS sections being updated:

- `design-system/SPEC.md` §4.7 — ItemCard primitive (renamed from `.crit-card`). Codify the card-head composition, the lifecycle expanded view, the source-row primitive, the collapse affordance.
- `design-system/SPEC.md` §4.8 — update ID-rendering rule to scope to URL hash / cross-ref contexts only; the in-card head ID chip is dropped.
- `design-system/SPEC.md` §9.5 — vocabulary table extended with lifecycle verbs (raised, addressed, resolved, capped, acknowledged, withdrawn, ghosted, drift) + the `via hard_cap` / `via ghost_cap` modifiers.

Files that MUST land in the same commit:

- `design-system/SPEC.md`
- `design-system/assets/styles/composed-components.css`
- `design-system/assets/Design System v2.html` (§13 re-rendered with .item-card BEM, new chrome, expanded lifecycle, sources segment, collapse affordances)
- `src/dual_research/ui/static/components.css`
- `src/dual_research/ui/static/run-detail.jsx`
- `src/dual_research/ui/static/shared.jsx` (helpers for lifecycle row, source row, evidence chip if extracted)
- `CHANGELOG.md`
- `pyproject.toml`
- `src/dual_research/__init__.py`

## 7. Test plan

- [ ] **Frame computed styles (collapsed, dark).** `.crit2 .item-card` background resolves to `--md-surface-container-high`, border-color to `--md-outline-variant`, border-radius to `16px`. `[data-raised-by="claude"]` has computed `border-left: 2px solid var(--p-sable)` resolved. Same for sage GPT and idle System.
- [ ] **Frame computed styles (light).** Same rules resolve to light-mode token values. No washed-out chip text (depends on spec 0165 token fix).
- [ ] **Hover lift (collapsed only).** Hover a collapsed `.item-card`. Computed `background` resolves to `--md-surface-container-highest`, `border-color` to `--md-outline`, `box-shadow` to `--md-elev-1`. Hover an expanded card — these properties do NOT change (expanded chrome is independent).
- [ ] **Card head composition (default).** Render a healthy run. For a Claude-raised question card with sources and `evidenceNeeded`:
  - `.item-card__head > [data-chip-role="provider"]` exists, has Claude SVG inside `.chip-leading-icon`, label "Claude".
  - `.item-card__head > [data-chip-role="round"]` exists, label text matches `/^Raised\s.+\sR\d+$/` (with `.chip-sep`).
  - `.item-card__head > [data-chip-role="kind"]` exists with `.cat-bubble` text "Q" and label "Questions".
  - `.item-card__head > [data-chip-role="evidence"]` exists with the link SVG.
  - `.item-card__head__right > [data-chip-role="state"]` exists, contains state label + resolver icon + R<N>.
  - `.item-card__head` does NOT contain an ID chip.
  - `.item-card__head` does NOT contain a sources count chip.
- [ ] **State chip — resolver identity.** For a Claude-resolved card, the state chip's middle slot has a sable-colored 12×12 square with the Anthropic sunburst SVG. For a GPT-resolved card, sage square with OpenAI rosette. For an Orchestrator-capped card, NO middle slot — chip reads `Capped · R<N>` plainly.
- [ ] **Capitalisation.** Round chip `.chip-label` computed `text-transform: capitalize`. State chip `.chip-label` same. `R<N>` suffix is uppercase as-is.
- [ ] **Evidence-needed body line hidden.** `.item-card__evidence-needed` computed `display: none` everywhere. Cards with `evidenceNeeded === true` still render the evidence icon chip in the head.
- [ ] **Expanded lifecycle layout.** Click a collapsed card's head. `data-expanded="true"`. `.item-card__body` and `.item-card__timeline` have computed `display: none`. `.item-card__lifecycle` is present. The LIFECYCLE overline reads "LIFECYCLE" in uppercase data-font. First `.lc-row` has provider = raised-by, round = R1, verb chip "raised", and quote = item body text.
- [ ] **Lifecycle transition rows.** For a card with N transitions, total `.lc-row` count = N + 1 (synthetic raised + transitions). Each row contains the expected chips per the verb tone map (raised=info / addressed=warn / resolved=ok / capped=err / acknowledged=warn / withdrawn=idle / ghosted=warn / drift=err).
- [ ] **Orchestrator / System rows skip provider chip.** A capped-by-orchestrator transition row contains `[round R<N>] [capped] [via hard_cap?]` chips. No provider chip in `.lc-row-chips` for those rows.
- [ ] **Source attribution chips on lifecycle.** For a card with `evidenceNeeded`, the synthetic raised row contains an extra `[🔗 source requested]` chip with tone-info. For a card with sources, the first agent transition row contains `[🔗 source provided]` chip with tone-ok.
- [ ] **Sources segment.** For a card with N sources (N > 0), `.item-card__sources` is present, contains `.item-card__sources-overline` reading "SOURCES (N)" and N `.source-row` elements. The first source row has `aria-expanded="true"` on its head (pre-expanded); subsequent rows have `aria-expanded="false"`. Body markup is in the DOM for every row (toggled via CSS).
- [ ] **Source row meta chip.** Each `.source-row__head` contains a `.source-row__meta.chip.tone-neutral.mono` showing `[provider icon] R<N>`. The chip is right-aligned (`margin-left: auto`).
- [ ] **Source row body fields.** When expanded, `.source-row__fields` is a 130 px / 1fr grid of `<dt>` / `<dd>` pairs: URL, SEARCH QUERY, FETCHED, UNVERIFIED REASON (when applicable). `.source-row__excerpt` is the italic-serif quote in a tinted recess.
- [ ] **Auto-expand first card with sources per phase.** Open each phase tab. The first `.item-card` whose `.item-card__sources` segment is non-empty has `data-expanded="true"`. All other cards have `data-expanded="false"`.
- [ ] **Card head chevron rotation.** For a collapsed card, `getComputedStyle(card.querySelector('.item-card__head'), '::after').transform` resolves to `matrix(1, 0, 0, 1, 0, 0)` (no rotation) or equivalent. For an expanded card, it resolves to a 90° rotation matrix. Toggling the card flips the transform.
- [ ] **Phase-section group default unfolded.** On phase tab open, every `.crit-group` has `data-collapsed="false"`. Their `.crit-group__body` is visible (non-zero height).
- [ ] **Phase-section group toggle.** Click `.crit-group__hd`. `data-collapsed` flips to `"true"`. The `.crit-group__body` collapses (height 0, display none). Click again — flips back to `"false"`.
- [ ] **Phase-section chevron rotation.** When `data-collapsed="true"`, the `.crit-group__chev` element has computed `transform: rotate(-90deg)` (matches timeline pane convention). When `data-collapsed="false"`, no rotation.
- [ ] **Phase-section header click feedback.** Hover `.crit-group__hd`. Computed `background-color` resolves to a 4 % on-surface mix. Click — `background-color` momentarily resolves to 8 % during active state.
- [ ] **ID drop — URL anchor still works.** Navigate to `/runs/<id>#Q7`. The card with that ID still scrolls into view (the DOM `id` attribute on `<article>` is preserved).
- [ ] **DS reference catch-up.** Open `design-system/assets/Design System v2.html` §13. Markup uses `.item-card` BEM throughout. Rendered examples show the new chrome, the canonical head composition, the lifecycle expanded view, and the sources segment. No `.crit-card` selectors remain.
- [ ] **Old-run safety.** Render the earliest archived run. No console errors. Cards render with the new chrome. Cards without transitions show only the synthetic raised row in the expanded lifecycle.
- [ ] **Tests pass.** `uv run pytest tests/ -q` exits 0.

## 8. Implementation steps (suggested order)

1. **DS rename** (`.crit-card` → `.item-card`) in `design-system/SPEC.md` §4.7 + `design-system/assets/Design System v2.html` §13 + `design-system/assets/styles/composed-components.css`. Drop any `.crit-card` selectors.
2. **Add the new chrome rules** to `composed-components.css` and mirror to `src/dual_research/ui/static/components.css` (frame, hover, expanded, lifecycle, sources, affordances).
3. **Refactor `src/dual_research/ui/static/run-detail.jsx`** in stages:
   a. Add `data-raised-by` + `data-expanded` to the `<article class="item-card">` element. Wire the head-click toggle.
   b. Rebuild the head render — emit chips in the canonical order with `data-chip-role` attributes. Drop the ID chip + sources chip. Add the evidence chip + resolver icon.
   c. Replace the body + timeline render with the `.item-card__lifecycle` render. Synthesize the raised row from `data-raised-by` + item body. Parse `.item-card__transition` entries into `lc-row` instances.
   d. Refactor the sources segment to use `aria-expanded` toggling instead of conditional render. Inject the meta chip on each row head.
   e. Implement the auto-expand-first-with-sources logic per phase tab on render.
   f. Implement the pre-expand-first-source-row-per-card logic.
4. **Update `design-system/SPEC.md` §4.7 + §4.8 + §9.5** to codify the locked head composition + ID-rendering rule + verb vocabulary.
5. **Re-render `design-system/assets/Design System v2.html` §13** with the new examples.
6. **Run the test plan in full** (§7).
7. **CHANGELOG entry** under a new `## [X.Y.Z] — YYYY-MM-DD` section. Bump `pyproject.toml` + `src/dual_research/__init__.py` per MINOR.
