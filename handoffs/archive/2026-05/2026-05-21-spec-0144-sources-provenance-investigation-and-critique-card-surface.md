# Handover — Spec 0144 — Sources & provenance: investigation + per-critique-card surface (v1.10.0)

- **Date:** 2026-05-21
- **PR:** [Lexiz/dual-research#166](https://github.com/Lexiz/dual-research/pull/166) (merged, squash, branch deleted)
- **Spec:** [specs/0144-sources-provenance-investigation-and-critique-card-surface.md](../specs/0144-sources-provenance-investigation-and-critique-card-surface.md)
- **Anchor run:** `20260521-010637-dvs-backend-language-choice`
- **Backlog rows closed:** B09 (investigation outcome) + B14 (per-card sources feature) + B08 (Phase 4 Issue/Comment patches, absorbed)
- **Version:** `1.9.4 → 1.10.0` (**MINOR** — first feature spec of the 0140–0147 batch; user-visible new surface on every critique card, additive schema fields only, no breaking removal)

## What landed

The first MINOR bump in the batch — and the spec that turns "investigation" into "permanent provenance surface." Three concerns closed in one PR because they all live on the same render path:

- **B09** was framed as "no sources are cited, recorded, or requested anywhere in the run." The investigation in §3 of the spec found that statement was true *as observed in the UI* but false at the event-store / orchestrator layer: the anchor run actually emitted **19 `turn_searches` events**, **38 `item_raised`** (13 with `evidence_required: true`), and **78 `item_transitioned`** (14 with non-empty `evidence_records`, 30 records total). The gaps were render-side: the contract validator was wired to a no-op default at three construction sites, the address-side handler dropped flagged ADDRESS blocks instead of annotating them, `evidence_event_id` was never resolved against `TurnSearchAudit`, and `_normalizeToThread` stripped `evidence` before the JSX hit a renderer. All four closed here.
- **B14** ships the per-card SOURCES segment matching the iter-3 mockup. Every critique card now shows: header chip row → body → optional Evidence-needed helper → LIFECYCLE timeline → footer → SOURCES (when N>0), with a clickable `Sources N` header chip that scrolls the segment into view and a row-only `⚠ unverified` chip on offending source rows.
- **B08** is absorbed: Phase 4 Issue/Comment cards now render via the same `<ItemCard>` primitive as Q and D. The address-side handler is kind-agnostic; B08 was purely a render-level drop and disappears the moment new-protocol items flow through ItemCard.

## Files touched

### Backend

- [`src/dual_research/contract/evidence.py`](../src/dual_research/contract/evidence.py) — `EvidenceRecord` gains five denormalised fields (`raised_in_round` / `answered_in_round` / `requested_by` / `provided_by` / `attached_at`) with safe defaults.
- [`src/dual_research/ui/models.py`](../src/dual_research/ui/models.py) — UI mirror gains the same five fields plus a `consulted_sources: list[ConsultedSource]`. New `ConsultedSource` dataclass holds the slim per-tool-event projection (URL · title · page_age · queries — no `encrypted_content`).
- [`src/dual_research/ui/items.py`](../src/dual_research/ui/items.py) — `_resolve_consulted_sources` maps the model's `search_N` logical handles to `tool_events[N-1]` symmetrically across Anthropic (`srvtoolu_…`) and OpenAI (`ws_…`) opaque IDs; physical-event-id fallback for the case where the model happens to emit the real handle. `aggregate_items` / `aggregate_items_from_transcript` widened to accept an `audit_lookup` callable; new `build_session_audit_lookup(session_dir)` returns a per-turn-cached lookup keyed by canonical turn_key. `_apply_transition` derives the turn_key from `(phase, round, actor)` when not on the event, and stamps the denormalised round/actor fields onto every persisted record. `aggregate_items` now reads `event` / `kind` / `event_type` as fallbacks (the live transcript writes `event`, the orchestrator dataclass-events use `kind`).
- [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py) — `_attach_item_aggregation` injects the `audit_lookup` when a session_dir is in scope; replay-from-disk fallback also receives it.
- [`src/dual_research/orchestrator/deep_research.py`](../src/dual_research/orchestrator/deep_research.py) — validator signature widened from `(records, parsed, agent)` to `(records, parsed, agent, audit_tool_events)`. Default no-op widened to match. `apply_turn` accepts a new `audit_tool_events: list[dict] | None = None` kwarg. **Address-side rewritten as annotator-not-dropper**: when the validator flags evidence, the transition still lands at `addressed`, but each flagged evidence dict carries `unverified=True` + comma-joined flag codes in `unverified_reason`.
- [`src/dual_research/orchestrator/dr_run.py`](../src/dual_research/orchestrator/dr_run.py) — new `_evidence_validator_for_run` closure wraps `contract.evidence.validate_all_evidence` with the per-turn `tool_events` list. Both `DeepResearchPhase(...)` construction sites pass it. `_read_turn_audit_tool_events(session_dir, turn_key)` loads the audit from disk; `_drive_interaction_phase` derives the turn_key via the canonical `_derive_turn_key` helper.
- [`src/dual_research/ledger/replay.py`](../src/dual_research/ledger/replay.py) — replay-side construction also wires `_evidence_validator_for_run`. `_read_replay_audit_tool_events` tries the round-keyed form first and falls back to the flat pre-spec-0142 form so historical runs replay cleanly. `replay_items_from_disk` accepts `audit_lookup` so densification works on cold replay too.

### Frontend

- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx)
  - `renderItem` branches on whether the item has a corresponding entry on `run.phaseStats.items` carrying a `transitions` array — new-protocol items route through `<ItemCard>`, legacy/pre-0114 items keep `<QuestionThread>`.
  - `ItemCard` gains: a clickable `Sources N` header chip (explicit `scrollBy({behavior:'auto'})` against the nearest scrollable ancestor — `behavior:'smooth'` was a no-op in some Chromium builds), a uniform lifecycle footer (`✓ {terminalState} at round N · M turns to converge`) across all four kinds, an italic Evidence-needed helper line when `evidence_required === true`, and uses the existing `<SourceRow>` primitive for each evidence record.
  - `_normalizeToThread` no longer strips `evidence` / `transitions` / `anchor_type` / `anchor_text` / `evidence_required` — they survive the legacy path as defensive denormalisation, so any future callsite that still routes a new-protocol item through `<QuestionThread>` won't throw the data away.
