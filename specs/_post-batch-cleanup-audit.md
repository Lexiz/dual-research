# Post-batch cleanup audit — specs 0140–0147

Generated: 2026-05-22
Final batch commit on main: b2bffd2 (Spec 0147 handover, v1.12.1)

## Summary

- Total deferred items: **24**
- Items requiring Supabase action: **1** (migration `0006_turn_prompt_pieces.sql` — SQL captured verbatim below; this is the ONLY Supabase action and YES, the SQL was quoted both in the spec 0145 handover and in the on-disk migration file)
- Items that can fold into one consolidation spec: **9** (consumption-card backend follow-ups D10–D14 + UI surface follow-ups D04/D16 + telemetry surface D03; rationale: same audit/aggregator boundary)
- Items that need separate specs: **5** (D02 Anthropic cache-engagement fix, D08 RequestEvidence op, D15 legacy-shim sunset / backfill, D17 search_N resolution tightening, D19 per-attachment rich previews — each has its own surface area + risk profile)
- Zero-code operational actions the user runs manually: **3** (D01 Supabase migration apply, D24 fly support ticket, D09 fresh-run smokes)

## Item table

| Id | Spec | Type | Title | Action required | Verbatim source |
|---|---|---|---|---|---|
| D01 | 0145 | supabase-sql | Apply migration `0006_turn_prompt_pieces.sql` to production Supabase | Paste SQL (below) into Supabase Dashboard → SQL editor. Idempotent (`IF NOT EXISTS`). Without it, fresh-run pushes will hit a "table does not exist" error on the `turn_prompt_pieces` upsert step | Spec 0145 handover §"Schema delta — migration 0006": "**Apply status**: NOT YET APPLIED to production Supabase. The push CLI references the table on every push, so applying the migration is a prerequisite for any new push to populate per-piece rows… consider an `if-table-exists` guard or apply the migration before the next live run." |
| D02 | 0143 | code-followup | Anthropic cache-engagement fix (cache_control silently rejected) | Fire a fresh run with `DUAL_RESEARCH_DEBUG_USAGE=1` to capture raw SDK usage payloads in `<session>/usage-debug.jsonl`, then diagnose env-side vs request-side and patch | Spec 0143 handover: "The instrumentation is the prerequisite; the actual engagement fix lands in a follow-up spec once a fresh run with `DUAL_RESEARCH_DEBUG_USAGE=1` produces the raw usage payload… The smoking-gun shape stays the same either way: `cache_read_tokens == 0 AND cache_write_tokens == 0 AND cost matches plain input × output arithmetic`." |
| D03 | 0141 | code-followup | UI warning chips for `ProtocolViolation` / `EmptyTurnDetected` events | Add a small warning chip / badge / audit-log surface on affected turn cards once the events accumulate signal across real runs | Spec 0141 handover §Known follow-ups: "Both events ride the spec-0122 transcript bridge and persist to `transcript.jsonl`, but no warning chip / badge / audit-log surface in this spec." |
| D04 | 0141 | code-followup | Retry-on-empty-turn / prompt-tightening using `EmptyTurnDetected` signal | A follow-up spec that tightens "you must surface at least one block per turn or explicitly STATUS: AGREED" can lean on the new `EmptyTurnDetected` data once collected across multiple production runs | Spec 0141 handover §Known follow-ups: "Retry-on-empty-turn / prompt-tightening. Spec §6 keeps this out of scope. The fix is a signal, not a behaviour change…" |
| D05 | 0142 | backfill | Backfill historic runs' `inputs/input.json` to retire synth fallback | Run `_persist_initial_brief_bundle` against every `runs/*/brief.md` lacking `inputs/input.json` and push; estimated scope: one-shot script | Spec 0142 handover §"Backfill plan for historic runs": "Deferred to a follow-up. Spec §6 explicitly keeps backfill out of scope… A backfill is feasible if we want to retire the synth path: for every run with `brief.md` on disk and no `inputs/input.json`, run `_persist_initial_brief_bundle` against the on-disk dir and push." |
| D06 | 0143 | code-followup | Audit `gpt-5-mini` pricing rates (`PRICING` table not refreshed) | Verify `gpt-5-mini` row in `PRICING` against current OpenAI pricing; current $0.25/$2.00/$0.025/$0.025 may be stale (`gpt-5.4-mini` is now $0.75/$4.50/$0.075). Bump and add new `PRICING_VERSION` entry if reconcile flags the test tier | Spec 0143 handover §Known follow-ups: "GPT-5-mini rates not audited. The `gpt-5-mini` row in `PRICING` was left at `$0.25 / $2.00 / $0.025 / $0.025`… The `test` tier (Haiku + gpt-5-mini) is rarely run in prod, but if reconcile starts flagging the test-tier model, the same bump pattern applies." |
| D07 | 0140 | code-followup | Retroactive salvage of anchor-run draft body (lines 47–312 → `final.md`) | One-shot script: lift `runs/20260521-010637-dvs-backend-language-choice/phase4/round-07-claude.md` lines 47–312 into a clean `final.md` | Spec 0140 handover §Known follow-ups: "B12 path-3 (retroactive salvage). Out of scope per spec §4. The anchor run's `round-07-claude.md` still holds 312 lines of usable draft body; lines 47–312 could be lifted into a clean `final.md` by a one-shot script." |
| D08 | 0144 | code-followup | First-class `RequestEvidence` op channel | Add a `RequestEvidence` block / ledger op so mid-run "request sources" can be modelled distinctly from raise-time `evidence_required: bool`; needs new prompt language and a new parser path | Spec 0144 handover §Known follow-ups: "**B14(1)(b) `RequestEvidence` op stays deferred** per spec §2.2. This spec covers raise-time `evidence_required` only — the mid-run 'request sources' channel would need new prompt language and a new parser path." |
| D09 | 0140+ | manual-smoke | End-to-end smoke run on a drift-prone brief | Fire a fresh `/dual-research-run` on a brief known to drift in Phase 4 to confirm natural-agreement convergence; ~$10 LLM spend, ~15 min. Carries forward across every handover in the batch | Spec 0140 handover: "firing a fresh `/dual-research-run` on a brief known to drift in Phase 4 (to confirm the run converges at natural agreement rather than hard-cap) is left as a user-side smoke since it costs ~$10 of LLM spend and ~15 minutes." (also referenced in 0141, 0145, 0146, 0147) |
| D10 | 0146 | code-followup | Aggregator: emit `was_closeout: bool` per turn so `closeout.request` row renders | Backend follow-up (B16 §10.4). Without it the consumption card's `closeout.request` row stays suppressed | Spec 0146 handover §Known follow-ups: "**`closeout.request` row still suppressed.** The aggregator doesn't yet emit `was_closeout: bool` per turn (B16 §10.4 backend follow-up). The closeout row is not rendered." |
| D11 | 0146 | code-followup | Backend: ship `outputBreakdown` (reasoning / response / tool-calls split) | Anthropic extended-thinking exposes reasoning-tokens; OpenAI `usage.completion_tokens_details.reasoning_tokens`. Tool-call cost from assistant message's `tool_calls` length. Then the output row in CcxCard can split | Spec 0146 handover §Known follow-ups: "**`outputBreakdown` rendering deferred.** The output row stays a single `Output` row until reasoning / response / tool-calls are split (B16 §10.1 backend follow-up)." |
| D12 | 0146 | code-followup | Backend: ship `usage.cacheSavingsUsd` (or per-model rates) | Either ship `usage.cacheSavingsUsd` directly OR ship per-model `input_per_mtok` + `cache_read_per_mtok` so the FE computes it. Adds `cache savings · ×N reuse on Xk` line to totals block | Spec 0146 handover §Known follow-ups: "**`cacheSavingsUsd` line in totals block deferred.** The `cache savings · ×N reuse on Xk` line from design-system §14 is not rendered until the backend ships `usage.cacheSavingsUsd` (B16 §10.2)." |
| D13 | 0146 | code-followup | Backend: split web-sources tokens from prompt-piece dict | Surface a real `web sources` row + token count separately from the system-prompt aggregate | B16 backlog §10.5: "**Web-source tokens** — split the input-token cost of fetched search-result snippets out from the prompt-piece dict so a real `web sources` row + token count is renderable." |
| D14 | 0146 | code-followup | Backend: split tool-definitions tokens from system prompt | Surface a `tool definitions` row separately | B16 backlog §10.6: "**Tool-definitions tokens** — split the input-token cost of tool definitions out from the system prompt aggregate." |
| D15 | 0145 | code-followup | Legacy-shim sunset (`LEGACY_KEY_TO_CANONICAL` + legacy `user_prompt` ArtifactDef) | Deadline **2026-08-19** (90 days post-merge). Backfill historical `events.payload.prompt_pieces` JSONB → `turn_prompt_pieces`, remove JS shim + phase-aware `system` resolver, drop `user_prompt` ArtifactDef, drop `LEGACY_INPUT_BUNDLE_KEYS` | Spec 0145 handover §"Legacy-shim sunset date": "2026-08-19. Both the `LEGACY_KEY_TO_CANONICAL` map in `artifacts.jsx` and the legacy `user_prompt` `ArtifactDef` in `contract/artifacts.py` are tagged for removal." |
| D16 | 0145 | code-followup | FastAPI camelCase serialiser still mangles single-segment canonical IDs | Pre-existing bug spawned during 0145; partially mitigated in 0146 (`_to_camel` skips dotted keys) but single-segment IDs (`user_prompt`, `current_draft`, `all_p2_turns`) still get camelCased and are inverted client-side via `normalisePiecesRaw`. Cleaner fix: extend the server guard with explicit canonical-ID allowlist or rename to always-dotted IDs | Spec 0145 handover §Known follow-ups: "FastAPI camelCase serializer transforms dict keys… The follow-up task is queued separately. See the spawn-task chip from this session." + Spec 0146 §Known follow-ups: "**Single-segment canonical IDs not in the server fix.** The 1-line `_to_camel` guard only catches dotted keys…" |
| D17 | 0144 | code-followup | `search_N` resolution baseline 9/30 (30%) on anchor run | Either (a) tighten address-side prompt so models emit `search_N` more conservatively, or (b) improve audit-capture path so empty `consulted_sources` becomes rarer | Spec 0144 handover §Known follow-ups: "**`search_N` resolution baseline is 9/30 records (30%) on the anchor run.**" |
| D18 | 0144 | observability | Validator over-flagging rate is unmeasured on fresh runs | Anchor run pre-dates the validator deploy so carries `unverified=False` everywhere. Next fresh run will reveal false-flag rate; if >50% flag → urgent prompt-side fix | Spec 0144 handover §Known follow-ups: "**Validator over-flagging is unmeasured.** The validator (`validate_all_evidence`) now runs on every search-bearing turn but the anchor run pre-dates this deploy… The next fresh run will reveal how often the validator flags evidence." |
| D19 | 0145 | code-followup | Per-attachment rich previews (markdown/thumbnail/download) | Spec §5.4 described rich-preview branch not implemented; anchor run has zero attachments so couldn't exercise. Add once a fresh attachment-bearing run exists | Spec 0145 handover §"Spec interpretations worth noting": "**Per-attachment rich previews (markdown/thumbnail/download)** described in §5.4 are NOT implemented in this PR — the anchor run has zero attachments so the visual test couldn't exercise them… a follow-up spec can add the rich-preview branch once a fresh attachment-bearing run exercises the path." |
| D20 | 0145 | code-cleanup | Dead `Preflight*Tab` components in run-detail.jsx | Delete `PreflightContentTab`, `PreflightSourcesTab`, `PreflightFilesTab`, `SourceRowAttachment`, `FileCard`, `AttachmentsEmpty` — left in place during 0145 for minimal blast radius | Spec 0145 handover §Known follow-ups: "**Legacy `Preflight*Tab` components in run-detail.jsx are now dead code**… Left in place this PR for minimal blast radius; a follow-up sweep can delete them." |
| D21 | 0145 | docs | Diagram regeneration: `deep-research-pipeline.{light,dark}.svg` + How-It-Works rewire | Out of scope per 0145 §3 / §6. Regenerate SVGs with canonical-ID labels resolving byte-identically to `display_name()`; rewire `how-it-works.jsx` to use `deep-research-pipeline` instead of `02-phase-inputs` | Spec 0145 handover §Known follow-ups: "**Diagram regeneration deferred** — `deep-research-pipeline.{light,dark}.svg` regeneration + How-It-Works rewire stayed out of scope per spec §3 / §6." |
| D22 | 0146 | code-cleanup | Orphaned `.ccx-header .stats .sep` / `.pct` CSS rules | Remove from `components.css` (lines 2531-2532); harmless but unused | Spec 0146 handover §Known follow-ups: "**Cosmetic .ccx-header .pct / .sep CSS rules unused**… Left in place this PR (harmless). A cosmetic PR can remove them." |
| D23 | 0147 | code-cleanup | Variable-naming asymmetry `p0StatsRoundCount` vs `pXStatsCount` in `buildLiveTimeline` | Rename for symmetry once the legacy pre-0114 Phase 0 fallback path is provably dead. Also: `PhaseContent` dead function at `run-detail.jsx:~7544` (no callers) — safe to delete in same janitor PR | Spec 0147 handover §Known follow-ups: "**Variable-naming asymmetry between `p0StatsRoundCount` and `p2StatsCount` / `p4StatsCount`.** Kept intentionally because Phase 0 is dual-shape…" + "**`PhaseContent` dead-code in `run-detail.jsx`** (function at ~line 7544 defined but no callers). Noticed during spec 0147 implementation; safe to delete in a janitor PR." |
| D24 | all | operational | File fly.io support ticket for `machines.dev` mid-rolling-deploy timeout | Six consecutive deploys (0140, 0141, 0142, 0144, 0146, 0147) hit the same shape: machine 1 healthy first pass, machine 2 reaches `stopped` when machines.dev API times out waiting on health checks; `fly machine start <id>` recovers. Overdue | Spec 0147 handover §Known follow-ups: "This is now the **sixth consecutive deploy** that hit the same shape… A fly support ticket is overdue — six-in-a-row is far past coincidence. Filed as the top follow-up across this batch's handovers; recommend a support thread before the next deploy." |

