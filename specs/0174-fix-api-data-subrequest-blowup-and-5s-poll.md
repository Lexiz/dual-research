---
kind: dev
spec: "0174"
slug: fix-api-data-subrequest-blowup-and-5s-poll
title: "Fix: /api/data subrequest-limit blowup (502) + drop dashboard poll from 15s to 5s"
type: bug
label: bug
version_bump: PATCH
target_version: 1.30.1
status: deployed
depends_on: []
complexity: S
created: 2026-05-22
queued_at: "2026-05-22T22:10:00Z"
started_at: "2026-05-22T20:16:18Z"
merged_at: "2026-05-22T20:21:31Z"
deployed_at: "2026-05-22T20:28:10Z"
pr: "https://github.com/Lexiz/dual-research/pull/193"
handover: handoffs/2026-05-22-spec-0174-fix-api-data-subrequest-blowup-and-5s-poll.md
failure_step: ""
source_session: dashboard-refresh-investigation-2026-05-22
promoted_from_draft: ""
---

# Spec 0174 — Fix: `/api/data` subrequest-limit blowup + 5s dashboard poll

> **Type:** bug  |  **Severity:** P1  |  **Affects:** v1.30.0 (current main). The Cloudflare Pages Function at `functions/api/data.js` returns `502 — Too many subrequests by single Worker invocation` on every request. The dashboard at `https://dual-research.pages.dev/` falls back to the build-time-baked content and never refreshes — users perceive it as a static page.
> **Bump:** PATCH — bug fix that restores the dashboard's auto-refresh capability, with a one-line UX tweak (poll interval).
> **Evidence:** `curl -s "https://dual-research.pages.dev/api/data"` returns `{"error":"Too many subrequests by single Worker invocation. To configure this limit, refer to https://developers.cloudflare.com/workers/wrangler/configuration/#limits","generated_at":null}` as of 2026-05-22 21:50 UTC.

---

## 1. Reproduction

**Environment:** dual-research dashboard at `https://dual-research.pages.dev/`, v1.30.0 (current main). Browser DevTools Network tab open.

**Steps:**

1. Hard-reload the dashboard.
2. Wait 15 seconds.
3. Observe DevTools Network — `dashboard-bootstrap.js` fires a `GET /api/data` request.
4. Observe the response.

**Expected:** `200 OK` JSON payload with current `specs`, `drafts`, `events`, `handoffs`. The dashboard rebinds the `data-region` containers with fresh content.

**Actual:** `502` with body `{"error":"Too many subrequests by single Worker invocation. …","generated_at":null}`. The bootstrap script logs `[dr-dashboard] /api/data failed: http 502`, falls back to `localStorage` cache (or leaves the server-rendered initial paint in place), and never updates. Every subsequent 15s poll fails identically.

## 2. Root cause

The Pages Function fetches the repo tree once, then **one subrequest per file** for every spec, draft, handoff, and event-sidecar blob ([functions/api/data.js:111–121](functions/api/data.js)):

```js
const [specRows, draftRows, handoffRows, eventBuckets] = await Promise.all([
  Promise.all(specBlobs.map((b) => fetchBlobText(b, token)…)),
  Promise.all(draftBlobs.map((b) => fetchBlobText(b, token)…)),
  Promise.all(handoffBlobs.map((b) => fetchBlobText(b, token)…)),
  Promise.all(eventBlobs.map((b) => fetchBlobText(b, token)…)),
]);
```

At today's repo state — **~75 deployed specs + 4 queued + ~8 handoffs + ~75 event-sidecar files** — that's **~162 fetch() calls per invocation**. Cloudflare Workers / Pages Functions cap subrequests at **50 (free tier) / 1000 (paid)**. The function blows past the free-tier limit and Cloudflare returns 502 before all blob fetches complete.

This worked at the time spec 0160 shipped (small repo, ~30 specs). It silently broke as the repo grew. The dashboard kept rendering because `dashboard-bootstrap.js` falls back to the build-time-baked content on 502 — but no live updates happen.

## 3. Fix

Two coordinated changes.

### 3.1 — Switch the GitHub fetch to GraphQL (one batched request)

