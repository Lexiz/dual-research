# Handover — spec 0097 · QuestionThread + unified item-card family (Q · D · I · C cards with one anatomy — who → when → what → quote, six-word verdict vocabulary, tonal bubble + quote inside bubble, dashed footer)

- Date: 2026-05-19
- Spec: [`specs/0097-question-thread-unified-item-card-family.md`](../specs/0097-question-thread-unified-item-card-family.md)
- PR: https://github.com/Lexiz/dual-research/pull/103
- Merge commit: `4e3719f6e90a83c29330cc0ce51719e24952b111`
- Deployed version: `0.73.0`

## Bottom line for the next session

Spec 0097 shipped clean. Resolves Notion issue(s) 07, 08, 09, 10. Verify pass: 6/6 matrix rows. Production reports `0.73.0` at `/api/health`.

## What shipped

- Version bump: `MINOR` (bug)
- Target version: `0.73.0` → deployed `0.73.0`
- Files touched: 4 listed in § 2
- Implement diff: `+354 -672 (5 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `4e3719f6e90a83c29330cc0ce51719e24952b111`
- Working tree: dirty (0 modified files)
- Deployed version: `0.73.0`

## What the next spec needs to know

- Queue next: spec **0098**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 10m 56s |
| 5_verify | done | 1m 45s |
| 6_pr | done | 31s |
| 7_deploy | done | 2m 31s |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0097/screenshots/01-2200x1300-dark.png`
- `queue/runs/0097/screenshots/02-2200x1300-light.png`
- `queue/runs/0097/screenshots/03-1400x900-dark.png`
- `queue/runs/0097/screenshots/04-1400x900-light.png`
- `queue/runs/0097/screenshots/05-820x1180-dark.png`
- `queue/runs/0097/screenshots/06-820x1180-light.png`

## What I learned

1. **Verify plan detail field matters**: The `verify-plan.json` `detail` field defaults to empty, which routes screenshots to `#/runs` (list view). For specs that touch the critique pane / run-detail view, manually set `detail` to `"run-detail critique pane"` before running the capture script — the heuristic in `_route_from_detail()` matches on "critique"/"detail" keywords.

2. **Verdict vocabulary mapping needed**: The existing disagreement progression data uses arbitrary `step.action` values (e.g. "response", "agreed") that don't map 1:1 to the six-word vocabulary. Added `_mapVerdict()` to normalize non-vocab terms: "answered"/"agreed" → "conceded", "response"/"restated" → "pushback", etc. The console.error from VERDICT_VOCAB check will flag unmapped values in dev.

3. **QuestionRef now accepts `kindLetter` prop**: Default remains 'Q' for backward compat. The `data-kind` attribute drives CSS color routing per kind: Q uses tertiary (default), D/I use error, C uses primary. Spec 0098 can use this for the side-by-side critique pane.

4. **Reason step false positive persists**: Same as specs 0093-0096 — the handover-missing detection fires even when the file exists. Not blocking.

5. **Version bump both files**: Confirmed pattern from spec 0095 — both `pyproject.toml` and `src/dual_research/__init__.py` must be bumped.
