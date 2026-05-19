# Handover — spec 0098 · Critique pane M3 rework — Bar 1 (title · phase tabs · totals · drift chip) + Bar 2 (kind tabs · agent · status filters) + collapsible status-grouped sections + Σ Summary state + phase-header sizing taller than card headers

- Date: 2026-05-19
- Spec: [`specs/0098-critique-pane-m3-rework.md`](../specs/0098-critique-pane-m3-rework.md)
- PR: https://github.com/Lexiz/dual-research/pull/104
- Merge commit: `12c791b410d087ee4d83b29fdd40829d6cd36cfc`
- Deployed version: `0.73.1`

## Bottom line for the next session

Spec 0098 shipped clean. Resolves Notion issue(s) 02, 03. Verify pass: 6/6 matrix rows. Production reports `0.73.1` at `/api/health`.

## What shipped

- Version bump: `MINOR` (bug)
- Target version: `0.73.1` → deployed `0.73.1`
- Files touched: 3 listed in § 2
- Implement diff: `+349 -409 (4 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `12c791b410d087ee4d83b29fdd40829d6cd36cfc`
- Working tree: dirty (0 modified files)
- Deployed version: `0.73.1`

## What the next spec needs to know

- Queue next: spec **0099**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 6m 51s |
| 5_verify | done | 1m 02s |
| 6_pr | done | 21s |
| 7_deploy | done | 2m 26s |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0098/screenshots/01-2200x1300-dark.png`
- `queue/runs/0098/screenshots/02-2200x1300-light.png`
- `queue/runs/0098/screenshots/03-1400x900-dark.png`
- `queue/runs/0098/screenshots/04-1400x900-light.png`
- `queue/runs/0098/screenshots/05-820x1180-dark.png`
- `queue/runs/0098/screenshots/06-820x1180-light.png`

## What I learned

1. **Verify plan detail field**: Confirmed from spec 0097 — must set `detail` to `"run-detail critique pane"` in verify-plan.json so the capture script routes to the run-detail view instead of the runs list.

2. **"New this round" vs "carried over" grouping**: The backend doesn't emit a sub-status for open items. Implemented by comparing each item's raised round against the latest visible round in the phase — items raised in the latest round go to "Open - new this round", others to "Open - carried over".

3. **CritiqueTypeFilter now unused**: The old `CritiqueTypeFilter` component and `filterChipsFor` helper are no longer called since kind tabs are now inline native buttons in the `.crit2 .bar2`. Left as dead code to avoid risk; a follow-up can remove them.

4. **Reason step false positive persists**: Same as specs 0093-0097 — the handover-missing detection fires even when the file exists. Not blocking.

5. **Version bump both files**: Confirmed pattern — both `pyproject.toml` and `src/dual_research/__init__.py` must be bumped.
