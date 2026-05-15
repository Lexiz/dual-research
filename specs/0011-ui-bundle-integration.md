---
spec: 0011
title: UI bundle integration
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.12.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/11"
---

# Spec 0011 — UI bundle integration

## Context

Spec 0009 produces UI-shaped `Run` objects; spec 0010 serves them over HTTP and SSE. This spec drops the Claude Design React prototype from `~/Trimble/handoff/` into `src/dual_research/ui/static/` and wires it to the live API. End state: `dual-research serve` opens a browseable URL that shows real runs from disk.

## Proposed change

### Copy the prototype into the package

```
src/dual_research/ui/static/
├── index.html
├── theme.css
├── shared.jsx
├── live-data.jsx        ← replaces the prototype's data.jsx
├── run-detail.jsx
├── run-list.jsx
├── errors.jsx
├── design-language.jsx
├── tweaks-panel.jsx
└── app.jsx
```

Prototype files copied verbatim except for `app.jsx` (live data + URL routing) and `data.jsx` → `live-data.jsx` (live hooks instead of scenario constants).

### `live-data.jsx` — replace mock data with live hooks

The prototype's `data.jsx` exports seven scenario constants (`PHASE_1_RUN`, `PHASE_2_RUN`, …, `RUN_LIST`) onto `window`. Live build replaces these with two hooks:

- `useLiveRun(runId)` → `{ run, connected, error }`
  - Initial fetch: `GET /api/runs/{id}`
  - Live updates: `EventSource('/api/runs/{id}/stream')` listening for `snapshot` events
  - Returns a single mutable run object; React re-renders on each snapshot
  - `connected` flips to false on disconnect, back to true on reconnect
- `useRunList()` → `{ rows, connected }`
  - Initial fetch: `GET /api/runs`
  - Polls every 3 seconds (no global SSE endpoint in v1, per spec 0010)
  - `connected` is true when last fetch < 5s ago

`PHASES` (the static array used for the 6-dot strip) stays as before. The mock `INPUT_BRIEF`, `TOPIC`, `TURN_HISTORY` constants are removed — components that referenced them now read from the live run object.

### `router.jsx` — URL hash routing

The prototype switches views through a tweak (`t.view`). Live build reads/writes `window.location.hash`:

- `#/` (default) → All runs view
- `#/runs/<run_id>` → Run detail view
- `#/language` → Design language page

Listens for `hashchange`. Clicking a row in `RunListView` sets the hash to `#/runs/<id>`. The "view tabs" in the top chrome update the hash.

### `app.jsx` — minimal rewrite

- Remove `SCENARIOS` and the scenario tweak
- Wrap with `useRoute()` (from `router.jsx`) to drive view + run id
- For detail view: call `useLiveRun(runId)` and pass to `<RunDetail>`
- For list view: call `useRunList()` and pass to `<RunListView>`
- Connected indicator in the top chrome reads from the active hook's `connected`
- Keep the theme toggle and the tweaks panel (stream-speed slider only — the dev-only knob)

### Per-turn body fetching

`ArtifactCard` in `run-detail.jsx` expands on click. For past turns, fetch the body lazily:

```js
const [body, setBody] = useState(initial);
useEffect(() => {
  if (open && !body && filePath) {
    fetch(`/api/runs/${runId}/files/${filePath}`)
      .then(r => r.text()).then(setBody);
  }
}, [open]);
```

The `filePath` per turn is derived from `(phase, agent, round)` using the on-disk naming convention (`phase2/round-03-claude.md`, `phase1/draft-openai.md`, `final.md`, etc.). Server-side path is scoped to the session dir; spec 0010 enforces this.

### Markdown rendering

Prototype already uses `marked@14.1.4` via jsdelivr, scoped to `.md` styles in `theme.css`. No change needed. The README §9 noted DOMPurify is not used; we accept that for v1 (single-user local app; agent output trusted).

### Brand glyphs

Keep the prototype's abstract placeholder glyphs in `AgentIcon`. Out-of-scope for v1.

### `index.html` — load order

```html
<script type="text/babel" src="tweaks-panel.jsx"></script>
<script type="text/babel" src="shared.jsx"></script>
<script type="text/babel" src="live-data.jsx"></script>   <!-- was data.jsx -->
<script type="text/babel" src="router.jsx"></script>     <!-- new -->
<script type="text/babel" src="run-detail.jsx"></script>
<script type="text/babel" src="run-list.jsx"></script>
<script type="text/babel" src="errors.jsx"></script>
<script type="text/babel" src="design-language.jsx"></script>
<script type="text/babel" src="app.jsx"></script>
```

The CDN dependencies (React 18, Babel standalone, marked) stay as-is. No build step in v1.

### `pyproject.toml` — package the static dir

Add to `[tool.uv.build]` (or equivalent) so `src/dual_research/ui/static/**` ships with the wheel. Actually since this is `uv_build` and we use src-layout, it ships by default — no config change needed; verified empirically.

### Tests

The static bundle has no Python unit tests (no business logic in JSX). Manual verification through the preview tool:

- Boot `dual-research serve --port 6173`
- `preview_start` against `http://127.0.0.1:6173/`
- Walk through: list view → row click → detail view → expand a turn → expand a disagreement → switch to design language → back to list
- Screenshot each screen and attach to the PR

The 200 existing Python tests must still pass.

### CHANGELOG + version bump

`0.11.0 → 0.12.0`. Entry documents the URL and the workflow (run `serve`, open browser).

## Out of scope

- **Production build (Vite / esbuild).** Stays CDN React + Babel for v1. Faster page loads / hot reload would go in a follow-up if and when needed.
- **Auth.** Still localhost only.
- **Keyboard navigation / ARIA.** README §8 explicitly lists this as a minimum-viable area; spec 0011 ships the prototype's existing handling unchanged.
- **In-run errors filter chips.** Existing in `RunErrorsView` per the README §8 follow-up note.
- **Token-by-token streaming.** Backend doesn't emit deltas; out of scope here.
- **Real brand icons.** Placeholder glyphs until licensed SVGs are approved.

## Test plan

- [ ] 200 existing Python tests still pass
- [ ] `dual-research serve` boots; `curl http://127.0.0.1:6173/` returns the bundle HTML
- [ ] All runs view renders 9 fixture rows from the local `runs/` dir
- [ ] Clicking a row navigates (hash updates, detail view loads)
- [ ] Detail view shows topic, phase strip, agents, disagreements, errors
- [ ] Connected indicator is green when SSE is healthy
- [ ] Design language view renders (static)
- [ ] Screenshots of each view attached to the PR

## Risks

- **SSE reconnect logic.** `EventSource` auto-reconnects but with provider-controlled cadence. If the server restarts, the UI shows "disconnected" briefly. Acceptable.
- **Race between initial fetch + first SSE frame.** If the SSE snapshot arrives before the REST fetch resolves, we want the freshest one to win. Use a monotonic "last-snapshot-time" guard.
- **CDN reliability.** React 18, Babel standalone, marked, Geist all load from unpkg/jsdelivr/gstatic. If a CDN is down, the UI fails to boot. Acceptable for a local-only tool; would matter if we ever publicly hosted this.

## Open questions

None.