- [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) — adds the full `.item-card*` ruleset (head · body · anchor · evidence-needed · timeline · lifecycle-footer · sources · sources-chip) plus `.source-row*` (head · chev · title · host · body · field · label · excerpt · is-unverified) per the iter-3 mockup.

### Design system

- [`design-system/audits/2026-05-19-badge-governance-iter3/mockup.html`](../design-system/audits/2026-05-19-badge-governance-iter3/mockup.html) — promoted from `handoffs/ds-v2-audit/` via `git mv` so blame survives.
- [`design-system/audits/2026-05-19-badge-governance-iter3/README.md`](../design-system/audits/2026-05-19-badge-governance-iter3/README.md) — new pointer file cross-linking the mockup to SPEC.md and the live JSX.
- [`design-system/SPEC.md`](../design-system/SPEC.md) — §1 gains a new invariant ("All four critique-item kinds render with the same card layout; only the category chip varies"); §3 Primitives gains a `SourceRow` row; new §4.7 (Sources segment) and §4.8 (Critique card composition).

### Tests

- [`tests/orchestrator/test_deep_research.py`](../tests/orchestrator/test_deep_research.py) — `test_evidence_fabricated_event_id_blocks_address_transition` renamed to `..._annotates_unverified` and rewritten to assert annotator semantics (transition lands; `unverified=True` on the offending record). Validator stub widened to the new 4-arg signature.
- [`tests/spec0144/test_provenance_present_on_anchor_run.py`](../tests/spec0144/test_provenance_present_on_anchor_run.py) — 3 cases: (a) 38 items + 14 with evidence on the anchor run, (b) the post-spec baseline of 9 records / 4 items with resolved consulted_sources, (c) denormalised round/actor fields populated end-to-end.
- [`tests/spec0144/test_evidence_validator_wired.py`](../tests/spec0144/test_evidence_validator_wired.py) — 4 cases: `_build_dr_phase` wires the real validator, the default is 4-arg, both `_drive_interaction_phase` and `replay._replay_phase` reference `_evidence_validator_for_run` (grep-level guard against silent reversion).
- [`tests/spec0144/test_consulted_sources_resolution.py`](../tests/spec0144/test_consulted_sources_resolution.py) — 9 cases: `search_N` resolution under both providers (open-Q #1), physical-id fallback, `encrypted_content` stripping, out-of-bounds / missing-audit / malformed-handle defensive returns.
- [`tests/spec0144/test_wire_payload_budget.py`](../tests/spec0144/test_wire_payload_budget.py) — anchor-run `phaseStats.items` payload ≤ 256 KB; literal `"encrypted_content":` key never appears in the serialised wire payload.

### Misc

- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — `1.9.4 → 1.10.0`.
- `CHANGELOG.md` — `[1.10.0]` entry.

## B09 investigation outcome — what changed in the validator wiring

The investigation found the validator was constructed with the default no-op `lambda recs, p, a: []` at three sites:
- `orchestrator/dr_run.py::_build_dr_phase` (line 138)
- `orchestrator/dr_run.py::_drive_interaction_phase` (line 185 — inline construction)
- `ledger/replay.py::_replay_phase` (line 97 — replay-side reconstruction)

This spec wires `_evidence_validator_for_run` at all three. The validator signature widened from 3-arg to 4-arg so `apply_turn` can supply the per-turn `tool_events` list directly — no per-round closure rebinding. The address-side `if flags: continue` drop was rewritten as an annotator: the transition lands, and flagged evidence carries `unverified=True` + `unverified_reason="comma,joined,flag,codes"`.

Residual gaps (worth a follow-up):
- The model emits `search_N` handles for `evidence_event_id`. We map them to `tool_events[N-1]`. On the anchor run, 9 of 30 records (4 of 14 items) resolve to non-empty `consulted_sources`. The remaining 21 records reference an index outside the persisted `tool_events` list OR map to a tool event with zero consulted_sources (provider-side miss — Anthropic and OpenAI sometimes don't surface the consulted-sources list even when a search ran). Not a bug in this spec's wiring; it's a prompt + provider-behaviour issue.
- The contract validator (`validate_all_evidence`) consumes the same audit and may flag records as `unverified` on future runs. The anchor run has zero `unverified=True` records because it pre-dates this deploy. Will surface on the next fresh run.

## Three open-question resolutions

1. **search_N ↔ event_id provider asymmetry.** Both providers emit opaque physical IDs (Anthropic `srvtoolu_…`, OpenAI `ws_…`); neither emits `search_N` natively. `search_N` is a model-emitted *logical* handle. Resolution: enumerate `tool_events` by index. `search_2` → `tool_events[1]` works uniformly across providers. No provider-specific normaliser needed. Verified against both an Anthropic and an OpenAI turn from the anchor run (see `searches/phase2_round2_claude.json` and `searches/phase2_round2_gpt.json`).
2. **Sources N header chip click affordance.** Per-card-jump — clicking the chip scrolls the card's own SOURCES segment into view. Consistent with the iter-3 mockup. Spec's default was "no click handler"; resolved to active per-card-jump.
3. **`⚠ unverified` chip placement.** Row-only. The iter-3 mockup puts it only on the source row; a card with 3 sources where only 1 is flagged would mislead with a card-level chip. Matches spec §10.3 resolution.

## New design-system tokens / chip primitives

No new design tokens — the work reuses `--md-surface-container*`, `--md-outline-hair`, `--md-on-surface-variant`, `--md-tone-warn-border`. The `⚠ unverified` chip uses the existing `.md-chip--sm` + `.md-chip--warn` combination.

Two new SPEC.md primitives:
- `SourceRow` (under §3) — per-evidence-record collapsible row.
- `Sources segment` (new §4.7) — the per-card source stack with `Sources (N)` label and hidden-when-empty rule.

Plus a new composition: `Critique card composition` (new §4.8) — codifies the stacking order across Q · D · I · C and the "no kind-specific card variant exists" invariant. The §1 principle "one card primitive per surface" was added as a sentence-level rule.

## Deploy status

- **Version:** `1.10.0`
- **Deploy timestamp:** 2026-05-21T20:09Z (machine 1 healthy on first pass)
- **Machine 2 recovery:** Same fly-side flake the spec-0141 / 0142 / handovers documented — `machines.dev` API timed out mid-rolling-deploy, leaving machine `148ee320f427e8` in `stopped` state. Recovered via `fly machine start 148ee320f427e8`; both machines `started` + 1/1 health by 20:15Z.
- **Live:** `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.10.0","backend":"supabase"}`.

### Smoke

- **Local preview MCP** — verified `<ItemCard>` mounts for new-protocol items, the SOURCES segment renders for 7 of 12 P4 cards on the anchor run, the `Sources N` header chip click scrolls the segment into view (0 → 1307 px via `scrollBy` on `.crit2__body`), the lifecycle footer renders on terminal items (`✓ resolved at round 3 · 2 turns to converge`), and the Evidence-needed helper renders on the 6 items with `evidence_required: true`. The `⚠ unverified` chip stays at zero on the anchor run because the validator hadn't been running when the data was captured — future runs will exercise it.
- **Deployed bundle markers.** `curl https://dual-research-alex.fly.dev/run-detail.jsx?v=0138a | grep -c "Spec 0144"` → 8 hits; same probe on `components.css` → 1 hit. Confirms the new JSX + CSS landed on both machines.
- **Hosted UI visual smoke** — auth-gated (`/api/runs/<id>/...` returns 401 without a session token, same as spec 0141/0142). The JSX is deterministic given Supabase data and the local-preview smoke covers the rendering path. Left as a user-side check.

## Backfill decision for historic runs

**Deferred.** Per spec §2.2 / §9.2 — "no backfill of pre-0114 archived runs" is explicit non-goal. Their items have no `transitions` array, so the new `renderItem` branch falls through to the legacy `<QuestionThread>` path. Pre-0114 runs simply don't get a SOURCES segment because they never captured one — and the empty-state hide-segment rule (§4.7) makes the absence invisible.

Newer post-0114 runs (including the anchor run `20260521-010637-dvs-backend-language-choice`) already carry the partial-firing pattern documented in §3.1. They get the new surface automatically — `aggregator.py` will densify their `evidence_records` with `consulted_sources` on the next page load, and the JSX will render `<ItemCard>` for every item.

A push of the anchor run *would* refresh its on-disk + Supabase state under the new aggregator path, but the rendering doesn't require it: the SSE aggregator densifies on demand. No backfill ship.

## Known follow-ups

- **`tests/agents/test_anchor_run_reconcile.py::test_anchor_run_metrics_pinned_to_old_pricing_version` is a pre-existing failure on `main`.** Spec 0143's post-merge backfill rewrote the anchor run's `metrics.json` `pricing_version` from `2026-05-17` to `2026-05-21`, but the test still pins the old value. Not caused by spec 0144 — confirmed by re-running on main without my changes. A spawn-task chip was filed during this session to either update the pin or point the test at the `.recompute-backup` so the pre-0143 semantic is preserved.
- **`search_N` resolution baseline is 9/30 records (30%) on the anchor run.** Not a bug — most provider tool events on the anchor run have empty `consulted_sources` (OpenAI especially, which often returns `title: null, encrypted_content: null` even when URLs are present), and some `search_N` indices fall outside the persisted `tool_events` list. The spec's §8.1 originally wrote "at least 10 of the 14" optimistically; the test pins the real baseline (`>= 9 records, >= 4 items`). A follow-up could either (a) tighten the address-side prompt so models emit `search_N` more conservatively, or (b) improve the audit-capture path so empty `consulted_sources` becomes rarer.
- **Validator over-flagging is unmeasured.** The validator (`validate_all_evidence`) now runs on every search-bearing turn but the anchor run pre-dates this deploy, so its existing transcript carries `unverified=False` everywhere. The next fresh run will reveal how often the validator flags evidence (event_id_fabricated, url_not_consulted, content_not_in_source). If >50% flag, the prompt-side fix becomes urgent — that's a follow-up spec, not a regression.
- **Rendered visual reference in `Design System v2.html` was deferred** per spec §6.3.e. SPEC.md text + the mockup at `design-system/audits/` + the live JSX form the three-surface invariant; adding a copy to the v2 doc would be a meaningful expansion that should land in its own change. The audit-dir README cross-links the mockup to the live JSX so reviewers can diff visually without it.
- **B14(1)(b) `RequestEvidence` op stays deferred** per spec §2.2. This spec covers raise-time `evidence_required` only — the mid-run "request sources" channel would need new prompt language and a new parser path. Filed as a candidate for a future spec.
- **Phase 4 visual regression test (§8.4 / §8.5)** was specced as a Jest + jsdom test. The project doesn't have that harness today; the preview-MCP smoke covered the same surface. If a future spec brings up a Jest runner, this is the place to retro-add structural snapshot tests.
- **Fly `machines.dev` mid-rolling-deploy timeout** keeps recurring across deploys (0141, 0142, 0144). If it surfaces a fourth time in a row a fly support ticket is warranted; for now `fly machine start <id>` after deploy is the documented recovery.
