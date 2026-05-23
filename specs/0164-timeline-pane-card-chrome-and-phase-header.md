---
kind: dev
spec: "0164"
slug: timeline-pane-card-chrome-and-phase-header
title: Timeline pane — M3 card chrome + phase header simplification + narrow-view strip equalisation
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.25.0
status: deployed
depends_on: []
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T17:08:41Z"
started_at: "2026-05-22T17:15:00Z"
merged_at: "2026-05-22T19:55:00Z"
deployed_at: "2026-05-22T19:57:00Z"
pr: "https://github.com/Lexiz/dual-research/pull/187"
handover: "handoffs/2026-05-22-spec-0164-timeline-pane-card-chrome-and-phase-header.md"
failure_step: ""
source_session: timeline-iteration-2026-05-22
promoted_from_draft: "003"
---

# Spec 0164 — Timeline pane M3 card chrome + phase header simplification + narrow-view strip equalisation

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — visible visual refresh on every run-detail page. No schema or API change; class names preserved; existing data renders unchanged.

---

## 1. Context

The live timeline pane (`.rdvc__pane` left column on the run-detail page) has six visual gaps that this spec closes in one MINOR release:

1. The phase-header marker label reads as a cryptic `P0` / `P1` / `P2` / `P3` / `P4`. The marker box has room for the full word.
2. After the chevron, `<span class="tl-phase__pcode">PHASE 0</span>` renders the same phase number again in uppercase data-font. The marker (once it carries the full label) makes the pcode redundant.
3. Turn cards (`.tl-thread`) sit on the same surface tier as the pane background (`var(--md-surface-container)`), with only a 1 px `--md-outline-hair` separating card from pane. Cards visually blend with the pane.
4. The phase body (`.tl-phase__body`) has zero horizontal padding, so cards extend flush to the pane edges.
5. The Claude (`.as.is-a.in-header`) and GPT (`.as.is-b.in-header`) header strips share the same flat `var(--md-surface-container)` background. Brand identity reads only off the existing 2 px left-border + brand-mark icon.
6. At viewports ≤ 1799 px, `.as.in-header { min-width: 600px; flex: 0 0 auto }` causes the GPT strip inside `.tl__tabs` to overflow the pane edge by ~33 px (the tabs row has wider leading content than the head row). The trailing activity phrase clips with no ellipsis.

The design-system reference at `design-system/assets/Design System v2.html` §16 is itself out of sync with the live impl — its anatomy example shows a 4-column phase header (`chev · pcode · name · meta`) with no marker and no chip cluster, predating spec 0099 (phase marker) and spec 0119 (phase-header chip cluster). This spec brings live timeline + `design-system/SPEC.md` text contract + the rendered DS §16 reference into alignment.

## 2. Proposed change

### 2.1 Phase header — marker label "Phase {N}"

**Now.** The marker renders as a 10 px state-coloured dot + a `.lbl` span. At `src/dual_research/ui/static/run-detail.jsx:903` (the `.tl-phase__hd` JSX render), the markup is:

```html
<span class="tl-phase__marker is-done" aria-hidden="true">
  <span class="dot"></span>
  <span class="lbl">P0</span>
</span>
```

`.tl-phase__marker .lbl` already has `text-transform: none` (verified in computed styles), so the literal mixed-case "Phase 0" renders correctly. The marker box auto-expands to fit the longer label.

**After.** Same dot, same state classes (`.is-done` / `.is-current` / etc.). The `.lbl` span reads `Phase 0` / `Phase 1` / `Phase 2` / `Phase 3` / `Phase 4`:

