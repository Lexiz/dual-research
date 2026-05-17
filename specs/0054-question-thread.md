---
spec: 0054
title: QuestionThread + QuestionRef + AP-01 enforcement
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.52.0
created: 2026-05-17
pr: "https://github.com/Lexiz/dual-research/pull/58"
---

# Spec 0054 — QuestionThread + QuestionRef + AP-01

## Context

The biggest visible design move in the design-system arc (per brief S9). Two new primitives + one anti-pattern enforcement.

**QuestionThread** is a vertical turn-by-turn conversation timeline that lives inside unfolded critique cards. It surfaces "who raised the question, who responded in which round, with what verdict" at full fidelity.

**QuestionRef** decodes the legacy `Q-g-r1-04` database keys into legible chrome — codifies AP-01 anti-pattern (cryptic IDs leaking the database).

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | Add QuestionThread + QuestionRef sections to `components.css` | Copy from brief's CSS (~230 lines). Includes timeline `::before` dashed-rail, per-turn-kind dot styling, QuestionRef compact + full layouts. |
| D2 | New `QuestionThread` + `QuestionRef` + `parseQId` in `shared.jsx` | From brief's `primitives.jsx`. parseQId decodes legacy `Q-g-r1-NN` strings. |
| D3 | `QuestionThread` API: `id`, `status`, `question`, `turns`, `footer`, `statusChips` | Matches brief S9.7. |
| D4 | `QuestionRef` two formats: compact `Q . 04` and full `Q . 04 . [GPT] . r1` | Default compact. Auto-parses legacy IDs. |
| D5 | Wire `QuestionThread` inside QuestionCard expanded body | When a question card unfolds, render `<QuestionThread>` as the primary body, replacing the old flat body + metadata. Turns derived from question fields (raisedBy, raisedRound + answeredBy, answeredRound). |
| D6 | Derive turns from question fields in the frontend | No wire-format changes. Build turns array from existing `q.raisedBy`, `q.raisedRound`, `q.answeredBy`, `q.answeredRound`, `q.body`, `q.answerBody`, `q.quote` fields. Origin turn from raiser, response turn from answerer when present. Ghosted rounds from ledger entry. |
| D7 | Replace `q.id` in CardHeadline with `<QuestionRef>` | AP-01 enforcement. CardHeadline's publicId for questions now renders decoded QuestionRef instead of raw `Q-c-r1-01` string. |
| D8 | Add `.sentp` (sentiment paragraph) CSS from brief | Small addition (~2 lines) from the brief's components.css, used for question body presentation. |
| D9 | Cache-bust to `?v=0054` in index.html | Per arc convention. |

## Files touched

- `src/dual_research/ui/static/components.css` — append QuestionThread + QuestionRef + sentp sections (~230 lines from brief).
- `src/dual_research/ui/static/shared.jsx` — add `QuestionThread`, `QuestionRef`, `parseQId`; export on `window`.
- `src/dual_research/ui/static/run-detail.jsx` — wire QuestionThread inside QuestionCard expanded body; replace raw IDs with QuestionRef in CardHeadline.
- `src/dual_research/ui/static/index.html` — cache-bust.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- **Critique-pane three-axis filter + DriftCluster + summary panel** — SPEC-0057.
- **Wire-format changes** to add explicit `turns` arrays — derive in frontend for now.
- **Modal restructure** — SPEC-0058.
- **Sweep of Q-IDs in errors.jsx** — grep confirms no Q-[cg] patterns rendered as primary chrome in errors.jsx. The only Q-ID reference in the codebase is a description string in how-it-works.jsx (user-facing documentation, not cryptic chrome).

## Test plan

- 725 baseline pytest green.
- Preview-verify on partner-vetting (`3a4a`).
- Both themes.
- Zero console errors.
- `/api/health` reports new version.

## Risks

- **Turns data derivation** — building turns from flat question fields gives at most 2 turns (origin + answer). Full multi-round threads require wire-format changes in a future spec.
- **PhaseTab removal** — SPEC-0053 handover notes PhaseTab was already removed. Not relevant to this spec.
