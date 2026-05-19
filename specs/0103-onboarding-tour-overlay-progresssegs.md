---
spec: 0103
title: Onboarding tour overlay + ProgressSegs admin (8-step tour over the live app via data-tour-anchor attributes; no redraw of underlying surfaces; ProgressSegs 8-segment per-user track)
label: new-feature
version-bump: MINOR
status: proposed
target-version: 0.76.0
created: 2026-05-19
pr: ""
---

# Spec 0103 — Onboarding tour overlay + ProgressSegs

> Ship bucket: **Page-level**
> Depends on: **0092, 0093, 0094, 0096**
> Complexity: **L**
> Targeted version bump: **MINOR** (new-feature label — overlay tour + admin surface are new top-level features)

## 1. Goal

Replace the existing 3-screen modal flow (`onboarding.jsx`,
`OnboardingScreen`) with the canonical **8-step tour that
overlays the live app**. Each step is a spotlight pinned to a
real DOM node on the running page (run-list row, run-detail
header, phase rail, timeline, critique pane, consumption card)
plus a 360 dp M3 callout floating to the side. **The tour must
not re-render the underlying app shell.** Specs touching the
target surfaces (0095, 0098, 0099, 0100) add `data-tour-anchor`
attributes to the canonical DOM nodes; the tour reads their
bounding boxes at step time.

