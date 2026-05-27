---
spec: 0081
title: Cache /api/runs/{id} snapshot by (run_id, latest_event_seq)
label: bug
version-bump: PATCH
status: merged
target-version: 0.69.5
created: 2026-05-18
pr: "https://github.com/Lexiz/dual-research/pull/81"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0081 — Run-snapshot cache + SSE gzip skip

## Context

Spec 0079 attacked the wrong endpoint. The user's "modal opens take
tens of seconds" report bundled two distinct hot paths:

1. The **modal**, which calls `/api/runs/{id}/inputs/{key}` once the
   run-detail page is already open. Spec 0079 fixed this with an LRU
   on the input-bundle helper. ✅
2. The **run-detail page itself**, which calls `/api/runs/{id}` to
   render the timeline + critique panels in the first place. Spec
   0079 did **nothing** for this endpoint. The user's actual
   observation — "it took 11 s to load an individual record" — is
   this path, not the modal.

After spec 0080 stopped the Fly proxy flap and restored reachability,
real network-level probes showed the steady-state `/api/health`
sitting at ~170 ms, but a populated `/api/runs/{id}` was still
multi-second. Reading the code makes the cause obvious
([datasource.py:59](src/dual_research/ui/datasource.py:59)):

```python
@contextmanager
def materialize(self) -> Iterator[Path]:
    tmp = tempfile.TemporaryDirectory(...)
    self._write_files(dest)       # paginate ALL session_files
    self._write_transcript(dest)  # rebuild transcript from events
    self._write_blobs(dest)       # base64-decode every attachment
    yield dest                    # load_run_snapshot reads them back
```

Every call to `/api/runs/{id}` does this. For a prod-tier run with
hundreds of files and a multi-MB events history, that's many
paginated Supabase round-trips + tmp-dir writes + tmp-dir reads, per
single page render. The SSE polling loop runs the same dance every
time `max(events.seq)` changes. With multiple viewers on the same run,
the cost multiplies linearly.

### Why caching is correct

The snapshot is a pure function of `(run_id, max(events.seq))`:

- **Done runs** — `phase_reached == "done"`, max seq is fixed at the
  `run_completed` event. The snapshot for that pair never changes →
  cache it forever.
- **Live runs** — every new event bumps the seq. Cache misses force a
  re-materialise, but only **once** per new event no matter how many
  GET requests + SSE subscribers see the new seq at the same time.

No invalidation hook is required besides process restart on deploy —
the cache key itself is the freshness signal.

### A second, defensive bug surfaced while looking

`GZipMiddleware` (added in spec 0079) wraps response bodies and
buffers chunks until it can decide whether to compress (threshold
`minimum_size`). For a `text/event-stream` response that ships tiny
events one at a time, that buffering can hold each event open
indefinitely waiting for enough bytes to gzip. SSE-over-HTTP is
designed to be flushed immediately; gzip in front of it breaks
realtime delivery. Symptom would be: a live run-detail page never
"catches up" — the initial snapshot lands fine (the GET) but live
incremental updates lag or never arrive.

We haven't proven this is biting users in production (the
`min_machines_running = 0` cold-start and the proxy flap dominated
all visible latency to date), but the architectural risk is real and
the fix is small.

## Proposed change

### Change 1 — Run-snapshot LRU

**`src/dual_research/ui/server.py`**:

- New module-level cache: `_RUN_SNAPSHOT_CACHE = BoundedLRU(maxsize=50)`.
- New helper `_materialize_snapshot_supabase(client, run_id, *, seq=None) -> dict`
  that wraps the existing `SupabaseSessionData.materialize()` +
  `load_run_snapshot()` + `_to_camel(to_jsonable(run))` pipeline,
  memoised by `(run_id, seq)`. `seq` defaults to a fresh
  `latest_event_seq` call; the SSE loop passes its already-known
  current seq to skip the redundant probe.
- Replace the `get_run` body with a single call to the helper.
- Replace the `_supabase_event_stream` body's materialise block with
  a call to the helper, passing the current seq.

**`src/dual_research/ui/server.py` — `_clear_caches_for_test()`** —
extended to also `clear()` the new snapshot cache so existing tests
stay hermetic.

**Memory budget.** Each cached entry is the camelCase JSON dict the
endpoint returns. Realistic worst case ~500 KB per entry × 50 entries
= **25 MB**. Comfortably inside the 512 MB VM that spec 0078
provisioned.

### Change 2 — Defensive gzip skip on SSE paths

**`src/dual_research/ui/server.py`** — new class:

```python
class _GZipMiddlewareSkipStream(GZipMiddleware):
    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http" and scope.get("path", "").endswith("/stream"):
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)
```

Both `_make_app` and `_make_supabase_app` swap from `GZipMiddleware`
to `_GZipMiddlewareSkipStream`. Gzip still applies to everything that
isn't an SSE endpoint.

## Out of scope

- **Indexing `events(run_id, seq)`.** The `latest_event_seq` query
  (`ORDER BY seq DESC LIMIT 1`) needs to be cheap; spec 0019's schema
  already covers it via the primary key. No new migration here.
- **Trimming what `load_run_snapshot` reads.** The cache makes
  per-request cost irrelevant for cache hits; refactoring the
  aggregator to read selectively from Supabase (skip transcript /
  blobs unless needed) is real cleanup but a bigger spec.
- **Cache invalidation on hypothetical
  out-of-band-edit-of-session_files.** That can't happen — rows are
  only ever written via the orchestrator's `--push` and live
  push-watch, both of which append new keys rather than mutate
  existing ones for completed turns.
- **A region in `fra` / `ams`.** Even with this spec, EU users pay
  ~100–150 ms RTT to `iad` per request. A separate spec if that
  baseline matters after this one lands.

## Test plan

### Unit

Already shipped in `tests/ui/test_server_cache.py`:

- [x] `test_run_snapshot_helper_caches_at_constant_seq` — second
      call at unchanged seq hits exactly one Supabase query (the
      seq probe) instead of the multi-query materialise.
- [x] `test_run_snapshot_helper_invalidates_when_seq_advances` —
      appending a new event row forces a fresh materialise on next
      call.
- [x] `test_run_snapshot_helper_accepts_prefetched_seq` — passing
      `seq=...` skips even the seq probe, so a cached hit is zero
      Supabase queries.
- [x] `test_gzip_skip_stream_middleware_bypasses_sse_path` — direct
      ASGI scope test: `/stream` path with `Accept-Encoding: gzip`
      gets no `Content-Encoding: gzip` from the middleware.
- [x] `test_gzip_skip_stream_middleware_still_compresses_non_stream`
      — sanity: `/api/runs` with a 4 KB body still receives
      `Content-Encoding: gzip`.
- [x] Existing `_clear_caches_for_test` test extended to also clear
      `_RUN_SNAPSHOT_CACHE`.

778 tests passing locally.

### On-Fly post-deploy

- [ ] **First call to `/api/runs/{id}` is the slow one; second is fast.**
  Authenticated curl twice in a row against
  `/api/runs/20260518-083618-backend-language-choice`. First TTFB
  matches today's; second is sub-second (cache hit on the seq lookup
  + cached payload).
- [ ] **No OOM in logs** for 30 min after deploy.
- [ ] **End-to-end browser test:** open
  `https://dual-research-alex.fly.dev/#/runs/...`, refresh, second
  load is noticeably faster than first.

## Risks

- **Cached snapshot stale because seq is also cached somewhere
  upstream.** It isn't — `latest_event_seq` runs a fresh
  `SELECT seq FROM events ... LIMIT 1` against Supabase on every call
  (no memoisation). The cache key is therefore as fresh as Supabase
  itself.
- **Memory growth.** Bounded at ~25 MB at maxsize=50. If real
  snapshots are bigger, we move to a size-aware eviction policy.
- **`max(events.seq)` query gets slow on huge runs.** The events
  table is keyed `(run_id, seq)`; `ORDER BY seq DESC LIMIT 1` is a
  trivial index-driven query. Not a concern at our scale.
- **The SSE-skip might silently disable gzip somewhere we wanted it.**
  Only paths *ending in* `/stream` are skipped. Every other endpoint —
  `/api/runs`, `/api/runs/{id}`, `/api/runs/{id}/inputs/{key}`,
  `/api/runs/{id}/files/{path}` — still gzips above the 1 KB floor.
- **Rollback:** revert this PR. Behaviour returns to the spec 0079
  baseline (still reachable thanks to spec 0080, just slow on
  run-detail again).

## Open questions

1. **Should we also LRU the run-list query** (`/api/runs`)? It
   changes when new runs land; could TTL-cache for ~5 s. Probably
   yes, but data-driven — measure first.
2. **Should `_materialize_snapshot_supabase` short-circuit done runs**
   even harder (e.g. skip the seq probe entirely once we've seen a
   `phase_reached == "done"` snapshot)? Marginal win; the seq probe
   is already a one-row index lookup.
