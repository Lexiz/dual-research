---
spec: 0031
title: Consumption-tab follow-ups — tier-lookup window, click-to-expand bars, per-phase web-search count
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.29.0
created: 2026-05-16
pr: "https://github.com/Lexiz/dual-research/pull/33"
---

# Spec 0031 — Consumption-tab follow-ups

## Context

First end-to-end pass over the spec-0030 consumption tab surfaced
three concrete asks:

1. **The bars still show 128K, not 1M, on existing runs.** Spec
   0030's wiring is correct for runs *recorded after* v0.28.0
   landed, but every run replayed from a pre-0030 transcript carries
   no `claude_context_window` / `openai_context_window` fields on
   its `run_started` event. The aggregator defaults to 0; the
   frontend then hits its `DEFAULT_CONTEXT_WINDOW = 128_000`
   fallback. `model_id` *is* in old transcripts, so we can derive
   the right window server-side from `config.py::TIERS`. No data
   changes required — just the aggregator deriving the window from
   the known model id.

2. **Per-piece numbers aren't visible.** Spec 0030 renders one
   coloured segment per prompt-piece kind, but the actual token
   counts live only inside the `title=` hover tooltip. The user
   wants a click-to-expand interaction that lays the numbers out
   explicitly — same unfold pattern we built on the Conversation
   tab. Without numbers in the open, the bars don't carry their
   weight as a diagnostic.

3. **Per-phase web-search count + cost.** Originally pitched as
   "tokens used by tools" — neither provider reports tool tokens
   separately (search results are folded into `input_tokens`), so
   the honest substitute is the **search request count** and its
   **per-request cost**. `AgentResult.extras["searches"]` already
   captures the count for both providers; pricing just needs a
   per-request rate. Anthropic charges $10/1k web-search requests;
   OpenAI charges roughly $25/1k for `gpt-5.5` / `gpt-5-mini`.

All three land on the same surface (`run-detail.jsx::ConsumptionView`
+ aggregator + pricing) and naturally bundle into a single spec.

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **`AgentState.context_window` falls back to a TIERS-lookup by `model_id`.** | Aggregator's `_on_run_started` is the right place: when `claude_context_window` / `openai_context_window` are missing or zero, scan `config.py::TIERS` for any `ModelSpec` whose `model_id` matches and use its `context_window`. Old transcripts immediately render at 1M after the next deploy with zero data migration. |
| D2 | **Same fallback applied per-turn.** | If `state.context_window` is still 0 at `_on_turn_ended` time (theoretical edge — `run_started` was never seen), use the same lookup against the event's `model_id`. Defence in depth; never breaks. |
| D3 | **Bars on the Consumption tab become clickable.** | Click anywhere in a `ConsumptionRow` → toggle expansion. The whole row (both lanes) expands together, keeping the side-by-side rhythm. Click again to collapse. Mirrors the Conversation-tab card unfold from spec 0030 — same UX vocabulary across both tabs. |
| D4 | **Expanded body = a two-column per-piece table.** | Left column: prompt-piece kind labels in canonical Tk order (`brief`, `d1`, `d2`, `plan`, `hist`, `draft`, `histp`). Two value columns: Claude tokens, OpenAI tokens — empty for the silent lane. Bottom rows summarise input total, output total, web-search count, and per-search cost. Numbers come from `usage.promptPieces` + `usage.in/out` + `usage.searches/searchCost` on the wire. |
| D5 | **`AgentResult.extras["searches"]` flows into `TurnEnded.searches` (new field).** | Same path the existing token fields take. Aggregator stamps it on `TurnTokenUsage.searches` and computes the per-search cost via the new pricing rate (D6). |
| D6 | **`ModelPricing` gains `web_search_per_request: float`.** | Anthropic `claude-sonnet-4-6` / `claude-haiku-4-5`: $0.010. OpenAI `gpt-5.5` / `gpt-5-mini`: $0.025. Defaults to 0.0 for unknown models. `compute_search_cost(model_id, n)` → USD. |
| D7 | **Search cost is a separate side-channel — does NOT join `cost_usd`.** | Existing `AgentResult.cost_usd` and `AgentState.cost` keep their token-only semantics (no behaviour change for the run-total chip). The expanded panel labels search cost explicitly so the user sees what's what. A future spec can decide whether to roll search cost into the headline number. |
| D8 | **Per-phase web-search count is shown in the expanded body, not on the collapsed row.** | Avoids cluttering the dense bar grid. Hidden by default; revealed when the user is already inspecting that phase. |
| D9 | **No new event-shape change beyond the `searches` integer.** | `TurnEnded.searches: int = 0`. Defaults preserve compatibility with old transcripts (which become "0 searches"). |
| D10 | **Old-transcript `searches` data IS recoverable.** | The `searches` value was being persisted on `AgentResult` since the agent layer was written but not threaded into events. Old runs simply show 0 — acceptable. A future spec could mine the transcript for tool-call markers if needed. |