```html
<span class="tl-phase__marker is-done" aria-hidden="true">
  <span class="dot"></span>
  <span class="lbl">Phase 0</span>
</span>
```

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx:903` — inside `<span className="tl-phase__marker is-{state}">`, the `<span className="lbl">` text content: `P${vp.pid}` → `Phase ${vp.pid}`.

No CSS change. No DS-CSS change.

### 2.2 Phase header — drop `.tl-phase__pcode`

**Now.** After the chevron, an element renders the phase number in uppercase data-font:

```html
<span class="tl-phase__pcode">PHASE 0</span>
```

This element lives at approximately `src/dual_research/ui/static/run-detail.jsx:914`, immediately after the marker + chevron group inside `.tl-phase__hd`. The CSS rule that styles it lives in `src/dual_research/ui/static/components.css` (uppercase, letter-spaced 10 px data font, faint colour).

`.tl-phase__hd` uses `grid-template-columns: auto 20px auto auto 1fr auto` — 6 columns: marker · chevron · pcode · name · meta · chips.

**After.** Delete the element + its CSS rule. The marker (now reading "Phase 0") is the canonical identity. The grid drops to 5 columns: `auto 20px auto 1fr auto` (marker · chevron · name · meta · chips).

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx:914` — remove the `<span className="tl-phase__pcode">PHASE {vp.pid}</span>` element.
- `src/dual_research/ui/static/components.css` — delete the `.tl-phase__pcode` rule. Update `.tl-phase__hd { grid-template-columns: auto 20px auto 1fr auto; }`.
- `design-system/assets/styles/composed-components.css` — same change (canonical mirror).
- `design-system/SPEC.md` §4.4 — remove any reference to `.tl-phase__pcode`. Document the marker as `dot + full-word label` (`Phase 0` / `Phase 1` / etc.).
- `design-system/assets/Design System v2.html` §16 — replace the current 4-column anatomy example with the new 5-column layout (marker · chevron · name · meta · chips).

### 2.3 Phase body — 16 px horizontal gutter

**Now.** Both `.tl-phase__hd` and `.tl-phase__body` use `padding: 4px 0 8px` / `padding: 10px 8px` (zero or near-zero horizontal). Turn cards extend flush to the pane left + right edges.

**After.** Both surfaces inset 16 px from the pane edges:

```css
.tl-phase__hd  { padding: 12px 16px; }
.tl-phase__body { padding: 8px 16px 12px; gap: 6px; }
```

The `gap: 6px` on `.tl-phase__body` controls inter-card spacing (replacing any per-card `margin`).

**Files to change.**
- `src/dual_research/ui/static/components.css` — update both selectors.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/assets/Design System v2.html` §16 — re-render anatomy showing the inset.
- `design-system/SPEC.md` §4.4 — codify the 16 px gutter as a pane-level rule.

### 2.4 Turn card frame — M3 chrome + provider stripe + 16 dp radius

**Now.** `.tl-thread` background is `var(--md-surface-container)` (same as pane). Border `1px solid var(--md-outline-hair)`. No explicit border-radius (inherits default). Padding 0 on the card (head owns its own padding). No hover state. No provider stripe. No transition.

Dark-mode resolved values: card background `#14171c`, hair border `#1c1f24` — both inside 4 percentage points of the pane background `#0f1115`. Cards visually blend with the pane.

**After.** Filled M3 card on `surface-container-high` (one tier brighter than the pane), `outline-variant` border (one tier more visible), 16 dp radius, a 2 px provider-colored left stripe, and hover/expanded elevation lifts.

Resolved dark-mode values:
- Card background: `#191c21` (vs. pane `#0f1115` — clearly distinct)
- Card border: `#262a31` (vs. previous hair `#1c1f24` — visibly outlined)

CSS (lands in both `src/dual_research/ui/static/components.css` and `design-system/assets/styles/composed-components.css`):

```css
.tl-thread {
  background: var(--md-surface-container-high);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-shape-lg);   /* 16 dp — M3-Expressive card */
  padding: 0;
  margin: 0;
  overflow: hidden;
  transition: background     var(--md-dur-short-3) var(--md-easing-standard),
              box-shadow     var(--md-dur-short-3) var(--md-easing-standard),
              border-color   var(--md-dur-short-3) var(--md-easing-standard);
}

.tl-thread:hover {
  background: var(--md-surface-container-highest);
  border-color: var(--md-outline);
  box-shadow: var(--md-elev-1);
}

/* Provider left-stripe via :has() — sable Claude / sage GPT / idle System */
.tl-thread:has(.tl-card-head > .chip.tone-claude) {
  border-left: 2px solid var(--p-sable);
}
.tl-thread:has(.tl-card-head > .chip.tone-gpt) {
  border-left: 2px solid var(--p-sage);
}
.tl-thread:has(.tl-card-head > .chip.tone-neutral:not(.mono)) {
  border-left: 2px solid var(--p-idle);
}

/* Expanded card */
.tl-thread.is-open-expanded {
  background: var(--md-surface-container-low);
  border-color: var(--md-outline-variant);
  box-shadow: var(--md-elev-2);
}
.tl-thread.is-open-expanded > .tl-card-head {
  background: var(--md-surface-container-high);
  border-bottom: 1px solid var(--md-outline-hair);
}
```

