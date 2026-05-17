---
spec: 0056
title: Run detail header + chrome restructure + ActiveRunChip
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.54.0
created: 2026-05-17
pr: ""
---

# Spec 0056 — Run detail header + chrome restructure

## Context

Ship 2 surface spec #2. Four V2 changes to the chrome bar and the
run-detail header (SUR-05..08):

1. Chrome bar right cluster currently has five different button styles in 600 px. Unify the visual language with consistent styling.
2. Active-run chip in chrome when in run-detail -- single-click back to list.
3. Run-detail header: equal-row paddings (12/16) + drafter callout pill.
4. Blocking-item callout under the agent strips.

Depends on SPEC-0053 (Tab system) for the chrome unification.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Chrome bar right cluster** (SUR-05) -- unify visual styling across ConnectionPill, AppVersionChip, HowItWorksLink, ThemeToggle, AvatarMenu. Apply consistent padding, borders, hover states, and font sizes. Use `Tab` primitive for HowItWorks link. Keep utility controls (ConnectionPill, ThemeToggle, AvatarMenu) as styled buttons since they aren't semantically tabs. | Unified visual language across the chrome cluster. |
| D2  | **ActiveRunChip** (SUR-06) -- when route is `runs/<id>`, render a chip in the chrome right cluster showing the short run ID (first 4 hex chars) with arrow-left icon. Click navigates back to run list. Hidden on run-list view. Uses `RunIDChip` primitive from SPEC-0052. | Single-click back navigation from chrome. |
| D3  | **Run-detail header restructure** (SUR-07) -- two-row header with equal padding (12px vertical, 20px horizontal). Row 1: topic title + cost chip + reconcile chip + search summary + status pill. Row 2: phase dots + drafter callout pill + relative-time meta. | Normalizes density inconsistency. |
| D4  | **Drafter callout pill** -- `<Chip>` with agent tone + AgentIcon + "Claude drafter" / "GPT drafter" label. Sits in row 2 of the header. Hidden when `run.drafter` is null. | Uses SPEC-0052 Chip + AgentIcon primitives. |
| D5  | **Blocking-item callout** (SUR-08) -- when run has open standing items in phaseLedgers, render a callout bar between header and main content: "N open . M ghosted". Clickable, scrolls to first open item in the critique pane. Hidden when no open items. | Attention cue at the detail level. |
| D6  | **No structural changes to the timeline or critique panes.** | Scope discipline. |
| D7  | **AgentStrip primitive adoption** -- Timeline pane's bespoke inline-styled agent pills migrate to the class-backed `AgentStrip` from SPEC-0052's shared.jsx. | Adopts primitive. |
| D8  | **Cache-bust bumped to `?v=0056` in index.html.** | Per arc convention. |

## Files touched

- `src/dual_research/ui/static/run-detail.jsx` -- header restructure (two-row, drafter pill, blocking callout), AgentStrip adoption.
- `src/dual_research/ui/static/app.jsx` -- chrome bar right-cluster visual unification, ActiveRunChip wiring.
- `src/dual_research/ui/static/index.html` -- cache-bust.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- **Timeline + critique surface rework** (SUR-09..11) -> SPEC-0057.
- **Modal restructure** -> SPEC-0058.
- **Keyboard contract** -> SPEC-0059.
- **Run-list attention promotion** -> SPEC-0055 (already shipped).
- **Noted for follow-up:** none.

## Test plan

- 725 baseline pytest green.
- Preview-verify on partner-vetting (`3a4a`):
  - Header row 1: topic + cost chip + status pill all aligned, 12/16 padding.
  - Header row 2: phase dots + drafter callout + elapsed time, aligned.
  - Drafter callout shows "Claude drafter" with sable agent color.
  - Blocking-item callout shows correct count.
  - Chrome bar right cluster renders with unified visual styling.
  - ActiveRunChip shows run ID when in run-detail; hidden on run-list.
  - Click ActiveRunChip -> navigates back to run list.
- Both themes.
- Zero console errors.
- ReconcileChip 5-state preservation.
- `/api/health` reports new version.

## Risks

- **AgentStrip migration** could change layout if min-width tokens shift.
- **Drafter callout fallback** when `run.drafter` is null -- hide entirely.
- **Blocking-item callout count source** -- uses ledger entries from spec 0043 (run.phaseLedgers).

## Brief mapping

`SUR-05` (chrome right cluster), `SUR-06` (ActiveRunChip), `SUR-07` (header restructure + drafter pill), `SUR-08` (blocking callout).
