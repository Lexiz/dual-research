---
spec: 0006
title: Prompt caching to unblock prod-tier rate limit and cut multi-round cost
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.7.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/6"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0006 — Prompt caching

## Context

Spec 0005 surfaced a hard blocker for prod-tier full-convergence E2E: Anthropic's 30K input-tokens-per-minute rate limit on the current account tier. Phase 2 round 2 inlines the brief + both Phase 1 drafts + round-1 turns (~100K input tokens) and trips the limit.

Two structural reasons this is worth fixing now, not punting to later:

1. **Cache reads do not count against the per-minute input-token rate limit.** ([Anthropic rate-limits docs](https://docs.claude.com/en/api/rate-limits).) Caching the static prefix unblocks prod-tier convergence on the current account tier — no account upgrade needed.
2. **The static prefix is huge and stable.** Phase 2 round k+1 reuses ~95% of the round-k input. Without caching we pay full input price ($3/Mtok Sonnet 4.6) every round; with caching the static prefix is 10x cheaper ($0.30/Mtok cache-read), and writes a one-time premium ($3.75/Mtok cache-write) on the first call per session. For a typical 4-round Phase 2 + Phase 3 + 3-round Phase 4 run, expected savings: ~70-80% of input cost.

Anthropic prompt caching is opt-in via `cache_control: {"type": "ephemeral"}` markers on content blocks. The 5-minute default TTL is shorter than a single session, so this spec also opts into the **1-hour extended-cache-TTL beta** (`anthropic-beta: extended-cache-ttl-2025-04-11`) so cache hits survive across phases.

OpenAI Responses API caches prompt prefixes automatically (≥1024 token shared prefix). No explicit markers needed; `cached_tokens` is already extracted in `GptAgent`. So this spec is functionally Anthropic-only on the code side; OpenAI gets verified-working as a side effect.

## Proposed change

### Cache breakpoint marker in prompts

Add a sentinel string to `protocol/prompts.py`:

```python
CACHE_BREAKPOINT = "<<<CACHE_BREAKPOINT>>>"
```

Insert it into each phase prompt builder at the boundary between the stable prefix and the dynamic per-call suffix:

| Prompt | Marker position |
|---|---|
| `preflight_prompt` | After inlined brief |
| `research_prompt` | After inlined brief |
| `negotiation_round1_prompt` | After both Phase 1 drafts |
| `negotiation_turn_prompt` | After both Phase 1 drafts (before prior turns) |
| `drafting_prompt` | After FSD canonical section (before prior turns) |
| `review_turn_prompt` | After inlined current draft (before prior turns) |
| `repair_prompt` | (no marker — short, single call) |

### Anthropic agent: split + apply cache_control

`ClaudeAgent.run` detects the marker, splits the prompt into two text content blocks, and attaches `cache_control` (1-hour TTL) to the prefix block:

```python
if CACHE_BREAKPOINT in prompt:
    prefix, suffix = prompt.split(CACHE_BREAKPOINT, 1)
    content = [
        {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral", "ttl": "1h"}},
        {"type": "text", "text": suffix},
    ]
else:
    content = prompt
messages = [{"role": "user", "content": content}]
```

The 1-hour TTL is gated by the `anthropic-beta: extended-cache-ttl-2025-04-11` header. Add it to `ClaudeAgent.__init__` default headers alongside the existing 1M-context beta.

### Cost ticker honours cache savings

`compute_cost` already multiplies `cache_read_tokens` by the lower cache-read rate. The cost ticker line will show the reduced per-call cost organically. The cumulative `total_cost_usd` likewise drops.

Add a one-line log when caching fires: `[cache] claude phase2-r2: 87K read · 6K write`. Useful diagnostic for confirming cache hits.

### OpenAI verification

No code change needed. Add an assertion in the unit tests that `cached_tokens` extraction is wired (already covered indirectly by `test_search_flag.py` style tests; add one focused test).

### Files added or modified

- `src/dual_research/protocol/prompts.py` — `CACHE_BREAKPOINT` constant; insert marker in 6 builders
- `src/dual_research/protocol/__init__.py` — re-export
- `src/dual_research/agents/anthropic_agent.py` — split prompt, apply cache_control, add beta header
- `src/dual_research/agents/base.py` — `cache_enabled()` flag (env: `DUAL_RESEARCH_NO_CACHE=1`)
- `src/dual_research/orchestrator/_call.py` — cache-hit log line on `TurnEnded`
- `tests/agents/test_cache_wiring.py` (new) — marker detection + structured content
- `tests/protocol/test_prompts_cache_marker.py` (new) — marker present in each phase prompt
- `CHANGELOG.md`, `pyproject.toml`, `__init__.py` — 0.6.0 → 0.7.0

## Out of scope

- **Multi-breakpoint caching** (caching the prior-turns prefix too, for compounding savings round-over-round). Anthropic allows up to 4 breakpoints; we use 1 for now. Easy follow-up if the savings analysis warrants.
- **Cache analytics / live cost-savings ticker.** Cost ticker is already cache-aware via `compute_cost`; per-call diagnostic line is enough.
- **OpenAI explicit caching control.** Automatic; trust it.

## Test plan

- [ ] Unit: every phase prompt builder (except `repair_prompt`) emits exactly one `CACHE_BREAKPOINT` marker
- [ ] Unit: `repair_prompt` does NOT include the marker
- [ ] Unit: `ClaudeAgent` constructs the right messages-API content shape when marker present (two text blocks; first has `cache_control`)
- [ ] Unit: `ClaudeAgent` falls back to single-string content when marker absent
- [ ] Unit: `cache_enabled()` honours env var (case-insensitive)
- [ ] Live smoke: one call with marker → `cache_creation_input_tokens > 0`; second identical call within TTL → `cache_read_input_tokens > 0`
- [ ] Prod-tier full-convergence E2E: same Postgres-vs-SQLite brief that hit the rate limit in spec 0005 should now run to Phase 4 approval (or hard-cap, either is fine — what matters is round 2 does NOT 429)
- [ ] All 81 prior tests still pass

## Risks

- **Cache budget overhead.** First call pays cache_write premium (~25% more than input). On a one-round, one-call run, caching is slightly more expensive than no caching. Acceptable: the orchestrator does ≥2 calls per phase, and the static prefix is reused 4-15 times per session.
- **Beta header dependency.** `extended-cache-ttl-2025-04-11` is a beta. If Anthropic moves the date or retires it, we fall back to 5-minute cache (still works for short phases). Mitigation: try the beta header; if API rejects, retry without and log a warning. v1 doesn't implement the fallback — we'll add it if the header is ever rejected in practice.
- **OpenAI cache may not engage** if the prefix < 1024 tokens or differs between calls. With the brief inlined, every phase-call prefix is well over 1024 tokens, so cache should always engage. Verified by inspecting `cached_tokens` field.
- **Prod-tier E2E still might not converge.** That's a model-behaviour issue, not a code defect. The success criterion for this spec is "round 2 input call no longer 429s" — convergence beyond that is a bonus.
