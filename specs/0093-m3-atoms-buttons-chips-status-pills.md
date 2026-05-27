---
spec: 0093
title: M3 atoms — buttons (5 variants) + FAB + icon button + chips (4 kinds) + status pills (canonical OK) + switches + segmented buttons
label: refactoring
version-bump: PATCH
status: proposed
target-version: 0.72.2
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0093 — M3 atoms

> Ship bucket: **Primitives**
> Depends on: **0092**
> Complexity: **M**
> Targeted version bump: **PATCH** (no new feature; primitives align to the token layer)

## 1. Goal

Replace the current button / chip / pill / switch / segmented-control
atoms with their M3 anatomies, so every later spec can use the
canonical primitives without re-inventing them. Resolves Issue 4
(canonical OK pill style) along the way. After this spec lands,
the run-list filter strip, run-detail header pills, and every chip
on the page reads from one consistent set of classes — and the
"OK" badge looks the same everywhere.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — add the full M3
  atom block: `.md-btn` + 5 variants (`--filled`, `--tonal`,
  `--outlined`, `--text`, `--elevated`) + 3 sizes (default 40 dp,
  `--sm` 32 dp, `--lg` 48 dp); `.md-icon-btn` (40 × 40 dp pill);
  `.md-fab` and `.md-fab--ext`; `.md-chip` + `.md-chip--selected`,
  `.md-chip--filter-a`, `.md-chip--sm`; `.md-status` + the **six
  state modifiers** (`--running`, `--converged`, `--drift`,
  `--errored`, `--idle`, `--queued`) with the canonical pastel
  pill anatomy from
  [v2-m3.css:428-441](docs/design-system-v2/assets/styles/v2-m3.css);
  `.md-switch` thumb-grows-on-on; `.md-seg` + `.md-seg__opt`
  segmented buttons. Mirror
  [v2-m3.css:299-494](docs/design-system-v2/assets/styles/v2-m3.css)
  verbatim. Also add the universal `.chip` / `.chip.tone-{ok,info,
  warn,err,idle,a,b,neutral,info-strong}` tonal chips from
  [v2-m3-page.css:575-594](docs/design-system-v2/assets/styles/v2-m3-page.css)
  and the v1.no-dot variant.
- `src/dual_research/ui/static/shared.jsx` — refactor the existing
  `Button`, `SB`, `Chip`, `StatusBadge`, `Pill`, and
  `ThemeToggleSegmented` primitives to render the new class names.
  `Button` now emits `<button class="md-btn md-btn--{variant}">`
  where variant is `filled` / `tonal` / `outlined` / `text` /
  `elevated`. `Chip` emits `<span class="md-chip">…</span>` or
  `<span class="chip tone-{tone}">…</span>` for tonal chips —
  pick by prop. `StatusBadge` emits `<span class="md-status
  md-status--{state}">`. Keep the existing prop API on each
  primitive so call sites do not break; the change is class names
  only. The single canonical OK style is the `md-status
  md-status--converged` chip (Issue 4 resolution) — refactor every
  caller that emitted a custom "ok" badge to use `<StatusBadge
  status="converged" label="ok" />`. Search for the antipatterns
  via `grep -rn 'ok-badge\|class.*ok\b\|>ok<' src/dual_research/ui/`
  before editing and unify them.
- `src/dual_research/ui/static/tweaks-panel.jsx` — replace the
  hand-rolled segmented buttons with `<div class="md-seg">
  <button class="md-seg__opt" aria-selected="…">…</button> …
  </div>` markup.
- `src/dual_research/ui/static/icons.jsx` — the `Mdi` glyph
  primitive continues to render the existing MDI icon-font glyphs,
  but add an `<MaterialSymbol name="…" size={20} />` primitive
  alongside it. `MaterialSymbol` emits `<span class="ms ms-{size}"
  aria-hidden="true">{name}</span>`. Subsequent specs use
  `MaterialSymbol` for any new icon, and the existing `Mdi`
  callers continue to render until refactored individually. The
  two primitives are not interchangeable — picking the right one
  is per-callsite.
- `pyproject.toml` — `0.72.1` → `0.72.2`.

## 3. Material 3 anatomy

- `#atoms` covers everything in this spec. Tokens read:
  `--md-shape-full` (pill radius), `--md-shape-sm` (chip radius),
  `--md-label-l-size` / `--md-label-l-track` (button label), the
  state-layer overlay rule (`::before` with `background:
  currentColor; opacity: var(--md-state-*);`), and
  `--md-elev-1..2` (filled hover lifts to elev-1, elevated lifts
  to elev-2 on hover). All values are verbatim from
  [v2-m3.css:299-494](docs/design-system-v2/assets/styles/v2-m3.css).
- The 22 dp pastel status pills with leading 6 dp dot are the
  Issue-4 canonical style. The "lower two OKs" the product owner
  picked correspond to `.md-status--converged` (pastel green pill
  + dot + uppercase label).

Exact CSS class names introduced or refactored:

```
.md-btn, .md-btn--{filled,tonal,outlined,text,elevated}, .md-btn--{sm,lg}, .md-btn[disabled]
.md-icon-btn
.md-fab, .md-fab--ext
.md-chip, .md-chip--selected, .md-chip--filter-a, .md-chip--sm
.md-status, .md-status--{running,converged,drift,errored,idle,queued}
.md-switch
.md-seg, .md-seg__opt
.chip, .chip.tone-{ok,info,info-strong,warn,err,idle,a,b,neutral}, .chip.no-dot
```

## 4. Notion issues addressed

1. **Issue 4 — All "OK" badges must use one consistent style.**
   `docs/design-system-v2/notion-issues/screenshots/04-ok-badges.png`
   shows three "ok" pills in three styles; the product owner
   picked the lower two (pastel-green pill + dot + uppercase
   label). After this spec, **every** "ok" badge in the app
   renders as `<span class="md-status md-status--converged">ok</span>`.
   Validation: load `#/runs/<a run with preflight + briefcritique
   ok pills>` at 2200×1300; visually confirm all three "ok"
   chips in the phase-0 preflight strip read identical to each
   other and match the design-system canonical pill.

## 5. Acceptance criteria

- [ ] `document.querySelectorAll('.md-btn').length > 0` after page
      load (refactor took effect); zero `class="btn-*"` /
      `class="button-*"` / hand-rolled `<button style="border: 0">…</button>`
      buttons remain in the run-list, run-detail header, or
      critique pane (verify via Grep).
- [ ] All six status pill variants render with identical height
      (22 dp), identical leading 6 dp dot in currentColor, and
      uppercase label.
- [ ] Issue 4: every "ok" indicator in the phase-0 preflight strip
      renders with the same `.md-status--converged` class. None
      uses an ad-hoc inline-styled pill.
- [ ] Hovering a filled button reveals elevation-1 shadow;
      hovering an elevated button lifts to elevation-2. Verified
      visually under DevTools forced `:hover`.
- [ ] Pressing a button shows the 12 % state-layer overlay (via
      `::before`); focus shows 10 %; hover shows 8 %.
- [ ] All atom primitives render correctly in dark and light
      without any per-theme override CSS.
- [ ] `MaterialSymbol` primitive renders the glyph (not the
      literal name string) at the requested size.
- [ ] The `md-switch` thumb expands from 16 dp to 24 dp on toggle
      and slides via `--md-easing-emphasized` at
      `--md-dur-short-3`.
- [ ] Tweaks panel theme/density toggles continue to function
      after the segmented-control refactor.

## 6. Visual verification matrix

- `2200×1300 dark` — route `#/runs/<latest-converged>` to see the
  full pill range in the run-detail header.
- `2200×1300 light` — same route, theme flipped.
- `1400×900 dark` — route `#/runs`, focus on the filter strip
  segmented control + chips.
- `1400×900 light` — same.
- `820×1180 dark` — single-column collapse; confirm buttons stay
  40 dp tall and chips wrap rather than overflow.
- `820×1180 light` — same.

All six are required because atom heights are the canonical
contract every other spec depends on; a missed regression at
<900 px would cascade.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database (`parseQId`-decoded
      `QuestionRef` for any q-id rendering — N/A here but verify
      no atom regresses existing decoded refs).
- [ ] No emoji as icons (Material Symbols Outlined only).
- [ ] No off-grid spacing (4 px / 8 px grid). Button height 40
      dp; small 32 dp; large 48 dp; status pill 22 dp (intentional
      — M3 attention chip standard).
- [ ] No hex codes in component CSS — atoms read `--md-primary`,
      `--md-on-primary`, `--md-primary-container`, etc.
- [ ] No per-theme overrides where token roles cover the case.
- [ ] Reduced-motion contract preserved
      (`prefers-reduced-motion: reduce` kills the state-layer
      transition).
- [ ] Focus ring visible on every focusable atom (button, chip,
      switch, segmented option, icon-btn).

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0092-m3-token-foundation.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** The atoms are pure CSS + JSX presentation. Status pills
read whatever `run.status` the backend already emits
(`running`, `converged`, `drift`, `errored`, `idle`, `queued`);
no new states are introduced.

## 11. CSS class anchor list

```
.md-btn, .md-btn--{filled,tonal,outlined,text,elevated}        → #atoms (button variants)
.md-btn--{sm,lg}                                               → #atoms (button sizes)
.md-icon-btn                                                   → #atoms (icon button)
.md-fab, .md-fab--ext                                          → #atoms (FAB + extended FAB)
.md-chip, .md-chip--selected, .md-chip--filter-a, .md-chip--sm → #atoms (chips)
.md-status, .md-status--{running,converged,drift,errored,idle,queued}
                                                               → #atoms (status pills — canonical OK)
.md-switch                                                     → #atoms (switch)
.md-seg, .md-seg__opt                                          → #atoms (segmented buttons)
.chip, .chip.tone-{ok,info,info-strong,warn,err,idle,a,b,neutral,no-dot}
                                                               → #cards / #thread / #critique (tonal chips)
```
