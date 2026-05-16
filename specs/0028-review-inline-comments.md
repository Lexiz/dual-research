---
spec: 0028
title: Cross-review inline comments — Phase 4 side-by-side modal
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.26.0
created: 2026-05-16
pr: ""
---

# Spec 0028 — Cross-review inline comments

## Context

The visualisation track ends here.

- **0025** — modal pattern, summary cards, preflight tabs, attachment
  ingest, hash-stable block ids (✅ shipped).
- **0027** — Phase 2 negotiation side-by-side modal with anchored
  critique cards (✅ shipped).
- **0028 (this spec)** — apply the same pattern to **Phase 4**
  (cross-review of the converged document). After this, every place
  in the timeline where an agent critiques prior content has a
  side-by-side review modal.

Phase 4 is structurally close to Phase 2:

- Both are turn-based with parallel agent calls per round.
- Both produce numbered-list / D-N-anchored critique sections.
- The headings are slightly different (`## Comments on the current
  draft`, `## Issue ledger`, `## Disagreement carryover audit`)
  but the shape is the same.

The semantic difference is **what's being critiqued**: Phase 2
critiques the other agent's plan / prior turn; Phase 4 critiques the
**current draft** (the converged document the drafter produced in
Phase 3, with possible later revisions via the drafter's
`## Revised draft` section). So the side-by-side modal's left pane
needs to show the current draft, not the other agent's prior turn.

Phase 3 (single-shot drafting) stays single-pane: there are no
critique sections to anchor to. The final document modal also stays
single-pane for the same reason. Spec 0025's `DocumentModal` already
handles both correctly.

## Design decisions

| # | Decision | One-liner |
|---|---|---|
| D1 | **Left pane shows the latest draft version available at view time.** | Highest `phase4/draft-vN.md` if any drafter revision has landed; falls back to `phase3/draft-v1.md`. Surfaced via a new `Run.current_draft_path` field. |
| D2 | **No per-round draft-history tracking in v1.** | A Phase 4 turn in round 3 may be commenting on the draft that existed at round 3, even if round 4 has since produced a revision. Showing the round-3-correct draft requires tracking draft versions per round; out of scope. The latest draft is usually what users want to see anyway. |
| D3 | **`extract_review_items` extended to Phase 4 sections.** | New section headings recognised: `## Issue ledger (delta + currently open)`, `## Comments on the current draft`, plus the existing `## Substantive disagreements I'm holding` / `## Resolved or non-blocking differences` (already in scope from spec 0027). |
| D4 | **Same marker convention as 0027.** | `> quote: <verbatim ≤25-word span>` and `> after: <heading title>`. The `review_turn_prompt` gets the same one-paragraph addition under each critique section. |
| D5 | **Drafter turns share the modal.** | The drafter's Phase 4 turn body has a `## Revised draft` section in addition to comment / issue sections. The side-by-side modal still works — comments / issues / disagreements anchor the same way. The revised-draft section just renders inline in the right pane as plain text (it's not a critique). |
| D6 | **Same modal component as Phase 2.** | `NegotiateReviewModal` is now dispatched for both Phase 2 and Phase 4 turn cards. The only difference is the resolver for the left-pane file path. |
| D7 | **Keyboard + ghost-block behaviour unchanged.** | `j`/`k` walk, `Esc` close, `> after:` items still mount a dashed-ghost insertion placeholder. The styles are already in `theme.css`. |

## Proposed change

### 1. Prompt — `src/dual_research/protocol/prompts.py`

In `review_turn_prompt`, add the same anchor-marker paragraph that
0027 added to the Phase 2 prompts. Three places:

- Under `## Issue ledger (delta + currently open)` — each numbered
  issue may carry `> quote: …` referencing the relevant line in the
  current draft.
- Under `## Comments on the current draft` — each numbered comment
  may carry `> quote: …` (or `> after:` for "missing X" comments).
  This is the natural home for anchored review comments.
- Under `## Substantive disagreements I'm holding` — same as the
  Phase 2 wording (D-N entries with `> quote:` sub-line).

### 2. Parser — `src/dual_research/protocol/parse.py`

`extract_review_items` gains two more section recognisers:

- `## Issue ledger (delta + currently open)` → numbered list,
  `kind="question"`.
- `## Comments on the current draft` → numbered list,
  `kind="question"`.

Existing recognisers (open questions, substantive disagreements,
resolved, final-surfaced, round-1 diff) keep their current behaviour.
A Phase 4 turn body that includes both Issue ledger and Comments
produces one flat list with both blocks of items.

No change to the `ReviewItem` dataclass; same `{kind, body, quote,
after, item_id}` shape.

### 3. Aggregator — `src/dual_research/ui/aggregator.py`

- `_read_phase_review_items` now walks `phase4/round-NN-*.md` files
  too, keyed `phase4_round{R}_<agent>` (same convention used since
  0025 / 0027).