Rewrite `functions/api/data.js` to fetch all file contents through GitHub's GraphQL API in a **single POST request** (or 2–3 if pagination is needed). GraphQL exposes a `Repository.object(expression)` field that returns `Blob.text` for an arbitrary `<ref>:<path>` expression — we can ask for all ~162 files' contents in one query as parallel aliased fields.

**Query shape (sketch — implementer refines paginations + limits at impl time):**

```graphql
query DashboardBundle {
  repository(owner: "Lexiz", name: "dual-research") {
    spec_0163: object(expression: "main:specs/0163-push-events-to-main-during-branch-phase.md") {
      ... on Blob { text }
    }
    spec_0164: object(expression: "main:specs/0164-timeline-pane-card-chrome-and-phase-header.md") {
      ... on Blob { text }
    }
    # … one aliased field per file …
    event_0163: object(expression: "main:dashboard/events/0163.jsonl") {
      ... on Blob { text }
    }
    # … etc
  }
}
```

To know **which files exist** without exceeding the limit, the Function must first walk the repo tree (1 REST call, same as today — `/repos/.../git/trees/main?recursive=1`), then build the GraphQL query from the file list, then POST the query (1 GraphQL call). Net subrequest count: **~2** instead of ~162.

GitHub GraphQL has a **per-query field limit of ~500 fields** — well above our current ~162. If the repo grows past that, the implementer splits the query into batches of ≤ 400 fields per POST, capped at ~3 batches total even at a 1000-spec repo size.

**Edge cases:**
- Missing files (a tree entry exists but `Blob.text` returns null) → skip silently, same as the current per-file 404 handling.
- Non-UTF-8 / binary content → GraphQL returns `isBinary: true` and `text: null`; treat as missing.
- Rate-limit (5000/hour fine-grained PAT) — the GraphQL endpoint counts each query as ~1 against the rate-limit budget; way under the 5000/hr ceiling.

**Cache strategy** (preserved from spec 0160 — already in `data.js`): cache the response under `caches.default` with `max-age=15s` + `stale-while-revalidate=60s`. Even after this fix, the cache absorbs most polls so GitHub never sees them.

**Files to change:**
- [functions/api/data.js](functions/api/data.js) — rewrite the body of the post-tree-walk fetch block (lines 109–121) to POST a single GraphQL query and parse the aliased response. Keep `fetchBlobText` only as fallback if needed; otherwise delete.
- [functions/api/data.test.js](functions/api/data.test.js) — update the happy-path fixture to mock GitHub's GraphQL POST shape instead of the REST tree + per-blob fetches. The four existing test cases (happy path, cache hit, upstream 401 → 502, missing GITHUB_TOKEN) all need new fixture wiring; the assertions on the returned payload shape stay the same.

### 3.2 — Drop the dashboard poll interval from 15s to 5s

Single line in `DASHBOARD_BOOTSTRAP_JS` ([scripts/spec_lifecycle/render_dashboard.py:2104](scripts/spec_lifecycle/render_dashboard.py)):

```js
var POLL_MS = 15000;
```

Becomes:

```js
var POLL_MS = 5000;
```

**Rationale.** With the GraphQL fix, the function returns in ~300–500 ms (one tree call + one GraphQL POST), and the response is cached for 15 s anyway. A 5 s client-side poll means the user sees an update within 5 s of any change reaching `origin/main` (the live-event-push mechanism from spec 0163 lands events in ~1–2 s, so the end-to-end latency is ~5–7 s).

**Rate-limit math.** The cache header `Cache-Control: max-age=15, stale-while-revalidate=60` (per spec 0160) means most polls hit Cloudflare's edge cache and never reach the Function. At a 5 s poll, each user generates ~12 polls/min → ~3 cache misses/min → 180 cache misses/hour per user. With a 5000/hour fine-grained PAT budget, this comfortably supports ~25 concurrent users. Acceptable for a personal dashboard.

