# Handover — Spec 0143 — Cost & token attribution + header polish (v1.9.4)

- **Date:** 2026-05-21
- **PR:** [Lexiz/dual-research#165](https://github.com/Lexiz/dual-research/pull/165) (merged, squash, branch deleted)
- **Spec:** [specs/0143-cost-token-attribution-and-header-polish.md](../specs/0143-cost-token-attribution-and-header-polish.md)
- **Anchor run:** `20260521-010637-dvs-backend-language-choice`
- **Backlog rows closed:** B03 (cost / token capture skew) + B11 (top-bar copy button + Total labels)
- **Version:** `1.9.3 → 1.9.4` (PATCH — bug fix only; informational schema additions, no contract change)

## What landed

The 2026-05-21 reconcile job flagged `gpt-5.5-2026-04-23` as drifting 72% under the OpenAI invoice ($1.33 local vs $4.81 invoiced) and `openai-web-search` as drifting 179% over ($0.475 local vs $0.17 invoiced), while every Claude call on the same run silently recorded `cache_read_tokens: 0` AND `cache_write_tokens: 0`. The root causes turned out to be simpler than the spec's first-pass hypothesis: the OpenAI under-count is **entirely** explained by stale `PRICING` rates (4× too low across input/output/cache, and a stale $25/1k web_search rate that's actually $10/1k); re-pricing the captured tokens through the new rates lands exactly on the $4.81 invoice. The Anthropic skew can't be diagnosed from on-disk data alone — the cost arithmetic proves cache_control isn't engaging at the API level (the per-call cost matches plain input × $3/M exactly, which wouldn't be true if the API had billed cache writes), but distinguishing env-disabled-at-runtime from API-silently-rejecting needs an instrumented re-run. This PR ships the instrumentation now and defers the engagement-fix to a follow-up.

## Files touched

- `src/dual_research/agents/base.py` — added `debug_usage_enabled()`, `append_usage_debug()`, `reasoning_tokens` field on `TokenUsage` (informational; not in `compute_token_cost`).
- `src/dual_research/agents/anthropic_agent.py` — one-shot WARNING log when `cache_control` was intended but the response shows zero cache fields; best-effort raw-usage capture gated by `DUAL_RESEARCH_DEBUG_USAGE`.
- `src/dual_research/agents/openai_agent.py` — `reasoning_tokens` capture from `usage.output_tokens_details.reasoning_tokens`; mirror raw-usage capture under the debug flag.
- `src/dual_research/agents/pricing.py` — bumped `gpt-5.5` to `$5.00 / $30.00 / $0.50` (input / output / cache_read) + web_search to `$0.010` (verified 2026-05-21 against developers.openai.com/api/docs/pricing); `PRICING_VERSION = "2026-05-21"`.
- `src/dual_research/orchestrator/_call.py` — added `session_dir` to the `audit_context` dict so the agents can write `usage-debug.jsonl` to the right place; threaded `reasoning_tokens` into the `TurnEnded` event + transcript row.
- `src/dual_research/events/types.py` — `TurnEnded.reasoning_tokens` (defaults to 0).
- `src/dual_research/persistence/metrics.py` — `CallRecord.reasoning_tokens` (defaults to 0).
- `src/dual_research/ui/static/run-detail.jsx` — `CostBadge` gets a lowercase `total` prefix and a `Total:`-leading tooltip; `PhaseDotsRow.copyRunId` writes `<id> · <fmt.cost> · <fmt.tokens>t` to the clipboard.
- `specs/0143-cost-token-attribution-and-header-polish.md` — §1, §3.1, §5, §7 rewritten in-tree to reflect the corrected root cause (stale rates, not missing reasoning_tokens).
- `tests/agents/test_anchor_run_reconcile.py` — new; 3 cases pinning the new rates against the anchor-run invoice.
- `tests/agents/test_capture_cache_fields.py` — new; 4 cases on OpenAI reasoning_tokens passthrough + Anthropic kwargs regression-pin.
- `tests/agents/test_debug_usage.py` — new; 10 cases on the debug env flag.
- `tests/agents/test_pricing.py` — updated for the new GPT-5.5 search rate.
- `tests/agents/test_pricing_version.py` — added the new `(2026-05-21, digest)` snapshot pair.
- `tests/ui/test_aggregator_token_tracking.py`, `tests/audit/test_recompute.py` — updated for the new GPT-5.5 search rate.
- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — `1.9.3 → 1.9.4`.
- `CHANGELOG.md` — `[1.9.4]` entry.

## Schema / env / token changes

Two additive informational fields and one new env var; no breaking change.

- `TokenUsage.reasoning_tokens: int = 0` — new field, default 0, sums via `__add__`. Captured from OpenAI's `usage.output_tokens_details.reasoning_tokens`. **Not** wired into `compute_token_cost` — folding would double-bill, since the Responses API already includes reasoning inside `output_tokens` (proven by the anchor-run invoice reconciliation).
- `TurnEnded.reasoning_tokens` + `CallRecord.reasoning_tokens` — same field, plumbed through the event + persistence shapes so spec 0146's Consumption-card rework can read it later. Old transcripts deserialise unchanged (default 0).
- `DUAL_RESEARCH_DEBUG_USAGE=1` — opt-in, off by default. When on, both agents append the raw SDK usage payload to `<session>/usage-debug.jsonl` per call. Best-effort: any serialisation or I/O failure is swallowed so it can never break a run.

No DB migration, no cache-bust, no protocol changes.

## Tests

```
1274 passed in 10.33s
```

Up from 1257 (Spec 0142 baseline) — **+17 new tests**:

- 3 × anchor-run reconcile (post-fix rates match invoice; pre-fix would drift sanity-pin; anchor `metrics.json` still records the old `pricing_version`)
- 4 × OpenAI reasoning_tokens passthrough + Anthropic `_build_content` regression-pin + TokenUsage __add__
- 10 × debug-usage env flag (default off, parametrised truthy detection, no file when off, row appended when on, no-op without session_dir, serialisation errors swallowed)

The load-bearing test is `test_openai_reconcile_against_invoice_post_spec_0143`, which reads the on-disk anchor run's `metrics.json`, re-prices the captured per-call tokens under the new `PRICING` table, and asserts the per-model totals land at the recorded 2026-05-21 invoice values within $0.05. This pins the rate table against the only piece of ground truth available — the provider invoice.

## Deploy

```
fly deploy
…
both machines on version 188, 1/1 health passing
```

Both machines rolled cleanly at 2026-05-21T18:54-55Z; no fly-side flakes this time (specs 0141 + 0142 hit the machines.dev mid-rolling timeout — this deploy did not).

Live: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.9.4","backend":"supabase"}`.

### Smoke

- **Local UI smoke** — verified during PR prep via the preview MCP harness. CostBadge on the anchor run renders `total $10.3127 · 2882.3kt`; tooltip leads with `Total: 10.3127 USD (tokens 9.7327 · web search 0.5800) · 2,882,339 tokens`. The RunIDChip click handler wrote `20260521-010637-dvs-backend-language-choice · $10.3127 · 2882.3kt` to the clipboard; post-click tooltip swapped to `copied — id · cost · tokens`. Pre-click tooltip previewed the full payload (`<id> · <cost> · <tokens>t — click to copy`).
- **Hosted UI smoke** — left as a user-side check; the JSX is deterministic given Supabase data and the local smoke covered the rendering path.
- **Reconcile rebuild** — see below.

## Open questions resolved

1. **Which sub-hypothesis explains the Anthropic non-engagement?** Deferred — cost arithmetic ruled out the "streamed-usage shape doesn't expose cache fields" path, leaving env-side vs request-side as the remaining branches. The instrumentation lets the next run produce the data needed to discriminate. **Resolved by shipping instrumentation now and deferring the engagement-fix.**
2. **Is the OpenAI search-rate $25/1k current?** No — confirmed `$10/1k` per [OpenAI's developer pricing page](https://developers.openai.com/api/docs/pricing) (verified 2026-05-21). Bumped the rate; the search counter itself was correct (19 audit files match 19 counted calls). **Resolved.**
3. **`reasoning_tokens` as a separate field or folded into `output_tokens`?** Separate field — but informational-only, NOT in billing. The Responses API's `output_tokens` already includes reasoning for GPT-5.5 (proven by the invoice reconciliation arithmetic in the spec §1 rewrite); folding into pricing would double-bill. The field exists so spec 0146 can surface "of which reasoning" on the Consumption card. **Resolved.**

## Backfill / reconcile-rebuild

**Triggered post-deploy and completed cleanly.** Per a user decision during PR prep (overriding spec §4's "no retroactive backfill of historical runs" default), `uv run dual-research recompute-costs --all --push` ran against all 18 local runs in `runs/`. Every `metrics.json` was rewritten under the new `PRICING_VERSION = "2026-05-21"` (pre-spec-0048 runs that had no pricing_version got stamped for the first time; spec-0048-era runs got their pricing_version bumped from `2026-05-17` → `2026-05-21` and a `.recompute-backup` of the original `metrics.json` kept alongside). Total swing was **+$36.6059** across the 18 runs — anchor run alone went `$10.3127 → $13.5110` (+$3.20), matching the spec §1 prediction exactly. All 18 runs pushed to Supabase under the new pricing. The reconcile chip on the hosted UI should transition from `drift` → `ok` for the affected runs after the next nightly reconcile job picks up the new local-vs-invoice deltas.

## Known follow-ups

- **Anthropic cache engagement diagnosis.** The instrumentation is the prerequisite; the actual engagement fix lands in a follow-up spec once a fresh run with `DUAL_RESEARCH_DEBUG_USAGE=1` produces the raw usage payload. The follow-up will either (a) trace the issue to `cache_enabled()` returning False at runtime (env-side — would need a fixture or smoke test that asserts cache is on in prod), or (b) trace it to the API silently rejecting cache_control (request-side — would need a fix at the kwargs-construction layer, probably around the beta header or the cache_control block shape). The smoking-gun shape stays the same either way: `cache_read_tokens == 0 AND cache_write_tokens == 0 AND cost matches plain input × output arithmetic`.
- **Spec 0146 Consumption-card rework can lean on `reasoning_tokens`.** The field is plumbed end-to-end (capture → event → persistence) and lands on every new run. The card can render an "of which reasoning" segment alongside the existing "of which web search" without any additional capture work.
- **Spec 0145 canonical prompt-pieces** is unaffected — this spec didn't touch `prompt_pieces` capture or the Tk-vocabulary registry.
- **GPT-5-mini rates not audited.** The `gpt-5-mini` row in `PRICING` was left at `$0.25 / $2.00 / $0.025 / $0.025`. The model isn't listed on OpenAI's current developer pricing page under that name (the current "mini" tier is `gpt-5.4-mini` at `$0.75/$4.50/$0.075`). The `test` tier (Haiku + gpt-5-mini) is rarely run in prod, but if reconcile starts flagging the test-tier model, the same bump pattern applies — update `PRICING`, bump `PRICING_VERSION`, refresh the snapshot hash.
- **PRICING_VERSION pair maintenance.** Each future rate change must add a new entry to `tests/agents/test_pricing_version.py::expected_versions_to_snapshots`. The test failure message tells the reviewer exactly what to do; the contract is unchanged.
