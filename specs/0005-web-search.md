---
spec: 0005
title: Web search wiring + prod-tier full-convergence E2E
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.6.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/5"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0005 — Web search + prod-tier E2E

## Context

The V/U source-tagging discipline in the protocol (preserved byte-for-byte from the original) assumes agents can actually retrieve fresh sources during a run — `[V]` claims require a real tool call. Through specs 0002-0004 the agents had no search tool wired, so every claim was honestly tagged `[U]` and the corroboration sections were "(none)". The protocol still worked but the V/U discipline was vestigial.

This spec wires web search into both SDK-native tool surfaces:

- **Anthropic Claude** — `web_search` server-side tool on the Messages API (`tool_type: "web_search_20250305"`).
- **OpenAI GPT-5.5** — `web_search` tool on the Responses API (requires switching `GptAgent` from Chat Completions to Responses; the Chat Completions API doesn't expose `web_search`).

After wiring, this spec also runs a **prod-tier full-convergence E2E**: a synthetic brief through Phase 0 → 1 → 2 → 3 → 4 → `final.md` on `claude-sonnet-4-6` (1M-context beta) + `gpt-5.5`, with web search enabled. Exercises the convergence-path code that spec 0004 only unit-tested with stub agents.

After this spec, the orchestrator is feature-complete and ready for the UI work (which the user is preparing in parallel via Claude Design).

## Proposed change

### Anthropic web_search

Add a `web_search` server-side tool to every `claude_agent.run()` call. Tool definition:

```python
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 10,
}
```

The model decides when to invoke. Streaming still works; text deltas come through `text_stream`. Search-tool-use blocks (`server_tool_use`, `web_search_tool_result`) appear in the final message but don't disrupt the text flow. Usage tokens (input/output/cache) already include the tool round-trip overhead.

Cost: $10 per 1000 searches (separate from token cost). Track in `pricing.py` and surface in the metadata header.

### OpenAI Responses API + web_search

Rewrite `GptAgent` to use `client.responses.create(...)` with streaming and `tools=[{"type": "web_search"}]`. Event types we care about:

- `response.output_text.delta` — incremental text (current Chat Completions equivalent)
- `response.completed` — final response object, contains `usage` (input/output/cached tokens) and `model`

Usage extraction mirrors the current Chat Completions path: `input_tokens`, `output_tokens`, `cache_read_tokens` (from `prompt_tokens_details.cached_tokens` if present).

### Pricing additions

```python
# pricing.py — additional flat-rate search cost trackers
ANTHROPIC_WEB_SEARCH_PER_1K = 10.00  # USD
OPENAI_WEB_SEARCH_PER_1K = 30.00     # USD (estimated; tune from real bills)
```

Search counts will be extracted from the response objects (Anthropic puts them in content blocks; OpenAI in the response object's `tools` usage). For v1 we'll log them in the AgentResult `extras` dict; precise cost rollup can come in a follow-up if it matters.

### Disabling search

Env var `DUAL_RESEARCH_NO_WEB_SEARCH=1` disables the tool on both providers. Useful for tests and offline scenarios. Default: enabled.

### Files added or modified

- `src/dual_research/agents/anthropic_agent.py` — add tools parameter conditionally
- `src/dual_research/agents/openai_agent.py` — rewrite to Responses API
- `src/dual_research/agents/pricing.py` — flat-rate web search constants + helper
- `src/dual_research/agents/base.py` — `AgentResult.extras` is already an open dict; add `searches: int` convention
- `tests/agents/test_search_wiring.py` (new) — light unit test that the tool param is included when enabled and absent when env var set
- `CHANGELOG.md`, `pyproject.toml`, `__init__.py` — 0.5.0 → 0.6.0

### Prod-tier E2E

Run after the wiring is verified by a tiny smoke test:

```bash
dual-research \
  --prompt "<simple brief that's likely to converge>" \
  --models prod \
  --soft-cap 6 \
  --hard-cap 10 \
  --out /tmp/dual-research-prod-final.md
```

Verify:
- Phase 0 → 1 → 2 → 3 → 4 → final.md
- Web searches actually fire (visible in transcript or content)
- `final.md` is coherent and contains all six required sections
- Metadata header shows HIGH or MODERATE confidence
- Total cost < $10

## Out of scope

- **Search-cost rollup precision.** v1 logs flat-rate $/1k; if real bills show drift, a follow-up spec adjusts the pricing table.
- **Per-search query inspection.** Not surfaced in events; available in the transcript via content blocks.
- **Notion-rooted brief E2E** — the prod-tier E2E uses a `--prompt` brief for simplicity. Notion ingest is already verified by spec 0002. A follow-up spec could add a Notion-rooted prod-tier E2E, but it's not required for the orchestrator to be feature-complete.

## Test plan

- [ ] Unit: `ClaudeAgent.run` passes tools param when env var not set
- [ ] Unit: `ClaudeAgent.run` omits tools param when `DUAL_RESEARCH_NO_WEB_SEARCH=1`
- [ ] Unit: `GptAgent.run` uses Responses API and includes web_search tool by default
- [ ] Smoke E2E (test tier, web search on): tiny prompt → confirm both agents make at least one search and surface a `[V]` claim with a real URL
- [ ] Prod-tier E2E: full Phase 0→4 convergence on a synthetic brief; `final.md` written; all six sections present; confidence tag HIGH or MODERATE; cost < $10
- [ ] All 70 prior tests still pass

## Risks

- **Responses-API streaming event shape may have edge cases.** Mitigation: implement carefully against the openai 2.36 SDK; if event shape varies, fall back to non-streaming response handling.
- **Anthropic web_search tool quota / errors.** The `max_uses: 10` cap bounds spend per call. SDK retries are already wired (`max_retries=3` in the AsyncAnthropic client).
- **Prod-tier E2E cost.** Estimated $2-5; capped by `--hard-cap 10` for both phases. Will abort and inspect if it exceeds $15.
- **Convergence still flaky even at prod tier.** Possible but less likely. Mitigation: if the prod-tier E2E also hits hard cap, the deadlock path still produces a valid `final.md` with the deadlock appendix, and we ship spec 0005 with documented limitations rather than blocking forever.