**Files to change:**
- [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py) — flip `POLL_MS = 15000` to `POLL_MS = 5000` in the `DASHBOARD_BOOTSTRAP_JS` constant.
- [tests/js/dashboard-bootstrap.test.js](tests/js/dashboard-bootstrap.test.js) — no assertion change required (the test doesn't depend on the interval value), but verify the test still passes after the rebuild.

### 3.3 — Don't touch the fallback / cache behaviour

`dashboard-bootstrap.js` already handles 502 by reading `localStorage` (per spec 0160 §3 error states). That fallback path stays — it's the safety net if the GraphQL approach ever fails the same way (e.g. a future query-field-count regression).

## 4. Out of scope

- **Pre-bundling a static `data.json` at build time.** Cleaner architectural fix (one fetch per /api/data instead of two), but loses the "live" property unless the build runs after every event push. Deferred — GraphQL gets us to ~2 subrequests, which is plenty of headroom.
- **`functions/api/data.js` rewrite to use Octokit / a GraphQL library.** The current code uses bare `fetch()` against `api.github.com`; this spec stays in that style and just changes the endpoint + payload shape.
- **Optimistic client-side merging** so the user sees events sooner than the next poll. Deferred — server-side cache + 5 s poll gets the perceived latency low enough.
- **Replacing the build-time-baked dashboard with a fully-shell-only render.** Out of scope; the spec-0160 shell-only mode already exists as the canonical build output.

## 5. Design-system gate

No UI changes. No DS work required.

## 6. Regression-prevention test

A test that **fails before this fix and passes after**:

- [ ] **Vitest** in `functions/api/data.test.js` — happy-path fixture asserts the Pages Function makes **exactly 2 subrequests total** for a fixture repo with ~10 files (`fetchMock.mock.calls.length === 2`). Before this fix, the equivalent assertion would resolve to `1 + N` where `N = file count`. The assertion locks the GraphQL-batched fetch pattern; any future regression that reintroduces per-file fetches blows the count and trips the test.

## 7. Test plan

- [ ] **Vitest: GraphQL fetch shape.** Update [functions/api/data.test.js](functions/api/data.test.js) happy-path fixture to mock GitHub's GraphQL POST. Assert: 1 tree REST call + 1 GraphQL POST + response cached. Assert `specs.length`, `events["0001"].length` matches the fixture.
- [ ] **Vitest: cache hit unchanged.** The `caches.default.match` early-return path still works — fixture caches a Response and asserts the GraphQL call is NOT made.
- [ ] **Vitest: 401 from GitHub → 502 to client.** Existing assertion preserved; only the failing endpoint URL changes (GraphQL POST URL instead of per-blob GET).
- [ ] **Vitest: missing `GITHUB_TOKEN` → 502 with helpful message.** Unchanged.
- [ ] **Manual: live deploy.** After `fly deploy` (or just Cloudflare Pages auto-rebuild from main), open `https://dual-research.pages.dev/`, hard-reload, wait 5 s. `dashboard-bootstrap.js` fires `/api/data`, response is `200 OK`, dashboard regions update with current main state.
- [ ] **Manual: poll interval.** DevTools Network tab — three `/api/data` requests within a 15 s window (5 s interval × 3).
- [ ] **`uv run pytest tests/ -q`** exits 0. `npm test` (vitest) passes.

## 8. Risks

- **GraphQL query size.** At ~162 aliased fields, the query body is ~10–15 KB. GitHub's GraphQL endpoint accepts up to 50 KB body; well under. If the repo grows past ~400 files, batch into multiple POSTs (the implementer adds a chunked-batch loop).
- **Field-name collisions.** Aliased field names must be valid GraphQL identifiers. Filenames with dashes / dots need sanitization (`spec_0163_…`). Implementer handles via a `pathToAlias(path)` helper.
- **Auth scope.** Same fine-grained PAT (`Contents: Read-only` on `Lexiz/dual-research`) works for GraphQL too — no token rotation required.
- **Rate-limit blowup if the cache breaks.** A 5 s poll with no cache = 720 polls/hour/user. If the cache header gets dropped or the edge cache misbehaves, the PAT's 5000/hour limit could be approached at ~7 concurrent users. Mitigation: keep the cache header; alert if observed cache-miss rate spikes.

## 9. Implementation steps

1. Rewrite the post-tree-walk fetch in `functions/api/data.js` to GraphQL. Single POST. Parse the aliased response.
2. Update `functions/api/data.test.js` fixtures.
3. Flip `POLL_MS = 15000 → 5000` in `DASHBOARD_BOOTSTRAP_JS`.
4. Run `npm test` (vitest). Iterate until all four functions/api tests + dashboard-bootstrap tests pass.
5. Run `uv run pytest tests/ -q`. Expect zero failures.
6. CHANGELOG entry + version bump.
