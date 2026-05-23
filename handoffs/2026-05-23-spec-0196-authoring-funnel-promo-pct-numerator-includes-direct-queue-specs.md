---
spec: "0196"
date: 2026-05-23
version: 1.39.2
pr: "https://github.com/Lexiz/dual-research/pull/224"
---

# Spec 0196 — authoring-funnel `promo_pct` numerator fix — shipped

The Metrics-tab authoring-funnel sub-line no longer renders nonsense values
like `538% reached queue`. The numerator now correctly excludes direct-queue
specs (those authored via `/spec-queue` without a draft step), matching the
denominator's population.

## What landed

- **[scripts/spec_lifecycle/render_dashboard.py:1370](../scripts/spec_lifecycle/render_dashboard.py)** — one-symbol change: `queued_recent` → `promoted_recent` in the `promo_pct` calculation. Comment block above the line rewritten to spell out the metric's meaning: `% of drafts that existed in this window which graduated into queued specs`. Direct-queue specs are excluded because they never entered the draft funnel.
- **[tests/spec_lifecycle/test_render_dashboard_spec_0183.py](../tests/spec_lifecycle/test_render_dashboard_spec_0183.py)** — new test `test_authoring_funnel_promo_pct_excludes_direct_queue_specs` with a fixture that catches the regression sharply (5 direct-queue specs + 1 promoted + 1 backlog → `50% reached queue`, not pre-fix `300%`). Existing `test_authoring_funnel_promo_pct_uses_new_denominator` annotated to spell out that its fixture coincidentally produces the same percentage under both broken and fixed math — so the new test is the actual regression guard.
- **CHANGELOG / version** — `1.39.1` → `1.39.2` (PATCH per bug type).

Full suite: 1727 passed (was 1726). The metric is now bounded in `[0, 100]` by construction (numerator and denominator describe the same population).

## Live smoke

After the deploy, the dashboard regenerator (`.github/workflows/dashboard.yml`) regenerates `https://lexiz.github.io/dual-research/` from the renderer that just shipped. The Metrics tab → Spec authoring funnel sub-line will now read a bounded conversion rate. For the current repo state (mostly direct-queue authoring, occasional drafts), expect a value close to either `0%` (no draft activity in window) or some small bounded percentage.

`fly status -a dual-research-alex`: 2 machines on v525 image, both passing. Smoke: `curl https://dual-research-alex.fly.dev/` → 200.

## Deploy notes

Second deploy of today's drain that exercised the spec 0193 image-based sweep fallback live. Same pattern as spec 0195's deploy:

```
sweep: cluster has 4 machines (expected 2) — checking image-release fallback filter (spec 0193)
sweep: spec-0193 fallback destroying 2 machine(s) not on current image (registry.fly.io/dual-research-alex:deployment-01KSAWF8N0EHEK7WBSZPAVJB96)
sweep: fallback destroy failed for 7812614c951148
sweep: fallback destroy failed for d895907a693608
sweep: fallback destroyed 0/2 stale machines on dual-research-alex (failed=2)
```

Fallback identified the correct 2 stale v523 machines; the destroys "failed" with `machine not found` because fly's own cleanup was racing the sweep. Cluster ended clean (2 v525 machines passing). This is exactly the deferred refinement from spec 0195's handoff: the sweep should treat `machine not found` as success-equivalent so the tally matches reality. Pattern is consistent across two deploys now — definitely worth queueing as a follow-up.

## What this DOES NOT do

- **Add a dashboard breakdown of "direct-queue vs promoted" authoring.** Spec §6 explicit; that's a separate "spec sourcing" chart belonging to its own spec.
- **Rename `queued_recent`.** Spec §6 explicit; the variable name is fine in context.
- **Backfill `promoted_from_draft` on historical specs.** The frontmatter is the source of truth as-is.
- **Reconsider the 30-day window.** Same window for both halves; no change.

## Deferred during implementation

- **Refine `sweep_stale_blues.sh` to treat `machine not found` as destroy-equivalent success.** This is the same item I deferred at the end of spec 0195's handoff, observed again on this deploy. The sweep correctly identifies the stale machines via the spec-0193 image-based fallback, but the `fly machine destroy --force` calls race fly's own cleanup and return `machine not found` even though the end state (machine gone) is the desired one. The script's stderr reads `fallback destroy failed for <id>` and the final tally reads `destroyed 0/2 (failed=2)` even though both zombies actually got cleaned. A follow-up could: (a) parse `fly machine destroy` stderr and reclassify "machine not found" as success-equivalent, OR (b) follow each destroy with a `fly machine list` probe and credit the destroy if the machine is absent. Small refinement; the cluster still converges (sweep exits 0) but the reporting confuses anyone reading the post-deploy log.

## Rebase note

PR #224's first squash-merge attempt failed with `DIRTY` mergeable state, same
pattern as every prior spec in today's drain. Resolved by rebasing onto
`origin/main`, keeping both sides' append-only additions on
`dashboard/events/0196.jsonl`, force-with-lease-pushing, then admin-squashing.