## Supabase SQL queue (in order)

### D01 — Spec 0145 migration `0006_turn_prompt_pieces`

Apply via Supabase Dashboard → SQL editor. Idempotent — safe to re-run.

```sql
-- Spec 0145 — per-piece token attribution, indexed by (run_id, turn_key, artifact_id).
--
-- Apply via Supabase Dashboard → SQL editor (single migration, idempotent).
-- Re-running is safe: IF NOT EXISTS guards both the table and the index.
--
-- The push CLI populates this table from the `prompt_pieces` payload on
-- every `turn_ended` event. Each (run_id, turn_key) gets one row per
-- artifact_id emitted by the protocol-side `pieces_for_*()` function.
-- For attachments, `artifact_id` carries the resolved canonical ID
-- (e.g. `user_prompt.attachment.abc123`); `attachment_id` (nullable)
-- is the raw attachment ID for joinability against `session_files` and
-- `attachment_blobs`; `display_title` is the resolved human-readable
-- title at push time (the value `display_name()` would return given
-- the contemporaneous `attachments.json`).
--
-- The UI server's consumption endpoint reads this table directly when
-- available; falls through to `events.payload.prompt_pieces` JSONB when
-- the table has no rows for the run (historical pre-spec runs).
--
-- Backfill of historical runs into this table is OUT OF SCOPE (per spec
-- §3 non-goals). New pushes from this version forward populate the
-- table; older runs continue to render via the legacy JSONB fallback
-- through the JS read-shim.
--
-- Rollback: `DROP TABLE turn_prompt_pieces;` — purely additive, no
-- changes to existing tables or constraints.

CREATE TABLE IF NOT EXISTS turn_prompt_pieces (
    run_id          TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    turn_key        TEXT NOT NULL,
    artifact_id     TEXT NOT NULL,
    tokens          INT NOT NULL,
    attachment_id   TEXT,
    display_title   TEXT,
    PRIMARY KEY (run_id, turn_key, artifact_id)
);

CREATE INDEX IF NOT EXISTS turn_prompt_pieces_run_idx
    ON turn_prompt_pieces (run_id, turn_key);
```

