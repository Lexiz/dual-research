---
spec: 0148
title: Consumption-card backend follow-ups + protocol-violation UI surface
label: new-feature
version-bump: MINOR
status: ready
target-version: 1.13.0
created: 2026-05-22
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0148 — Consumption-card backend follow-ups + protocol-violation UI surface

> Ship bucket: **Close the consumption-card B16 backlog (§10.1–§10.6) and surface the spec-0141 protocol-violation signals on turn cards — one merged spec because all seven items live on the same `events/transcript → aggregator → run-detail.jsx render` boundary and share a single test-fixture pass.**
> Depends on:
> - **0146** (Consumption card visual rework — every backend follow-up in this spec was explicitly named in 0146's §3 non-goals as a B16 backend hand-off; the `CcxCard` anatomy this spec fills in is the one 0146 froze).
> - **0145** (Canonical prompt-pieces + per-attachment token tracking — D13/D14 split rows out of the prompt-piece dict shipped in 0145; D16 extends the dotted-key allowlist 0146 added to `_to_camel`).
> - **0143** (Cost / token attribution — `usage.cost`, `usage.tokenCost`, `usage.searchCost`, `reasoning_tokens` capture machinery this spec consumes was finalised in 0143).
> - **0141** (Critique aggregation invariants — `ProtocolViolation` and `EmptyTurnDetected` events were emitted and bridged to `transcript.jsonl` by 0141; this spec is the rendering consumer).
> - **0122** (Transcript bridge — the JSONL stream this spec's D03 chip reads from).
> Complexity: **M** — seven scoped changes, no single one large; concentrated in `aggregator.py`, `models.py`, `protocol/prompt_pieces.py`, `server.py`, and a single React component file (`run-detail.jsx`). Zero schema or migration changes (the spec-0145 `turn_prompt_pieces` table is already extended-enough; new fields are additive on the JSON payload only).
> Targeted version bump: **MINOR (1.12.1 → 1.13.0)** — adds five new public payload fields (`usage.wasCloseout`, `usage.outputBreakdown`, `usage.cacheSavingsUsd`, `usage.promptPieces["web_sources"]`, `usage.promptPieces["tool_definitions"]`) plus two new UI surfaces (closeout-request row, protocol-violation chips). No behaviour-contract change; no migration.

---

## 1. Context

Spec 0146 landed the Consumption-card M3 visual rework — anatomy, sub-row grid, totals block, per-attachment surface — but explicitly punted six backend-side gaps (B16 §10.1–§10.6) plus one server-side serialiser edge case (single-segment canonical IDs). The card today renders correctly for what it has, but four of its design-system §14 surfaces stay empty:

- The `closeout.request` row in the unfolded view is suppressed because the aggregator doesn't tell the frontend which turns *were* closeout requests.
- The `Output` row stays single because reasoning / response / tool-call tokens aren't split — even though `reasoning_tokens` is already captured per-call on `TokenUsage` and reaches the wire.
- The totals block's `cache savings · ×N reuse on Xk` line is absent because the aggregator ships `cache_read` token counts but never converts them to a USD savings figure (or ships the per-model rates that would let the frontend do it).
- The per-piece dict aggregates web-source token cost and tool-definition token cost into the system-prompt total, so the audit-surface rows the user wants — *how much did the web search snippets cost in input tokens?* / *how much did the tool definitions add?* — can't be drawn.

Spec 0141 separately landed two new events — `ProtocolViolation` and `EmptyTurnDetected` — that ride the spec-0122 transcript bridge and persist to `transcript.jsonl`. They are emitted by [orchestrator/deep_research.py:390](src/dual_research/orchestrator/deep_research.py) and `:566` and accumulate signal across runs, but no UI surface renders them today. A run can ship a `ProtocolViolation` without the operator ever knowing unless they grep the transcript by hand.

Spec 0145 surfaced (and 0146 partially fixed) a pre-existing FastAPI `_to_camel` bug: the recursive snake_case → camelCase serialiser rewrites every dict key that doesn't contain a dot. 0146 added a dotted-key guard, which handles the long tail of canonical artifact IDs like `user_prompt.message`, but the three **single-segment** canonical IDs — `user_prompt`, `current_draft`, `all_p2_turns` — still get camelCased on the wire. The frontend works around it via `normalisePiecesRaw` ([run-detail.jsx:2230](src/dual_research/ui/static/run-detail.jsx)), which adds snake_case aliases after fetch. The workaround is functional but inverts the spec-0145 design intent (canonical IDs are the contract — JS reads them verbatim, server doesn't mangle them).

All seven gaps land in one spec because they touch the same five files (aggregator, models, protocol/prompt_pieces, server, run-detail.jsx), share a single anchor-run replay test, and either all ship together as the *complete* B16 §10 close-out or land piecemeal across three minor versions leaving the card in a visibly intermediate state at each step.

---

## 2. Goals

1. **`was_closeout: bool` on every `TurnTokenUsage` payload.** Derived in the aggregator from `prompt_pieces["closeout.request"]` being non-zero — i.e. this turn received closeout-request text in its system prompt (the `pieces_for_*` emitters already include `closeout.request` whenever the closeout text is in the bundle; see [prompt_pieces.py:122](src/dual_research/protocol/prompt_pieces.py) for the preflight branch, mirrored in plan-negotiation and review emitters). The original spec authors' "from `RoundResult.closeout_event`" path is not viable because the aggregator is event-stream-based (`TurnEnded`) and does NOT see `RoundResult` — but `closeout.request` in the prompt-pieces dict carries the same signal in an already-bridged form. When true, CcxCard renders the `closeout.request` row in the unfolded view with the canonical-ID label resolved via `display_name()` and the token count drawn from `prompt_pieces["closeout.request"]`.

2. **`outputBreakdown` on every `TurnTokenUsage` payload.** Three sub-fields, all integers:
   - `reasoning` — sourced from `TokenUsage.reasoning_tokens` ([agents/base.py:218](src/dual_research/agents/base.py)), populated today for OpenAI extended-thinking models via `output_tokens_details.reasoning_tokens` ([openai_agent.py:144–164](src/dual_research/agents/openai_agent.py)) and threaded through `TurnEnded.reasoning_tokens` ([events/types.py:161](src/dual_research/events/types.py)) at [_call.py:198](src/dual_research/orchestrator/_call.py). The aggregator does NOT currently extract this onto `TurnTokenUsage` — this spec adds the 1-line extraction. For Anthropic, this spec adds defensive capture of `usage.thinking_tokens` (extended-thinking is not currently enabled on the agent config — the field stays `0` until it is).
   - `tool_calls` — **always `0` in v1.13.0.** This codebase's only "tool" is the providers' built-in `web_search` (Anthropic `web_search_20250305`, OpenAI Responses-API `web_search` — see [openai_agent.py:26](src/dual_research/agents/openai_agent.py) and [anthropic_agent.py:33](src/dual_research/agents/anthropic_agent.py)). Web-search invocations are counted via `searches` and billed via `search_cost`, not as model output tokens. There are no general-purpose tool calls in any current phase, so the JSON-`tool_calls`-array tokenisation spec authors envisioned has no source data. Field is preserved in the breakdown shape for forward compatibility with future tool-using phases. (If the next spec adds a phase with assistant tool_calls, the capture site is already plumbed via `extras` on `AgentResult`.)
   - `response` — derived: `output_tokens - reasoning - tool_calls`. Never negative; clamped at `0` with a single-line warning logged if the arithmetic underflows (defensive against provider-side reporting inconsistencies).
   When `reasoning + tool_calls == 0`, `CcxCard` continues to render a single `Output` row (the current behaviour) to avoid empty-sub-row clutter on plain non-reasoning turns.

3. **`usage.cacheSavingsUsd` on every `TurnTokenUsage` payload, plus the totals-block line.** Computed server-side at aggregator-time using existing per-model `cache_read_per_mtok` rates from [agents/pricing.py:56–93](src/dual_research/agents/pricing.py):
   ```
   cache_savings_usd = cache_read_tokens × (input_per_mtok - cache_read_per_mtok) / 1e6
   ```
   The new field is per-turn; the totals block in CcxCard sums across turns for the agent and renders `cache savings · ×N reuse on Xkt` per design-system §14.

4. **Web-sources tokens split from the prompt-piece dict.** New canonical ID `system.web_sources` registered in [contract/artifacts.py](src/dual_research/contract/artifacts.py). **Architectural note on emission site:** the spec authors originally placed emission in `pieces_for_*`, but those functions don't see web-search content (they run *before* the agent call; search results come back *inside* the response). The data-flow-honest emission site is the agent layer — each agent already counts `searches` and stashes it in `AgentResult.extras`; this spec extends that with `web_sources_text` (concatenated text of search-result snippets the provider returned this turn). `_call.py` reads `extras["web_sources_text"]` after the agent call and augments the per-turn `prompt_pieces` dict with `system.web_sources = estimate_tokens(web_sources_text)` *before* emitting `TurnEnded`. The CcxCard unfolded view then renders a discrete `Web sources` row via the existing data-driven `groupPiecesForPhase` machinery; zero search-results → key absent → no row (current behaviour preserved).

5. **Tool-definitions tokens split from the system prompt.** Same emission-site reasoning as §2.4: the tools array (`[{"type":"web_search_20250305","name":"web_search"}]` for Anthropic, `[{"type":"web_search","search_context_size":"high"}]` for OpenAI) is constructed at the agent layer, not the protocol layer. New canonical ID `system.tool_definitions`. Each agent stashes `tool_definitions_text` (the JSON of the tools array as shipped to the provider) in `AgentResult.extras` when `web_search_enabled()` is true; `_call.py` reads it after the call and augments `prompt_pieces["system.tool_definitions"] = estimate_tokens(tool_definitions_text)`. CcxCard renders a `Tool definitions` row via the same data-driven path. When web_search is disabled (or some future phase ships no tools) the key is absent and no row renders.

6. **`_to_camel` server-side fix for single-segment canonical IDs.** Extend the dotted-key guard added by 0146 to also pass through keys present in a `CANONICAL_SINGLE_SEGMENT_IDS` frozenset, derived at import time from the `ArtifactDef` registry by filtering for `id` values without a dot. Today the set is `{"user_prompt", "current_draft", "all_p2_turns"}`; future single-segment additions to the registry are picked up automatically. The frontend `normalisePiecesRaw` snake_case-alias workaround ([run-detail.jsx:2230–2241](src/dual_research/ui/static/run-detail.jsx)) is **retired in the same PR** so the contract direction matches spec 0145 (canonical IDs are the wire shape).

7. **Warning chips for `ProtocolViolation` / `EmptyTurnDetected` on turn cards.** A new `<ViolationChip kind="protocol-violation" | "empty-turn" details={…} />` component reads from the transcript bridge for the in-flight run, joins by `(phase, round, agent)`, and renders a small Material-tone chip on the affected turn card. Click → expands an inline detail block (the event's `reason` / `payload` fields). No new persistence; the chip is a pure render over the existing `transcript.jsonl` stream that the aggregator's `_read_transcript` ([ui/aggregator.py:88](src/dual_research/ui/aggregator.py)) already loads.

---

## 3. Non-goals

- **No new persistence schema.** The seven items all ride existing payload shapes (additive fields on `TurnTokenUsage`; events already persisted to `transcript.jsonl`). No new tables, no migrations, no changes to the spec-0145 `turn_prompt_pieces` table.
- **No backfill of historical runs.** `was_closeout`, `outputBreakdown`, `cacheSavingsUsd`, `system.web_sources` / `system.tool_definitions` rows are forward-only. Pre-0148 runs render with the new fields absent → CcxCard falls through to current behaviour (single Output row, no closeout row, no cache-savings line in totals, web-source/tool-definition cost folded into `system.task.<phase>`). Same policy as spec 0145's `turn_prompt_pieces` (forward-only by design).
- **No retry-on-empty-turn / prompt-tightening (D04 deferred).** The D03 chip surfaces the `EmptyTurnDetected` signal so it becomes visible across fresh runs; D04 (using that signal to actually retry or tighten the prompt) is queued for a follow-up spec after ≥1 production run produces an `EmptyTurnDetected` event we can design against. The audit lumped D04 in with D03; this spec drops D04 because it's a behaviour change on a different surface (protocol/prompts.py + orchestrator turn loop), not the aggregator → render boundary.
- **No Anthropic cache-engagement fix (D02 separate spec).** The cache-savings line will read `$0.00` for Anthropic turns until D02 lands the engagement fix and `cache_read_tokens` becomes non-zero. This is correct rendering of a real zero — no shimming. The instrumentation hook (`DUAL_RESEARCH_DEBUG_USAGE=1`) is shipped and untouched.
- **No legacy-shim sunset (D15 separate spec, deadline 2026-08-19).** The frontend `normalisePiecesRaw` is retired in this PR (the workaround for D16), but `LEGACY_KEY_TO_CANONICAL` and the legacy `user_prompt` `ArtifactDef` (in their pre-0145 sense) stay until D15 lands.
- **No diagram regeneration (D21 separate).** The new canonical IDs (`system.web_sources`, `system.tool_definitions`) need to land in `deep-research-pipeline.{light,dark}.svg` eventually, but the diagram regen is a D21 deliverable.
- **No Compare-tab visual changes.** Same `CcxCard` flows through to compare via CSS inheritance.
- **No Jest harness / visual regression suite.** Out of scope per the spec-0144 carve-out.
- **No `PRICING_VERSION` bump.** Cache-savings is computed from existing rates with no version-sensitive arithmetic; the spec-0143 pin pattern only triggers on rate changes.
- **No tool-call cost-by-name attribution.** `outputBreakdown.tool_calls` is a single integer (sum of tokens in the tool_calls JSON). Per-tool-name breakdown is not in scope; if a future spec wants it, the same `tool_calls` array can be tokenised per-entry.

---

## 4. Current-state audit

### 4.1 — Aggregator: `TurnTokenUsage` construction

| File | Lines | Role |
|---|---|---|
| `src/dual_research/ui/models.py` | 551–620 | `class TurnTokenUsage` — dataclass with the fields that flow to the wire. Fields to add: `was_closeout: bool = False`, `output_breakdown: dict[str, int] = field(default_factory=dict)`, `cache_savings_usd: float = 0.0`. |
| `src/dual_research/ui/aggregator.py` | 420–434 | `out_tokens = int(event.get("output_tokens", 0))` — output-token extraction site. Spec adds `reasoning_tokens` / `tool_call_tokens` extraction siblings, then `output_breakdown` assembly. |
| `src/dual_research/ui/aggregator.py` | 481–484 | Prompt-pieces dict extraction from `TurnEnded` event. Spec adds web-sources / tool-definitions key handling. |
| `src/dual_research/ui/aggregator.py` | 520–534 | `run.phase_token_usage[key] = TurnTokenUsage(...)` payload construction — the assembly site where the three new fields are populated. |
| `src/dual_research/ui/aggregator.py` | 88, 982 | `_read_transcript` — loads `transcript.jsonl`; the source D03 reads `ProtocolViolation` / `EmptyTurnDetected` events from. No change here; the events are already in the stream. |

### 4.2 — Events: `ProtocolViolation` / `EmptyTurnDetected`

| File | Lines | Role |
|---|---|---|
| `src/dual_research/events/types.py` | 499–523 | `class ProtocolViolation(Event)` — payload shape (`reason`, `phase`, `round`, `agent`, …). No change. |
| `src/dual_research/events/types.py` | 527–550 | `class EmptyTurnDetected(Event)` — payload shape. No change. |
| `src/dual_research/orchestrator/deep_research.py` | 390 | `violations.append(ProtocolViolation(...))` — emission site. No change. |
| `src/dual_research/orchestrator/deep_research.py` | 566 | `empty_turn_events.append(EmptyTurnDetected(...))` — emission site. No change. |

### 4.3 — Closeout detection (for D10 `was_closeout`)

**Architectural correction vs. original spec framing:** the aggregator is event-based (`TurnEnded`); it does NOT see `RoundResult` / `PhaseResult`. The original "from `RoundResult.closeout_event`" path is not viable. The signal already on the wire is `prompt_pieces["closeout.request"]` — `pieces_for_*` emits this key whenever the closeout-request text is in the prompt bundle.

| File | Lines | Role |
|---|---|---|
| `src/dual_research/protocol/prompt_pieces.py` | 122, 163, 222 | `pieces_for_preflight` / `pieces_for_plan_negotiation` / `pieces_for_review` already emit `out["closeout.request"] = estimate_tokens(closeout_request)` when their `closeout_request` kwarg is set. No change. |
| `src/dual_research/ui/aggregator.py` | ~538 (`TurnTokenUsage` ctor) | Derive `was_closeout = prompt_pieces.get("closeout.request", 0) > 0` from the already-extracted dict and pass to ctor. |

### 4.4 — Token capture (for D11 `outputBreakdown`)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/agents/base.py` | 218 | `reasoning_tokens: int = 0` already on `TokenUsage`. |
| `src/dual_research/agents/openai_agent.py` | 144–164 | OpenAI reasoning extraction → `TokenUsage.reasoning_tokens`. Already plumbed end-to-end through `TurnEnded.reasoning_tokens` at [_call.py:198](src/dual_research/orchestrator/_call.py); the aggregator just needs to extract onto `TurnTokenUsage.output_breakdown`. |
| `src/dual_research/agents/anthropic_agent.py` | 138–145 | Anthropic `TokenUsage` construction. Spec adds defensive `getattr(u, "thinking_tokens", 0) or 0` capture; flows through the existing plumbing. |
| Assistant-message `tool_calls` | n/a in v1.13.0 | This codebase has no general-purpose assistant tool calls. `outputBreakdown.tool_calls` is hard-coded to `0` (see §2.2). |

### 4.5 — Pricing (for D12 `cacheSavingsUsd`)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/agents/pricing.py` | 8–15 | Cache multiplier constants (`CACHE_READ_MULTIPLIER`, `CACHE_WRITE_MULTIPLIER`). |
| `src/dual_research/agents/pricing.py` | 56–93 | `PRICING` dict with `input_per_mtok` + `cache_read_per_mtok` per model. The data D12 multiplies against. |
| `src/dual_research/agents/pricing.py` | 123–129 | `compute_token_cost()` — existing per-call cost computation. New `compute_cache_savings_usd()` sibling helper goes alongside. |

### 4.6 — Web-sources + tool-definitions emission (for D13 / D14)

**Architectural correction vs. original spec framing:** the spec authors placed emission in `pieces_for_*`, but that function family runs *before* the agent call and doesn't see web-search content (results come back inside the provider's response) or know the per-agent tools array (constructed at agent layer). The data-flow-honest emission site is the agent layer + post-call augmentation in `_call.py`.

| File | Lines | Role |
|---|---|---|
| `src/dual_research/agents/anthropic_agent.py` | 33 (tool-def constant), 138–145 (TokenUsage), 228+ (`_count_web_searches`) | Add `_concat_web_search_results(message) -> str` sibling and `json.dumps(tools, sort_keys=True)` capture into `extras["web_sources_text"]` + `extras["tool_definitions_text"]`. |
| `src/dual_research/agents/openai_agent.py` | 26 (tool-def constant), 117 (`web_search_call` walker for audit) | Same shape — concatenate `action.sources` snippet text into `extras["web_sources_text"]`; serialise tools into `extras["tool_definitions_text"]`. |
| `src/dual_research/orchestrator/_call.py` | 188 (just before `TurnEnded` construction) | After the agent call, augment local `prompt_pieces` dict via `estimate_tokens()` on `extras["web_sources_text"]` and `extras["tool_definitions_text"]`. Imports `estimate_tokens` from `dual_research.protocol.prompt_pieces`. |
| `src/dual_research/contract/artifacts.py` | inside `REGISTRY` tuple (after `closeout.request`) | Register `ArtifactDef("system.web_sources", "Web search results", ArtifactKind.SYSTEM, "per-turn", False)` and `ArtifactDef("system.tool_definitions", "Tool definitions", ArtifactKind.SYSTEM, "per-turn", False)`. |
| `src/dual_research/protocol/prompt_pieces.py` | n/a | **No change** — `pieces_for_*` stay clean; agent-layer augmentation is additive. |

### 4.7 — Server camelCase serialiser (for D16)

| File | Lines | Role |
|---|---|---|
| `src/dual_research/ui/server.py` | 1879–1904 | `_to_camel` — recursive snake_case → camelCase rewriter. Dotted-key guard at `:1895` (spec 0146). Spec adds the single-segment canonical-ID allowlist guard alongside. |
| `src/dual_research/contract/artifacts.py` | 142, 150 | `ArtifactDef` dataclass + `REGISTRY` tuple — source the allowlist from. |

### 4.8 — Frontend: `CcxCard` + `normalisePiecesRaw`

| File | Lines | Role |
|---|---|---|
| `src/dual_research/ui/static/run-detail.jsx` | 2230–2241 | `normalisePiecesRaw` — the snake_case-alias workaround; retired once D16 lands the server fix. |
| `src/dual_research/ui/static/run-detail.jsx` | 2314 | `function CcxCard(...)` — header of the component. |
| `src/dual_research/ui/static/run-detail.jsx` | 2340 | `const piecesRaw = normalisePiecesRaw(usage.promptPieces)` — call to retire. |
| `src/dual_research/ui/static/run-detail.jsx` | 2502–2509 | `grouped.rows.map(renderInputRow)` — where new `web_sources` / `tool_definitions` rows surface; `groupPiecesForPhase` already iterates whatever the dict contains, so no per-row change needed *if* `consumptionLabel` resolves the new IDs cleanly. |
| `src/dual_research/ui/static/run-detail.jsx` | 2540–2547 | Web-search mono line — kept for the call-count display; the new `system.web_sources` row is the *input-token cost*, not the per-query fee (which is `searchCost`). Two different surfaces. |

### 4.9 — Frontend: turn-card / timeline-card surface (for D03 chips)

**Locations confirmed during validation:**

| File | Lines | Role |
|---|---|---|
| `src/dual_research/ui/static/run-detail.jsx` | 1088 (`function TlTurnRow`), 1140 (`<div className="tl-card-head__right">` chip cluster) | Mount point for `<ViolationChip>` — sits alongside the category chips inside the right-aligned cluster on every turn card. Join key is `item.phase` × `item.round` × `item.agent` (already on the item). |
| `src/dual_research/ui/models.py` | `Run` dataclass | Currently does NOT carry transcript or violations. This spec adds `violations: list[dict] = field(default_factory=list)` on `Run`. |
| `src/dual_research/ui/aggregator.py` | 88 (`_read_transcript` already loaded) + the materialise site that constructs `Run` | Populate `run.violations` by filtering `_read_transcript` output to `kind in {"protocol_violation", "empty_turn_detected"}`. |
| `src/dual_research/ui/server.py` | 209 (`get_run` returns `_to_camel(to_jsonable(run))`) | No change — the new `violations` field rides through the existing serializer. |

---

## 5. Proposed change

### 5.1 — D16: server-side single-segment canonical-ID allowlist

In [server.py:1879](src/dual_research/ui/server.py), extend the dotted-key guard:

```python
from dual_research.contract.artifacts import REGISTRY as _ARTIFACT_REGISTRY

_CANONICAL_SINGLE_SEGMENT_IDS: frozenset[str] = frozenset(
    artifact.id for artifact in _ARTIFACT_REGISTRY if "." not in artifact.id
)


def _to_camel(obj: Any) -> Any:
    """… (existing docstring; add a line about the single-segment guard) …"""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str):
                if "." in k or k in _CANONICAL_SINGLE_SEGMENT_IDS:
                    out[k] = _to_camel(v)
                else:
                    out[_snake_to_camel(k)] = _to_camel(v)
            else:
                out[str(k)] = _to_camel(v)
        return out
    ...
```

Same PR, frontend retirement in [run-detail.jsx:2230–2241](src/dual_research/ui/static/run-detail.jsx) — delete `normalisePiecesRaw` and replace `normalisePiecesRaw(usage.promptPieces)` with `usage.promptPieces` directly at the lone call site (`:2340`). A grep confirms no other caller.

The allowlist is import-time derived so the next time someone registers a single-segment canonical ID (e.g. a hypothetical `final_draft` to mirror `current_draft`), the serialiser picks it up without code change.

### 5.2 — D10: `was_closeout` on `TurnTokenUsage`

Add the field to the dataclass ([models.py:552](src/dual_research/ui/models.py)):

```python
@dataclass
class TurnTokenUsage:
    ...
    # Spec 0148 — closeout-request signal for CcxCard's closeout.request row.
    # True iff prompt_pieces carries a non-zero "closeout.request" entry,
    # meaning this turn received closeout-request text in its system prompt
    # (the pieces_for_* emitters already include this key in the bundle
    # whenever the closeout text is present). Derived in the aggregator;
    # event-only path. Forward-only — pre-0148 transcripts carry the
    # default False because the aggregator stamps it; the closeout row
    # still renders for any historic turn whose prompt_pieces dict
    # contains "closeout.request" (the data was already on the wire).
    was_closeout: bool = False
```

In the aggregator at the `TurnTokenUsage` construction site (line ~538 in current main), derive the flag from the already-extracted `prompt_pieces` dict:

```python
was_closeout = int(prompt_pieces.get("closeout.request", 0)) > 0
```

and pass it as `was_closeout=was_closeout` to the `TurnTokenUsage(...)` ctor call.

In CcxCard ([run-detail.jsx:2502](src/dual_research/ui/static/run-detail.jsx)), the row is data-driven via `grouped.rows`. Add `closeout.request` to the row vocabulary in `groupPiecesForPhase` for the phases that can have a closeout (phases 0, 2, 4 — the negotiation phases). The piece token count is already in `usage.promptPieces["closeout.request"]` for closeout turns; the `usage.wasCloseout` flag is informational (drives row visibility for any visual treatment the row needs beyond presence-in-pieces).

### 5.3 — D11: `outputBreakdown`

Capture sites:
1. **OpenAI reasoning** — already wired end-to-end: `reasoning_tokens` is extracted at [openai_agent.py:144–164](src/dual_research/agents/openai_agent.py), threaded into `TokenUsage` and onto `TurnEnded.reasoning_tokens` at [_call.py:198](src/dual_research/orchestrator/_call.py). The aggregator does NOT currently extract this from the event into `TurnTokenUsage`; this spec adds that 1-line extraction.
2. **Anthropic thinking** — currently unwired. Spec adds defensive capture at [anthropic_agent.py:139](src/dual_research/agents/anthropic_agent.py): `reasoning = getattr(getattr(u, "thinking_tokens", 0), ...)` (exact attribute path confirmed at impl time against the installed SDK version). Will stay 0 in production until extended-thinking is enabled in the agent config; the wire shape is forward-ready.
3. **`tool_calls`** — see §2.2: always `0` in v1.13.0 because this codebase has no general-purpose assistant tool_calls. No capture site; no event-payload addition.

Wire-shape addition on `TurnTokenUsage` ([models.py:552](src/dual_research/ui/models.py)):

```python
# Spec 0148 — output-token breakdown for CcxCard's split Output row.
# Keys: "reasoning", "response", "tool_calls" (all ints). Invariant:
# sum == out (the existing total output_tokens field). Clamp at 0 on
# arithmetic underflow with a warn-log; never negative.
# v1.13.0 — tool_calls is always 0 for this codebase (only tool is
# providers' built-in web_search, counted via `searches`/`search_cost`);
# the field exists for forward compatibility with future tool-using phases.
output_breakdown: dict[str, int] = field(default_factory=dict)
```

Aggregator — at the `TurnTokenUsage` construction site (line ~538), extract reasoning from the event payload and assemble:

```python
reasoning = int(event.get("reasoning_tokens", 0))
tool_calls = 0  # spec 0148 — see §2.2
response = max(0, out_tokens - reasoning - tool_calls)
if reasoning + tool_calls > out_tokens:
    logger.warning("[spec-0148] outputBreakdown underflow at %s: out=%d, "
                   "reasoning=%d, tool_calls=%d", key, out_tokens,
                   reasoning, tool_calls)
output_breakdown = {"reasoning": reasoning, "response": response, "tool_calls": tool_calls}
```

CcxCard split: in [run-detail.jsx:2515–2530](src/dual_research/ui/static/run-detail.jsx), when rendering the Output row, branch on `usage.outputBreakdown`:
- If `reasoning + tool_calls == 0` → single `Output` row (existing behaviour).
- Else → three sub-rows under a single Output header: `Reasoning · Nkt · $X.X`, `Response · Nkt · $X.X`, `Tool calls · Nkt · $X.X` (the tool_calls sub-row is skipped when its value is 0, so v1.13.0 renders only Reasoning + Response). The USD values are computed by splitting the existing per-turn output cost proportionally to the token shares.

### 5.4 — D12: `cacheSavingsUsd`

New helper in [agents/pricing.py:130](src/dual_research/agents/pricing.py) (alongside `compute_token_cost`):

```python
def compute_cache_savings_usd(model_id: str, cache_read_tokens: int) -> float:
    """Returns the USD savings from cache-read tokens vs. fresh input.

    Spec 0148. `cache_savings_usd = cache_read × (input_per_mtok - cache_read_per_mtok) / 1e6`.
    Returns 0.0 for unknown models (consistent with `compute_token_cost`'s fallback).
    """
    if not cache_read_tokens:
        return 0.0
    pricing = PRICING.get(model_id)
    if not pricing:
        return 0.0
    rate_delta = pricing["input_per_mtok"] - pricing["cache_read_per_mtok"]
    return cache_read_tokens * rate_delta / 1_000_000
```

`TurnTokenUsage.cache_savings_usd: float = 0.0` field, populated at aggregator-time via the helper.

CcxCard totals block: sum `usage.cacheSavingsUsd` and `usage.cacheRead` across the agent's turns; render the design-system §14 line:

```
cache savings · ×N reuse on Xkt   $0.X
```

where `N = round(cache_read_total / input_billed_total, 1)` (the existing "reuse signal" arithmetic; see [run-detail.jsx:2491–2499](src/dual_research/ui/static/run-detail.jsx)) and the `$` value is the summed `cache_savings_usd`.

### 5.5 — D13: emit `system.web_sources` (from agent layer)

Register the new canonical ID in [contract/artifacts.py](src/dual_research/contract/artifacts.py) inside the `REGISTRY` tuple (single line, `ArtifactKind.SYSTEM`, `"per-turn"` scope):

```python
ArtifactDef("system.web_sources", "Web search results",
            ArtifactKind.SYSTEM, "per-turn", False),
```

In **[anthropic_agent.py](src/dual_research/agents/anthropic_agent.py)**, alongside the existing `_count_web_searches` helper, add `_concat_web_search_results(message) -> str` that walks the final-message content blocks and concatenates the text of every `web_search_tool_result` block (i.e. the pages the provider fetched). Stash the result in `extras["web_sources_text"]` on the `AgentResult` constructed at the end of `run()`.

In **[openai_agent.py](src/dual_research/agents/openai_agent.py)**, alongside the search-audit capture, walk `final_response.output` for `web_search_call` items (already iterated for the audit path at [:117](src/dual_research/agents/openai_agent.py)) and concatenate the `action.sources` snippet content into a string. Stash in `extras["web_sources_text"]`.

In **[_call.py](src/dual_research/orchestrator/_call.py)**, after the agent call and before constructing `end_event = TurnEnded(...)`, augment `prompt_pieces` (the local copy, not the function argument) when `web_sources_text` is non-empty:

```python
from dual_research.protocol.prompt_pieces import estimate_tokens

pieces_dict = dict(prompt_pieces) if prompt_pieces else {}
ws_text = (result.extras or {}).get("web_sources_text") or ""
if ws_text:
    pieces_dict["system.web_sources"] = estimate_tokens(ws_text)
# … then pass pieces_dict to TurnEnded(prompt_pieces=pieces_dict, …)
```

CcxCard: once `groupPiecesForPhase` iterates the augmented dict, `consumptionLabel("system.web_sources")` resolves to `"Web search results"` via the registry, and a row surfaces automatically alongside the existing system/user/prior_turns rows. Token count and proportional cost are computed by the existing per-row arithmetic.

### 5.6 — D14: emit `system.tool_definitions` (from agent layer)

Register the new canonical ID:

```python
ArtifactDef("system.tool_definitions", "Tool definitions",
            ArtifactKind.SYSTEM, "per-turn", False),
```

In **anthropic_agent.py** and **openai_agent.py**, when `web_search_enabled()` is true and the request ships a tools array, JSON-serialise that array (use `json.dumps(tools, sort_keys=True)` for stability) and stash in `extras["tool_definitions_text"]`. The tools-array constants are already defined at module level in each agent ([anthropic_agent.py:33](src/dual_research/agents/anthropic_agent.py), [openai_agent.py:26](src/dual_research/agents/openai_agent.py)).

In `_call.py`, the same augmentation path as §5.5:

```python
td_text = (result.extras or {}).get("tool_definitions_text") or ""
if td_text:
    pieces_dict["system.tool_definitions"] = estimate_tokens(td_text)
```

CcxCard renders the row via the same data-driven machinery. Because the tools array is small (~15–25 tokens), the row will read `system.tool_definitions · ~20t · $0.0` — visually small but discoverable, which is the spec's stated audit intent.

**Invariant note.** Unlike spec authors' original framing, the new `system.web_sources` + `system.tool_definitions` rows do NOT subtract from `system.task.<phase>` — they're additive pieces on the prompt-pieces dict, representing input-token bands the spec-0145 emitter never captured. The provider-reported `input_tokens` count is unchanged; the proportional renormalisation against `input_tokens` in CcxCard absorbs the new entries naturally.

### 5.7 — D03: `ProtocolViolation` / `EmptyTurnDetected` chips

Render path:
1. **Aggregator surfacing.** Confirm at impl time whether `_read_transcript`'s output is on the `/api/runs/<id>` snapshot. If yes, the events are already on `run.transcript` (or equivalent) and the frontend can read them directly. If no, add a one-line addition to the snapshot DTO surfacing `run.violations = [event for event in transcript if event["kind"] in {"protocol_violation", "empty_turn_detected"}]`.
2. **New component** in [run-detail.jsx](src/dual_research/ui/static/run-detail.jsx):

   ```jsx
   function ViolationChip({ kind, details }) {
     const [open, setOpen] = useState(false);
     const label = kind === "protocol-violation" ? "Protocol violation" : "Empty turn";
     return (
       <div className={`violation-chip is-${kind}`}>
         <button type="button" className="violation-chip__head" onClick={() => setOpen(o => !o)}>
           <span className="violation-chip__dot" aria-hidden />
           <span className="violation-chip__label">{label}</span>
           <span className="violation-chip__chev">{open ? "▾" : "▸"}</span>
         </button>
         {open && (
           <pre className="violation-chip__body">{JSON.stringify(details, null, 2)}</pre>
         )}
       </div>
     );
   }
   ```

3. **Mount point**: on each `TimelineCard` (or equivalent turn-card render block — locate at impl time), filter `run.violations` to events with matching `(phase, round, agent)` and render one chip per event.
4. **Styles** in [components.css](src/dual_research/ui/static/components.css): a single `.violation-chip` rule block using existing M3 tokens (`--md-sys-color-error-container` / `--md-sys-color-on-error-container` for `protocol-violation`; `--md-sys-color-tertiary-container` / `--md-sys-color-on-tertiary-container` for the softer `empty-turn` warning). No new colour tokens.

---

## 6. Test plan

- [ ] **Unit (`tests/ui/test_aggregator_spec_0148.py`)**: a fixture transcript with one closeout turn, one reasoning-bearing turn (OpenAI + Anthropic), one tool-call-bearing turn, and one cache-read-bearing turn. Assert the resulting `TurnTokenUsage` payloads carry `was_closeout`, `output_breakdown`, `cache_savings_usd` populated correctly.
- [ ] **Unit (`tests/ui/test_pricing_spec_0148.py`)**: `compute_cache_savings_usd("gpt-5", 88_448)` returns `~0.0995` (assuming current $1.25 / $0.125 per-Mtok rates) — pin to two decimal places, recalibrate if the test goes red at a different `PRICING_VERSION`.
- [ ] **Unit (`tests/ui/test_to_camel_spec_0148.py`)**: `_to_camel({"user_prompt": 1, "current_draft": 2, "all_p2_turns": 3, "phase_summary_0": 4})` returns `{"user_prompt": 1, "current_draft": 2, "all_p2_turns": 3, "phaseSummary0": 4}`. The three single-segment canonical IDs pass through; `phase_summary_0` (not a canonical ID) still camelCases.
- [ ] **Unit (`tests/protocol/test_prompt_pieces_spec_0148.py`)**: a fixture phase-input where the system prompt has both a `<sources>…</sources>` block and a tool-definitions JSON. Assert `pieces_for_<phase>` emits three distinct keys: `system.task.<phase>`, `system.web_sources`, `system.tool_definitions`, with token counts summing to the original aggregate.
- [ ] **Anchor-run replay**: rebuild metrics + push for `20260521-010637-dvs-backend-language-choice`. Assert the new fields populate. Confirm existing assertions (`total_cost_usd = 13.5110`, etc.) hold unchanged — i.e. the changes are visible-but-additive.
- [ ] **Anchor-run replay (D03 chips)**: same run; confirm the transcript carries zero `ProtocolViolation` / `EmptyTurnDetected` events (the run pre-dates spec 0141's deploy or simply didn't trigger them), so the new chip mount-point renders nothing. The fixture for chip *presence* comes from the next D09 fresh-run smoke.
- [ ] **Frontend dotted-key removal**: confirm `grep -n normalisePiecesRaw src/dual_research/ui/static/` returns zero hits after the deletion. CcxCard renders per-piece sub-rows from `usage.promptPieces` directly.
- [ ] **Manual smoke**: a fresh `/dual-research-run` on a drift-prone brief (the long-deferred D09 smoke; cost ~$10). Confirm:
  - Closeout row appears on closeout turns.
  - Output row splits into reasoning / response / tool_calls when applicable.
  - Cache-savings line shows in the totals block with non-zero value (OpenAI side, where cache is engaged).
  - Web-sources and tool-definitions rows appear on phases that use them.
  - Single-segment canonical IDs (`user_prompt`, etc.) arrive at the JS verbatim (DevTools inspection of `/api/runs/<id>`).
  - If the run triggers a `ProtocolViolation` or `EmptyTurnDetected`, the corresponding chip surfaces on the affected turn card.

---

## 7. Risks

- **`outputBreakdown` arithmetic mismatch.** Provider-side `reasoning_tokens` is sometimes reported in a different basis than `output_tokens` (e.g. reasoning excluded from total in one provider, included in another). The clamp-at-zero + warn-log defends the invariant; the first fresh-run smoke will reveal whether either provider reports `reasoning + tool_calls > out_tokens` consistently — if so, fix at the capture site, not the aggregator.
- **`tool_call_tokens` tokeniser drift.** Each agent's tokeniser counts the JSON-serialised `tool_calls` array using the same tokeniser the provider uses for billing. If our tokeniser drifts from the provider's, the breakdown's `tool_calls` share is wrong (in either direction). Mitigation: the breakdown sums to `out_tokens` regardless (because `response` is derived as the remainder), so the *visual total* is always correct; only the share between `response` and `tool_calls` shifts. Acceptable for a v1 — invoice-grade tool-call attribution is a follow-up.
- **Web-sources / tool-definitions emitter coverage.** If a `pieces_for_<phase>` emitter is missed in §5.5 or §5.6, that phase's CcxCard view silently keeps showing the aggregate `system.task.<phase>` value without the split — a regression hidden by an absence. Mitigation: the unit test enumerates all five emitters; a missing branch fails the suite.
- **`_to_camel` retirement breaks pre-0148 frontends.** Deleting `normalisePiecesRaw` means a pre-0148 *frontend* (browser cache + older bundle) talking to a post-0148 *backend* still works (server emits snake_case for the three IDs; the old frontend was reading snake_case via the alias map anyway). Reverse — post-0148 frontend hitting pre-0148 backend — would fail to find `user_prompt` because the backend still sends `userPrompt`. The frontend is bundled with the server; deployment is atomic. No real exposure unless a user pins to a stale frontend.
- **`ViolationChip` rendering on backfilled vs. live transcripts.** Pre-0141 runs have no events of these kinds, so the chip surface is silently empty for old runs — correct. The chip surface is gated on `run.violations` length > 0, so no empty-state UI churn.
- **D03 join key.** `(phase, round, agent)` is the join axis for chip-to-card. If the event payload uses a different field name (e.g. `agent_id` vs `agent`), the join fails silently and chips don't render. Mitigation: an impl-time assertion that the event payload fields match the card key set; unit test reads a fixture event and asserts the join.
- **Anchor-run forward-compatibility.** The anchor run was pushed under spec-0145 (with the legacy aggregate) and re-pushed under spec-0146 (with the camelCase guard for dotted keys). Re-pushing under 0148 changes the wire-shape of single-segment IDs and the prompt-pieces dict (web_sources / tool_definitions split out). Backwards consumers (none today, since the only consumer is the bundled frontend) are unaffected, but the push CLI's "is this the latest schema" guard, if any, should accept the new keys gracefully — confirm there's no schema-validation strictness that rejects unknown piece IDs.

---

## 8. Open questions

All three resolved during pre-implementation validation (2026-05-22):

- **Anthropic extended-thinking `thinking_tokens` field path** — **Resolved:** the Anthropic SDK exposes `usage.thinking_tokens` as a flat attribute when extended-thinking is enabled; absent → default `0`. Capture via `getattr(u, "thinking_tokens", 0) or 0` defensively at [anthropic_agent.py:139](src/dual_research/agents/anthropic_agent.py) alongside the existing `cache_read_input_tokens` extraction. Extended-thinking is NOT currently enabled in this codebase's agent config, so the captured value will be `0` for every Anthropic turn on a fresh run — this is correct; the field is forward-ready.
- **`tool_call_tokens` placement** — **Resolved as: not applicable in v1.13.0.** This codebase has no general-purpose assistant tool_calls (the only "tool" both providers expose is built-in web_search, already counted via `searches`/`search_cost`). `outputBreakdown.tool_calls` is hard-coded to `0` for forward compatibility with future tool-using phases. No `TokenUsage` field added; no event-payload field added. The §2.2 + §5.3 amendments lock this in.
- **Closeout row token-count source** — **Confirmed:** `pieces_for_preflight` ([prompt_pieces.py:122](src/dual_research/protocol/prompt_pieces.py)), `pieces_for_plan_negotiation` ([:163](src/dual_research/protocol/prompt_pieces.py)), and `pieces_for_review` ([:222](src/dual_research/protocol/prompt_pieces.py)) all emit `out["closeout.request"] = estimate_tokens(closeout_request)` when their `closeout_request` kwarg is set. D10's `was_closeout` flag is therefore safely derivable as `prompt_pieces.get("closeout.request", 0) > 0` in the aggregator — no protocol-layer changes needed for D10.

**Newly-recorded resolution from validation pass:**

- **D13 / D14 emission site** — **Resolved as: agent-layer post-call augmentation, not `pieces_for_*`.** The original spec framing ("in `pieces_for_*`, emit a `system.web_sources` row") doesn't fit the architecture: search-result content comes back inside the provider's response (not the system prompt), and tool definitions are constructed at the agent layer (not visible to the protocol layer). The resolution is the §5.5 + §5.6 amendments: each agent stashes `web_sources_text` and `tool_definitions_text` in `AgentResult.extras`; `_call.py` augments the per-turn `prompt_pieces` dict before emitting `TurnEnded`. Data flow stays honest, no architectural inversion, and the canonical-ID contract is preserved at the wire boundary.