**`:has()` rationale.** Native CSS `:has()` ships in Chrome 105+, Safari 15.4+, Firefox 121+ — all browsers the dual-research UI targets. Using `:has()` keeps the JSX clean (no `data-provider` attribute on the `<article>`). The system-card stripe selector uses `.chip.tone-neutral:not(.mono)` to distinguish identity-System chips from the mono activity chip that may also use `.tone-neutral`.

`overflow: hidden` is load-bearing — without it the expanded body's rounded corners clip incorrectly when the card lifts.

**Files to change.**
- `src/dual_research/ui/static/components.css` — replace the current `.tl-thread` rules with the full block above + the three `:has()` provider stripes.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §3 Primitives — add a new "Timeline card (`.tl-thread`)" row documenting the four states (rest / hover / expanded-rest / expanded-hover) and the per-provider stripe.
- `design-system/SPEC.md` §4.4 — codify the chrome + the stripe rule.
- `design-system/assets/Design System v2.html` §16 — replace existing `.tl-turn` 5-col-grid examples with the M3 card rendered in all three provider variants (Claude / GPT / System), both rest and expanded.

### 2.5 Header agent strips — 8 % provider tint

**Now.** `.as.in-header` has flat `background: var(--md-surface-container)` (rule at approximately `src/dual_research/ui/static/components.css:407`). Identity is conveyed only by the 2 px left-border (sable for `is-a`, sage for `is-b`) + the brand-mark icon inside the strip.

**After.** Strip background carries a subtle 8 % tonal mix matching the provider:

```css
.as.is-a.in-header {
  background: color-mix(in srgb, var(--p-sable) 8%, var(--md-surface-container));
}
.as.is-b.in-header {
  background: color-mix(in srgb, var(--p-sage)  8%, var(--md-surface-container));
}
```

The 2 px left-stripe and the brand-mark icon stay.

**Files to change.**
- `src/dual_research/ui/static/components.css` — add the two rules near the existing `.as.in-header` rule.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §3 AgentStrip primitive — add: *"Inside `.tl__head` / `.tl__tabs` (the `in-header` variant), the strip carries an 8 % color-mix tonal background matching the provider."*
- `design-system/assets/Design System v2.html` §16 — render an in-header AgentStrip variant showing the tint.

### 2.6 Narrow-view strip equalisation (≤ 1799 px)

**Now.** `.as.in-header { min-width: 600px; flex: 0 0 auto }` is unconditional. At 1280 px viewport (640 px pane, 599 px inner content box after 20 px row padding × 2), the 600 px strip mostly fits inside `.tl__head` (leading content ≈ 239 px → 360 px available → strip overflows 240 px under the right padding, mostly hidden) but in `.tl__tabs` the leading content is ≈ 272 px (the tab labels are wider) so the strip overflows the pane edge by ~33 px. The trailing activity phrase (`"deadlocked"`) visibly clips to `"deadloc…"` with no ellipsis applied.

The result is two strips with identical CSS that visually present at different widths.

**After.** At viewports ≤ 1799 px (the existing live `@media` breakpoint used elsewhere in the timeline pane), both strips force-cap to 320 px and right-align to the same column inside the pane:

```css
@media (max-width: 1799px) {
  .tl__head .as.in-header,
  .tl__tabs .as.in-header {
    min-width: 0 !important;
    width: 320px !important;
    max-width: 320px !important;
    flex: 0 0 320px !important;
  }
  .tl__head .as.in-header .as-activity,
  .tl__tabs .as.in-header .as-activity {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
```

Math: at 1280 px viewport, each pane is 640 px. Inner content box (after pane horizontal padding 20 px × 2) is 599 px. `.tl__tabs` leading content is the limiting factor at 272 px. Maximum strip width that fits without overflow is 599 − 272 = 327 px. The cap is set to 320 px to leave a 7 px buffer.

