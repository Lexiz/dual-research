---
spec: 0057
title: Timeline + critique restructure (PhaseRail + ChipCluster + 3-axis filter + DriftCluster + Summary panel + CardHeadline migration)
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.55.0
created: 2026-05-17
pr: https://github.com/Lexiz/dual-research/pull/61
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0057 — Timeline + critique restructure

## Context

Ship 2 surface spec #3. Restructures the timeline pane + critique pane in
run-detail.jsx. Five V2 changes (SUR-09..11, SUR-14) plus the deferred
CardHeadline migration from SPEC-0052 D10.

1. **Sticky PhaseRail** — persistent indicator of current phase down the timeline pane left edge.
2. **ChipCluster discipline** — max 5 chips per row; overflow collapses to `+N`.
3. **Three-axis critique filter** — kind + agent + status. Plus a dedicated DriftCluster group.
4. **Summary panel enhancement** — highest-leverage open thread renders as the panel's opening artifact.
5. **CardHeadline migration** — inline-styled badges migrate to Chip primitives.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Sticky PhaseRail** (SUR-09) — vertical rail down the timeline pane left edge, sticky-positioned, shows current phase + completed/upcoming phases. Click a phase to scroll the timeline to that section. | New component in run-detail.jsx; reads `run.phases` data and `PHASES` constant. |
| D2  | **ArtifactCard → Card primitive migration** (SUR-09) — timeline cards migrate from inline-styled `<div>` to `<Card interactive>` / `<Card live agent>`. Live cards use Card.live variant. | Uses SPEC-0052 Card/CardBody primitives. |
| D3  | **ChipCluster** (SUR-10) — new `<ChipCluster max={5}>` wrapper. Overflow surfaces as `+N` button. | New component in shared.jsx; CSS in components.css. |
| D4  | **Three-axis critique filter** (SUR-11) — add agent (All/Claude/GPT) and status (All/Open/Resolved/Drift) axes. All three axes independent TabGroups. Filter logic AND-combines. | Three rows of Tabs above the critique card list. |
| D5  | **DriftCluster** (SUR-11) — ghosted items get their own group above OPEN/RESOLVED. Renders only when there are drift items. | Separate visual group; same Card rendering. |
| D6  | **Summary panel enhancement** (SUR-14) — highest-leverage open thread (most ghosted rounds) renders as QuestionThread at top of summary. | Uses existing QuestionThread primitive. |
| D7  | **CardHeadline → Chip migration** (SPEC-0052 D10 deferred) — kind badge and status badge migrate from inline `<span>` to `<Chip tone>`. Uses `toneFromAccent` helper. | Resolves SPEC-0052 carve-out. |
| D8  | **PaneButton + PaneButtonGroup removal** — SPEC-0053 migrated all call sites to Tab. Grep confirms zero remaining references. Delete the orphan definitions. | Cleanup. |
| D9  | **No backend changes.** All data from existing `run.questions` / `run.phaseLedgers` / `run.disagreements`. | Scope discipline. |
| D10 | **Cache-bust to `?v=0057`.** | Per arc convention. |
| D11 | **TimelineAgentPill unchanged** — SPEC-0056 already migrated to shared AgentStrip. No further changes needed. | Per SPEC-0056 handover. |

## Files touched

- `src/dual_research/ui/static/run-detail.jsx` — PhaseRail, Card migration, ChipCluster adoption, 3-axis filter, DriftCluster, Summary enhancement, CardHeadline migration, PaneButton removal.
- `src/dual_research/ui/static/shared.jsx` — new ChipCluster component.
- `src/dual_research/ui/static/components.css` — append `.cc` (ChipCluster) + `.phase-rail` sections.
- `src/dual_research/ui/static/index.html` — cache-bust.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- **Modal restructure** → SPEC-0058.
- **Keyboard contract / shortcuts overlay / cmd-K palette** → SPEC-0059.
- **Cross-run dashboards** → SPEC-0060.
- **Aggregator / wire-format changes** — frontend-only.

### Noted for follow-up

(None so far.)

## Test plan

- 725 baseline pytest green.
- Preview-verify on partner-vetting (3a4a):
  - PhaseRail renders down timeline pane left edge with phase indicators.
  - Click phase in rail scrolls timeline to that section.
  - Critique pane has 3-axis filter (kind / agent / status).
  - DriftCluster group renders above OPEN/RESOLVED when drift items exist.
  - Summary tab shows highest-leverage thread.
  - CardHeadline renders with Chip primitives.
  - ChipCluster collapses >5 chips into `+N`.
- Both themes. Zero console errors. ReconcileChip 5-state preserved.

## Risks

- **Single-spec scope size** — biggest spec in the arc. Implement in layers.
- **Sticky positioning** — needs explicit scroll-relative parent. Timeline scroll container identified at line 848 of run-detail.jsx.