**Rollback**: `DROP TABLE turn_prompt_pieces;` — purely additive, no other tables depend on it.

## Per-spec breakdown

### Spec 0140 — Phase 4 deadlock extractor + escape-valve
- D-ids covered: D07 (retroactive salvage of anchor-run draft body), D09 (end-to-end smoke run)
- Notes: extractor + escape-valve fix shipped cleanly; only deferred items are out-of-scope per spec §4 (retroactive salvage) and the cost-gated user-side smoke. Telemetry note about `via_artifact_promotion=True` now covering two cases is documented but doesn't require user action.

### Spec 0141 — Critique aggregation invariants
- D-ids covered: D03 (UI surface for `ProtocolViolation`/`EmptyTurnDetected`), D04 (retry-on-empty-turn prompt-tightening), D09 (carry-forward smoke)
- Notes: B02 + B06 + B10 closed at the data layer; B10 verified self-resolving. Both new event types are persisted but not yet surfaced visually. Hosted UI visual smoke for Resolved-view matching Phase 4 timeline is auth-gated and was left as a user-side check.

### Spec 0142 — Prompt capture for full-view modals
- D-ids covered: D05 (backfill historic runs' `inputs/input.json`), D09 (hosted UI visual smoke on Initial Brief modal)
- Notes: anchor run re-pushed opportunistically; other historic runs continue using the synth-path fallback. Backfill is feasible via one-shot script but explicit non-goal per spec §6.

### Spec 0143 — Cost & token attribution + header polish
- D-ids covered: D02 (Anthropic cache-engagement fix — needs fresh-run debug payload), D06 (`gpt-5-mini` pricing audit)
- Notes: pricing rates fixed and reconcile-rebuild was actually run against all 18 local runs (overriding spec §4's default no-backfill). Anchor run `metrics.json` rewritten, +$36.6059 swing across 18 runs, all re-pushed. Instrumentation (`DUAL_RESEARCH_DEBUG_USAGE=1`) shipped; engagement fix still pending. `PRICING_VERSION` test-pin maintenance is automatic-via-failure-message.

### Spec 0144 — Sources & provenance investigation + critique card surface
- D-ids covered: D08 (`RequestEvidence` op), D17 (`search_N` resolution tightening), D18 (validator over-flagging rate unmeasured)
- Notes: 0143's `test_anchor_run_metrics_pinned_to_old_pricing_version` failure was flagged but resolved mid-batch via commit `3b9982f` per 0147 cross-batch follow-ups. Phase 4 visual regression test deferred (no Jest harness today). Backfill of pre-0114 runs is explicit non-goal.

### Spec 0145 — Canonical prompt-pieces + per-attachment token tracking
- D-ids covered: **D01 (Supabase migration 0006 NOT YET APPLIED — top priority)**, D15 (legacy-shim sunset 2026-08-19), D16 (camelCase single-segment IDs), D19 (per-attachment rich previews), D20 (dead `Preflight*Tab` components), D21 (diagram regeneration), D09 (fresh attachment-bearing run smoke)
- Notes: protocol-layer change shipped end-to-end, but production Supabase migration must be applied before the next live run or the `turn_prompt_pieces` upsert will error (rest of push pipeline still lands). Anchor run backfill deferred — historical JSONB still uses legacy `user_prompt` aggregate; JS read-shim translates at display time.

### Spec 0146 — Consumption card visual rework
- D-ids covered: D10 (`was_closeout` per turn), D11 (`outputBreakdown`), D12 (`cacheSavingsUsd`), D13 (web-sources tokens split), D14 (tool-definitions tokens split), D16 (cleaner camelCase fix), D22 (orphaned `.ccx-header .stats .sep`/`.pct` CSS), D09 (fresh attachment-bearing run smoke)
- Notes: server-side `_to_camel` dotted-key skip + frontend `normalisePiecesRaw` shipped together; per-attachment sub-rows auto-show on unfold. B16 backlog §10.1–10.6 explicitly listed as backend follow-ups; D10–D14 + D13–D14 (web sources / tool defs) are the substantive ones.

### Spec 0147 — Phase 0 critique section + live timeline determinism
- D-ids covered: D23 (variable naming + `PhaseContent` dead code), D24 (fly support ticket — sixth-in-a-row), D09 (fresh-run determinism smoke)
- Notes: zero open questions, smallest blast radius of the batch. `dr-critique-jump` from P0 timeline cards confirmed working live (`item.statsPhase === 0`). All B01–B16 backlog rows now on main.

## Consolidation recommendation

### One consolidation spec: "Consumption card backend + UI surface follow-ups"

Fold these D-ids into a single spec because they all live on the audit/aggregator → UI render boundary and share a common dispatch (the `TurnTokenUsage` / `TurnEnded` payload + the `CcxCard` rendering path):

- **D10** — `was_closeout: bool` per turn (aggregator)
- **D11** — `outputBreakdown` (reasoning / response / tool-calls)
- **D12** — `cacheSavingsUsd` (or per-model rates)
- **D13** — web-sources tokens split
- **D14** — tool-definitions tokens split
- **D03** — UI surface for `ProtocolViolation` / `EmptyTurnDetected` (same render-path neighbourhood; both events already on the transcript bridge)
- **D04** — retry-on-empty-turn / prompt-tightening (consumes the `EmptyTurnDetected` signal D03 also surfaces)
- **D16** — camelCase serialiser single-segment IDs (the underlying root for half of the rendering bugs the above expose — fix once)

These 8 share aggregator-emitter authorship + frontend rendering authorship and benefit from a single test fixture pass. Land as `Spec 0148 — Consumption-card backend follow-ups + protocol-violation UI surface`.

### Separate specs (own surface area / risk profile)

- **D02 — Anthropic cache-engagement fix.** High-stakes protocol-layer fix; risk profile (silent cache-control rejection costs ~3× on every Anthropic call) warrants its own spec with the debug payload as ground truth.
- **D08 — `RequestEvidence` op channel.** New protocol op + parser path + prompt language; orthogonal to consumption-card work; lives at the `contract/blocks.py` boundary.
- **D15 — Legacy-shim sunset + backfill (deadline 2026-08-19).** Bundles a historical-data backfill with a JS+Python shim deletion; sequencing-critical (backfill must complete before shim deletes); time-bound.
- **D17 — `search_N` resolution tightening.** Either prompt-side or audit-capture-side; needs measurement on fresh runs first (depends on D18 baseline).
- **D19 — Per-attachment rich previews.** UI-only but needs a fresh attachment-bearing run to design against; gated by D09.

### Zero-code operational actions (manual, don't bloat a spec)

- **D01 — Apply Supabase migration 0006.** Paste-and-run; the user just opens Supabase Dashboard → SQL editor and pastes the block above. ~30 seconds.
- **D24 — File fly.io support ticket.** Communication action, not a code change. Six consecutive deploys with the same `machines.dev` mid-rolling timeout warrant a support thread before the next push.
- **D09 — Fresh-run smokes.** ~$10 LLM spend + ~15 minutes each. Carries forward across the batch; the user fires `/dual-research-run` on a drift-prone brief whenever they have the budget.

### Janitor PR candidates (single small cleanup PR)

- **D20** — Dead `Preflight*Tab` components in run-detail.jsx
- **D22** — Orphaned `.ccx-header .stats .sep` / `.pct` CSS rules
- **D23** — Variable naming `p0StatsRoundCount` → `p0StatsCount` + delete `PhaseContent` dead function

Also candidates: **D07** (anchor-run draft body salvage script — one-shot, low risk) can run as a standalone shell command, no spec needed.

### Spec-or-script borderline

- **D05 — Historic-run `inputs/input.json` backfill.** Feasible as a one-shot script (read `runs/*/brief.md`, call `_persist_initial_brief_bundle`, push). If you want to retire the synth fallback entirely, fold into D15's backfill pass; if you only want it as a hygiene cleanup, run as a script.
- **D06 — `gpt-5-mini` pricing audit.** Read OpenAI's developer pricing page → update one row in `pricing.py` + add one entry to `test_pricing_version.py`. Could be a 2-file diff inside the consolidation spec or a standalone tiny PR.
- **D21 — Diagram regeneration + How-It-Works rewire.** Substantial; touches `diagrams/`, `src/dual_research/ui/static/diagrams/`, `how-it-works.jsx`, and CI parity tests. Spec-worthy if you want the CI diagram-parity test from B15 §test-plan to actually exist (currently doesn't); a single follow-up PR if you just want fresh-labelled SVGs.

## Reverse-coverage check

Confirming every Bxx from `specs/_backlog-inventory.md` actually landed:

| Backlog | Title | Landed in | Status |
|---|---|---|---|
| **B01** | Phase 0 section in Critique panel | Spec 0147 | Fully covered |
| **B02** | Disagreement raise/close invariant violated | Spec 0141 | Fully covered (15/16 → 15/15 on anchor) |
| **B03** | Token / cost capture skew between Claude and ChatGPT | Spec 0143 | Fully covered — but OpenAI side (stale `PRICING`) only; Anthropic cache engagement is **partial** — instrumentation shipped, engagement fix deferred to D02 |
| **B04** | Live timeline rendering non-deterministic | Spec 0147 | Fully covered (`_roundHasInFlight` + `pXRunningFloor`) |
| **B05** | Initial Brief full-view shows empty prompts | Spec 0142 | Fully covered for forward runs; historic-run backfill deferred (D05) |
| **B06** | Empty turns with zero critique movement | Spec 0141 | Covered as a signal (`EmptyTurnDetected`); prompt-tightening to actually prevent empty turns deferred to D04 |
| **B07** | Phase 4 deadlock after turn 8 | Spec 0140 | Fully covered |
| **B08** | Phase 4 cards missing Issue/Comment patches | Spec 0144 (absorbed) | Fully covered — `<ItemCard>` is kind-agnostic, B08 disappears with the render-path fix |
| **B09** | Source / provenance logic absent on this run | Spec 0144 | Investigation outcome shipped; validator wired at three sites |
| **B10** | Resolved view contradicts Phase 4 timeline | Spec 0141 | Verified self-resolving once B02/B06 land cleanly |
| **B11** | Top-bar copy button + Total cost/token labels | Spec 0143 | Fully covered (`CostBadge` "total" prefix + copyRunId clipboard) |
| **B12** | Phase 4 draft extractor `##` brittleness | Spec 0140 | Fully covered (path 1 + 2); path 3 retroactive salvage deferred to D07 |
| **B13** | Phase 4 escape valve precondition too narrow | Spec 0140 | Fully covered (one_agreed + terminal + soft-cap widening) |
| **B14** | Source provenance visible on every critique card | Spec 0144 | Fully covered; sub-items (1)(b) `RequestEvidence` op deferred to D08; `search_N` resolution is partial (D17) |
| **B15** | Canonical prompt-pieces + per-attachment token tracking | Spec 0145 | Fully covered on disk; Supabase migration NOT applied (D01); legacy-shim sunset queued (D15); per-attachment rich previews deferred (D19); diagram regeneration deferred (D21) |
| **B16** | Consumption card visual rework | Spec 0146 | Fully covered for visual rework; §10.1–10.6 backend follow-ups (output breakdown, cache savings, web sources, tool defs, closeout detection, attachments-in-snapshot) deferred to D10–D14 |

**Verdict:** 16/16 rows touched main; **3 partial closures** worth noting:
- B03 (Anthropic side instrumented, not fixed → D02)
- B14 (raise-time covered, mid-run `RequestEvidence` deferred → D08)
- B15 (code shipped, **production Supabase migration not yet applied → D01**)
- B16 (UI shipped, backend follow-ups → D10–D14)

The reverse check is clean — no Bxx was silently dropped. Every partial closure has a tracked Dxx with a verbatim source quote.
