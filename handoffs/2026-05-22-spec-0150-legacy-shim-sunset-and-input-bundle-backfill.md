# Handover — Spec 0150 — Legacy-shim sunset + historical input-bundle backfill (v1.15.0)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#172](https://github.com/Lexiz/dual-research/pull/172) (merged, squash, branch deleted)
- **Spec:** [specs/0150-legacy-shim-sunset-and-input-bundle-backfill.md](../specs/0150-legacy-shim-sunset-and-input-bundle-backfill.md)
- **Audit:** [specs/_post-batch-cleanup-audit.md](../specs/_post-batch-cleanup-audit.md) — closed **D15 + D05**. Three operational rows remain: **D09 / D18 / D24**. The audit is now **code-complete**.
- **Anchor run:** `20260521-010637-dvs-backend-language-choice` — post-0145 prompt_pieces keys (translation = no-op for `turn_prompt_pieces`); per-turn input bundles + `inputs/input.json` were pre-0145 vintage and DID get rewritten.
- **Version:** `1.14.0 → 1.15.0` (MINOR — deliberate deadline-bound checkpoint signalling the 90-day shim window closed cleanly. No new wire fields, no protocol changes, no new prompt language. Net code is **negative 206 LOC**).

## What landed

Six work products in one ship: three backfill passes against production data, then five surgical deletions, plus three impl-time follow-ups discovered during real-data Phase F verification.

### Backfill (three passes via `scripts/backfill_legacy_shim.py`)

- **Pass 1 (D15) — `events.payload.prompt_pieces` JSONB → `turn_prompt_pieces` table.** 10 historical runs upserted, **1,196 canonical rows after cleanup**. Translation policy: prefer-canonical when both legacy and canonical present in the same dict; phase-aware system resolver mirrors the JS shim's `LEGACY_SYSTEM_BY_PHASE` table. Idempotency gate: dry-run after execute reports zero candidates.
  - 8 runs in `turn_prompt_pieces` came back as "to backfill" with zero pairs / rows — these are pre-prompt-piece-emission runs (their `turn_ended` events carry empty `prompt_pieces` dicts). Trivially backfilled.
  - The push pipeline's own `_iter_turn_prompt_pieces_rows` writes rows VERBATIM from the event payload — no translation. After Pass 2 / Pass 3 re-pushed the touched session-dirs, 161 legacy-keyed rows (`brief`, `d1`, `d2`, `plan`, `hist`, `draft`, `histp`) appeared in `turn_prompt_pieces` because the events still carry the legacy 8-key vocab. A one-shot SQL DELETE cleaned them up. **Documented risk**: any future `dual-research --push` of a pre-0145 historical run will re-introduce these rows; the cleanup needs to re-run.

- **Pass 2 (D05) — `inputs/input.json` backfill + push.** 21 session-dirs got a persisted `_persist_initial_brief_bundle()` write locally, then `dual-research --push` to Supabase. The hosted UI now serves `system_source="recorded"` for every pre-0142 run (vs the spec-0085 `agent-default` caveat). 1 dir (the anchor) already had a persisted file from spec 0142 — Pass 2 skipped it; Pass 3 later translated its legacy-keyed content.

- **Pass 3 (per-turn bundles + pre-spec-0145 input.json files) — `inputs/*.json` key translation.** 235 per-turn `phase{N}_round*_<agent>.json` files across 7 sessions + the anchor's pre-0145 `input.json` translated in place (text values byte-identical, keys flipped legacy → canonical). Phase number derived from the filename; phase-aware system-key resolution preserved. Pushed via a minimal `_push_inputs_dir_only` helper that uploads ONLY the `inputs/*.json` rows (the full push pipeline overshot Supabase's `statement_timeout` on the multi-MB transcript files — the events / blobs / runs rows are already in Supabase from earlier pushes).

### Deletions (Phase E — five surfaces)

