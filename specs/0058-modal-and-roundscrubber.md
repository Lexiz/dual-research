---
spec: 0058
title: Modal primitive (single + split) + sub-tabs + RoundScrubber + provider-symmetric SourceCard
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.56.0
created: 2026-05-17
pr: ""
---

# Spec 0058 — Modal + RoundScrubber + SourceCard

## Context

Ship 3 spec #1. The brief's CMP-06 modal primitive + two surface
features (SUR-12 RoundScrubber, SUR-13 provider-symmetric
SourceCard) all live in or open from the modal layer.

The current modal in shared.jsx uses inline styles. This spec
consolidates onto a CSS-class-backed `.dr-modal` primitive with two
variants (single + split), adopts `tabs-line` for sub-tabs (uses
SPEC-0053's Tab system), adds a RoundScrubber for walking turns
without closing, and makes the ConsultedSourceCard provider-symmetric
(closes the spec 0038 Anthropic/OpenAI rendering asymmetry).

Note: SPEC-0057 removed PaneButton/PaneButtonGroup. This spec uses
Tab/TabGroup instead for all sub-tab strips.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Add Modal CSS sections to `components.css`** -- `.dr-backdrop` (position fixed, theme-aware opacity), `.dr-modal` base (max 1100, bg-1, border-2, r-4, e-2 shadow, 3px agent-color left border), `.dr-modal.is-split` (max 1280), `.dr-modal-header`, `.dr-modal-body`, `.dr-modal-tabs`, `.dr-modal-split` (1fr 1fr grid), `.dr-modal-pane`. | Brief section 8.10. |
| D2  | **Refactor `Modal` React primitive in `shared.jsx`** -- Replace inline styles with CSS classes. New props: `variant: 'single' \| 'split'` (default single), `agent: 'a' \| 'b' \| null` (for left border color). Backdrop click + Esc closes. Focus trap (capture on mount, return on unmount, tab cycles within modal). Existing `tabs` prop replaced with `tabStrip` render prop for caller-controlled tab strips. | One primitive replaces all bespoke modal layouts. |
| D3  | **Migrate every modal in run-detail.jsx to the class-backed `<Modal>`**: DocumentModal (single), NegotiateReviewModal (split), DraftReviewModal (split), InputBriefModal (single), PreflightResponseModal (single). | Pure JSX swap; rendering content stays bespoke. |
| D4  | **Sub-tabs using `tabs-line` variant** (SPEC-0053) -- wherever modals currently have inline-styled tab strips (NegotiateLeftSubTabs, DraftRightSubTabs, NegotiateDocTabs), migrate to `<TabGroup variant="line">` + `<Tab>`. | Uses Tab system; tabs-line is the brief's "minimal underline rail" intended for modal sub-tabs. |
| D5  | **RoundScrubber** (SUR-12) -- new component at the bottom of side-by-side modals. Shows available round numbers as clickable pills with prev/next arrows. Click a round number to switch the modal content to that round's turn. Reads timeline items from the run to determine available rounds for the current phase/agent. | New component; reads existing timeline data. |
| D6  | **Provider-symmetric ConsultedSourceCard** (SUR-13) -- current card renders Anthropic richly (title + host + page_age + cited_text) and OpenAI sparsely (URL-only). Symmetrize: both providers render `title (or URL fallback) + host chip + page_age chip (when available) + cited_text block (when available) + [cited] tag`. Where data is missing, render a muted placeholder. | Closes spec-0038 asymmetry. |
| D7  | **Cache-bust bumped to `?v=0058` in index.html.** | Per arc convention. |
| D8  | **No backend changes.** | Scope discipline. |

## Files touched

- `src/dual_research/ui/static/components.css` -- append `.dr-modal*` + `.dr-backdrop` sections, `.round-scrubber` section.
- `src/dual_research/ui/static/shared.jsx` -- refactor `Modal` primitive to CSS-class-backed.
- `src/dual_research/ui/static/run-detail.jsx` -- migrate all modals; migrate sub-tabs to TabGroup line; add RoundScrubber; symmetrize ConsultedSourceCard.
- `src/dual_research/ui/static/index.html` -- cache-bust ?v=0058.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- **Full keyboard contract** (Esc closes is part of D2; j/k/shortcuts overlay = SPEC-0059).
- **Cross-run dashboards** -> SPEC-0060.
- **New wire formats for source data** -- frontend-only symmetrization.

### Noted for follow-up

(None discovered yet.)

## Test plan

- 725 baseline pytest green.
- Preview-verify on partner-vetting (3a4a):
  - Click Phase 2 critique card -> NegotiateReviewModal opens via `<Modal variant="split">` with agent-color left border.
  - Click Phase 1 draft -> DraftReviewModal opens.
  - Click any Document -> DocumentModal opens.
  - All modals close on backdrop click + Esc.
  - Sub-tabs render via TabGroup line variant.
  - RoundScrubber at bottom of split modals; clicking rounds switches content.
  - ConsultedSourceCard renders symmetrically for both providers.
  - Backdrop tokens correct in both themes.
- Both themes.
- Zero console errors.
- `/api/health` reports new version.

## Risks

- **Modal migration breadth** -- 5+ modals need migration without regressing content layout.
- **Focus trap** -- simple impl (capture on mount, return on unmount).
- **RoundScrubber data dependency** -- needs round-indexed access to timeline items.
- **SourceCard data gaps** -- missing fields render as muted placeholders.

## Brief mapping

`CMP-06` (Modal single + split + agent-color left border), `SUR-12` (Modal RoundScrubber), `SUR-13` (provider-symmetric SourceCard).
