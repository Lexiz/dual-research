---
spec: 0110
title: Modal sizing + phase rail anchoring + button contrast + critique card layout
label: refactoring
version-bump: PATCH
status: proposed
target-version: 0.76.12
created: 2026-05-19
pr: ""
---

# Spec 0110 — Pre-test polish bundle

Four small but visible fixes the user flagged before starting full QA.

## 1. Modal sizing

Modals open at inconsistent widths. The `Input — brief` modal renders at
`560px` (the `.md-dialog--basic` max-width), while `Draft review` and
`Phase 1 draft` open at `1080px` (`.md-dialog--rich`). Inside any modal
the body sometimes leaves a large vertical gap below content.

Fixes:
- Default the Modal primitive's `variant` to `'rich'` so every modal opens
  at the wider canvas unless explicitly downsized.
- Ensure `.dr-modal-body` claims `flex: 1; min-height: 0; overflow: auto`
  so the inner content fills the vertical space between header and footer.
- Ensure the body's first child (TabContent or single-column body)
  stretches: `.dr-modal-body > * { min-height: 0; }` plus
  `.dr-modal-body > div, .dr-modal-body > article { flex: 1; }`.

## 2. Phase rail anchoring

The `F0/F1/F2/F3/F4` markers on the left rail are computed as equal-flex
segments. As phase cards expand/collapse the markers drift out of sync
with their corresponding phase headers.

Fix: move the marker INTO each `.tl-phase__hd`. The marker becomes part
of the phase header itself, so collapse state doesn't matter. Drop the
external `.tl__rail` column. Keep a thin vertical connector line via a
left border on `.tl__body` or via a wrapper element so the visual
"rail" identity remains.

Acceptance: verified across four collapse states:
- All phases collapsed
- All phases expanded
- Phase 0 + 2 + 4 collapsed, 1 + 3 expanded
- Phase 0 expanded only

In every state, the marker labelled `F<n>` must sit at the vertical
centre of its corresponding `.tl-phase__hd`.

## 3. Button text contrast

`.md-btn--text { color: var(--md-primary); }` resolves to sable
(`#d4a574`) on light surfaces — washed-out tan-on-cream. Affects the
top-bar `All runs / Compare / Search` buttons and every other text
button (`How it works`, etc.).

Fix: switch `.md-btn--text` color to `var(--md-on-surface)` so text
buttons have full text-on-surface contrast. Hover state already uses
the `::before` overlay so the affordance survives.

## 4. Critique card content layout

Inside a critique-card turn-row (`.qt-row`), the agent metadata batch
(`.qt-pill`) sits on the LEFT in a 2-column grid; the quote text sits
in the RIGHT column, indented and width-restricted. User wants the
batch on its own line and the text below using the full card width.

Fix: change `.qt-row` from grid `minmax(160px, auto) 1fr` to flex
column (stack pill on top, quote below). Drop the `<900px` media
override since the new default is single-column.

## 2. Files touched

- `src/dual_research/ui/static/shared.jsx` — Modal primitive: default
  `variant = 'rich'`.
- `src/dual_research/ui/static/components.css` — four rule changes:
  - `.md-btn--text` colour swap
  - `.qt-row` flex-column
  - `.dr-modal-body > *` stretch override
  - Drop `.md-dialog--basic { max-width: 560px }` or bump it to 1080px
    so it matches rich.
- `src/dual_research/ui/static/run-detail.jsx` — TlPhaseSection: render
  the rail marker inside `.tl-phase__hd` instead of a separate
  `.tl__rail` column. Drop the `.tl__rail` JSX from Timeline.
- `pyproject.toml`, `__init__.py`, `uv.lock`, `index.html` cache-bust
  `?v=0101` → `?v=0102`.
- `CHANGELOG.md` 0.76.12 entry.

## 3. Acceptance criteria

- [ ] Every modal opens at 1080px+ wide and ≥72vh tall.
- [ ] Modal body stretches to fill available height (no large dead
      space between content and modal footer).
- [ ] `.md-btn--text` foreground colour reads `--md-on-surface` (not
      `--md-primary`). Top-bar buttons legible on the cream chrome.
- [ ] `.qt-row` is `display: flex; flex-direction: column;` in CSS.
      Critique question turn rows show pill on top, text below using
      full width.
- [ ] Phase rail markers stay anchored to phase headers in every
      collapse state. Hand-verified via Playwright screenshots in all
      four named states.
- [ ] `uv run pytest tests/ -q` → 924+ passed.

## 4. Backend touched?

**no.**
