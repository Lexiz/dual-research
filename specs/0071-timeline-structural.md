---
spec: 0071
title: Timeline structural pass — PhaseRail, phase headers, card size, collapsibility
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.64.0
created: 2026-05-18
pr: "https://github.com/Lexiz/dual-research/pull/71"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0071 — Timeline structural pass

## Context

Ship 5 of 9 in the tweak-cycle arc. Targets the **timeline pane**
(left side of run-detail) and parallel collapsibility on the critique
pane. Four user screenshots (14.23, 14.49, 14.57, 18.05).

## Design decisions (refined against main)

| #   | Decision | Rationale |
| --- | -------- | --------- |
| D1  | **PhaseRail label contrast** — completed-phase labels get `color: var(--ok)` (currently `--fg-3` for all non-current). Current-phase label already has `--fg-0`. | Fixes 14.23's readability. |
| D2  | **PhaseRail anchor positioning — DEFERRED** — the draft proposed IntersectionObserver to anchor pills to phase headers. Current PhaseRail uses compact dots+labels in a sticky column, which works well as navigation. Anchoring adds complexity with collapse interactions. Noted for follow-up. | Low ROI, high risk with D4 collapse interactions. |
| D3  | **PhaseRail sticky preserved** — no change to sticky behavior (SPEC-0057). | Don't regress. |
| D4  | **Phase header (PhaseDivider) collapsibility** — wrap each phase's cards in a CollapsibleSection. Default expanded. Click header toggles cards. Persist to localStorage per run+phase. | Per 14.23 + 18.05 collapsibility ask. |
| D5  | **Phase header visual standout** — border changes from `--border-1` to `--border-2`; add fontWeight 700 on label; slightly wider via negative margin (-4px each side). | Per 14.49 — header needs more visual separation. |
| D6  | **Reduce card vertical padding** — card base padding from `var(--s-3) var(--s-4)` (12px 16px) to `var(--s-2) var(--s-3)` (8px 12px). Cards become visually denser. | Per 14.49 — cards too tall. |
| D7  | **Small badge sizing bump + unification** — inline ok/issue badges on cards get unified styling: fontSize 11 (from 10.5), padding `2px 7px` (from `1px 6px`). Both pill + bordered variants use same style. | Per 14.57 — consistent, slightly larger. |
| D8  | **Critique pane section collapsibility** — DRIFT, OPEN, RESOLVED sections each wrapped in CollapsibleSection. Default expanded. Persist to localStorage per run+section. | Per 18.05. |
| D9  | **New `<CollapsibleSection>` primitive** — shared.jsx. Generic disclosure: `{ title, count?, countColor?, defaultOpen=true, persistKey?, onToggle?, children, renderTitle? }`. Renders header row + chevron + animated slot. | One primitive, two surface uses (D4, D8). |
| D10 | **Animation** — disclosure uses `max-height` transition 180ms, respecting `prefers-reduced-motion`. | Polish. |
| D11 | **Cache-bust to `?v=0071`** | Arc convention. |

## Files touched

- `src/dual_research/ui/static/shared.jsx` — add `<CollapsibleSection>` primitive, expose on window.
- `src/dual_research/ui/static/run-detail.jsx` — PhaseRail label contrast (D1); PhaseDivider collapsibility (D4); PhaseDivider visual standout (D5); critique pane section wrappers (D8); badge unification (D7).
- `src/dual_research/ui/static/components.css` — card padding reduction (D6); CollapsibleSection CSS; phase-rail label contrast rule for completed.
- `src/dual_research/ui/static/design-language.jsx` — CollapsibleSection spotlight (M1).
- `src/dual_research/ui/static/index.html` — cache-bust.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- PhaseRail anchor positioning (D2 deferred — noted for follow-up).
- Three-axis filter strip — SPEC-0072.
- Summary panel copy — SPEC-0072.
- Phase 4 Issues/Comments split — SPEC-0072 (will reuse CollapsibleSection).
- Disagreement detail-modal rewrite — SPEC-0073.

## Test plan

- 744 baseline pytest green.
- Preview-verify on partner-vetting (`3a4a`):
  - PhaseRail: completed labels readable in both themes (green text).
  - Phase headers visually distinct (darker border, bolder label, slightly wider).
  - Click phase header -> cards collapse. Click again -> expand. Reload preserves.
  - Cards have less vertical padding; content still legible.
  - Small badges: consistent pill style, slightly larger.
  - Critique pane: DRIFT, OPEN, RESOLVED sections each collapsible.
- Reduced-motion: disclosure animations disabled.
- Both themes; zero console errors.

## Risks

- Card padding reduction (D6) affects all Card usages globally — verify modal cards, compare view cards still look right.
- CollapsibleSection localStorage keys must not collide with existing `dr_onboarded` etc.

## Design system alignment (per arc M1)

- **New primitive `<CollapsibleSection>`** — exposed on window. Spotlight added to design-language.jsx.
- **Card padding tokens** — reduced via CSS class change (component-level, not token-level — simpler).
- **PhaseRail label contrast** — completed state gets semantic `--ok` color via CSS class rule.
