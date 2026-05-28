---
spec: "0246"
date: 2026-05-28
version: 1.60.0
pr: https://github.com/Lexiz/dual-research/pull/282
kind: post-deploy
---

# Spec 0246 — All Runs landing page card-layout rewrite + summary stats (v1.60.0)

## What landed

Rewrote the project's primary landing page from a flat, inline-styled table
(`RunListView`) into a card-based layout (`AllRunsPage`) per the design
handoff, plus the additive backend fields the cards need.

- **Backend (§4).** `RunListRow` gained `phases`, `rounds_completed`/`rounds_max`,
  `agents` (per-agent `cost` + chips), and `note` — all additive, with the
  spec 0245 `deleted_at`/`deleted_by` preserved. New nested dataclasses
  `AgentChip` / `AgentBreakdown` / `RunNote` in
  [`models.py`](src/dual_research/ui/models.py). Shared derivation helpers
  `derive_phase_outcomes` / `derive_agent_breakdowns` / `derive_run_note`
  (+ `_run_failed_error_type`) in
  [`aggregator.py`](src/dual_research/ui/aggregator.py), wired into both
  `summarize_run` (fs) and `_supabase_list_runs`
  ([`server.py`](src/dual_research/ui/server.py)). The phase strip reuses the
  already-computed terminal phase + status (no extra read); agent cost adds
  one `metrics.json` read; the errored-note `error_type` scan runs only for
  errored rows.
- **CSS (§2.2–2.12).** All new `.ar-*` / `.rc-*` composed components landed
  in both `composed-components.css` (authoritative) and `components.css`
  (live mirror). Tokens-only, no hex. Reused the existing `pulse-info`
  keyframe for the running ticker; added `rc-shimmer` for the active phase.
- **JSX (§2.1–2.12).** `RunListView` → `AllRunsPage` (owns its fetch). The old
  `RunRow` render body is replaced by `RunCard`. Removed the inline `/`-focus
  search. The spec 0245 archive machinery (toggle, dialogs, handlers,
  `_secondsSinceIso`) is **kept and relocated** into the card layout, not
  rebuilt. `PhaseMini` survives for the `/#/language` showcase.
  [`app.jsx`](src/dual_research/ui/static/app.jsx) suppresses the global
  `ChromeBar` on the list route and gives it full-height scroll so the new
  sticky `.ar-chrome` is the only chrome there.
- **Tests.** `tests/test_spec_0246_all_runs.py` (14 — source-pattern + data
  layer). The three spec 0245 source-pattern tests were updated to the new
  card anatomy (the affordances moved per §2.12; behavior preserved). Full
  suite: **2356 passed**.

## Runtime verification

Local server on 1.60.0; Claude Preview MCP, no console errors. Verified:
dark + light full page (theme toggle integrates with the existing app theme
system, not a parallel `dr-theme` store), `?filter=errored` (8 cards, only
Needs-attention group, stats panel still unfiltered — Scenario 4),
responsive @ 760 px (stats → 2 cols, phase chart full width). Computed-style
checks: failed phase bar = `--p-err`; agent row on `--md-surface-container`.
Live prod health = 1.60.0; `/api/runs` is auth-gated (401 unauth, expected).

## Deploy anomaly (resolved)

The merge-commit (`fdd2218`) deploy run's **test job passed but its deploy
job was cancelled** by the `deploy-main` concurrency group racing against the
rapid pre-merge `--push-to-main` queue-state commits, compounded by a
transient GitHub Actions cache-service outage ("services aren't available").
A stale ancestor queue-state run was mid-deploy of the 1.59.0 tree (it then
failed). Recovery: waited for the stale run to settle, then
`gh workflow run deploy.yml --ref main` (run `26595775343`) which deployed
main HEAD (1.60.0) cleanly. Fly confirmed at 1.60.0. A `deploy_pivoted`
event records the anomaly. See **Deferred** below — this is a recurring
class the spec 0212 buffer-events doctrine only partially covers (the
pre-merge step-18 `--push-to-main` calls still create racing runs).

## Deferred during implementation

- **Theme-toggle localStorage key divergence from the spec mock** — Spec §2.9 /
  Acceptance Scenario 3 specify persisting to `localStorage['dr-theme']`. The
  live app already owns a theme system keyed on `dr.theme` (App state +
  `body.light`), so the chrome's theme button was wired to the existing
  `onToggleTheme` rather than introducing a competing `dr-theme` store. This
  is the structurally correct choice (one theme source of truth) but diverges
  from the mock's literal key. If the exact `dr-theme` key is required, the
  follow-up is to migrate the app's theme persistence key — out of scope for
  this visual rebuild.
- **Pre-merge `--push-to-main` deploy-race hardening** — `/dev-next` step 18
  pushes the `merged` state to main via plumbing *before* `gh pr merge`,
  producing 3+ rapid main commits immediately before the merge commit. Under
  the `deploy-main` concurrency group (and especially during Actions cache
  flakiness) this can cancel the merge-commit's deploy job and leave a stale
  ancestor run deploying old code — exactly what happened this cycle. The
  spec 0212 "buffer events, no `--push-to-main` between merge and step 23"
  doctrine does not cover the *pre-merge* step-18 pushes. Candidate fix:
  fold the step-18 `merged` state write into the step-23 atomic
  `push-files-to-main` so only one main commit (the merge) triggers deploy,
  or have `/dev-next` always `workflow_dispatch` the deploy of main HEAD
  rather than racing the push-triggered runs.