## Proposed change

### 1. Aggregator — `src/dual_research/ui/aggregator.py`

- New helper `_context_window_from_tier(model_id: str) -> int`. Walks
  `from dual_research.config import TIERS` and returns the
  `context_window` of the first `ModelSpec` whose `model_id` equals
  the argument (case-sensitive). Returns 0 if no match.
- `_on_run_started`: after the existing assignments, if
  `agents["claude"].context_window == 0`, look up by
  `agents["claude"].model_id` and assign. Same for `gpt`. This is
  the **fix for issue #1**.
- `_on_turn_ended`: when stamping `context_window` on the new
  `TurnTokenUsage`, prefer `state.context_window` (same as today),
  but if 0, fall back to the same tier-lookup using the event's
  `model_id`.
- `_on_turn_ended` also reads `event.get("searches", 0)` and stores
  it on `TurnTokenUsage.searches` (D5).

### 2. Pricing — `src/dual_research/agents/pricing.py`

- Extend `ModelPricing` with `web_search_per_request: float = 0.0`
  and a `notes` clause noting the source.
- Update existing `PRICING` entries:
  - `claude-sonnet-4-6`: 0.010
  - `claude-haiku-4-5`: 0.010
  - `gpt-5.5`: 0.025
  - `gpt-5-mini`: 0.025
- New helper `compute_search_cost(model_id: str, n: int) -> float`.
  Mirrors `compute_cost`'s lenient prefix-match.

### 3. Models — `src/dual_research/ui/models.py`

`TurnTokenUsage` gains:

```python
@dataclass
class TurnTokenUsage:
    ...
    searches: int = 0          # spec 0031
    search_cost: float = 0.0   # spec 0031 — USD; computed at aggregator time
```

Wire shape: `searches`, `searchCost`. Old transcripts produce
0 / 0.0 (defaults).

### 4. Events — `src/dual_research/events/types.py`

`TurnEnded` gains `searches: int = 0`. The transcript writer in
`_call.py` (already extended in spec 0030) adds `searches=` to its
keyword dump.

### 5. `_call.py` — pull `searches` from `result.extras`

Already-existing field (`AgentResult.extras["searches"]`). One
line: `searches = (result.extras or {}).get("searches", 0) or 0`,
then pass to the `TurnEnded(...)` constructor and the
`transcript.write(...)` call.

### 6. Frontend — `src/dual_research/ui/static/run-detail.jsx`

- `ConsumptionRow` becomes clickable; tracks per-row `expanded`
  state. The whole row's container element gets `cursor: pointer`
  and toggles a sibling expanded body.
- New `ConsumptionRowExpanded({ row, run })` component:
  - Renders below the row when expanded.
  - 3-column grid: kind label · Claude value · OpenAI value.
  - One row per kind in `KIND_ORDER`, only kinds present on at
    least one lane shown.
  - Below the kind table: `Input total`, `Output`, `Web searches`,
    `Tool cost` rows summarising both lanes.
  - Numbers formatted via existing `fmt.tokens` / `fmt.cost`.
- The `ConsumptionLegend` adds a small one-line note under it:
  "*click any phase row to see exact per-input numbers*".
