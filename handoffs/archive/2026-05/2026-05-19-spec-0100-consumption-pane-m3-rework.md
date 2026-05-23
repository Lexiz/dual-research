# Handover — spec 0100 · Consumption pane full rework — collapsed + unfolded with sub-rows + uniform width across phases with round chip above card + sticky bottom legend

- Date: 2026-05-19
- Spec: [`specs/0100-consumption-pane-m3-rework.md`](../specs/0100-consumption-pane-m3-rework.md)
- PR: https://github.com/Lexiz/dual-research/pull/106
- Merge commit: `a36126aac2ccadb95e24f488db5c11afa020efe9`
- Deployed version: `0.74.0`

## Bottom line for the next session

Spec 0100 shipped clean. Resolves Notion issue(s) 12, 13, 14, 15. Verify pass: 6/6 matrix rows. Production reports `0.74.0` at `/api/health`.

## What shipped

- Version bump: `MINOR` (bug)
- Target version: `0.74.0` → deployed `0.74.0`
- Files touched: 3 listed in § 2
- Implement diff: `+514 -365 (4 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `a36126aac2ccadb95e24f488db5c11afa020efe9`
- Working tree: dirty (0 modified files)
- Deployed version: `0.74.0`

## What the next spec needs to know

- Queue next: spec **0101**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 6m 14s |
| 5_verify | done | 4m 05s |
| 6_pr | done | 19s |
| 7_deploy | done | 2m 48s |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0100/screenshots/01-2200x1300-dark.png`
- `queue/runs/0100/screenshots/02-2200x1300-light.png`
- `queue/runs/0100/screenshots/03-1400x900-dark.png`
- `queue/runs/0100/screenshots/04-1400x900-light.png`
- `queue/runs/0100/screenshots/05-820x1180-dark.png`
- `queue/runs/0100/screenshots/06-820x1180-light.png`

## What I learned

1. **Capture script needs tab clicks for Consumption tab**: The standard capture-shots.py script navigates to the run detail but defaults to the Conversation tab. To capture the Consumption pane, an inline Playwright script is needed that clicks the "Consumption" tab button after navigation. The verify plan's `detail` field only controls routing, not UI interactions.

2. **Verify plan detail field**: Setting `detail: "consumption"` in the verify plan routes to the canonical run detail (the `_route_from_detail` heuristic matches "consumption"), but doesn't activate the consumption tab. Future specs targeting specific tabs should note this limitation.

3. **Input sub-bucket mapping**: The spec's §3 HTML references sub-buckets like "system prompt", "conversation history" that don't directly map to the backend's `promptPieces` keys (`system`, `brief`, `d1`, `d2`, `plan`, `hist`, `draft`, `histp`). Created CCX_INPUT_FILL and CCX_INPUT_LABEL mappings to bridge the gap. Output sub-buckets (reasoning, response, tool calls) aren't broken out in the backend data, so the unfolded output section shows a single "response" row for total output.

4. **Old consumption components kept as stubs**: ConsumptionCard, ConsumptionRow, ConsumptionPhaseHeader are stubbed to `return null` rather than deleted, since they may be referenced by name elsewhere. The new components are CcxCard and CcxLegend.

5. **Version bump both files**: Confirmed pattern — both `pyproject.toml` and `src/dual_research/__init__.py` must be bumped (same as spec 0099).
