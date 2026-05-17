---
spec: 0055
title: "Run list -- sort + attention promotion + filter Tabs + URL state + /-bound search"
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.53.0
created: 2026-05-17
pr: "https://github.com/Lexiz/dual-research/pull/59"
---

# Spec 0055 -- Run list rework

## Context

Ship 2 surface spec #1. The run list is the entry point for every session -- it should answer "which runs need me?" at scan distance, and let the user sort + filter + search without clicking into chrome menus.

Four V2 changes (SUR-01..04):
1. Fix PHASE column header overlap (stacking-context).
2. Sortable columns + URL-persisted sort state.
3. Errored / deadlocked rows get a 2 px `--err` / `--warn` left border.
4. Attention-first variant: lead with errored/deadlocked rows + inline blocking-item callout.

Plus `/`-bound search focus + Tab system wrap in `<TabGroup>`.

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **Fix PHASE column header overlap** (SUR-01). The bespoke grid header is a `div` with inline styles. Inspected: no stacking-context bug present on current main (SPEC-0053 already fixed the header row with `background: var(--bg-2)` + `border-bottom: 1px solid var(--border-2)`). Verified -- no action needed beyond confirming. | Already fixed by SPEC-0053's CMP-11 table header distinction work. |
| D2 | **Sortable columns** (SUR-02) on Run ID, Status, Topic, Phase, Started, Duration, Cost. Click column header to toggle asc/desc. Active sort column shows an arrow indicator (Mdi `sort-ascending` / `sort-descending`). Default sort: Started DESC. | Client-side sort; no backend changes. |
| D3 | **URL-persisted sort + filter + search state** -- encode as `?sort=started:desc&filter=running&q=foo`. Mount-time read; action writes via `history.replaceState`. Debounce search writes at 250ms. | No router changes; pure `window.history.replaceState`. |
| D4 | **`/`-bound search focus** -- global keydown listener on `/` focuses the run-list search input (if mounted; ignore in modals or if target is input/textarea). Search input added to header banner right side. | A11Y-04 partial. |
| D5 | **Errored / deadlocked row attention** (SUR-03) -- `--err` 2 px left border for `errored`, `--warn` 2 px left border for `deadlocked`. Other states unchanged. | Via inline style on RunRow. |
| D6 | **Attention-first variant** (SUR-04) -- when errored or deadlocked runs exist, render them in a leading "Needs attention (N)" section at the top, with inline summary (`P2 . 5/6 rounds . errored`). Others fall below in default sort. | Visual section, not separate component. |
| D7 | **Filter Tabs in TabGroup** -- wrap existing Tab strip in `<TabGroup>` per SPEC-0053. Already using `<Tab>` primitives; just needs the group wrapper. | Adopts SPEC-0053 TabGroup. |
| D8 | **No backend changes.** All sort + filter + search client-side. | Scope discipline. |
| D9 | **Cache-bust `?v=0055`** in index.html. | Per arc convention. |

## Files touched

- `src/dual_research/ui/static/run-list.jsx` -- sortable columns, URL state, attention promotion, `/`-search focus, search input, TabGroup wrap.
- `src/dual_research/ui/static/components.css` -- attention row border styles (`.rl-row-err`, `.rl-row-warn`).
- `src/dual_research/ui/static/index.html` -- cache-bust.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- **Cross-run dashboards** (Compare, Search) -- SPEC-0060.
- **Full keyboard contract** (arrow-key navigation in run list, j/k) -- SPEC-0059.
- **Run detail header restructure** -- SPEC-0056.
- **Backend filtering / sort** -- frontend-only.

## Out of scope -- noted for follow-up

(Nothing discovered so far.)

## Test plan

- 725 baseline pytest green (no Python changes).
- Preview-verify on `localhost:6173`:
  - Click column headers -> sort toggles asc/desc with arrow indicator.
  - URL updates with `?sort=...&filter=...&q=...`.
  - Reload preserves state from URL.
  - Errored runs have `--err` left border; deadlocked have `--warn`.
  - Attention section at top when errored/deadlocked runs exist.
  - TabGroup wraps filter tabs.
  - `/` keypress focuses search; `Esc` blurs.
- Both themes.
- Zero console errors.

## Risks

- URL state churn on search keystrokes -- mitigated with 250ms debounce.
- Attention-first re-ordering changes row positions on SSE updates -- acceptable; re-render is the right behavior.

## Brief mapping

`SUR-01` (PHASE overlap -- verified fixed), `SUR-02` (sortable + URL-persisted), `SUR-03` (errored/deadlocked left border), `SUR-04` (attention-first variant).
