---
kind: dev
spec: "0253"
slug: fix-all-runs-card-status-diverges-from-detail
title: "Fix: All-Runs card status diverges from run-detail status for abandoned runs"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: M
created: 2026-05-29
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "User-reported live bug that misreports dead runs as in-flight on the home page and inflates the in-flight compute tally — high priority to ship."
---

<!-- DEV SPEC RULE: this body contains no open questions, TBD markers, or
"figure it out later" prose. Every decision is answered here or deferred via
§7 Out of scope with a named target. -->

# Spec 0253 — Fix: All-Runs card status diverges from run-detail status for abandoned runs

> **Type:** bug  |  **Severity:** P2  |  **Affects:** All-Runs home page (`/`) card status badge + the RUNNING / NEEDS-ATTENTION lane grouping, supabase-backed (hosted `dual-research-alex.fly.dev`) and filesystem-backed UI modes alike.
> **Bump:** PATCH — bug fix.
> **Evidence:** User screenshot of the home page: two old runs (started May 28 10:21 and May 24 15:59) sit under the **RUNNING** lane with a `● RUNNING` badge and feed the "2 in flight · $9.27 spent so far" header tally, while each run's detail page reports **abandoned**. Display ids in the capture: `bb38`, `313f`.

---

## 1. Reproduction

**Environment:** Hosted UI at `dual-research-alex.fly.dev` (supabase backend mode). The same divergence class reproduces in filesystem mode via `summarize_run`.

**Steps:**

1. Start a run, let it emit transcript events into a phase (e.g. Phase 2), then let the orchestrator die without writing a terminal event (host recycle / SIGKILL / panic) — the spec-0181 "abandoned" scenario.
2. Wait > 30 min (`RUN_STALE_THRESHOLD_MINUTES`, [src/dual_research/ui/labels.py:21](src/dual_research/ui/labels.py:21)).
3. Open the All-Runs home page and read the card's status badge / lane.
4. Click into the run's detail page and read its status.

**Expected:** The card status badge and lane match the detail page — both report `abandoned`. There is exactly one definition of "is this run still alive," so the list and the detail can never disagree.

**Actual:** The card shows `● RUNNING` (and is counted in the "N in flight" header tally), while the detail page shows `abandoned`. Two such stale runs (May 24, May 28) are stuck "running" indefinitely.

## 2. Root cause hypothesis

`derive_run_status` is the single status truth table — spec 0136 consolidated the list and detail paths onto it ([src/dual_research/ui/labels.py:121](src/dual_research/ui/labels.py:121)). Spec 0181 added the staleness rule that flips a silent run to `abandoned` when `now - last_event_at > 30 min` ([src/dual_research/ui/labels.py:190](src/dual_research/ui/labels.py:190)). The rule is skipped entirely when `last_event_at is None`, falling through to `running` ([src/dual_research/ui/labels.py:164](src/dual_research/ui/labels.py:164)).

The defect: **the truth table was unified but its `last_event_at` *input* was not.** The three call sites each derive "last activity" from a different, path-local proxy, and the two list proxies diverge from the authoritative last-event timestamp the detail path uses:

| Path | Function | `last_event_at` fed to `derive_run_status` | Sound? |
|---|---|---|---|
| List — supabase (hosted) | `_supabase_list_runs` → `_status_from_columns` ([src/dual_research/ui/server.py:1134](src/dual_research/ui/server.py:1134), [src/dual_research/ui/server.py:1200](src/dual_research/ui/server.py:1200)) | the `pushed_at` DB column ([src/dual_research/ui/server.py:1142](src/dual_research/ui/server.py:1142)) | No — `pushed_at` is a row-upsert timestamp, not a run-liveness signal. When it is `NULL` the staleness rule is skipped → `running` forever; when it is bumped by any later non-event write it reads "alive." |
| List — filesystem | `summarize_run` → `_last_activity_ts` ([src/dual_research/ui/aggregator.py:479](src/dual_research/ui/aggregator.py:479), [src/dual_research/ui/aggregator.py:1336](src/dual_research/ui/aggregator.py:1336)) | last valid event ts, **else newest mtime of dir/`state.json`/`metrics.json`**, else dir-name ts | No — file mtimes drift upward (deploy/sync/upload re-touch artifacts), and the tail parse `json.loads(lines[-1])` returns `None` on a truncated final line ([src/dual_research/ui/aggregator.py:1327](src/dual_research/ui/aggregator.py:1327)) — the canonical SIGKILL-mid-write signature — which then triggers the mtime fallback. |
| Detail — both modes | `load_run_snapshot` → `_finalise_status` ([src/dual_research/ui/aggregator.py:1130](src/dual_research/ui/aggregator.py:1130)) | last **valid transcript event** ts, set during full replay ([src/dual_research/ui/aggregator.py:251](src/dual_research/ui/aggregator.py:251)); the replay skips unparseable lines ([src/dual_research/ui/aggregator.py:1202](src/dual_research/ui/aggregator.py:1202)) | Yes — authoritative. |

