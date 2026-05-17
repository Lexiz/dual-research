---
spec: 0053
title: Tab system (3 variants) + table header
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.51.0
created: 2026-05-17
pr: ""
---

# Spec 0053 -- Tab system (3 variants) + table header

## Context

Ship 2 spec #2 of the Claude Design migration arc. SPEC-0052 landed
the primitive vocabulary (Button, Chip, SB, RunIDChip, Card,
AgentStrip, segmented ThemeToggle). This spec introduces the **Tab
primitive**, which subsumes the legacy components still alive in
production: `PaneButton` (spec 0046), `FilterChip` (errors.jsx),
run-list filter buttons, and `ChromeTab` (app.jsx top chrome). One
primitive, three variants, multiple sweeps.

Also lands the **table header distinction** (CMP-11) -- the `.tbl`
primitive gains `--bg-2` background + `--border-2` bottom border +
semibold weight + `--fg-2` text. The bespoke run-list grid header
also gets the same treatment.

## Design decisions

| # | Decision | One-liner |
| --- | -------- | --------- |
| D1 | **Add Tab + TabGroup sections to `components.css`** -- copy from brief's `styles/components.css` (Tab, tabs-line, tabs-solid). Also add table header styling. | Three variants per CMP-08: default (bordered pill), `tabs-line` (underline rail), `tabs-solid` (segmented control). |
| D2 | **Tab active state drops the 2 px info underline** (CMP-01) -- replaced with `--bg-2` fill + weight 600. | Brief's CSS handles this natively. |
| D3 | **New `Tab` + `TabGroup` React primitives in `shared.jsx`.** | Match brief's primitives.jsx API. Exposed on `window`. |
| D4 | **Migrate `PaneButton` call sites in run-detail.jsx** to `<Tab>` / `<TabGroup variant="solid">`. | PaneButton definition stays (legacy sweep is per-file in future specs). |
| D5 | **Migrate `FilterChip` in errors.jsx** to `<Tab>` with dot/count. | Uses default Tab variant with filter-chip pattern. |
| D6 | **Migrate run-list filter strip** to `<Tab dot filterTone count>`. | Inline-styled buttons become class-backed Tab primitives. |
| D7 | **Migrate `ChromeTab` in app.jsx** to Tab. | Top chrome tab uses default Tab variant. |
| D8 | **Run-list grid header + .tbl thead** get CMP-11 treatment. | `--bg-2` bg, `--border-2` bottom, semibold, `--fg-2` text. |
| D9 | **`PhaseTab` (dead code)** removed -- defined at run-detail.jsx:6547 but never called; all phase tab rendering uses PaneButton since spec 0046. |
| D10 | **Cache-bust bumped to `?v=0053`.** |

## Out of scope

- **Run list sort + URL state + attention promotion** (SUR-01..04) -- SPEC-0055.
- **Run detail header restructure** (SUR-05..08) -- SPEC-0056.
- **Modal primitive + sub-tabs (tabs-line consumer)** -- SPEC-0058.
- **Removing PaneButton/PaneButtonGroup definitions** -- call sites migrate here; definitions removed when next spec touches run-detail.jsx.

## Test plan

- 725 baseline pytest green (no Python changes).
- Preview-verify on partner-vetting (`3a4a`):
  - Critique pane Phase 2/4/Summary tabs render as tabs-solid.
  - Conversation/Consumption toggle works as tabs-solid.
  - Run-list filter strip renders with dot + count + filterTone.
  - Errors view filter chips render as Tab.
  - Top chrome tab renders.
  - Table headers visually distinct from rows in both themes.
- Both themes. Zero console errors. Cache-bust updated.

## Risks

- Tab is heavily used -- multiple surfaces migrate in one PR. Mitigation: preview-verify every surface.
- `tabs-solid` segmented control has light-mode overrides. Must test both themes.

## Brief mapping

`CMP-01` (Tab active state), `CMP-08` (Tab 3 variants), `CMP-11` (table header distinction).
