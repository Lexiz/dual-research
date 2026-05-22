---
spec: "0161"
date: 2026-05-22
version: 1.23.1
pr: "https://github.com/Lexiz/dual-research/pull/184"
---

# Handover — Spec 0161 — JS test stack for Pages Function and dashboard-bootstrap.js (v1.23.1)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#184](https://github.com/Lexiz/dual-research/pull/184)
- **Merge commit:** `433cc5b`
- **Cycle time:** ~14 minutes (started 14:58:36Z, deployed 15:12:25Z)
- **Significance:** first spec auto-queued by the spec 0158 deferred-spec subagent, closing the loop end-to-end (spec 0160 deferred → subagent queued 0161 → 0161 shipped).

## What landed

### Test surface — 5 new cases

- **`functions/api/data.test.js`** (vitest, node env) — 4 cases:
  - **Happy path** — mocked `fetch` returns a tree + per-blob fixtures (two specs + one event sidecar), stubbed `caches.default`, `env.GITHUB_TOKEN` set. Asserts `status === 200`, `specs.length === 2`, `events["0001"].length === 1`, valid ISO `generated_at`, `cache-control` carries `max-age=15` + `stale-while-revalidate=60`, `waitUntil` was called to schedule the cache write.
  - **Cache hit** — `caches.default.match` returns a pre-built Response; handler returns it without calling `fetch`.
  - **Error case** — trees fetch returns 401; handler returns 502 with structured `{ error: <string>, generated_at: null }`.
  - **Missing GITHUB_TOKEN** — `env.GITHUB_TOKEN` absent; returns 502 with `/GITHUB_TOKEN/`-matching message (locks in the auth-precondition path from spec 0160's HOSTING.md troubleshooting).
- **`tests/js/dashboard-bootstrap.test.js`** (vitest, happy-dom env) — 1 case: boots the shell HTML from `--shell-only`, stubs `window.fetch` with a fixture `/api/data` payload (one in-progress + one queued spec), executes the bootstrap IIFE via `new Function()`, awaits paint via `vi.waitFor`. Asserts `[data-region="queue"]` has 1 row, `[data-region="hero"]` contains the in-progress spec's title and number, skeleton lines were replaced, `[data-last-updated]` was rewritten.

### Tooling — new

- `package.json` at repo root — `vitest@^1.6` + `happy-dom@^14` as **devDependencies only**. Production stays zero-dep.
- `vitest.config.js` — two environments by glob, `globalSetup` renders `--shell-only` once per session so the bootstrap test exercises the artefact the build actually ships (DASHBOARD_BOOTSTRAP_JS string constant in render_dashboard.py, written to the output dir).
- `tests/js/globalSetup.js` — spawns `uv run python -m scripts.spec_lifecycle.render_dashboard --shell-only`, exposes the tmp dir via `DR_DASHBOARD_OUT`.
- `Makefile` `test-js` target — opt-in `npm install --no-audit --no-fund && npm test`.
- `.gitignore` adds `node_modules/`, `package-lock.json`.
- Fixtures under `tests/js/fixtures/{specs,events,handoffs}/` — escape pytest's collector by living outside `tests/spec_lifecycle/`.

### Path deviation from spec body

Spec 0161 §2.3 wrote the bootstrap test at `dashboard/site/dashboard-bootstrap.test.js`. That path is gitignored as the build-output dir (`dashboard/.gitignore: site/`). Test moved to `tests/js/dashboard-bootstrap.test.js`; `vitest.config.js` updated to glob both locations. Spec's intent (test the bootstrap-script artefact) is preserved.

### Test results

- **JS suite** — `make test-js`: 5/5 pass in ~450ms.
- **Python suite** — `uv run pytest tests/ -q`: **1510 passed** (no regressions; pytest does not recurse into `tests/js/`).

## Deploy notes — bluegreen succeeded, blue cleanup deferred

The user-visible outcome is fine: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.23.1","backend":"supabase"}`. The proxy is routing to the new green machines (v278 image `deployment-01KS83SY7E234000V212QTW9Q4`).

But the deploy *flow* hit a new failure mode worth flagging — different from the 9-in-a-row pattern spec 0159 broke:

1. First `fly deploy` attempt got an Unrecoverable error during the bluegreen rollout. The build + push succeeded; the green machines came up healthy; but the cleanup phase failed to acquire a lease on the old blue machines. The lease-holder reported was `89f4c34c-532e-5ae3-939f-02646a1c5aae@tokens.fly.io` (a Fly internal automation token, not mine).
2. Two retries hit the same lease-lock pattern on different blue VMs (`78121e4a95d938`, then `185d273b411e98`, then a 408 timeout on the same), each time creating fresh green machines but failing to destroy the old blues.
3. Net cluster state at handoff: **4 machines** instead of 2 — two v273 blues still serving (but unrouted), two v278 greens routed and healthy. One stopped v274 from an earlier intermediate attempt was manually destroyed during diagnosis.

`fly status` at end-of-cycle:

```
185d273b411e98  v273  started  1/1 passing   ← stale blue, undestroyed
78121e4a95d938  v273  started  1/1 passing   ← stale blue, undestroyed
78452e0f2444e8  v278  started  1/1 passing   ← live green
d892619c5037e8  v278  started  1/1 passing   ← live green
```

User-side service is unaffected — the Fly proxy never showed degraded behavior throughout. The mess is cosmetic + slightly cost-impacting (4 machines instead of 2 on `shared-cpu-1x:512MB`).

## Open infra observations (not flagged as deferred — user decision pending)

- **Stale blue cleanup.** Manual sweep: `fly machine destroy 185d273b411e98 --force && fly machine destroy 78121e4a95d938 --force`. Both are v273 and unrouted; destroying them won't affect traffic.
- **Lease-lock pattern in bluegreen cleanup phase.** Spec 0159 broke the *cold-boot-margin* timeout pattern; this is a separate failure mode in the *cleanup* phase. May be a regression in Fly's bluegreen orchestrator, or a stale token from earlier failed attempts holding leases past their natural expiration. Worth observing across the next 2-3 deploys before deciding on a follow-up spec. If it persists, candidate mitigations include falling back to rolling deploys (giving up spec 0159's bluegreen benefit), filing a Fly support ticket, or adding a post-deploy "destroy any blue machines older than 5min" cleanup script.

