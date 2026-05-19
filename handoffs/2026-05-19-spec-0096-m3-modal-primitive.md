# Handover — spec 0096 · M3 modal primitive (basic 560 dp + rich 1080 dp, shape-xl, elevation-3, agent-tinted left border)

- Date: 2026-05-19
- Spec: [`specs/0096-m3-modal-primitive.md`](../specs/0096-m3-modal-primitive.md)
- PR: https://github.com/Lexiz/dual-research/pull/102
- Merge commit: `7b85f89f301e289791ed8212addae4ebfdbd49d1`
- Deployed version: `0.72.5`

## Bottom line for the next session

Spec 0096 shipped clean. Verify pass: 6/6 matrix rows. Production reports `0.72.5` at `/api/health`.

## What shipped

- Version bump: `PATCH` (refactoring)
- Target version: `0.72.5` → deployed `0.72.5`
- Files touched: 4 listed in § 2
- Implement diff: `+73 -9 (4 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `7b85f89f301e289791ed8212addae4ebfdbd49d1`
- Working tree: dirty (0 modified files)
- Deployed version: `0.72.5`

## What the next spec needs to know

- Queue next: spec **0097**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 1m 54s |
| 5_verify | done | 1m 38s |
| 6_pr | done | 29s |
| 7_deploy | done | 2m 18s |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0096/screenshots/01-2200x1300-dark.png`
- `queue/runs/0096/screenshots/02-2200x1300-light.png`
- `queue/runs/0096/screenshots/03-1400x900-dark.png`
- `queue/runs/0096/screenshots/04-1400x900-light.png`
- `queue/runs/0096/screenshots/05-820x1180-dark.png`
- `queue/runs/0096/screenshots/06-820x1180-light.png`

## What I learned

1. **Additive dual-class approach for M3 migration**: The Modal component now emits both v1 (`dr-modal`, `dr-backdrop`) and M3 (`md-dialog`, `md-dialog__scrim`) classes on the same elements. This lets existing callsites work unchanged while new consumers can target M3 classes. The v1 CSS rules (higher z-index, different border-radius) still apply alongside M3 rules — the browser picks whichever has higher specificity or later source order for each property.

2. **Modal footer should not be wrapped in md-dialog__actions**: The existing `footer` prop renders standalone components like `<RoundScrubber>` that have their own layout. Wrapping in `md-dialog__actions` (flex-end) would break their centering. Future specs that need the actions row should use a separate `actions` prop.

3. **Reason step false positive persists (note 4 from spec 0095)**: The handover-missing detection continues to fire even when the handover file exists. Not blocking; same as specs 0093-0095.

4. **Version bump both files**: Confirmed the pattern from spec 0095 — both `pyproject.toml` and `src/dual_research/__init__.py` must be bumped. The `/api/health` endpoint reads from `__init__.py`.
