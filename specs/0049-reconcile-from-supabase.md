---
spec: 0049
title: Reconcile-costs reads run-cost data from Supabase (re-enable daily cron)
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.47.0
created: 2026-05-17
pr: ""
---

# Spec 0049 — Reconcile-costs reads run-cost data from Supabase

## Context

Spec 0048 ([`0048-cost-reconciliation-and-pricing-version.md`](./0048-cost-reconciliation-and-pricing-version.md))
shipped the always-on cost-verification system. The GitHub Actions
daily cron was wired but **disabled in 0.46.1** because CI runners
check out a clean repo with no local `runs/` directory (gitignored).
Result: the cron would reconcile `$0 local vs $X billed` daily and
report spurious drift — eroding trust in the run-detail
verification chip.

This spec re-enables the daily cron by teaching `reconcile-costs` to
gather run-cost data from **Supabase** (where the actual run metrics
already live in hosted mode, per spec 0020's run-push pattern)
instead of the local `runs/` directory. The local-disk path stays
working for laptop use; the new Supabase-source path is what the
cron uses.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **New `gather_supabase_totals(client, *, start_date, end_date) -> LocalTotals`.** | Lives in `audit/reconcile.py` alongside `gather_local_totals`. Same return-shape contract — both produce `dict[date_iso, dict[(provider, model_id), {usd, run_ids, pricing_versions}]]` so `compare_day` is source-agnostic. |
| D2  | **Per-run aggregation extracted to shared `_ingest_run_metrics`.** | Both gather paths feed the same metrics-payload shape (the JSONB column in Supabase mirrors the JSON file on disk). Factoring the per-call walk into one helper means a future per-call-shape change updates both paths atomically. |
| D3  | **SQL prefilter on `created_at` (indexed), Python-side check on `metrics.started_at`.** | `started_at` lives inside the JSONB blob; filtering it via PostgREST's `metrics->>started_at` syntax works but skips the index. Filtering on `created_at` (top-level, indexed) is fast; the Python check enforces the canonical bucket. The two timestamps differ by milliseconds (push happens immediately after run-start). End padded by 1 day to catch midnight-boundary cases. |
| D4  | **New `--source {local,supabase}` CLI flag, default `local`.** | Backward-compatible default. `--source supabase` requires the same Supabase creds `--push` already needs (`SUPABASE_URL` + `SUPABASE_ANON_KEY` + `SUPABASE_SERVICE_ROLE_KEY`); CLI fails fast with a clear message if missing. |
| D5  | **`reconcile_day` / `reconcile_range` gain optional `local_totals` kwarg.** | When `None` (default), local totals are gathered from `runs_dir` (spec 0048 behaviour preserved). When provided, used as-is — lets the CLI gather once across a date range and pass through. Supabase mode benefits: one SQL query for `--from/--to` ranges instead of one per date. |
| D6  | **CLI no longer warns "runs dir not found" when `--source supabase`.** | `runs_dir` is unused in that mode; the warning was a `--source local`-specific signal. |
| D7  | **GitHub Actions daily cron re-enabled with `--source supabase`.** | `02:00 UTC` schedule restored. Command changes to `reconcile-costs --since-yesterday --source supabase --push --tolerance 1.0`. CI runner's empty `runs/` directory is no longer a problem because the gather doesn't touch it. |
| D8  | **No new env vars.** | Reuses everything spec 0048 + 0.46.1 already wired (`OPENAI_ADMIN_KEY`, `OPENAI_PROJECT_ID`, `SUPABASE_*`). |
| D9  | **No frontend changes.** | The verification chip + Consumption-tab annotation already consume `/api/reconcile/<date>`; what changes is only what populates that endpoint. |

## Files touched

- [`src/dual_research/audit/reconcile.py`](../src/dual_research/audit/reconcile.py) — `gather_supabase_totals`, `_ingest_run_metrics` (factored from `gather_local_totals`), `reconcile_day` + `reconcile_range` gain `local_totals` kwarg, `__all__` exports the new public symbol.
- [`src/dual_research/cli.py`](../src/dual_research/cli.py) — `--source` flag, conditional Supabase-client construction, gather-once-pass-through into `reconcile_day`, missing-runs warning gated on `--source local`.
- [`.github/workflows/reconcile-costs.yml`](../.github/workflows/reconcile-costs.yml) — re-enable `schedule: "0 2 * * *"`; command gets `--source supabase`.
- [`tests/audit/test_reconcile_supabase_source.py`](../tests/audit/test_reconcile_supabase_source.py) — **new**, 6 tests covering the gather + the SQL prefilter contract.
- `pyproject.toml` + `src/dual_research/__init__.py` + `CHANGELOG.md` + `how-it-works.jsx` VERSION_NOTES — 0.46.1 → 0.47.0.

## Out of scope

- A standalone `dual-research reconcile-runs-from-supabase` admin tool — `--source` flag on the existing CLI is enough.
- Auto-detection of which source to use based on env (e.g. `RUNS_BACKEND=supabase`) — explicit flag is clearer; no implicit mode-switching.
- Backfilling reconcile snapshots for historical dates — possible via `--from/--to --all`, but no automated backfill in this spec.
- Anthropic admin-key situation — still unresolved upstream (Anthropic Console UI doesn't expose admin-key minting in this org). The cron will report `partial · ✓ OpenAI · ⚠ Anthropic` until the key is available; setting `ANTHROPIC_ADMIN_KEY` later activates the Anthropic side with no code change.

## Test plan

- [x] `gather_supabase_totals` against a fake client returns the same shape as `gather_local_totals` for equivalent metrics payloads.
- [x] SQL prefilter uses `created_at >= start_date` AND `< end_date + 1day`; canonical end-of-window enforced by Python check.
- [x] Runs whose `metrics.started_at` falls outside the canonical window are excluded.
- [x] Empty result + malformed-metrics tolerance (rows with `metrics: None` / no metrics field) don't crash.
- [x] `pricing_versions_seen` collected from multiple runs on the same day.
- [x] Real-world smoke: `reconcile-costs --day 2026-05-16 --source supabase` against prod produces the same totals as the equivalent local-source run (validates parity).
- [ ] Post-merge: re-trigger `workflow_dispatch` to confirm the daily cron completes successfully end-to-end with `--source supabase`.

## Risks

- **Supabase `runs.metrics` shape drift.** If a future spec changes the per-call shape stored in Supabase but not on local disk, one gather path would silently diverge. Mitigation: D2 — both paths feed the SAME `_ingest_run_metrics` helper, so any shape mismatch surfaces immediately rather than silently rolling up to zero.
- **`runs.metrics` is a JSONB column.** PostgREST returns JSONB as a native dict; if it ever switched to returning a string, the gather would silently no-op. Mitigation: `isinstance(metrics, dict)` check guards the iteration.
- **Cron false-alarms on the Anthropic-still-missing side.** With `--source supabase` working, the cron status will be `partial` (OpenAI verified, Anthropic skipped) — not `drift`. Exit code 0 per 0.46.1 semantics. No false alerts.

## Open questions

- Should `--source` default to `supabase` when `RUNS_BACKEND=supabase` is set? **Default this spec:** no — explicit flag, no implicit mode-switching. Revisit if both modes end up always paired with their respective env.
- Should the cron *also* write `reconcile/<date>.json` to the runner's ephemeral disk for debugging? **Default:** no — `--push` lands the snapshot in Supabase, which the UI reads directly. Local-disk writes on a throw-away runner add nothing.