These are *open observations*, not handoff-deferred items — the user explicitly asked to think about Fly separately from closing this cycle, so neither path is auto-spawning a follow-up subagent.

## Queue at handoff

- **Empty.** Nine specs shipped today (0154 → 0155 → 0156 → 0157 → 0158 → 0159 → 0160 → 0161). The spec 0158 subagent loop fired exactly once (0160 → 0161) and worked clean.

## File map

```
# New
package.json                                              # devDependencies only
vitest.config.js                                          # two-env config + globalSetup
Makefile                                                  # added test-js target
functions/api/data.test.js                                # 4 vitest cases
tests/js/globalSetup.js                                   # renders --shell-only once per session
tests/js/dashboard-bootstrap.test.js                      # 1 happy-dom case
tests/js/fixtures/specs/0001-foo.md
tests/js/fixtures/specs/0002-bar.md
tests/js/fixtures/events/0001.jsonl
tests/js/fixtures/handoffs/2026-01-01-spec-0001-foo.md

# Modified
.gitignore                                                # node_modules/, package-lock.json
CHANGELOG.md                                              # [1.23.1] section
pyproject.toml, src/dual_research/__init__.py             # 1.23.1
specs/0161-js-test-stack-for-pages-function.md            # status: deployed
dashboard/events/0161.jsonl                               # full event stream
handoffs/2026-05-22-spec-0161-...md                       # this file
```