With `margin-left: auto` already present on `.as.in-header`, both strips right-align to the column `[299..619]` at 1280 px pane width. The activity phrase falls back to `text-overflow: ellipsis` if the live phrase doesn't fit at 320 px.

`!important` is used to override the unconditional `min-width: 600px` and `flex: 0 0 auto` declarations that win on specificity otherwise.

**Files to change.**
- `src/dual_research/ui/static/components.css` — add the `@media (max-width: 1799px)` block.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §4.4 — add a responsive note: *"In narrow viewport (≤ 1799 px), both `.as.in-header` instances are capped at 320 px and right-align to the same column inside `.rdvc__pane`."*

## 3. UX / behaviour

After this spec lands:

- Every run-detail page renders with the new chrome on first load. No toggle. No opt-in.
- Phase markers read in full: `Phase 0` / `Phase 1` / `Phase 2` / `Phase 3` / `Phase 4`. The redundant `PHASE 0` pcode after the chevron is gone.
- Turn cards are visually distinct from the pane surface: 16 dp radius, 1 px visible outline, 2 px left stripe in the brand colour (sable for Claude turns, sage for GPT turns, idle grey for System cards). Cards are inset 16 px from the pane edges. Hover lifts to `elev-1`. Expanded turn cards lift to `elev-2`.
- Claude and GPT header strips carry a subtle 8 % tonal background so the strip identity reads even without focusing on the brand-mark icon.
- At viewports under 1800 px wide, both Claude and GPT strips render at exactly 320 px and right-align to the same column. Activity phrases that exceed the strip width truncate with an ellipsis instead of clipping.

Pre-existing runs render identically — no schema change, no data migration. The new chrome targets `.tl-thread` / `.tl-phase__hd` / `.tl-phase__body` / `.as.in-header`, all of which are present on every run vintage.

## 4. Data / schema deltas

None. This spec changes presentation only — no event-store fields, no run-detail JSON shape, no run-summary fields, no migrations.

## 5. Out of scope

- **Identity-chip backgrounds + activity-chip surface bump + light-mode chip text drift fix** — covered by spec 0165 (which depends on this spec).
- **System + Error chip primitives + agentless-card composition + `[object object]` data-layer fix** — covered by spec 0166 (depends on this spec).
- **Live-state agent-strip wiring (`.is-live` class + dot pulse + elev-2 lift)** — covered by spec 0166.
- **Phase-chip cluster category bubble alpha dim** — covered by spec 0165.
- **2-decimal cost precision on the expanded-card action row** — covered by spec 0165.
- **Critique-pane card chrome** — covered by separate critique spec(s) which depend on this spec for the M3 primitive.

## 6. Design-system gate

This spec touches UI. Cited DS sections being updated:

- `design-system/SPEC.md` §3 Primitives — new "Timeline card (`.tl-thread`)" row (per §2.4).
- `design-system/SPEC.md` §4.4 Timeline pane — phase header marker rename, pcode removal, card chrome, 16 px gutter, agent-strip tint, narrow-mode strip equalisation rule (per §2.1–2.6).
- `design-system/SPEC.md` §9.4 Composition order — unchanged; cited as the rule the provider stripe enforces visually.

Files that MUST land in the same commit:

- `design-system/SPEC.md`
- `design-system/assets/styles/composed-components.css`
- `design-system/assets/Design System v2.html` (§16 anatomy re-render — 5-col header, M3 cards in all three provider variants, in-header AgentStrip tint example)
- `src/dual_research/ui/static/components.css`
- `src/dual_research/ui/static/run-detail.jsx`
- `CHANGELOG.md` (new MINOR section)
- `pyproject.toml` (version bump)
- `src/dual_research/__init__.py` (version bump)

## 7. Test plan

