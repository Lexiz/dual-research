---
spec: 0029
title: Token-consumption tab — per-turn context-window visualisation
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.27.0
created: 2026-05-16
pr: ""
---

# Spec 0029 — Token-consumption tab

## Context

The run-detail timeline today shows two things in the left pane:

1. A scrolling list of phase dividers and collapsible artifact cards
   (the "Conversation" — what each agent said in each turn).
2. A toolbar below the pane header with two `AgentLegendChip`s
   reporting per-agent run totals (Claude / GPT tokens + cost).

The chips collapse the entire run into two numbers, which is good
for at-a-glance cost monitoring but bad for understanding **how
the context is filling up**. The whole orchestration is structured
around chats that grow: Phase 2 round 4's prompt carries every prior
round's transcript; Phase 4 round 3 carries every prior review turn.
A user inspecting a slow / expensive run today has to count
artifacts and eyeball card stats to figure out which chats are
approaching context exhaustion.

The data is already in the event stream — `TurnEnded` carries
`input_tokens`, `output_tokens`, `cache_read_tokens`,
`cache_write_tokens`, `cost_usd`, `model_id`, `phase`, `label`,
`agent`. The aggregator currently throws the per-turn detail away
and only accumulates agent totals (`aggregator.py:253`). This spec
preserves the per-turn detail and surfaces it through a new
**Consumption** tab in the timeline pane that visualises each
chat's context-window fill, lane-per-agent, in the style of the
`how-it-works` chat-lifecycle diagram.

The conversation surface itself is unchanged — the existing UI is
exactly what the user wants on the Conversation tab.

## Design decisions

| # | Decision | One-liner |
|---|---|---|
| D1 | **Two tabs in the timeline pane toolbar: `Conversation` and `Consumption`.** | The Conversation tab renders what we render today (phase dividers + collapsible cards + modal). The Consumption tab renders the new bar viz. Default selection: `Conversation`. State is per-run (resets on run change), not global. |
| D2 | **Move both `AgentLegendChip`s to the right end of the toolbar.** | Same component, same numbers, same accent borders. Tabs sit on the left; chips on the right; `liveCount` pill stays adjacent to the chips. |
| D3 | **One bar row per turn (per round per agent).** | Each API call is the unit of visualisation. P0/P1/P3 produce one row each; P2 and P4 produce one row per round per agent. This is what the user means by "as it builds up and we get more input and the input gets maybe bigger" — each subsequent P2 round's bar is visibly longer than the prior round's because the history grows. A phase-aggregate view (one bar per phase) loses that signal. |
| D4 | **Bar denominator = the model's actual context window.** | Each bar is sized to its model's true context cap (Claude 4.5 Sonnet → 200K, GPT-5 → 200K, GPT-4o → 128K, etc.). Asymmetric widths between the two lanes are honest: a user can see at a glance that "Claude has more headroom than GPT" or vice versa. Source of truth is the `model_id` field already on each `TurnEnded` event; resolution is a small `CONTEXT_WINDOWS` dict alongside `agents/pricing.py`. |
| D5 | **Bar anatomy: input segment + output segment + remainder.** | Three pieces, left-to-right: (a) `input_tokens` as a solid coloured fill (agent colour), (b) `output_tokens` as a thinner trailing segment in a darker shade of the same agent colour, (c) the rest of the context window in `--bg-2`. Cache-read tokens within input are shown as a lighter inner shade (input is split into cache-read + fresh-input visually). Hover tooltip carries the full breakdown including cost and model id. |
| D6 | **Layout reuses the `LifecycleRow` grid pattern from `how-it-works.jsx`.** | A 3-column grid: `110px (phase / round label) | 1fr (Claude lane) | 1fr (OpenAI lane)`. The phase label cell is sticky-grouped — consecutive rows in the same phase share a single label cell on the left, with rounds indicated as `R1`, `R2`, … on the right side of the cell (or as compact sub-labels per row — see test plan). For P3 (drafter only), the non-drafter lane is rendered as the existing `silent` placeholder from how-it-works. |
| D7 | **No prompt-piece breakdown in v1.** | The user's ask hints at colour-coding each input chunk by kind (brief / drafts / history / plan), like the `Tk` chips in how-it-works. The orchestrator doesn't currently emit per-piece token counts — it sends the assembled prompt to the API and gets back a single `input_tokens` number. A future spec can either (a) instrument the prompt assembler to tally per-piece sizes or (b) tokenize the assembled prompt locally with `tiktoken` / `anthropic.tokenize` to back-derive. v1 ships single-colour input fill; the framework is built so the segment list can grow without refactoring. |
| D8 | **Per-turn data is recorded in a new `Run.phase_token_usage` dict.** | Flat dict keyed by `phase{N}_round{R}_<agent>` (or `phase{N}_<agent>` for single-shot phases) — the same key convention `phase_summaries` and `phase_review_items` already use. Value is a `TurnTokenUsage` dataclass with `{in_, out, cache_read, cache_write, cost, model_id}`. Mutated by the aggregator on `TurnEnded`; the existing `state.tokens.in_ += …` accumulation is unchanged (run-total chips keep working). |
| D9 | **Old runs render gracefully.** | A run replayed from a transcript that predates this spec will have an empty `phase_token_usage` dict. The Consumption tab in that case shows a small "no per-turn data" empty state with the existing agent-total chips emphasised. No data corruption; no migration. |
| D10 | **No new server endpoint.** | `phase_token_usage` is serialised as `phaseTokenUsage` inside the existing `/api/runs/{id}` snapshot, alongside `phaseSummaries`, `phaseReviewItems`, etc. The SSE delta stream picks it up automatically (the aggregator already round-trips `Run` through `to_jsonable`). |

