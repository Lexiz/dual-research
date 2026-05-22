---
kind: dev
spec: "0160"
slug: dashboard-live-data-via-pages-function
title: Dashboard live data via Cloudflare Pages Function
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.23.0
status: queued
queue_position: 1
depends_on: []
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T14:30:41Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: dashboard-live-data-ideation-2026-05-22
promoted_from_draft: ""
---

# Spec 0160 — Dashboard live data via Cloudflare Pages Function

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — adds a new data path (Pages Function + client-side fetch) that supersedes the static-snapshot mechanism for the dashboard's live data. No breaking changes — historical per-spec pages, renderer CLI, and local-preview flow stay intact.
> **Evidence:** dashboard at `dr-dashboard.pages.dev` shows spec 0157 as latest while 0158 is `status: deployed` (`specs/0158-deferred-spec-subagent.md` frontmatter), 0159 is merged (commit `7525a71`), and `dashboard/events/0159.jsonl` already carries the `merged` event. Source-of-truth is fresh; the build → deploy → edge-cache pipeline is the bottleneck. Spec 0156's handoff explicitly flagged this as the open follow-up: *"Dashboard hosting is broken… decide on a hosting path."*

---

## 1. Context

The dashboard is a static snapshot rebuilt by Cloudflare Pages on every push to `main` (per `dashboard/HOSTING.md`). Each `/dev-next` cycle pushes 4–6 commits in quick succession (`queued`, `start in_progress`, the PR merge, `mark merged`, `deployed v… + handoff`). Cloudflare Pages free-tier coalesces and serializes builds; the Python `pip install pyyaml && python -m scripts.spec_lifecycle.render_dashboard` build runs ~30–60s end-to-end; edge caches add propagation lag. Net effect: when cycles ship fast (spec 0157 was 5 minutes start-to-deploy), the dashboard is one or two cycles behind the repo state.

Spec 0156 §2.2 introduced a 60s `<meta http-equiv="refresh">` and a client-side ticker, which closes the *between-builds* gap but cannot compensate for the *build-not-yet-finished* gap. The fundamental architecture is "rebuild a snapshot on every commit" — improving the snapshot doesn't fix snapshot-of-stale-data. Spec 0156 §5 explicitly deferred "server-side push" as a bigger lift, but the cheaper "live-fetch via Pages Function" path was not evaluated at the time. That's what this spec does.

## 2. Proposed change

Three coupled surfaces, one coherent feature.

### 2.1 — Pages Function: `functions/api/data.js` (new)

