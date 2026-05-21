---
spec: 0143
title: Cost & token attribution correction + run-detail header total-cost copy affordance
label: bug
version-bump: PATCH
status: ready
target-version: 1.9.4
created: 2026-05-21
pr: ""
---

# Spec 0143 — Cost & token attribution correction + run-detail header total-cost copy affordance

> Ship bucket: **Cost-data correctness + run-detail header polish.**
> Depends on: **0039** ([0039-cost-pipeline-integrity.md](./0039-cost-pipeline-integrity.md)) — the headline `cost_usd` invariant, dedup-by-label, and `token_cost + search_cost == cost` rule this spec keeps intact. **0048** ([0048-cost-reconciliation-and-pricing-version.md](./0048-cost-reconciliation-and-pricing-version.md)) — the `PRICING_VERSION` snapshot and `reconcile_results` payload shape this spec's "reconciles against provider" test plan reads. **0049** ([0049-reconcile-from-supabase.md](./0049-reconcile-from-supabase.md)) — the Supabase-backed reconcile job that already flags the anchor run's drift. **0138** ([0138-active-agent-pulse-critique-card-parity-and-run-id-chip.md](./0138-active-agent-pulse-critique-card-parity-and-run-id-chip.md)) §5.3 — the existing `RunIDChip` + `copyRunId` plumbing this spec extends.
> Complexity: **S/M** — one targeted aggregator/agent-capture fix (B03) + a small header re-label and an extended copy payload (B11). The agent-side patch is a couple of lines; the verification surface (a fixture-based unit test) is the bulk of the work.
> Targeted version bump: **PATCH (1.9.3 → 1.9.4)** — bug fix. No protocol, contract, persistence-schema, or wire-format changes; the header changes are additive labels + an extended clipboard payload.

---

## 1. Context

