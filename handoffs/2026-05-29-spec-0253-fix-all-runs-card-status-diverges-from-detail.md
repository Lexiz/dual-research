---
spec: "0253"
date: 2026-05-29
version: 1.63.4
pr: https://github.com/Lexiz/dual-research/pull/293
kind: post-deploy
---

# Spec 0253 — Fix: All-Runs card status diverges from run-detail status for abandoned runs

**Shipped v1.63.4.** PR [#293](https://github.com/Lexiz/dual-research/pull/293), squash-merged (`8eade93`), deployed to `dual-research-alex.fly.dev` via `deploy.yml` (run 26626295225, conclusion `success`). Host health confirms `1.63.4` / supabase.

## What landed

A dead run could show `● RUNNING` on the All-Runs home page (and inflate the "N in flight · $X spent" header tally) while its detail page read `abandoned`. Root cause: `derive_run_status` was unified (spec 0136) but its `last_event_at` *input* was not — each path derived "last activity" from a different proxy, and the two list proxies diverged from the authoritative last-event timestamp the detail replay uses.

The fix corrects only the `last_event_at` plumbing; `derive_run_status` and the 30-minute threshold are unchanged.

- **Supabase list** ([`server.py`](src/dual_research/ui/server.py)) — dropped the `pushed_at` row-upsert proxy. New `_max_event_ts_by_run(client, run_ids)` reads `MAX(events.ts)` per listed run via one batched, paginated query over the same `events` table the detail page replays, reduced in Python (PostgREST aggregate functions are disabled by default on Supabase and the test fake doesn't model them; event volumes are tiny — ~5k rows total — so fetch-and-reduce is cheap). Falls back to `created_at` when a row has zero events. `last_event_at` in `_supabase_list_runs` is now `max_event_ts.get(id) or created_at`.
- **Filesystem list** ([`aggregator.py`](src/dual_research/ui/aggregator.py)) — `_latest_event_ts` reads a bounded 64 KB tail and walks backward past a truncated/corrupt final line (the SIGKILL-mid-write signature) to the last *valid* event. `_last_activity_ts` dropped its newest-mtime fallback (mtimes drift upward as deploy/sync re-touch artifacts, masking dead runs) in favour of `_earliest_known_ts` (creation time).

## Why the bug fired (confirmed against live data)

Both stuck rows (`bb38` = `20260528-082137-…`, `313f` = `20260524-135902-…`) carry `exit_code IS NULL` (no terminal signal) and `MAX(events.ts)` well over 30 min old (08:47 and 14:20 respectively). A bulk re-upsert on 2026-05-28 23:5x bumped **every** run's `pushed_at` to ~now at once, resetting the supabase list's staleness clock and resurrecting all dead runs to `running`. Reading `MAX(events.ts)` flips both to `abandoned` and is immune to row re-writes. Verified via live SQL that every active run has events, so the `created_at` / `_earliest_known_ts` fallbacks are defensive and unreachable with current data.

## Tests

`tests/test_spec_0253_run_status_list_detail_parity.py` — 12 tests exercising the real list entry points (`_supabase_list_runs`, `summarize_run`) against captured-shape artifacts and asserting parity with the detail path (`_materialize_snapshot_supabase`, `load_run_snapshot`), per spec 0238 discipline:

- Supabase stale run → list == detail == `abandoned`, with a *recent* `pushed_at` to reproduce the bulk-re-push trigger (fixture fidelity, §8).
- Supabase no-events old row → list `abandoned` off `created_at`.
- Supabase healthy run → both `running`.
- `_max_event_ts_by_run` per-run max, pagination past the 1000-row page boundary, empty input.
- Filesystem truncated-final-line → list == detail == `abandoned`.
- Filesystem all-corrupt transcript + recent state.json mtime + old dir → `abandoned` (no mtime fallback).
- Filesystem healthy → both `running`.
- `_latest_event_ts` walk-back / all-corrupt / missing-file.

Full suite: **2439 passed**. The existing spec-0181 staleness tests and aggregator-status tests pass unchanged.

## Deferred during implementation

- **Symmetric zero-event creation-time floor on the supabase detail path** — The spec's §3.2 prose asserts the detail path "would derive `abandoned`" for an old run that never emitted a valid event, but the detail replay only sets `last_event_at` from replayed events (`apply_event`, [aggregator.py:251](src/dual_research/ui/aggregator.py:251)); with zero valid events it stays `None` → `running`, and the supabase materialized tmp dir is named `dr-<run_id>-…` so `_earliest_known_ts`'s `YYYYMMDD-HHMMSS` dir-name fallback does not match it. The list path's new `created_at` fallback (§3.1) would therefore read `abandoned` while the supabase detail page reads `running` for such a row — a residual list/detail divergence of the exact class this spec removes. **Not reachable today**: live SQL confirms every active run in `runs_active` has events, so the `created_at` fallback never fires divergently. Closing it cleanly for the supabase side requires threading `created_at` into `_materialize_snapshot_supabase` / `SupabaseSessionData.materialize` (or seeding the tmp-dir name with the run id's `YYYYMMDD-HHMMSS` prefix) so the detail path has the same creation-time floor as the list — a contained follow-up. Default disposition `archive` (unreachable with current data); revisit if a zero-event row ever appears or if the materialization path is touched for another reason.
