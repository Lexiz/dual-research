# Handover — spec 0102 · How It Works overlay + right-side menu + Changelog (full-screen M3 dialog · sticky right menu · How It Works ↔ Changelog toggle · 9 collapsible sub-sections with inline diagrams)

- Date: 2026-05-19
- Spec: [`specs/0102-how-it-works-overlay-changelog.md`](../specs/0102-how-it-works-overlay-changelog.md)
- PR: https://github.com/Lexiz/dual-research/pull/108
- Merge commit: `81366638e50cfbeb639a0419f43ff33cc6226682`
- Deployed version: `0.75.0`

## Bottom line for the next session

Spec 0102 shipped clean. Verify pass: 6/6 matrix rows. Production reports `0.75.0` at `/api/health`.

## What shipped

- Version bump: `MINOR` (new-feature)
- Target version: `0.75.0` → deployed `0.75.0`
- Files touched: 4 listed in § 2
- Implement diff: `+542 -304 (5 files)`

## Spec rewrite log

_no rewrite needed_

## Current state of main

- Commit: `81366638e50cfbeb639a0419f43ff33cc6226682`
- Working tree: dirty (0 modified files)
- Deployed version: `0.75.0`

## What the next spec needs to know

- Queue next: spec **0103**.
- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.
- Files in § 2 are now in their post-spec state; review them before re-modifying.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_read | done | 0s |
| 2_reason | done | 0s |
| 3_rewrite | skipped | 0s |
| 4_implement | done | 6m 16s |
| 5_verify | done | 1m 26s |
| 6_pr | done | 18s |
| 7_deploy | done | 2m 31s |
| 8_handover | pending | — |

## Screenshots reference

- `queue/runs/0102/screenshots/01-2200x1300-dark.png`
- `queue/runs/0102/screenshots/02-2200x1300-light.png`
- `queue/runs/0102/screenshots/03-1400x900-dark.png`
- `queue/runs/0102/screenshots/04-1400x900-light.png`
- `queue/runs/0102/screenshots/05-820x1180-dark.png`
- `queue/runs/0102/screenshots/06-820x1180-light.png`

## What I learned

1. **`?how=1` deep link is the key for overlay capture scripts**: Standard capture-shots.py navigates to hash routes but can't click buttons to open overlays. Using `?how=1` query param in the URL is the reliable way to open the HIW overlay in Playwright without JS `dispatchEvent` hacks. Future overlay-based specs should consider a similar query-param deep link for testing.

2. **Additive approach for route-to-overlay migration**: The spec said "replace the route" but policy says additive. Kept the `how-it-works` route as a stub page that tells users to use the button, while the overlay is the primary surface. `window.HowItWorksPage` serves as the legacy fallback.

3. **Existing content doesn't map 1:1 to spec's 9 sections**: The spec lists 9 canonical sub-section names but the existing how-it-works.jsx had different section organization (Overview, Chat lifecycle, Cost shape, Deep-dive with 5 phases, Zoom in, FAQ, Changelog). Mapped them to the spec's 9 IDs by redistributing content. Decision logged in `queue/runs/0102/decisions.md`.

4. **Responsive breakpoint for overlay right menu**: At 960px (not 820px) the CSS grid switches from two-column to single-column. The 820px viewport shots confirm the single-column layout renders correctly with the horizontal segmented toggle at the top.
