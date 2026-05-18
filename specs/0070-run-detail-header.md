---
spec: 0070
title: Run-detail header — agent strip equalization, phase-tab info hierarchy, remove blocking banner
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.63.0
created: 2026-05-18
pr: "https://github.com/Lexiz/dual-research/pull/70"
---

# Spec 0070 — Run-detail header restructure

## Context

Ship 4 of 9 in the tweak-cycle arc. Targets the run-detail page's
top header band across three user-flagged areas:

- Agent strip pills are unequal width due to differing model string
  lengths. User wants both pills the same width, with vertical reduction.
- The blocking-item callout banner (`N open . M ghosted . click to jump`)
  is "completely useless" — remove it.
- Phase tab strip crams all info into one tab label ("PHASE 2 Negotiate
  . 26 Q . 10 D") — restructure with chip clusters for better hierarchy.

Depends on SPEC-0067 (chip vocabulary) and SPEC-0068 (brand icons).

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **AgentStrip equalized** — both pills get `flex: 1 1 0` so they share width equally. | Fix lopsidedness. |
| D2  | **AgentStrip vertical reduction** — reduce padding from `var(--s-2) var(--s-3)` to `4px var(--s-3)`. | "Way too big vertically." |
| D3  | **AgentStrip internal layout unchanged** — left: icon + name + model; right: tokens . cost . status. Already correct. | No props change needed. |
| D4  | **Remove BlockingItemCallout** — delete the component and its usage. Same info lives in critique pane. | Per user: "completely useless." |
| D5  | **Header stays two rows** — removing the banner doesn't collapse rows (banner was between header and main content, not inside header). Net gain: ~32px vertical. | Scope discipline. |
| D6  | **Phase tab strip restructure** — each tab gets structured chips: `[Phase N] [Label] [X questions] [Y disagreements]` using Chip primitives inside the Tab body. | Fix cramped single-string approach. |
| D7  | **Phase tab active vs inactive** — inactive tab count chips use muted `var(--fg-3)` text; active at full opacity. | Clear focal point. |
| D8  | **Count chips show 0 explicitly** — `0 questions` renders muted, not hidden. | Predictable layout. |
| D9  | **Phase tab counts use full words** — `26 questions`, `10 disagreements` not `26 Q` / `10 D`. | Consistency with SPEC-0067. |
| D10 | **ReconcileChip 5-state preserved** — explicit no-touch. | Hard constraint. |
| D11 | **Cache-bust bumped to `?v=0070`.** | Per arc convention. |
| D12 | **No backend changes.** | Frontend only. |

## Files touched

- `src/dual_research/ui/static/run-detail.jsx` — Remove BlockingItemCallout usage; restructure phase-tab rendering.
- `src/dual_research/ui/static/shared.jsx` — AgentStrip: no API change needed (equalization done via parent flex).
- `src/dual_research/ui/static/components.css` — `.as` padding reduction (D2).
- `src/dual_research/ui/static/design-language.jsx` — Update AgentStrip spotlight (M1).
- `src/dual_research/ui/static/index.html` — cache-bust.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- PhaseRail (vertical green strip) — SPEC-0071.
- Critique-pane filter strip — SPEC-0072.
- Timeline phase header band styling — SPEC-0071.
- Modal AgentStrip usage — propagates automatically from CSS change.

## Test plan

- 744 baseline pytest green.
- Preview-verify on partner-vetting (`3a4a`):
  - Header: Claude + GPT pills visually identical in width.
  - Banner row gone — timeline starts immediately after header.
  - ReconcileChip still renders in its correct state.
  - Drafter pill still visible.
  - Phase tab strip: each tab shows structured chips with full words.
  - Active phase tab visually distinct from inactive.
- Both themes; zero console errors.
- Cache-bust + `/api/health`.

## Risks

- Header height reflow — removing banner shifts timeline up ~32px. PhaseRail anchors should handle this fine.
- AgentStrip equalization may push right-side header content narrower at small viewports. Verify at 1280px.

## Design system alignment (per arc M1)

- **`<AgentStrip>` CSS update** — padding reduction codified in `.as` class in `components.css`.
- **Phase tab chip-cluster pattern** — documented usage pattern ("structured chips inside Tab body") codified in the phase tab rendering.
- **BlockingItemCallout pattern retired** — no longer part of the system.
- **AgentStrip spotlight updated** in `design-language.jsx` to reflect the denser default.