- Cloudflare Pages auto-discovers any file under `functions/` and serves it as an edge function at the matching URL path. `functions/api/data.js` exports a `onRequest` handler reachable at `/api/data` on the same origin as the dashboard.
- Reads four directory listings from the GitHub Contents API on the private `Lexiz/dual-research` repo (`specs/`, `specs/drafts/`, `handoffs/`, `dashboard/events/`) using a `GITHUB_TOKEN` env var (fine-grained PAT with `contents:read` on this repo, configured in Pages → Settings → Environment variables → Encrypted).
- For frontmatter files: fetches each file's contents via `git/blobs/{sha}` (the trees API gives the SHA up front, so we get bulk listing + per-file SHA in one round-trip; subsequent blob fetches go in parallel via `Promise.all`).
- Parses YAML frontmatter (use [`yaml`](https://www.npmjs.com/package/yaml) — small, no native deps, works in Workers runtime) and JSONL event sidecars (one JSON.parse per line).
- Returns `application/json` of shape:
  ```ts
  {
    generated_at: ISO-8601-string,
    specs: Array<{ number, slug, title, type, status, target_version, queue_position, depends_on, complexity, queued_at, started_at, merged_at, deployed_at, pr, handover, failure_step, source_session, promoted_from_draft }>,
    drafts: Array<{ draft_id, slug, title, type, created, status }>,
    handoffs: Array<{ spec, date, version, pr }>,
    events: Record<spec_number, Array<{ ts, step, data }>>,
  }
  ```
- Response headers: `Cache-Control: public, max-age=15, stale-while-revalidate=60`. Uses Cloudflare's edge cache (`caches.default`) keyed on the request URL — first request after expiry pays the GitHub round-trip; subsequent requests within the window are served from edge in <10ms.
- Errors return a structured JSON body (`{ error, generated_at: null, last_good_url: null }`) with `502` status so the client knows to fall back to the cached state in localStorage.

### 2.2 — Renderer shell mode: `scripts/spec_lifecycle/render_dashboard.py`

- New CLI flag: `--shell-only`. When set, the renderer still produces `index.html`, `tokens.css`, `components.css`, `dashboard.css`, `dashboard-live.js`, but the page body emits *empty data containers* with `data-region` attributes instead of fully-rendered specs/drafts/handoffs/events. Per-spec `spec-NNNN.html` pages are still emitted in full (those don't need to be live — they're rarely visited mid-cycle, and `/api/data` only feeds the index).
- The default mode (no flag) is unchanged — local `uv run python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out /tmp/dr-dash` previews still produce a self-contained baked-in dashboard. This is the fallback path if the Function ever breaks: the user can rebuild locally and copy to Cloudflare manually.
- Specifically modify [`_html_head`](scripts/spec_lifecycle/render_dashboard.py) at line 342 to: drop the `<meta http-equiv="refresh" content="60">` (the JS handles refresh now, every 15s); add `<script src="dashboard-bootstrap.js" defer></script>` alongside the existing `dashboard-live.js`.
- The hero / queue / deployed / drafts sections become skeleton placeholders (e.g. `<section class="hero" data-region="hero"><div class="skeleton-line"></div></section>`) when `--shell-only` is on. These skeletons match the dimensions of the populated state so the page doesn't reflow when data arrives.
- HOSTING.md build command (line 27) updates from `python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out dist` to `python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out dist --shell-only`.

### 2.3 — Client bootstrap: `dashboard/site/dashboard-bootstrap.js` (new)

- New file (~200 lines) alongside the existing `dashboard/site/dashboard-live.js`.
- On `DOMContentLoaded`: fetch `/api/data`, render the four data-region sections into the shell DOM, then `setInterval(refresh, 15000)`.
- Render functions mirror the Python ones in `scripts/spec_lifecycle/render_dashboard.py` ([`_render_hero_idle`](scripts/spec_lifecycle/render_dashboard.py) at line 365, the queue table renderer around line 643, the deployed table around line 715). To avoid drift, the JS renderers are kept narrow: they produce HTML strings using `data-*` attributes that the existing CSS class names already style. No new CSS — same `card`, `chip`, `hero` composed components per `design-system/SPEC.md`.
- On successful fetch: write the full payload to `localStorage["dashboard-data"]` and update a `<header data-last-updated>` element with the relative time. The existing `dashboard-live.js` ticker continues to handle the per-second stage-elapsed display from `data-stage-started-at` attributes the bootstrap script puts on the hero (read from the now-current `events` array).
- On fetch failure: if `localStorage["dashboard-data"]` exists, re-render from that and show a `<span class="chip tone-warning" data-stale>stale since HH:MM:SS</span>` badge in the header. If no cached data: show a friendly empty state with the error.

### 2.4 — Hosting documentation: `dashboard/HOSTING.md`

- Append a "§ Live data setup" section explaining the one-time PAT creation (GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → New token; resource owner Lexiz; repository access `Lexiz/dual-research` only; permissions `Contents: Read-only`; copy the token).
- Cloudflare side: Pages project → Settings → Environment variables → add `GITHUB_TOKEN` as Encrypted, scope to Production and Preview.
- Local-dev section: `wrangler.toml` at repo root, plus `.dev.vars` (gitignored) for local Function testing via `npx wrangler pages dev dist`. Add `.dev.vars` to `dashboard/.gitignore`.

## 3. UX / Behavior

- **Before:** open the dashboard, see whatever Cloudflare's most recent build produced. Mid-cycle, that's often 2–5 minutes behind. Meta-refresh fires every 60s but reloads the same snapshot until Cloudflare finishes a new build.
- **After:** open the dashboard, see a skeleton for ~100–300ms, then live data populates. The header shows `last updated: 4s ago`. Every 15s the data refreshes silently (no page reload, no scroll loss). Worst-case lag is the edge-cache TTL: 15s freshness target, 60s stale-while-revalidate ceiling.
- **DS citations:** uses existing `card`, `chip`, `hero`, `stage-list` composed components verbatim — no new primitives. Skeleton placeholders use the `--md-surface-variant` token already in `design-system/assets/styles/tokens-and-primitives.css` for the loading shimmer (no shimmer animation if `prefers-reduced-motion: reduce`).
- **Error states:** Pages Function down → `stale since HH:MM:SS` chip + last-good data; GitHub API down → same; no cached data ever loaded → empty state with the error string.
- **Reduced motion:** existing `dashboard-live.js` already honors `prefers-reduced-motion`. Bootstrap script does no animation, just data swaps.

## 4. Data / Schema deltas

- No database changes. The Function reads existing on-disk files (spec frontmatter, handoff frontmatter, event JSONL) via GitHub Contents API.
- New API endpoint contract: `GET /api/data` returns the JSON shape documented in §2.1. Schema is inlined as a JSDoc type comment at the top of `functions/api/data.js`.
- New env var: `GITHUB_TOKEN` (encrypted in Pages settings, never in source).
- New gitignored file: `.dev.vars` at repo root (local Function testing).

## 5. Out of scope

- **Server-Sent Events / WebSocket push** from the fly.io app. Larger architectural lift. The 15s polling cadence achieves "feels live" without keeping a persistent connection open. Spec 0156 §5 already deferred this; this spec doesn't reverse that.
- **Moving event storage off git** (Supabase, Cloudflare KV, etc.). Loses the git audit trail. The current approach — events committed alongside frontmatter — is intentional.
- **Per-spec `spec-NNNN.html` pages reading live data.** They stay as build-time HTML. Rationale: they're rarely loaded mid-cycle, and their content (frontmatter + completed event timeline) doesn't change after deployment. Lower priority for live-ness.
- **Build-time render removal.** The Cloudflare build still runs on every push, producing the static shell + the historical per-spec pages. We're just shrinking *what* gets rebuilt to data-empty HTML.
- **Reducing `/dev-next`'s commit count.** Orthogonal to this spec — even one commit per cycle would still pay build lag under the snapshot model. Live fetch makes commit count irrelevant to dashboard freshness.
- **Auth on `/api/data` beyond the GitHub PAT.** The endpoint returns the same data anyone with the dashboard URL can see; gating it adds friction without security gain. The PAT only protects GitHub-side from anonymous Function abuse.
- **Migrating off Cloudflare Pages.** This spec uses Cloudflare's free-tier capabilities (Pages + Functions + edge cache) — no platform change.

## 6. Test plan

- [ ] Test: `tests/spec_lifecycle/test_render_dashboard_shell_only.py` — given a fixture spec set, render with `--shell-only` and assert `index.html` contains `<section ... data-region="hero">` but does NOT contain any spec number, title, or status text in the section body. Also assert `<script src="dashboard-bootstrap.js" defer></script>` is in the `<head>`.
- [ ] Test: `tests/spec_lifecycle/test_render_dashboard_default_still_works.py` — render without `--shell-only` and assert the dashboard contains the fixture spec's number and title baked into HTML (regression: local preview path unchanged).
- [ ] Test: `tests/spec_lifecycle/test_render_dashboard_no_meta_refresh.py` — assert neither shell-only nor default mode emits `<meta http-equiv="refresh">` anymore (the JS handles refresh now).
- [ ] Test: `functions/api/data.test.js` (vitest with a mocked `fetch` global) — given a mocked GitHub Contents API returning two fixture specs and one event sidecar, assert the Function returns JSON with `specs.length === 2`, `events["0001"].length === 1`, and a `generated_at` ISO string.
- [ ] Test: `functions/api/data.test.js` cache hit case — second call within `max-age` returns the cached response without re-calling fetch.
- [ ] Test: `functions/api/data.test.js` error case — mocked GitHub returning 401, assert Function returns a `502` JSON response with an `error` key.
- [ ] Test: `dashboard/site/dashboard-bootstrap.test.js` (vitest + happy-dom) — given a fixture `/api/data` JSON, assert the queue table is populated with the expected number of rows and the hero shows the latest in-flight spec.
- [ ] Manual: open `dr-dashboard.pages.dev` after a `/spec-queue` invocation; observe the new spec appearing in the queue within 30s without a page reload.
- [ ] Manual: temporarily revoke the `GITHUB_TOKEN` in Cloudflare → reload dashboard → observe the `stale since HH:MM:SS` chip and last-good data (cached in localStorage from prior session).
- [ ] Manual: open the dashboard during an in-flight `/dev-next`, leave open for the duration of a spec cycle (~5–20 min); observe stage transitions (`queued` → `cycle_started` → `branched` → … → `deployed`) appearing in the hero within ~15s of each event being committed to `main`.
- [ ] Manual: trigger a deliberate Function error (e.g. break the YAML parser); observe the dashboard falls back to localStorage data and surfaces the error in the console — no white screen.

## 7. Risks

- **GitHub API rate-limit exhaustion.** A fine-grained PAT gives 5000 req/hr. The Function makes ~1 trees call + N blob calls per cache miss. With ~230 files (159 specs + 60 handoffs + ~10 events + drafts) and 30s cache TTL, worst-case is 120 misses/hr × 230 calls = 27,600 — over the limit. Mitigation: aggressive shape change — fetch only the **changed** files between misses by tracking the trees response's `truncated` + per-path SHAs in a second cache layer; deployed-spec frontmatter changes once then never again, so its blob fetch result is cached for 1 hour (still cheap to re-verify SHA via trees). Realistic steady-state: ~30 calls per miss (current cycle's events + a handful of recent specs) × 120 misses/hr = 3600/hr — well under limit. If still too high, fall back to a Cloudflare KV cache layer with 5-minute TTL.
- **PAT leakage.** A token committed to source or exposed in client JS would let anyone read this private repo. Mitigation: HOSTING.md documents env-var-only placement; `wrangler.toml` references the secret by name (no value); `.dev.vars` added to gitignore; the Function never returns the token in error messages. The token's scope is read-only on this repo only, so worst-case leak severity is "the dashboard data was already public via the dashboard URL anyway."
- **First-paint flash of skeleton.** Users see loading skeletons for ~100–300ms before data arrives. Mitigation: skeleton shapes match populated shapes so no reflow; first fetch is over HTTP/2 to the same origin, typically <200ms; localStorage cache means returning visitors see populated data immediately (then it refreshes 15s later).
- **Pages Function runtime errors silently degrade UX.** Mitigation: client falls back to localStorage data with a "stale" chip; Function logs to Cloudflare's tail logs (`wrangler pages deployment tail`); the manual revoke-token test in §6 verifies the fallback works end-to-end.
- **Drift between Python renderer (build-time) and JS renderer (runtime).** The hero/queue/deployed render logic now lives in two places. Mitigation: keep the JS renderer thin — same CSS classes, same data attributes, no formatting logic the Python side does differently. Where formatting is shared (humanized durations, "X ago" timestamps), inline a JS port at the top of `dashboard-bootstrap.js` and assert in a test that for a fixed timestamp both sides produce identical strings. Accept that the two paths can drift on cosmetic edge cases — the Python path is only used for local previews, so any drift is a low-stakes mismatch.
- **Cloudflare Pages Functions free-tier limits.** 100,000 invocations/day on free plan, 10ms CPU per invocation. A page open for 8 hours polling every 15s = ~1900 calls/day per user. Single-user dashboard easily fits. If multi-user grows, the edge cache absorbs most hits (cache-hit responses don't count against the invocation quota).
- **Local dev requires `wrangler` + Node tooling.** New dev dependency. Mitigation: optional — tests use vitest with mocked Workers globals (no Wrangler needed for CI); only manual `pages dev` testing needs Wrangler installed locally. Document install in HOSTING.md.
