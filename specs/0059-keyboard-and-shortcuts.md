---
spec: 0059
title: Keyboard contract + shortcuts overlay + search palette
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.57.0
created: 2026-05-17
pr: "https://github.com/Lexiz/dual-research/pull/63"
---

# Spec 0059 — Keyboard contract + shortcuts overlay + search palette

## Context

A11Y-03 (unified keyboard contract: arrow keys + j/k + Enter + Esc everywhere) and A11Y-04 (`?` opens shortcuts overlay, Cmd+K opens search palette, `/` focuses run-list search -- already wired in SPEC-0055).

The existing codebase has j/k navigation inside the NegotiateReviewModal (run-detail.jsx ~line 3781) and `/` to focus search in the run list (run-list.jsx ~line 141). This spec unifies keyboard interaction into a global contract and adds two new chrome surfaces: a shortcuts overlay and a command palette.

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **Global keyboard handler** in `app.jsx`. Document-level `keydown` listener dispatched via a `useKeyboardContract()` hook. Input/textarea/contentEditable exemption. | Single source of truth for all global shortcuts. |
| D2 | **`?` opens ShortcutsOverlay** -- full-page scrim listing all bindings by context. Uses the Modal primitive from SPEC-0058 (single variant). | A11Y-04 requirement. |
| D3 | **`Cmd+K` / `Ctrl+K` opens SearchPalette** -- full-page scrim with search input + filtered results from the in-memory run list. Uses Modal primitive. | A11Y-04 requirement. |
| D4 | **`/` focuses run-list search** -- already wired in SPEC-0055. This spec verifies it still works after the global handler lands. Global handler delegates to run-list's existing handler. | Sanity check. |
| D5 | **`Esc` closes overlays** -- built into Modal's existing Esc handler. Global handler does NOT close route-level views. | Standard pattern. |
| D6 | **Focus management** -- overlays capture focus on open; return to previous element on close. Leverages Modal's existing focus trap. | A11y baseline. |
| D7 | **Input/textarea exemptions** -- global bindings ignored when user is typing in an input/textarea/contentEditable. Cmd+K still fires (it's a modifier chord). | Prevent accidental navigation while typing. |
| D8 | **No backend changes.** Search palette filters client-side against in-memory run list. | Cross-run search is SPEC-0060. |
| D9 | **Existing j/k handler in NegotiateReviewModal preserved.** The per-modal handler in run-detail.jsx already has input exemptions and j/k/arrow/Enter support. It continues to work because modal Esc/focus trapping is scoped. | No regression. |
| D10 | **Cache-bust to `?v=0059`.** | Per arc convention. |

## Files touched

- `src/dual_research/ui/static/app.jsx` -- `useKeyboardContract()` hook; renders ShortcutsOverlay and SearchPalette.
- `src/dual_research/ui/static/shortcuts-overlay.jsx` -- **new file**; ShortcutsOverlay component.
- `src/dual_research/ui/static/search-palette.jsx` -- **new file**; SearchPalette component with client-side filtering.
- `src/dual_research/ui/static/index.html` -- add script srcs for new files; cache-bust `?v=0059`.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- **Cross-run search backend** (`/search` dashboard) -- SPEC-0060.
- **j/k inside QuestionThread** for walking turns -- noted for follow-up.
- **Run-list row keyboard walking** (arrow keys walk rows, Enter opens) -- the draft proposed this but it requires significant refactoring of RunListView's rendering model (no stable row refs). Deferred; the existing `/` search + click interaction is sufficient.
- **Run-detail timeline card walking** -- same issue; timeline cards don't have stable indexed refs for keyboard navigation. Deferred.

## Test plan

- 725 baseline pytest green.
- Preview-verify:
  - `?` opens shortcuts overlay; all bindings listed; `Esc` closes; focus returns.
  - `Cmd+K` opens search palette; type query filters runs; `Esc` closes.
  - `/` focuses run-list search (SPEC-0055 behavior preserved).
  - Typing in input/textarea does NOT trigger global bindings (except Cmd+K).
- Both themes.
- Zero console errors.
- `/api/health` reports 0.57.0.

## Risks

- **Browser Cmd+K conflict** -- some browsers use Cmd+K for address bar. `preventDefault()` after intercept.
- **Focus return after overlay close** -- Modal already handles this via `previousFocusRef`.

## Brief mapping

`A11Y-03` (unified keyboard contract), `A11Y-04` (`?` overlay, `Cmd+K` palette, `/` search focus).
