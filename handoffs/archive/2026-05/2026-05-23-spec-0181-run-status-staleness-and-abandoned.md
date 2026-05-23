---
spec: "0181"
date: 2026-05-23
version: "1.36.4"
pr: "https://github.com/Lexiz/dual-research/pull/211"
---

# Spec 0181 — Run liveness check + `abandoned` lifecycle status — handoff

## What landed

The All-Runs list and run-detail page now classify silent runs as `abandoned` instead of `running` once they've gone ≥ 30 minutes without an event. Catches orchestrators that died (host recycled, SIGKILL, panic) before writing a terminal event. Distinct from `errored` (which means an explicit failure with a known cause).

- **`derive_run_status` gains `last_event_at` + `now` parameters** ([src/dual_research/ui/labels.py:113](src/dual_research/ui/labels.py:113)) + a new precedence rule 6: when no terminal signal fired and `(now - last_event_at) > RUN_STALE_THRESHOLD_MINUTES` → `abandoned`. Backward-compatible — callers that don't pass `last_event_at` keep the pre-spec "running forever" behaviour. ISO `Z` suffix + naive-datetime inputs both handled; malformed timestamps degrade to the default `running` fall-through.
- **Three call sites plumb the signal**:
  - **FS-backed list** (`summarize_run`): new `_latest_event_ts` reads the transcript tail (~64 KB read, cheap on multi-MB transcripts); new `_last_activity_ts` adds a fallback chain — transcript ts → newest mtime of `state.json` / `metrics.json` / the dir itself → parsed session-dir timestamp. The fallback chain is what catches the user-flagged four stuck rows (orchestrator crashed before writing any transcript).
  - **Supabase-backed list** (`_status_from_columns`): reads each row's `pushed_at` column. Docstring rewritten to drop the false "pushed runs are by definition completed" invariant.
  - **Detail-page replay** (`_finalise_status`): reads `Run._terminal_signals.last_event_at`, populated by `apply_event` on every transcript event (including non-terminal ones — the truth is "did anything arrive recently").
- **`pushed_at` semantics change** ([src/dual_research/persistence/remote.py:_build_run_row](src/dual_research/persistence/remote.py)). Now refreshed on every upsert (was set only by table default on INSERT). Doubles as the canonical "last activity" signal for Supabase-backed runs.
- **`RunStatus` enum + UI badge mapping**. New `"abandoned"` value in `RunStatus` Literal. New `.md-status--abandoned` modifier (warn/amber tone, same palette as `drift` but distinct class so future divergence is cheap) in both `design-system/assets/styles/tokens-and-primitives.css` (DS canonical) and `src/dual_research/ui/static/components.css` (live app — two-place rule). `StatusBadge` gains the mapping + a hover tooltip explaining the policy.
- **`run-list.jsx`**: new `abandoned` filter chip alongside the existing status chips; `abandoned` added to `ATTENTION_STATUSES` so abandoned runs surface in the "Needs attention" bucket too.
- **Design-system docs**: status-pill row in §3 (Primitives) updated to reflect 7 states; §9.5 vocabulary table gains a `Run status` row that names the canonical 7-state set.
- **Threshold**: `RUN_STALE_THRESHOLD_MINUTES = 30` lives at `dual_research.ui.labels`. Module constant — env-driven tuning is a follow-up if operationally needed.
- **Regression tests added** at `tests/test_run_status_staleness.py` — 12 assertions: 9 truth-table cases (staleness branch, threshold semantics, `None` backward-compat, Z-suffix ISO parsing, garbage timestamps, precedence over all 5 terminal rules) + 3 call-site plumbing assertions.

No schema migration. The four currently-stale rows in production flipped to `abandoned` the moment this deployed (truth table is derived live on every read).

## Verify

Live: <https://dual-research-alex.fly.dev/>. The four previously-stuck rows (`20260515-103340-sample-brief`, `20260515-103340-what-is-the-regulatory-landscape-...`, `20260515-103352-partner-vetting`, `20260519-132504-backend-language-choice-ingest-test`) now show ABANDONED in the All-Runs list. `running 0` in the filter chip row; `abandoned 4` chip alongside the others; "Needs attention" bucket count rose from 15 to 19.

## Deploy notes

- `fly deploy` clean, both machines (`18530d9c0d9178`, `e823e05c570958`) green; old blue machines destroyed.
- `scripts/sweep_stale_blues.sh`: `sweep: no stale blues on dual-research-alex`.
- Smoke: deployed `run-list.jsx` carries `filter === 'abandoned'`; deployed `shared.jsx` carries the `abandoned: 'abandoned'` mapping; `index.html` cache-buster bumped to `v=0181a`.

## Tests

`uv run pytest tests/ -q` — 1661 passed in 20.43s. Includes the 12 new `test_run_status_staleness.py` assertions.

## Deferred during implementation

- **"0s ago" display for abandoned runs with no transcript** — the All-Runs list renders `started_at_ago = 0` as `"0s ago"`. Affects only rows where `_earliest_event_ts` returned `None` (transcripts that never had any events). For an abandoned run that's actually 8 days old, the "0s ago" cell is misleading. The fix is downstream of spec 0181: either render `"—"` / `"unknown"` when `started_at_ago == 0 AND started_at is None`, or fall back to the parsed session-dir timestamp the way `_last_activity_ts` does for the staleness signal. The bug pre-dates this spec (those rows used to render as "0s ago running" — equally misleading) but is more visible now that the column highlights abandoned rows.
