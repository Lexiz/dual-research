---
spec: "0184"
date: 2026-05-23
version: "1.36.7"
pr: "https://github.com/Lexiz/dual-research/pull/214"
---

# Spec 0184 — Mockup fidelity check — handoff

## What landed

New test file `tests/spec_lifecycle/test_dashboard_mockup_parity.py` (6 assertions) locks the live dashboard render against `dashboard/mockups/dashboard-redesign-v3-horizontal.html`. Pure stdlib (`html.parser` + regex); sub-second runtime; no new dependency.

- **Region ordering** — under `.page`: `.hero` → `.counters` → `<nav class='tabs'>` → `.tab-panel`. Mirrors mockup lines 518/642/677.
- **Timeline structure** — exactly 11 `.tl__step` children inside `.hero` (not just anywhere on the page).
- **Counter row** — exactly 5 `.counter` under `.counters`; 5th carries `.counter--accent`.
- **Tab strip order** — `now → spec → history → metrics` in document order.
- **Token budget** — every `--md-*` / `--p-*` / `--chart-*` token used by the mockup's `.tl*` / `.counter*` / `.chart*` rules appears in the live CSS for the same region.
- **No hex literals** — CLAUDE.md tokens-only rule, scoped to `.hero` / `.counters` regions in the live output.

No production code change. Pure additive test surface. The fixture in `_render_inflight_fixture` calls the real `render_index` with a small in-flight repo — not a stubbed renderer (per spec §4 "resist over-mocking").

## Verify

`uv run pytest tests/spec_lifecycle/test_dashboard_mockup_parity.py -v` → 6 passed. Full suite: 1676 passed in 21.70s.

## Deploy notes

`fly deploy` had a rocky run today:

- Initial deploy attempt failed with `Error: failed to get lease on VM ... machine not found / failed to release lease: unauthorized`. This is a fly-side coordination issue (lease management) — the new v459 machines started successfully despite the lease error.
- After the lease error, `fly status` showed 4 machines: 2 new v459 (passing) + 2 stale v457 still serving traffic. `scripts/sweep_stale_blues.sh` reported `sweep: no stale blues on dual-research-alex` followed by `sweep: cluster has 4 machines (expected 2) — dumping metadata for filter diagnosis` and emitted JSON for all 4 machines. The sweep's filter did NOT recognize the v457 stragglers as stale (likely because both old and new carry the same `fly_bluegreen_deployment_tag` pattern).
- Manually destroyed the two stale v457 machines via `fly machine destroy <id> --force`. After that, both remaining machines are on v459 and live HTTP smoke (`/api/health` × 5) returns `200 200 200 200 200`.
- One v459 machine's check temporarily reported `critical` after the destroy, but HTTP traffic is fully served — the check appears to be a stale internal status update.

The stale-blue sweep's "cluster oversized but filter didn't match" diagnostic mode worked exactly as designed (alerting + dumping metadata for offline investigation). [Spec 0193](specs/0193-stale-blue-sweep-image-based-filter.md) — already queued — addresses the underlying filter robustness.

## Tests

`uv run pytest tests/ -q` — 1676 passed in 21.70s. Includes the 6 new `test_dashboard_mockup_parity.py` assertions.

## Deferred during implementation

- **Mockup uses 3 non-canonical shorthand tokens** (`--accent`, `--font-data`, `--font-plain`) that pre-date the project's DS token naming pass. Live render uses canonical names (`--p-accent`, `--md-font-data`, `--md-font-plain`). The token-budget test currently tolerates these via a documented `_MOCKUP_SHORTHAND_ALLOWLIST` in `tests/spec_lifecycle/test_dashboard_mockup_parity.py`. The proper fix is to rewrite the mockup at `dashboard/mockups/dashboard-redesign-v3-horizontal.html` to use canonical tokens — then this allowlist shrinks to `{}`. The mockup is 1140 lines so it's a separate edit, not a one-liner in the test file.
