---
spec: 0079
title: Hosted UI modal-load perf — warm machine, gzip, immutable cache headers, server-side LRU
label: bug
version-bump: PATCH
status: merged
target-version: 0.69.3
created: 2026-05-18
pr: "https://github.com/Lexiz/dual-research/pull/79"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0079 — Hosted UI modal-load perf

## Context

On the hosted UI (`https://dual-research-alex.fly.dev`), clicking any
card in the timeline of a run-detail page opens a modal that shows the
full per-turn **input bundle** (system prompt + prior turns + brief +
tool outputs — i.e. exactly what was fed into the LLM for that
specific turn). Users report this modal sits on a loading spinner for
"excruciatingly long" before the content appears. The same complaint
applies to the per-turn **search-audit** view that the modal also
fetches.

Spec 0078 fixed an unrelated regression (Fly VM OOM-on-boot) that was
producing 502s across the whole `/api/*` surface. With the server now
serving 200s, the underlying per-request latency is now visible — and
it's the actual issue this spec addresses.

### Where the time is spent

Per-modal-open the frontend hits at least two endpoints, both of which
read from Supabase via the same shape of query
([server.py:942](src/dual_research/ui/server.py:942),
[server.py:857](src/dual_research/ui/server.py:857)):

```sql
SELECT content FROM session_files
WHERE run_id = ? AND path = 'inputs/{key}.json' LIMIT 1
```

The `content` column is a TEXT blob holding the **entire** per-turn
input bundle JSON. For a prod-tier 1 M-context run this is routinely
**hundreds of KB to a few MB** of JSON for a single turn. Four
compounding sources of latency:

1. **Cold-start (largest, intermittent).** `fly.toml` has
   `auto_stop_machines = "stop"` + `min_machines_running = 0`. After
   ~5 min idle the machine halts; the first click pays the full
   Python 3.14 + supabase-py + fastapi import cost — **30–60 s** end
   to end. This is what the user feels as "excruciatingly long" on
   their first interaction.
2. **No server-side caching.** Every modal re-open re-queries
   Supabase. Open the same card twice → same Supabase round-trip
   twice. No in-memory LRU on the server, no memoisation across
   sessions.
3. **No HTTP compression.** No `GZipMiddleware` is attached to the
   FastAPI app. A 500 KB JSON payload that would gzip to ~50 KB is
   currently shipped uncompressed over the wire.
4. **No browser-cache hints.** Responses omit `Cache-Control`, so
   every modal re-open re-issues a network request even when the
   browser already has the bytes in memory or disk.

Two-hop network (browser → Fly `iad` → Supabase → Fly → browser) makes
each of the above worse; we can't change the hops but we can minimise
how often they're traversed and how big the payload is.

## Proposed change

Three independent sub-changes. Any one of them is a measurable win;
all three combined should move modal-open from "tens of seconds" to
"<200 ms warm, ~1–2 s cold".

### Change 1 — Keep one machine warm

**`fly.toml`**:

```diff
 [http_service]
   internal_port = 8080
   force_https = true
   auto_stop_machines = "stop"
   auto_start_machines = true
-  min_machines_running = 0
+  min_machines_running = 1
   processes = ["app"]
```

One machine stays running at all times; the second auto-starts under
load (concurrency `soft_limit = 50`) and auto-stops when idle. This
eliminates the 30–60 s cold-start hit for the first interactive click
after an idle period.

Expected additional cost: ~$2–4/month on `shared-cpu-1x:512MB`. Small
enough not to require a separate Open Question.

### Change 2 — Gzip middleware

**`src/dual_research/ui/server.py`** in `_make_supabase_app`:

```python
from fastapi.middleware.gzip import GZipMiddleware
...
app = FastAPI(...)
app.state.backend = "supabase"
app.add_middleware(GZipMiddleware, minimum_size=1024)  # NEW
app.add_middleware(SupabaseAuthMiddleware, client=client)
```

`minimum_size=1024` skips compression for tiny responses (auth errors,
health checks) where the CPU cost would dominate. Input-bundle and
search-audit responses are routinely 100 KB+, so they always compress.
Expected wire-size reduction: **5–10×** on JSON payloads, **3–5×** on
markdown bodies.

Apply the same middleware to `_make_app` (filesystem mode) for parity;
local users benefit too even though the wire is loopback.

### Change 3 — Immutable Cache-Control + server-side LRU on immutable endpoints

