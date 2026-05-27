---
spec: 0030
title: Timeline UX pass — inline unfold, per-input segments, real context windows, parser repairs
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.28.0
created: 2026-05-16
pr: "https://github.com/Lexiz/dual-research/pull/32"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0030 — Timeline UX pass

## Context

Spec 0029 shipped the Consumption tab and exposed a handful of issues
that landed in the user's first end-to-end pass:

1. **Card click goes straight to a modal.** Spec 0025 replaced
   inline-expand with a centred modal "for every place an agent
   critiques prior content." On a normal timeline pass, that's too
   heavy — the user wants to skim, not commit to a full-page view on
   every click. They want the cards back to **unfold inline** with a
   summary and a synthesised gist; the modal becomes the explicit
   second click via a "View in full mode" button.

2. **Disagreement cards show a "Contested point" heading with no
   body.** The parser in `disagreements.py::_parse_one_entry`
   (lines 176–193) extracts `point` only when the round file uses
   the exact form `(a) D-N: "the contested-point statement"`. Real
   round files often use a heading-only form ("`### D-3 — SQLite vs
   Postgres for production`") with the actual point in the bullets
   underneath, leaving `point=""`. The UI dutifully renders the
   "Contested point" label with no content.

3. **Progression timeline shows "raised" with no note.**
   `_progression_note(action, entry)` (line 483) returns
   `entry.get("point") or entry.get("my_position") or ""`. When #2
   fails, both fall through to `""` and the progression step prints
   the action verb with no context. This is the same root cause as
   #2 — fixing the point extractor implicitly fixes the note.

4. **Consumption bars show a single input fill, not per-input
   segments.** Spec 0029 D7 explicitly deferred this. The user's
   ask was always "reuse the how-it-works `Tk` palette" — one
   coloured segment per prompt-bundle piece. Shipping that
   completes the original vision and makes the buildup truly visible
   (you can see the history segment grow round by round).

5. **Bars are sized to 200K when prod runs the 1M-context tier.**
   Spec 0029 hand-rolled `agents/context_windows.py` with made-up
   200K values, ignoring the `ModelSpec.context_window` field that
   already lives on `config.py::PROD_TIER` (1_000_000 for both
   models). This was a registry-duplication bug from day one — the
   right context window has been sitting in `config.py` the whole
   time. Fix: delete the registry, surface `context_window` through
   the event stream, store per turn.

The five items share the same surface (timeline pane + per-turn
data flow) and land naturally as one spec.

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **Cards unfold inline on click. The modal moves behind a "View in full mode" button inside the unfolded body.** | Reverses the spec-0025 "no inline expand" decision for the click handler only. The Modal component itself stays — it's still the right primitive for the heavy view — but it's no longer the *immediate* click target. |
| D2 | **Unfolded card body = summary paragraph + stats chips + synthesised gist line + "View in full mode" button.** | Summary comes from the existing `run.phaseSummaries[key]` (extracted by spec 0025). Stats chips are the same TurnStats-derived chips that show on the collapsed card today. The gist is a one-line synthesised sentence (e.g. "Claude raised 4 questions, conceded D-3") composed from `TurnStats` + `Run.disagreements` — light synthesis, no LLM. The full body stays in the modal. |
| D3 | **Disagreement parser falls back to bullet/prose content when the inline `D-N: "…"` form is absent.** | `_parse_one_entry` learns a second extractor: if no `(a) D-N: "…"` is found, walk the lines beneath the entry header and take the first non-empty content line (stripped of bullet markers) as `point`. Same change applies to `my_position` / `other_position` fallback (use the first bullet labelled "I claim" / "they claim" if the inline form is missing). |
| D4 | **Per-input consumption segments use the seven `Tk` kinds from how-it-works.** | `brief`, `d1` (Phase 1 draft claude), `d2` (Phase 1 draft openai), `hist` (P2 prior-round transcripts), `plan` (agreed plan), `draft` (current draft-vN.md), `histp` (P4 prior-round transcripts). One coloured segment per kind per bar. Direct visual continuity with `ChatLifecycle`. |
| D5 | **Orchestrator emits per-piece token sizes alongside `input_tokens` on `TurnEnded`.** | The prompt assembler already has the per-piece strings in hand at call time. We tokenize each piece (`tiktoken` for OpenAI, `anthropic.tokenize` or a char-÷-4 heuristic for Anthropic — see D6 for the precision call) and emit a `prompt_pieces: dict[str, int]` field on the event. Aggregator preserves the dict on `TurnTokenUsage.prompt_pieces`. |
| D6 | **Per-piece sizes are best-effort, not invoice-grade.** | The provider's `input_tokens` count is the cost-of-record. Our per-piece sum may differ by a small percent due to tokenizer drift (Anthropic doesn't ship a public tokenizer; we use char÷3.5 as the standard rough conversion). The visual is "what fraction of the input was each piece," not "exact API billing." The numeric percent on each bar reads the provider's `input_tokens` for the total; segment widths are computed proportionally from `prompt_pieces` and renormalised to sum to `input_tokens`. |
| D7 | **Context window comes from the wire, not a frontend registry.** | `agents/context_windows.py` is deleted. The `run_started` event already carries `claude_model` / `openai_model` — we extend it with `claude_context_window` / `openai_context_window` (sourced from `ModelSpec.context_window` in `config.py`). Aggregator stores these on `AgentState.context_window`. Each `TurnTokenUsage` also gets a `context_window` field (so per-bar denominators survive when the model id rotates mid-run, hypothetically). Frontend reads the denominator straight off the wire. |
| D8 | **`AgentState.model` gets the friendly name and the context-window number.** | The chrome already shows model names; surfacing the window means we can also drop a "1M / 200K" badge in the consumption legend if useful. Out of scope for the legend in v1, but the data is there. |
| D9 | **Inline-unfold animation is a single CSS max-height transition.** | No animation library. Matches the rest of the codebase's inline-style approach. ~150ms ease-out. |
| D10 | **The Modal component, `ArtifactModal`, `NegotiateReviewModal`, and the inline-comment scroll-and-flash machinery stay exactly as they are.** | Spec 0027/0028 inline comments still work — clicking "View in full mode" on a Phase 2 / Phase 4 turn card opens the same side-by-side modal. The only behaviour change is what the click on the *card itself* does. |

## Proposed change

### 1. Inline unfold — `src/dual_research/ui/static/run-detail.jsx`

- `Timeline` keeps its `openId` state but ALSO tracks per-card
  `expandedIds: Set<string>` for the inline-unfold view.
- `TimelineItem` / `ArtifactCard` rework:
  - Click on the card header → toggle the card in `expandedIds`
    (no longer sets `openId`). The collapsed appearance is
    unchanged from today.
  - When expanded, the card shows: existing TL;DR summary row +
    a new "Gist" line (D2) + the existing stats chips +
    a `<button>` labelled **View in full mode** at the bottom of
    the unfolded body.
  - Clicking **View in full mode** sets `openId` and opens the
    existing modal as it does today.
  - Keyboard: `Enter` or `Space` on the focused card toggles
    expansion; `o` while expanded opens the modal.
- The collapsed → expanded transition is a CSS `max-height`
  animation (~150ms ease-out) — single transition rule on the
  unfolded container.
- Live items (`item.live === true`) keep their current streaming
  view; expansion is a no-op while live.

### 2. Gist composer — same file

A new `composeGist(item, run)` helper. Reads:
- `item.statsPhase`, `item.agent`, `item.round`.
- `run.phaseStats[phaseN][round][agent]` (or `phaseN[agent]` for
  single-shot phases) — the existing `TurnStats`.
- `run.disagreements` — filter to ones touched in this round
  (`d.round === item.round && d.phase === item.statsPhase`).

Outputs a one-liner like:
- Phase 0 (preflight): `"Claude flagged 12 issues with the brief"` /
  `"Claude approved the brief"`.
- Phase 1 (draft): `"Wrote the plan draft (no critique stats yet)"`.
- Phase 2 (round R): `"Raised 4 questions; conceded D-3"`.
- Phase 3 (drafter): `"Wrote v1 of the converged document"`.
- Phase 4 (round R): `"3 issues, 1 substantive disagreement"`.

A switch statement keyed on `phase × (drafter ? 'draft' : 'review')`.
Empty stats → omit the sentence entirely (no awkward `"Raised 0
questions"`).

### 3. Disagreement parser fallback — `src/dual_research/ui/disagreements.py`

`_parse_one_entry` (line 176–) currently extracts `point` only from
the `(a) D-N: "the point"` form. Extend it:

- After the inline-form scan fails, fall back to "the first
  non-empty content line below the entry header." Content lines
  are bullets (`- `, `* `, `1. `) and plain paragraphs; whitespace
  and the entry header itself are skipped.
- Strip leading bullet markers; cap at 200 characters with `…`
  truncation. This becomes `point`.
- Similar fallback for `my_position` / `other_position`: prefer
  inline `(b)` / `(c)` markers; fall back to the first bullet
  labelled `**I claim**`/`**they claim**` (case-insensitive); fall
  back again to the second / third content line if labels are
  absent.

`_progression_note` (line 479–) needs no change — once `point` is
populated, the note pipeline finds it via `entry.get("point")`.

### 4. Prompt-piece instrumentation — orchestrator + agents

This is the heaviest piece. New data shape on `TurnEnded`:

```python
@dataclass(frozen=True, kw_only=True)
class TurnEnded(Event):
    ...
    prompt_pieces: dict[str, int] = field(default_factory=dict)
    #   "brief" | "d1" | "d2" | "hist" | "plan" | "draft" | "histp"
    #   → token count for that piece
```

The prompt assembler — currently in `protocol/prompts.py` —
constructs each turn's prompt by concatenating fixed pieces. Today
the function returns the assembled string. Refactor it to return a
`PromptBundle` dataclass:

```python
@dataclass(frozen=True)
class PromptBundle:
    text: str
    pieces: dict[str, int]  # kind → token count (best-effort)
```

Each `make_phase{N}_prompt` (or equivalent) emits `text` AND a
`pieces` map. The agent layer (`anthropic_agent.py`,
`openai_agent.py`) carries the `pieces` map forward and includes
it in the `TurnEnded` event payload.

Tokenisation:
- OpenAI side: `tiktoken.encoding_for_model(model_id).encode(text)`,
  fall back to `cl100k_base` for unknown models.
- Anthropic side: char ÷ 3.5 heuristic. Anthropic doesn't publish a
  public tokenizer; the heuristic is the documented rule of thumb
  and is good enough for proportional segment widths. (D6.)

### 5. Wire context windows — config + run_started + aggregator

- `events/types.py::RunStarted` gains
  `claude_context_window: int = 0` and
  `openai_context_window: int = 0`.
- Orchestrator emits these when starting a run, sourced from
  `tier.claude.context_window` / `tier.openai.context_window`.
- `aggregator._on_run_started` stamps them on
  `AgentState.context_window` (new field, `int`, defaults to 0).
- `aggregator._on_turn_ended` copies the agent's
  `context_window` (or the event's, if it carries one) onto the
  new `TurnTokenUsage.context_window` field.
- Wire format: `phaseTokenUsage[key].contextWindow`,
  `agents.<ag>.contextWindow`.

### 6. Frontend — read window from wire, render per-input segments

- **Delete** the `CONTEXT_WINDOWS_JS` / `contextWindowFor` block
  in `run-detail.jsx`. `TokenBar` reads `usage.contextWindow`
  directly; falls back to the agent's `run.agents[ag].contextWindow`
  if missing; final fallback is `128_000` for old runs.
- `TokenBar` segments rework:
  - If `usage.promptPieces` is present and non-empty, render one
    coloured segment per kind in the canonical Tk order:
    `brief, d1, d2, plan, hist, draft, histp` (the order matches
    how-it-works' visual). Colours come from a small
    `KIND_COLORS` map (mirrors the `Tk` palette in
    `how-it-works.jsx`).
  - Renormalise segment widths so they sum to `input_tokens`
    (D6) — handles tokeniser drift gracefully.
  - Output tail and cache-read inner shade rendering unchanged.
  - Hover tooltip lists every non-zero piece with its token count.
- The `ConsumptionLegend` at the bottom expands to include a row
  of kind swatches with their labels.

### 7. Delete `src/dual_research/agents/context_windows.py`

And the import in `run-detail.jsx`'s notes. Also update spec 0029's
front-matter status to remain `merged` but add a follow-up
reference note: "spec 0030 supersedes the registry approach with
wire-format context windows."

### 8. Tests

- `tests/protocol/test_prompt_bundle.py` (new) — each
  `make_phase{N}_prompt` returns a `PromptBundle` whose `pieces`
  contains the expected kinds with non-zero counts. The kinds
  match the spec D4 list verbatim.
- `tests/events/test_turn_ended_prompt_pieces.py` (new) — agent
  layer surfaces `prompt_pieces` on `TurnEnded`.
- `tests/ui/test_aggregator_token_tracking.py` — extend with a
  `context_window` and `prompt_pieces` assertion on each per-turn
  entry; both round-trip through `_to_camel` correctly.
- `tests/ui/test_disagreements.py` — extend with a fixture using
  the heading-only `### D-N — short label` form and assert that
  `Disagreement.point` falls back to the first bullet's text.
- `tests/ui/test_disagreement_progression.py` (extend existing) —
  same fixture → the "raised" progression step's `note` is
  populated from the same fallback.
- `tests/agents/test_context_windows.py` — **delete** (its
  premise — that a JS-side registry tracks windows — no longer
  applies).
- `tests/ui/test_server.py` — assert the snapshot carries
  `contextWindow` on agents and on each `phaseTokenUsage` entry.
- Frontend: manual only.

### 9. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.27.0 → 0.28.0.
- `CHANGELOG.md`: new `## [0.28.0] — YYYY-MM-DD` entry.
- `VERSION_NOTES` entry at the top of `how-it-works.jsx`
  summarising the five items.

## Out of scope

- **Reflowing the modal contents.** The "View in full mode" modal
  is the same modal that opens today; no layout change.
- **Live per-piece streaming.** The bars update on `TurnEnded`,
  not mid-call — same cadence as spec 0029.
- **Cost-budget warnings on the bars.** Still out of scope (D5
  / 0029).
- **A precise Anthropic tokeniser.** The char÷3.5 heuristic is
  intentional and documented (D6). A future spec could ship a
  proper tokeniser if the visual ever feels meaningfully off.
- **Per-round draft history for Phase 4.** Still deferred from
  spec 0028's known limitation.
- **Disagreement-parser overhaul.** This spec adds a fallback for
  the missing `point` only. The broader parser (status
  transitions, resolution detection, deadlock marking) stays as-is.
- **The TEST_TIER context-window mismatch.** `TEST_TIER` declares
  `gpt-5-mini` at 400K which differs from my earlier 128K guess;
  this is now resolved because we read from the wire. No further
  action.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec 0030 adds at
      least 10 new tests (prompt-bundle shapes per phase,
      `TurnEnded` event field, aggregator wiring for both
      `context_window` and `prompt_pieces`, disagreement
      fallback for both heading-only and inline forms, snapshot
      camelCase presence).
- [ ] Manual: trigger a fresh prod-tier run. Click a Phase 2 turn
      card → unfolds inline with the gist line + summary + stats +
      "View in full mode" button. Click the button → existing
      modal opens. `Esc` closes the modal but leaves the card
      expanded. Click the card header again → collapses.
- [ ] Manual: Consumption tab on the same run shows segmented
      bars in the Tk palette; segments grow round-by-round (`hist`
      visibly larger in P2 R3 than P2 R1).
- [ ] Manual: bars are 1M-token wide for prod runs; hover tooltip
      shows `window: 1,000,000t`. Test-tier runs (haiku + gpt-5-
      mini) show their respective windows (200K / 400K).
- [ ] Manual: a Phase 2 round with a heading-only `### D-N` form
      now shows the contested point's first bullet on the
      Disagreements pane; the progression step's "raised" note
      carries the same text. Pre-fallback round files still
      parse correctly (no regression on the inline-form fixtures).
- [ ] Manual: pre-0029 transcripts still produce empty
      Consumption bars (no `prompt_pieces`, no
      `context_window`) — the empty-state UI from spec 0029 still
      shows.
- [ ] Manual: hosted UI deploy — verify `phaseTokenUsage[*]`
      entries on the wire carry `contextWindow` and
      `promptPieces`; SSE delta updates flow through.

## Risks

- **The parser fallback may scrape the wrong line.** If a heading-
  only D-N block leads with a meta line ("- Status: open"), that
  could end up in `point`. Mitigation: skip lines that match
  known meta-prefixes (`status:`, `- status:`, `> `) before
  taking the first content line. Captured as a tiny helper in
  `_parse_one_entry`.
- **Anthropic char÷3.5 heuristic over- or under-counts.** Renorm
  to `input_tokens` (D6) keeps the visual proportional. The
  hover tooltip is honest about kind sizes being "approximate"
  if the renorm factor differs from 1.0 by > 10%.
- **`prompt_pieces` adds payload to every `TurnEnded` event.**
  Seven small integers — negligible.
- **Refactor of `prompts.py` to return `PromptBundle`s touches a
  protocol-critical file.** All existing prompt-text fixtures must
  still match exactly; the refactor only adds a sibling `pieces`
  dict. A regression here would change agent behaviour, so the
  test suite stays the regression gate.
- **Cards that aren't `turn`-kind have less to gist.** For Phase
  0 input, Phase 1 plan, Phase 3 doc, the gist is shorter and
  borrows from preflight stats / phase-completion events. The
  composer's switch statement has a sensible default per kind.

## Open questions

- Whether the **"View in full mode"** button should default to a
  keyboard shortcut (`o`?) when the card is focused — captured as
  D1 but not strictly required. v1 keeps `Esc` for close and `o`
  for open; we can iterate if either feels wrong.
- Whether the **gist composer** should also surface
  `current_draft_path` references on Phase 4 review cards ("3
  comments on draft v2"). v1 doesn't; future spec.
- Whether to keep `agents/context_windows.py` as a
  thin compat shim until external consumers migrate, or just
  delete it outright. v1 deletes outright — the registry was
  never exported in a public surface.
