---
spec: 0039
title: Cost-pipeline integrity — preserve metrics on resume, price the cache tier that was actually used, fold tool spend into the headline
label: bug
version-bump: MINOR
status: merged
target-version: 0.37.0
created: 2026-05-16
pr: ""
---

# Spec 0039 — Cost-pipeline integrity

## Context

Audit of the [Partner Vetting Architectural Proposal run](../runs/20260516-035048-partner-vetting-arch-critique)
(2026-05-16) surfaced a roughly 4× under-report in the user-facing
total: `metrics.json` says `total_cost_usd = $2.45`, the deduplicated
transcript sums to `$8.78`, and a faithful recomputation that folds
web-search fees in brings the recoverable number to **≈$9.86**. The
provider dashboards report "≈$12" — the missing ~$2 is the 1h-cache
underbilling, which the recompute tool **cannot retroactively fix**
because old transcripts only carry the aggregate `cache_write_tokens`
field (no per-TTL split). The 1h-cache fix takes effect for new runs
going forward; the search-fee fold-in is what's recoverable on
backfill. Three independent defects compose to produce this:

A subtlety surfaced during validation: the **naive** sum of every
`turn_ended.cost_usd` in this run's transcript is $12.74, but that
double-counts phase 4's parse-error recovery — every `phase4-r*-*`
label appears twice. The 41 turn_ended events collapse to 29 unique
turns when deduped by `label` (later event wins). `_corrupted-backup/`
in the run dir captures the parse failure that triggered the retry.
Any code that sums the transcript MUST dedupe by label or it will
overstate runs where a retry occurred. D3 and D10 capture this.

1. **Resume loses prior metrics.** `Metrics()` is instantiated empty
   in [orchestrator/run.py:110](../src/dual_research/orchestrator/run.py)
   on every session entry. Prior `metrics.json` is never re-hydrated.
   When a run is resumed (the partner-vetting run was killed after
   phase 3 and resumed for phase 4), the final `metrics.save()` writes
   only the resume window's calls — overwriting the pre-resume cost.
   The [aggregator fallback at ui/aggregator.py:211-215](../src/dual_research/ui/aggregator.py)
   knows about resume windows but only kicks in when `cost == 0.0`,
   so a non-zero resume window silently masks the rest of the run.

2. **Cache writes are priced at the 5-minute rate while the API is
   billed at the 1-hour rate.** [anthropic_agent.py:30](../src/dual_research/agents/anthropic_agent.py)
   requests the `extended-cache-ttl-2025-04-11` beta and emits
   `cache_control: {"type": "ephemeral", "ttl": "1h"}`. Anthropic
   bills 1-hour writes at **2× base input**, but
   [pricing.py:31](../src/dual_research/agents/pricing.py) hardcodes
   `cache_write_per_mtok = 3.75` (the 1.25× = 5-minute rate). On the
   partner-vetting run, 856,866 Claude cache-write tokens hit Sonnet
   4.6 ($3/Mtok base) at the wrong rate — if every write was at the
   1h tier, this bug under-billed by ~$1.93 (`856,866 × (6.00 −
   3.75) / 1,000,000`). The exact figure depends on the per-call
   5m/1h split. Anthropic helpfully reports the split as
   `usage.cache_creation.ephemeral_5m_input_tokens` and
   `ephemeral_1h_input_tokens`, so we can price each tier exactly.

3. **Web-search fees are deliberately excluded from the headline.**
   Spec 0031 D7 kept `search_cost` as a "side-channel" surfaced only
   in the Consumption tab's expanded panel. Search cost is real money
   on the invoice — 20 Claude searches × $0.010 + 35 OpenAI searches
   × $0.025 = **$1.08** on this run (deduped) — and is currently
   missing from every persisted total (metrics.json `total_cost_usd`,
   RunCompleted event, Supabase `runs.total_cost_usd`, CLI summary).
   The Consumption tab is the only place a user can find it. With
   (1) and (2) fixed, the gap between the headline and the invoice
   becomes obvious; we should close it rather than leave a known
   side-channel.

