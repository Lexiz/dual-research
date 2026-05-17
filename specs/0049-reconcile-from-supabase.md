---
spec: 0049
title: Reconcile-costs reads run-cost data from Supabase (re-enable daily cron)
label: new-feature
version-bump: MINOR
status: proposed
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

## Proposed change

- New `gather_supabase_totals(client, *, start_date, end_date) -> LocalTotals` in `audit/reconcile.py` — queries the Supabase `runs` table for runs whose `started_at` falls in the date range, pulls each run's `metrics_json` payload, groups by `(date, provider, model_id)` exactly like `gather_local_totals` does for disk. Returns the same `LocalTotals` shape so `compare_day` is unchanged.
- New `--source {local,supabase}` flag on `reconcile-costs` CLI. Default `local` for backward compat. `--source supabase` requires Supabase env vars (already loaded for `--push`).
- `.github/workflows/reconcile-costs.yml` — re-enable the daily `schedule: cron "0 2 * * *"` line; switch the command to `reconcile-costs --since-yesterday --source supabase --push --tolerance 1.0`.
- Tests: `tests/audit/test_reconcile_supabase_source.py` exercises the new gather path against a `RemoteSession` fake (matches the existing Supabase test pattern in `tests/ui/`).

## Out of scope

- A standalone `dual-research reconcile-runs-from-supabase` admin tool — just a flag on the existing CLI.
- Auto-detection of "which source to use" based on env — explicit flag is clearer.
- Backfilling reconcile snapshots for historical dates — possible but separate spec.

## Test plan

- [ ] `gather_supabase_totals` against a `RemoteSession` fake returns the same shape as `gather_local_totals` for equivalent data.
- [ ] `reconcile-costs --source supabase --since-yesterday` end-to-end against mocked Supabase + mocked OpenAI → produces a `ReconcileReport` whose totals match expectation.
- [ ] CI cron (after re-enabling) produces a `verified` / `partial` report instead of spurious drift.
- [ ] Local default (`--source local` implicit) still works exactly as in 0.46.1.

## Risks

- **Supabase `runs.metrics_json` shape drift.** If a future spec changes the per-call shape stored in Supabase but not the local-disk `metrics.json` shape, the gatherer needs to handle both. Mitigation: share parsing code with `gather_local_totals`.
- **Performance on long date ranges.** Querying every run in a wide `--from/--to` window could pull many rows. Mitigation: filter at the SQL level by `started_at >= ?` AND `started_at < ?`.

## Open questions

- Should `--source` default to `supabase` when running in hosted mode (detect via `RUNS_BACKEND` env)? **Default this spec:** no — explicit flag, no implicit mode-switching.
- Should the cron also write reconcile snapshots to local disk on the runner (ephemeral) for debugging the most-recent CI invocation? **Default:** no — `--push` already lands the snapshot in Supabase, which is the source of truth in hosted mode.
