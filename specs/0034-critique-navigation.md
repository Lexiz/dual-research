---
spec: 0034
title: Critique navigation — first-class Q+D, side-by-side rework, sentiment cards, click-to-highlight
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.32.0
created: 2026-05-16
pr: "https://github.com/Lexiz/dual-research/pull/36"
---

# Spec 0034 — Critique navigation

## Context

Spec 0033 made the **input** to each turn legible. This spec makes the
**critique flow between turns** navigable. Three gaps from the first
end-to-end run:

1. **Phase 2 side-by-side "works" but doesn't help the user.** Spec
   0027 shipped a side-by-side modal with quote-matching anchors, but
   `findBlockWithText` resolves substring-matches at render time —
   when the agent paraphrases the quote or the substring straddles
   markdown formatting, the click silently does nothing. The user
   tried to use it and bounced. Same architecture exists in Phase 4
   (spec 0028) with the same problem.

2. **Questions and disagreements share an explorer that's labelled
   "Disagreements".** The right pane tab today renders only
   `run.disagreements` — but Phase 2 turns also carry *questions* in
   their `## Open questions for X` section, counted in `TurnStats.
   open_questions` and surfaced as a chip on each card. Questions
   are not first-class anywhere: no IDs, no progression, no panel.
   The user wants both, typed, with the same drill-down depth.

3. **Cards don't tell you what happened in a turn.** Spec 0030's
   single-line gist composer (`"Raised 4 questions; conceded D-3"`)
   is too shallow once you've seen one round. The user wants a
   short paragraph synthesising the turn's sentiment + key counts +
   key resolutions — enough to skim a round-by-round narrative
   without opening modals.

4. **Round-to-round dynamics are invisible.** The card chips show
   THIS round's open-question + disagreement counts, but not how
   they *changed* from the prior round. If Claude entered round 3
   with 4 open questions and exits with 1, the card looks the same
   as if nothing moved.

5. **The Disagreements panel is its own island.** Clicking a
   disagreement card shows its progression list inline, but the
   timeline cards where it was raised / contested / resolved sit
   in the other half of the screen with no visual link. The user
   wants to click a Q/D in the explorer and have the corresponding
   turn-cards in the timeline flash.

These five concerns share one piece of infrastructure: **stable IDs
on every question and disagreement, with turn-key references for
where they were raised and resolved.** Once that exists, every
ask above is a UI consumer of the same data model. Splitting the
spec would leave the IDs orphaned for a release.

