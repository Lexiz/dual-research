---
spec: "0183"
date: 2026-05-23
version: "1.36.6"
pr: "https://github.com/Lexiz/dual-research/pull/213"
---

# Spec 0183 — Authoring funnel DRAFTS bucket counts backlog — handoff

## What landed

- **Plumbing**: `render_index → _render_metrics → _render_authoring_funnel` now thread `drafts: list[DraftRow]`. The data was already collected by `collect()` — just hadn't been passed down.
- **DRAFTS bucket count** at [scripts/spec_lifecycle/render_dashboard.py:1257-1264](scripts/spec_lifecycle/render_dashboard.py:1257) now `current_drafts + promoted_recent` (was `= promoted_recent`). With N unpromoted drafts on disk and zero recent promotions, the bucket reads `N` instead of `0`.
- **`promo_pct` denominator** matches the new bucket count (conversion rate compares queued to all drafts that existed in the window).
- **Sub-line prose** rewritten so the new semantics are explicit: `Last 30 days · X drafts in backlog + Y promoted · Z% reached queue · W% of queued shipped`.
- **No DS change, no wire format change, no schema change.** Single-file Python change inside `render_dashboard.py`.
- **New tests** at `tests/spec_lifecycle/test_render_dashboard_spec_0183.py` — 5 assertions (current-backlog-only, sum semantics, new denominator on `promo_pct`, no-dedup sum, empty-state guard).

## Verify

The fix ships to the GitHub Pages dashboard at <https://lexiz.github.io/dual-research/> via the next successful build of `.github/workflows/dashboard.yml`. Live-render smoke against this repo confirms the new sub-line text and the updated bucket count. **Caveat**: the gh-pages dashboard build workflow has been failing on every push today for unrelated GitHub billing reasons (`The job was not started because recent account payments have failed`). The merged code is correct; the dashboard will update automatically once billing is resolved. The fly deploy of `dual-research-alex.fly.dev` is unaffected.

## Deploy notes

- `fly deploy` **failed on first two attempts** — both rolled back due to `× Failed to download pluggy==1.6.0 / Connection reset by peer` from `files.pythonhosted.org` during the `uv run` startup. Not caused by this spec — fly machines re-resolve the env on every boot and one of the two new machines hit a transient PyPI fetch failure. Succeeded cleanly on the third attempt.
- `scripts/sweep_stale_blues.sh`: `sweep: no stale blues on dual-research-alex`.

## Tests

`uv run pytest tests/ -q` — 1670 passed in 19.65s. Includes the 5 new `test_render_dashboard_spec_0183.py` assertions.

## Deferred during implementation

- **`promo_pct` numerator includes direct-queue specs, not just promoted-from-draft** — observed via the live render: `Last 30 days · 0 drafts in backlog + 8 promoted · 538% reached queue · 84% of queued shipped`. The 538% gives the game away: `queued_recent` counts every spec that became `queued` in the window (including specs directly authored via `/spec-queue` without a draft step), but the denominator is `current_drafts + promoted_recent` (the draft funnel). When most of the repo's specs skip the draft step (direct `/spec-queue` from a conversation), the ratio blows up past 100%. This spec followed §3.3 of the body literally (which kept `queued_recent` as the numerator), and the pre-fix code had the same shape with a smaller-yet-still-wrong denominator. The semantically correct fix is to switch the numerator to `promoted_recent` so the metric reads "% of drafts that converted to queued specs" rather than the current mongrel "% of drafts that … made queued specs happen somewhere?". One-line change in [scripts/spec_lifecycle/render_dashboard.py:1308](scripts/spec_lifecycle/render_dashboard.py:1308); the test file at `tests/spec_lifecycle/test_render_dashboard_spec_0183.py` would need its `test_authoring_funnel_promo_pct_uses_new_denominator` updated to match.
