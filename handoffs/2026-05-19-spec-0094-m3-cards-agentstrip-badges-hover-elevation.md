# Handover — spec 0094 · M3 cards + AgentStrip + badge inventory + hover elevation-2 rule + AgentStrip badge sizing/symmetry

- Date: 2026-05-19
- Spec: [`specs/0094-m3-cards-agentstrip-badges-hover-elevation.md`](../specs/0094-m3-cards-agentstrip-badges-hover-elevation.md)
- PR: https://github.com/Lexiz/dual-research/pull/100

## Bottom line for the next session

Spec 0094 shipped clean. Resolves Notion issue(s) 01, 03. Verify pass: 6/6 matrix rows. Production reports `0.72.3` at `/api/health`.

## What shipped

- Version bump: `PATCH` (bug)
- Target version: `0.72.3` → deployed `0.72.3`
- Files touched: 4 listed in § 2
- Implement diff: `+138 -5 (4 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `543b62337ad08a8df9a698ebcab81fa15edfa396`
- Working tree: dirty (0 modified files)
- Deployed version: `0.72.3`

## What the next spec needs to know

- Queue next: spec **0095**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 2m 28s |
| 5_verify | done | 1m 36s |
| 6_pr | done | 22s |
| 7_deploy | in_progress | — |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0094/screenshots/01-2200x1300-dark.png`
- `queue/runs/0094/screenshots/02-2200x1300-light.png`
- `queue/runs/0094/screenshots/03-1400x900-dark.png`
- `queue/runs/0094/screenshots/04-1400x900-light.png`
- `queue/runs/0094/screenshots/05-820x1180-dark.png`
- `queue/runs/0094/screenshots/06-820x1180-light.png`

## What I learned

1. **verify-plan.json `detail` field must be populated**: The capture-shots.py script uses the `detail` field to determine the route. When it's empty, it defaults to `#/runs` (list view) instead of the run-detail page. Subsequent specs that need run-detail shots should ensure the plan detail mentions "detail", "timeline", "critique", or includes the explicit `#/runs/<latest>` route fragment.

2. **Reason step false positive persists**: The CLI's reason checker still flags the previous handover file as missing even when it exists on disk (same bug reported in 0093 handover item 4). Not blocking — verify manually and log decision.

3. **Additive CSS approach works well**: M3 card classes (.md-card) coexist cleanly with v1 .card classes. The Card component's `variant` prop selects which system to use, so migration can happen incrementally per call-site.

4. **ModelBadge replaces TimelineAgentPill**: The spec asked to replace model badges in run-detail. The TimelineAgentPill function still exists in run-detail.jsx (not deleted — additive policy) but is no longer called from the two header strip locations. If a future spec needs the old activity-display behavior, it can re-reference TimelineAgentPill.
