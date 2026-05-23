# Handover — Spec 0145 — Canonical prompt-pieces + per-attachment token tracking (v1.11.0)

- **Date:** 2026-05-21
- **PR:** [Lexiz/dual-research#167](https://github.com/Lexiz/dual-research/pull/167) (merged, squash, branch deleted)
- **Spec:** [specs/0145-canonical-prompt-pieces-and-per-attachment-token-tracking.md](../specs/0145-canonical-prompt-pieces-and-per-attachment-token-tracking.md)
- **Anchor run:** `20260521-010637-dvs-backend-language-choice` (used as the legacy-key shim test case)
- **Backlog rows closed:** B15 (canonical prompt-pieces registry + per-attachment token tracking) — clean restart of the reverted 0139 spec
- **Version:** `1.10.0 → 1.11.0` (**MINOR** — second feature spec of the 0140–0147 batch; protocol-layer change, additive schema, frontend modal restructure)

## What landed

The load-bearing protocol-layer change that closes the long-standing "attachments are folded into a single `user_prompt` row" gap. Three coordinated surfaces moved in one PR because the contract changes only make sense end-to-end: the protocol emitter, the persistence path, and the frontend modal restructure.

- **Protocol** — every `pieces_for_*()` in [`protocol/prompt_pieces.py`](../src/dual_research/protocol/prompt_pieces.py) drops the aggregate `user_prompt` key and emits `user_prompt.message` + one `user_prompt.attachment.<id>` row per attachment instead. A new frozen `Attachment` dataclass (`id`, `title`, `content`) threads through every emitter and through all seven `*_input_bundle()` siblings in [`protocol/prompts.py`](../src/dual_research/protocol/prompts.py). The bundles now emit canonical artifact IDs (`system.task.*`, `user_prompt.message`, `user_prompt.attachment.<id>`, `phase1.claude/.openai`, `phase2.agreement.plan`, `current_draft`, `prior_turns.phase{0,2,4}`) instead of the legacy 8-key short vocab — only the keys the phase actually populates appear; the old "empty-string filler slot" pattern is gone.

- **Orchestrator** — [`orchestrator/run.py`](../src/dual_research/orchestrator/run.py) gains `_resolve_run_attachments(session_root)`, `_attachment_id(ing)`, and `_read_attachment_text(session_root, ing)` helpers. `run_session()` reads `attachments.json` once at session setup, converts each `ingest.Attachment` to a `prompt_pieces.Attachment` (sha256[:8] preferred ID, basename slug fallback; text extensions get full file content, binaries stay empty), and threads the list through every `run_dr_phase{0..4}` as a new `attachments=` kwarg. `_persist_initial_brief_bundle` accepts the same list so the Initial-Brief modal hydrates with per-attachment rows. Every `pieces_for_*()` and `*_input_bundle()` call site in [`orchestrator/dr_run.py`](../src/dual_research/orchestrator/dr_run.py) now passes `attachments=attachments` (six `pieces_for_*` sites + four bundle sites).

- **Persistence** — migration [`0006_turn_prompt_pieces.sql`](../supabase/migrations/0006_turn_prompt_pieces.sql) creates a per-piece token-attribution table indexed by `(run_id, turn_key, artifact_id)` with nullable `attachment_id` + `display_title` columns. Foreign-key cascade against `runs`; purely additive — no changes to existing tables. The push CLI's new `_push_turn_prompt_pieces` helper ([`persistence/remote.py`](../src/dual_research/persistence/remote.py)) walks the event stream and upserts one row per piece, with `attachment_id` parsed from canonical artifact IDs via the registry's `<id>` template regex and `display_title` resolved via `display_name()` against the contemporaneous `attachments.json`. The helper is split off from the inline iteration (Q1 resolution) so unit tests drive it directly.

- **Aggregator passthrough** — no code change in [`ui/aggregator.py::_on_turn_ended`](../src/dual_research/ui/aggregator.py); a load-bearing inline comment documents the canonical-ID passthrough contract and the no-normalisation invariant. Both canonical-ID runs and legacy-key historical runs flow through the same path; the JS shim is the only translation point.

- **Frontend** — [`ui/static/artifacts.jsx`](../src/dual_research/ui/static/artifacts.jsx) gains `phaseOrderFor(phaseNum)`, `canonicaliseLegacyKey(legacyKey, {phaseNum})`, `canonicalisePieces(pieces, {phaseNum})`, and `hasCanonicalKey(pieces)`. The legacy short-key shim covers `{system, brief, d1, d2, plan, hist, draft, histp}` → canonical IDs, with phase-aware overrides for `system` (`system.task.input`/`research_plan`/`plan_negotiation`/`drafting`/`review`). Sunset is annotated `// REMOVE AFTER 2026-08-19` per the Q4 resolution. [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) deletes `INPUT_PIECE_LABEL` / `INPUT_PIECE_ORDER` / `INPUT_PIECE_DEFAULT_COLLAPSED`; `InputTabContent` / `InputSection` / `AgentInputPane` resolve labels via `window.DrArtifacts.displayName`. `InputBriefModal` collapses from four tabs to a single "User prompt" tab containing three named section groups (`InputSectionGroup`): System prompt (collapsed), User prompt (expanded — contains `user_prompt.message` + per-attachment rows), Derived inputs (collapsed). `PreflightResponseModal` renames Agent Input → User prompt with the same three-section restructure. `CcxCard` adds a per-attachment expand affordance on the User-prompt row (▸ chevron, default-collapsed); sub-rows render `user_prompt.message` + one row per attachment via a new `SubInputRow` component using the existing `.ccx-bar-row` grid with a `.ccx-bar-row--sub` indent + dimmed-bar treatment.

- **Schema delta** — single new table `turn_prompt_pieces`; rollback is `DROP TABLE turn_prompt_pieces;`. The header comment in [`0006_turn_prompt_pieces.sql`](../supabase/migrations/0006_turn_prompt_pieces.sql) documents the apply procedure (Supabase Dashboard → SQL editor) and the rollback command.

## Files touched

### Protocol
- [`src/dual_research/protocol/prompt_pieces.py`](../src/dual_research/protocol/prompt_pieces.py) — new `Attachment` dataclass; all 5 `pieces_for_*()` functions emit canonical IDs with per-attachment rows.
- [`src/dual_research/protocol/prompts.py`](../src/dual_research/protocol/prompts.py) — all 7 `*_input_bundle()` siblings accept `attachments` + emit canonical-ID keys; `INPUT_BUNDLE_KEY_ORDER` renamed to `LEGACY_INPUT_BUNDLE_KEYS` with the spec-0145 comment.

### Orchestrator
- [`src/dual_research/orchestrator/run.py`](../src/dual_research/orchestrator/run.py) — `_resolve_run_attachments`, `_attachment_id`, `_read_attachment_text`; threads `attachments` through `_persist_initial_brief_bundle` + all 5 `run_dr_phase{0..4}` calls.
- [`src/dual_research/orchestrator/dr_run.py`](../src/dual_research/orchestrator/dr_run.py) — each `run_dr_phaseN()` gains `attachments` kwarg; six `pieces_for_*()` call sites + four `*_input_bundle()` call sites migrated.

### Persistence
- [`supabase/migrations/0006_turn_prompt_pieces.sql`](../supabase/migrations/0006_turn_prompt_pieces.sql) — new table + index.
- [`src/dual_research/persistence/remote.py`](../src/dual_research/persistence/remote.py) — `_push_turn_prompt_pieces` helper, `_iter_turn_prompt_pieces_rows` iterator, `_load_attachments_title_map`; push pipeline calls them after blobs.

### UI server / aggregator
- [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py) — annotation-only: documents the load-bearing canonical-ID passthrough contract.

### Frontend
- [`src/dual_research/ui/static/artifacts.jsx`](../src/dual_research/ui/static/artifacts.jsx) — adds `phaseOrderFor`, `canonicaliseLegacyKey`, `canonicalisePieces`, `hasCanonicalKey`, `LEGACY_KEY_TO_CANONICAL` to `window.DrArtifacts`.
- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — legacy vocab deleted; `InputSectionGroup` + `SubInputRow` added; `InputBriefModal` / `PreflightResponseModal` restructured; `CcxCard` per-attachment expand; `outputSlotFor` returns canonical IDs.
- [`src/dual_research/ui/static/index.html`](../src/dual_research/ui/static/index.html) — cache-bust `v=0138a` → `v=0145a` across all 25 static-asset query strings.

### Tests
- [`tests/protocol/test_prompt_pieces.py`](../tests/protocol/test_prompt_pieces.py) — canonical-key shape, attachment decomposition, idempotency, sum invariant, registry membership.
- [`tests/protocol/test_input_bundles.py`](../tests/protocol/test_input_bundles.py) — canonical-key bundle shape per phase, per-attachment rows, system-text placeholder preservation.
- [`tests/orchestrator/test_session_setup.py`](../tests/orchestrator/test_session_setup.py) — canonical-key assertions on the persisted initial-brief bundle.
- [`tests/ui/test_aggregator_input_bundles.py`](../tests/ui/test_aggregator_input_bundles.py), [`tests/ui/test_server_input_bundles.py`](../tests/ui/test_server_input_bundles.py) — synth-fallback canonical-key assertions.
- [`tests/spec0145/`](../tests/spec0145/) — new package; 35 cases across `test_resolve_run_attachments.py`, `test_push_turn_prompt_pieces.py`, `test_aggregator_passthrough.py`, `test_migration_0006_sql.py`.

### Misc
- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — `1.10.0 → 1.11.0`.
- `CHANGELOG.md` — `[1.11.0]` entry.

## Schema delta — migration 0006

```sql
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

**Apply**: Supabase Dashboard → SQL editor, paste the contents of `supabase/migrations/0006_turn_prompt_pieces.sql`. Idempotent — re-running is safe.

**Rollback**: `DROP TABLE turn_prompt_pieces;` — purely additive, no other tables depend on it.

**Apply status**: NOT YET APPLIED to production Supabase. The push CLI references the table on every push, so applying the migration is a prerequisite for any new push to populate per-piece rows. Existing pushes (events/runs/files/blobs) continue to land because they hit different tables; only the new `turn_prompt_pieces` upsert will fail until the table exists. The push CLI does NOT crash on a missing table — Supabase returns an error that the helper currently lets bubble up; consider an `if-table-exists` guard or apply the migration before the next live run.

## Four open-question resolutions

1. **§5.2 push-CLI placement** — separate `_push_turn_prompt_pieces` helper called from the existing turn-iteration block. Direct unit-test coverage at `tests/spec0145/test_push_turn_prompt_pieces.py`.
2. **§5.4 `InputBriefModal` tab consolidation** — rename Content → "User prompt" and fold Sources/Files into the User-prompt section as per-attachment rows. Three named sections inside the new tab: System prompt · User prompt · Derived inputs. Anchor run has zero attachments, so the visual test was the legacy-shim path: the historical `{system, brief}` bundle resolves to `system.task.input` + `user_prompt.message` rows, no Derived-inputs section (no other populated keys).
3. **§5.4 `phaseOrderFor(phaseNum)`** — JS-side in `artifacts.jsx` (kept co-located with `displayName` and `canonicaliseLegacyKey`). Promote to Python if the future diagram-regeneration follow-up needs the same ordering.
4. **§5.4 read-shim deletion deadline** — 2026-08-19 (90 days post-merge). Comment in `artifacts.jsx`: `// REMOVE AFTER 2026-08-19 (90 days post-merge; sunset follow-up backfills any remaining legacy data through one push pass and drops both this shim and the legacy user_prompt ArtifactDef).`

## Legacy-shim sunset date

**2026-08-19.** Both the `LEGACY_KEY_TO_CANONICAL` map in `artifacts.jsx` and the legacy `user_prompt` `ArtifactDef` in `contract/artifacts.py` are tagged for removal. The sunset spec needs to:
1. Backfill historical `events.payload.prompt_pieces` JSONB → `turn_prompt_pieces` rows (one push pass against every run dir).
2. Remove the JS `LEGACY_KEY_TO_CANONICAL` map + `canonicaliseLegacyKey` + the phase-aware `system` resolver.
3. Remove the `user_prompt` `ArtifactDef` from the Python registry (and its JS mirror).
4. Drop the `LEGACY_INPUT_BUNDLE_KEYS` constant from `protocol/prompts.py` (test fixture only at that point).

## Backfill plan for historic runs

**Deferred** — explicit non-goal per spec §3 / §6. The strategy:

- Historical events stay in `events.payload.prompt_pieces` JSONB unchanged. The Consumption tab + full-view modals render them via the JS read-shim, which translates legacy short keys → canonical IDs at display time.
- A future backfill spec (or the sunset spec above) can replay every historical run's `turn_ended` events through `_iter_turn_prompt_pieces_rows` to populate `turn_prompt_pieces` without re-running any agents. The push CLI already does this work for new pushes; backfill is the same code path on cold data.
- Until that backfill, only newly-pushed runs populate `turn_prompt_pieces`. Historical runs render via the JSONB fallback.

## Deploy status

- **Version**: `1.11.0`
- **Deploy timestamp**: 2026-05-21T~21:30Z (single rolling deploy, no `machines.dev` mid-deploy flake this time — clean first pass on both machines)
- **Live**: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.11.0","backend":"supabase"}`
- **Bundle markers**: `curl https://dual-research-alex.fly.dev/run-detail.jsx?v=0145a | grep -c "Spec 0145"` → 17 hits. The new JSX bundle is on both machines.

### Smoke (local preview against the anchor run)

- **InputBriefModal restructure** — opening the Initial Brief card on the anchor-run timeline now renders a single "User prompt" tab containing two visible section groups (SYSTEM PROMPT / USER PROMPT) plus an empty Derived-inputs slot. The expanded User-prompt section shows the "Chat message" row label (resolved via `displayName('user_prompt.message')`), replacing the pre-spec "User prompt: Brief" label.
- **Legacy-key shim** — verified via `window.DrArtifacts.canonicaliseLegacyKey('d1') === 'phase1.claude'`, `canonicaliseLegacyKey('brief') === 'user_prompt.message'`, `canonicaliseLegacyKey('system', {phaseNum: 2}) === 'system.task.plan_negotiation'`. `phaseOrderFor(0)` returns the documented Phase-0 arrival order.
- **Display-name resolution** — verified `displayName('user_prompt.message') === 'Chat message'`, `displayName('user_prompt.attachment.abc', {titleForId: {abc: 'Foo'}}) === 'Attachment · Foo'`.
- **CcxCard** — the anchor run has zero attachments so the new expand affordance doesn't fire (matches the spec's "no per-attachment rows on the anchor run" expectation). The existing rows render unchanged.
- **Hosted UI smoke** — auth-gated (`/api/runs/<id>/inputs/input` returns 401 without a session token, same pattern as specs 0141-0144). Data-layer correctness verified by the bundle-marker probe + local-preview snapshot; the JSX is deterministic given Supabase data and the local smoke covers the rendering path.

