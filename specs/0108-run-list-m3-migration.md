---
spec: 0108
title: Run-list page M3 token migration
label: refactoring
version-bump: PATCH
status: proposed
target-version: 0.76.7
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0108 — Run-list page M3 token migration

> Depends on: 0092 (tokens), 0095 (md-appbar CSS), 0107 (run-detail tokens)
> Complexity: **S**
> Drive mode: **by hand** (verifier hardening still pending).

## 1. Goal

The run-list page is the first surface every user lands on. It currently uses
~48 inline v1-token references (`var(--bg-0/1/2)`, `var(--fg-0/1/2/3/4)`,
`var(--border-1/2)`, `var(--r-2)`, `var(--mono)`) across the top header, filter
strip, column-header band, row list, and footer hint. Result: the list page
reads as v1 against the rest of the M3-migrated app.

After this spec lands, every surface and on-surface colour reference inside
`run-list.jsx` reads from `--md-*` tokens, and the page harmonises visually
with the run-detail page that v0.76.4 + 0.76.6 already migrated.

## 2. Files touched

- `src/dual_research/ui/static/run-list.jsx` — token sweep across the 5 surface
  regions:
  - Header 1 (top app bar wrapper, brand pill, search input, "live" tag)
  - Header 2 (filter-tab strip)
  - Column-header band
  - List body wrapper
  - Footer hint
  - Per-row inline styles (`RunRow`, `PhaseMini`) including the run-id pill,
    topic block, phase/round labels, cost cell, chevron
  - Mapping:
    `--bg-0` → `--md-surface`,
    `--bg-1` → `--md-surface-container-low`,
    `--bg-2` → `--md-surface-container-high`,
    `--bg-3` → `--md-surface-container-highest`,
    `--fg-0` → `--md-on-surface`,
    `--fg-1` → `--md-on-surface-variant`,
    `--fg-2` → `--md-on-surface-muted`,
    `--fg-3` → `--md-on-surface-faint`,
    `--fg-4` → `--md-on-surface-decor`,
    `--border-1` → `--md-outline-hair`,
    `--border-2` → `--md-outline-variant`,
    `--r-2`     → `--md-shape-sm`,
    `var(--mono)` stays (palette-neutral font-family helper).
- `pyproject.toml` — bump `0.76.6` → `0.76.7`
- `src/dual_research/__init__.py` — same bump
- `uv.lock` — refresh
- `src/dual_research/ui/static/index.html` — cache-bust `?v=0096` → `?v=0097`
- `CHANGELOG.md` — new `[0.76.7]` entry

Notably **not** touched: any `.jsx` outside run-list, `shared.jsx`'s
StatusBadge primitive (already emits `.md-status` markup from spec 0093),
the `Tab` / `TabGroup` primitives (already M3 from spec 0095).

## 3. Acceptance criteria

- [ ] `grep -c "var(--bg-\|var(--fg-\|var(--border-" run-list.jsx` returns 0.
- [ ] `getComputedStyle(document.querySelector('main')?.parentElement || document.body)` shows the run-list page header background matches `--md-surface-container-low`, not the v1 `--bg-1`.
- [ ] Status pills in each row render via `.md-status` class — confirm at least
      6 distinct status flavours exist on the page when viewing all runs.
- [ ] `uv run pytest tests/ -q` → 924+ passed.
- [ ] No new pageerror / console-error on the run-list route in dark or light.
- [ ] Visual regression: dark + light hand-shots match the M3 surface
      hierarchy used by the run-detail page (header bar one tier above page
      surface, column header band one tier above that, rows on body surface).

## 4. Visual matrix

- `2200×1300 dark` — full list with multiple status flavours
- `2200×1300 light`
- `1400×900 dark`
- `1400×900 light`

Hand-captured via Playwright with `dr_onboarded=true` injected during init.

## 5. Backend touched?

**no.**
