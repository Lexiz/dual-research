---
spec: "0195"
date: 2026-05-23
version: 1.39.1
pr: "https://github.com/Lexiz/dual-research/pull/223"
---

# Spec 0195 — All-Runs no-transcript started-cell fallback — shipped

The four legacy `abandoned` rows surfaced by spec 0181 no longer render
`"0s ago"` in the started column. `summarize_run` now falls back to the
session-dir `YYYYMMDD-HHMMSS` prefix when no transcript event exists, and
the list cell renders `"—"` when both signals are absent.

## What landed

- **[src/dual_research/ui/aggregator.py:1100](../src/dual_research/ui/aggregator.py)** — new `_earliest_known_ts(session_dir)` helper. Priority: (1) first event ts in `transcript.jsonl`; (2) parsed `YYYYMMDD-HHMMSS` dir-name prefix; (3) `None`. The dir-prefix branch mirrors `_last_activity_ts`'s last-resort branch at line ~1163 but for the *earliest*, not latest, timestamp. No mtime fallback for `started_at` because file mtimes drift upward as state.json / metrics.json are written — they make a poor proxy for *start* time. The doc-comment spells this out.

- **[src/dual_research/ui/aggregator.py:317](../src/dual_research/ui/aggregator.py)** — `summarize_run` call site swap: `_earliest_event_ts(session_dir / "transcript.jsonl")` → `_earliest_known_ts(session_dir)`.

- **[src/dual_research/ui/static/run-list.jsx:480](../src/dual_research/ui/static/run-list.jsx)** — cell renderer guards the `relTime` call: `{run.startedAt || run.startedAtAgo > 0 ? fmt.relTime(run.startedAtAgo) : '—'}`. The em-dash matches the existing "missing data" convention used by `fmt.duration` / `fmt.cost`.

- **[tests/test_run_status_staleness.py](../tests/test_run_status_staleness.py)** — 4 new tests under the spec 0195 §section:
  - `test_summarize_run_falls_back_to_session_dir_ts_for_started_at` — dir-prefix fallback (the canonical fix).
  - `test_summarize_run_returns_none_when_no_ts_signal` — `None` when no signal.
  - `test_summarize_run_prefers_transcript_first_event_over_dir_ts` — transcript wins over prefix when both exist.
  - `test_earliest_known_ts_returns_dir_prefix_when_transcript_empty` — empty-transcript file (exists but no parseable lines) still falls back to the dir prefix.

- **CHANGELOG / version** — `1.39.0` → `1.39.1` (PATCH per bug type).

Full suite: 1726 passed (was 1722).

No DS / schema / wire-format change.

## Sort-order side-effect

Documented in spec §5 and intended: the four currently-stuck-at-top abandoned rows fall to their true position under `started:desc` after the fix. The spec-0181 explicit `abandoned` filter chip already gives users the "find the abandoned ones" affordance — they no longer need the broken sort to surface them.

## Live smoke

The bug is FS-backed (`summarize_run` path); the live app is Supabase-backed (`server.py:1050` reads `created_at` directly, never `None`). So the visible behaviour on the live URL doesn't directly demonstrate the fix — the affected code path runs only on direct-FS reads (local dev or the rare write-mode). The unit tests are the load-bearing verification here. Smoke: `curl https://dual-research-alex.fly.dev/` → 200.

## Deploy notes

**This was the first deploy that exercised the spec 0193 image-based sweep fallback live, and it WORKED as designed:**

```
$ bash scripts/sweep_stale_blues.sh
sweep: no stale blues on dual-research-alex
sweep: cluster has 4 machines (expected 2) — checking image-release fallback filter (spec 0193)
sweep: spec-0193 fallback destroying 2 machine(s) not on current image (registry.fly.io/dual-research-alex:deployment-01KSAVRP0WG5E6NFM03M495KCE)
sweep: fallback destroy failed for 286366db437298
sweep: fallback destroy failed for 48e025ea233018
sweep: fallback destroyed 0/2 stale machines on dual-research-alex (failed=2)
```

The fallback **correctly identified** the two v517 zombies (different image from the current v519 release). The `fly machine destroy --force` calls returned `failed to obtain lease: machine not found` — because fly was already in the middle of pruning the machines concurrently. The cluster ended clean either way: `fly status` showed 2 v519 machines passing, the dropped machines were gone.

**This is a real validation of the spec 0193 design.** The identify-and-attempt-destroy logic works; the only gap is that the destroy step doesn't treat "machine not found" as success-equivalent (the machine being absent is, in fact, the desired end state). That's a small follow-up — see deferral below.

## What this DOES NOT do

- **Touch the detail-page started-at header.** Spec §6 explicit; the detail page is rarely opened for never-started runs and renders empty for nearly every other field, so a dash-vs-zero in the header is not a priority.
- **Backfill Supabase `started_at`.** Spec §3.3 explicit; the Supabase path already uses `created_at` which is always present.
- **Make `relTime(0)` render `"—"` globally.** A run that genuinely just started 0 seconds ago should still render as `"0s ago"`. The decision lives at the call site, not the formatter.
- **Add a `_latest_known_ts` symmetric helper.** `_last_activity_ts` already plays that role with its own fallback ladder; renaming or unifying is out of scope per spec §6.

## Deferred during implementation

- **Treat `fly machine destroy` 'machine not found' as success in `sweep_stale_blues.sh`.** Today's deploy demonstrated that `fly machine destroy --force <id>` can fail with `Error: failed to obtain lease: failed to get lease on VM …: machine not found` even when `fly machine list` reports the machine as present — fly's cleanup is asynchronous relative to its own list endpoint. The end state is correct (machine is gone), but the script logs `fallback destroy failed for <id>` and the final tally reads `destroyed 0/2 (failed=2)` even though both zombies actually got cleaned up. A future spec could parse the `fly machine destroy` stderr (or use a follow-up `fly machine list` to verify absence) and re-classify "machine not found" as success-equivalent. Small refinement, would make the sweep's output match reality more accurately. Not blocking — sweep's exit code is still 0, the cluster still converges, and the human-readable verdict is recoverable from `fly status`.

## Rebase note

PR #223's first squash-merge attempt failed with `DIRTY` mergeable state, same
pattern as every prior spec in today's drain. Resolved by rebasing onto
`origin/main`, keeping both sides' append-only additions on
`dashboard/events/0195.jsonl`, force-with-lease-pushing, then admin-squashing.