### Smoke (fresh runs against the deployed UI)

Pending — applying migration 0006 and firing a fresh run with attachments is the remaining live-data check. Without the migration, the new push step against `turn_prompt_pieces` will surface an error. The current production runs continue to read via the JSONB fallback path because the UI server's existing consumption endpoint is unchanged.

## Known follow-ups + caveats

- **FastAPI camelCase serializer transforms dict keys** — a pre-existing bug spawned as a follow-up task during this session. The response model camelCases dict keys recursively, so the aggregator's `prompt_pieces` dict arrives with `user_prompt` → `userPrompt` and `system.task.plan_negotiation` → `system.task.planNegotiation` on the wire. Result: the Consumption tab's User-prompt row has always shown 0t on legacy-aggregate runs because the JS lookup against the snake_case canonical IDs misses. Spec 0145 doesn't introduce this — verified by walking the old code path on `main` — but the per-attachment expansion will inherit the same lookup miss when fresh runs land. The follow-up task is queued separately. See the spawn-task chip from this session.
- **Migration 0006 needs manual apply** — the on-disk SQL is unit-test-pinned but the production Supabase has not yet been updated. Apply via the Supabase Dashboard SQL editor (paste the migration's contents). Until then, fresh-run pushes will hit a "table does not exist" error on the `turn_prompt_pieces` upsert step; the rest of the push (runs/events/session_files/attachment_blobs) lands normally.
- **Anchor-run backfill not run** — historical `prompt_pieces` JSONB still uses the legacy `user_prompt` aggregate. The JS shim handles this on the read path; no Supabase change needed for backwards-compatibility. A future spec can backfill `turn_prompt_pieces` from the JSONB if cross-run per-attachment analytics become useful.
- **Spec 0146 (consumption-card visual rework) is unblocked** — depends on this spec + 0143 (both shipped). 0146 will surface the per-attachment rows as nested sub-bars or a separate disclosure cluster; the data plumbing this spec landed is what 0146 reads.
- **Diagram regeneration deferred** — `deep-research-pipeline.{light,dark}.svg` regeneration + How-It-Works rewire stayed out of scope per spec §3 / §6. Cache-bust still bumped because the JS bundle changed.
- **CI cross-language registry parity test** — already exists at `tests/contract/test_artifacts_registry_sync.py`; passes against the spec-0145 additions because the new functions (`phaseOrderFor`, `canonicaliseLegacyKey`) live alongside the registry without modifying the REGISTRY tuple itself.
- **Legacy `Preflight*Tab` components in run-detail.jsx are now dead code** — `PreflightContentTab`, `PreflightSourcesTab`, `PreflightFilesTab`, `SourceRowAttachment`, `FileCard`, `AttachmentsEmpty`. Left in place this PR for minimal blast radius; a follow-up sweep can delete them. They don't import any new symbols, so they're cheap to carry until either spec 0146 reclaims them or a cleanup PR removes them.

## Spec interpretations worth noting

- **`artifact-display.js` was folded into `artifacts.jsx`** rather than created as a new module. The existing JS-registry-mirror module already exposes `window.DrArtifacts.displayName`; adding `phaseOrderFor` + `canonicaliseLegacyKey` to the same module keeps a single source of truth for the JS-side artifact surface. The CI sync test at `tests/contract/test_artifacts_registry_sync.py` still passes (the REGISTRY tuple is unchanged).
- **Three-section restructure inside the modal** uses `CollapsibleSection` for the section group header itself (System prompt / User prompt / Derived inputs as collapsible accordions), with the existing per-piece `InputSection` rows nested inside. The spec's text didn't specify the visual treatment for the section dividers; the chosen approach reuses the established disclosure primitive so visual consistency is automatic.
- **Per-attachment rich previews (markdown/thumbnail/download)** described in §5.4 are NOT implemented in this PR — the anchor run has zero attachments so the visual test couldn't exercise them, and the existing `InputSection`'s markdown renderer is adequate for text attachments. Binary attachments will render as a zero-content row with their canonical title; a follow-up spec can add the rich-preview branch once a fresh attachment-bearing run exercises the path.