Two endpoints are immutable-once-written for a given run + key. Once
a turn's bundle exists in `session_files`, it never changes (retries
get new turn keys; runs are append-only). They are:

| Endpoint                                          | Helper                              |
| ------------------------------------------------- | ----------------------------------- |
| `GET /api/runs/{run_id}/inputs/{turn_key}`        | `_read_input_bundle_supabase`       |
| `GET /api/runs/{run_id}/searches/{turn_key}`      | `_read_search_audit_supabase`       |

The generic `/api/runs/{run_id}/files/{path:path}` endpoint serves both
immutable artifacts (`phase*/...md`, `final.md`, `brief.md`) AND mutable
ones (`transcript.jsonl`, `state.json`, `metrics.json`), so it's left
out of this scope to avoid a path-classification footgun. Gzip applies
to it regardless via the middleware. A path-filtered Cache-Control pass
can land in a follow-up if perf data shows it's worth the complexity.

**Browser-cache hint** — emit on these two responses only:

```
Cache-Control: public, max-age=86400, immutable
```

The `immutable` directive tells well-behaved browsers to skip even
conditional `If-Modified-Since` revalidation for the freshness window
— a click-and-reopen within 24 h costs zero network bytes.

**Server-side LRU cache** — wraps the two reads above, keyed by
`(run_id, key)`. Bounded size + size-aware eviction:

- Max **100 entries** per cache (one per endpoint, two caches).
- Entries are JSON strings/dicts cached at the helper-return level —
  serialisation cost is paid once per entry.
- Threading: use `cachetools.LRUCache` wrapped in a `threading.Lock`,
  or hand-rolled `OrderedDict` + lock. Implementation detail; the
  spec mandates the contract, not the library. (We add `cachetools`
  to `pyproject.toml` only if hand-rolling proves clumsy.)
- Eviction is purely LRU on count; no TTL. Bundles are immutable, so
  the only invalidation needed is **process restart** — which already
  happens on every deploy and machine restart.
- Memory budget: assume worst case 500 KB per entry × 100 entries × 2
  caches = **100 MB**. Fits inside the 512 MB VM (spec 0078) with
  headroom for fastapi + uvicorn + Python heap + the 100 MB of import
  baseline.

### Change 4 — Tiny refactor to thread the cache cleanly

Both `_read_input_bundle_supabase` and `_read_search_audit_supabase`
are module-level helpers taking `(client, run_id, turn_key)`. The
cache must live for the process lifetime, not per-request. Options:

- **Module-level cache singletons.** Simple, works with the existing
  helper signatures. Cache key just omits `client`, which is fine
  because there's only one client per process.
- **Cache stored on `app.state`.** More elegant for testing (each
  test gets its own app, hence its own cache) but requires plumbing
  the `app.state` reference into the helpers.

Choose the simpler module-level approach; testing can clear the
caches via a helper (`_clear_caches_for_test()`). Tests for the
caching layer use a stub client and assert "second call hits cache
without invoking the client".

## Out of scope

- **Etag / conditional GET support.** `immutable` + 24 h `max-age`
  already covers the user-facing win; adding etags is a second 30 %
  improvement that doesn't justify the complexity here.
- **HTTP/2 server push or preloading.** Marginal, complex, and
  fastapi/uvicorn support for HTTP/2 push is patchy.
- **Streaming responses for large bundles.** The modal needs the
  whole payload to render the editor view; streaming would just push
  the latency-perceiving boundary into the frontend.
- **Pre-fetching all bundles on run-detail page load.** Defeats the
  lazy-load model and explodes initial page weight; lose-lose.
- **Caching the run-snapshot endpoint
  (`GET /api/runs/{run_id}`).** That data DOES change during a live
  run (new rounds, new events), so caching it requires a freshness
  signal. Worth a separate spec if perf data warrants it.
- **Trimming the server image / dropping `pyiceberg`.** Still future
  work (out of scope on spec 0078 as well).
- **Frontend changes.** Browser-cache headers + gzip benefit the
  existing frontend code as-is; no React/JSX work required.
- **Local UI server (`dual-research serve` on a laptop).** Gzip
  middleware is added there for parity but the cold-start / cache
  considerations are inert (filesystem reads, no Supabase round-trip).

## Test plan

### Unit / integration