These three are tangled enough that fixing them piecemeal would mean
visiting the same 14 cost surfaces multiple times. This spec
addresses them together, settles a single source of truth for "what
did this run cost?", and adds a one-shot backfill so existing runs
recompute correctly.

Prior context:
- [Spec 0030 — token-consumption tab](./0030-timeline-ux-pass.md)
  established the per-turn `TurnTokenUsage` plumbing.
- [Spec 0031 — consumption follow-ups](./0031-consumption-followups.md)
  added `search_cost` as a side-channel (D7); this spec promotes it
  into the headline.
- [Spec 0032 — convergence + live push](./0032-convergence-and-live-push.md)
  introduced `--push-while-running`, which currently propagates the
  same flawed `total_cost_usd`.
- [Briefing — Partner Vetting cost audit](../handoffs)
  (Perplexity-generated; partly mistaken about the failure mode but
  prompted this investigation).

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Headline cost = full invoice (tokens + per-request tool fees).** | `cost_usd` everywhere — `AgentResult.cost_usd`, `TurnEnded.cost_usd`, `CallRecord.cost_usd`, `metrics.json.total_cost_usd`, `RunCompleted.total_cost_usd`, Supabase `runs.total_cost_usd` — becomes the **complete** cost for that scope, with web-search fees included. `search_cost` survives as a breakdown number for the UI ("of which $X is web search") but never as a *separate* total to be added or omitted elsewhere. Reverses Spec 0031 D7. |
| D2  | **Metrics state is rehydrated on every session entry.** | `Metrics.load_or_new(path)` replaces `Metrics()` in `orchestrator/run.py`. If `metrics.json` exists and parses, its `calls` list (plus `started_at`) is reconstructed; new turns append. Resume windows compose cleanly. `started_at` is preserved from the first session; `ended_at` is overwritten on each completion. |
| D3  | **Transcript remains the canonical truth; metrics.json is a cache of it. Dedup by `label`, later wins.** | The aggregator's `_sum_transcript_cost` path becomes the *primary* reader, not a fallback. `_empty_run()` always sums the transcript and uses metrics.json only when transcript is missing/empty. Critically, when a run includes a parse-error recovery (e.g. partner-vetting's phase-4 retries), the same `turn_ended` label appears multiple times — the sum **must** keep only the latest event per label or it overstates the total. This dedup also applies on the per-turn aggregation path so `TurnTokenUsage` reflects the canonical attempt, not a failed earlier one. |
| D4  | **Pricing splits cache writes by TTL tier.** | `ModelPricing` replaces `cache_write_per_mtok` with `cache_write_5m_per_mtok` and `cache_write_1h_per_mtok`. `compute_cost` takes a `TokenUsage` that carries the split. Backward-compatibility: any code/transcript still using the single `cache_write_tokens` integer is treated as **5-minute writes** (matches pre-beta behaviour). |
| D5  | **TokenUsage carries a 5m/1h split AND a back-compat alias.** | New fields: `cache_write_5m_tokens: int = 0`, `cache_write_1h_tokens: int = 0`. The existing `cache_write_tokens` field becomes a `@property` that returns the sum — preserves all aggregator code that reads it for display, and means old transcripts (which only have `cache_write_tokens`) load with that integer going into `cache_write_5m_tokens` and zero in 1h. |
| D6  | **Cost computation includes searches and is a single function.** | New `compute_full_cost(model_id, usage, searches) -> float` is the canonical entry point. Both agents call it for `AgentResult.cost_usd`. Old `compute_cost` is preserved as `compute_token_cost` (it still has callers — pricing tests, the recompute tool's breakdown) but is **not** what stamps the headline. `compute_search_cost` stays as is. |
| D7  | **Agents read the per-TTL cache breakdown from the provider response.** | `anthropic_agent.py` reads `usage.cache_creation.ephemeral_5m_input_tokens` and `ephemeral_1h_input_tokens` when present. If `cache_creation` is absent (older response shape, beta rejected), fall back to crediting the entire `cache_creation_input_tokens` to 5m. `openai_agent.py` always emits 0 for both new fields (OpenAI doesn't bill cache writes separately). |
| D8  | **Transcript event shape carries the new fields with safe defaults.** | `TurnEnded` gains `cache_write_5m_tokens: int = 0` and `cache_write_1h_tokens: int = 0` alongside the existing `cache_write_tokens`. The orchestrator writes all three (the aggregate is convenient for old readers). The transcript writer never removes `cache_write_tokens` — old aggregators stay green. |
| D9  | **Aggregator computes per-turn cost from the event's full data, not by adding search_cost on top.** | `_on_turn_ended` reads `event.get("cost_usd", 0.0)` and trusts it (it now includes search). The `search_cost` *breakdown* is still computed from `searches × per-search rate` and stored on `TurnTokenUsage.search_cost` for the Consumption tab's "of which" line. Token-only cost becomes `TurnTokenUsage.token_cost = cost - search_cost` (new field), also for the breakdown UI. |
| D10 | **One-shot backfill tool for existing runs.** | New CLI subcommand `dual-research recompute-costs [--run RUN_ID] [--all] [--push]`. For each target run: re-walks `transcript.jsonl` **deduping by `label` (later event wins, matching D3)**, recomputes every per-turn `cost_usd` under the new pricing rules (including search), rewrites `metrics.json`, optionally re-pushes to Supabase. Before overwriting, the old `metrics.json` is copied to `metrics.json.pre-0039.bak` (skipped if the `.bak` already exists — idempotent). Reports a diff (`old → new` per run) and a grand-total delta. |
| D11 | **`RunCompleted` total is always recomputed at run-end from the in-memory `Metrics`.** | `metrics.total_cost_usd()` is the authority; the orchestrator's `RunCompleted` emission and the final `metrics.save()` both consume it. Removes one of three current paths that can drift. |
| D12 | **Supabase schema stays decimal(10,4) for `total_cost_usd`.** | The number is still ≤ $999,999.9999. We bump no columns. The opaque `metrics` JSONB column gets the freshly-saved metrics.json on every push, so the JSONB and the materialised column always agree. |
| D13 | **Live push (`--push-while-running`) uses the same recomputed totals.** | The 30s push loop reads metrics.json after every write (it already does, via `_build_run_row`). Because D2 keeps metrics.json correct across the run lifecycle, the hosted UI stays accurate during long runs without further changes. |
| D14 | **Versioning + release notes.** | Label stays `bug` (CHANGELOG entry goes under `### Fixed`); version bumps 0.35.0 → 0.37.0 per the audit briefing (skips 0.36.0, reserved for a parallel-session spec). Out of step with CONTRIBUTING.md's `bug → PATCH` default — noted here intentionally because the TokenUsage / TurnEnded / pricing-table shape changes warrant MINOR per the repo's pre-1.0 practice. The CHANGELOG `Fixed` callout calls out that totals on the run list & detail header will *increase* for runs that used web search or 1h-cache writes. |

## Proposed change

### 1. Pricing — `src/dual_research/agents/pricing.py`

- Replace `cache_write_per_mtok` field with two fields on `ModelPricing`:
  ```python
  cache_write_5m_per_mtok: float = 0.0
  cache_write_1h_per_mtok: float = 0.0
  ```
- Update `PRICING` entries. Sonnet 4.6:
  ```python
  cache_write_5m_per_mtok=3.75,   # 1.25× input
  cache_write_1h_per_mtok=6.00,   # 2× input
  ```
  Haiku 4.5: `1.25 / 2.00`. OpenAI models: both 0.0 (no separate cache-write billing).
- Rename existing `compute_cost` → `compute_token_cost`. Logic uses both new fields, weighted by `usage.cache_write_5m_tokens` and `usage.cache_write_1h_tokens`.
- Add `compute_full_cost(model_id, usage, searches) -> float`:
  ```python
  return compute_token_cost(model_id, usage) + compute_search_cost(model_id, searches)
  ```
- `compute_search_cost` unchanged.
- Add module-level constants `CACHE_WRITE_5M_MULTIPLIER = 1.25`, `CACHE_WRITE_1H_MULTIPLIER = 2.0` so the relationship to base-input rate is self-documenting.

### 2. TokenUsage — `src/dual_research/agents/base.py`

- Add fields:
  ```python
  cache_write_5m_tokens: int = 0
  cache_write_1h_tokens: int = 0
  ```
  Order them after `cache_write_tokens` to minimise positional-arg breakage if any caller constructs `TokenUsage` positionally (sweep the repo and fix any such call — current uses all keyword-style).
- Convert `cache_write_tokens` to a `@property` returning `cache_write_5m_tokens + cache_write_1h_tokens`. Since it was a dataclass field, this requires either:
  - **Option A**: keep `cache_write_tokens` as a field, add the two new fields, and document that `cache_write_tokens == 5m + 1h` (the agents enforce this).
  - **Option B**: drop `cache_write_tokens` as a field and add a property.
  - **Pick A** to minimise blast radius — the JSON shape on the transcript stays identical, and aggregators that read `cache_write_tokens` keep working.
- Update `TokenUsage.__add__` to also sum the two new fields.

### 3. Anthropic agent — `src/dual_research/agents/anthropic_agent.py`

- After extracting `u = final_msg.usage`, read the structured cache_creation breakdown:
  ```python
  cc = getattr(u, "cache_creation", None)
  if cc is not None:
      cw_5m = getattr(cc, "ephemeral_5m_input_tokens", 0) or 0
      cw_1h = getattr(cc, "ephemeral_1h_input_tokens", 0) or 0
  else:
      cw_5m = getattr(u, "cache_creation_input_tokens", 0) or 0
      cw_1h = 0
  ```
- Build `TokenUsage` with all three cache-write fields (`cache_write_tokens = cw_5m + cw_1h`, the new split filled in). Sanity-check that `cw_5m + cw_1h == cache_creation_input_tokens`; if mismatch, log a warning and trust the breakdown.
- Replace `cost = compute_cost(...)` with `cost = compute_full_cost(self._spec.model_id, usage, searches)`. `searches` is already computed earlier in the function.
- Comment block above the cache-control wiring (line 28-30) updated to reference Spec 0039 and note that the 1h tier costs more — so the choice is deliberate (we *want* the longer TTL for our use case where multi-round phases reread the same draft).

### 4. OpenAI agent — `src/dual_research/agents/openai_agent.py`

- Build `TokenUsage` with `cache_write_5m_tokens=0`, `cache_write_1h_tokens=0`, `cache_write_tokens=0` (unchanged — OpenAI doesn't bill cache writes separately).
- Replace `cost = compute_cost(...)` with `cost = compute_full_cost(self._spec.model_id, usage, searches)`. `searches` is already counted earlier.

### 5. Metrics — `src/dual_research/persistence/metrics.py`

- `CallRecord` gains `cache_write_5m_tokens: int = 0`, `cache_write_1h_tokens: int = 0` (preserving `cache_write_tokens` for back-compat).
- Add `searches: int = 0` and `search_cost: float = 0.0` to `CallRecord` so the breakdown is preserved in metrics.json (today it's lost — only the merged total survives).
- `Metrics.record` reads the new fields off `result.usage` and `result.extras["searches"]` + recomputes `search_cost` via pricing.
- `totals_by_agent` adds `searches` and `search_cost` keys per bucket. Existing `cost_usd` per bucket is the full cost (since D6).
- New `Metrics.load(path)` classmethod:
  ```python
  @classmethod
  def load(cls, path: Path) -> "Metrics":
      payload = json.loads(path.read_text(encoding="utf-8"))
      calls = [CallRecord(**c) for c in payload.get("calls", [])]
      started_at = payload.get("started_at") or datetime.now(timezone.utc).isoformat()
      ended_at = payload.get("ended_at")
      m = cls(calls=calls, started_at=started_at)
      m.ended_at = ended_at
      return m
  ```
  Tolerant of missing new fields (defaults applied by dataclass).
- New `Metrics.load_or_new(path)` classmethod — returns `load(path)` if file exists and parses, else `cls()`.

### 6. Orchestrator — `src/dual_research/orchestrator/run.py`

- Line 110: `metrics = Metrics()` → `metrics = Metrics.load_or_new(session.metrics_path)`.
- Line 270 area: keep `metrics.total_cost_usd()` as the source for `RunCompleted.total_cost_usd`. No other change here — D2 handles the rest.

### 7. Events — `src/dual_research/events/types.py`

- `TurnEnded` gains:
  ```python
  cache_write_5m_tokens: int = 0
  cache_write_1h_tokens: int = 0
  search_cost: float = 0.0   # USD, broken out from cost_usd
  ```
  `cost_usd` semantics change: now full cost (tokens + searches). The field is the same name; no consumer-side rename, but the value is bigger for runs with searches or 1h cache writes.
- No change to `RunCompleted` shape.
- `CostUpdate.total_usd` and `by_agent` semantics: full cost (matches `cost_usd` everywhere else).

### 8. Orchestrator call wrapper — `src/dual_research/orchestrator/_call.py`

- Pull the new fields from `result.usage` and pass to `TurnEnded(...)` constructor and `transcript.write(...)`.
- Compute `search_cost` from `(result.extras or {}).get("searches", 0)` and the model's per-search rate via `compute_search_cost(result.model_id, searches)`; attach to the event.
- `metrics.record(...)` keeps doing what it does — `CallRecord` now stores the breakdown.

### 9. Aggregator — `src/dual_research/ui/aggregator.py`

- `_empty_run` (around line 200): swap the priority. Now:
  ```python
  cost = _sum_transcript_cost(session_dir / "transcript.jsonl")
  if cost == 0.0:
      metrics = _read_metrics(session_dir / "metrics.json")
      cost = float(metrics.get("total_cost_usd", 0.0)) if metrics else 0.0
  ```
  Transcript is primary (D3); metrics.json is the cold-start fallback for runs that haven't emitted any turn yet.
- `_on_turn_ended`: `cost = float(event.get("cost_usd", 0.0))`. Trust the event's full cost (D9).
- Compute and store on `TurnTokenUsage`:
  ```python
  search_cost = compute_search_cost(turn_model_id, searches)
  token_cost = max(0.0, cost - search_cost)
  ```
  Both fields land on the turn record. `search_cost` already exists per spec 0031 — `token_cost` is new (see §10).
- `_sum_transcript_cost`: no logic change. Per-event `cost_usd` is now full cost, so the sum is naturally full cost.

### 10. Models — `src/dual_research/ui/models.py`

- `TurnTokenUsage` gains `token_cost: float = 0.0` (the "of which is tokens" breakdown). `cost` keeps its meaning of "total per-turn cost" (now matches transcript). `search_cost` keeps its meaning.
- Wire-shape camelCase: `tokenCost`, `searchCost`, `cost`.
- `RunListRow.cost` semantics: full cost. No field rename.

### 11. UI server — `src/dual_research/ui/server.py`

- `/api/runs` row: `cost = float(r.get("total_cost_usd") or 0.0)` (unchanged code; values just got bigger).
- The Supabase reader that returns `runs.metrics` JSONB: no schema change required — D12.

### 12. Remote push — `src/dual_research/persistence/remote.py`

- `_build_run_row`: pick `total_cost_usd` from the *recomputed* metrics.json (D11 guarantees it's current). Order of fallbacks unchanged. No schema migration.

### 13. CLI — `src/dual_research/cli.py`

- Line 346 area: print `total cost: ${result.total_cost_usd:.4f}` (unchanged code; value is now full cost). Add a parenthetical breakdown line when search cost > 0:
  ```
  total cost: $16.6537  (tokens $15.2537 · web search $1.4000)
  ```
- New subcommand wiring (D10): `dual-research recompute-costs [...]`. Implementation lives in a new module `src/dual_research/audit/recompute.py` so the CLI file stays thin.

### 14. Backfill — `src/dual_research/audit/recompute.py` (new)

- Public entry point:
  ```python
  def recompute_run(session_dir: Path, *, push: SupabaseCredentials | None = None) -> RecomputeReport
  ```
- Reads `transcript.jsonl`. For each `turn_ended` event:
  - Reconstruct `TokenUsage` from `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_5m_tokens` (or `cache_write_tokens` if 5m is absent — treat as 5m, D5), `cache_write_1h_tokens`.
  - Read `searches` and `model_id` from the event.
  - Call `compute_full_cost(model_id, usage, searches)`.
  - Compare to `event["cost_usd"]`.
- Reconstruct `Metrics` from scratch, write a fresh `metrics.json`.
- If `push is not None`, call the existing remote-push pipeline.
- Return a structured diff: `{ "run_id": ..., "old_total": ..., "new_total": ..., "delta": ..., "per_call_diffs": [...] }`.
- CLI wrapper: `dual-research recompute-costs --run RUN_ID` or `--all` (walks `runs/` directory).

### 15. UI — `src/dual_research/ui/static/run-detail.jsx`

- Header `<CostBadge>`: tooltip becomes `"$X.XXXX (tokens $Y.YYYY · web search $Z.ZZZZ)"` when `searchCost > 0` on any agent; otherwise unchanged.
- Consumption tab expanded card: relabel the existing "tool cost" line to **"of which web search:"** so it's clear the headline `cost` already includes it. Remove the implicit "this is on top of token cost" reading.
- Footer budget meter: no change to bar split (already by-agent). Tooltip note added: hovering the total shows the same breakdown.
- Timeline turn-row inline stat (`run-detail.jsx:2063`): tooltip on the cost text gains the `(tokens $X · web search $Y)` breakdown when applicable.
- Run-list row: no change. The cost column shows full cost; we don't surface the breakdown on the list page.

### 16. UI — `src/dual_research/ui/static/run-list.jsx`

- No code change. The header's `∑ cost {fmt.cost(totalCost)}` and the per-row cost column both consume the full cost from `/api/runs` which is now correct. Note in the spec: existing rows' values *will increase* once D10 backfills.

### 17. Versioning + release notes

- `pyproject.toml`, `src/dual_research/__init__.py`: 0.35.0 → 0.37.0 (0.36.0 reserved for a parallel-session spec — explicit per the audit briefing).
- `CHANGELOG.md`: `## [0.37.0] — YYYY-MM-DD` under `### Fixed`, with three bullets matching the three root causes and one bullet for the backfill tool.
- A short callout in the "What's New" / version-notes page on the hosted UI: "Run totals now include web-search fees and 1h-cache writes; older runs were re-priced — costs you see today will be higher than before for runs that used those features."

### 18. Tests

- `tests/agents/test_pricing.py`:
  - `compute_token_cost` returns the same number as the pre-rename `compute_cost` did for usages with no 1h cache writes (regression guard).
  - 1h cache write priced at 2× input rate; 5m at 1.25× input rate (constants check).
  - `compute_full_cost` = token cost + search cost.
- `tests/agents/test_pricing.py` (new test): `compute_full_cost(sonnet, usage_with_5m_only, n=3)` matches an expected total to 6 decimal places.
- `tests/agents/test_anthropic_agent.py` (new test or extend): mock a response whose `usage.cache_creation` carries `(ephemeral_5m_input_tokens=100, ephemeral_1h_input_tokens=200)`; assert `result.usage.cache_write_5m_tokens == 100`, `cache_write_1h_tokens == 200`, `cache_write_tokens == 300`, and `result.cost_usd` matches the full cost.
- `tests/agents/test_anthropic_agent.py`: response with `cache_creation = None` and `cache_creation_input_tokens = 50` → all 50 land in `cache_write_5m_tokens`, `cache_write_1h_tokens == 0` (fallback path).
- `tests/persistence/test_metrics.py`:
  - `Metrics.load_or_new` returns an empty `Metrics` when file is missing.
  - `Metrics.load_or_new` rehydrates calls from an existing `metrics.json`; appending a new `record(...)` produces a 2-call file on next save.
  - `Metrics.load_or_new` tolerates an old-shape `metrics.json` (missing `cache_write_5m_tokens` / `cache_write_1h_tokens` / `searches` / `search_cost` on calls).
- `tests/orchestrator/test_run.py` (or equivalent): integration-style — run a session, kill, resume, assert final `metrics.json.total_cost_usd` equals the sum of *all* per-turn costs across both sessions.
- `tests/ui/test_aggregator_token_tracking.py`:
  - Transcript-first preference: when `metrics.json.total_cost_usd = 0` but transcript has turns, run snapshot uses transcript.
  - `TurnTokenUsage.token_cost + search_cost == cost` for every turn (invariant).
- `tests/ui/test_server.py`: `phaseTokenUsage` entries now expose `tokenCost`, `searchCost`, and `cost` with the invariant above.
- `tests/audit/test_recompute.py` (new module):
  - Recompute on the partner-vetting fixture (vendored as a small synthetic transcript): old `$2.45` → new `$16.65` ± rounding.
  - Idempotent: running twice produces the same `metrics.json`.
  - `--all` walks the directory.
- `tests/agents/test_pricing.py`: pricing snapshot table — `Sonnet 4.6` row has `cache_write_5m_per_mtok=3.75`, `cache_write_1h_per_mtok=6.00`.

## Out of scope

- **OpenAI organisation-level reconciliation against `/v1/organization/costs`.**
  The briefing recommends a provider-side reconciliation harness; it
  remains a good idea but is a separate spec. This spec gets internal
  numbers honest; provider-side cross-check is the next layer.
- **Reasoning tokens** (`output_tokens_details.reasoning_tokens` on
  OpenAI). Already folded into `output_tokens` by the API for billing
  purposes; capturing the breakdown is observability, not correctness.
  Defer.
- **Per-tool generalised "tool cost" field.** Web search is the only
  per-request tool we currently invoke; structuring for future tools
  (code execution, computer use, etc.) is premature. `search_cost`
  stays a named field; later tools can each get their own.
- **Anthropic Managed Agents runtime billing.** We don't use it.
- **Schema migration on the Supabase `runs` table.** D12 — no new
  columns. If the team later wants `search_cost_usd`, `token_cost_usd`,
  `cache_write_1h_tokens` materialised, that's a separate spec; the
  raw breakdown is queryable today via the `metrics` JSONB column.
- **UI: showing search cost as a separate column on the run list.**
  D15/D16 keep the list compact. Detail view carries the breakdown.
- **Re-pricing past runs that pre-date the `searches` field on
  `TurnEnded`** (anything before spec 0031 merged). Those runs will
  recompute their token cost honestly under the new TTL split but
  show `searches = 0` and `search_cost = 0`. Acceptable — the prior
  number was already token-only.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; this spec adds at least 12 new tests across pricing, agents, metrics, orchestrator, aggregator, server, and audit modules.
- [ ] Manual: kill an in-progress run after phase 1, resume it, confirm `metrics.json.total_cost_usd` reflects *all* phases at the end (not just the resume window).
- [ ] Manual: trigger a fresh prod-tier run that uses web search and 1h cache. After it completes, verify:
  - CLI prints the breakdown line (`(tokens $X · web search $Y)`).
  - Hosted UI header `CostBadge` tooltip shows the breakdown.
  - Run-list cost column matches detail-page header cost.
  - Footer budget meter total matches detail-page header cost.
  - Consumption tab expanded card's "of which web search" line + token cost equals the row's total cost.
- [ ] Run `dual-research recompute-costs --run 20260516-035048-partner-vetting-arch-critique`; confirm:
  - Old `metrics.json.total_cost_usd ≈ $2.45`, new value `≈ $9.86 ± $0.10`. The gap to the provider dashboards' "≈$12" is the 1h-cache underbilling, which the recompute tool can't retroactively fix on old transcripts (they only carry the aggregate `cache_write_tokens`, no per-TTL split). The deduped transcript baseline is $8.78; +$1.08 search-fee fold-in = $9.86.
  - Per-call diff report lists each unique (deduped by `label`) turn with its old/new cost.
  - Running it again produces an empty diff (idempotent); `metrics.json.pre-0039.bak` exists with the original $2.45 value.
- [ ] Run `dual-research recompute-costs --all --push`; verify the Supabase `runs.total_cost_usd` column for each run matches the new metrics.json.
- [ ] Refresh hosted UI; run list `∑ cost` header total equals the sum of the run-list rows; both reflect the new totals.
- [ ] `--push-while-running` on a fresh run: hosted UI total at completion equals local CLI total.
- [ ] Live tail of the cost ticker shows monotonically increasing total across all turns of a single session.

## Risks

- **The headline number gets bigger.** Existing user mental model is
  calibrated to today's (undercounted) totals. Mitigation: D17's
  version-notes callout + a one-line note on the run-list header
  ("totals re-priced 2026-05-XX") for the week after release.
- **Backfill is irreversible per-run.** Once `metrics.json` is
  rewritten, there's no path back to the old number without re-reading
  the transcript under the old pricing. Mitigation: the recompute tool
  copies the old `metrics.json` to `metrics.json.pre-0039.bak` before
  rewriting (skipped if `.bak` already exists, so re-running the tool
  preserves the original-original). Acceptable size overhead (small
  file).
- **TokenUsage shape change has wide reach.** Many tests construct
  `TokenUsage(...)` directly. D5's "keep `cache_write_tokens` as a
  field" keeps the JSON shape stable on the transcript, but Python
  callers may need updating. Mitigation: dataclass keyword-only by
  convention in this repo; if mypy or grep finds positional callers,
  fix them as part of this spec.
- **Resume rehydrate could load a corrupted `metrics.json`.** D2's
  `load_or_new` catches `JSONDecodeError` and falls through to an
  empty Metrics, logging a warning. The transcript-primary D3 path
  then still produces correct UI numbers. Persistence stays best-effort
  for metrics.json; transcript is the truth.
- **Pricing rates drift.** Same risk noted in spec 0031 — addressed
  the same way: rates live in one dict, one-line edits when vendors
  update.
- **Per-TTL fields absent in the Anthropic response** (e.g. older API
  version, beta rejection). D7's fallback path keeps cost honest at
  the 5m rate, which is the same behaviour as today's bug — no
  regression, just no improvement on those calls. Logged as a
  one-line warning at agent level so it's discoverable.
- **The Consumption tab's previously-shown "tool cost" number is no
  longer a separate add-on.** Users who learned to "add it in their
  head" will double-count if we don't rename clearly. Mitigation: D15
  relabels the line to "of which web search" — language that signals
  it's a breakdown, not a separate charge.

## Open questions

- Should `search_cost` and `token_cost` also surface in the run-list
  CSV / export endpoint? Currently no export exists. If one lands
  later, this spec's CallRecord fields are already structured for it.
- Should the recompute tool be auto-triggered on every release that
  changes pricing rates? Today it's manual. A `dual-research version`
  command that records the pricing-snapshot version in `metrics.json`
  (e.g. `"pricing_version": "2026-05-16"`) would make this answerable
  per run. Probably a follow-up spec rather than in-scope here.
- Whether to fail-loud on Anthropic responses missing `cache_creation`
  when the request had `ttl: "1h"`. Today we'd silently 5m-price them.
  Recommendation: warn, not fail; capture the model_id + request_id
  in logs so we can audit if it ever happens.