## Proposed change

### 1. Model — `src/dual_research/ui/models.py`

New dataclass and `Run` field:

```python
@dataclass
class TurnTokenUsage:
    """Per-turn token + cost detail, captured from `TurnEnded` events."""
    in_: int = 0            # serialises as `in` at the JSON boundary
    out: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost: float = 0.0
    model_id: str | None = None


@dataclass
class Run:
    ...
    # ─── Per-turn token usage (spec 0029) ────────────────────────────────────
    # Keyed by `phase{N}_<agent>` for single-shot phases (0, 1, 3) and
    # `phase{N}_round{R}_<agent>` for round-loop phases (2, 4). Empty when
    # the run was replayed from a pre-0029 transcript that didn't record
    # per-turn telemetry.
    phase_token_usage: dict[str, TurnTokenUsage] = field(default_factory=dict)
```

`to_jsonable` already handles `in_ → in` rename — the new dataclass
benefits automatically. Wire shape: `phaseTokenUsage: { [key: string]:
{ in: number, out: number, cacheRead: number, cacheWrite: number,
cost: number, modelId: string | null } }`.

### 2. Aggregator — `src/dual_research/ui/aggregator.py`

In the existing `TurnEnded` handler (around line 253), in addition
to the current `state.tokens.in_ += …` accumulation, write a new
`TurnTokenUsage` keyed by the turn's phase + round + agent. Key
shape mirrors spec 0027/0028:

- Phases 0, 1, 3 → `phase{N}_<agent>` (single-shot).
- Phases 2, 4 → `phase{N}_round{R}_<agent>` (round-keyed).

The phase number comes from `event["phase"]` (a string like `"2"`
or `"4"` — the aggregator already parses these). Round number for
phases 2/4 comes from the existing per-agent round counter the
aggregator tracks for `phase_review_items`.

No event-shape change required; `TurnEnded` already carries
everything we need.

### 3. Context-window registry — `src/dual_research/agents/context_windows.py` (new)

Small module exporting one dict and one helper:

```python
"""Model-id → context-window-size lookup for the consumption viz."""

CONTEXT_WINDOWS: dict[str, int] = {
    # Anthropic
    "claude-opus-4-7": 200_000,
    "claude-opus-4-7[1m]": 1_000_000,
    "claude-sonnet-4-6": 200_000,
    "claude-haiku-4-5-20251001": 200_000,
    # OpenAI
    "gpt-5": 200_000,
    "gpt-5-mini": 200_000,
    "gpt-4.1": 128_000,
    "gpt-4o": 128_000,
}

DEFAULT_CONTEXT_WINDOW = 128_000


def context_window_for(model_id: str | None) -> int:
    """Look up a context window for a model id; fall back to 128k."""
    if not model_id:
        return DEFAULT_CONTEXT_WINDOW
    return CONTEXT_WINDOWS.get(model_id, DEFAULT_CONTEXT_WINDOW)
```

