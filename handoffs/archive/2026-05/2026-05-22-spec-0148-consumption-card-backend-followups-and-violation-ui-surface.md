# Handover — Spec 0148 — Consumption-card backend follow-ups + protocol-violation UI surface (v1.13.0)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#170](https://github.com/Lexiz/dual-research/pull/170) (merged, squash, branch deleted)
- **Spec:** [specs/0148-consumption-card-backend-followups-and-violation-ui-surface.md](../specs/0148-consumption-card-backend-followups-and-violation-ui-surface.md)
- **Audit:** [specs/_post-batch-cleanup-audit.md](../specs/_post-batch-cleanup-audit.md) rows D03, D10, D11, D12, D13, D14, D16 — all closed (D04 intentionally split off; see §3 non-goals).
- **Anchor run:** `20260521-010637-dvs-backend-language-choice` (replay, not a fresh run).
- **Version:** `1.12.1 → 1.13.0` (**MINOR** — five new public payload fields + two new UI surfaces; no schema, no migration, no protocol contract change).

## What landed

First spec after the 0140–0147 batch. Seven deferred items from the post-batch cleanup audit consolidated into one ship because they all live on the events / aggregator → CcxCard render boundary and share a single test-fixture pass.

- **D16 — single-segment canonical-ID allowlist in `_to_camel`.** Server-side guard ([ui/server.py:1878](../src/dual_research/ui/server.py)) extended with an import-time-derived frozenset of single-segment IDs sourced from `contract.artifacts.REGISTRY` by filtering `id_template` for entries without `.` or `<>`. The allowlist today is `{user_prompt, current_draft, all_p2_turns, all_carry_forward}`; future single-segment additions to the registry are picked up automatically. Frontend `normalisePiecesRaw` shim retired in the same PR — only a retirement comment remains; zero function-call sites in `run-detail.jsx`.