Also ship the admin `ProgressSegs` 8-segment per-user track on
the `/admin/users` page, one segment per onboarding step.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the
  tour scene + callout block: `.scene` + `.scene__label` +
  `.scene__viewport` + `.scene__mask` + `.scene__cutout` per
  [v2-m3-page.css:338-374](docs/design-system-v2/assets/styles/v2-m3-page.css);
  `.callout` + `.callout__step` + `.callout__title` +
  `.callout__body` + `.callout__progress` + `.callout__actions`
  + `.callout__spacer` per
  [v2-m3-page.css:376-407](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the ProgressSegs strip `.seg-track` + `.seg-track__seg` +
  `.seg-track__seg--{done,curr,queued}` per
  [v2-m3-page.css:312-321](docs/design-system-v2/assets/styles/v2-m3-page.css).
  Add a new `.tour-overlay` family for the live-app overlay
  wrapper:
  - `.tour-overlay` — fixed-position covering the viewport,
    z-index above the app but below the modal scrim.
  - `.tour-overlay__mask` — the dim layer, `inset: 0`,
    `pointer-events: none`, `background: rgba(0,0,0,0.55)`
    (or 30 % in light); with a `clip-path` cut-out positioned
    on the anchor element's bounding box.
  - `.tour-overlay__cutout` — the highlight ring around the
    anchor element (2 px info border, scrim hole).
  - `.tour-overlay__callout` — the 360 dp callout box; uses
    `.callout` family above. Position is computed at step time
    from the anchor's bounding box.
- `src/dual_research/ui/static/onboarding.jsx` — rewrite. The
  new module exports `<TourOverlay open step onClose
  onAdvance onBack />`. The component:
  - **Does not re-render any underlying surface.** It mounts as
    a sibling of the app root and overlays via `position:
    fixed`.
  - For step 1 (welcome modal) and step 4 (phases-explainer)
    and step 8 (closing modal), the overlay renders an M3 rich
    dialog (`<Modal variant="rich">`) over a dimmed mask of the
    live page. The dialog body for step 4 inlines the SVG from
    [Design System v2.html#tour-4](docs/design-system-v2/assets/Design%20System%20v2.html)
    lines 1828-1842 (the phases-overview diagram).
  - For steps 2, 3, 5, 6, 7 (spotlights), the overlay reads the
    bounding box of the DOM element with `[data-tour-anchor="…"]`
    matching the step's anchor id, computes the `clip-path`
    cut-out, and positions the `.callout` next to it (right
    side at 1500+ px, below at <1500 px). The step ids and
    their anchors:
    | Step | Anchor selector                            | Surface owned by |
    |------|--------------------------------------------|------------------|
    | 2    | `[data-tour-anchor="run-row"]`             | Spec 0095        |
    | 3    | `[data-tour-anchor="run-detail-header"]`   | Spec 0095        |
    | 5    | `[data-tour-anchor="timeline-phase-rail"]` | Spec 0099        |
    | 6    | `[data-tour-anchor="critique-pane"]`       | Spec 0098        |
    | 7    | `[data-tour-anchor="consumption-card"]`    | Spec 0100        |
  - Steps 2 and 3 require navigation: step 2 expects the user
    to be on `/runs`; step 3 expects `/runs/<id>`. The tour
    advances the URL via `navigate(…)` between step 2 and step
    3, then back between step 8 and dismissal.
  - On `Continue` advance: increment step, update the
    `dr_tour_step` localStorage value, recompute the spotlight.
  - On `Back` regress: decrement step, recompute.
  - On `Skip` / final `Done`: set `dr_onboarded = true` in
    localStorage; remove the overlay. The 3-screen v1 flow is
    deleted entirely.
- `src/dual_research/ui/static/run-list.jsx` — add
  `data-tour-anchor="run-row"` to the first rendered RunRow in
  `RunListView` (line 95+). Only the first row carries the
  attribute; the tour reads its bounding box for step 2.
- `src/dual_research/ui/static/run-detail.jsx` — add the four
  tour anchors:
  - `data-tour-anchor="run-detail-header"` on the run-detail
    sticky header strip (around line 103 `RunDetailHeader`).
  - `data-tour-anchor="timeline-phase-rail"` on the `.tl__rail`
    container (Spec 0099 renders this; this spec adds the
    attribute).
  - `data-tour-anchor="critique-pane"` on the `.crit2`
    container (Spec 0098 renders this; this spec adds the
    attribute).
  - `data-tour-anchor="consumption-card"` on the first `.ccx`
    card in the consumption pane (Spec 0100 renders this; this
    spec adds the attribute).
- `src/dual_research/ui/static/app.jsx` — mount the
  `<TourOverlay />` component as a sibling of the app root.
  On first sign-in (no `dr_onboarded` flag), set `open=true` and
  `step=1`. Render unconditionally for `?reset_onboarding=1` so
  the tour can be re-triggered for development.
- **New file**: `src/dual_research/ui/static/admin-users.jsx` —
  the admin Users page rendering the ProgressSegs strip per
  user. Mirror the design-system anatomy from
  [Design System v2.html#admin](docs/design-system-v2/assets/Design%20System%20v2.html)
  lines 2862-2938. Read user list from a `useUserList()` hook
  (the existing auth.jsx exposes the current user; this spec
  adds the admin list read). If the backend admin endpoint
  doesn't exist yet, render the current user only as a single-
  row table with their own progress — the spec is forward-
  compatible.
- `src/dual_research/ui/static/index.html` — add the new
  `admin-users.jsx` script tag with cache-bust.
- `src/dual_research/ui/static/router.jsx` — register the
  `/admin/users` route → `<AdminUsers />`.
- `pyproject.toml` — `0.75.0` → `0.76.0`.

## 3. Material 3 anatomy

- `#tour` — verbatim source for the 8-step canonical tour. Each
  step uses an M3 basic / rich dialog + a 360 dp callout. The
  spotlight cut-out is a `clip-path` polygon punched out of the
  scrim.
- `#admin` — verbatim source for the ProgressSegs 8-segment
  strip. Eight cells, fixed; ok / info / muted per state.
- `#modal` — steps 1, 4, 8 use the rich dialog primitive from
  Spec 0096.
- `#a11y` — the overlay traps focus inside the callout when
  active; `Tab` cycles within the callout buttons; `Escape`
  fires `onClose`.

**Inline HTML structure** (steps 2 and 7 shown as canonical
examples; the same pattern applies to 3, 5, 6):

```html
<!-- Tour overlay: live page underneath, dimmed mask with cutout, floating callout -->
<div class="tour-overlay">

  <!-- Mask with the cutout punched out via clip-path -->
  <div class="tour-overlay__mask" style="clip-path: polygon(/* viewport with cutout-hole */);"></div>

  <!-- 2 px info-tinted highlight ring around the anchor -->
  <div class="tour-overlay__cutout" style="top:110px;left:12px;right:12px;height:70px;"></div>

  <!-- 360 dp M3 callout, positioned next to the anchor -->
  <div class="callout" style="top:200px;right:24px;">
    <div class="callout__step">STEP 2 · RUN ROW</div>
    <div class="callout__title">One row, the whole run</div>
    <p class="callout__body">Each row carries the run ID, topic, current phase, round, status, duration, tokens, and cost. Eight columns, scannable in one glance.</p>
    <div class="row">
      <div class="callout__progress">
        <span></span><span class="on"></span><span></span><span></span><span></span><span></span><span></span><span></span>
      </div>
      <div class="callout__spacer"></div>
      <button class="md-btn md-btn--text md-btn--sm">Back</button>
      <button class="md-btn md-btn--filled md-btn--sm">Continue</button>
    </div>
  </div>

</div>
```

ProgressSegs admin strip per user (one row per user, the strip
to the right of name + last-sign-in):

```html
<div class="md-list__item">
  <span class="ms ms-24 md-list__lead">account_circle</span>
  <div class="md-list__body">
    <div class="md-list__headline">priya.m@dual.dev</div>
    <div class="md-list__support">last sign-in · 2026-05-19 11:18 · paused at step 5</div>
  </div>
  <div style="width:320px;">
    <div class="seg-track" aria-label="5 of 8 steps">
      <div class="seg-track__seg seg-track__seg--done"></div>
      <div class="seg-track__seg seg-track__seg--done"></div>
      <div class="seg-track__seg seg-track__seg--done"></div>
      <div class="seg-track__seg seg-track__seg--done"></div>
      <div class="seg-track__seg seg-track__seg--curr"></div>
      <div class="seg-track__seg seg-track__seg--queued"></div>
      <div class="seg-track__seg seg-track__seg--queued"></div>
      <div class="seg-track__seg seg-track__seg--queued"></div>
    </div>
    <div class="t-label-s subtle" style="margin-top:4px;">5 / 8</div>
  </div>
  <span class="md-status md-status--running">in progress</span>
</div>
```

## 4. Notion issues addressed

Implements design-system page-level surface only; no Notion
issue.

## 5. Acceptance criteria

- [ ] First-sign-in (no `dr_onboarded` localStorage flag) opens
      the tour at step 1. The welcome modal appears over a
      dimmed `/runs` page; the run-list is still rendered in
      the DOM underneath the scrim (verified by DOM query for
      `.run-row`).
- [ ] **No tour-only re-creation.** Verify by inspecting the
      DOM at each step: the underlying app surface is present
      and untouched. The tour overlay is a sibling of the app
      root.
- [ ] Step 2 reads the bounding box of `[data-tour-anchor="run-row"]`
      (rendered by `run-list.jsx`) and positions the spotlight
      cut-out around it.
- [ ] Step 3 navigates to `/runs/<id>` and reads
      `[data-tour-anchor="run-detail-header"]`.
- [ ] Step 4 renders the rich dialog with the phases-explainer
      SVG inlined.
- [ ] Steps 5-7 read their anchors (`timeline-phase-rail`,
      `critique-pane`, `consumption-card`) and position
      spotlights accordingly.
- [ ] Step 8 closing modal sets `dr_onboarded = true` and
      removes the overlay; focus returns to the page.
- [ ] `Back` button regresses one step and updates the cut-out;
      `Skip` button on any step jumps to step 8.
- [ ] `?reset_onboarding=1` forces step 1 regardless of the
      localStorage flag.
- [ ] `/admin/users` route renders `<AdminUsers />` with one
      `.md-list__item` per user, each containing an 8-segment
      `.seg-track` that visualises the user's tour state
      (done / curr / queued).
- [ ] The `.seg-track` exactly mirrors the design-system
      anatomy — 8 cells, ok / info / muted per state, fixed at
      8 because the tour has 8 steps.
- [ ] All overlay surfaces render correctly in dark and light
      without per-theme overrides (the scrim opacity is the
      only per-theme value, covered by Spec 0096).

## 6. Visual verification matrix

- `2200×1300 dark` — capture each of the 8 steps. (Multiple
  screenshots; spawn from a single tour run via the `?reset_
  onboarding=1` flag.)
- `2200×1300 light` — same 8 captures.
- `1400×900 dark` — capture steps 2 and 5 (the spotlights most
  sensitive to viewport size); verify the callout positions to
  the right of the anchor at this width.
- `1400×900 light` — same.
- `820×1180 dark` — capture steps 2 and 5; verify the callout
  positions **below** the anchor (not to the right) when
  viewport <900 px.
- `820×1180 light` — same.

All six required.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database.
- [ ] No emoji as icons.
- [ ] No off-grid spacing.
- [ ] No hex codes in component CSS.
- [ ] No per-theme overrides where token roles cover the case.
- [ ] Reduced-motion contract preserved — spotlight slide
      reads `--md-easing-emphasized-decel` at
      `--md-dur-medium-2`; killed under `reduce`.
- [ ] Focus ring visible on callout buttons + admin row
      focusables.
- [ ] **Page-level anti-pattern:** the tour must NOT re-render
      the run-list / run-detail / phase rail / timeline /
      critique / consumption — they must remain the live app
      surfaces underneath. Spec-out the explicit DOM-query
      verification.
- [ ] **Admin anti-pattern:** the user list is read-only;
      ProgressSegs are visual progress indicators, not toggles.
      No "reset tour for user" button on this surface — that
      lives elsewhere if at all.

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0102-how-it-works-overlay-changelog.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** The tour state lives in localStorage. The admin user
list reads from whatever auth `me`/list endpoint already exists
(`auth.jsx`); if the admin-list endpoint doesn't exist,
`<AdminUsers />` renders the current user only with their own
ProgressSegs derived from localStorage. **Degrade gracefully:**
no backend admin endpoint → single-row table. No
`dr_tour_step` flag → start at step 1. No anchor found at step
time → skip the step (advance to the next one) rather than
fabricating a position.

## 11. CSS class anchor list

```
.tour-overlay                              → #tour (live-app overlay container)
.tour-overlay__mask                        → #tour (dimmed scrim with clip-path cutout)
.tour-overlay__cutout                      → #tour (highlight ring around anchor)
.tour-overlay__callout                     → #tour (positioned callout)

.scene                                     → #tour (per-step scene wrapper, design-system showcase only)
.scene__label                              → #tour (step label)
.scene__viewport                           → #tour (anchored region)
.scene__mask                               → #tour (clip-path mask)
.scene__cutout                             → #tour (cutout ring)

.callout                                   → #tour (360 dp callout)
.callout__step, __title, __body            → #tour (callout anatomy)
.callout__progress, __actions, __spacer    → #tour (progress dots + action row)

.seg-track                                 → #admin (8-segment track)
.seg-track__seg                            → #admin (per-step segment)
.seg-track__seg--{done,curr,queued}        → #admin (state-tinted segments)

[data-tour-anchor="run-row"]               → #tour (anchor on RunRow in 0095)
[data-tour-anchor="run-detail-header"]     → #tour (anchor on run-detail header in 0095)
[data-tour-anchor="timeline-phase-rail"]   → #tour (anchor on .tl__rail in 0099)
[data-tour-anchor="critique-pane"]         → #tour (anchor on .crit2 in 0098)
[data-tour-anchor="consumption-card"]      → #tour (anchor on .ccx in 0100)
```