- [ ] **Visual smoke at three widths.** Run `uv run dual-research serve`, open `/runs/20260521-010637-dvs-backend-language-choice` at 1280 px / 1600 px / 1920 px viewport. At 1280 px and 1600 px the narrow-mode strip equalisation is active and both `.as.in-header` widths must be exactly 320 px with right-edges at identical x. At 1920 px the strips render at their natural width (≥ 600 px).
- [ ] **Phase marker text.** All phase headers read `Phase 0` / `Phase 1` / `Phase 2` / `Phase 3` / `Phase 4`. No `P0` / `P1` / etc. anywhere in the DOM under `.tl-phase__marker .lbl`.
- [ ] **`.tl-phase__pcode` is gone.** `document.querySelectorAll('.tl-phase__pcode').length === 0` on the run-detail page. The CSS rule is also gone — `getComputedStyle` on a synthetic element with class `tl-phase__pcode` shows no styling from `components.css`.
- [ ] **Card chrome computed styles (dark mode).** `.tl-thread`: `background-color === rgb(25, 28, 33)` (`#191c21`), `border-color === rgb(38, 42, 49)` (`#262a31` resolved from `--md-outline-variant`), `border-radius === 16px`. `.tl-thread:has(.chip.tone-claude)` has computed `border-left-color === rgb(212, 165, 116)` (`--p-sable`). `.tl-thread:has(.chip.tone-gpt)` has `border-left-color === rgb(124, 196, 184)` (`--p-sage` resolved).
- [ ] **Card chrome computed styles (light mode).** Apply `body.light` (or whatever the live theme toggle is) and re-check: `.tl-thread` background resolves to the light surface-container-high value, border to the light outline-variant, radius unchanged at 16 px. Stripe colors unchanged.
- [ ] **Hover lift.** Hover a `.tl-thread`. Computed `box-shadow` resolves to the `--md-elev-1` token. Background bumps to `--md-surface-container-highest`. `border-color` bumps to `--md-outline`. Transition is visible (150 ms standard easing).
- [ ] **Expanded lift.** Expand a turn card. The card has `.is-open-expanded`. Computed `box-shadow` resolves to `--md-elev-2`. Background drops to `--md-surface-container-low`. The card head (`.tl-card-head`) inside the expanded card has `background === --md-surface-container-high` and a 1 px hairline bottom border.
- [ ] **Pane gutter.** `.tl-phase__hd` computed padding `12px 16px`; `.tl-phase__body` computed padding `8px 16px 12px`, computed `gap === 6px`.
- [ ] **Agent-strip tint.** `.as.is-a.in-header` background resolves to a color-mix of 8 % sable + surface-container. `.as.is-b.in-header` resolves to 8 % sage + surface-container. The 2 px left-border stays present.
- [ ] **Narrow-view strip widths.** At 1280 px viewport, both `.tl__head .as.in-header` and `.tl__tabs .as.in-header` have computed width `320px`. Their `getBoundingClientRect().right` values are equal (to within 1 px rounding).
- [ ] **Narrow-view ellipsis.** With the live phrase `"deadlocked at round 4 — manual intervention required"`, the `.as-activity` text truncates with `text-overflow: ellipsis` rather than clipping mid-glyph. Visible via inspecting `overflow` + `text-overflow` computed styles.
- [ ] **Old-run safety.** Render `/runs/<earliest-archived-run>` (a pre-spec-0114 run). No console errors. All `.tl-thread` cards render with the new chrome. All phase headers show the full `Phase N` label.
- [ ] **DS reference catch-up.** Open `design-system/assets/Design System v2.html` §16 in a browser. The rendered anatomy matches: 5-column phase header, marker + chev + name + meta + chips. M3 cards rendered with Claude / GPT / System variants. In-header agent strip rendered with the 8 % tint.
- [ ] **Tests pass.** `uv run pytest tests/ -q` exits 0.

## 8. Implementation steps (suggested order)

1. Update `design-system/SPEC.md` §3 + §4.4 first (text contract before code).
2. Update `design-system/assets/styles/composed-components.css` with the new rules.
3. Mirror the changes into `src/dual_research/ui/static/components.css`. Diff the two files to confirm parity.
4. Update `src/dual_research/ui/static/run-detail.jsx` (marker label + pcode removal).
5. Re-render `design-system/assets/Design System v2.html` §16.
6. Run the visual smoke tests (§7).
7. Write the CHANGELOG entry under a new `## [X.Y.Z] — YYYY-MM-DD` section.
8. Bump `pyproject.toml` + `src/dual_research/__init__.py` per MINOR.