Prior context: spec 0027 (Phase 2 inline comments), spec 0028
(Phase 4 review inline comments), spec 0033 (`item.turnKey` plumbed
into every timeline item — this spec depends on those keys being
stable references back to the timeline).

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **Questions get first-class `Question` objects parallel to `Disagreement`, with the same shape.** | New `Question` dataclass in `ui/models.py` mirroring `Disagreement`: `id`, `phase`, `raised_round`, `raised_by`, `answered_round` / `answered_by` (nullable), `status` (`open` / `answered`), `body`, `quote` / `after` anchors, `raised_turn_key`, `answered_turn_key`. The aggregator's `reconstruct()` learns to emit them alongside disagreements; `Run.questions: list[Question]` joins `Run.disagreements`. |
| D2 | **Question IDs are assigned at parse time using a stable per-raiser-per-round scheme.** | Format: `Q-{raiser_initial}-r{round}-{idx}` (e.g. `Q-c-r1-01` for Claude's first round-1 question). The protocol doesn't require agents to emit `Q-N` IDs — they would need a prompt change and back-pressure. The positional + raiser-prefixed scheme is stable as long as the parser walks turns in deterministic order, and avoids a prompt revision. |
| D3 | **Answer matching is positional first, with verbatim-text fallback.** | Round N+1's `## Answers to {other_name}'s open questions` section addresses round N's `## Open questions for {other_name}` list in order (protocol convention). Match by position; if the round N+1 turn has fewer answers than there were questions, the trailing questions stay `open`. As a robustness check, if the positional answer mentions the question body verbatim or a 6+ word substring of it, we treat it as a confirmed match; otherwise it's positional-only and tagged `match: 'positional'` in a debug field for future heuristic tuning. |
| D4 | **Disagreement IDs are unchanged (still `D-N`, agent-emitted).** | The protocol already defines `D-N` IDs and the parser already extracts them (`disagreements.py::_parse_one_entry`). Only the threading of `raised_turn_key` / `closed_turn_key` is new — derived from the round number and the agent who emitted each `ProgressionStep`. |
| D5 | **`Disagreement` and `Question` both gain `raised_turn_key` + `closed_turn_key`/`answered_turn_key`.** | Format matches spec 0033's `item.turnKey`: `phase{N}_round{R}_{agent}` (e.g. `phase2_round3_claude`). Lets the UI's click-to-highlight feature jump straight from an explorer card to a specific timeline card without any client-side derivation. |
| D6 | **Side-by-side anchor resolution moves from render-time to parse-time.** | The current `findBlockWithText` (in `run-detail.jsx::scrollAndFlash`) scans the rendered left-pane DOM for the quote substring on every click. Replace with: parser resolves each `> quote: …` anchor against the prior content's block IDs at write time (in `extract_review_items` / aggregator), and emits a `block_id: str \| null` field on each `ReviewItem`. The frontend uses the resolved ID directly via `getElementById`; falls back to the existing quote-matching only when `block_id` is `null` (paraphrased quote, parser miss). |
| D7 | **Block IDs are assigned at markdown-render time on the BACKEND** and emitted alongside the markdown. | Today block IDs (`id="b-…"`) are generated by the Markdown renderer in the frontend (per spec 0025 comment). For parser-time resolution, the backend needs the same IDs in the same positions. New helper `protocol/blocks.py::assign_block_ids(markdown: str) -> tuple[str, list[BlockRecord]]` — returns the rewritten markdown with `<!-- block-id: b-N -->` HTML comments embedded after each block, plus a list of `BlockRecord(id, text, line_start)`. The frontend renderer detects these comments and lifts the IDs into the rendered DOM nodes; the parser uses the records to resolve anchors. |
| D8 | **Phase 1 gets a side-by-side viewer with brief on the left and the draft on the right — but cross-references are heuristic, not anchor-based.** | The Phase 1 prompt doesn't ask the agent to anchor draft sections to brief sections — it's an independent draft, not a critique. Two ways forward considered: (a) require an "anchors" sub-section in the Phase 1 prompt (agent behaviour change — too risky in this spec); (b) heuristic substring matching from draft to brief on hover/click — best-effort, no protocol change. Picked (b). The Phase 1 side-by-side renders draft sections with a "🔗 brief" affordance on each section heading; clicking scans the brief for the closest-matching span (using the same block-resolver from D6) and flashes the match if found, else flashes nothing. Out of scope: deep Phase 1 cross-references. |
| D9 | **Sentiment paragraph replaces the single-line gist on Phase 1 and Phase 2 unfolded cards.** | New `composeSentiment(item, run)` helper. Reads `TurnStats`, the turn's `parsed_turn` fields (status, agreement check, mind-changed), counts of new vs resolved disagreements/questions this round, and prior-round counts. Returns 2-3 sentences — e.g. `"Claude raised 4 new questions and conceded D-3 (the SQLite vs Postgres argument). Mostly aligning on the plan — agreed in principle on 3 of 5 sections. Round-3 endorsement: still negotiating."` Pure deterministic switch over `(phase, status, deltas)` — no LLM. |
| D10 | **Card chips gain a delta annotation: `4 Q (-2)` / `5 D (+1, -2)`.** | The current chips show absolute counts. The new annotation shows the delta from the agent's prior-round chip: `-2` means "two were resolved/answered since last round", `+1` means "one new this round". Computed in `composeGist`-adjacent code. The chip tooltip explains the convention. |
| D11 | **`DisagreementExplorer` becomes `CritiqueExplorer` and renders both Qs and Ds, typed.** | The right-pane component is renamed. The phase-tabs (Phase 2 / Phase 4) gain a per-type count breakdown: `Phase 2 · 3 Q · 4 D`. Each card in the body shows a small left-rail tag `Q` (blue) or `D` (orange). The "open vs resolved" filter is unchanged but applies across both types. Filter buttons gain a 3rd toggle: `All / Questions / Disagreements`. |
| D12 | **Clicking a Q or D card in the explorer flashes the corresponding turn-cards in the timeline.** | Cross-axis link. Implementation: an explorer card click sets a `highlightedTurnKeys: Set<string>` state on `RunDetail`; the timeline listens for that and applies a 1.5s flash animation to any `<ArtifactCard>` whose `item.turnKey` is in the set. The set covers the raised-turn-key and (if resolved) the closed/answered-turn-key. CSS: `box-shadow` ring in `COLORS.info` for Qs, `COLORS.warn` for Ds, fading over 1500ms. The set clears 2s after click so subsequent unrelated clicks don't pile flashes. |
| D13 | **Disagreement progression in the explorer card gains turn-key links per step.** | The existing `ProgressionStep` shows `round`, `agent`, `action`, `note`. Now each step also surfaces a small "→ jump to turn" affordance that adds the step's turn to the highlight set (same mechanism as D12). Lets the user walk a disagreement's history click-by-click. |
| D14 | **Phase 2 + Phase 4 modals keep their existing layout — only the left-pane resolution mechanism changes.** | The `NegotiateReviewModal` left/right split, the keyboard nav (j/k/Enter), the dashed-ghost placeholder for `> after:` items, and the spec-0033 `Original | Input` sub-tabs all survive. The internal change is that `jumpToItem` no longer calls `findBlockWithText` first; it uses the pre-resolved `block_id` directly via `document.getElementById(block_id)`, falls back to text-match only on `null`. Quieter, more reliable behaviour with the same UX. |
| D15 | **Phase 1 side-by-side modal is a new component (`DraftReviewModal`) — not a fork of `NegotiateReviewModal`.** | The two modals' content shapes are different enough that sharing the parent component would force conditionals on every section. New `DraftReviewModal` for `kind === 'plan'` items: left pane = brief (with `Original | Input` sub-tabs from spec 0033), right pane = draft markdown rendered with per-section heading affordances. No keyboard-nav cards on the right; the section headings are the navigation surface. Smaller than `NegotiateReviewModal`. |
| D16 | **The dispatcher in `ArtifactModal` routes `kind === 'plan' \| 'plan-live'` to `DraftReviewModal` instead of the one-pane `DocumentModal`.** | Phase 1 cards already had `Input` as a second tab (spec 0033). The new modal is now the default `View in full mode` destination for Phase 1; one-pane `DocumentModal` stays the default for Phase 3 + Phase 5 (single converged document / final). |
| D17 | **No prompt changes in this spec.** | The data model lift (Q+D first-class, turn-key threading, block-id pre-resolution) is all parser-side. Agents emit the same protocol artefacts they already do. A future spec could add explicit Q-N IDs in the prompt if positional matching proves too fragile (see Risks). |

## Proposed change

### 1. Block-ID assignment — new `protocol/blocks.py`

```python
@dataclass(frozen=True)
class BlockRecord:
    """One markdown block with a stable ID + its plain text for matching."""
    id: str         # "b-1", "b-2", …
    text: str       # the block's plain-text body (anchor-matching target)
    line_start: int # 0-indexed line in the source markdown

def assign_block_ids(markdown: str) -> tuple[str, list[BlockRecord]]:
    """Walk the markdown by block (paragraph / heading / list / blockquote
    / fenced code), assign sequential IDs, and return:
    - The rewritten markdown with HTML comments embedded after each block:
      ``…\n<!-- block-id: b-N -->\n…``
    - The ordered list of BlockRecords for anchor resolution.

    Block boundary heuristic: blank-line-separated chunks at the top level,
    with list-item-aware splitting (each top-level numbered/bulleted item
    is its own block). Code fences (``` … ```) are atomic.
    """
```

Tests live in `tests/protocol/test_blocks.py`:
- Sequential IDs across heading + para + list + code fence.
- HTML comments embedded after each block.
- Empty markdown returns `("", [])`.
- BlockRecord.text excludes markdown punctuation (headings stripped of `#`, list markers stripped) — what the user reads on screen.

### 2. Pre-resolve anchors at parse time — `protocol/parse.py`

`ReviewItem` (line 183) gains `block_id: str | None`:

```python
@dataclass(frozen=True)
class ReviewItem:
    kind: str
    body: str
    quote: str | None
    after: str | None
    item_id: str | None
    block_id: str | None  # NEW — pre-resolved anchor on the prior content
```

`extract_review_items(turn_text)` keeps its signature but is now called
through a new wrapper `resolve_review_items(turn_text, prior_blocks:
list[BlockRecord])` which:
1. Walks the items extracted from `turn_text`.
2. For each item with `quote: X`: search `prior_blocks` for one whose
   `text` contains `X` (normalising whitespace + case-insensitive), pick
   the first match. Assign `block_id` to that block.
3. For each item with `after: H`: search `prior_blocks` for a heading
   block whose text equals `H`. Assign that block's `block_id`.
4. Falls through to `block_id = None` if no match found.

The aggregator (see §3) is the only caller that has both the turn text
and the prior content's blocks; the resolver is called there.

### 3. Aggregator — questions + turn-keys + resolved anchors

`ui/aggregator.py::_read_phase_review_items` is extended:

- For each Phase 2 / Phase 4 turn file, compute the PRIOR content
  (round R-1 turn for round R; Phase 1 draft for round 1) and pass its
  blocks (via `assign_block_ids`) to `resolve_review_items`. Store the
  resolved `ReviewItem` list with `block_id` filled in.
- The wire-format dict for `phaseReviewItems` gains a `blockId` field per
  item (camelCase passthrough).

New `ui/questions.py`:

```python
@dataclass
class Question:
    id: str  # "Q-c-r1-01"
    phase: int  # 2 | 4
    raised_round: int
    raised_by: str  # "claude" | "gpt"
    answered_round: int | None
    answered_by: str | None
    status: QuestionStatus  # "open" | "answered"
    body: str
    quote: str | None
    after: str | None
    block_id: str | None
    raised_turn_key: str
    answered_turn_key: str | None

def reconstruct_questions(session_dir: Path, *, phase: int) -> list[Question]:
    """Walk every Phase {phase} turn file. For each agent's `## Open
    questions for X` section, extract numbered questions, assign IDs,
    and link to the next round's `## Answers to X's open questions`
    section (positional match — see D3).
    """
```

`load_run_snapshot` (line 74) calls `reconstruct_questions` for phases
2 and 4 and stores the union on `Run.questions: list[Question]`.

`Disagreement` (in `ui/models.py`) gains `raised_turn_key: str` and
`closed_turn_key: str | None`. `ui/disagreements.py::reconstruct` is
updated to populate them from the first/last progression step's round
+ agent.

Wire format: `run.questions` lands on the wire as `questions` (list of
camelCase dicts).

### 4. Sentiment composer — `run-detail.jsx`

New `composeSentiment(item, run)` helper near `composeGist` (line ~1344):

```js
function composeSentiment(item, run) {
  // Returns a 2-3 sentence paragraph synthesised from:
  // - item.stats (TurnStats)
  // - run.questions filtered to item.statsPhase / round / agent
  // - run.disagreements filtered to item.statsPhase / round / agent
  // - prior-round counts (item.statsPhase, item.round - 1)
  // Deterministic switch over (phase, status, deltas).
  // Empty string if nothing meaningful to say (Phase 1 first turn).
}
```

Phase 1 paragraph examples:
- `"Claude wrote a 1,247-word independent draft. Anchored 12 claims as [V] (verified) and 4 as [U] (unverified, training-derived). Flagged 3 claims they expect GPT to dispute."`

Phase 2 paragraph examples:
- Round 1: `"Claude surfaced 6 differences vs GPT's draft. Raised 4 open questions and proposed an initial plan with Claude as drafter. No agreements yet — round 1 surfaces, doesn't converge."`
- Round 3 (negotiating): `"Claude conceded D-2 (the SQLite question, citing GPT's WAL-mode benchmark). Raised 1 new question, answered 3 of GPT's prior 4. Still holding D-4 on caching strategy."`
- Round 5 (agreed): `"Claude endorsed the plan with Claude as drafter. Final-surfaced 1 disagreement (FSD-1 on rate-limiting strategy). Most-changed: the original framing of "free tier" — now structured around use-case classes."`

Phase 4 paragraph examples mirror Phase 2 but with `Issues` / `Comments`.

`ArtifactExpandedBody` (line 1289) is updated to call
`composeSentiment` for `kind: 'plan' | 'turn'` items and render the
result as a multi-line paragraph; the existing `composeGist` is kept
as a fallback for the cases the sentiment composer returns `""`.

### 5. Round-to-round chip deltas — `run-detail.jsx`

`StatsChips` (line ~1279) is extended. For each chip (open-questions
or disagreements), if there's a prior-round entry in
`run.phaseStats[phaseN][round-1][agent]`, append a delta annotation:

- `4 Q (-2)` — the chip's count plus a small muted delta.
- `5 D (+1, -2)` — separate annotations for "new this round" and
  "resolved since last round".

The "resolved since last round" calculation uses `run.questions` /
`run.disagreements` (with their `answered_round` / `closed_round`
fields, now populated) — count items where
`raised_round <= prevRound && answered_round === round`.

A 4-line tooltip on the chip explains: "+N new this round · -N
resolved or answered since last round".

### 6. Side-by-side viewer rework

`NegotiateReviewModal` (line ~1524):
- `jumpToItem(it)` updated to use `it.blockId` if present:
  - `it.blockId` set: `document.getElementById(it.blockId)` →
    scrollIntoView + flash. No DOM scan.
  - `it.blockId` null + `it.quote` set: fall back to today's
    `findBlockWithText` logic.
  - `it.blockId` null + `it.after` set: fall back to today's heading
    scan + ghost-block mount.
- The frontend Markdown renderer detects the `<!-- block-id: b-N -->`
  HTML comments emitted by `assign_block_ids` and applies them as
  `id` attributes on the rendered DOM nodes (one `id` per block).

`DraftReviewModal` (new component):
- Layout matches `NegotiateReviewModal`: left pane (brief, with the
  spec-0033 `Original | Input` sub-tabs), right pane (the agent's
  draft).
- The right pane is a plain `LazyMarkdownBody` (no ReviewCard list);
  the section headings (`## Summary`, `## Detailed findings`, etc.)
  render with a small "🔗 brief" affordance.
- Clicking the affordance: pass the section's heading text + the
  first paragraph's text to a `findBriefMatch(text, briefBlocks)`
  helper. If found, scroll-and-flash the brief block; if not, no
  visible action (only a console warning in dev).

`ArtifactModal` dispatcher updated to route `kind === 'plan' |
'plan-live'` to `DraftReviewModal`.

### 7. CritiqueExplorer — formerly DisagreementExplorer

`DisagreementExplorer` (line ~2665) is renamed to `CritiqueExplorer`
and rewritten:

- The pane header label becomes `Critique` (or `Q & D` — see Open
  questions).
- `tabs` (phase 2 / phase 4) carry per-type counts:
  ```
  Phase 2 · Negotiate · 3 Q · 4 D · 7 total
  ```
  with the Q count blue + D count orange.
- A new filter strip below the phase tabs:
  ```
  [ All ]  [ Questions ]  [ Disagreements ]    [ Open · Resolved ]
  ```
  First group filters by type, second filters by status (same as today's
  open / resolved split, just typed).
- `PhaseContent` is extended to take both `questions` and `disagreements`
  arrays. Cards render with a `Q` / `D` left-rail tag.
- Each card body shows: ID + short label + status + progression list
  (existing for D, new for Q). The "→ jump to turn" affordances on each
  progression step are new (per D13).
- Click anywhere on a card body sets the timeline highlight (D12).

### 8. Cross-axis highlight — `RunDetail` + `Timeline` + `ArtifactCard`

New shared state at the `RunDetail` level:

```js
const [highlightedTurnKeys, setHighlightedTurnKeys] = React.useState(new Set());
const highlightTurns = React.useCallback((keys) => {
  setHighlightedTurnKeys(new Set(keys));
  setTimeout(() => setHighlightedTurnKeys(new Set()), 2000);
}, []);
```

Passed down to:
- `<Timeline run={run} tab={timelineTab} highlightedTurnKeys={highlightedTurnKeys} />`
- `<CritiqueExplorer run={run} onHighlightTurns={highlightTurns} />`

`Timeline` forwards `highlightedTurnKeys` to each `<ArtifactCard>`.
`ArtifactCard` (line ~1222) reads `item.turnKey` (already plumbed in
spec 0033) and applies a `box-shadow` + outline ring when its key is
in the set:

```css
.dr-card-flash-q { box-shadow: 0 0 0 2px var(--info), 0 0 24px var(--info-glow); transition: box-shadow 1500ms ease-out; }
.dr-card-flash-d { /* same but warn */ }
```

Two variants because clicking a `Q` and clicking a `D` should visually
differ (the user's audit trail of which thing they're following).

### 9. Repurpose the spec-0033 round-key regex fix for Phase 0 questions

Out of scope on parse-time question extraction: Phase 0 critiques
(`phase0/preflight-{agent}.md`) contain a `## Framing concerns` and
`## Missing inputs` numbered-list section. These conceptually map to
questions about the brief — but they're directed at the user, not the
other agent, and don't have a multi-round resolution pattern. **Not
covered by this spec.** A future spec could surface them in the
explorer under a `Phase 0 · Brief concerns` tab.

### 10. Tests

New / extended tests:

- `tests/protocol/test_blocks.py` (new) — `assign_block_ids` across
  paragraph / heading / list / code-fence / blockquote inputs.
  HTML-comment embedding + BlockRecord text-stripping.
- `tests/protocol/test_parse_review_items.py` (extend existing) —
  `resolve_review_items(turn_text, prior_blocks)` populates `block_id`
  for verbatim quotes; returns `None` for paraphrased quotes;
  resolves `after:` headings against block heading text.
- `tests/ui/test_questions.py` (new) — `reconstruct_questions`:
    - Phase 2 round 1: extracts Claude's + GPT's questions, IDs them
      `Q-c-r1-NN` / `Q-g-r1-NN`, status `open`.
    - Phase 2 round 2: positional answer matches link round-1 questions
      to round-2 answers; status flips to `answered`; `answered_round`
      + `answered_turn_key` populated.
    - Phase 2 round 2 with fewer answers than questions: trailing
      questions stay `open`.
    - Phase 4 fixture with Issue-ledger format → Q objects emitted.
- `tests/ui/test_aggregator_questions.py` (new) — `Run.questions` is
  populated by `load_run_snapshot`; wire-format `questions` list
  round-trips through `_to_camel`.
- `tests/ui/test_disagreements.py` (extend) — `Disagreement.
  raised_turn_key` + `closed_turn_key` populated from progression
  steps.
- `tests/ui/test_aggregator_review_items.py` (extend) — `block_id` is
  set on review items when the prior content contains a verbatim
  quote; falls to `None` for paraphrases.
- `tests/ui/test_server.py` — verify the snapshot carries
  `questions` + `Disagreement.raisedTurnKey` + `phaseReviewItems[*].
  blockId` correctly camelCased.

Frontend: manual.

### 11. Files touched (non-exhaustive)

Backend:
- `src/dual_research/protocol/blocks.py` (new).
- `src/dual_research/protocol/parse.py` — `ReviewItem.block_id`,
  `resolve_review_items`.
- `src/dual_research/ui/questions.py` (new).
- `src/dual_research/ui/disagreements.py` — `raised_turn_key` /
  `closed_turn_key` plumbing.
- `src/dual_research/ui/models.py` — `Question` dataclass,
  `Disagreement.raised_turn_key` / `closed_turn_key`,
  `Run.questions`.
- `src/dual_research/ui/aggregator.py` — wire `questions` into
  `load_run_snapshot`; call `resolve_review_items` with prior blocks;
  populate `*_turn_key` fields.

Frontend:
- `src/dual_research/ui/static/run-detail.jsx`:
  - `composeSentiment` added.
  - `StatsChips` extended with deltas.
  - `NegotiateReviewModal::jumpToItem` uses `blockId`.
  - `DraftReviewModal` added; dispatched for `kind: 'plan'`.
  - `DisagreementExplorer` → `CritiqueExplorer`; per-type counts +
    filter strip; `Q | D` card tags; per-step "→ jump" affordances.
  - `RunDetail` owns `highlightedTurnKeys` + forwards to `Timeline` +
    `CritiqueExplorer`.
  - `ArtifactCard` applies `dr-card-flash-q` / `dr-card-flash-d` CSS
    when `item.turnKey` is in the highlight set.
- `src/dual_research/ui/static/shared.jsx`:
  - Markdown renderer detects `<!-- block-id: b-N -->` HTML comments
    and applies them as `id` attrs on the rendered nodes.
- `src/dual_research/ui/static/theme.css`:
  - `.dr-card-flash-q` / `.dr-card-flash-d` rules.

### 12. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.31.0 → 0.32.0.
- `CHANGELOG.md`: new `## [0.32.0] — YYYY-MM-DD` entry.
- `VERSION_NOTES` entry in `how-it-works.jsx`.

## Out of scope

- **Prompt changes.** The protocol stays as-is — no new `Q-N` IDs in
  agent output, no per-section anchor instruction for Phase 1, no
  `## Brief concerns` sectioning. A future spec can layer those on top
  if positional matching or heuristic Phase 1 cross-refs prove too
  fragile.
- **Editing a question or disagreement from the UI.** Read-only.
- **Phase 0 preflight surfacing in the explorer.** Phase 0 carries
  `## Missing inputs` and `## Framing concerns` — conceptually
  questions about the brief, but directed at the user, not the other
  agent. Surface in a future spec under its own tab.
- **Cross-references between Phase 1 draft sections and brief sections
  via explicit anchors.** The Phase 1 prompt would need to emit
  anchor lines; this spec uses heuristic substring matching instead.
- **Editing the AGREED_PLAN's FSD list from the explorer.** Final-
  surfaced disagreements remain read-only.
- **Persistence of explorer filter state across runs.** The
  `All / Questions / Disagreements` toggle resets to `All` on every
  run-id change.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec 0034 adds at least
      25 new tests (block-id assignment per markdown shape,
      `resolve_review_items` for verbatim + paraphrased + heading
      anchors, `reconstruct_questions` for round-1 + round-N
      positional matches + partial answers + Phase 4 issue-ledger,
      `*_turn_key` plumbing on Disagreement + Question, snapshot wire
      shape).
- [ ] Manual: fresh prod-tier run. Phase 2 turn cards on the
      Conversation tab now show a multi-sentence paragraph when
      unfolded (instead of the single gist line), with counts of
      questions raised + disagreements resolved.
- [ ] Manual: same cards' chip annotations show `4 Q (-2)` /
      `5 D (+1, -2)`-shape deltas relative to the prior round.
- [ ] Manual: open a Phase 2 round 3 turn card → modal opens with
      the side-by-side layout. Click a critique item on the right
      pane → left pane scrolls + flashes the referenced block,
      reliably even when the agent paraphrased (because of
      pre-resolution; falls back to text-match when block_id is
      null, with a visible reminder in dev tools).
- [ ] Manual: open a Phase 1 plan card → new `DraftReviewModal`
      opens with brief on left, draft on right. Click a draft
      section heading affordance → brief flashes the closest
      matching block (when found).
- [ ] Manual: open the Critique explorer (formerly Disagreements).
      Phase 2 tab shows `Phase 2 · 3 Q · 4 D · 7 total`. Filter
      to `Questions` → only Q cards render. Filter to
      `Disagreements` → only D cards. Filter `Open` /
      `Resolved` works across both types.
- [ ] Manual: click a Q card in the explorer → the timeline's
      raised-turn-card flashes blue, and (if answered) the
      answered-turn-card flashes blue too. Wait 2s → flashes
      clear. Click a D card → same but orange.
- [ ] Manual: pre-0034 transcript — load any spec-0033 run from
      disk. `Run.questions` populates from the existing turn files
      via the new parser. Block IDs assign on-the-fly via the
      aggregator. The explorer + sentiment paragraphs all render
      against historical data without re-running.
- [ ] Manual: hosted UI deploy — verify `questions` rides the wire
      and the explorer's Q cards render against the hosted run.

## Risks

- **Positional answer-matching mis-links questions.** If an agent
  answers questions out-of-order or skips one, the positional match
  threads the answer to the wrong question. Mitigation: the
  positional match is also annotated with a `match: 'positional' |
  'verbatim'` debug field; in CI we count `'positional'` matches per
  run and surface a warning footer in the explorer if > 50% of
  matches are positional-only. If feedback says the mismatch rate is
  too high, a follow-up spec adds explicit `Q-N` IDs in the prompt.
- **Block-ID assignment drift between backend (`protocol/blocks.py`)
  and frontend (`shared.jsx` markdown renderer).** If they disagree on
  block boundaries, anchors resolve to wrong IDs. Mitigation: tests
  in `tests/protocol/test_blocks.py` lock the boundary heuristic;
  the frontend renderer detects + applies whatever IDs the backend
  emits (single source of truth). The frontend's no-backend mode
  (test fixtures without `<!-- block-id: … -->` comments) keeps the
  old fallback ID generation logic.
- **`composeSentiment` is verbose for round 1.** Round 1 has no
  prior counts to delta against, so the paragraph might read
  similarly across the two agents. Mitigation: round-1 phrasing
  emphasises *what's being surfaced* (count of differences, count
  of questions) instead of round-over-round dynamics — see
  examples in §4.
- **`CritiqueExplorer` rename breaks any external link to the
  former `#disagreement-explorer` anchor.** Internal naming only;
  the public route is `/runs/<id>` with no anchor in v1. Search
  the codebase for `disagreement-explorer` references; rename if
  any external surface mentions it.
- **`highlightedTurnKeys` flash interaction during live SSE
  updates.** When the timeline re-renders due to an SSE delta
  mid-flash, the flash should persist because `box-shadow`
  transitions live on the DOM element. The 2s clear timeout still
  fires correctly because it's on the parent's React state, not
  the DOM. Verify with a long-running flash + SSE event.
- **`DraftReviewModal`'s "🔗 brief" affordance feels noisy.** Every
  section heading on the right pane gains a small icon. If feedback
  says it's clutter, swap to "show only on hover" — trivial CSS
  change in a follow-up.
- **Block-ID HTML comments leak into rendered output if the
  frontend doesn't strip them.** Visible `<!-- block-id: b-3 -->`
  text in the page is a visual bug. Mitigation: `shared.jsx`
  markdown renderer's tokeniser handles HTML comments — they're
  removed from the rendered text and consumed for ID assignment.
  Test fixture: a round file with `<!-- block-id: b-1 -->` literal
  in the source should still render without the comment text
  visible.

## Open questions

- Whether the explorer pane label should be **"Critique"** or
  **"Q & D"** or **"Questions and disagreements"**. v1 picks
  "Critique" — shortest, captures both, doesn't break the
  panel-header pattern (one-word labels: Timeline / Errors /
  Critique). Easy to flip if it reads wrong.
- Whether the **per-step "→ jump to turn"** affordance on each
  ProgressionStep should be an icon-button or a clickable round
  number. v1 makes the round number clickable (less visual
  noise). Re-evaluate if discoverability is poor.
- Whether the **sentiment paragraph** should default to expanded
  on the card or stay behind the existing unfold gesture. v1
  keeps the unfold gesture (paragraph appears on click — matches
  spec 0030's pattern). Could be expanded-by-default in a
  follow-up if the paragraph is genuinely valuable at-a-glance.
- Whether `Question.id` should follow the `Q-{raiser}-r{round}-{idx}`
  shape or a globally-monotonic counter (`Q-001`, `Q-002`, …). v1
  picks the structured form — easier to debug "which question was
  that" when reading raw logs; the explorer renders just the round
  + index portion in the card.
- Whether to **highlight all in-flight live turn cards** when an
  explorer Q/D references the agent currently typing. v1 doesn't —
  the flash uses `turnKey`, and live cards have a `*-live` ID
  variant that wouldn't match. Could match both variants in a
  follow-up; risks being noisy.