- `TokenBar` gets a `cursor: pointer` hover hint via the row's
  click handler — no separate click on the bar itself, since
  expansion is row-scoped (D3).

### 7. Tests

- `tests/agents/test_pricing.py` (extend / new) — `compute_search_cost`
  for known and unknown models; `web_search_per_request` rates
  match D6.
- `tests/ui/test_aggregator_token_tracking.py` — new test:
  `searches` from `TurnEnded` lands on `TurnTokenUsage.searches`;
  `search_cost` is computed via pricing and stamped.
- `tests/ui/test_aggregator_token_tracking.py` — new test for D1 +
  D2: a `run_started` event WITHOUT `claude_context_window` but
  WITH `claude_model="claude-sonnet-4-6"` produces
  `agents["claude"].context_window == 1_000_000`.
- `tests/ui/test_server.py` — assert `searches` and `searchCost`
  appear on each `phaseTokenUsage` entry (camelCase boundary).
- Frontend: manual only.

### 8. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.28.0 → 0.29.0.
- `CHANGELOG.md`: `## [0.29.0] — YYYY-MM-DD`.
- `VERSION_NOTES` entry on the how-it-works page summarising the
  three items.

## Out of scope

- **True tool-token attribution.** Neither Anthropic nor OpenAI
  reports the token cost of tool RESULTS as a separate line item;
  search-result content is folded into `input_tokens` and is
  indistinguishable from prompt content downstream. Search count +
  per-request cost is the honest substitute (D6 / D7).
- **Rolling search cost into the headline `cost` chip.** Out of
  scope per D7. Future spec if needed.
- **Reasoning tokens** (OpenAI's `output_tokens_details.reasoning_tokens`).
  Real, separate, non-trivial — but asymmetric (no Anthropic
  equivalent) and not requested in the user's prompt.
- **Per-piece breakdown for the *output* tail.** Output isn't
  decomposable the way input is; the unfolded body shows it as a
  single number.
- **Mining old transcripts for searches that weren't recorded in
  events.** Old runs show 0 searches — acceptable per D10.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec 0031 adds at
      least 6 new tests (pricing rates + search-cost helper,
      aggregator wiring for searches and search_cost, tier-lookup
      fallback for context_window, snapshot wire-format).
- [ ] Manual: refresh https://dual-research-alex.fly.dev/ on an
      existing run after deploy. Bars show 1,000,000-token width
      for prod-tier runs without re-running anything (D1).
- [ ] Manual: click a phase row on the Consumption tab → expands
      below into a per-piece table with explicit token counts;
      bottom of the table shows web-search count + tool cost per
      lane (D3 / D4 / D8).
- [ ] Manual: click again → collapses. Multiple rows can be
      expanded independently.
- [ ] Manual: trigger a fresh prod-tier run, verify `searches`
      values are non-zero in the expanded body when the agents
      perform web search.

## Risks

- **Search-pricing values may drift.** Per-request rates from
  vendors change; the in-tree values are best-effort. Mitigation:
  the rates live in one dict (`pricing.PRICING`), tested for
  presence; updating any number is a one-line change.
- **Tier-lookup fallback prefers the FIRST matching `ModelSpec`.**
  If two tiers ever share a `model_id` with different
  `context_window` values (currently they don't), the iteration
  order picks the first one. Acceptable until a real conflict
  arises; flagged in the helper docstring.
- **Click-to-expand on a long Consumption tab can stack a lot of
  expanded panels.** No virtualization; list is small (≤ ~25 rows
  in practice). Acceptable.
- **Search cost is presented separately from the headline `cost`
  chip.** Risk that users miss it. Mitigation: the expanded body
  labels both lines clearly; a future spec can promote.

## Open questions

- Whether to also annotate the **collapsed** row with a small
  "🔍 N" badge when search count > 0. Cleaner discoverability;
  costs vertical real estate on every row. v1 keeps it
  expanded-only per D8; happy to promote if you ask.
- Whether `web_search_per_request` rates should be sourced from a
  shared pricing table (e.g. an upstream JSON) rather than
  hand-maintained. v1 keeps them in `pricing.py` to match the
  existing per-token-rate convention.
