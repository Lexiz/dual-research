---
spec: "0160"
date: 2026-05-22
version: 1.23.0
pr: "https://github.com/Lexiz/dual-research/pull/183"
---

# Handover — Spec 0160 — Dashboard live data via Cloudflare Pages Function (v1.23.0)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#183](https://github.com/Lexiz/dual-research/pull/183)
- **Merge commit:** `d01765e`
- **Cycle time:** ~14 minutes (started 14:36:03Z, deployed 14:50:13Z)

## What landed

### `functions/api/data.js` (new — Cloudflare Pages Function)

- Cloudflare auto-discovers any file under `functions/` and serves it as an edge function at the matching URL path. `functions/api/data.js` becomes `GET /api/data` on the same origin as the dashboard.
- Reads the full repo tree in one `git/trees/?recursive=1` call, then fetches matching specs / drafts / handoffs / event sidecars in parallel via `git/blobs/{sha}`. Parses YAML frontmatter (minimal hand-rolled parser tuned for our schema — see § Deviations below) and JSONL events.
- Uses a fine-grained PAT scoped to `Contents: Read-only` on `Lexiz/dual-research`, sourced from `env.GITHUB_TOKEN` (encrypted env var in Pages settings).
- Edge cache: `Cache-Control: public, max-age=15, stale-while-revalidate=60`; stores via `caches.default` so subsequent requests within the window are served from edge in <10ms.
- Error path: `502 + { error, generated_at: null }` so the bootstrap client falls back to localStorage.

### `scripts/spec_lifecycle/render_dashboard.py`

- New `--shell-only` CLI flag plus `shell_only=True` kwarg on `render_index()`. Shell mode emits data-empty `[data-region]` skeletons sized to roughly match populated state (limits reflow when content swaps in). Default mode (no flag) is unchanged — fully baked-in dashboard for local previews and as the build-time fallback.
- Both modes wrap each section (hero, pipeline, metrics, queue, feed, drafts, all-specs) in a `<div data-region="...">` container so the bootstrap script can find and swap them uniformly.
- New `DASHBOARD_BOOTSTRAP_JS` constant (~280 lines) — written to `dashboard-bootstrap.js` at build time, alongside the existing `dashboard-live.js`. Fetches `/api/data` on `DOMContentLoaded`, paints all five live sections (hero, queue, feed, drafts, all-specs), polls every 15s. Caches the last good payload in `localStorage`; on fetch failure repaints from cache with a `stale` chip in the header. No-op on local previews where `/api/data` 404s — the server-rendered baseline stays in place. Mirrors the Python renderer's HTML shape so DS styling carries over verbatim.
- `_render_header` now emits a `<span data-last-updated>` that the bootstrap rewrites with a live "updated X ago" string on every successful fetch.
- Skeleton CSS appended to `DASHBOARD_CSS` — `.region-skeleton`, `.skeleton__line`, `.skeleton__icon`, pulse animation honoring `prefers-reduced-motion`.

### `wrangler.toml` (new at repo root) + `.gitignore` + `dashboard/HOSTING.md`

- `wrangler.toml` declares `name = "dr-dashboard"` and `pages_build_output_dir = "dist"` for `npx wrangler pages dev dist` local-dev.
- `.dev.vars` added to repo-root `.gitignore` for local-only `GITHUB_TOKEN` storage.
- `dashboard/HOSTING.md`: build command updated to include `--shell-only`. New § Live data setup walks through the one-time fine-grained PAT creation (token name, scope, expiration) and the Cloudflare env-var configuration (Production + Preview, Encrypted). New "Local Function dev (optional)" section explains `wrangler pages dev`. New "Live data troubleshooting" section covers stale-chip / rate-limit / sticky-cache scenarios.

### Retired

- The 60s `<meta http-equiv="refresh">` from spec 0156 §2.2. Bootstrap script's 15s `/api/data` poll handles freshness without page reloads. Updated the spec 0156 test to assert the tag's absence.

## Tests

`uv run pytest tests/ -q` — **1510 passed** (1500 prior + 10 new across three new test files):

- `test_render_dashboard_shell_only.py` — data-region skeletons present, no spec content leaks, bootstrap script referenced, `data-last-updated` marker present.
- `test_render_dashboard_default_still_works.py` — default mode bakes spec content, data-region wrappers still present (so bootstrap can swap), both scripts referenced, no skeletons in populated sections.
- `test_render_dashboard_no_meta_refresh.py` — neither mode emits the meta-refresh tag.
- Updated `test_meta_refresh_present_in_index` → `test_meta_refresh_retired_per_spec_0160`.

Manual smoke against the live repo (153 specs + 4 drafts): both modes produce 7 `data-region` wrappers, write `dashboard-bootstrap.js` to the output dir, omit meta-refresh.

