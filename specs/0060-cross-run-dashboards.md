---
spec: 0060
title: Cross-run dashboards — /compare (two-run side-by-side) + /search (cross-run query)
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.58.0
created: 2026-05-17
pr: ""
---

# Spec 0060 — Cross-run dashboards

## Context

Ship 4 spec #1. Two new surfaces (NEW-01, NEW-02) — the only specs
in the arc that add backend endpoints.

1. **`#/compare`** — two-run side-by-side dashboard. Pick run A + run B, see synced-scroll panels with per-phase comparison and a delta column for differences.
2. **`#/search`** — cross-run search dashboard. Server-side substring search across run topics, agent prose (questions), and citations. Query behaviour invisible across runs today.

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **New routes `#/compare` and `#/search`** in `router.jsx`. Both reachable from chrome bar Tab items and SearchPalette nav items. | Hash routes, same pattern as existing views. |
| D2 | **New `compare.jsx` surface** — two RunIDChip pickers at top (or pre-filled via `?a=<id>&b=<id>` hash params). Synced-scroll left+right panels render each run's phase timeline side-by-side. Delta column highlights diverged phases (different drafter, different round counts). | Client-side: fetches both runs individually via existing `/api/runs/<id>`. |
| D3 | **Synced scroll** between left+right panels. Scroll one panel, the other follows proportionally. Pure frontend scroll event listener. | Simple proportional scroll sync. |
| D4 | **New `search.jsx` surface** — full-page search input, results grouped by run with snippet + match type + click-to-jump. | Uses new `/api/search` endpoint. |
| D5 | **New server endpoint `GET /api/search?q=<query>`** — substring match across run topics, question bodies, citation URLs. Results capped at 50. Each includes `run_id`, `display_id`, `topic`, `match_type`, `snippet`, `score`. | Both fs and supabase modes. |
| D6 | **No server-side compare endpoint** — client fetches both runs via existing `/api/runs/<id>`. Simplifies scope. | MVP decision: skip D6 from draft. |
| D7 | **Heatmap / provider stats in /search** deferred. | Out of scope for MVP. |
| D8 | **Compare delta column** — narrow column between panels showing divergence markers per phase. Simple text markers. | Basic visual polish only. |
| D9 | **Cache-bust `?v=0060`** in index.html. | Per arc convention. |
| D10 | **Backend tests** for `/api/search` endpoint (~8-10 new tests). | Python tests for the new endpoint. |
| D11 | **SearchPalette + ShortcutsOverlay integration** — add Compare and Search to NAV_ITEMS and shortcut groups. | Per SPEC-0059 handover recommendation. |

## Files touched

- `src/dual_research/ui/static/compare.jsx` — **new file**; Compare surface.
- `src/dual_research/ui/static/search.jsx` — **new file**; Search surface.
- `src/dual_research/ui/static/router.jsx` — add `#/compare` and `#/search` routes.
- `src/dual_research/ui/static/app.jsx` — chrome bar Tab items + view rendering for new routes.
- `src/dual_research/ui/static/search-palette.jsx` — add Compare + Search to NAV_ITEMS.
- `src/dual_research/ui/static/shortcuts-overlay.jsx` — add `g c` / `g s` bindings (if applicable) or just nav items.
- `src/dual_research/ui/server.py` — new `/api/search` endpoint in both app factories.
- `tests/ui/test_server_search.py` — **new**; cross-run search endpoint tests.
- `src/dual_research/ui/static/index.html` — add script srcs for compare.jsx + search.jsx; cache-bust.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- **Server-side compare endpoint** — client fetches both runs individually. Follow-up if perf matters.
- **Heatmap + provider stats in /search** — deferred.
- **Search result re-ranking / ML-quality scoring** — substring match with simple score.
- **Compare delta animation / diff highlighting** — basic markers only.
- **Bookmarkable compare URLs across users** — local URL state only.
- Noted for follow-up: full-text search index if run count exceeds ~100.

## Test plan

- 725 + ~8-10 new tests — all green.
- Preview-verify:
  - Navigate to `#/search` -> input renders -> query "partner" -> results from partner-vetting run.
  - Click a result -> navigates to that run-detail.
  - Navigate to `#/compare` -> two pickers -> select runs -> side-by-side renders.
  - Synced scroll works.
  - Delta column shows divergence markers.
- Both themes.
- Zero console errors.
- `/api/health` reports 0.58.0.

## Risks

- **Largest scope in arc** — two new surfaces + new endpoint. Mitigation: MVP approach (simple substring search, client-side compare with proportional scroll).
- **Performance** of cross-run search on large run sets — current dataset is ~13 runs; trivial.

## Brief mapping

`NEW-01` (Compare two runs `#/compare`), `NEW-02` (Cross-run search dashboard `#/search`).