- **`artifacts.jsx`**: `LEGACY_KEY_TO_CANONICAL` (8-key map), `LEGACY_SYSTEM_BY_PHASE` (phase-aware system resolver), `canonicaliseLegacyKey()`, `canonicalisePieces()`, `hasCanonicalKey()`. `window.DrArtifacts` is back to its spec-0117 surface + the spec-0145 `phaseOrderFor` helper.
- **`run-detail.jsx`**: `LEGACY_PIECE_KEYS` Set, `LEGACY_PIECE_LABELS` map, `hasNewVocabPieces()`, `legacyGroupPieces()`, plus the legacy-vocab dispatch branch in `CcxCard` (`isNewVocab ? groupPiecesForPhase : legacyGroupPieces` collapsed to `groupPiecesForPhase` directly). Two `canonicalisePieces` call sites in `InputTabContent` and `PreflightResponseModal` simplified to `bundle.pieces` directly. Replacement `SYNTHETIC_ROW_LABELS = { user_prompt: 'User prompt' }` map covers the FE-only synthetic aggregate row's label (which used to resolve via the bare `user_prompt` ArtifactDef).
- **`contract/artifacts.py`**: legacy single-segment `ArtifactDef("user_prompt", "User prompt", …)` removed. `_CANONICAL_SINGLE_SEGMENT_IDS` in `ui/server.py` derives at import time from the registry; it self-pruned to exactly `{current_draft, all_p2_turns, all_carry_forward}` (3 entries; was 4).
- **`protocol/prompts.py`**: `LEGACY_INPUT_BUNDLE_KEYS` 8-tuple removed.
- **`ui/aggregator.py` + `ui/server.py`**: `build_phase0_input_bundle()` removed, plus its two call sites — the FS-mode synth in `_read_input_bundle_fs:1247` and the inline Supabase-mode synth in `_read_input_bundle_supabase:1517-1533`. Missing `inputs/input.json` post-deletion returns `None` (404 to the FE) — every pre-0142 run was backfilled with a persisted bundle in Pass 2, so the 404 path is unreachable in practice.

Cache-buster bumped `?v=0149a → ?v=0150a` across all 25 static-asset imports in `index.html`.

### Three impl-time follow-ups (out of original spec scope but in-scope for correctness)

These three were discovered during real-data Phase B / C / F runs; each is a small, surgical fix that prevents a known regression:

1. **`aggregator.py:_on_turn_inputs` idempotency guard.** The serve mode replays events to compute snapshots; the writer used to overwrite existing `inputs/<key>.json` files on every replay. For historical runs whose `turn_inputs` events still carry the legacy 8-key vocab, that overwrote backfilled canonical files with legacy data on every page load. The serve became its own restore-from-Supabase loop, silently undoing the backfill. **Guard**: `if path.exists(): return` (still stamps `input_path` on the run snapshot). The orchestrator's first write still lands (the file doesn't exist yet on first emission).

2. **`live-data.jsx:useInputBundle` cache-buster.** The spec-0079 `_IMMUTABLE_CACHE_CONTROL = "public, max-age=86400, immutable"` header on `inputs/*.json` responses meant any browser with a pre-deploy cached response would serve the legacy-keyed bundle to the shim-deleted FE for up to 24h — rendering pre-0145 runs' per-turn input modals into the "Derived inputs" catch-all bucket (because `sectionFor()` only matches canonical prefixes). **Fix**: appended `?v=0150` to the fetch URL in `useInputBundle`. The query-param change forces a fresh fetch from any browser; the new response (canonical post-backfill) gets cached for the next 24h under the new URL.

3. **`persistence/remote.py:push_session_dir` dedup.** Retried turns can produce two `turn_ended` events with the same `(agent, phase, label)` → same `_derive_turn_key` → same artifact rows. Postgres rejects duplicates within a single upsert batch ("ON CONFLICT DO UPDATE command cannot affect row a second time"). **Fix**: collapse `(run_id, turn_key, artifact_id)` duplicates into a dict-keyed bucket (latest occurrence wins) before the batched upsert. Matches one-row-at-a-time upsert semantics.

## Files touched

### Backend (Python)
- [`src/dual_research/contract/artifacts.py`](../src/dual_research/contract/artifacts.py) — legacy `user_prompt` ArtifactDef removed.
- [`src/dual_research/protocol/prompts.py`](../src/dual_research/protocol/prompts.py) — `LEGACY_INPUT_BUNDLE_KEYS` removed.
- [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py) — `build_phase0_input_bundle()` removed; `_on_turn_inputs` idempotency guard added.
- [`src/dual_research/ui/server.py`](../src/dual_research/ui/server.py) — both synth-fallback call sites removed (FS + Supabase modes).
- [`src/dual_research/orchestrator/run.py`](../src/dual_research/orchestrator/run.py) — docstring updated (mention of deleted function dropped).
- [`src/dual_research/persistence/remote.py`](../src/dual_research/persistence/remote.py) — pre-batch dedup for the pieces upsert.

