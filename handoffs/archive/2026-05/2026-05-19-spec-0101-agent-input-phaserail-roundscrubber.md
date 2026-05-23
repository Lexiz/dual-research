# Handover — spec 0101 · Agent input panel + PhaseRail + RoundScrubber M3 anatomy sweep

- Date: 2026-05-19
- Spec: [`specs/0101-agent-input-phaserail-roundscrubber.md`](../specs/0101-agent-input-phaserail-roundscrubber.md)
- PR: https://github.com/Lexiz/dual-research/pull/107
- Merge commit: `0fd595ff000a42bf107406bfee24a4d0a8e769cf`
- Deployed version: `0.74.1`

## Bottom line for the next session

Spec 0101 shipped clean. Verify pass: 6/6 matrix rows. Production reports `0.74.1` at `/api/health`.

## What shipped

- Version bump: `PATCH` (refactoring)
- Target version: `0.74.1` → deployed `0.74.1`
- Files touched: 4 listed in § 2
- Implement diff: `+153 -177 (5 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `0fd595ff000a42bf107406bfee24a4d0a8e769cf`
- Working tree: dirty (0 modified files)
- Deployed version: `0.74.1`

## What the next spec needs to know

- Queue next: spec **0102**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 7m 25s |
| 5_verify | done | 6m 40s |
| 6_pr | done | 25s |
| 7_deploy | done | 2m 31s |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0101/screenshots/01-2200x1300-dark.png`
- `queue/runs/0101/screenshots/02-2200x1300-light.png`
- `queue/runs/0101/screenshots/03-1400x900-dark.png`
- `queue/runs/0101/screenshots/04-1400x900-light.png`
- `queue/runs/0101/screenshots/05-820x1180-dark.png`
- `queue/runs/0101/screenshots/06-820x1180-light.png`

## What I learned

1. **PhaseRail was dead code**: The old `PhaseRail` function (SPEC-0057) was defined but never called in JSX — the timeline now uses `tl__rail` with `.seg` divs from spec 0099. Safe to fully replace the old styles and component.

2. **Modal captures need custom Playwright scripts**: The standard `capture-shots.py` only navigates to pages. Specs that require opening modals (like this one — NegotiateReviewModal for phases 2/4) need a custom capture script that uses `dispatchEvent` to click turn rows. The `.dr-backdrop` / `.md-dialog__scrim` overlay intercepts Playwright's native `.click()` on elements behind it; using JS `dispatchEvent` bypasses this.

3. **NegotiateReviewModal opens for statsPhase 2 or 4**: To target the right modal in capture scripts, look for `.tl-phase` sections with `PHASE 2` or `PHASE 4` headers, then click a `.tl-turn` inside.

4. **Material Symbols via `.ms` class**: The codebase uses `<span className="ms ms-20">icon_name</span>` for Material Symbols (not a `<MaterialSymbol>` component). The spec mentioned `<MaterialSymbol>` but the actual pattern is the `.ms` font class.

5. **Version bump both files**: Confirmed again — both `pyproject.toml` and `src/dual_research/__init__.py` must be bumped (same as specs 0099, 0100).
