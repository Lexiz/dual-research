---
spec: 0102
title: How It Works overlay + right-side menu + Changelog (full-screen M3 dialog · sticky right menu · How It Works ↔ Changelog toggle · 9 collapsible sub-sections with inline diagrams)
label: new-feature
version-bump: MINOR
status: proposed
target-version: 0.75.0
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0102 — How It Works overlay + Changelog

> Ship bucket: **Page-level**
> Depends on: **0092, 0093, 0094, 0095, 0096**
> Complexity: **L**
> Targeted version bump: **MINOR** (new-feature label — full-screen overlay + right-menu + toggle is a new top-level surface)

## 1. Goal

Move the "How It Works" page from its current route-based render
to a **full-screen M3 dialog overlay** triggered by the top app
bar button. Inside the overlay, render the nine canonical sub-
sections (`Protocol overview` · `Preflight` · `Independent
research` · `Plan negotiation` · `Drafting` · `Review loop` ·
`Disagreement & convergence` · `Cost & consumption` · `Version
notes`) plus the Changelog, with a sticky right-side menu that
toggles between **How It Works** and **Changelog**. Every long
sub-section collapses to a one-sentence summary with a `Read more`
chevron; only heroes and diagrams stay visible by default.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the
  How-It-Works block: `.hiw` + `.hiw-sec` + `.hiw-sec > .label`
  + `.hiw-sec > h3` + `.hiw-sec > .lede` + `.hiw-diagram` per
  [v2-m3-page.css:409-435](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the changelog block: `.changelog` + `.changelog__entry` +
  `.changelog__date` + `.changelog__body` per
  [v2-m3-page.css:457-471](docs/design-system-v2/assets/styles/v2-m3-page.css).
  Add a new `.hiw-overlay` family for the dialog wrapper:
  - `.hiw-overlay` — the rich dialog (uses `.md-dialog
    .md-dialog--rich` from Spec 0096, max-width 1080 dp).
  - `.hiw-overlay__layout` — internal grid: `1fr 240px`,
    long-form left + sticky right menu.
  - `.hiw-overlay__menu` — sticky right menu container,
    `position: sticky; top: 24px; align-self: start;`.
  - `.hiw-overlay__menu-toggle` — segmented control switching
    between How It Works and Changelog (uses
    `.tab-group-solid` from Spec 0095).
  - `.hiw-overlay__menu-list` — `<ol>` of links, one per sub-
    section, anchoring to `#hiw-{slug}`.
  - `.hiw-sec[data-collapsed="true"]` — collapsed sub-section
    state. The hero (diagram) stays visible; multi-paragraph
    prose collapses to the `.lede` only; the rest of the body
    is `display: none`. A `Read more` chevron toggles
    `data-collapsed`.
- `src/dual_research/ui/static/how-it-works.jsx` — rewrite the
  existing route-based `HowItWorks` component (currently line
  1682, registered as `window.HowItWorks`) as a full-screen
  modal-overlay component. The component takes `open` and
  `onClose` props and renders inside a `<Modal variant="rich"
  scrim>` wrapper from Spec 0096. The body is the
  `.hiw-overlay__layout` grid: the left column is the existing
  `.hiw` content (9 sub-sections in the canonical order from
  the design system), the right column is the sticky menu.
  Each `.hiw-sec` renders with the existing diagram + label +
  h3 + lede pattern but with the new collapse contract: the
  body content after the lede is wrapped in
  `.hiw-sec__body[data-collapsed="true|false"]` driven by a
  per-section React state. The first sub-section
  (`#hiw-hero`, Protocol overview) is open by default; the
  remaining eight are collapsed by default. The Changelog
  view replaces the `.hiw` content with a `.changelog` list
  when the right-menu toggle is on `Changelog`; the most
  recent entry is open by default, prior entries collapsed.
- `src/dual_research/ui/static/app.jsx` — replace the
  `route.view === 'how-it-works'` route (line 119) and the
  separate page render (line 270 calls `navigate('how-it-works')`)
  with a state flag `howOpen` that opens the overlay in place.
  The "How it works" button in `RightCluster` (line 274) sets
  `howOpen = true`; closing the modal sets it back to false.
  No URL navigation; the URL hash is preserved so the user
  doesn't lose their place. Add a query-string fallback
  (`?how=1`) so deep links still open the overlay over the
  current page.
- `pyproject.toml` — `0.74.1` → `0.75.0`.

## 3. Material 3 anatomy

- `#how` — verbatim source for content + layout.
- `#changelog` — verbatim source for the changelog entries.
- `#modal` — the overlay reads `--rich` variant (max-width
  1080 dp, shape-xl, surface-3, elevation-3, scrim).
- `#tabs` — the right-menu toggle uses
  `.tab-group-solid` from Spec 0095.

Class-name contract:

```
.hiw-overlay                        → #how · #modal (rich dialog overlay)
.hiw-overlay__layout                → #how (1fr 240px grid)
.hiw-overlay__menu                  → #how (sticky right menu)
.hiw-overlay__menu-toggle           → #how (How It Works ↔ Changelog segmented)
.hiw-overlay__menu-list             → #how (sub-section links)

.hiw                                → #how (long-form content stack)
.hiw-sec                            → #how (per sub-section)
.hiw-sec > .label                   → #how (small uppercase label)
.hiw-sec > h3                       → #how (Roboto Serif headline-large)
.hiw-sec > .lede                    → #how (body lede)
.hiw-sec__body                      → #how (collapsible body)
.hiw-sec[data-collapsed="true"] .hiw-sec__body
                                    → #how (collapsed state)
.hiw-diagram                        → #how (inline SVG diagram wrapper)

.changelog                          → #changelog (entry stack)
.changelog__entry                   → #changelog (one release entry)
.changelog__date                    → #changelog (release date · version)
.changelog__body                    → #changelog (entry body)
.changelog__entry[data-collapsed="true"] .changelog__body
                                    → #changelog (collapsed past entry)
```

## 4. Notion issues addressed

Implements design-system page-level surface only; no Notion
issue.

## 5. Acceptance criteria

- [ ] Clicking the "How it works" button in the top app bar
      opens a full-screen overlay (covers the viewport with a
      55 % dark scrim / 30 % light scrim). The underlying page
      remains in place; the URL does not navigate.
- [ ] Pressing `Escape` or clicking outside the dialog closes
      the overlay. The triggering button regains focus.
- [ ] The overlay layout is a two-column grid: 1 fr long-form
      content on the left, 240 dp sticky menu on the right.
- [ ] The right-menu toggle switches between two views: "How
      It Works" (default) and "Changelog". Active state via
      `.tab-solid.is-active`.
- [ ] In "How It Works" view, the menu lists exactly nine
      sub-section links in this order: Protocol overview,
      Preflight, Independent research, Plan negotiation,
      Drafting, Review loop, Disagreement & convergence,
      Cost & consumption, Version notes. Each link anchors to
      the corresponding `.hiw-sec` (`#hiw-hero`, `#hiw-p0`,
      `#hiw-p1`, `#hiw-p2`, `#hiw-p3`, `#hiw-p4`, `#hiw-dis`,
      `#hiw-cost`, `#hiw-vn`).
- [ ] On first render, only `#hiw-hero` is fully expanded;
      the other eight sub-sections show diagram + label + h3 +
      lede and a `Read more` chevron. Clicking the chevron
      flips `data-collapsed` and reveals the remainder.
- [ ] In "Changelog" view, the menu lists the recent release
      dates. The most recent entry is open by default; the rest
      collapse to date + title with a `Read more` chevron.
- [ ] The overlay renders correctly in dark and light without
      per-theme overrides.
- [ ] The diagrams inside each sub-section use the canonical
      SVGs from the design-system bundle. The implementer
      copies the SVG markup from
      [Design System v2.html#how](docs/design-system-v2/assets/Design%20System%20v2.html)
      (lines 2293-2860). These SVGs are static; no JS.
- [ ] Deep link `?how=1` opens the overlay on page load over
      whatever route is in the hash. Closing the overlay
      removes `?how=1` from the URL.

## 6. Visual verification matrix

- `2200×1300 dark` — open the overlay; capture (a) How It
  Works view with hero expanded and other sections collapsed,
  (b) one sub-section expanded after `Read more`,
  (c) Changelog view.
- `2200×1300 light` — same three states.
- `1400×900 dark` — same. Verify the 1080 dp max-width fits
  with side margins; the right-menu remains 240 dp wide.
- `1400×900 light` — same.
- `820×1180 dark` — single-column collapse: the right menu
  becomes a horizontal segmented control at the top of the
  overlay; the long-form content stacks below. Verify the
  collapse contract still works.
- `820×1180 light` — same.

All six required.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database.
- [ ] No emoji as icons (Material Symbols Outlined only).
- [ ] No off-grid spacing.
- [ ] No hex codes in component CSS.
- [ ] No per-theme overrides where token roles cover the case.
- [ ] Reduced-motion contract preserved — overlay open animation
      reads `--md-easing-emphasized-decel` at `--md-dur-medium-2`;
      killed under `reduce`.
- [ ] Focus ring visible on every focusable (menu items, Read-
      more chevrons, toggle).
- [ ] **Page-level anti-pattern:** the overlay does NOT redraw
      the underlying app shell; it sits on top of the live
      page. Verify by opening the overlay from `#/runs/<id>` and
      confirming the run-detail layout is still rendered in the
      DOM underneath the scrim.

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0101-agent-input-phaserail-roundscrubber.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** The How-It-Works content is static (lives in
`how-it-works.jsx`). The changelog reads from `useAppMeta()`'s
version array which already exists. **Degrade gracefully:** if
the changelog API doesn't return a particular release entry,
omit it from the list rather than rendering a placeholder; if
no diagram SVG exists for a sub-section, render the lede + body
without the `.hiw-diagram` slot.

## 11. CSS class anchor list

```
.hiw-overlay                                            → #how · #modal (overlay container)
.hiw-overlay__layout                                    → #how (two-column grid)
.hiw-overlay__menu                                      → #how (sticky right menu)
.hiw-overlay__menu-toggle                               → #how (HIW ↔ Changelog toggle)
.hiw-overlay__menu-list                                 → #how (sub-section anchor links)

.hiw                                                    → #how (long-form content stack)
.hiw-sec                                                → #how (one sub-section)
.hiw-sec > .label, .hiw-sec > h3, .hiw-sec > .lede      → #how (sub-section anatomy)
.hiw-sec__body, .hiw-sec[data-collapsed="true"]         → #how (collapse contract)
.hiw-diagram                                            → #how (SVG wrapper)

.changelog                                              → #changelog (entry stack)
.changelog__entry                                       → #changelog (entry)
.changelog__entry[data-collapsed="true"]                → #changelog (collapsed past entry)
.changelog__date, .changelog__body                      → #changelog (entry anatomy)
```