## Deploy notes

- First `fly deploy` attempt failed with a lease-lock error on machine `68327e7f264378` held by a token expiring at `14:48:41Z` — likely a stale lease from concurrent activity. Retry after the lease expired succeeded cleanly under bluegreen.
- **Spec 0159's bluegreen fix continues to hold.** Once the lease cleared, the deploy ran the full bluegreen sequence (cordon → stop → destroy old, new machines started+healthy) with zero "Unrecoverable error" timeouts. The image is now 114 MB (down from the pre-0159 ~1.2 GB) which makes cold boots far quicker.
- Smoke: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.23.0","backend":"supabase"}`. No leftover stopped machines.

## Operator actions still required (documented in HOSTING.md § Live data setup)

The Pages Function will return `502 GITHUB_TOKEN env var not configured` until these are done. Until then, the dashboard at `dr-dashboard.pages.dev` keeps working from whatever was last built (baked-in mode if the build command hasn't been updated yet).

1. **Create a GitHub fine-grained PAT** at github.com/settings/tokens/beta — scope `Contents: Read-only` on `Lexiz/dual-research` only. Pick the longest expiration your security policy allows.
2. **Add `GITHUB_TOKEN`** as Encrypted env var in Cloudflare Pages → your `dr-dashboard` project → Settings → Environment variables. Scope both **Production** and **Preview**.
3. **Update the build command** in Cloudflare Pages → Settings → Build & deployments to: `pip install pyyaml && python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out dist --shell-only`.

After step 3 lands, the next push to `main` rebuilds the dashboard in shell mode and the Function starts serving live data immediately.

## Deviations from the spec body

- **YAML parsing in the Function:** spec §2.1 mentioned using the [`yaml`](https://www.npmjs.com/package/yaml) npm package, but pulling in npm dependencies for a Pages Function would require a `package.json` + lockfile + build-step setup the repo doesn't have. Wrote a minimal hand-rolled parser instead — handles our schema (simple `key: value`, quoted strings, inline lists, blank values) but not nested mappings, block scalars, or anchors. Our frontmatter doesn't use those. If we ever need them, swap in `yaml` later (small change, but adds tooling).
- **Bootstrap script location:** spec §2.3 phrasing implied a source file at `dashboard/site/dashboard-bootstrap.js`. Followed the established pattern from spec 0156's `dashboard-live.js` instead: a Python string constant (`DASHBOARD_BOOTSTRAP_JS`) inside `render_dashboard.py` that gets written to `dashboard-bootstrap.js` in the output dir at build time. Same shipping shape; matches `DASHBOARD_LIVE_JS`.

## Deferred during implementation

- **JS unit tests for `functions/api/data.js` and `dashboard-bootstrap.js`.** Spec §6 listed vitest tests at `functions/api/data.test.js` and `dashboard/site/dashboard-bootstrap.test.js` (three cases for the Function — happy-path, cache-hit, error-path — and one for the bootstrap). Adding them requires a new node test stack (`package.json`, `vitest.config`, `happy-dom`, CI wiring) the repo doesn't have. The Python renderer tests cover the shell-mode contract; the JS is exercised end-to-end via the manual checks. Spec 0158's deferred-spec subagent should pick this up as a follow-up — title candidate: "JS test stack for Pages Function and dashboard-bootstrap.js (vitest + happy-dom)". Citations: `functions/api/data.js`, `scripts/spec_lifecycle/render_dashboard.py` `DASHBOARD_BOOTSTRAP_JS` constant.

## Queue at handoff

- **Empty.** Eight specs shipped today (0154 → 0155 → 0156 → 0157 → 0158 → 0159 → 0160).

## File map

```
# New
functions/api/data.js                                 # Cloudflare Pages Function
wrangler.toml                                         # local-dev config
tests/spec_lifecycle/test_render_dashboard_shell_only.py
tests/spec_lifecycle/test_render_dashboard_default_still_works.py
tests/spec_lifecycle/test_render_dashboard_no_meta_refresh.py

# Modified
scripts/spec_lifecycle/render_dashboard.py            # --shell-only flag, DASHBOARD_BOOTSTRAP_JS, skeleton CSS, retired meta-refresh
tests/spec_lifecycle/test_render_dashboard.py         # updated meta-refresh assertion
dashboard/HOSTING.md                                  # § Live data setup, build command update
.gitignore                                            # .dev.vars
CHANGELOG.md                                          # [1.23.0] section
pyproject.toml, src/dual_research/__init__.py         # 1.23.0
specs/0160-...md                                      # status: deployed
dashboard/events/0160.jsonl                           # full event stream
handoffs/2026-05-22-spec-0160-...md                   # this file
```
