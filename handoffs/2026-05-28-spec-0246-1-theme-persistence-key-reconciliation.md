---
spec: "0246.1"
date: 2026-05-28
version: "1.60.1"
pr: "https://github.com/Lexiz/dual-research/pull/283"
kind: post-deploy
---

# Spec 0246.1 — theme-persistence key reconciliation

Refactoring carve-out of spec 0246. The live app persisted the light/dark
theme under `dr.theme` (dot) while spec 0246 §2.9 / Acceptance Scenario 3 name
`dr-theme` (hyphen) — the spec corpus pointed at a key that did not exist at
runtime. Closed the divergence from the code side (the side that was wrong),
leaving spec 0246's shipped text accurate without editing it.

## What landed

- **`app.jsx` (`App()`):** module-level `const THEME_KEY = 'dr-theme'`. Initial
  read at [src/dual_research/ui/static/app.jsx:23](src/dual_research/ui/static/app.jsx)
  reads `THEME_KEY`, falls back to legacy `getItem('dr.theme')`, then defaults
  `'dark'`. The theme effect writes `setItem('dr-theme', theme)` and sweeps the
  legacy key with `removeItem('dr.theme')` on every tick (no-op after the first
  render). `body.classList.toggle('light', …)` DOM contract unchanged.
- **Regression guard:** `tests/test_spec_0246_1_theme_key.py` — 3 source-pattern
  tests: positive (`THEME_KEY = 'dr-theme'`), migration positive (`getItem('dr.theme')`
  fallback + `removeItem('dr.theme')` sweep both present), antipodal absence
  (no `setItem('dr.theme'` write remains).
- Version 1.60.0 → 1.60.1 (PATCH); CHANGELOG `### Changed` entry; version-notes
  sidecar regenerated.

## Verification

- `uv run pytest tests/ -q` — 2359 passed.
- GH Actions `deploy.yml` run 26596817608 concluded `success`; v1.60.1 live.
- Live smoke on `https://dual-research-alex.fly.dev/app.jsx`: `THEME_KEY = 'dr-theme'`
  present (1), `getItem('dr.theme')` fallback present (1), `removeItem('dr.theme')`
  sweep present (1), `setItem('dr.theme'` absent (0). Full migration anatomy live.

## Notes

- No spec 0246 file edit (per §2.2) — the runtime now matches what 0246 already
  says. No server / schema impact (localStorage is per-browser client state).
- Out-of-scope items from the spec (§5) remain out of scope: editing 0246's body,
  and consolidating the other `dr_*` keys (`dr_onboarded`, `dr_tour_step`) onto
  one namespace convention. Neither is a deferral from this cycle — both were
  declared out of scope at spec time.
