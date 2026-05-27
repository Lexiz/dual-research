---
spec: 0096
title: M3 modal primitive (basic 560 dp + rich 1080 dp, shape-xl, elevation-3, agent-tinted left border)
label: refactoring
version-bump: PATCH
status: proposed
target-version: 0.72.5
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0096 — M3 modal primitive

> Ship bucket: **Primitives**
> Depends on: **0092, 0094**
> Complexity: **S**
> Targeted version bump: **PATCH** (no new feature; primitive refactor)

## 1. Goal

Replace the existing `Modal` primitive (rendered in `shared.jsx`)
with the M3 dialog anatomy: shape-xl corners (28 dp), surface-3
background, elevation-3 shadow, max-width 560 dp for the basic
dialog and 1080 dp for the rich (full-screen) variant. Add the
optional agent-tinted left border (sable for Claude-attributed
dialogs, sage for GPT-attributed). After this spec, the
RoundScrubber footer + agent-input modal + How-It-Works overlay +
onboarding tour modals (later specs) all read from one canonical
dialog primitive.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the M3
  dialog block: `.md-dialog` + `.md-dialog__icon` +
  `.md-dialog__title` + `.md-dialog__body` + `.md-dialog__actions`
  per [v2-m3.css:601-619](docs/design-system-v2/assets/styles/v2-m3.css).
  Add variants:
  - `.md-dialog--basic` (default, max-width 560 dp).
  - `.md-dialog--rich` (max-width 1080 dp, used by How-It-Works
    + onboarding step 4 phases-explainer).
  - `.md-dialog--agent-a` (sable left border, 4 px,
    `border-left: 4px solid var(--p-sable);`).
  - `.md-dialog--agent-b` (sage left border).
  Add a `.md-dialog__scrim` rule for the dimmed backdrop:
  `position: fixed; inset: 0; background: rgba(0,0,0,0.55);
  z-index: 50;`. Light theme overrides to
  `rgba(20,23,28,0.30)`.
- `src/dual_research/ui/static/shared.jsx` — refactor the
  `Modal` primitive (currently around line 380-509) to emit the
  new markup. The existing props (`title`, `onClose`, `footer`,
  `actions`, `width`) stay; the change is internal. Default
  variant `basic`; add `variant="rich"` for full-screen and
  `agentTint="a" | "b"` for the left-border variant. The scrim
  click closes the modal; `Escape` key closes. Focus trap stays
  as-is (the existing impl is correct M3).
- `src/dual_research/ui/static/run-detail.jsx` — refactor every
  existing `<Modal …>` callsite (there are several: agent-input
  modal at line ~3992, phase rail modal, error-detail modal) to
  use the new prop API. No layout changes expected; the existing
  `width` props map cleanly to `variant`.
- `pyproject.toml` — `0.72.4` → `0.72.5`.

## 3. Material 3 anatomy

- `#modal` — basic dialog: shape-xl (28 dp), surface-3
  background, elevation-3 shadow, max-width 560 dp, padding
  `--md-sp-6` (24 dp). Rich dialog (used by How-It-Works + tour
  step 4): max-width 1080 dp, otherwise identical.
- `#elevation` — dialogs sit at level-3 (`--md-elev-3`).
- Agent-tint contract (`#identity`): if the dialog is
  attributed to an agent (e.g. the agent-input modal showing
  Claude's input), the 4 px left border carries the sable / sage
  hue.

Class-name contract:

```
.md-dialog__scrim          → backdrop scrim, fixed-position, dimmed
.md-dialog                 → base dialog; shape-xl, surface-3, elevation-3
.md-dialog--basic          → max-width 560 dp
.md-dialog--rich           → max-width 1080 dp
.md-dialog--agent-a        → sable 4 px left border
.md-dialog--agent-b        → sage 4 px left border
.md-dialog__icon           → top-centred 24 dp icon
.md-dialog__title          → headline-small in Roboto Serif
.md-dialog__body           → on-surface-variant prose
.md-dialog__actions        → flex-end button row, 8 dp gap
```

## 4. Notion issues addressed

Implements design-system primitive only; no Notion issue.

## 5. Acceptance criteria

- [ ] `.md-dialog--basic` renders with computed `max-width:
      560px`; `.md-dialog--rich` renders with `max-width:
      1080px`.
- [ ] Both variants have `border-radius:` resolving to 28 px
      (`var(--md-shape-xl)`).
- [ ] Both variants have `box-shadow:` resolving to the
      elevation-3 token recipe.
- [ ] The scrim covers the full viewport and dims at 55 %
      opacity in dark mode, 30 % in light mode.
- [ ] Clicking the scrim closes the modal; pressing `Escape`
      closes the modal; the focus trap returns focus to the
      element that triggered the modal on close.
- [ ] `<Modal agentTint="a">` shows a 4 px sable left border;
      `agentTint="b"` shows sage; absence shows no left border.
- [ ] The agent-input modal at `#/runs/<id>` (open via the
      timeline turn's "Show input" action) renders without
      layout regression against the v1 baseline.

## 6. Visual verification matrix

- `2200×1300 dark` — open the agent-input modal from a run-
  detail timeline turn.
- `2200×1300 light` — same.
- `1400×900 dark` — same. Verify the modal doesn't overflow
  horizontally; the rich variant in particular needs to confirm
  the 1080 dp max-width plus the scrim margin still fits.
- `1400×900 light` — same.
- `820×1180 dark` — verify the dialog shrinks to fit the
  viewport (full-width with 16 dp margin) and the actions row
  remains flex-end.
- `820×1180 light` — same.

All six required. The dialog primitive is reused by four later
specs; any breakpoint regression here cascades.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database.
- [ ] No emoji as icons (Material Symbols only inside
      `md-dialog__icon`).
- [ ] No off-grid spacing — padding 24 dp, gap 8 dp, max-widths
      560 / 1080 dp (M3 canonical).
- [ ] No hex codes in component CSS — agent-tint reads
      `var(--p-sable)` / `var(--p-sage)` from the foundation
      palette layer.
- [ ] No per-theme overrides for component selectors; scrim
      opacity is the only per-theme value and lives on the
      `body.light .md-dialog__scrim` rule.
- [ ] Reduced-motion contract preserved — modal open animation
      `--md-easing-emphasized-decel` at `--md-dur-medium-2` is
      killed under `reduce`.
- [ ] Focus ring visible on actions row; focus trap holds inside
      the dialog.

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0095-m3-tabs-top-app-bar-chrome-compaction.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** The modal primitive is presentation-only.

## 11. CSS class anchor list

```
.md-dialog                          → #modal (base · shape-xl · elevation-3)
.md-dialog--basic, --rich           → #modal (size variants)
.md-dialog--agent-{a,b}             → #modal · #identity (agent-tinted variants)
.md-dialog__scrim                   → #modal (backdrop)
.md-dialog__icon                    → #modal (top icon slot)
.md-dialog__title                   → #modal · #type (headline-small / Roboto Serif)
.md-dialog__body                    → #modal (prose body)
.md-dialog__actions                 → #modal (action row, flex-end)
```
