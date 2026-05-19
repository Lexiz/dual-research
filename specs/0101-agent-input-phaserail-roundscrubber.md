---
spec: 0101
title: Agent input panel + PhaseRail + RoundScrubber M3 anatomy sweep
label: refactoring
version-bump: PATCH
status: proposed
target-version: 0.74.1
created: 2026-05-19
pr: ""
---

# Spec 0101 — Agent input panel, PhaseRail, RoundScrubber

> Ship bucket: **Composed**
> Depends on: **0092, 0094, 0096**
> Complexity: **S**
> Targeted version bump: **PATCH** (refactoring label — primitives sweep, no new feature)

## 1. Goal

Bring three secondary surfaces into M3 anatomy: the agent input
panel (two tonal panes per agent), the PhaseRail (five-cell
horizontal strip), and the RoundScrubber (segmented round
navigation). After this spec, every read-only inspector surface
reads from the canonical primitive set and renders identically in
both themes without per-agent CSS.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the
  agent-input block: `.agent-input` (two-column grid) +
  `.agent-input__pane` + `.agent-input__pane--{a,b}` (tonal
  background + agent-tinted outline) + `.agent-input__head` +
  `.agent-input__body` per
  [v2-m3-page.css:290-310](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the PhaseRail block: `.phase-rail` + `.phase-rail__cell` +
  `.phase-rail__cell .ph` + `.phase-rail__cell .name` +
  `.phase-rail__cell .meta` + `.phase-rail__cell--{done,current}`
  per
  [v2-m3-page.css:182-209](docs/design-system-v2/assets/styles/v2-m3-page.css).
  RoundScrubber styling reuses `.md-seg` + `.md-seg__opt` from
  Spec 0093 + `.md-icon-btn` for the prev/next arrows.
- `src/dual_research/ui/static/run-detail.jsx` — refactor:
  - `PhaseRail` component (line 715): rewrite to emit `<div
    class="phase-rail">` with one `<div class="phase-rail__cell
    [phase-rail__cell--done|--current]">` per phase. The current
    phase carries an info-tinted outline; done phases carry the
    ok-tinted background.
  - `RoundScrubber` rendering (around line 4016, inside the
    agent-input modal): wrap in the canonical chrome — prev
    arrow + `.md-seg` + next arrow + meta caption — per the
    design-system canonical at
    [Design System v2.html · #modal RoundScrubber](docs/design-system-v2/assets/Design%20System%20v2.html)
    lines 1484-1496. The actual `RoundScrubber` primitive in
    `shared.jsx` (line 1005) already emits a segmented control;
    the change is the wrapping chrome and the use of
    `<MaterialSymbol name="chevron_left" />` / `chevron_right`
    inside the icon buttons.
  - Agent input modal (the modal opened when a user clicks
    "Show input" on a timeline turn): refactor the body to
    `<div class="agent-input"><div class="agent-input__pane
    agent-input__pane--a">…</div><div class="agent-input__pane
    agent-input__pane--b">…</div></div>`. Each pane has a head
    (AgentStrip + StatusBadge) and a body (the pre-formatted
    input bundle the agent received). At <1500 px the panes
    stack vertically per the
    [v2-m3-page.css:310](docs/design-system-v2/assets/styles/v2-m3-page.css)
    rule.
- `src/dual_research/ui/static/shared.jsx` — `RoundScrubber`
  (line 1005) keeps its prop API. Internal markup updates to
  emit the canonical wrapping chrome. The component renders
  the modal footer slot so it pairs with the M3 dialog
  primitive from Spec 0096.
- `pyproject.toml` — `0.74.0` → `0.74.1`.

## 3. Material 3 anatomy

- `#input` — two-pane tonal layout, one per agent. Tonal
  containers read `--md-primary` / `--md-secondary` at 5 %
  opacity over surface-container; outline reads the same
  palette at 28 % blended with `--md-outline-hair`.
- `#modal` (PhaseRail + RoundScrubber section) — PhaseRail is
  a 5-cell grid; RoundScrubber is a segmented-button row with
  prev/next icon buttons and a meta caption.
- `#a11y` — the segmented round options use
  `role="tab" aria-selected="…"`; the prev/next icon buttons
  use `aria-label="Previous round"` / `"Next round"`.

Class-name contract:

```
.agent-input                             → #input (two-column grid)
.agent-input__pane, --a, --b             → #input (tonal panes)
.agent-input__head, __body               → #input (anatomy)

.phase-rail                              → #modal (5-cell strip)
.phase-rail__cell, --done, --current     → #modal (per-phase cell)
.phase-rail__cell .ph, .name, .meta      → #modal (cell anatomy)

(.md-seg + .md-seg__opt reused for RoundScrubber options — from Spec 0093)
(.md-icon-btn reused for prev/next arrows — from Spec 0093)
```

## 4. Notion issues addressed

Implements design-system anatomy only; no Notion issue.

## 5. Acceptance criteria

- [ ] Agent-input modal renders `<div class="agent-input">` with
      exactly two `.agent-input__pane` children, one per agent.
- [ ] Each pane head carries the canonical AgentStrip + a status
      pill. Pane body is pre-formatted text in the data font.
- [ ] At <1500 px viewport, the two panes stack vertically per
      the media query rule.
- [ ] PhaseRail renders five cells (P0..P4); cells with
      completed status carry `--done`; the active phase carries
      `--current` with an info-tinted outline.
- [ ] RoundScrubber renders inside the modal footer as
      `[icon-btn ◀] [md-seg with one md-seg__opt per round]
      [icon-btn ▶] [meta caption]`. The active round opt carries
      `aria-selected="true"`.
- [ ] Prev/next icon buttons are 40 × 40 dp; round opts are 40
      dp tall — both align on the M3 control baseline.
- [ ] Renders correctly in dark and light without per-theme
      overrides.

## 6. Visual verification matrix

- `2200×1300 dark` — open the agent-input modal on a timeline
  turn that has a paired counterpart. Capture the modal with
  RoundScrubber visible in the footer.
- `2200×1300 light` — same.
- `1400×900 dark` — same; verify panes still side-by-side at
  this width (stack threshold is <1500 px in the design system
  spec, but the bundle rule
  [v2-m3-page.css:310](docs/design-system-v2/assets/styles/v2-m3-page.css)
  uses the same `max-width: 1499px` breakpoint — at exactly
  1400 dp the panes stack).
- `1400×900 light` — same.
- `820×1180 dark` — single column; verify the modal sizes to
  fit and the PhaseRail wraps to 2 + 2 + 1 (or stacks per the
  responsive grid).
- `820×1180 light` — same.

All six required.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database.
- [ ] No emoji as icons.
- [ ] No off-grid spacing.
- [ ] No hex codes in component CSS.
- [ ] No per-theme overrides for component selectors.
- [ ] Reduced-motion contract preserved.
- [ ] Focus ring visible on every focusable.

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0100-consumption-pane-m3-rework.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** The agent-input modal reads the existing per-turn input
bundle the backend already emits. PhaseRail reads phase state
from the existing run snapshot. RoundScrubber reads rounds from
the existing per-phase turn list. **Degrade gracefully:** if a
phase emits no turns, the cell renders queued (no outline, no
tint). If a round is missing from the scrubber array (e.g. one
agent ahead), render the cell as `disabled` rather than skip it.

## 11. CSS class anchor list

```
.agent-input                             → #input (two-column grid container)
.agent-input__pane, --a, --b             → #input (tonal panes, agent-tinted outline)
.agent-input__head                       → #input (pane head — AgentStrip + status)
.agent-input__body                       → #input (preformatted input bundle)

.phase-rail                              → #modal (PhaseRail strip)
.phase-rail__cell                        → #modal (one cell per phase)
.phase-rail__cell--done, --current       → #modal (status-tinted cells)
.phase-rail__cell .ph, .name, .meta      → #modal (cell anatomy)

(uses .md-seg + .md-seg__opt + .md-icon-btn from Spec 0093 for the RoundScrubber)
```
