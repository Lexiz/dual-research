---
spec: 0075
title: Consumption tab agent-card restructure — equal-height, data-top-bars-bottom, wider bars
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.68.0
created: 2026-05-18
pr: https://github.com/Lexiz/dual-research/pull/75
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0075 — Consumption tab agent-card restructure

## Context

Ship 9 of 9 in the tweak-cycle arc (closing spec). Targets the
**Consumption tab** which the user described as "wrongly made" across
two screenshots:

- **`20.14`** — the P2 Negotiate row. Two cards (Claude orange,
  GPT green) at different vertical heights because Claude has more
  breakdown rows than GPT. When expanded, the structure is wrong —
  the user expects: data points TOP, total bar BOTTOM (of the
  collapsed view); on expand, the additional breakdown bars + their
  costs cascade DOWNWARD inside the SAME card. Currently the layout
  has bars mid-card with data above + below, and expansion creates
  inconsistent jumping.
- **`20.18`** — the same problem across multiple phase rows. The
  view feels "jumpy from left to right"; bars not aligned across
  phases; no visual rhythm.

The user also wants the bars **wider** — the slack space between
`P2 Negotiate` text and where the bar starts should be reclaimed and
split between Claude and GPT bars.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Agent cards equal height** — both cards in the expanded phase row already use `align-items: stretch` grid. Verify this works correctly with the new layout. | Direct fix to 20.14's lopsidedness. |
| D2  | **Card internal layout — data+costs at top, bars at bottom** — metrics chips + cost line grouped at top, then divider, then bars zone. | Per user's direction. |
| D3  | **Total bar visible in collapsed ConsumptionRow** — add a compact total bar to each lane cell in the collapsed row. | Per user — collapsed should already show the bar. |
| D4  | **Bar cascade on expand** — expanded card shows total bar + breakdown bars below the data zone. Card grows downward only. | Per user's direction. |
| D5  | **Bar widening** — reduce phase-label column from 160px to 100px; reduce bar label columns from 140px to 100px. | Per user — "increase these bars, there is space." |
| D6  | **Phase-label column token** — add `--consumption-label-w` token to tokens.css. | Avoids magic numbers. |
| D7  | **Design system spotlight** — add Consumption card miniature to design-language.jsx ComponentSpotlights. | Per M1. |
| D8  | **Cache-bust to `?v=0075`.** | Per arc convention. |
| D9  | **No backend changes.** | Frontend only. |

## Files touched

- `src/dual_research/ui/static/run-detail.jsx` — ConsumptionCard zone reordering, TokenLaneCell total bar addition, bar column widths
- `src/dual_research/ui/static/components.css` — `.consumption-card` class for the three-zone layout
- `src/dual_research/ui/static/tokens.css` — `--consumption-label-w` token
- `src/dual_research/ui/static/design-language.jsx` — Consumption card spotlight
- `src/dual_research/ui/static/index.html` — cache-bust
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`

## Out of scope

- Aggregator output structure — no API changes.
- New input slot types / new metrics.
- Cross-run consumption dashboard.
- Cost reconciliation logic.
- Phase-row level collapsibility redesign.

## Test plan

- 744 baseline pytest green.
- Preview-verify on partner-vetting (`3a4a`): all phase rows render correctly with data at top, bars at bottom.
- Both themes; zero console errors.

## Risks

- Taller collapsed rows due to inline total bar — acceptable trade-off for better data density.
- Phase-label column at 100px may truncate long labels — acceptable with text-overflow: ellipsis.

## Design system alignment (per arc M1)

- **`--consumption-label-w` token** in tokens.css for phase-label and bar-label column widths.
- **`.consumption-card` CSS class** in components.css for the three-zone vertical layout.
- **Consumption card spotlight** added to design-language.jsx ComponentSpotlights.
