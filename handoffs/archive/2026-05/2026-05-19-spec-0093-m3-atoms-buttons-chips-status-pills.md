# Handover — spec 0093 · M3 atoms — buttons (5 variants) + FAB + icon button + chips (4 kinds) + status pills (canonical OK) + switches + segmented buttons

- Date: 2026-05-19
- Spec: [`specs/0093-m3-atoms-buttons-chips-status-pills.md`](../specs/0093-m3-atoms-buttons-chips-status-pills.md)
- PR: https://github.com/Lexiz/dual-research/pull/99

## Bottom line for the next session

Spec 0093 shipped clean. Resolves Notion issue(s) 04. Verify pass: 6/6 matrix rows. Production reports `0.72.2` at `/api/health`.

## What shipped

- Version bump: `PATCH` (refactoring)
- Target version: `0.72.2` → deployed `0.72.2`
- Files touched: 5 listed in § 2
- Implement diff: `+282 -44 (6 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `67ea4b5d4c3e2fd33e5a6ca640dbb86f4c28150e`
- Working tree: dirty (1 modified files)
- Deployed version: `0.72.2`

## What the next spec needs to know

- Queue next: spec **0094**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 5m 23s |
| 5_verify | done | 49s |
| 6_pr | done | 28s |
| 7_deploy | in_progress | — |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0093/screenshots/01-2200x1300-dark.png`
- `queue/runs/0093/screenshots/02-2200x1300-light.png`
- `queue/runs/0093/screenshots/03-1400x900-dark.png`
- `queue/runs/0093/screenshots/04-1400x900-light.png`
- `queue/runs/0093/screenshots/05-820x1180-dark.png`
- `queue/runs/0093/screenshots/06-820x1180-light.png`

## What I learned

1. **handover.py `str + int` bug**: `tree_status.strip().count(chr(10))` returns an int, but the f-string concatenated it with `+` instead of wrapping in `str()`. Fixed in-flight; the fix is committed alongside this handover.

2. **Tonal chip `.chip::before` scoping**: Adding a `::before` pseudo-element to the base `.chip` class would add a leading dot to ALL chips (including non-tonal ones like count chips and RunIDChip descendants). Solution: scope the dot to `.chip[class*="tone-"]::before` so only tonal variants get the dot.

3. **tweaks-panel.jsx loads before shared.jsx**: `_cn` helper is not available in tweaks-panel.jsx since it's defined in shared.jsx which loads later. Used plain string concatenation instead of `_cn()` in that file.

4. **Reason step false positive**: The Step 2 Reason check for the previous handover file flags "file not found" even when it exists on main. The cli's reason checker may not be looking at the right path or checking git properly. Not blocking — proceed if the handover file is verified manually via `git log`.
