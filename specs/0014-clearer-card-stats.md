---
spec: 0014
title: Clearer card stats — Phase 1 badges and explicit labels
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.15.0
created: 2026-05-15
pr: ""
---

# Spec 0014 — Clearer card stats

## Context

After spec 0013 the timeline cards on Phase 0/2/4 carry inline chips, but two issues surfaced on review:

1. **Phase 1 parallel-draft cards have no chips.** The Phase 1 protocol prompt doesn't ask for `STATUS:` / `OPEN_QUESTIONS:` markers, so the per-turn parser returns all-`None` and the chip row is empty. But the drafts themselves contain a structured `Open questions` section and a `Claims I expect the other agent might dispute` section — both are exactly the "questions and anticipated disagreements" payload the user wants surfaced.

2. **`OQ` / `BD` / `OI` labels are unreadable.** Short two-letter codes optimize for horizontal density but cost legibility — a viewer has to remember the abbreviation. The user also flagged that they don't visually connect to the right-pane Disagreement explorer, which calls out the same concept by its full name. Spelling chips out (`5 questions`, `2 disagreements`, `3 issues`) costs ~30 px per chip and gains immediate readability + vocabulary alignment with the rest of the UI.

## Proposed change

### Phase 1 chip-data extraction

Extend `src/dual_research/ui/turn_stats.py::_phase1_stats` to populate `open_questions` and `blocking` by counting the items inside the Phase 1 draft's structured sections, since the protocol's marker fields aren't present in this phase. The counts feed the same chip pipeline used by Phase 2/4 — the UI side needs no changes.

Two section names per concept (covering both agents' format conventions observed in real runs):

| Concept | Headings to match (case-insensitive substring) |
|---|---|
| open questions | `Open questions`, `open questions` |
| anticipated disagreements | `Claims I expect the other agent might dispute`, `dispute`, `Disagreements` |

Section bodies are detected in two formats:

- **H2 form** — `## Open questions` (used by Claude). Body runs until the next `## ` heading.
- **Numbered-section form** — `5. **Open questions** — …` (used by GPT/OpenAI). Body runs until the next top-level numbered section (`\d+. \*\*…\*\*`) or end of file.

Inside the body, count list items that begin with `^\d+\.` (numbered list) or `^[*-] ` (bulleted), excluding sub-items (lines with leading whitespace before the marker).

New helpers in `turn_stats.py`:

```python
def _count_items_in_section(text: str, section_candidates: list[str]) -> int | None:
    """Return the number of top-level list items inside the first matching
    section. None when no candidate section is found."""

def _phase1_stats(session_dir: Path, backend_ag: str) -> TurnStats | None:
    """Phase 1 drafts don't include the negotiation markers; instead, count
    structured "open questions" and "anticipated disputes" sections."""
```

The aggregator continues to call `build_phase_stats(session_dir)` unchanged — the JSON-over-the-wire shape is identical, only the values are now populated.

### Chip label overhaul (UI)

`src/dual_research/ui/static/run-detail.jsx::StatsChips` rewritten so chips read as plain English at the cost of ~30 px per chip:

| Phase | Chip A | Chip B | Status pill |
|---|---|---|---|
| 1 (plan) | `N questions` (info / ok) | `N disagreements` (warn) when >0 | — |
| 2 (negotiate) | `N questions` (info / ok) | `N disagreements` (warn) when >0 | `agreed` when STATUS=AGREED |
| 4 (review) | `N issues` (warn / ok) | — | `approved` / `not approved` |
| 0 (preflight) | unchanged (`ok` / `needs input · N`) | — | — |

The chip primitive itself (`StatChip`) keeps the same visual envelope — a fg-tinted bordered span with a small label and a numeric counter. Label text shifts from a fixed 2-character prefix to the natural-language word, with the count appearing first (`5 questions` reads like a normal English phrase).

The status pill (`agreed` / `approved` / `not approved`) stays exactly as today.

### Tests

- `tests/ui/test_turn_stats.py` — three new cases:
  - `test_phase1_counts_questions_and_disputes_from_h2_form` — synthetic Claude-style draft → `open_questions=N`, `blocking=M`.
  - `test_phase1_counts_questions_and_disputes_from_numbered_form` — synthetic OpenAI-style draft.
  - `test_phase1_fixture_round_trip` — fixture `cache-multi-round`: both agents' phase 1 stats now have populated `open_questions` and `blocking`.
- `tests/ui/test_aggregator.py::test_phase_stats_populated` — extend to assert Phase 1 counts are non-`None` for the fixture.

Total expected: 211 → 215 passing.

### Files touched

- `src/dual_research/ui/turn_stats.py` — Phase 1 section-counting logic.
- `src/dual_research/ui/static/run-detail.jsx` — label rewrite in `StatsChips` / `StatChip` / `StatusInline`.
- `tests/ui/test_turn_stats.py` — three new tests.
- `tests/ui/test_aggregator.py` — one assertion added.
- `pyproject.toml`, `src/dual_research/__init__.py`, `CHANGELOG.md` — 0.14.0 → 0.15.0.

## Out of scope

- Backend / orchestrator changes. Same posture as specs 0009–0013.
- Surfacing Phase 1 STATUS, since the protocol doesn't emit one for Phase 1.
- Phase 3 (single-shot draft) and Phase 5 (final) chips — no per-turn metadata to surface.
- Per-card cost / token counts — still requires a backend change.
- The right-pane Disagreement explorer — already uses the full word `Disagreements`; nothing to change there.

## Test plan

- [ ] All 211 existing tests still pass
- [ ] 4 new tests under `tests/ui/` pass
- [ ] Live verification at 1440 × 900 on the cache-multi-round fixture:
  - Phase 1 cards now show `N questions · M disagreements` per agent
  - Phase 2 turn cards read `5 questions` (round 1), `0 questions · agreed` (claude round 2+), `3 questions · 2 disagreements` (gpt round 2+)
  - Phase 4 cards read `3 issues` / `0 issues · approved`
  - Phase 0 Input still reads `ok`
- [ ] Screenshot of the run-detail view attached to the PR

## Risks

- **Section-counting heuristic brittleness.** Agents vary in how they format Phase 1 drafts. Mitigation: two heading patterns + multiple candidate names; degrades gracefully (chip just doesn't render). v1 acceptable.
- **Chip row width.** Spelling labels out grows each chip by ~30 px. A worst case row has `5 questions · 2 disagreements · agreed` (~210 px) plus the `r3` tag and chevron — fits comfortably in the ~400 px reserved on the timeline pane at 1440 px. Below 1024 px viewport: spec 0012's posture (don't commit) still applies.

## Open questions

None.
