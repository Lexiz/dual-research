---
spec: "0189"
date: 2026-05-23
version: 1.37.1
pr: "https://github.com/Lexiz/dual-research/pull/218"
---

# Spec 0189 — statusCounts.open includes `addressed` — shipped

One-line bug fix. The critique pane's bar-2 segments (`All · Open · Resolved
· Drift`) now satisfy the arithmetic invariant `All == Open + Resolved +
Drift` on phases that contain `addressed` mid-arc items. Previously the
`_isOpenStatus` predicate matched only `'open' | 'open-new'`, so `addressed`
items contributed to the `All` count but fell out of every per-state count.

## What landed

- **[src/dual_research/ui/static/run-detail.jsx:7123](../src/dual_research/ui/static/run-detail.jsx)** — `_isOpenStatus` widened to also match `'addressed'`. Spec 0189 Option A: the canonical "what counts as open?" predicate now covers all three open-side states. The change flows automatically through both consumers:
  - `statusCounts.open` at line ~7222 — `addressed` items now count in the Open chip total.
  - `pushItem`'s status-filter early-return + the open-bucket assignment — `addressed` items now match the explicit Open branch instead of falling through to `pushItem`'s "[critique] unknown item.status" `console.warn` + default-open bucket. Net bucketing outcome identical (still lands in `openCarriedItems`); incidental win is one fewer console warning per `addressed` item.

- **[tests/spec0189/test_status_counts_addressed_routes_to_open.py](../tests/spec0189/test_status_counts_addressed_routes_to_open.py)** — 3 new structural tests:
  - `test_is_open_status_includes_addressed` — pins the fix.
  - `test_is_open_status_still_covers_open_and_open_new` — regression guard.
  - `test_is_resolved_status_unchanged_does_not_match_addressed` — confirms Resolved predicate stays narrow per spec §6.
  Full suite: 1693 passed (was 1690).

- **CHANGELOG / version** — `1.37.0` → `1.37.1` (PATCH per bug type).

## Live smoke

```
$ curl -sS https://dual-research-alex.fly.dev/run-detail.jsx?v=0181a \
    | grep '_isOpenStatus = '
const _isOpenStatus = (s) => s === 'open' || s === 'open-new' || s === 'addressed';
```

Confirmed: the deployed bundle carries the widened predicate.
`fly status -a dual-research-alex`: two app machines on version 488 running
image `01KSAG9EQQ5N5QY1QQAKN0QC0Q`.

## Deploy notes

- `fly deploy` hit a new lease-error variant this time: `failed to get lease
  on VM 2862655ae70478: machine not found`. The orchestrator was still
  rolling out — the v488 green machines came up healthy a few seconds later
  but the bluegreen swap never fired the destroy-blue stage.
- `scripts/sweep_stale_blues.sh` did NOT destroy the v486 zombies because
  Fly's orchestrator hadn't tagged them with
  `fly_bluegreen_deployment_tag == "safe_to_destroy"` — they were still
  carrying their original numeric deployment tag. The sweep's filter is
  intentionally narrow (Fly's own verdict is what makes the sweep safe by
  construction). When the orchestrator never reaches the swap stage, the
  tag never gets set.
- Recovery: manual `fly machine destroy --force <v486 machine ID>` for both
  v486 zombies after verifying v488 was healthy + serving traffic. Final
  state: 2 machines on v488, both passing health checks.
- This is a new failure mode beyond the held-lease one documented in
  [memory: project-fly-lease-drift-recovery](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md).
  Updating the memory with this variant so the next handler knows to check
  for `safe_to_destroy` tag presence before trusting the sweep, and to fall
  back to manual destroy when the tag is absent.

## What this DOES NOT do

- **Touch `_isResolvedStatus`.** Per spec §6 explicitly — `addressed` is "not
  yet closed" and routing it to Resolved would be a different bug. The
  resolved predicate keeps its narrow `'resolved' | 'answered' | 'resolved-*'`
  match.
- **Add a fifth `Addressed (N)` count chip.** Spec §6 noted this as an
  out-of-scope alternative; the All / Open / Resolved / Drift partition is
  preserved.
- **Refactor `pushItem`'s `console.warn` path.** Out of scope — the warning
  still fires for other unknown status values; we only silenced the
  `addressed` case incidentally because the predicate now covers it.
- **Fix bar-1 run-wide counts.** The spec §6 noted the bar-1 predicate
  (`it.status === 'open'` vs `!== 'open'`) has its own inconsistency
  separate from this fix; it stays out of scope and will need a follow-up
  spec if anyone notices the bar-1 mismatch.
- **Add a behavioural JSX/jsdom runtime test.** The structural regex test
  is the cheap version that survives in pytest (matching the established
  pattern in `tests/spec0173/test_item_round_shape.py`).

## Rebase note

PR #218's first squash-merge attempt failed with `DIRTY` mergeable state, same
pattern documented in previous handoffs. Resolved by rebasing onto
`origin/main`, keeping both sides' append-only additions on
`dashboard/events/0189.jsonl`, force-with-lease-pushing, then admin-squashing.
This conflict is structural to the `/dev-next` cycle's `--push-to-main` event
cadence and will keep happening until spec 0191 / 0192 introduce the python
supervisor that batches event emission.
