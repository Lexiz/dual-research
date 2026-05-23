# Handover — spec 0099 · Timeline pane M3 rework — header chrome + vertical phase rail outside column anchored to header centers + tl-turn variants + single dashed top border on unfold + REPAIR row variant with explainer

- Date: 2026-05-19
- Spec: [`specs/0099-timeline-pane-m3-rework.md`](../specs/0099-timeline-pane-m3-rework.md)
- PR: https://github.com/Lexiz/dual-research/pull/105
- Merge commit: `ef67c82359b023f75eb1bf9d5fc605b836755bd1`
- Deployed version: `0.73.2`

## Bottom line for the next session

Spec 0099 shipped clean. Resolves Notion issue(s) 05, 11, 16. Verify pass: 6/6 matrix rows. Production reports `0.73.2` at `/api/health`.

## What shipped

- Version bump: `PATCH` (bug)
- Target version: `0.73.2` → deployed `0.73.2`
- Files touched: 3 listed in § 2
- Implement diff: `+414 -66 (4 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `ef67c82359b023f75eb1bf9d5fc605b836755bd1`
- Working tree: dirty (0 modified files)
- Deployed version: `0.73.2`

## What the next spec needs to know

- Queue next: spec **0100**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 4m 32s |
| 5_verify | done | 1m 21s |
| 6_pr | done | 18s |
| 7_deploy | done | 2m 19s |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0099/screenshots/01-2200x1300-dark.png`
- `queue/runs/0099/screenshots/02-2200x1300-light.png`
- `queue/runs/0099/screenshots/03-1400x900-dark.png`
- `queue/runs/0099/screenshots/04-1400x900-light.png`
- `queue/runs/0099/screenshots/05-820x1180-dark.png`
- `queue/runs/0099/screenshots/06-820x1180-light.png`

## What I learned

1. **Reason step false positive persists**: Same as specs 0093-0098 — the handover-missing detection fires even when the file exists. Not blocking.

2. **Version bump both files**: Confirmed pattern — both `pyproject.toml` and `src/dual_research/__init__.py` must be bumped.

3. **REPAIR detection via turnKey suffix**: The backend doesn't set a `repair: true` flag directly on timeline items. Instead, `hasRepairSibling(run, turnKey)` checks `phaseTokenUsage` for keys with a `Repair` suffix. The spec says "the backend already emits this flag" but the actual mechanism is the turnKey naming convention.

4. **Old PhaseRail + PhaseDividerHeader kept**: The old `PhaseRail` and `PhaseDividerHeader` components were kept alongside the new M3 timeline (additive approach). They are now dead code in the Timeline component but may be referenced by other parts of the codebase. A follow-up can clean them up.

5. **Narrow viewport (820x1180) capture limitation**: The capture script at 820x1180 shows the runs list, not the run detail view. The responsive CSS rule for rail collapse is verified by code inspection only. If future specs need narrow-viewport run-detail shots, the capture script needs a `detail` routing parameter.
