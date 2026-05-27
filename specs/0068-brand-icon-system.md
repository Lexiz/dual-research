---
spec: 0068
title: Brand-icon system + Design-page DNA reskin
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.61.0
created: 2026-05-18
pr: https://github.com/Lexiz/dual-research/pull/68
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0068 — Brand-icon system + Design-page DNA reskin

## Context

Ship 2 of 9 in the tweak-cycle arc. Foundation spec B (paired with 0067). Two coupled workstreams:

1. **Brand-icon primitive + migration** — adds `<BrandMark>` primitive and migrates every surface that identifies Claude / OpenAI's GPT to use official brand marks instead of the existing `AgentIcon` tile treatment.
2. **Design page DNA reskin** — replaces the current full-reference design language page with a curated DNA one-pager. Full reference preserved at `?full=1`.

The DNA page becomes the **live source-of-truth for the design system** from this spec onward.

## Design decisions

| #   | Decision | Rationale |
| --- | -------- | --------- |
| D1  | New `<BrandMark name size variant>` primitive in shared.jsx | Single primitive subsumes every agent-icon swap |
| D2  | `BRAND_SVGS` dict in shared.jsx — single source of truth for SVG paths | Avoid path duplication |
| D3  | Colors: solid uses agent brand color, ghost uses tinted variant | Preserve existing brand fidelity |
| D4  | `AgentIcon` reimplemented to delegate to `<BrandMark>` | Lowest-risk migration — existing call sites unchanged |
| D5  | `AgentStrip` updated to use `<BrandMark>` via its existing monogram render | Single edit, broad reach |
| D6  | Run-list dual-color square replaced with two adjacent BrandMark halves | Per user direction |
| D7  | Critique-card attribution chips get BrandMark prefix | Continuity across all agent-identifying surfaces |
| D8  | Modal header agent stripe uses BrandMark | Style consistency |
| D9  | CodeCluster agent chip gets BrandMark | Foundation specs compose cleanly |
| D10 | Design page reuses the primitive — no duplicate SVG paths | Source unified |
| D11 | AgentDuoVisual + DemoRunCapsule untouched | Per user direction |
| D12 | All SVG paths inline — no CDN, no img tags | Offline-friendly |
| D13 | Accessibility: aria-label on identifying, aria-hidden on decorative | A11Y-01 carry-over |
| D14 | Cache-bust bumped to `?v=0068` | Arc convention |
| D15 | DNA one-pager as default Design page; full reference at `?full=1` | Replace outdated full reference with curated tour |
| D16 | DNA sections: Hero, Palette, Brand marks, Component spotlights, Construction | Curated showcase |
| D17 | Component spotlight scaffolding with "add new entries here" comment | M1 mandate operationalized |
| D18 | Accessibility on DNA page: heading levels, keyboard navigation | A11Y-01 + A11Y-02 |

## Files touched

- `src/dual_research/ui/static/shared.jsx` — `<BrandMark>` primitive + `BRAND_SVGS` dict; `AgentIcon` delegates to BrandMark; expose on window
- `src/dual_research/ui/static/design-language.jsx` — DNA one-pager restructure + FullReference at `?full=1`
- `src/dual_research/ui/static/run-list.jsx` — dual-color gradient → BrandMark composition
- `src/dual_research/ui/static/components.css` — DNA page styling
- `src/dual_research/ui/static/index.html` — cache-bust `?v=0068`
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`

## Out of scope

- AgentDuoVisual in auth.jsx and onboarding.jsx — user-vetoed
- Run-list status badges — use status colors, not agent colors
- App's own "dual-research" wordmark — separate brand concern
- Adding spotlights for primitives not yet shipped (CollapsibleSection from 0071, QuoteCallout from 0073) — scaffolding only
- Backend changes — none

## Test plan

- 744 baseline pytest green (no new Python tests).
- Preview-verify on partner-vetting (`3a4a`): brand marks in AgentStrip, timeline cards, critique cards, modal headers.
- Design page: DNA one-pager at default route; `?full=1` shows full reference.
- Both themes; ghost variant readable.
- Zero console errors.

## Risks

- SVG quality at size 12 — verify OpenAI knot doesn't turn to mud
- Run-list dual composition — two BrandMarks side-by-side may need size tuning
- Visual regression in critique-card density from 12px brand marks

## Design system alignment

- **New primitive**: `<BrandMark name size variant>` exposed on window
- **BRAND_SVGS dict**: single source of truth for brand glyphs
- **AgentIcon**: thin wrapper delegating to BrandMark (backward compat)
- **DNA page = live SoT** for design system
- **Component spotlight scaffolding** for future specs
- **Construction principles codified**: token-only colors, full-word vocabulary, brand fidelity