For the hosted symptom: the home page takes the supabase list path, so its staleness signal is `pushed_at`. For a dead run `pushed_at` is null-or-not-stale → `running`. The detail page (`_materialize_snapshot_supabase` → `load_run_snapshot`, [src/dual_research/ui/server.py:1698](src/dual_research/ui/server.py:1698)) replays the actual events → `abandoned`. Same truth table, two different inputs, two different answers.

**Confirmed against the live `runs` / `events` tables** (Supabase project `qpdsxspdwqukircrfqkm`, queried 2026-05-29):

| `id` (display_id) | `exit_code` | `MAX(events.ts)` | `pushed_at` | current list status | correct |
|---|---|---|---|---|---|
| `20260528-082137-…` (`bb38`) | `NULL` | 2026-05-28 08:47 (≈15 h old) | 2026-05-28 23:55 (≈16 min old) | `running` | `abandoned` |
| `20260524-135902-…` (`313f`) | `NULL` | 2026-05-24 14:20 (≈4 days old) | 2026-05-28 23:52 (≈19 min old) | `running` | `abandoned` |

The precise trigger is **not** a null `pushed_at` — it is the opposite. Every run row in the table carries a `pushed_at` of `2026-05-28 23:44–23:55` (all within ~11 min of each other): a bulk re-upsert (reconcile / recompute-costs / full re-push) touched every row at once and bumped `pushed_at` to ≈now. Because the supabase list path uses `pushed_at` as its liveness proxy, that single batch reset the staleness clock for **every** run, resurrecting all long-dead ones to `running`. The two rows with `exit_code IS NULL` (no terminal signal) are the two stuck `running` cards in the evidence screenshot; rows with a non-null exit_code already resolve to `errored` / `deadlocked` / `completed` and so were not visibly affected. This confirms `pushed_at` is structurally the wrong signal: any future bulk write to `runs` re-runs the same regression. Reading `MAX(events.ts)` (§3.1) flips both rows to `abandoned` immediately and is immune to row re-writes.

## 3. Fix

Make every path feed `derive_run_status` the **same authoritative "last event timestamp" semantics** the detail replay already uses: the timestamp of the last *valid* emitted event, never a DB upsert-time proxy and never a filesystem mtime.