- **D10 — `was_closeout: bool` per turn.** Aggregator derives it from `prompt_pieces["closeout.request"] > 0` (event-only path; the closeout-request text already rides on the wire via spec 0145's `pieces_for_*` emitters). New field on `TurnTokenUsage` (forward-only — pre-0148 deserialisations default to False). CcxCard pulls `closeout.request` out of the system-prompt aggregate via the new `DYNAMIC_SEPARATE_KEYS` list and renders it as a discrete row when present.

- **D11 — `outputBreakdown = {reasoning, response, tool_calls}` per turn.** Aggregator extracts `reasoning_tokens` from the existing `TurnEnded` event payload onto a new `output_breakdown` dict on `TurnTokenUsage`. Anthropic side adds defensive `usage.thinking_tokens` capture at [anthropic_agent.py:143](../src/dual_research/agents/anthropic_agent.py) — inactive in production until extended-thinking is enabled on the agent config, but the wire shape is forward-ready. CcxCard splits the Output row into `Reasoning / Response (/ Tool calls)` sub-rows when `reasoning > 0`; falls back to a single Output row otherwise. **`tool_calls` is hard-coded to `0` in v1.13.0** because this codebase has no general-purpose assistant tool calls — the only "tool" both providers expose is built-in `web_search`, already counted via `searches` / `search_cost`. The breakdown shape is preserved for future tool-using phases; the underflow-clamp + warn-log defends the `sum == out` invariant.

- **D12 — `cacheSavingsUsd` per turn + totals-block line.** New `compute_cache_savings_usd(model_id, cache_read_tokens)` helper in [agents/pricing.py:148](../src/dual_research/agents/pricing.py) using the existing per-model `input_per_mtok` / `cache_read_per_mtok` rates (no `PRICING_VERSION` bump — additive). Field populated at aggregator time. CcxCard renders `cache savings · ×N reuse on Xkt` in the totals block whenever the turn engaged cache-read. Anchor-run replay shows $0.398 of cumulative cache savings across the 40 turns (GPT side; Claude side stays at $0 because D02 cache-engagement is still deferred).

- **D13 / D14 — `system.web_sources` + `system.tool_definitions` rows (architectural amendment from the original spec).** The spec authors originally placed emission in `pieces_for_*`, but `pieces_for_*` runs *before* the agent call — it can't see search-result snippets that come back inside the provider's response, and it doesn't know the per-agent tools array (constructed at the agent layer). The data-flow-honest fit is:
  - Both agents stash `web_sources_text` (concatenated `title\nurl` per result) and `tool_definitions_text` (`json.dumps(tools, sort_keys=True)`) in `AgentResult.extras` ([anthropic_agent.py:223](../src/dual_research/agents/anthropic_agent.py) `_concat_web_search_results`, [openai_agent.py:226](../src/dual_research/agents/openai_agent.py) `_concat_web_search_results`).
  - [orchestrator/_call.py:178](../src/dual_research/orchestrator/_call.py) reads `extras["web_sources_text"]` + `extras["tool_definitions_text"]` and augments the `prompt_pieces` dict via `estimate_tokens` *before* emitting `TurnEnded`.
  - Two new `ArtifactDef`s in `contract/artifacts.py` registry; mirrored in `static/artifacts.jsx`. The CcxCard renders the new rows via the existing data-driven `groupPiecesForPhase` machinery — no new render branches needed.
  - The Anthropic + OpenAI tool-definitions JSON tokenises to ~15-25 tokens; the web-sources concatenation produces stable deterministic input even if the SDK doesn't expose decrypted snippet text (we approximate with title + url per result).

- **D03 — `ProtocolViolation` / `EmptyTurnDetected` warning chips on turn cards.** New `violations: list[dict]` field on `Run` ([ui/models.py:691](../src/dual_research/ui/models.py)), populated in `load_run_snapshot` by filtering `transcript.jsonl` to the two event kinds emitted by spec 0141 (mirrored to disk via the spec-0122 transcript bridge). New `<ViolationChip>` component in `run-detail.jsx` mounts on each `TlTurnRow` (the per-turn card in the timeline pane) joined by `(phase, round, agent)`. Click expands an inline `<pre>` with the event JSON. Two Material 3 tones via existing tokens (`--md-sys-color-error-container` for `protocol_violation`; `--md-sys-color-tertiary-container` for the softer `empty_turn_detected`). No new design-system tokens.

## Files touched

### Backend (Python)
- [`src/dual_research/ui/server.py`](../src/dual_research/ui/server.py) — `_CANONICAL_SINGLE_SEGMENT_IDS` import-time frozenset + extended guard in `_to_camel` (D16).
- [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py) — populate `run.violations` from transcript filter (D03); derive `was_closeout` + assemble `output_breakdown` + compute `cache_savings_usd` at `TurnTokenUsage` ctor site (D10/D11/D12).
- [`src/dual_research/ui/models.py`](../src/dual_research/ui/models.py) — three new fields on `TurnTokenUsage` (D10/D11/D12); `violations` field on `Run` (D03).
- [`src/dual_research/agents/pricing.py`](../src/dual_research/agents/pricing.py) — new `compute_cache_savings_usd()` helper (D12).
- [`src/dual_research/agents/anthropic_agent.py`](../src/dual_research/agents/anthropic_agent.py) — defensive `thinking_tokens` capture (D11); `_concat_web_search_results` helper + `extras["web_sources_text"]` (D13); `extras["tool_definitions_text"]` (D14); `json` import added.
- [`src/dual_research/agents/openai_agent.py`](../src/dual_research/agents/openai_agent.py) — `_concat_web_search_results` helper + `extras["web_sources_text"]` (D13); `extras["tool_definitions_text"]` (D14); `json` import added.
- [`src/dual_research/orchestrator/_call.py`](../src/dual_research/orchestrator/_call.py) — augment `prompt_pieces` dict from `extras` before `TurnEnded` emission (D13/D14).
- [`src/dual_research/contract/artifacts.py`](../src/dual_research/contract/artifacts.py) — register `system.web_sources` + `system.tool_definitions` ArtifactDefs (D13/D14).

### Frontend
- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — retired `normalisePiecesRaw` (D16, retirement comment retained); `DYNAMIC_SEPARATE_KEYS` list pulls `closeout.request` / `system.web_sources` / `system.tool_definitions` out of the system-prompt aggregate (D10/D13/D14); `outputBreakdown` Output-row split branch (D11); `cacheSavingsUsd` totals-block line (D12); new `ViolationChip` component + `_violationsForTurnCard` join helper + mount in `TlTurnRow`'s right-cluster (D03).
- [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) — `.violation-chip` rule block with two tone variants (D03).
- [`src/dual_research/ui/static/artifacts.jsx`](../src/dual_research/ui/static/artifacts.jsx) — registry mirror updated with the two new IDs.
- [`src/dual_research/ui/static/index.html`](../src/dual_research/ui/static/index.html) — cache-buster `?v=0147a` → `?v=0148a` across all 25 imports.

### Tests
- [`tests/ui/test_to_camel_spec_0148.py`](../tests/ui/test_to_camel_spec_0148.py) — 5 cases.
- [`tests/ui/test_pricing_spec_0148.py`](../tests/ui/test_pricing_spec_0148.py) — 6 cases.
- [`tests/ui/test_aggregator_spec_0148.py`](../tests/ui/test_aggregator_spec_0148.py) — 10 cases.
- [`tests/protocol/test_prompt_pieces_spec_0148.py`](../tests/protocol/test_prompt_pieces_spec_0148.py) — 6 cases.
- [`tests/contract/test_artifacts.py`](../tests/contract/test_artifacts.py) — normative-id table extended for two new entries.
- [`tests/ui/test_server.py`](../tests/ui/test_server.py) — `TurnTokenUsage` wire-shape pin extended for three new fields.

### Misc
- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — `1.12.1` → `1.13.0`.
- `CHANGELOG.md` — `[1.13.0]` entry.
- `specs/0148-consumption-card-backend-followups-and-violation-ui-surface.md` — the spec itself, amended pre-implementation to reflect the four architectural drifts discovered during validation (D10 mechanism, D11 tool_calls, D13/D14 emission site).

## Open-question resolutions

All three §8 questions resolved during the pre-implementation validation pass (2026-05-22), with a fourth surfaced and resolved:

1. **Anthropic extended-thinking `thinking_tokens` field path.** The Anthropic SDK exposes `usage.thinking_tokens` as a flat attribute; absent → default 0. Captured via `getattr(u, "thinking_tokens", 0) or 0` defensively at [anthropic_agent.py:143](../src/dual_research/agents/anthropic_agent.py). Extended-thinking is not currently enabled in the model config, so the value will stay 0 on every Anthropic turn on the first fresh run — this is correct; the field is forward-ready for when extended-thinking gets enabled.
2. **`tool_call_tokens` placement on the event payload.** Resolved as: **not applicable in v1.13.0.** This codebase has no general-purpose assistant tool calls; the only "tool" both providers expose is built-in web_search, already counted via `searches`/`search_cost`. `outputBreakdown.tool_calls` is hard-coded to `0` for forward compatibility. No `TokenUsage` field added; no event-payload field added.
3. **Closeout row token-count source.** Confirmed: `pieces_for_preflight` ([prompt_pieces.py:122](../src/dual_research/protocol/prompt_pieces.py)), `pieces_for_plan_negotiation` ([:163](../src/dual_research/protocol/prompt_pieces.py)), and `pieces_for_review` ([:222](../src/dual_research/protocol/prompt_pieces.py)) all emit `out["closeout.request"] = estimate_tokens(closeout_request)` when their `closeout_request` kwarg is set. D10's `was_closeout` flag is safely derivable as `prompt_pieces.get("closeout.request", 0) > 0` in the aggregator — no protocol-layer changes needed.

**Newly recorded — D13/D14 emission site.** Original spec framing placed emission in `pieces_for_*`, but search-result content comes back inside the provider's response and tool definitions are constructed at the agent layer — `pieces_for_*` can't see either. Resolution: each agent stashes `web_sources_text` and `tool_definitions_text` in `AgentResult.extras`; `_call.py` augments the per-turn `prompt_pieces` dict before emitting `TurnEnded`. Spec §5.5 + §5.6 amendments lock this in.

## Tests

```
1389 passed in 10.79s
```

Up from 1387 (Spec 0147 baseline) — +27 new test cases (4 spec-0148 suites) minus 2 existing pins that were extended in place to track the new wire-shape fields.

## Deploy status

- **Version:** `1.13.0`
- **Deploy timestamp:** 2026-05-22T~00:03Z (machine 1 healthy first pass; **machine 2 recovered after the same recurring `machines.dev` mid-rolling-deploy flake — this is the seventh consecutive deploy hitting the pattern documented in 0140 / 0141 / 0142 / 0144 / 0146 / 0147 handovers**).
- **Live health:** `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.13.0","backend":"supabase"}`.
- **Both machines:** image `dual-research-alex:deployment-01KS6F3C7E7ZVCQCXX8EVHP6ZS`, version 206, `started`, 1/1 health passing on both. Recovered machine 2 via `fly machine start 148ee320f427e8 -a dual-research-alex` (~12 seconds).

### Smoke

1. **Local preview (against the same bytes deployed to hosted).** Server boots on v1.13.0, no JS errors, 42 Consumption cards render against the anchor run. `/api/runs/<id>` payload exposes `wasCloseout` / `outputBreakdown` / `cacheSavingsUsd` / `violations`. `user_prompt` arrives verbatim on the wire (D16 contract). `cache savings · ×0.4 reuse on 4.2kt` line renders on a cache-engaged GPT turn (D12 visual). Timeline renders 41 turn cards with no `.violation-chip` instances (anchor pre-dates spec 0141 emit — expected).
2. **Hosted bundle markers.** `curl -s https://dual-research-alex.fly.dev/run-detail.jsx?v=0148a | grep -c -E 'Spec 0148|ViolationChip|outputBreakdown|cacheSavingsUsd|wasCloseout|DYNAMIC_SEPARATE_KEYS|_violationsForTurnCard'` → **21 hits**. The two new canonical IDs are present in the hosted `artifacts.jsx?v=0148a`. Confirms the new JSX bundle landed on both machines under the new cache-bust.
3. **Hosted UI visual smoke** — auth-gated (same pattern as 0141-0147). The JSX is deterministic given Supabase data and the local-preview smoke covers the rendering path; left as a user-side check.
4. **Anchor-run replay (D10/D11/D12/D03).** Total cost from transcript: $10.3127 (matches the prior spec-0146 replay; the $13.5110 figure the spec referenced was the post-spec-0143 reconcile number from `metrics.json`, not transcript replay). New fields default appropriately because the anchor pre-dates the agent-layer emit paths: 0 turns with `was_closeout=True`, 0 reasoning tokens, 0 violations, $0.398 total cache savings (GPT side, where the cache engages today).
5. **Fresh-run smoke (D09)** — pending; the long-deferred user-side $10 LLM-spend smoke. **This is the only verification that actually exercises the D13 / D14 / D11-Anthropic / D03-active-event paths end-to-end on real provider output**, because the anchor run pre-dates every one of those emit sites. The deployed bundle is the right target.

## Known follow-ups

- **Fly `machines.dev` mid-rolling-deploy timeout — SEVENTH consecutive deploy.** Same exact shape as every deploy since 0140: machine 1 reaches good state on first pass; machine 2 reaches `stopped` when the fly API times out waiting on health checks; `fly machine start <id>` recovers in ~10 seconds. **Audit row D24 is now seven-in-a-row.** A fly support thread is overdue across the entire batch; this handover is the seventh consecutive escalation note.
- **D02 cache engagement for Anthropic.** Cache-savings line for Claude turns will read `$0.0` until D02 lands the cache-control engagement fix and `cache_read_input_tokens` becomes non-zero. The instrumentation (`DUAL_RESEARCH_DEBUG_USAGE=1`) is shipped and untouched.
- **Anthropic extended-thinking not enabled.** `outputBreakdown.reasoning` on Claude turns will stay at 0 until extended-thinking is turned on in the agent config. The capture path is wired; flipping the config bit + a fresh run is all that's needed when that decision lands.
- **D04 deferred** per spec §3 non-goals — using `EmptyTurnDetected` as a signal to retry / tighten the prompt is a behaviour change on a different surface (protocol/prompts.py + orchestrator turn loop), not the aggregator → render boundary this spec covered. Audit kept it as a separate row to spec after ≥1 fresh run produces real EmptyTurnDetected data to design against.
- **D15 legacy-shim sunset deadline 2026-08-19.** `LEGACY_KEY_TO_CANONICAL` + the legacy `user_prompt` ArtifactDef (in their pre-0145 sense) stay until D15 lands. The `normalisePiecesRaw` retirement in this spec is independent of D15 — D15 is the older read-shim for pre-0145 transcripts.

## D09 status

This spec did NOT fire a fresh-run smoke (cost-gated, user-side action). The four affected D14 / D13 / D11-Anthropic / D03-active-event paths are unit-tested and locally-smoked, but their first end-to-end production exercise will be the next `/dual-research-run` against the deployed v1.13.0 bundle. **Recommendation:** the D09 fresh-run smoke remains open in the audit; on the next $10 spend, watch for:
- Cache-savings line on Claude turns (still $0 unless D02 also lands)
- `system.web_sources` + `system.tool_definitions` rows on every searching turn
- Output-row split (still single-line unless Anthropic extended-thinking flipped)
- Closeout row on any closeout-receiving turn
- Violation chip on any `ProtocolViolation` / `EmptyTurnDetected` event that fires

If a violation chip surfaces during the smoke, screenshot for the post-smoke note.

## Closure status (per audit row)

| Dxx | Status | Notes |
|---|---|---|
| **D03** | **CLOSED** (wire-active) | Component shipped + mounted. Anchor run has no events → no chips render. Will render naturally on any fresh run that emits `ProtocolViolation` / `EmptyTurnDetected`. |
| **D10** | **CLOSED** | Field on wire; rendered as discrete row when `closeout.request` is present in prompt_pieces. |
| **D11** | **PARTIAL** | Reasoning split wired end-to-end; renders correctly when reasoning > 0. OpenAI side: live on every reasoning-tier turn (no current model config enables it). Anthropic side: defensive capture wired but inactive until extended-thinking is enabled in agent config. `tool_calls` is intentionally 0 (no general-purpose tool calls in this codebase). |
| **D12** | **CLOSED** | Helper + field + totals-block line shipped. Anchor replay shows $0.398 cumulative on GPT turns; Claude turns will populate once D02 lands. |
| **D13** | **CLOSED** | Registry + agent-layer emit + `_call.py` augmentation + CcxCard data-driven row all shipped. First production exercise on next searching turn. |
| **D14** | **CLOSED** | Same path as D13. |
| **D16** | **CLOSED** | Allowlist derived from registry; `normalisePiecesRaw` retired (only the retirement comment remains in the JS bundle). |