- [ ] **Cache tests** — `tests/test_ui_server_cache.py` (new):
  - Calling `_read_input_bundle_supabase(stub, run_id, key)` twice
    invokes `stub.table(...).execute()` exactly **once**.
  - Same for `_read_search_audit_supabase` and the inline file
    handler.
  - After LRU eviction (insert > 100 distinct keys), the earliest
    entry is gone (second call to that key re-hits the stub).
  - `_clear_caches_for_test()` empties all three caches.
- [ ] **Header tests** — extend an existing endpoint test (or add):
  - Response from each of the three immutable endpoints carries
    `Cache-Control: public, max-age=86400, immutable`.
  - Response from `/api/runs` does NOT carry it (still freshly
    fetched per request).
- [ ] **Gzip tests** — request `/api/runs/{id}/inputs/{key}` with
  `Accept-Encoding: gzip`, assert `Content-Encoding: gzip` on the
  response and that decompressed body parses as the expected JSON.
  Use the existing TestClient with a sample run fixture.

### Manual / on-Fly

- [ ] **Cold-start hit eliminated.** `flyctl status` shows
  `min_machines_running = 1` reflected in machine count after deploy.
  Wait > 10 minutes idle, then open run-detail and click a card.
  Modal opens **without the multi-second hang** that motivated this
  spec.
- [ ] **Cache hit latency.** Open the same card twice consecutively.
  Server-side timing (uvicorn access log) shows the second request is
  noticeably faster, and the Supabase REST tab in the dashboard shows
  no second query for that key.
- [ ] **Gzip on the wire.** From a browser devtools Network tab on a
  card-open: response Content-Encoding is `gzip` and the
  transferred-size is significantly smaller than decoded-size for the
  input-bundle response.
- [ ] **End-to-end UX.** Drive the run-detail view of the
  `20260518-083618-backend-language-choice` run (the one that
  motivated spec 0078); click 5 different cards in quick succession;
  measure perceived wait. Target: modal content visible within
  ~200 ms on warm-machine cache-miss; near-instant on cache hit.

## Risks

- **Cache memory growth.** Bounded at ~150 MB worst-case, well inside
  the 512 MB VM. If real-world entries are larger than expected we
  switch to size-aware eviction (track total bytes, evict on
  threshold) instead of count-based — the LRU contract stays the
  same. Monitor `flyctl machine status` memory after a week of real
  traffic.
- **Stale cache after a hypothetical bundle-format change.** Bundles
  are immutable for `(run_id, key)`, so even a future format change
  only affects *new* runs; old runs' cached entries remain correct
  for *that* run. No real risk.
- **`min_machines_running = 1` reveals a startup bug.** Today, if a
  deploy regresses the import path, the symptom is "cold-start fails
  for the first user" — easy to miss. With one machine always
  running, the symptom becomes "machine in restart loop, status
  critical" — louder + monitored by the existing health check. Net
  positive for ops.
- **Gzip CPU overhead on shared-cpu-1x.** Negligible at our QPS
  (single-digit RPS, mostly read-only). The `minimum_size=1024` floor
  prevents wasted compression on small responses.
- **`Cache-Control: immutable` traps a stale page across deploys.**
  Bundles are immutable but the JSX bundle URL (`?v=NNNN` query
  param) changes on every spec, so the browser still fetches the new
  bundle. We are not adding `immutable` to the JSX itself — only to
  the per-turn data endpoints.
- **Rollback path.** If anything misbehaves: revert the spec PR.
  Single revert restores all four changes atomically. `fly deploy`
  from the reverted main re-deploys without `min_machines_running`,
  shutting the warm machine if Fly's auto-stop kicks in (saves the
  pennies).

## Open questions

1. **Should we also LRU-cache `_read_run_snapshot` for runs whose
   `phase_reached == "done"`?** Finished runs are immutable too, and
   the snapshot is a fan-out of multiple Supabase queries. Probably
   yes, but only after we have data showing it's a bottleneck — the
   user's complaint was modal-load, not run-detail-load.
2. **Should the LRU cache live in front of Supabase reads more
   generally** (e.g. as a thin wrapper around the supabase client) so
   future immutable endpoints inherit it automatically? Cleaner, but
   touches more code than this hotfix needs. Defer until a third
   immutable endpoint shows up.
3. **Does `min_machines_running = 1` make `auto_stop_machines = "stop"`
   redundant?** No — `auto_stop_machines` still controls whether the
   *second* machine (auto-started under load) gets shut down when load
   drops. Keep both settings; they compose.
