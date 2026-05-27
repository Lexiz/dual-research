---
spec: 0073
title: Question/Disagreement render unification + markdown rendering fix
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.66.0
created: 2026-05-18
pr: https://github.com/Lexiz/dual-research/pull/73
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0073 — Q/D render unification + markdown fix

## Context

Ship 7 of 9 in the tweak-cycle arc. Targets the **detail render** of
critique items — what the user sees when they expand a Question /
Disagreement / Issue / Comment card. Three problems:

1. **Disagreement detail** uses an old `CONTESTED POINT` + `PROGRESSION`
   timeline pattern that looks nothing like the QuestionThread cards used
   for questions. Should reuse the same turn-card pattern.
2. **Issue/Comment bodies** render raw text — `**bold**`, `*italic*`,
   `> blockquote` are visible as literal characters instead of styled.
3. **Quote fields** on Issues/Comments need a styled callout treatment.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Disagreement detail — rebuild via QuestionThread pattern** — replace `CONTESTED POINT` + `PROGRESSION` rendering with QuestionThread-style turn cards: contested point as question body, progression entries as turns with agent/round/action chips, resolution footer. Keep current positions section below. | Direct alignment with question detail. |
| D2  | **Extend QuestionThread with `kind` prop** — accepts `'question'` (default) or `'disagreement'`. For disagreements, turns display `step.action` as verdict, `step.note` as quote body. | One primitive for both views. |
| D3  | **Markdown wrap for Issue/Comment bodies (D4-D5 from draft)** — pipe bodies through `<Markdown text={...}>`. | Fixes raw **bold** and > blockquote rendering. |
| D4  | **QuoteCallout primitive** — styled callout for `.quote` fields on Issues/Comments. Left border + italic + muted bg. | Replaces inline italic rendering. |
| D5  | **Wrap disagreement step.note in Markdown** — progression notes may contain markdown formatting. | Consistent rendering. |
| D6  | **"Contested point" label → "Point"** — drop ALL-CAPS legacy label, use simple "Point" as SmallLabel text. | Vocabulary cleanup. |
| D7  | **Cache-bust to `?v=0073`** | Per arc convention. |
| D8  | **No backend changes.** | Frontend only. |

## Files touched

- `src/dual_research/ui/static/shared.jsx` — extend QuestionThread with `kind` prop; add QuoteCallout; expose on window.
- `src/dual_research/ui/static/run-detail.jsx` — rewrite DisagreementCard expanded body; Markdown wrap Issue/Comment bodies; QuoteCallout for quote fields.
- `src/dual_research/ui/static/components.css` — `.quote-callout` styling.
- `src/dual_research/ui/static/design-language.jsx` — spotlights for QuoteCallout.
- `src/dual_research/ui/static/index.html` — cache-bust.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- Three-axis filter strip — SPEC-0072.
- Phase 4 sub-section split — SPEC-0072.
- Critique pane summary copy — SPEC-0072.
- New question/disagreement aggregation — frontend rendering only.
- Issue/Comment metadata chip row refactor — deferred; current mono-text footer is functional.

## Test plan

- Baseline pytest green.
- Preview-verify on partner-vetting (3a4a):
  - Expand any Disagreement card → QuestionThread-style turn cards instead of old PROGRESSION.
  - Expand any Issue card → body renders markdown (no raw `**` or `>`).
  - Expand any Comment card → same as Issue.
  - Both themes; zero console errors.

## Risks

- Disagreement progression data shape may vary — fallback to raw text if step fields are missing.
- QuestionThread extension must not regress existing question rendering.

## Design system alignment (per arc M1)

- **QuestionThread API extended** — `kind` prop supports 'question' | 'disagreement'.
- **New primitive `<QuoteCallout>`** — styled callout for quote fields. Exposed on `window`. Spotlight added to design-language.jsx.
- **Markdown wrap pattern** — all critique card bodies now render via `<Markdown>`.
