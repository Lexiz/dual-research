# Handover — Audit gaps + proposed next three specs (0047 / 0048 / 0049)

**Date:** 2026-05-17
**Branch:** `main` (deployed)
**Hosted:** [`dual-research-alex.fly.dev/api/health`](https://dual-research-alex.fly.dev/api/health) → `{"version":"0.44.0","backend":"supabase"}`
**Specs shipped to date:** 0038 → 0046
**Last commit:** `2e63978 Spec 0046 — flip front-matter to merged + PR link`
**Tests:** 655+ green
**Working tree:** clean

## What this handover is

A thread-spanning audit identified **eight remaining gaps** across two sessions worth of work (specs 0038 → 0046). All eight are documented below with file paths, reproducers, and fix shapes. They're grouped into **three proposed specs** (0047 / 0048 / 0049) — small enough each to review independently, ordered so the cheapest one ships first.

The audit is the source of truth for what's missing; the prior handovers cover what landed:

- [`handoffs/2026-05-16-specs-0038-0041-handover.md`](2026-05-16-specs-0038-0041-handover.md) — specs 0038–0041 (UI surfacing, cost integrity, critique rework).
- [`handoffs/2026-05-17-specs-0042-0046-handover.md`](2026-05-17-specs-0042-0046-handover.md) — specs 0042–0046 (data integrity, ledger, badges, shell, critique design unification).

## What's finished

| Spec | PR | Version | What it shipped |
|---|---|---|---|
| 0038 | [#39](https://github.com/Lexiz/dual-research/pull/39) | 0.34.0 → 0.35.0 | Web search audit UI; 🔎 N chip; Web Search tab on modals; RunSearchSummary header chip; hallucination warnings in 3 places; GPT pill alignment fix; `?include=summary` server param. |
| 0039 | [#40](https://github.com/Lexiz/dual-research/pull/40) | 0.35.0 → 0.37.0 | Cost-pipeline integrity. `Metrics.load_or_new` rehydrate on resume; 1h cache TTL pricing split (`cache_write_5m_per_mtok` + `cache_write_1h_per_mtok`); web search fees folded into headline `cost_usd`; transcript dedup by label (later-wins); `recompute-costs` CLI; `metrics.json.pre-0039.bak` backup. |
| 0040 | [#41](https://github.com/Lexiz/dual-research/pull/41) | 0.37.0 → 0.38.0 | Phase 4 questions regex fix; compact critique cards click-to-expand; cross-link click-to-highlight for Q + D; `↩ N` annotation; `∑ Summary` tab; tabs left-aligned. |
| 0041 | [#42](https://github.com/Lexiz/dual-research/pull/42) | 0.38.0 → 0.39.0 | Parser kind split (issue / comment / question); `useLiveRun` retry-before-error; card body 70-char truncation; sentiment composer with overall-sentiment lead. |
| 0042 | [#43](https://github.com/Lexiz/dual-research/pull/43) | 0.39.0 → 0.40.0 | Phase 1 plan-draft parser coverage; `kind="claim"`; chips read parsed items not self-counters; right-pane "no anchored items" empty fixed (snake/camel key mismatch); `currentDraftPath` always populated; markdown setext heading bug; `totalIntroduced` phase-scoped. |
| 0043 | [#44](https://github.com/Lexiz/dual-research/pull/44) | 0.40.0 → 0.41.0 | Cross-round ledger (`LedgerEntry/State/Transition/Drift`); standing-items as structured input; conservative convergence (bilateral self-counter + ledger agreement); `LedgerDriftChip`. Surfaces 15 ghosted questions on partner-vetting. |
| 0044 | [#45](https://github.com/Lexiz/dual-research/pull/45) | 0.41.0 → 0.42.0 | Drop redundant phase status pills; `✓ agreed` only on final converged turn; `+raised −resolved` per-kind chips; side-by-side modal phase-aware doc tabs; right-pane action-specific empty-states; Phase 1 modal item strip; sentiment composer reads ledger. |
| 0045 | [#46](https://github.com/Lexiz/dual-research/pull/46) | 0.42.0 → 0.43.0 | Canonical tab order `[Content \| Input \| Web Search \| Sources \| Files]` across all full-view modals; empty tabs hidden; Input full-view drops "not used" rows; brief renamed "User prompt: Brief" floated to top; side-by-side panes equal-width; model pills equal-width. |
| 0046 | [#47](https://github.com/Lexiz/dual-research/pull/47) | 0.43.0 → 0.44.0 | Critique header restructured (buttons left, counts right); per-phase context-aware filter chips; human-readable card headlines; `GhostedAnnotation` wired; Summary tab per-round × per-model breakdown; Consumption tab inline expand; unified `PaneButton`. |

## What's not finished — eight gaps

Each entry: file paths · why it's broken · suggested fix shape.

### Real defects on `main`

#### F1 — Drafter-null run-detail crash
- **Symptom:** Run-detail page renders blank with React error `Cannot read properties of null (reading 'name')` for runs that have `drafter=null` + `status=completed`.
- **Reproducer:** `runs/20260515-111151-asyncio-vs-goroutines/` (and 4 other local runs with the same shape — anything killed before Phase 3 but marked complete).
- **Root cause:** `buildLiveTimeline` in [`live-data.jsx:531-537`](../src/dual_research/ui/static/live-data.jsx) adds `doc-final` with `agent: run.drafter` when `status==='completed'`. When `drafter` is null, `agent === null`, so `meta = item.agent ? AGENT_META[item.agent] : null` produces `meta = null` in `ArtifactCard`. Then `ArtifactHeader`'s `kind === 'doc'` branch ([`run-detail.jsx:~2200`](../src/dual_research/ui/static/run-detail.jsx)) does `<span>by {meta.name}</span>` unguarded. `kind === 'doc-live'` branch (~10 lines below) has the same issue.
- **Fix shape:** Two-char fix — `meta?.name` (or `meta && <span>by {meta.name}</span>`) on the 4 unguarded accesses. Could also drop the `doc-final` item entirely when `drafter` is null (cleaner semantically). Pick one.
- **Test:** Synthetic run with `drafter=null`, status='completed' → `load_run_snapshot` succeeds + frontend renders without throwing.

#### F2 / F6 — Post-finalize `'NoneType' object has no attribute 'rounds'`
- **Symptom:** Partner-vetting transcript has a `critical · halted` `ORCHESTRATOR_PANIC` error at 2026-05-16T09:21:55Z with `Error type: AttributeError · Message: 'NoneType' object has no attribute 'rounds'` recorded AFTER `phase: done`.
- **Reproducer:** Look in `runs/20260516-035048-partner-vetting-arch-critique/transcript.jsonl` for `event: run_failed`. The relevant fields: `code: ORCHESTRATOR_PANIC`, `phase: done`, `agent: null`, `where: orchestrator`.
- **Root cause guess:** A `.rounds` attribute is being read on a None `Phase2Outcome` (most likely) during finalize. Spec 0036 added None-guards in `emit_final` / `confidence_tag` / `render_metadata_header`; at least one finalize path still derefs unguarded. Likely candidates: `src/dual_research/orchestrator/finalize.py`, `src/dual_research/orchestrator/emit_final.py`, or the metadata-header rendering in `finalize.py`.
- **Fix shape:** Audit the finalize path for any `phase{N}_outcome.rounds` access without a None-guard. Add the guard. Best discovered with a synthetic run where `phase2_outcome=None` was forced by an early `phase4` failure.
- **Test:** Synthetic resume scenario where Phase 2 outcome is None going into `emit_final` → no crash.

#### F5 — Phase 4 sibling-key collapse on Consumption tab
- **Symptom:** Runs with parse-error recovery emit `phase4-r1-claude` AND `phase4-r1-claude-repair` (etc.) as separate `turn_ended` events with the SAME label after dedup-by-label. Consumption tab shows only one card per `(phase, round, agent)`; the per-card detail under-reports.
- **Reproducer:** `runs/20260516-035048-partner-vetting-arch-critique/` — phase 4 had 3 INVALID_TURN_FORMAT recoveries. Consumption tab shows 5 cards (one per round) but each card's per-piece detail misses the repair-turn input.
- **Root cause:** Per-turn key derivation `phase{N}_round{R}_{agent}` in [`aggregator.py::_on_turn_ended`](../src/dual_research/ui/aggregator.py) — collides on `-repair` siblings. The transcript-dedup logic (later-wins by label, from spec 0039) intentionally collapses cost; this is correct for the agent-level rollup but wrong for the per-card display.
- **Fix shape:** Two options, pick one:
  1. **Append a repair-N suffix to the per-turn key** when the label has `-repair-N` — e.g. `phase4_round1_claude_repair1`. Aggregator + frontend Consumption tab + Summary tab all need to handle the new key shape.
  2. **Accept the collapse on Consumption tab** and explicitly add a "repair turn" indicator on the card. Cheaper code-wise but less informative.
- **Test:** Synthetic transcript with a `phase4-r1-claude` followed by `phase4-r1-claude-repair-1` → Consumption tab shows both (option 1) or shows one with a "repair x1" indicator (option 2).

### Cost work (open)

#### C1 / F3 / F4 — Cost reconciliation (you picked option 3 by default; here are the real options)
- **Context:** During spec 0039, I offered three options to close the ~$2 gap on partner-vetting (recomputed $9.86 vs invoice ~$12). You didn't pick; we shipped option 3.
- **Status:** Partner-vetting's 1h-cache underbilling is permanently lost on the historical run. New runs going forward record the per-TTL split exactly. The gap on past runs is only addressable via one of:
  1. **Reconciliation harness** (preferred). Pull Anthropic `/v1/organizations/cost_report` + OpenAI `/v1/organization/costs` for a run's date range. Compare to local recomputed metrics. Surface delta. Needs admin API keys for both providers. Daily-aggregate level only — can't go per-call.
  2. **`--assume-1h-cache-writes` flag on `recompute-costs`.** Re-price the aggregate `cache_write_tokens` at the 1h rate (2× input) instead of 5m (1.25× input). Defensible because the agent always requested `ttl: "1h"`; risk is overcounting if Anthropic silently fell back to 5m on edge cases.
  3. **Accept the loss.** Status quo. Status: shipped by default.
- **Fix shape:** Option 1 — new `src/dual_research/audit/reconcile.py` + `dual-research reconcile-costs [--from DATE] [--to DATE] [--api-key-anthropic KEY] [--api-key-openai KEY]` CLI. Outputs a CSV-or-JSON delta report.

#### F8 — `pricing_version` snapshot
- **Symptom:** `metrics.json` records cost numbers but doesn't say which pricing-table version was applied. A future rate change can't recompute "what would the bill have been under today's rates" honestly.
- **Root cause:** Out of scope from spec 0039 §10.
- **Fix shape:** One-line addition. `pricing.py` exports `PRICING_VERSION = "2026-05-16"` (bump when rates change). `Metrics.to_json` includes `"pricing_version": PRICING_VERSION` in the payload. `audit/recompute.py` overrides on backfill. ~5 lines of code.
- **Test:** `metrics.to_json` contains the version key. `recompute-costs` overwrites it.

### Audit UI extensions (deferred from spec 0038 / 0036)

#### F7 — `[V]` / `[U]` citation tag inline rendering
- **Symptom:** The model's markdown output uses `[V]N` (verified) and `[U]N` (unverified) tags for citations, but they render as plain text. No cross-link to the Web Search tab's `ConsultedSourceCard` rows.
- **Reference:** Spec 0038 D18 deferred this explicitly: "Out of scope — the spec 0036 cross-reference is already structural (`matched_query_id` on each Citation); rendering anchored cross-references inside the rendered markdown would require a markdown-renderer hook and is its own surface."
- **Fix shape:** Markdown component post-render pass:
  1. Walk the rendered DOM after marked.parse.
  2. Find text nodes matching `[V]N` / `[U]N`.
  3. Wrap each in a `<span class="citation-tag" data-citation-n="N">[V]N</span>`.
  4. Click handler: find the Web Search tab's `ConsultedSourceCard` with citation `N`, scroll-and-flash it.
  5. Hover tooltip with the citation's title + URL.
- **Touch:** [`src/dual_research/ui/static/shared.jsx::Markdown`](../src/dual_research/ui/static/shared.jsx), `run-detail.jsx::WebSearchTabContent` (add scroll target IDs).
- **Test:** Manual — open a Phase 4 turn, hover a `[V]3` tag, click → Web Search tab opens scrolled to citation 3.

#### F10 — Server-side re-fetch of cited URLs
- **Symptom:** OpenAI returns URL-only consulted sources (no snippet text). Anthropic's `cited_text` is good when present but URLs can rot. The Web Search tab shows blank cited_text rows for OpenAI citations and stale data for Anthropic ones where the source has moved.
- **Reference:** Spec 0036 explicitly deferred: "Would close OpenAI snippet gap + hedge link rot, but introduces network/extractor/ToS surfaces. Wait until the gap bites in real reviews." Spec 0041 reiterated as out of scope.
- **Fix shape:** Substantial — needs:
  - `src/dual_research/audit/refetch.py` — HTTP fetcher with timeout, retry, user-agent. Honour `robots.txt` and a small allowlist of well-known content domains (avoid ToS-restricted ones unless explicitly opted in).
  - Content extractor: trafilatura or readability-lxml to pull main content. Cache extracted text per URL hash.
  - Storage: per-URL cache as `audit/refetched/<url-hash>.json` (or Supabase table if hosted).
  - New endpoint: `GET /api/runs/<id>/searches/<turn_key>/refetch?source_id=N` — triggers a fetch + returns the extracted snippet.
  - UI: `ConsultedSourceCard` shows a "fetch snippet" button when `cited_text` is null; clicking triggers fetch + populates the card.
  - Background job (optional): on-write fetch for new audit bundles so the UI never waits.
  - Error handling: 403, paywall, JS-rendered (Cloudflare check), ToS exclusions.
  - ~2–3 days of work; nontrivial surface.

## What's still open — quick summary

| ID | Item | Surface | Effort |
|---|---|---|---|
| F1 | Drafter-null crash | Frontend | ~30 min |
| F2/F6 | Post-finalize NoneType | Orchestrator finalize path | ~1 hour |
| F5 | Phase 4 sibling-key collapse | Aggregator + Consumption UI | ~half day |
| C1 | Cost reconciliation harness | Pricing + new CLI | ~1–2 days |
| F8 | `pricing_version` snapshot | Pricing + metrics persistence | ~30 min |
| F7 | `[V]`/`[U]` inline rendering | Markdown component + Web Search tab | ~half day |
| F10 | Server-side URL re-fetch | New audit module + endpoint + UI | ~2–3 days |

## Proposed grouping — three specs

### Spec 0047 — Run-detail resilience + Phase 4 sibling-key fix
**Label:** `bug` · **Version bump:** PATCH (or MINOR if F5 changes the per-turn key shape on the wire) · **Effort:** ~half a day

**Items:** F1 + F2/F6 + F5.

**Why grouped:** All three are defensive fixes on existing runs. Different files (frontend / orchestrator / aggregator) but the testing motion is identical — open the partner-vetting run + any `drafter=null` run, verify nothing crashes, verify Phase 4 Consumption shows all turns.

**Suggested design decisions:**
- D1: `ArtifactHeader.kind === 'doc' / 'doc-live'` branches use `meta?.name` (or branch entirely on `meta != null`).
- D2: `buildLiveTimeline` only emits `doc-final` when `drafter != null` (defensive — the protocol shouldn't produce drafter-null + completed in normal flow, but historical runs do).
- D3: Audit `src/dual_research/orchestrator/finalize.py` for unguarded `phase{N}_outcome.rounds` (or similar attribute) access. Add None-guards.
- D4: New per-turn key derivation handles `-repair-N` siblings — option 1 (suffix) or option 2 (indicator on the card). **Open question; spec author picks.**
- D5: Tests for all three: synthetic transcript with `drafter=null + completed`, synthetic resume with `phase2_outcome=None`, synthetic transcript with sibling `-repair-1` events.

**Files touched:**
- `src/dual_research/ui/static/run-detail.jsx` (4 unguarded accesses)
- `src/dual_research/ui/static/live-data.jsx` (buildLiveTimeline doc-final emission)
- `src/dual_research/orchestrator/finalize.py` (None-guards)
- `src/dual_research/ui/aggregator.py` (per-turn key, if option 1)
- Tests in `tests/orchestrator/`, `tests/ui/`

**Risk:** Low. All three items are defensive; no behaviour change on the happy path.

---

### Spec 0048 — Cost reconciliation + audit-time pricing snapshot
**Label:** `new-feature` · **Version bump:** MINOR · **Effort:** ~1–2 days

**Items:** C1 (pick: reconciliation harness OR `--assume-1h-cache-writes` flag OR accept-and-close) + F8 (`pricing_version` snapshot).

**Why grouped:** Same code surface (`pricing.py`, `audit/recompute.py`, optionally new `audit/reconcile.py`). F8 is the prerequisite for "rerun under different rates" so they pair naturally.

**Suggested design decisions:**
- D1: New `PRICING_VERSION = "YYYY-MM-DD"` constant in `pricing.py`. Bump when rates change.
- D2: `Metrics.to_json` includes `"pricing_version": PRICING_VERSION`.
- D3: `dual-research reconcile-costs [--from DATE] [--to DATE] [--anthropic-key KEY] [--openai-key KEY] [--runs-dir PATH]` CLI. Pulls daily aggregates from both providers, compares to local recomputed totals over the same date range, outputs a delta report (per-day + grand total).
- D4: Optional `--assume-1h-cache-writes` flag on `recompute-costs` (Option B). Re-prices the aggregate `cache_write_tokens` at the 1h rate. Defensible; document the risk.
- D5: Reconciliation report format: human-readable text by default, `--format json` for machine consumption.
- D6: New `src/dual_research/audit/reconcile.py` houses the API clients + comparison logic.
- D7: Tests: mocked Anthropic + OpenAI responses; reconciliation produces correct deltas; pricing_version round-trips.

**Files touched:**
- `src/dual_research/agents/pricing.py` (PRICING_VERSION constant)
- `src/dual_research/persistence/metrics.py` (include in payload)
- `src/dual_research/audit/recompute.py` (preserve / overwrite version)
- `src/dual_research/audit/reconcile.py` **(new)**
- `src/dual_research/cli.py` (new subcommand)
- Tests in `tests/audit/`, `tests/agents/`

**Risk:** Medium. Needs admin API keys at runtime; mock cleanly in tests so CI doesn't depend on live API.

**Open question for spec author:** decide between C1 options 1 / 2 / 3. Recommended: option 1 (full harness) since it's the most useful long-term and is what gives confidence the recompute matches reality.

---

### Spec 0049 — Citation inline rendering + server-side URL re-fetch
**Label:** `new-feature` · **Version bump:** MINOR · **Effort:** ~2–3 days

**Items:** F7 + F10.

**Why grouped:** Both touch the audit-UI surface. F7 is the natural anchor in markdown; F10 populates the snippet that anchor reveals (closing OpenAI's snippet gap). Internally cohesive.

**Suggested design decisions:**
- D1: `Markdown` component post-render pass that wraps `[V]N` / `[U]N` text nodes in clickable spans with `data-citation-n`. Hover tooltip carries title + URL.
- D2: Click handler scrolls the parent modal's Web Search tab to the matching `ConsultedSourceCard` and applies `scrollAndFlash`.
- D3: New `src/dual_research/audit/refetch.py` — HTTP fetcher with timeout, retry, user-agent. Honours robots.txt.
- D4: Allowlist of well-known content domains by default; ToS-restricted domains explicitly opted in via config.
- D5: Content extraction via trafilatura (or readability-lxml). Cache extracted text per URL hash under `audit/refetched/<sha256>.json`.
- D6: Hosted mode: cache lives in a new Supabase table `refetched_sources` keyed by `(url_hash)`.
- D7: New endpoint `GET /api/runs/<id>/searches/<turn_key>/refetch?source_id=N` — returns cached snippet OR triggers fresh fetch (with reasonable timeout).
- D8: UI: `ConsultedSourceCard` shows "fetch snippet" button when `cited_text` is null. Click triggers refetch endpoint; populates card on success; shows error state on 403/paywall/ToS-block.
- D9: Optional background pre-fetch: on `TurnSearches` event, queue refetch for citations with null `cited_text`. **Cost note:** opt-in via env var; off by default.
- D10: Tests: mocked HTTP responses for fetcher; post-render DOM walk produces expected `data-citation-n` spans; click handler scrolls correctly.

**Files touched:**
- `src/dual_research/ui/static/shared.jsx::Markdown` (post-render pass for tags)
- `src/dual_research/ui/static/run-detail.jsx::WebSearchTabContent` (scroll-target IDs; refetch button on cards)
- `src/dual_research/audit/refetch.py` **(new)**
- `src/dual_research/ui/server.py` (new endpoint)
- `src/dual_research/persistence/` (if Supabase cache table)
- Tests in `tests/audit/`, `tests/ui/`

**Risk:** Highest of the three. F10 has real network failure surfaces (403 / paywall / JS-rendered / ToS) + storage growth + potential ToS exclusions. Consider splitting into 0049 (F7 only) + 0050 (F10 only) if you want smaller PRs.

## Suggested order

1. **Spec 0047 first** — half a day, no dependencies, lowest risk, unblocks viewing the 5 broken local runs.
2. **Spec 0048 second** — closes the partner-vetting cost gap question definitively. Independent of 0047. Needs Anthropic + OpenAI admin API keys at deploy time.
3. **Spec 0049 third** — largest surface; safe to defer until 0047 + 0048 land and stabilise. Could split F10 into its own 0050 if you want even smaller PRs.

## How to continue — workflow checklist

Per [`CONTRIBUTING.md`](../CONTRIBUTING.md):

```
spec → branch → implement → tests + preview-verify → version-bump →
CHANGELOG + VERSION_NOTES → PR (admin squash-merge) → fly deploy → STOP
```

Per-spec:

1. Copy [`specs/TEMPLATE.md`](../specs/TEMPLATE.md) → `specs/NNNN-<slug>.md`. Front-matter: `status: in-progress`, `target-version`, `created`, `pr: ""`.
2. Branch: `spec/NNNN-<slug>`.
3. Implement; run `uv run pytest tests/ -q` (expect 655+ green).
4. Preview-verify via `.claude/launch.json`'s `dual-research-ui` config — load partner-vetting + any drafter-null run + a fresh-shape synthetic.
5. Version bump in `pyproject.toml` + `src/dual_research/__init__.py`.
6. CHANGELOG: move `[Unreleased]` to versioned heading.
7. `VERSION_NOTES` at top of `how-it-works.jsx` if user-visible.
8. Spec front-matter `status: merged` + `pr:` populated before final push.
9. `gh pr create --label "spec/<label>" --title "Spec NNNN — <title>" ...`
10. `gh pr merge <PR#> --admin --squash --delete-branch`
11. `fly deploy` + `curl https://dual-research-alex.fly.dev/api/health` — verify new version.
12. **STOP.** Pause before the next spec per memory entry `feedback_pause_between_specs.md`.

## Hard constraints

- **STOP after each spec deploys + `/api/health` reports the new version.** Don't auto-start the next one.
- **DO NOT delete `runs/20260516-035048-partner-vetting-arch-critique/`** — canonical fixture across all specs.
- **Permissions are pre-configured globally** for `git`/`gh`/`uv`/`fly`/`pytest`/etc. inside `/Users/alexlisitzky/dual-research`. If anything prompts, update `~/.claude/settings.json` before continuing.
- **Memory entries** (`feedback_pause_between_specs.md`, `feedback_low_reversal_just_decide.md`, `feedback_no_handoff_unless_asked.md`, `feedback_secrets_pragmatic.md`) apply.

## Coverage matrix (compact, full version in audit summary)

41 explicit requirements across this thread arc → **30 covered**, **1 partial** (issue-by-which-round drill-down, partly addressed in 0046 D5), **8 unfixed** (the items above). Three specs close the remaining 8 with the Notion-as-MCP item explicitly excluded.

## Quick sanity checklist when each spec deploys

- [ ] `uv run pytest tests/ -q` green (655+ baseline; expect 3–10 new tests per spec).
- [ ] Preview-verified on `localhost:6173` against partner-vetting + at least one drafter-null run.
- [ ] `pyproject.toml` + `__init__.py` version match each other and `/api/health`.
- [ ] CHANGELOG entry under the right heading (Fixed / Added).
- [ ] VERSION_NOTES entry at the top of `how-it-works.jsx` if user-visible.
- [ ] Spec front-matter `status: merged` + `pr:` populated.
- [ ] PR merged via `--admin --squash --delete-branch`.
- [ ] `fly deploy` clean exit; `curl /api/health` reports new version.
- [ ] Local `main` synced.

## Kickoff prompt (also included below for copy-paste)

```
Read handoffs/2026-05-17-gaps-and-next-three-specs.md — full state of the dual-research repo as of 2026-05-17 (0.44.0 shipped). It enumerates the 8 remaining gaps from a thread-spanning audit, groups them into 3 proposed specs (0047 / 0048 / 0049), and details each with files, design decisions, and test plans. Start with 0047 (the cheapest bug-fix pass: F1 drafter-null crash + F2 post-finalize NoneType + F5 Phase 4 sibling-key collapse). Permissions are pre-configured globally. cd /Users/alexlisitzky/dual-research and read it, that's it.
```
