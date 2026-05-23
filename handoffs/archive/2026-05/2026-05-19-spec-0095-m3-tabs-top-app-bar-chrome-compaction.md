# Handover — spec 0095 · M3 tabs + top app bar + chrome compaction (run-list 3→2 headers, top-bar layout when viewing a run)

- Date: 2026-05-19
- Spec: [`specs/0095-m3-tabs-top-app-bar-chrome-compaction.md`](../specs/0095-m3-tabs-top-app-bar-chrome-compaction.md)
- PR: https://github.com/Lexiz/dual-research/pull/101
- Merge commit: `75217f41dae7263c519c8b9e68682e1e39aa8029`
- Deployed version: `0.72.4`

## Bottom line for the next session

Spec 0095 shipped clean. Resolves Notion issue(s) 06, 17. Verify pass: 12/12 matrix rows. Production reports `0.72.4` at `/api/health`.

## What shipped

- Version bump: `PATCH` (bug)
- Target version: `0.72.4` → deployed `0.72.4`
- Files touched: 5 listed in § 2
- Implement diff: `+288 -55 (5 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `91c288d055e9114210dc4128fcf18b161222bc10`
- Working tree: dirty (0 modified files)
- Deployed version: `0.72.4`

## What the next spec needs to know

- Queue next: spec **0096**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 3m 10s |
| 5_verify | done | 1m 35s |
| 6_pr | done | 18s |
| 7_deploy | done | 5m 02s |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0095/screenshots/01-2200x1300-dark.png`
- `queue/runs/0095/screenshots/02-2200x1300-dark.png`
- `queue/runs/0095/screenshots/03-2200x1300-light.png`
- `queue/runs/0095/screenshots/04-2200x1300-light.png`
- `queue/runs/0095/screenshots/05-1400x900-dark.png`
- `queue/runs/0095/screenshots/06-1400x900-dark.png`
- `queue/runs/0095/screenshots/07-1400x900-light.png`
- `queue/runs/0095/screenshots/08-1400x900-light.png`
- `queue/runs/0095/screenshots/09-820x1180-dark.png`
- `queue/runs/0095/screenshots/10-820x1180-dark.png`
- `queue/runs/0095/screenshots/11-820x1180-light.png`
- `queue/runs/0095/screenshots/12-820x1180-light.png`

## What I learned

1. **`__init__.py` __version__ must be bumped alongside pyproject.toml**: The `/api/health` endpoint reads `__version__` from `src/dual_research/__init__.py`, NOT from pyproject.toml. Previous specs (0093, 0094) also only bumped pyproject.toml but not __init__.py, which is why health was stuck at 0.72.1. Fixed here for 0.72.4. Future specs MUST bump both files.

2. **Verify plan needs manual expansion for multi-route specs**: The CLI's verify-begin generates one row per viewport/theme combo, but this spec requires BOTH `#/runs` and `#/runs/<latest>` per combo. The verify-plan.json was manually expanded from 6 to 12 rows to cover both routes.

3. **Additive Tab/TabGroup variant approach**: The new `variant` prop on Tab (primary/solid/kind/phase/chrome) coexists with the existing v1 Tab API. Existing call sites (filter tabs, modal tabs, chrome tabs) continue using the v1 default. New M3 consumers pass `variant="primary"` etc. for M3 markup.

4. **Reason step false positive persists**: Same handover-missing false positive as specs 0093 and 0094 (note 1 in reason-notes.md). Not blocking.
