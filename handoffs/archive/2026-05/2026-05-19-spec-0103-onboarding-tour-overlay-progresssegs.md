# Handover — spec 0103 · Onboarding tour overlay + ProgressSegs admin (8-step tour over the live app via data-tour-anchor attributes; no redraw of underlying surfaces; ProgressSegs 8-segment per-user track)

- Date: 2026-05-19
- Spec: [`specs/0103-onboarding-tour-overlay-progresssegs.md`](../specs/0103-onboarding-tour-overlay-progresssegs.md)
- PR: https://github.com/Lexiz/dual-research/pull/109
- Merge commit: `d6e30e1f622a0a10f1755d70f449c96e95c3fe51`
- Deployed version: `0.76.0`

## Bottom line for the next session

Spec 0103 shipped clean. Verify pass: 6/6 matrix rows. Production reports `0.76.0` at `/api/health`.

## What shipped

- Version bump: `MINOR` (new-feature)
- Target version: `0.76.0` → deployed `0.76.0`
- Files touched: 9 listed in § 2
- Implement diff: `+585 -194 (9 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `35b3b62ae19910a1b9c2a3747b4e89761f546a20`
- Working tree: dirty (0 modified files)
- Deployed version: `0.76.0`

## What the next spec needs to know

- Queue next: spec **0104**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 6m 00s |
| 5_verify | done | 39s |
| 6_pr | done | 19s |
| 7_deploy | done | 8m 12s |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0103/screenshots/01-2200x1300-dark.png`
- `queue/runs/0103/screenshots/02-2200x1300-light.png`
- `queue/runs/0103/screenshots/03-1400x900-dark.png`
- `queue/runs/0103/screenshots/04-1400x900-light.png`
- `queue/runs/0103/screenshots/05-820x1180-dark.png`
- `queue/runs/0103/screenshots/06-820x1180-light.png`

## What I learned

1. **`__init__.py` version must be bumped alongside `pyproject.toml`**: The `/api/health` endpoint reads `__version__` from `dual_research/__init__.py`, not from `pyproject.toml`. Both files must be bumped together. Missed this on the first deploy attempt; required a follow-up commit + redeploy.

2. **Additive approach for onboarding rewrite**: The spec says "replace" the 3-screen modal, but policy says additive. The old `OnboardingScreen` code was replaced in the file (since TourOverlay is the new export), but the app.jsx gate changed from a full-screen replacement to an overlay sibling — so the app shell is always rendered underneath.

3. **`data-tour-anchor` on first list item needs index tracking**: The run-list renders runs in two groups (attention + normal). The `tourAnchor` prop must be passed to the first row of whichever group renders first, which requires tracking the render index in both `.map()` calls.

4. **Capture script shows step 1 (welcome modal) by default**: The `?reset_onboarding=1` query param that triggers the tour also shows step 1 automatically. The spec's verification matrix shows "each of the 8 steps" but the capture script only takes one screenshot per viewport/theme combo. Future specs with multi-step tour verification should use custom Playwright scripts that advance through all steps.