- New helper `_find_current_draft_path(session_dir) -> str | None`
  that prefers the highest-numbered `phase4/draft-v*.md` and falls
  back to `phase3/draft-v1.md`. Populated on `Run.current_draft_path`.

### 4. Run model — `src/dual_research/ui/models.py`

```python
@dataclass
class Run:
    ...
    current_draft_path: str | None = None  # NEW (spec 0028)
```

Serialises as `currentDraftPath` at the wire boundary.

### 5. Frontend — `src/dual_research/ui/static/run-detail.jsx`

- `ArtifactModal` dispatcher: route phase 4 turn cards
  (`statsPhase === 4`) to `NegotiateReviewModal`, same as phase 2.
- `priorContentPathFor` becomes phase-aware:
  - Phase 2, round 1: other agent's Phase 1 draft (unchanged).
  - Phase 2, round N≥2: other agent's round N-1 turn (unchanged).
  - Phase 4: `run.currentDraftPath` (no round-specific lookup;
    latest draft wins — see D2).
- `reviewItemsFor` already keys on `phase{N}_round{R}_<agent>` for
  any N. No change needed.

### 6. Tests

- `tests/protocol/test_extract_review_items.py` — extend with Phase
  4 fixtures: `## Issue ledger` and `## Comments on the current
  draft` items parse correctly, anchor markers survive, item ids
  for Phase 4 disagreements still recognised.
- `tests/protocol/test_review_prompt_anchors.py` (new) — `review_turn_prompt`
  contains `> quote:` and `> after:` and the markers land inside the
  Comments / Issue ledger / Substantive-disagreements sections.
- `tests/ui/test_aggregator_review_items.py` — extend with a
  Phase 4 round fixture; `Run.phase_review_items` keyed by
  `phase4_round{R}_<agent>`. New test for `Run.current_draft_path`
  resolution (highest revision wins, falls back to phase3).
- `tests/ui/test_server.py` — assert the `/api/runs/{id}` snapshot
  includes `currentDraftPath` (camelCase boundary check).

### 7. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.25.0 → 0.26.0.
- `CHANGELOG.md`: `## [0.26.0] — 2026-05-16`.
- `VERSION_NOTES`: new entry at the top of `how-it-works.jsx`.

## Out of scope

- **Per-round draft history.** A future spec could track the draft
  version that existed at each Phase 4 round and show "the draft as
  it was when this comment was written." v1 always shows latest.
- **Phase 3 side-by-side.** Phase 3 is single-shot drafting with no
  critique sections; the single-pane modal from 0025 is the right
  shape.
- **Final document inline comments.** Spec 0025's `DocumentModal`
  renders the final markdown without anchoring. No critique data
  exists for the final.
- **Highlighting changed paragraphs between draft versions.** A
  diff view of the converged draft across revisions is a separate
  feature.
- **Cross-phase comment threads** (e.g. "this Phase 4 comment is the
  same as Phase 2's D-3 disagreement"). The protocol already carries
  D-N IDs across phases; the UI could link them. Out of scope here.

## Test plan

- [ ] `pytest tests/` stays green; spec 0028 adds at least 8 new
      tests (parser shapes for Phase 4 sections, prompt marker
      presence, aggregator wiring, `current_draft_path` resolution).
- [ ] Manual: trigger a fresh full-tier run, click a Phase 4 turn
      card → side-by-side modal opens with the latest draft on the
      left and the agent's comments / issues / disagreements on the
      right. Click a card with `> quote:` → left pane scrolls +
      flashes. Click an `> after:` card → dashed-ghost appears
      under the named section. `j`/`k` walks; `Esc` closes.
- [ ] Manual: old (pre-marker) Phase 4 turns render as un-anchored
      cards — they still appear in the list, just don't jump.

## Risks

- **Drafter turns mix `## Revised draft` with comments.** The
  side-by-side modal won't show the revised-draft text in any
  special way — it renders as the body of one of the comment cards
  (since the drafter sections in the body are not numbered
  critiques). The left pane shows the *latest* revision regardless,
  so the user can still inspect the revised draft via the
  single-pane Phase 5 final modal or via the existing file endpoint.
  Acceptable for v1.
- **`current_draft_path` is run-wide, not per-turn.** Comments
  written in Phase 4 round 2 may have been about a draft that has
  since been revised. The flash highlight may land in a slightly
  different place than the agent meant. Mitigation: the substring-
  fallback in `scrollAndFlash` (from 0027) is forgiving; minor
  drift is acceptable. Per-round draft history is the right
  follow-up.
- **Older runs.** Pre-marker Phase 4 turns still render as
  un-anchored cards (same graceful fallback as 0027). No data
  corruption.

## Open questions

- Whether `Run.current_draft_path` should be a list instead of a
  single string (so the UI could let users pick a draft version).
  v1 ships the single-string form; promoting to list is non-breaking
  if needed.