### Frontend (JSX)
- [`src/dual_research/ui/static/artifacts.jsx`](../src/dual_research/ui/static/artifacts.jsx) — shim block + window exports removed.
- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — legacy-vocab detection + label map + dispatch branch removed; `canonicalisePieces` call sites simplified; `SYNTHETIC_ROW_LABELS` map added for the FE-only synthetic `user_prompt` aggregate.
- [`src/dual_research/ui/static/live-data.jsx`](../src/dual_research/ui/static/live-data.jsx) — `useInputBundle` fetch URL gained `?v=0150` cache-buster.
- [`src/dual_research/ui/static/index.html`](../src/dual_research/ui/static/index.html) — cache-buster `0149a → 0150a` (25 imports).

### Scripts / data
- [`scripts/backfill_legacy_shim.py`](../scripts/backfill_legacy_shim.py) — new; three-pass backfill with retry + minimal-push helpers.

### Tests
- [`tests/scripts/test_backfill_legacy_shim_spec_0150.py`](../tests/scripts/test_backfill_legacy_shim_spec_0150.py) — new; 33 cases on the translation table + Pass 3 plumbing.
- [`tests/persistence/test_backfill_idempotency_spec_0150.py`](../tests/persistence/test_backfill_idempotency_spec_0150.py) — new; 6 cases on the D15 idempotency pin.
- [`tests/contract/test_artifact_registry_post_0150.py`](../tests/contract/test_artifact_registry_post_0150.py) — new; 2 cases asserting the post-deletion registry shape + allowlist self-pruning.
- [`tests/ui/test_aggregator_input_bundles.py`](../tests/ui/test_aggregator_input_bundles.py) — `build_phase0_input_bundle` import + 4 test cases retired.
- [`tests/protocol/test_input_bundles.py`](../tests/protocol/test_input_bundles.py) — `LEGACY_INPUT_BUNDLE_KEYS` import + 1 pin test retired.
- [`tests/contract/test_artifacts.py`](../tests/contract/test_artifacts.py) — bare `user_prompt` references in 3 normative tables removed.
- [`tests/ui/test_to_camel_spec_0148.py`](../tests/ui/test_to_camel_spec_0148.py) — allowlist assertion updated from `expected_minimum = {…4 items…}` to `expected == {…3 items…}` (exact equality now).
- [`tests/ui/test_server_input_bundles.py`](../tests/ui/test_server_input_bundles.py) — Phase-0 synth test inverted to assert 404 instead of 200.
- [`tests/spec0145/test_aggregator_passthrough.py`](../tests/spec0145/test_aggregator_passthrough.py) — anchor-shape fixture key updated from bare `user_prompt` to `user_prompt.message`.

### Misc
- [`pyproject.toml`](../pyproject.toml), [`src/dual_research/__init__.py`](../src/dual_research/__init__.py), [`uv.lock`](../uv.lock) — `1.14.0 → 1.15.0`.
- [`CHANGELOG.md`](../CHANGELOG.md) — `[1.15.0]` entry.

## Phase B — dry-run audit counts (surfaced to operator before Phase C)

### Pass 1 (D15)
- Total runs with `turn_ended` events: **18**
- Runs already backfilled: 0 (pre-execute)
- Runs to backfill: **18**
- Total (run_id, turn_key) pairs: **289**
- Total artifact rows to write: **1,232**
- Events with missing/invalid `phase` field: **0** ✅
- Legacy/canonical translation conflicts: **0** ✅

### Pass 2 (D05)
- Total `runs/*/` directories: **22**
- Dirs with `brief.md`: 22
- Dirs lacking `inputs/input.json`: **21**
- Dirs skipped (no `brief.md`): 0

