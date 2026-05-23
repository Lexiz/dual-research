---
spec: "0193"
date: 2026-05-23
version: 1.39.0
pr: "https://github.com/Lexiz/dual-research/pull/222"
---

# Spec 0193 — image-based fallback for sweep_stale_blues.sh — shipped

Retires the manual `fly machine destroy --force <id>` step that was needed
for every deploy in today's queue drain. `scripts/sweep_stale_blues.sh`
now carries a second filter — gated behind four safety checks — that
destroys machines on an out-of-release image when Fly's `safe_to_destroy`
tag fails to fire.

## What landed

- **[scripts/sweep_stale_blues.sh](../scripts/sweep_stale_blues.sh)** — additive changes:
  - New `JQ_FALLBACK_FILTER='.[] | select(.config.image != $CURRENT_IMG) | .id'` selects machines NOT on the current release image.
  - New `get_current_release_image()` helper. In live mode calls `fly releases --app … --json` and picks the most recent `Status` ∈ `{"running", "complete"}` release by `CreatedAt`, returning its `ImageRef`. In test mode (`--input` given) reads a sibling `<input>.release.json` fixture file with `{"image_ref": "…"}`.
  - The existing oversize-cluster diagnostic branch was extended (additive — original `safe_to_destroy`-tag path untouched) with the fallback flow: skip if no current image (gate 3), refuse if no machine matches the current image (gate 4 — would zero the cluster), otherwise destroy the off-image machines. All paths still exit 0 per the spec-0162 best-effort invariant.

- **[tests/spec0193/](../tests/spec0193/)** — 6 new tests + 5 fixture JSON pairs:
  - `test_fallback_fires_on_documented_shape` — the exact shape from spec 0186's deploy (4 machines, none tagged, 2 off-image).
  - `test_fallback_does_not_fire_when_tag_filter_handles_it` — spec-0162 path still wins when applicable.
  - `test_fallback_refuses_when_zero_machines_on_current_image` — gate 4 refusal path.
  - `test_fallback_skipped_when_current_image_undeterminable` — gate 3 skip path (no `.release.json`).
  - `test_cluster_at_expected_size_neither_filter_fires` — at expected size, no diagnostic fires.
  - `test_script_exit_code_is_always_zero` — best-effort invariant across all five fixtures.

- **[tests/scripts/test_sweep_stale_blues_filter.py](../tests/scripts/test_sweep_stale_blues_filter.py)** — one existing spec-0162 test updated. The pre-0193 diagnostic phrase `"dumping metadata for filter diagnosis"` was replaced by `"checking image-release fallback filter (spec 0193)"`; the existing test was updated to assert the new phrasing (plus the underlying behavior — the diagnostic dump still fires on the gate-failure paths).

- **CHANGELOG / version** — `1.38.0` → `1.39.0` (MINOR per new-feature type).

Full suite: 1722 passed (was 1716).

## Hotfix included in this cycle

Discovered during the live deploy of this very spec: my initial `get_current_release_image()` jq selector used snake_case keys (`status`, `image_ref`, `created_at`) but the `fly releases --app … --json` output uses **PascalCase** keys (`Status`, `ImageRef`, `CreatedAt`) as of fly CLI v0.4.54. Result: the live helper always returned empty, so the fallback always skipped — only the fixture-based test path worked.

The live sweep's stderr surfaced this immediately: `sweep: spec-0193 fallback skipped — could not determine current release image`. One-line patch ([commit ad1f33f](https://github.com/Lexiz/dual-research/commit/ad1f33f) on main, not in PR #222) corrected the jq selector. Verified by sourcing the function and calling it directly:

```bash
$ get_current_release_image
registry.fly.io/dual-research-alex:deployment-01KSAV5YPBBXDB5TZKSGJ856Y2
$ fly status -a dual-research-alex | grep Image
 Image    │ dual-research-alex:deployment-01KSAV5YPBBXDB5TZKSGJ856Y2
```

Matches. The fallback is now actually usable live. Fixture tests still pass because fixtures use lowercase `image_ref` (hand-authored) and the helper's test-mode branch reads from those files directly.

The cleaner shape would have been to ship spec 0193 with the PascalCase selector from the start; the spec's example code in §2.1 used snake_case, which is what I implemented before testing live. Lesson for future shell-tool specs: live-test the live mode at least once before merging, even when the unit-test path is green. Adding a manual-smoke checkbox to the spec template might be the right follow-up.

## Live smoke

```
$ bash scripts/sweep_stale_blues.sh
sweep: no stale blues on dual-research-alex

$ curl -sS -o /dev/null -w "%{http_code}\n" https://dual-research-alex.fly.dev/
200
```

`fly status -a dual-research-alex`: 2 machines on the latest version, both passing.

## Deploy notes

- `fly deploy` hit the held-lease pattern documented in
  [memory: project-fly-lease-drift-recovery](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md).
  This time fly cleared the stale machines on its own during the
  health-check wait — no manual `fly machine destroy --force` needed,
  no `sweep_stale_blues.sh` call needed for recovery. Pure luck of
  timing; the new fallback would have handled it if fly hadn't.
- After the cycle: ran `bash scripts/sweep_stale_blues.sh` against the
  steady-state cluster (2 machines on current image, no tagged blues,
  no oversize) — output `sweep: no stale blues on dual-research-alex`,
  no fallback engaged. Exit 0 as expected.
- Memory entry
  [project-fly-lease-drift-recovery.md](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md)
  is now partially superseded — the "manual destroy when sweep doesn't
  catch the blues" branch should no longer be needed after this spec.
  Leaving the memory entry intact for now; if the next few drains run
  cleanly via the fallback, a follow-up can simplify it.

## What this DOES NOT do

- **Make `fly deploy` itself succeed first-try.** The lease-acquire
  errors during bluegreen rollouts are an upstream fly issue. This
  spec only handles the cleanup; the deploy errors still surface and
  the cycle still proceeds.
- **Retroactively destroy historical stale machines.** Sweep runs
  post-deploy on the current cluster; no backfill against past states.
- **Tune the `EXPECTED_COUNT` default.** Still 2; per-app overrides via
  `--expected-count` are unchanged.
- **Replace the tag-based filter.** Spec 0162's filter stays primary —
  Fly's own verdict is the strongest signal we have. This spec is the
  fallback.
- **Notify the user when the fallback fires.** Output lands in the
  `/dev-next` step 19 deploy stdout, which is already surfaced to the
  user verbatim. No new notification mechanism.

## Rebase note

PR #222's first squash-merge attempt failed with `DIRTY` mergeable state, same
pattern as every prior spec in today's drain. Resolved by rebasing onto
`origin/main`, keeping both sides' append-only additions on
`dashboard/events/0193.jsonl`, force-with-lease-pushing, then admin-squashing.

## Deferred during implementation

- **Live-mode smoke test pre-merge.** This cycle shipped with a PascalCase /
  snake_case key mismatch that only surfaced after deploy because the unit
  tests only exercise fixture-mode. A follow-up could add a `--dry-check` or
  similar flag to `sweep_stale_blues.sh` that returns 0 / 1 based on whether
  the live helper successfully queries `fly releases`, and wire that into
  `/dev-next` post-deploy. Not in scope here because the discovered bug is
  already patched and verified.