The dict is small and intentionally hand-maintained — model ids
change rarely and an out-of-list model just falls back to 128k
(visually it'll look slightly squished but still render correctly).

The dict is **duplicated** in `run-detail.jsx` as a frontend
constant. Sharing across the Python/JS boundary would require a
generated module — not worth the build complexity for 8 entries.
Both sides cite the spec to keep them in sync.

### 4. Frontend — `src/dual_research/ui/static/run-detail.jsx`

**`Timeline` (line 203)** — split into a tabbed container:

```jsx
function Timeline({ run }) {
  const [tab, setTab] = React.useState('conversation');  // 'conversation' | 'consumption'
  // … existing buildTimeline, openId, openItem ...
  return (
    <section …>
      <PaneHeader … />
      <PaneToolbar>
        <TimelineTabs active={tab} onChange={setTab} />
        <span style={{ flex: 1 }} />
        <AgentLegendChip agent="claude" … />
        <AgentLegendChip agent="gpt"    … />
        {liveCount > 0 && <LivePill count={liveCount} />}
      </PaneToolbar>
      {tab === 'conversation' ? (
        <ConversationView run={run} items={items} openId={openId} setOpenId={setOpenId} />
      ) : (
        <ConsumptionView run={run} />
      )}
      {tab === 'conversation' && openItem && (
        <ArtifactModal item={openItem} run={run} onClose={() => setOpenId(null)} />
      )}
    </section>
  );
}
```

**`TimelineTabs`** (new) — segmented control of two pills matching
the existing `AgentLegendChip` aesthetic (`border-radius: 999`,
`var(--bg-2)`, agent-style accent border on the active pill). No
icons; just text + a thin underline / fill on the active pill.

**`ConversationView`** (new, but is just the existing render path
extracted) — the current `items.map(…)` rendering plus the
overflow-auto container. No behavioural change.

**`ConsumptionView`** (new) — renders the bar grid. Pseudocode:

```jsx
function ConsumptionView({ run }) {
  const rows = buildConsumptionRows(run);  // [{ label, phase, round?, claude?, gpt? }, …]
  if (rows.every(r => !r.claude && !r.gpt)) {
    return <EmptyConsumption agents={run.agents} />;
  }
  return (
    <div className="dr-consumption" style={{ /* 3-col grid */ }}>
      <ConsumptionHeader />
      {rows.map(row => <ConsumptionRow key={row.id} row={row} />)}
    </div>
  );
}
```

`buildConsumptionRows(run)` walks the canonical phase order
(0, 1, 2 × N rounds, 3, 4 × N rounds) and pulls the matching
`run.phaseTokenUsage[key]` entry per agent. A missing entry yields
a "silent" lane cell, the same placeholder how-it-works uses for
P3's non-drafter lane.

`ConsumptionRow` renders three cells:
- Phase / round label (mono uppercase, like LifecycleRow's tag cell).
- `<TokenBar usage={row.claude} agent="claude" />` or silent.
- `<TokenBar usage={row.gpt}    agent="gpt"    />` or silent.

`TokenBar` (new) — the actual progress bar. Computes:
- `denominator = CONTEXT_WINDOWS_JS[usage.modelId] ?? 128_000`
- `inputFill = usage.in / denominator`
- `cacheFill = usage.cacheRead / denominator` (lighter shade inside input)
- `outputFill = usage.out / denominator` (darker trailing shade)
- Renders three flex-row segments inside a rounded container with
  `var(--bg-2)` background and the agent's accent border.

A row below the bar shows the compact numeric:
`{fmt.tokens(usage.in)}t in · {fmt.tokens(usage.out)}t out · {(inputFill * 100).toFixed(1)}%`.

Hover (`title` attr — keeps it lightweight) carries the full
breakdown: input / output / cache read / cache write / cost / model.

### 5. Tests

Backend:

- `tests/ui/test_aggregator_token_tracking.py` (new) —
  - `TurnEnded` for `phase=0, agent=claude` populates
    `Run.phase_token_usage["phase0_claude"]` with the right
    `{in_, out, cache_read, cache_write, cost, model_id}`.
  - Two `TurnEnded` events for phase 2 round 3 (claude + gpt) both
    land under their distinct keys.
  - Phase 3 only writes one entry (drafter only).
  - Old behaviour preserved: `agents.claude.tokens.in_` still
    accumulates correctly across all turns.
- `tests/ui/test_server.py` — extend an existing snapshot test to
  assert `phaseTokenUsage` appears in the wire payload with the
  expected `in` (not `in_`) field name.
- `tests/agents/test_context_windows.py` (new) —
  - Every model id we currently use in pricing (`agents/pricing.py`)
    appears in `CONTEXT_WINDOWS` OR maps to the default.
  - `context_window_for(None)` returns the default.
  - `context_window_for("unknown-model")` returns the default.

Frontend: manual only (project convention — no FE unit tests yet).

### 6. Versioning + release notes

- `pyproject.toml`, `src/dual_research/__init__.py`: 0.26.0 → 0.27.0.
- `CHANGELOG.md`: `## [0.27.0] — YYYY-MM-DD` block summarising the
  consumption tab + the per-turn telemetry plumbing.
- `VERSION_NOTES` entry at the top of `how-it-works.jsx` mentioning
  the new tab.

### 7. How-it-works cross-reference

Add a short note in `how-it-works.jsx` under the Chat Lifecycle
section: "*The Consumption tab in the run timeline shows the same
lanes filled with real token counts from the run.*" One sentence;
links the diagram to the new viz.

## Out of scope

- **Per-piece prompt breakdown** (brief / drafts / history / plan as
  separate segments). Requires either prompt-assembler instrumentation
  or local tokenisation. Worth a follow-up spec if v1 doesn't carry
  enough signal. v1 ships a single input fill per turn.
- **Live updates during a turn.** `TurnEnded` fires once the API
  call completes; mid-turn token streaming isn't surfaced. The bar
  appears in full when the turn lands. Acceptable — this is a
  post-hoc / mid-run diagnostic, not a streaming meter.
- **Cross-phase chat continuity.** Each phase is a fresh API call
  with reconstituted history; there's no "single continuous Claude
  chat" object to track. The bars are per-turn, not per-conversation.
- **Cost-budget warnings.** The existing `Budget` field (`models.py:101`)
  is unrelated; this spec doesn't surface budget warnings on the bars.
- **Frontend tokenisation fallback.** If `phaseTokenUsage` is empty
  (old runs), the tab shows an empty state — it does not attempt to
  back-derive token counts by tokenising the artifact bodies.
- **CSV / JSON export of the consumption data.** The wire format is
  already JSON; users wanting raw numbers can hit `/api/runs/{id}`
  directly. No new export endpoint.
- **Cache-pricing nuance.** Cache reads cost ~10% of fresh input
  tokens; the aggregator's existing cost accumulation already handles
  that (the pricing module distinguishes). We surface the cache-read
  count visually but don't separately tag the cost split.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec 0029 adds at least
      6 new tests (per-turn aggregator wiring, key shapes for all
      phase types, wire-format presence, context-window registry
      lookups + fallback).
- [ ] Manual: trigger a fresh full-tier run, watch the timeline pane
      while it progresses. Toggle to Consumption. Each phase / round
      that lands produces a new row; bars grow visibly across P2
      rounds; P3 has one lane filled (drafter) and one silent.
- [ ] Manual: hover a bar — tooltip shows input / output / cache
      read / cache write / cost / model id. Numbers match the
      Conversation tab's per-turn card stats.
- [ ] Manual: load an old run (e.g. a fixture run from before this
      spec). Consumption tab shows the empty state; Conversation
      tab is unchanged.
- [ ] Manual: switch between runs in the all-runs list. Active tab
      resets to Conversation on run change (per D1).
- [ ] Manual: hosted UI — deploy and verify the snapshot endpoint
      carries `phaseTokenUsage`. SSE delta updates flow through.

## Risks

- **Asymmetric bar widths look weird at first glance.** Claude at
  200K vs GPT at 128K means the Claude lane's bar container is
  visibly wider. This is honest (the context windows really are
  asymmetric) but may confuse a user who expects identical lanes.
  Mitigation: the per-bar numeric row shows the `%` of context used,
  so the comparison the user usually wants ("how full is each chat?")
  is one glance away regardless of bar width.
- **Context-window registry drifts when new models ship.** Adding a
  new model to `agents/pricing.py` will silently fall back to 128k
  in the consumption viz until `CONTEXT_WINDOWS` is updated. The
  `test_context_windows.py` test catches the missing-id case at
  CI time.
- **Old transcripts produce an empty Consumption tab.** Acceptable
  per D9; the empty state explains it. No back-filling attempted.
- **Bar tooltip uses `title` attribute, not a styled popover.** The
  styled-popover route would mean writing yet another tooltip
  component; `title` is good enough for v1 and matches the existing
  cost-badge pattern (`run-detail.jsx:82`).
- **Per-piece breakdown deferral may underwhelm.** The user's prompt
  asked for per-input segmentation; v1 ships one fill colour per
  turn. The framing in the spec calls this out (D7) and the visual
  framework is built so segments can grow without refactoring.

## Open questions

- Whether to also surface the **drafter's revised-draft** Phase 4
  turns differently. They have a `## Revised draft` section that
  bloats output tokens compared to comment-only turns. v1 just
  shows the raw `output_tokens` for each turn; nothing special for
  drafter rounds. A future spec could tag drafter-revision rounds.
- Whether the Consumption tab should be remembered across page
  reloads (URL hash / localStorage). v1 resets to Conversation on
  any run change or reload — simpler and avoids stale-tab-on-other-run
  confusion. Promotable later.
- Whether to render a **summary row at the top** of the Consumption
  tab — total tokens by phase across both agents, as a quick
  "where did the budget go" view. v1 just lists per-turn rows; the
  per-agent chips in the toolbar carry the run-total signal.
