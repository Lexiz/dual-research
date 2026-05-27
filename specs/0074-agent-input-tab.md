---
spec: 0074
title: Agent Input tab rework — rename, reorder, structural restructure
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.67.0
created: 2026-05-18
pr: https://github.com/Lexiz/dual-research/pull/74
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0074 — Agent Input tab rework

## Context

Ship 8 of 9 in the tweak-cycle arc. Targets the **modal Input tab** which
needs renaming, reordering, and structural improvements:

- **Rename** "Input" to "Agent Input" in all modal contexts (top-level
  modal tabs AND the left-pane sub-tabs in negotiate/draft modals).
- **Reorder** so Agent Input is the first tab in full-view modals
  (preflight input, preflight response, output modals).
- **Reorder entries** inside the panel: System Prompt first (collapsed),
  User Prompt second (expanded), remaining entries after.
- **Use CollapsibleSection** from SPEC-0071 instead of the hand-rolled
  disclosure widget for consistent disclosure UX across the app.
- **Improve empty state** for pre-0033 runs: show a meaningful message
  instead of just "bundle not recorded".
- **Render via Markdown** instead of raw `<pre>` for better readability.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Rename "Input" -> "Agent Input"** in all modal tab labels and sub-tab labels. | Per briefing 15.13. |
| D2  | **Reorder modal tabs** so Agent Input is first. Update `TABS_CANON` ordering to `['input', 'content', 'webSearch', 'sources', 'files']`. | Per briefing 15.13. |
| D3  | **Reorder entries** inside InputTabContent: system first (collapsed by default), brief second (expanded), then rest. This matches "System Prompt first, User Prompt second" from the briefing. | Current order already has brief first, system second. Swap. |
| D4  | **Use CollapsibleSection** primitive from SPEC-0071 for entry collapsibility instead of the hand-rolled button+state in InputSection. Consistent disclosure UX. | Design system alignment. |
| D5  | **Render body via Markdown** instead of raw `<pre>`. Input pieces are often markdown-formatted text (briefs, system prompts). | Consistency with SPEC-0073 markdown rendering. |
| D6  | **Improve empty state** — when bundle is missing, show "Agent input bundle was not recorded for this run." with a dashed-border empty state. No fake system prompt injection. | D3 from draft scaled back: we don't have a reliable source for a "default" system prompt for old runs, and hardcoding one is brittle. |
| D7  | **NegotiateLeftSubTabs** — rename 'Input' -> 'Agent Input' in the left-pane sub-tabs too. | Consistency. |
| D8  | **ArtifactHeader for input kind** — rename the timeline card header from "Input" to "Agent Input". | Consistency. |
| D9  | **Cache-bust to `?v=0074`**. | Arc convention. |
| D10 | **CollapsibleSection spotlight** already exists from SPEC-0071. No new spotlight needed — reuse existing. | M1 alignment. |

## Out of scope (noted for follow-up)

- **Child Pages as sibling entries** (D7 from draft) — the input bundle data shape has no "child page" concept. The `pieces` dict has keyed entries (`system`, `brief`, `d1`, `d2`, etc.) with no URL/resource metadata. Implementing child-page rendering requires backend changes to the input bundle format. Deferred.
- **External resource mention extraction** (D6 from draft) — parsing chat content for URLs/Notion links requires a new parser + backend support. Deferred.
- **Sources/Files tab merge** — kept separate per draft D11 recommendation.
- **Search palette compatibility** — search palette doesn't index tab names; no change needed.
- **Backend changes** — no aggregator changes. The input bundle API is unchanged.

## Files touched

- `src/dual_research/ui/static/run-detail.jsx` — tab rename + reorder + InputSection refactor + Markdown rendering + entry reorder + empty state.
- `src/dual_research/ui/static/components.css` — `.agent-input-entry` class for input section styling.
- `src/dual_research/ui/static/design-language.jsx` — note in Component Spotlights about Agent Input panel pattern.
- `src/dual_research/ui/static/index.html` — cache-bust.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Test plan

- 744 baseline pytest green.
- Preview-verify on partner-vetting (`3a4a`):
  - Modal tabs order: `Agent Input` first, then Content, etc.
  - System Prompt entry collapsed by default, User Prompt expanded.
  - Markdown rendering for entry bodies.
  - Left-pane sub-tabs show "Agent Input" label.
  - Timeline card header says "Agent Input".
- Both themes; zero console errors. Cache-bust + `/api/health`.

## Risks

- **Tab reorder may surprise users** who expect Content first — low risk since the briefing explicitly requested Agent Input first.
- **Markdown rendering of system prompts** may have formatting artifacts if the system prompt has unusual markup — mitigated by the existing Markdown component being battle-tested.

## Design system alignment (per arc M1)

- **Modal sub-tab ordering rule** — "Agent Input first" becomes a system rule. Codified in `TABS_CANON` order.
- **CollapsibleSection reuse** — Agent Input entries now use the same CollapsibleSection primitive as timeline phase headers and critique sections.
- **`.agent-input-entry`** CSS class added to components.css for input entry styling, replacing inline styles.
- **Entry order convention** — System Prompt first (collapsed), User Prompt second (expanded), remaining in canonical order.