### Pass 3 (per-turn bundles, added mid-execute after surfacing the gap to operator)
- Total `inputs/*.json` files (incl. input.json post-spec-0150): 265
- Legacy-keyed files to translate: **235** (Pass 3 first run) + **40** (after re-enabling `input.json` scan) = 275
- Files with mixed legacy+canonical keys: **0** ✅
- Files lacking phase prefix in filename: 1 (the anchor's `input.json`)

## Phase C — execute outcomes

- **Pass 1**: ~1,196 canonical rows landed in `turn_prompt_pieces` across 10 runs (some empty-pieces runs contributed 0 rows). One-shot SQL cleanup deleted 161 legacy-keyed rows that the post-Pass-2/3 push re-introduced (per the "documented risk" above).
- **Pass 2**: 21 `inputs/input.json` files written locally + pushed to Supabase. `session_files` row counts for `path=like.inputs%` jumped accordingly.
- **Pass 3**: 235 + 40 = 275 per-turn / pre-spec-0145-input.json files translated in place across 7 + 1 = 8 candidate sessions, then pushed via the minimal `_push_inputs_dir_only` helper.

## Phase D / Phase F — visual identity check

Local preview (post-restart on v1.15.0 + canonical local data + post-deletion JSX + cache-busted `useInputBundle`):
- Anchor run-detail page: timeline / critique chips / metadata top-bar render identical to baseline.
- Consumption tab: per-round token rows / cache-reuse stripes / total bars match baseline.
- InputBriefModal (Claude turn 1 → Phase 0): title "User prompt" (from `SYNTHETIC_ROW_LABELS` since the registry no longer has the bare entry); SYSTEM PROMPT section (1 piece) + USER PROMPT section (1 piece, expanded by default); NO "Derived inputs" bucket. **Matches baseline exactly.**

Visual identity gate: **passed**. Phase F's rollback path (per Open Question 4) was not engaged.

## Open-question resolutions (spec §8)

1. **`build_phase0_input_bundle()`'s consumer error path.** Resolved: returns `None` (translates to HTTP 404 via the FastAPI handler). Post-backfill, every pre-0142 run has a persisted `inputs/input.json` so the 404 path is unreachable in practice. The FE's existing 404-handling in `useInputBundle` renders the "No agent input bundle available for this turn." empty state — clean.

2. **Translation table location.** Resolved: inline in `scripts/backfill_legacy_shim.py` as `LEGACY_KEY_TO_CANONICAL` + `LEGACY_SYSTEM_BY_PHASE` module-level constants. The one-shot script's table is dead code after deletion; keeping it in `contract/` would have outlived the cleanup unnecessarily.

3. **Supabase `runs` column for last-backfill timestamp.** Resolved: skipped. The idempotency check via `_load_existing_piece_run_ids()` (presence in `turn_prompt_pieces`) covers Pass 1; the on-disk file-existence check covers Pass 2; the per-key legacy-vs-canonical scan covers Pass 3. No extra column needed.

4. **Rollback policy if Phase F divergence.** Resolved: `git revert` the deletion PR but leave backfilled data in place (the canonical rows / files are correct under both the shim-present and shim-absent paths). **Not engaged**: Phase F visual identity matched baseline.

## Deploy status

- **Version**: `1.15.0`
- **Deploy timestamp**: 2026-05-22T~03:00Z
- **Live health**: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.15.0","backend":"supabase"}` (consistent).
- **D24 ninth-in-a-row timeout fired.** Machine `148ee320f427e8` reached `stopped` when the machines.dev API timed out waiting on health checks. Recovered via `fly machine start 148ee320f427e8 -a dual-research-alex` (~8 seconds). Machine `d8d04d3fe402d8` passed health first try. **D24 stays operator-deferred** per the 0149 carry-forward; the cumulative count is now nine-in-a-row.

### Smoke

- **Hosted health**: v1.15.0 ✓
- **Hosted bundle markers**: `curl https://dual-research-alex.fly.dev/run-detail.jsx?v=0150a | grep -c SYNTHETIC_ROW_LABELS` → 3 (the replacement label map is present); shim-residue grep returns **0** (no `LEGACY_KEY_TO_CANONICAL`, `canonicaliseLegacyKey`, `LEGACY_PIECE_LABELS`, `hasNewVocabPieces`, `legacyGroupPieces` on the wire).
- **Local preview**: full Phase F equivalent run on `localhost:6173` against the canonical local data set. Modal title + section bucketing + populated-piece counts identical to the pre-deletion baseline.

## Documented operational risk for the future

The push-pipeline's `_iter_turn_prompt_pieces_rows` writes `prompt_pieces` keys VERBATIM from the event payload — no legacy → canonical translation. If anyone re-pushes a pre-0145 historical run via `dual-research --push <run>`, 7 legacy-keyed rows (`brief`, `d1`, `d2`, `plan`, `hist`, `draft`, `histp`) will re-appear in `turn_prompt_pieces` for that run. The cleanup snippet:

```python
LEGACY_KEYS = ['brief','d1','d2','plan','hist','draft','histp']
for k in LEGACY_KEYS:
    client.table('turn_prompt_pieces').delete().eq('artifact_id', k).execute()
```

Adding translation to the push pipeline was considered (this spec's `scripts/backfill_legacy_shim.py:plan_pass1` does it via `translate_prompt_pieces`); deferred because shim-like behaviour in the push pipeline is the same logical compatibility surface we just spent 90 days retiring elsewhere. Re-pushing a pre-0145 run is operationally rare; if it becomes common, ship a follow-up.

## Tests

```
1460 passed in 11.31s
```

Up from 1404 (Spec 0149 baseline) — **+56 net**: 33 new in `tests/scripts/test_backfill_legacy_shim_spec_0150.py` + 6 new in `tests/persistence/test_backfill_idempotency_spec_0150.py` + 2 new in `tests/contract/test_artifact_registry_post_0150.py` = +41 new; offset by retired / updated tests (the `LEGACY_INPUT_BUNDLE_KEYS` pin, the four `build_phase0_input_bundle` cases, the three bare-`user_prompt` registry assertions).

## Audit refresh

[`specs/_post-batch-cleanup-audit.md`](../specs/_post-batch-cleanup-audit.md) updated:

- D15 + D05 struck through; status note bumped to `2026-05-22 — Spec 0150 shipped (v1.15.0). Closed D15 + D05. Audit is code-complete; three operational rows remain (D09, D18, D24).`
- Open-row count: **5 → 3**.

## Outstanding follow-ups

After Spec 0150, **three audit rows remain**, all operational:

- **D09 — fresh-run smoke (deferred to post-spec-0150).** The validation gate for D02 (cache_read > 0 on a Claude turn), D04 (zero net-new `EmptyTurnDetected`), D17 (`search_N` resolution rate ≥ 60%), D18 (validator FP rate), D19 (file-bearing attachment preview branches). Cost: ~$10 LLM + ~15 min.
- **D18 — validator over-flagging measurement.** Purely observational; blocked on D09 data.
- **D24 — fly.io `machines.dev` support ticket.** Operator-deferred. The mid-rolling-deploy timeout fired again on this deploy (ninth consecutive). Filing a support ticket remains overdue.

Additional spec-0150-internal follow-ups (not audit rows; documented for future hands):
- **Phase 0 empty-turn check investigation** (carried from the 0149 handover). The post-0148 explore pass found Phase 0 prompts DO emit RAISE blocks, contradicting the 0149 handover's "Phase 0 always fires `EmptyTurnDetected`" hypothesis. Resolving the contradiction needs D09 data; queue as a v1.15.x mini-spec post-D09.
- **Push-pipeline legacy-key translation.** See the "Documented operational risk" section above.
- **fly auto-deploy + manual-deploy image-hash race investigation.** Carried from 0149 — both v1.14.0 machines reported v1.14.0 but had different image hashes. Did not recur on this deploy (both machines on the same image). Watch on next deploy.

## Spec interpretations worth noting

- **Pass 3 was added mid-execute.** The original spec (§2.1, §2.2) covered only `turn_prompt_pieces` rows and `inputs/input.json`. During Phase D smoke I discovered all 235 per-turn `inputs/phase{N}_round*_<agent>.json` files in pre-0145 runs were still legacy-keyed; after shim deletion the FE's per-turn input modal would mis-bucket every pre-0145 turn into "Derived inputs". Operator greenlit the scope expansion ("Yes — translate + re-push"). Pass 3 + the minimal `_push_inputs_dir_only` helper landed mid-Phase C.
- **Pass 2 + Pass 3 push pipeline used reduced batch sizes** (`EVENT_BATCH_SIZE=5`, `FILE_BATCH_SIZE=5`) via module-attribute monkey-patch. Historical runs carry multi-MB transcripts that blow past Supabase's `statement_timeout` on the default 500-event batches. The monkey-patch is scoped to the backfill push only.
- **The `_on_turn_inputs` idempotency guard is a real production change**, not a one-shot backfill helper. It improves robustness for any future serve replay scenario, not just spec 0150's data. Worth keeping.
- **The `useInputBundle` cache-buster is `?v=0150` (not `?v=0150a`)** — chosen so the URL bump is keyed to the spec / data shape change, not the static-asset cache-buster (which is bumped per-deploy). If a future spec needs to invalidate input bundles again, bump to `?v=0151` etc.