**3.1 — Supabase list path (`_supabase_list_runs`, [src/dual_research/ui/server.py:1070](src/dual_research/ui/server.py:1070)).** Stop using `pushed_at` as the staleness signal. After fetching the listed run rows, issue one batched aggregate over the `events` table for the listed `run_id`s — `MAX(ts)` grouped by `run_id` — and pass that per-row max-event-ts as `last_event_at` into `_status_from_columns`. This reads the same `events` table the detail materialization reads, so the list result is authoritative-by-construction and can never drift from the detail page. It is one extra round-trip for the whole list (≤100 rows), not a per-row query — cheap at current row volumes. The spec-0181 comment that justified `pushed_at` as "cheaper than a per-row events.MAX(ts) JOIN" is superseded: a single grouped query is not per-row. Rows with no events fall back to `created_at` (the run's creation time), so a never-emitted old row reads `abandoned`, not `running`.

**3.2 — Filesystem list path (`_last_activity_ts`, [src/dual_research/ui/aggregator.py:1336](src/dual_research/ui/aggregator.py:1336) + `_latest_event_ts`, [src/dual_research/ui/aggregator.py:1302](src/dual_research/ui/aggregator.py:1302)).** Two changes:

- Make `_latest_event_ts` resilient: walk backward from the tail past unparseable / truncated lines to the last *valid* JSON event, mirroring the replay's skip-bad-lines behaviour. A corrupt final line must not erase a known-good earlier event ts.
- **Drop the mtime fallback** from `_last_activity_ts`. When no valid event ts exists, fall back to the dir-name creation timestamp via `_earliest_known_ts` ([src/dual_research/ui/aggregator.py:1264](src/dual_research/ui/aggregator.py:1264)), never `max(mtime …)`. A run that never emitted an event and whose dir is hours old then reads `abandoned` (its creation time is stale), matching what the detail path would derive.

**3.3 — Repair of the currently-stuck rows.** Under 3.1 the fix is self-healing: once the list reads `MAX(events.ts)`, `bb38` / `313f` (and any peer) immediately re-derive to `abandoned` on the next list fetch — their events are already old. No data migration or column backfill is required. If implementation-time inspection shows either row has zero events in the `events` table, the `created_at` fallback (3.1) still yields `abandoned`.

The truth table `derive_run_status` itself and the 30-minute threshold are unchanged — only the *input* plumbing is corrected.

## 4. User stories & acceptance criteria

### 4.1 — User stories

> As a `viewer`, I want a run's status badge on the All-Runs home page to match the status shown on that run's detail page, so that I can trust the home page and not be told a dead run is still in flight.

> As a `researcher`, I want abandoned runs to leave the RUNNING lane and the "N in flight · $X spent" tally, so that the header reflects real live compute rather than counting stalled runs.

### 4.2 — Acceptance scenarios (BDD)

> **Scenario 1:** stale run reads abandoned on both surfaces
> GIVEN a run whose last `events` row (supabase) / last valid transcript event (filesystem) is older than `RUN_STALE_THRESHOLD_MINUTES` and which has no terminal event
> WHEN the All-Runs home page list is fetched and the same run's detail page is fetched
> THEN both report status `abandoned` and the run does not appear in the RUNNING lane or the in-flight tally.

> **Scenario 2:** healthy in-flight run still reads running
> GIVEN a run whose last event is within `RUN_STALE_THRESHOLD_MINUTES` and which has no terminal event
> WHEN the All-Runs home page list is fetched and the same run's detail page is fetched
> THEN both report status `running` and the run appears in the RUNNING lane.

## 5. Regression-prevention test

Follows spec 0238 live-failure discipline (exercise the *real* list entry points against captured artifacts, not just helper-level units) and the spec 0206 source-pattern doctrine (pure-stdlib pattern tests; no Playwright / `tests/ui/`). Capture the actual stuck-run artifacts as fixtures: the transcript (filesystem) and a `runs`-row + `events` rows snapshot (supabase) for one of `bb38` / `313f`.

- [ ] Test: supabase list parity — feed `_supabase_list_runs` / `_status_from_columns` the captured stale run (events all > 30 min old, `pushed_at` set to its observed live value ≈16 min old — recent, NOT null, so the test reproduces the bulk-re-push trigger, exit_code null) and assert the list status equals `load_run_snapshot`'s detail status equals `abandoned`. Fails before the fix (list returns `running` off the recent `pushed_at`), passes after (reads `MAX(events.ts)`).
- [ ] Test: filesystem list parity — `summarize_run` on a fixture session dir whose transcript's **final line is truncated/corrupt** but whose earlier events are > 30 min old returns `abandoned` (resilient tail walk-back), matching `load_run_snapshot`. Fails before the fix (`_latest_event_ts` returns `None` → mtime fallback → `running`).
- [ ] Test: no-events old row — a supabase row / fs dir with zero events and an old `created_at` / dir-name ts reads `abandoned`, not `running` (mtime-fallback removal + `created_at`/`_earliest_known_ts` fallback).
- [ ] Test: healthy run unaffected — a run with a recent last event still reads `running` on the list path, in both modes (no false-abandoned regression).

## 6. Blast radius

`derive_run_status` is the shared truth table consumed by all three paths; this spec changes only the `last_event_at` argument each path computes, not the table's precedence. Callers of `_status_from_columns` ([src/dual_research/ui/server.py:1177](src/dual_research/ui/server.py:1177)) and `_last_activity_ts` ([src/dual_research/ui/aggregator.py:1336](src/dual_research/ui/aggregator.py:1336)) are confined to the two list paths in `server.py` / `aggregator.py`. The new batched `MAX(events.ts)` query adds one round-trip per list fetch; the events table is already indexed on `run_id` (it powers the SSE / materialization paths). `_latest_event_ts` is also fed by `_last_activity_ts` only — the resilient walk-back is strictly more permissive (it returns more valid timestamps, never fewer). The existing spec-0181 staleness tests at [tests/test_run_status_staleness.py](tests/test_run_status_staleness.py) and the existing aggregator-status tests lock the truth table and must continue to pass unchanged.

## 7. Out of scope

This spec does NOT touch any file under `src/dual_research/ui/static/` or `design-system/` — no new DS primitive, no badge/lane styling change. The `● RUNNING` badge (`rc-status`) and the RUNNING / NEEDS-ATTENTION lane grouping are reused as-is from specs 0181 and 0246; the only behaviour change is which runs land in which lane, driven by the corrected status value.

- Changing `RUN_STALE_THRESHOLD_MINUTES` or adding per-phase staleness thresholds — deferred; not the cause of this bug.
- Persisting a dedicated `last_event_at` column on the `runs` row as a write-time optimization — deferred to a follow-up dev spec to be drafted post-merge if the batched `MAX(events.ts)` query ever shows up in list-latency profiling; the query-time approach in §3.1 is correct and sufficient now and avoids a schema migration + backfill.
- Surfacing an explicit "abandoned" reason / death-cause on the card — out of scope; a separate spec.

## 8. Risks

- **Events-table query cost.** If a future row-volume spike makes the batched `MAX(events.ts)` aggregate slow, list latency could regress. Mitigated by the single-batched-query (not per-row) shape and the existing `run_id` index; the §7 deferred `last_event_at` column is the escape hatch if profiling ever demands it.
- **Fixture fidelity.** The captured supabase fixture must reproduce the real `pushed_at` value — confirmed recent (≈16 min old, bumped by a bulk re-upsert), NOT null — so the test locks the actual misfire rather than a vacuous null case. The §5 test pins `pushed_at` to a recent value with `MAX(events.ts)` ancient.
- **Resilient tail walk-back bounds.** Walking back past corrupt lines must stay bounded (read a capped tail window, like the current ~64 KB) so a pathological all-garbage transcript can't cause an unbounded backward scan; the fallback to `_earliest_known_ts` covers the "no valid event found in window" case.