On run [`20260521-010637-dvs-backend-language-choice`](https://qpdsxspdwqukircrfqkm.supabase.co) (the anchor for this batch — Notion item B03), the run-detail header and Consumption tab show:

- **Claude** — 2,182,034 tokens / **$8.5076**
- **GPT** — 700,305 tokens / **$1.8051**
- **Run total** — `runs.total_cost_usd = $10.3127` (Supabase row)

That ratio reads as Claude spending ~$3.90 / 100k tokens while GPT spends ~$2.58 / 100k tokens — a 1.5× per-token gap between two models whose **published input rates** differ by 2.4× ($3.00/1M vs $1.25/1M) but whose **effective** rates should converge once prompt caching is engaged on both sides. The independent ground truth confirms the skew: spec 0049's daily reconcile job ran on 2026-05-21 against this same run and flagged it ([`reconcile_results.payload`](src/dual_research/audit/reconcile.py), Supabase row `date = 2026-05-21`):

```json
{
  "verification_status": "drift",
  "total_local_usd": 10.3127,
  "total_provider_usd": 4.9834,
  "total_delta_usd": 5.3293,
  "per_model_deltas": [
    { "model_id": "gpt-5.5-2026-04-23", "local_usd": 1.3301,
      "provider_usd": 4.8134, "delta_pct": 72.4, "flagged": true },
    { "model_id": "openai-web-search",  "local_usd": 0.4750,
      "provider_usd": 0.1700, "delta_pct": 179.4, "flagged": true }
  ],
  "providers_skipped": { "anthropic": "ANTHROPIC_ADMIN_KEY not set" }
}
```

Two independent skews compose to produce what the user sees on the Consumption tab:

1. **Anthropic prompt-cache capture is silently zero on this run.** Every one of the 20 Claude calls in `runs.metrics.calls` records `cache_read_tokens: 0` and `cache_write_tokens: 0` — including Phase 0 rounds 2–4, Phase 2 rounds, Phase 4 rounds, where the system prompt and the locked-in negotiation context **should** be cache-eligible. A spot-check against published per-token rates confirms the per-call `cost_usd` arithmetic is internally consistent ($3/1M × 8501 + $15/1M × 1907 = $0.0541 — matches `phase0-r1-claude.cost_usd = $0.054108` exactly), so the divergence is upstream of pricing: either the request isn't engaging the cache (e.g. cache_control breakpoint is positioned after the variable suffix, or the prompt prefix mutates between calls), or the streamed-response usage shape doesn't expose `cache_read_input_tokens` the way the non-streamed shape does. Net effect: every Claude call is billed at full input rate ($3/1M) instead of the 10× cheaper cache-read rate ($0.30/1M) for the load-bearing prefix, inflating Claude's recorded cost and obscuring the true per-token ratio.

2. **OpenAI's local cost is under-reported by 72% vs the provider invoice.** Local accounting for `gpt-5.5-2026-04-23` sums to $1.33 across this run; OpenAI's billing API (queried by [`reconcile-costs`](src/dual_research/audit/reconcile.py)) attributes $4.81. The drift sign is the **opposite** of skew (1) — OpenAI is *under*-counted, not over-counted — which is why naively comparing only the local Claude vs local GPT numbers gives a misleading "Claude is too expensive" story. The most likely cause for the OpenAI under-count is reasoning-token output not being captured (the GPT-5.5 family bills `reasoning_tokens` as output but the current `openai_agent.py` capture path may be reading only the visible-completion `output_tokens`). The web-search side is over-counted by 179% — local says 19 × $0.025 = $0.475, provider invoiced $0.17, hinting either the call count is double-counted (one search per turn × two passes? a retry that didn't get deduped?) or the per-request rate in `PRICING` is too high.

The user-facing impact is that the Consumption tab and the top-bar CostBadge tell a **wrong story about which provider is expensive** for this kind of workload, and the daily reconcile chip glows orange every day on every multi-round run — eroding trust in the verification surface that spec 0048 was built to make trustworthy. The exact root-cause investigation for each skew (cache_control placement vs streaming-usage shape; reasoning-token capture vs search-count dedup) is in scope for this spec, but the spec's main load-bearing claim is: **the aggregator path is correct, the per-call invariants hold, the skew enters one layer upstream at the agent-capture level — fix it there, and the existing aggregator + reconcile machinery surfaces the corrected numbers automatically.**

B11 (the top-bar copy button + explicit "Total cost" / "Total tokens" labels) is intentionally bundled into the same spec because it strictly **depends on** B03 being right: there is no point adding a "copy run-id + cost + token totals" affordance while the totals it would copy are misleading. The Notion verbatim says this explicitly: *"Before wiring this up, validate that the cost and token totals being shown — and therefore copied — are accurate; this overlaps with Bug 2, which must be resolved first."*

---

## 2. Current-state audit

### 2.1 Anthropic prompt-cache capture path

| Surface | File:line | Current shape |
| --- | --- | --- |
| Beta header merge | [agents/anthropic_agent.py:48-55](src/dual_research/agents/anthropic_agent.py) | `extended-cache-ttl-2025-04-11` appended to `anthropic-beta` when `cache_enabled()`. |
| Content build with cache_control | [agents/anthropic_agent.py:190-207](src/dual_research/agents/anthropic_agent.py) | `_build_content(prompt)` splits on `CACHE_BREAKPOINT`, wraps prefix in `{ "type": "text", "text": prefix, "cache_control": {"type": "ephemeral", "ttl": "1h"} }`, suffix stays plain. |
| Streamed call | [agents/anthropic_agent.py:78-100](src/dual_research/agents/anthropic_agent.py) | `messages.stream(model, max_tokens, messages=[{role:user, content:_build_content(prompt)}], tools?)` — `await stream.get_final_message()` returns the final `Message` with `usage` populated. |
| Usage extraction | [agents/anthropic_agent.py:111-135](src/dual_research/agents/anthropic_agent.py) | Reads `cache_read_input_tokens`, `cache_creation_input_tokens`, `cache_creation.ephemeral_{5m,1h}_input_tokens`. Folds into `TokenUsage`, then `compute_full_cost(model_id, usage, searches)` stamps `cost`. |
| Prompt-piece breakpoint inserts | [protocol/prompts.py:119, 164, 211, 301, 541, 618](src/dual_research/protocol/prompts.py) | `CACHE_BREAKPOINT` is inserted at six call sites across Phase 0 / 1 / 2 / 4 prompt builders. The marker placement (prefix that should cache vs suffix that mutates per-turn) is the load-bearing detail. |

### 2.2 OpenAI capture path

| Surface | File:line | Current shape |
| --- | --- | --- |
| Cache-breakpoint strip | [agents/openai_agent.py:77](src/dual_research/agents/openai_agent.py) | OpenAI accepts no `cache_control`; the breakpoint is stripped server-side automatic caching does the work. |
| Usage extraction | [agents/openai_agent.py:~100-130](src/dual_research/agents/openai_agent.py) | (audit during spec execution) — `response.usage` exposes `input_tokens`, `output_tokens`, `input_tokens_details.cached_tokens`, `output_tokens_details.reasoning_tokens` for the Responses API. Confirm `reasoning_tokens` is being folded into the recorded `output_tokens` or accounted separately. |
| Search count | [agents/openai_agent.py — `_count_web_searches`](src/dual_research/agents/openai_agent.py) | Counts `web_search_call` tool-use blocks in the Responses output. Confirm no double-counting across retries / sibling turns. |

### 2.3 Per-turn cost capture and aggregation

| Surface | File:line | Notes |
| --- | --- | --- |
| `_on_turn_ended` cost-event handler | [ui/aggregator.py:413-526](src/dual_research/ui/aggregator.py) | Filters by `event.agent in ("claude","openai")` (correct), reads `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `cost_usd`, `search_cost`. Accumulates onto `state.tokens.*` and `state.cost` per UI-label agent (line 503-506). Per-turn `TurnTokenUsage` row keyed by `phase{N}_round{R}_{ag}` written at line 512. Repair siblings get `_repair` suffix per spec 0047. The aggregator itself does not invent skew — it sums the events the agents emit. |
| Per-call persistence to Supabase | [orchestrator/_call.py:161](src/dual_research/orchestrator/_call.py) + the `runs.metrics.calls` JSONB column | One `calls[]` entry per LLM call, carrying `agent`, `label`, `model_id`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `cache_write_{5m,1h}_tokens`, `cost_usd`, `searches`, `search_cost`. Identical fields to the per-turn UI event. |
| Pricing lookup | [agents/pricing.py:92-156](src/dual_research/agents/pricing.py) | `lookup_pricing` → `compute_token_cost` + `compute_search_cost` → `compute_full_cost`. The per-rate table at `PRICING` (line 56-89) is the canonical source for cents-per-token; `PRICING_VERSION = "2026-05-17"` snapshots it per spec 0048. |

The aggregator is **not the bug** — every per-call row sums consistently when re-computed against the pricing table (cross-check on `phase0-r1-claude` and `phase0-r2-claude` both reproduce the recorded `cost_usd` to four decimal places). The skew enters one layer upstream where each agent emits the per-call event: either the usage object it reads back from the SDK doesn't carry the cache fields, or the breakpoint isn't positioned to engage the cache, or the OpenAI reasoning-token / search-count capture is off.

### 2.4 `RunDetailHeader` top-bar row

| Element | File:line | Current shape |
| --- | --- | --- |
| Row 1 layout | [ui/static/run-detail.jsx:117-131](src/dual_research/ui/static/run-detail.jsx) | `header.run-detail__head` → flex row: `Topic`, `CostBadge`, `ReconcileChip`, `RunSearchSummary`, `StatusErrorsBadge`. |
| `RunDetailHeader` total derivation | [ui/static/run-detail.jsx:103-115](src/dual_research/ui/static/run-detail.jsx) | `total = run.agents.claude.cost + run.agents.gpt.cost`; `totalSearchCost = (claude.searchCost \|\| 0) + (gpt.searchCost \|\| 0)`; `totalTokens = (claude.tokens.in + .out) + (gpt.tokens.in + .out)`. |
| `CostBadge` rendering | [ui/static/run-detail.jsx:613-641](src/dual_research/ui/static/run-detail.jsx) | Mono pill: `<fmt.cost(cost)> · <fmt.tokens(tokens)>t`. Tooltip carries breakdown (`tokens X.XXXX · web search Y.YYYY`). **No "Total cost" / "Total tokens" labels are rendered**; the bare numbers and the "$" / "t" suffixes are the only cue. |
| `RunIDChip` + `copyRunId` | [ui/static/run-detail.jsx:268-310](src/dual_research/ui/static/run-detail.jsx) | Spec 0138 §5.3 — clicking the run-id chip writes `run.id` to clipboard; tooltip flips to "copied!" for 1.4 s. **Currently copies the run id only**, not the cost + token totals. The chip lives in row 2 (`PhaseDotsRow`), not row 1. |
| `RunIDChip` primitive | [ui/static/shared.jsx:844-852](src/dual_research/ui/static/shared.jsx) | `function RunIDChip({ id, size, className, onClick, title })` — pill-shaped mono chip; the existing API already accepts `onClick` and `title`. |

---

## 3. Proposed change

### 3.1 Fix the per-agent capture skew (B03)

**Step 1 — diagnose, then fix.** This spec carries a debug-instrumentation step before the patch, because the root cause for each of the two skews is "most likely X" rather than confirmed:

1. Re-run the anchor brief with `DUAL_RESEARCH_DEBUG_USAGE=1` (new env flag, gated by `agents/base.py`); both agents log the raw `usage` object their SDK returned to the run-relative `usage-debug.jsonl` file alongside the existing `transcript.jsonl`. One short run is enough — the data confirms whether `cache_read_input_tokens` is genuinely 0 on the wire, or whether the streamed-response usage shape simply doesn't expose it (forcing a post-stream `messages.create` peek, or a switch to `client.messages.with_raw_response.stream`).
2. From the diagnosis:
   - **If the Anthropic SDK's streamed-final-message returns `cache_read_input_tokens` correctly but the values are 0** → root cause is prompt-side. Audit each `CACHE_BREAKPOINT` insertion site (six locations in [protocol/prompts.py](src/dual_research/protocol/prompts.py) — lines 119, 164, 211, 301, 541, 618) and verify the prefix is stable across rounds (the system prompt + locked-in negotiation context, not the per-round critique deltas). Move the breakpoint if it's positioned after a per-round variable section.
   - **If the streamed shape genuinely doesn't expose `cache_read_input_tokens`** → bridge the gap. The streamed-final-message path at [anthropic_agent.py:91-100](src/dual_research/agents/anthropic_agent.py) needs to additionally surface the cache fields, either by switching to `client.messages.create(stream=False)` for the usage extraction half (incompatible with live streaming — undesirable) or by reading the `event.message.usage` deltas during the stream's `message_stop` event (preferred — the SDK exposes per-event usage on `RawMessageStopEvent`).
   - **For the OpenAI under-count** → add explicit `reasoning_tokens` capture from `response.usage.output_tokens_details.reasoning_tokens` (Responses API) and either (a) fold into `output_tokens` so the existing pricing path bills them correctly, or (b) carve a new `reasoning_tokens` field on `TokenUsage` priced at the same `output_per_mtok` rate. The reconcile delta (72% under-count) puts this at well over 100k reasoning tokens unaccounted across the run — the magnitude lines up with what GPT-5.5's reasoning mode typically generates.
   - **For the search-count over-count (179% drift)** → audit `_count_web_searches` for double-counting (one count per turn × two counted), and audit the rate in `PRICING["gpt-5.5"]` (currently `web_search_per_request=0.025`) against OpenAI's currently-published rate. The 179% drift could be either side.

**Step 2 — apply the targeted fix(es).** Each diagnosis path lands a small patch:

- For breakpoint placement: move the `CACHE_BREAKPOINT` marker in the affected prompt builder(s); no other file changes. The aggregator + pricing path automatically picks up the corrected `cache_read_tokens` values once the API engages the cache.
- For streamed-usage shape: replace [anthropic_agent.py:111](src/dual_research/agents/anthropic_agent.py)'s `u = final_msg.usage` with a `_collect_usage(stream)` helper that reads from `RawMessageStopEvent.message.usage` (which exposes the full usage shape) and falls back to `final_msg.usage` if absent. ~15 LOC.
- For OpenAI reasoning tokens: add `reasoning_tokens` to the `TokenUsage` field set at [agents/base.py](src/dual_research/agents/base.py) (or fold into `output_tokens` at the openai_agent.py extraction site — TBD by the patch), update `compute_token_cost` at [agents/pricing.py:119-125](src/dual_research/agents/pricing.py) if the new field is carried separately. ~10 LOC.
- For search rate: bump `gpt-5.5.web_search_per_request` to the verified-from-provider rate and bump `PRICING_VERSION = "2026-05-21"` per the spec 0048 rule.

**Step 3 — validate against the anchor run.** After the patch, re-run the anchor brief and check:
- `runs.metrics.calls[].cache_read_tokens` is non-zero for Claude calls after Phase 0 round 1 (the cache should hit on the second call onwards once the prefix is stable).
- `runs.metrics.calls[].output_tokens` for OpenAI calls reflects reasoning + visible-completion tokens.
- The 2026-05-21 reconcile job (or a manual `reconcile-costs --date 2026-05-21 --force-rerun`) shows `verification_status = "ok"` (delta ≤ 1% per-model) instead of `"drift"`.

The aggregator code at [ui/aggregator.py:413-526](src/dual_research/ui/aggregator.py) is **not touched** by this spec — its per-event accumulation logic is correct. The fix is purely at the per-agent capture layer; the aggregator + pricing + Consumption tab + CostBadge surface the corrected numbers automatically once the upstream events carry the right field values.

### 3.2 Add "Total cost" / "Total tokens" labels + extend the copy payload (B11)

Two coupled UI changes to the run-detail header. Both extend existing primitives — no new design-system surface.

**3.2.1 Re-label the `CostBadge`.** Today the badge renders as a bare `$10.31 · 2.88Mt` pill. The user reported that without an explicit "Total" qualifier, the figures are easily misread as per-phase or per-model (the Timeline pane next to it shows per-agent `TimelineAgentPill` costs — the visual proximity creates the confusion).

The change is additive label text, scoped to [ui/static/run-detail.jsx:625-640](src/dual_research/ui/static/run-detail.jsx):

```jsx
function CostBadge({ cost, tokens, searchCost }) {
  const sc = Number(searchCost) || 0;
  const tokenCost = Math.max(0, cost - sc);
  let tip = `Total: ${cost.toFixed(4)} USD · ${tokens.toLocaleString()} tokens`;
  if (sc > 0) {
    tip = (
      `Total: ${cost.toFixed(4)} USD (tokens ${tokenCost.toFixed(4)} · `
      + `web search ${sc.toFixed(4)}) · ${tokens.toLocaleString()} tokens`
    );
  }
  return (
    <span title={tip}
          className="mono"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '3px 9px', borderRadius: 999,
            background: 'var(--md-surface-container-high)', border: '1px solid var(--md-outline-hair)',
            fontSize: 11, color: 'var(--md-on-surface-variant)', flexShrink: 0,
            whiteSpace: 'nowrap',
          }}>
      <span style={{ color: 'var(--md-on-surface-faint)', fontSize: 10 }}>total</span>
      <span className="num">{fmt.cost(cost)}</span>
      <span style={{ color: 'var(--md-on-surface-faint)' }}>·</span>
      <span className="num" style={{ color: 'var(--md-on-surface-muted)' }}>{fmt.tokens(tokens)}t</span>
    </span>
  );
}
```

The new `<span>total</span>` segment uses `--md-on-surface-faint` (one tone lower than the numeric value) at 10 px — small enough that the pill width grows by ~28 px (about three characters at the current font size) without disrupting row 1's flex layout. The label deliberately reads `total` (lowercase, no colon) so it functions as a single-word qualifier rather than competing for visual weight with the number. Both the cost and the token segments stay numeric — one `total` prefix covers the pair, since they are both run-wide totals and the `·` separator visually groups them as one composite figure. The tooltip also gets a `Total:` prefix so the breakdown stays in scope.

CSS uses existing M3 surface + on-surface-faint tokens — no new design-system declarations.

**3.2.2 Extend `copyRunId` to copy id + total cost + total tokens.** The existing copy handler at [ui/static/run-detail.jsx:269-283](src/dual_research/ui/static/run-detail.jsx) writes only `run.id` to the clipboard. Extend it to write a single multi-field payload the user can paste into chat, a commit message, or an issue:

```jsx
function PhaseDotsRow({ run, startedClock, elapsedLabel }) {
  const [copiedRunId, setCopiedRunId] = React.useState(false);
  // Spec 0143 §3.2.2 — total cost + total tokens travel along with the
  // run id so a single click yields a paste-ready "run X · $Y · Zt" line.
  // Derivation mirrors RunDetailHeader so the two surfaces never drift.
  const totalCost = (run.agents?.claude?.cost || 0) + (run.agents?.gpt?.cost || 0);
  const totalTokens =
    (run.agents?.claude?.tokens?.in || 0) + (run.agents?.claude?.tokens?.out || 0) +
    (run.agents?.gpt?.tokens?.in || 0)    + (run.agents?.gpt?.tokens?.out || 0);
  const copyPayload = `${run.id} · ${fmt.cost(totalCost)} · ${fmt.tokens(totalTokens)}t`;

  const copyRunId = React.useCallback((e) => {
    e.stopPropagation();
    if (!run?.id || !navigator.clipboard) return;
    navigator.clipboard.writeText(copyPayload).then(
      () => {
        setCopiedRunId(true);
        setTimeout(() => setCopiedRunId(false), 1400);
      },
      () => { /* non-secure context — silent no-op, matches 0138 §5.3 */ },
    );
  }, [run?.id, copyPayload]);
  // …chip renders unchanged…
  return (
    // …
    <RunIDChip
      id={run.id}
      onClick={copyRunId}
      title={copiedRunId
        ? 'copied — run id · total cost · total tokens'
        : `${copyPayload} — click to copy`}
    />
    // …
  );
}
```

`fmt.cost` and `fmt.tokens` are the same formatters the `CostBadge` uses, so the copied numbers are always identical to the on-screen pill (no parallel formatting path, no risk of "0.4 places vs 2 places" drift). The chip's `title` tooltip previews the exact payload so the user sees what will land in the clipboard before clicking — important because the payload is now richer than just the id.

The on-screen `RunIDChip` rendering (id, font, position in row 2) is unchanged — only the click side-effect and the tooltip text change. The chip itself stays the affordance from spec 0138 §5.3; this spec just extends what it copies.

---

## 4. Out of scope

- **No Consumption-card visual rework.** The `CcxCard` collapsed/expanded anatomy at [ui/static/run-detail.jsx:2113-2240](src/dual_research/ui/static/run-detail.jsx) (single Total-tokens bar, per-phase rows, "of which web search" breakdown) is owned by spec **0146** in this batch. This spec leaves the card markup, CSS, and per-phase rendering exactly as today — it only changes the per-event numbers the card receives.
- **No canonical prompt-piece tracking.** Spec **0145** ([0145 canonical prompt-pieces](./0145-canonical-prompt-pieces.md) — same batch) covers stable cross-run prompt-piece identity for the Consumption-tab segment-width comparisons. This spec doesn't touch `prompt_pieces` capture, the `TurnTokenUsage.prompt_pieces` field, or the Tk-vocabulary segment renderer.
- **No run-list cost rendering changes.** [ui/static/run-list.jsx](src/dual_research/ui/static/run-list.jsx) renders cost via `summarize_run`'s `cost` field; that field's value will improve automatically when the upstream capture is fixed, but the run-list cell itself (formatter, sort key, column width) is not touched.
- **No retroactive backfill of historical runs.** Existing Supabase rows for runs prior to this patch keep their original `cost_usd` and token values. A `recompute-costs --backfill` invocation against historical transcripts is out of scope; old transcripts don't have the missing field data on the wire to recompute from.
- **No reconcile-chip behaviour change.** The 5-state `ReconcileChip` at [ui/static/run-detail.jsx](src/dual_research/ui/static/run-detail.jsx) (introduced by spec 0048) continues to drive its color from `reconcile_results.payload.verification_status`. After this spec lands, healthy runs should show the "ok" state — but the chip code itself is unchanged.
- **No new clipboard payload formats.** Markdown, JSON, and "share-link" payload modes for the copy button are deferred. The text payload (`<id> · <cost> · <tokens>t`) is the only shape this spec ships.
- **No deep-research cost-tracking changes.** Spec 0118 (deep-research consumption tracking) governs the deep-research turn-cost shape; this spec doesn't alter that path. Any DR-turn under-count is its own follow-up.

---

## 5. Test plan

1. **Unit — aggregator reconcile invariant** at `tests/ui/test_aggregator_cost.py` (new). Fixture: a synthetic `transcript.jsonl` carrying ten `turn_ended` events split across both agents, with realistic mixed `cache_read_tokens` / `cache_write_tokens` / `searches` values. After `build_run` + the fix, assert: `run.agents.claude.cost + run.agents.gpt.cost == sum(event.cost_usd)` (within 1e-6); `state.tokens.in_ + state.tokens.out` matches the per-agent fixture sum; and `state.search_cost <= state.cost` (the spec 0039 invariant). The same fixture covers the "repair sibling" code path at [aggregator.py:468](src/dual_research/ui/aggregator.py) to ensure dedup-by-label still holds after this spec.

2. **Unit — per-agent capture parity** at `tests/agents/test_capture_cache_fields.py` (new). Mock the Anthropic SDK's streamed-message API to return a `RawMessageStopEvent.message.usage` with non-zero `cache_read_input_tokens` and assert `ClaudeAgent.run`'s emitted `AgentResult.usage.cache_read_tokens` matches. Mirror for OpenAI's Responses API with non-zero `reasoning_tokens` → `AgentResult.usage.output_tokens` (or new field).

3. **Unit — reconcile-result consistency** at `tests/audit/test_reconcile_after_fix.py`. Feed a `metrics.json` shaped like the *post-fix* expected output for the anchor run into the existing `reconcile-costs` code path with mocked provider responses (matching the 2026-05-21 Supabase invoice values — Anthropic provider mocked even though the production environment skips it). Assert `verification_status = "ok"` and every `per_model_delta.flagged = false`.

4. **Integration — re-run anchor brief end-to-end.** Fire the same brief (Document Verification Service · Backend Language Choice) against the prod tier. Compare the resulting `runs.metrics.calls` field-by-field against the recorded 2026-05-21 row: post-fix Claude `cache_read_tokens` is non-zero after the first cache-write call; OpenAI `output_tokens` reflects reasoning + completion; total cost moves in the expected direction (Claude down, OpenAI up, net total closer to the provider-billed $4.98 for the OpenAI side). Document the before/after in the PR description.

5. **Manual smoke — top-bar copy + labels.** On the anchor run's hosted UI:
   - Cost badge reads "total $10.31 · 2.88Mt" (or whatever the post-fix total is).
   - Hover the cost badge → tooltip starts with `Total:`.
   - Click the `RunIDChip` → clipboard contains `<run-id> · $10.31 · 2.88Mt` (or whatever the post-fix numbers are). Verify via `pbpaste` on macOS.
   - Tooltip on the chip previews that exact string before the click.
   - On a fresh in-flight run (cost / tokens both incrementing), watch the tooltip update as the totals grow — confirms the `copyPayload` `useCallback` deps list (`[run?.id, copyPayload]`) re-evaluates correctly.

6. **Manual smoke — adjacent surfaces unaffected.** Visit Timeline / Consumption / Compare / Search / Run-list — none of these surfaces should render any visual difference. The Consumption tab's `CcxCard` per-row numbers will change (because the underlying per-call values change after the fix), but the card layout, colors, scale, and interaction model are all identical to today.

---

## 6. Risks

1. **Pricing-version drift on backfill comparisons.** Bumping `PRICING_VERSION` (if the OpenAI search rate is adjusted) means runs priced under the old table and re-reconciled against the new table will *appear* to drift — that's by design (spec 0048 D1 calls this out: "old runs ARE under old rates, drift is honest"). Mitigation: include a one-line note in the PR description so the next reconcile-chip-color watcher doesn't mistake the pricing-version bump for a fresh capture bug; the `metrics.pricing_version` field already records which table each run was priced under, so the reconcile job can distinguish honest pricing-version drift from real capture drift.

2. **Copy-button affordance discoverability.** The `RunIDChip` is a 4-character hex-prefix mono chip; nothing in its visual treatment hints that clicking copies anything, let alone a multi-field payload. Spec 0138 §5.3 deliberately leaned on the chip's tooltip ("X — click to copy") as the only discovery affordance, deferring a snackbar-style confirmation to a follow-up. This spec preserves that posture (the tooltip is the only signal), but the multi-field payload is a stretch — a user who clicks expecting to copy only the id is surprised by the extra fields. Mitigation: the tooltip text now previews the full payload, so the click happens with eyes-open. If user feedback flags this as confusing, a follow-up can split the affordance (e.g. shift-click = id only, plain click = full payload), but the spec ships with the unified click for simplicity.

3. **Cache breakpoint move breaking convergence.** If the diagnosis traces the Anthropic skew to `CACHE_BREAKPOINT` placement and the fix moves the marker, there is a small risk the new placement shifts what the agent sees in the cacheable prefix vs the variable suffix, which can affect how the agent reads the prompt across rounds. Mitigation: any breakpoint move ships with a re-run of the anchor brief and at least one other recent multi-round run (e.g. the 1.9.x batch's primary integration brief), comparing the resulting `agreed_plan` artifact hashes round-over-round to confirm no convergence regression. The breakpoint is a caching hint, not a semantic boundary — the agent receives identical text either way.

4. **Reasoning-token capture path regression.** OpenAI's Responses API exposes `reasoning_tokens` via `output_tokens_details`; if the field is renamed or restructured upstream, the new capture code at `openai_agent.py` would silently revert to the current under-count. Mitigation: the unit test at §5.2 mocks the exact field shape; the integration test at §5.4 catches any wire-level surprise. A `DEBUG_USAGE=1` env flag (added under §3.1 step 1) leaves a residual diagnostic surface so future drift is one env-var-flip away from observable.

5. **Rollback path.** The agent-capture patch is small, contained, and self-test-covered — `git revert` of the spec's PR restores the prior behaviour without data migration (the change writes additional values into `cache_read_tokens` / `output_tokens` fields that already exist in the persistence schema; reverting just stops writing the corrected values). The header re-label and copy-payload extension are pure UI; revert restores the previous bare-cost-pill and id-only copy. No persisted state needs unwinding.

---

## 7. Open questions

1. **Which side of the Anthropic skew is real?** The "most likely" diagnosis is breakpoint placement; the alternative is the streamed-response usage shape not exposing the cache fields. Both paths land a fix, but the precise patch differs. The §3.1 Step 1 instrumentation answers this in one short anchor-re-run before any code lands.

2. **Is the OpenAI search-rate published as $25/1k still current?** The reconcile job reports a 179% over-count vs the OpenAI invoice. Either `_count_web_searches` is double-counting, or the `web_search_per_request = 0.025` rate is stale. Confirm against OpenAI's currently-published Responses-API tool-call rate before bumping `PRICING_VERSION`.

3. **Should `reasoning_tokens` be a first-class field on `TokenUsage`, or folded into `output_tokens`?** Folding is simpler (no schema change, no aggregator touch, no per-turn UI change); breaking out as a separate field lets the Consumption tab eventually surface "of which reasoning" alongside "of which web search". Defer to the patch — the spec accepts either shape so long as the pricing math reflects reasoning tokens at the model's `output_per_mtok` rate.
