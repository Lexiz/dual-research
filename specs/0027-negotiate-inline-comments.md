---
spec: 0027
title: Negotiate inline comments — side-by-side modal with anchored critique cards
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.25.0
created: 2026-05-16
pr: ""
---

# Spec 0027 — Negotiate inline comments

## Context

Spec 0025 landed the visualisation foundations: summary cards, the modal
pattern, the preflight tabbed view, hash-stable block ids on every
rendered block, and attachment ingest. The remaining piece — the one
the user was originally asking for — is the **side-by-side review
experience** for negotiation rounds: clicking a Phase 2 turn opens a
big modal with the prior content on the left and the agent's
questions / remarks as inline-comment cards on the right; clicking a
card scrolls + highlights the relevant span on the left. The mental
model is Google Docs comments / GitHub PR review.

This is spec 2 of 3 on the visualisation track:

- **0025** — foundations (✅ shipped).
- **0027 (this spec)** — Phase 2 side-by-side inline comments.
  Renumbered from the original "0026" plan after PR #26 took that
  number for the how-it-works restructure.
- **0028** — apply the same pattern to Phase 3 (refine) + Phase 4
  (final-against-prior critique).

Today, opening a Phase 2 turn card opens a single-pane modal that
just renders the full markdown. Useful but flat: you can read what
the agent said, but you can't see what they're reacting to side-by-
side, and "open questions for openai" + "substantive disagreements
I'm holding" are just prose buried inside a long turn body. This spec
makes those critiques navigable.

Anchoring approach is **Hybrid C** (the user's choice during research,
2026-05-16): a one-line prompt hint asks each question / remark to
carry an inline `> quote:` of verbatim text from the prior content,
or `> after:` for "missing X" critiques. The parser extracts those
markers, but the UX degrades gracefully when an agent doesn't comply
— un-anchored items render as plain cards in the right pane, just
without click-to-jump.

## Design decisions

| # | Decision | One-liner |
|---|---|---|
| D1 | **Left pane shows the "thing being questioned"** | For round N≥2: the OTHER agent's round N-1 turn file. For round 1: the other agent's Phase 1 draft. (You comment _on_ the other side's most recent move; round 1 has no Phase 2 history yet.) |
| D2 | **Inline-quote marker syntax: `> quote: <verbatim span>`** | Markdown blockquote on a line by itself, immediately under each numbered question / disagreement item. The blockquote already renders nicely if the agent ignores the convention; the parser extracts the text after `> quote:`. |
| D3 | **Missing-content marker: `> after: <heading title>`** | Same blockquote convention. Used for "X is missing" critiques where the comment is about absence. Anchors to the section heading whose text starts with the marker. |
| D4 | **Anchor resolution is best-effort, two-step** | First: hash the quote text → look up `b-<hash>` block id. Second: if not found, do a substring scan across the left pane's rendered blocks. If both fail, the card just doesn't link (still renders). |
| D5 | **"Missing X" indicator: dashed ghost placeholder under the preceding block** | Proofreader's caret + dashed-border `<div>` rendered below the anchored heading with the question's body as muted prose. Auto-dismiss on next click. |
| D6 | **Comment cards are flat, not threaded** | Phase 2 negotiation is single-pass — each agent writes one turn per round and doesn't reply to specific cards. Flat list is the right shape. |
| D7 | **`j` / `k` walk between comment cards** | Reuses GitHub PR muscle memory. `Esc` closes the modal. |
| D8 | **No sync-scroll between panes** | Comments are grouped by section (Open questions / Disagreements / Resolved), not by document order — sync-scroll would constantly fight the user. Click-to-jump is enough. |
| D9 | **Prompt change is one short paragraph + an example** | Minimum surface. The agents are already producing this content; we're just asking them to tag it. Phase 2 already has 100+ lines of structural requirements, one more is incremental. |
| D10 | **Side-by-side modal only triggers for Phase 2 turn cards** | Plan drafts (phase 1) and the converged document (phase 3 + final) keep their single-pane modal from 0025. Spec 0028 layers the side-by-side onto phase 4 (cross-review). |

## Proposed change

### 1. Prompt — `src/dual_research/protocol/prompts.py`

In `negotiation_turn_prompt`, under both `## Open questions for {other_name}`
and `## Substantive disagreements I'm holding`, append one sentence
plus a worked example:

```
Right under each numbered item, add ONE blockquote line that anchors
the question or disagreement to the prior content:

  > quote: <a verbatim ≤25-word span from {other_name}'s most recent
  turn or their Phase 1 draft that this critique is about>

If the critique is about MISSING content (something that should be
there but isn't), use this form instead:

  > after: <verbatim section heading the missing content should
  follow, copied without the leading "## ">

The anchor line is one line, a markdown blockquote, immediately under
the item it belongs to. Skip it if no specific span is being
critiqued — un-anchored items are fine.
```

Same addition under `negotiation_round1_prompt` (different file, same
sections — round 1 references the other agent's Phase 1 draft).

Total prompt delta: ~10 lines per prompt. No structural changes; just
a tagging convention agents may follow.

### 2. Parser — `src/dual_research/protocol/parse.py`

New function:

```python
@dataclass(frozen=True)
class ReviewItem:
    kind: str           # "question" | "disagreement" | "resolved" | "remark"
    body: str           # the item's full body (numbered-list entry, multi-line)
    quote: str | None   # verbatim span from prior content (anchor target)
    after: str | None   # heading-text anchor for "missing X" items
    item_id: str | None # e.g. "D-3" for D-N anchored disagreements

def extract_review_items(turn_text: str) -> list[ReviewItem]: ...
```

Walks the four anchored sections of a Phase 2 turn:
- `## Open questions for <name>` → `kind="question"`.
- `## Substantive disagreements I'm holding` → `kind="disagreement"`.
- `## Resolved or non-blocking differences` → `kind="resolved"`.
- `## Final-surfaced disagreements` → `kind="disagreement"` with FSD-N id.

For each numbered or D-N anchor line, capture the body up to the next
sibling list-marker / heading. Within the body, scan for the first
line matching `^>\s*quote:\s*(.+)$` or `^>\s*after:\s*(.+)$` and
extract. Tolerant of leading-spaces / nested-blockquote quirks.

Returns empty list when sections are absent — same defensiveness as
`parse_turn`.

### 3. Aggregator — `src/dual_research/ui/aggregator.py`

In `load_run_snapshot`, after `phase_summaries` is populated, walk
every Phase 2 round file and extract review items into a new
`Run.phase_review_items: dict[str, list[ReviewItem]]` keyed by
`phase2_round{R}_<agent>` (same key shape as `phase_summaries`).
JSON-friendly conversion happens at the serialization boundary.

### 4. Wire format

Snapshot JSON grows `phaseReviewItems: { [key]: [ReviewItem, …] }`.
`ReviewItem` serializes as
`{ kind, body, quote, after, itemId }` (camelCased at the boundary).

### 5. Frontend — side-by-side modal

`run-detail.jsx::DocumentModal` becomes a dispatcher:

```jsx
function DocumentModal({ item, meta, run, onClose, accent }) {
  if ((item.kind === 'turn' || item.kind === 'turn-live')
      && item.statsPhase === 2) {
    return <NegotiateReviewModal item={item} run={run} ... />;
  }
  // existing single-pane behaviour
}
```

`NegotiateReviewModal` props: `item` (the turn card), `run`. Layout:

```
┌─────────────────────────────────────────────────────────────┐
│ <Modal header: "Claude — turn 3" subtitle "round 3">         │
├──────────────────────────────────┬──────────────────────────┤
│ LEFT (60%)                       │ RIGHT (40%)              │
│ prior content rendered as MD     │ Open questions (N)       │
│ — phase2/round-02-openai.md      │ ┌──────────────────────┐ │
│ for round 3 claude turn,         │ │ Q1  · 5 open         │ │
│ or phase1/draft-openai.md        │ │ "why not Postgres…"  │ │
│ for round 1.                     │ │ > anchored to b-…    │ │
│                                  │ └──────────────────────┘ │
│                                  │ Disagreements (M)        │
│                                  │ ┌──────────────────────┐ │
│                                  │ │ D-2  · open          │ │
│                                  │ │ "Index strategy"     │ │
│                                  │ └──────────────────────┘ │
└──────────────────────────────────┴──────────────────────────┘
```

The left pane reuses the existing `LazyMarkdownBody`. The right pane
is a stack of `<ReviewCard>` components grouped by kind with section
headers (Open questions / Disagreements / Resolved). Each card:

- Colored left-rail per kind (question = info-blue, disagreement =
  warn-amber, missing/after = dashed amber, resolved = ok-green).
- Two-line clamp on body.
- "Jump" affordance — appears on hover or when card is the active
  one via `j`/`k` walk.

### 6. Click-to-anchor

New helper in `shared.jsx`:

```jsx
window.scrollAndFlash(containerEl, blockId, { fallback: { kind, text } })
```

- `getElementById(blockId)` within the container; if found, use
  `scroll-into-view-if-needed` semantics (hand-rolled: smooth scroll,
  block: 'center'). Apply class `.dr-flash` for 1.5s.
- Fallback: scan `container.querySelectorAll('p,h1,h2,h3,h4,h5,h6,li,blockquote,pre')`
  for `textContent.includes(text)`. First match wins.
- "Missing" fallback: when `kind === 'after'`, find heading whose
  textContent starts with the marker; render a `<div class="dr-ghost-block">`
  underneath with the question's body inside.

### 7. CSS — `theme.css`

```css
@keyframes dr-flash {
  0%  { background: rgba(212, 160, 86, 0.42); }
  100% { background: rgba(212, 160, 86, 0); }
}
.dr-flash { animation: dr-flash 1.5s ease-out 1 both; }

.dr-ghost-block {
  border: 1px dashed var(--warn);
  border-radius: var(--r-2);
  padding: 10px 12px;
  margin: 10px 0;
  background: rgba(212, 160, 86, 0.06);
  color: var(--fg-2);
  font-size: 12.5px;
  position: relative;
}
.dr-ghost-block::before {
  content: '‸';
  position: absolute; left: -14px; top: 6px;
  color: var(--warn); font-weight: 700;
}
```

### 8. Keyboard

- `j` → next card. `k` → previous card.
- `Enter` on the active card → activate jump.
- `Esc` → close modal (existing `Modal` behaviour).

Active card has a 2px border-left highlight.

### 9. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.24.0 → 0.25.0.
- `CHANGELOG.md`: `## [0.25.0] — 2026-05-16`.
- `VERSION_NOTES`: new entry at the top.

## Out of scope

- **Phase 3 + 4 modals.** Apply the pattern to refine + cross-
  review in spec 0028.
- **Comment threading.** Negotiation is single-pass per round; flat
  cards are the right shape. Future spec could revisit if a real
  threaded-discussion concept emerges.
- **Multi-pane scroll-sync.** Click-to-jump only.
- **TextQuoteSelector with fuzzy diff-match-patch.** v1 uses hash +
  substring fallback (~40 LOC). Real annotation libraries are
  CDN-loadable but overkill for the v1 quality bar.
- **Editing / replying to comments.** Read-only.
- **W3C Web Annotations export.** Internal data shape only; no
  external interop.

## Test plan

- [ ] `tests/protocol/test_extract_review_items.py` — parser pulls
      questions / disagreements / resolved items, captures `quote` /
      `after` markers, returns empty for missing sections, handles
      multi-line item bodies, gracefully drops items without a
      quote line.
- [ ] `tests/protocol/test_negotiation_turn_prompt_anchors.py` —
      `negotiation_turn_prompt` mentions `> quote:` and `> after:`
      and `negotiation_round1_prompt` matches. Belt-and-braces
      against accidental copy-paste drift.
- [ ] `tests/ui/test_aggregator_review_items.py` — `Run.phase_review_items`
      populated for a synthetic phase 2 round file, keyed correctly.
- [ ] `tests/ui/test_server.py` — `/api/runs/{id}` response includes
      `phaseReviewItems` with camelCase keys.
- [ ] Manual: open a freshly-run Phase 2 turn card → side-by-side
      modal opens, left = prior content, right = grouped cards.
      Click a card → left pane scrolls + flashes the referenced
      block. Click an "after:" card → dashed ghost appears. `j`/`k`
      walks. Older runs without `> quote:` markers still render —
      cards just don't jump.
- [ ] All previous tests stay green (currently 343; spec 0026 may have
      added more, refresh in the test run).

## Risks

- **Agent compliance with the marker convention is best-effort.**
  We're adding a tagging hint to a prompt that already has a lot
  going on; some turns will skip the markers. The graceful fallback
  (un-anchored cards still render, just without jump) is the
  mitigation. If compliance is below ~50% after a couple of live
  runs, 0027b could promote markers to required-format with a parse
  error in the existing repair-turn flow.
- **Quote text doesn't always match exactly.** An agent's quote may
  collapse whitespace, normalise punctuation, or paraphrase.
  Mitigation: hash lookup → substring fallback. If even substring
  fails, the card stays in the list without a jump — the user can
  still read it. Future spec adds TextQuoteSelector prefix+suffix
  if needed.
- **Modal width on small screens.** 60/40 split needs at least
  ~900px to feel right. Desktop-first project; mobile is out of
  scope. The existing `Modal` already maxes at 1100; we can stretch
  to 1300 for this specific case.
- **Round 1 has no Phase 2 prior round to point at.** Left pane
  falls back to the other agent's Phase 1 draft. This is correct
  semantics — round 1 critiques are about the Phase 1 draft — but
  worth flagging because it's a different file shape on the left.
- **Older runs.** Existing on-disk Phase 2 turns predate the
  `> quote:` convention. They'll render as un-anchored cards. No
  data corruption; just a quality difference until a fresh run.

## Open questions

- Whether to also surface review items as a **count badge** on the
  card header (e.g. `5 anchored · 2 floating`). Out of scope for
  v1; the existing `5 questions · 2 disagreements` chip already
  conveys volume.
