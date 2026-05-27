---
kind: dev
spec: "0150"
slug: legacy-shim-sunset-and-input-bundle-backfill
title: Legacy-shim sunset + historical input-bundle backfill
type: refactoring
label: refactoring
version_bump: MINOR
target_version: 1.15.0
status: deployed
depends_on: []
complexity: M
created: 2026-05-22
queued_at: ""
started_at: ""
merged_at: "2026-05-22T02:53:03Z"
deployed_at: "2026-05-22T02:53:03Z"
pr: "https://github.com/Lexiz/dual-research/pull/172"
handover: "handoffs/2026-05-22-spec-0150-legacy-shim-sunset-and-input-bundle-backfill.md"
failure_step: ""
source_session: pre-lifecycle-bootstrap
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---
# Spec 0150 — Legacy-shim sunset + historical input-bundle backfill

> Ship bucket: **Retire the dual compatibility layers that have served pre-0145 / pre-0142 runs since 0145 introduced canonical artifact IDs and 0142 introduced the per-turn input bundle. Backfill historical runs into the canonical schema, then delete the JS shim, the legacy aggregate `ArtifactDef`, the `LEGACY_INPUT_BUNDLE_KEYS` tuple, and the input.json synth fallback — in that order. The sequencing is load-bearing: deleting before the backfill is verified complete breaks every historical run.**
> Deadline: **2026-08-19** (90 days post-merge of spec 0145; the queued sunset date the audit and the spec-0145 handover both pin).
> Depends on:
> - **0145** (Canonical prompt-pieces + per-attachment token tracking — registered the canonical `ArtifactDef` IDs and shipped the `turn_prompt_pieces` Supabase table; deliberately left the legacy aggregate `user_prompt` ArtifactDef and the JS read-shim in place for backward compatibility with pre-0145 runs).
> - **0142** (Prompt capture for full-view modals — shipped `_persist_initial_brief_bundle()` to write `inputs/input.json` at session setup AND the `build_phase0_input_bundle()` synth fallback that the UI server uses when the file is absent; the synth fallback is what D05 retires).
> - **0148** (Self-pruning camelCase allowlist — `_CANONICAL_SINGLE_SEGMENT_IDS` derived from `REGISTRY` at import time; this spec drops the legacy single-segment `user_prompt` ArtifactDef and the allowlist self-prunes accordingly).
> - **D01** (Supabase migration `0006_turn_prompt_pieces.sql`, applied 2026-05-22) — the target table the backfill writes into.
> Complexity: **M** — three small workloads (one backfill script, two deletion passes) bundled with a sequencing discipline that's the actual hard part. No new features; one new script; net code is negative.
> Targeted version bump: **MINOR (1.14.0 → 1.15.0)** — no new wire fields, but a deliberate deadline-bound checkpoint; the version bump signals "the 90-day shim window closed cleanly" for future tracking.

---

## 1. Context

Spec 0145 introduced canonical artifact IDs (`user_prompt.message`, `user_prompt.attachment.<id>`, `system.task.<phase>`, `prior_turns.phase<N>`, etc.) and wrote them through the new `turn_prompt_pieces` Supabase table. To avoid breaking the long tail of pre-0145 runs already persisted on production with the legacy 7-key vocabulary (`system`, `brief`, `d1`, `d2`, `plan`, `hist`, `draft`, `histp`), 0145 deliberately kept three compatibility paths in place:

1. **`LEGACY_KEY_TO_CANONICAL` map** in [artifacts.jsx:169-178](src/dual_research/ui/static/artifacts.jsx) — a JavaScript object that translates legacy keys to canonical IDs at display time on the frontend, with a phase-aware `system` resolver at [artifacts.jsx:185-191](src/dual_research/ui/static/artifacts.jsx) that maps `system` + phase id → `system.task.<phase>`.
2. **Legacy `user_prompt` `ArtifactDef`** in [contract/artifacts.py:184](src/dual_research/contract/artifacts.py) — a single-segment aggregate that the canonical `user_prompt.message` + `user_prompt.attachment.<id>` entries (also in the registry, at `:186` and `:188`) were meant to replace.
3. **`LEGACY_INPUT_BUNDLE_KEYS`** in [protocol/prompts.py:1250-1259](src/dual_research/protocol/prompts.py) — the 8-tuple the legacy input bundle uses; referenced by the read-shim at [run-detail.jsx:2134, 2139-2147](src/dual_research/ui/static/run-detail.jsx) to detect "this is a pre-0118 run, route through the legacy path."

Spec 0142 separately introduced `_persist_initial_brief_bundle()` to write `inputs/input.json` at session setup. Pre-0142 runs lack the file on disk; the UI server has a synth fallback at [ui/server.py:1239-1247](src/dual_research/ui/server.py) that calls `build_phase0_input_bundle()` to reconstruct the bundle from `<session_dir>/brief.md`. The fallback works but is structurally weird — every read of a pre-0142 run re-synthesises the bundle on demand instead of having a persisted artifact.

Both compatibility paths were tagged at creation time with a 90-day expiry. **The audit pinned 2026-08-19 as the sunset deadline** (90 days post-merge of spec 0145 on 2026-05-21). The reasoning, in plain terms:

- Compatibility paths are easy to add and hard to keep correct. Each subsequent spec has to think about both shapes (e.g. spec 0148's `DYNAMIC_SEPARATE_KEYS` had to be careful not to fire on legacy-vocab runs).
- The fall-through behaviour is silent. A pre-0145 run rendering via the legacy path looks the same as a post-0145 run; bugs in the shim only surface when historical-run behaviour diverges from forward-run behaviour, which nobody is actively checking.
- Both paths are write-once: pre-0145 runs that exist now will exist forever, and migrating them once is cheaper than carrying the shim indefinitely.

This spec backfills both data shapes into their canonical form, then deletes the compatibility paths. D15 (the audit's row name) and D05 (the audit's input-bundle backfill row name) are consolidated into a single spec because both backfills can ride one historical-runs sweep — the loop body iterates `runs/*/`, reads what's there, writes what's missing.

After this spec lands, the audit drops from five open rows to three: D09 (the deferred fresh-run smoke that validates 0149's hypothesis-driven fixes), D18 (validator over-flagging, blocked on D09), and D24 (the fly support ticket, operator-deferred). All three are operational, not code.

---

## 2. Goals

1. **Backfill `events.payload.prompt_pieces` JSONB → `turn_prompt_pieces` table.** Every historical run on production Supabase that has at least one `turn_ended` event carrying a `prompt_pieces` payload but zero rows in `turn_prompt_pieces` gets its pieces migrated. Idempotent; safe to re-run. Maps legacy keys to canonical IDs at write time using the same translation `LEGACY_KEY_TO_CANONICAL` performs on the frontend today.

2. **Backfill `inputs/input.json` into every historical run that has a `brief.md` but no persisted bundle.** Loops over `runs/*/`, calls `_persist_initial_brief_bundle()` for each match. Idempotent; pre-0142 runs gain a persisted artifact, post-0142 runs are skipped.

3. **Delete `LEGACY_KEY_TO_CANONICAL` + the phase-aware `system` resolver** from [artifacts.jsx](src/dual_research/ui/static/artifacts.jsx). After deletion, the frontend reads canonical IDs only; historical runs render correctly because the backfill in §2.1 has written canonical IDs into `turn_prompt_pieces`.

4. **Delete the 7-key legacy vocabulary read-shim** at [run-detail.jsx:2134, 2139-2147](src/dual_research/ui/static/run-detail.jsx). The legacy-vocab detection branch + the `LEGACY_PIECE_LABELS` display map both retire.

5. **Delete `LEGACY_INPUT_BUNDLE_KEYS`** from [protocol/prompts.py:1250-1259](src/dual_research/protocol/prompts.py). After deletion, no Python or JS code references the legacy 8-tuple.

6. **Delete the legacy single-segment `user_prompt` `ArtifactDef`** from [contract/artifacts.py:184](src/dual_research/contract/artifacts.py). The canonical `user_prompt.message` and `user_prompt.attachment.<id>` entries (registry lines `:186, :188`) remain. Spec 0148's `_CANONICAL_SINGLE_SEGMENT_IDS` self-prunes — `user_prompt` no longer rides the camelCase allowlist.

7. **Delete the `build_phase0_input_bundle()` synth fallback** at [ui/server.py:1239-1247](src/dual_research/ui/server.py). After §2.2 has run, every historical run with a `brief.md` has a persisted `inputs/input.json`; the synth path becomes unreachable code and goes away.

8. **End-to-end verification before any deletion.** A pinned set of pre-0145 historical runs (sampled across phases and complexity) renders identically before and after the shim deletion. Identity is asserted at the rendered-DOM level (CcxCard rows, modal contents) by manual visual inspection — no Jest harness today, per spec-0148 / 0149 carve-outs.

---

## 3. Non-goals

- **No new wire fields, no protocol changes, no new prompt language.** This is a tech-debt-removal spec; behaviour on forward runs is unchanged.
- **No `turn_prompt_pieces` schema change.** Migration `0006` already covers the table shape; the backfill writes into the existing columns.
- **No retroactive re-pricing of historical runs.** Backfilling `prompt_pieces` doesn't change any historical `metrics.json`; cost numbers stay frozen.
- **No JS / Python migration tooling for downstream consumers.** No third party reads the wire shape; the only consumer is the bundled UI server + frontend, deployed atomically.
- **No D09 fresh-run smoke.** Operator-deferred; this spec ships against the existing historical-runs corpus and the anchor run, both of which pre-date the shim retirement.
- **No D24 fly support ticket.** Operator-deferred per the 0149 handover; the ninth-consecutive `machines.dev` deploy timeout (if it fires here) gets logged but not escalated.
- **No D18 validator over-flagging measurement.** Same blocked-on-D09 status as in 0149's non-goals.
- **No Phase 0 empty-turn check correction.** The operator-flagged discovery from 0149's handover (Phase 0 may fire `EmptyTurnDetected` unconditionally) was tentatively investigated: the explore pass found Phase 0 prompts DO emit RAISE blocks (`preflight_prompt` at [prompts.py:137-176](src/dual_research/protocol/prompts.py); `preflight_prompt_v2` at `:1542`), which contradicts the handover's assumption. Either the assumption was wrong or there's a sub-case (e.g. specific Phase 0 turn shapes where no RAISE fires); resolving the contradiction is orthogonal to legacy-shim sunset and risks cross-contaminating a sequencing-critical change. **Out of scope for 0150; queued as a separate v1.15.x mini-spec after D09 produces actual Phase 0 `EmptyTurnDetected` data.**
- **No fly auto-deploy + manual-deploy race investigation.** Operator-flagged from 0149 (the two distinct image hashes on the v1.14.0 machines); this is an ops investigation, not a dual-research code change.
- **No diagram updates.** D21 closed in 0149 as a narrow annotation. The legacy-shim retirement doesn't add or remove canonical IDs; no diagram change needed.
- **No CHANGELOG entry for the backfill row counts.** The CHANGELOG documents user-facing behaviour; historical-row backfill is internal. The 0150 handover carries the row counts for operator records.

---

## 4. Current-state audit

### 4.1 — Frontend shim surfaces (D15)

| File | Lines | Role |
|---|---|---|
| [`src/dual_research/ui/static/artifacts.jsx`](src/dual_research/ui/static/artifacts.jsx) | 169–178 | `LEGACY_KEY_TO_CANONICAL` object. 8 keys → canonical IDs. |
| [`src/dual_research/ui/static/artifacts.jsx`](src/dual_research/ui/static/artifacts.jsx) | 185–191 | Phase-aware `system` resolver. Maps `system` + phase id → `system.task.<phase>`. |
| [`src/dual_research/ui/static/artifacts.jsx`](src/dual_research/ui/static/artifacts.jsx) | 193 | `canonicaliseLegacyKey()` — the function that applies the map. Grep for callers before deletion. |
| [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) | 2134 | Legacy-vocab detection (presence test for the 7-key set). |
| [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) | 2139–2147 | `LEGACY_PIECE_LABELS` display map; routes legacy keys to display names. |

After deletion: zero readers of legacy keys on the FE. Every historical run renders via the canonical path because §2.1's backfill has written canonical IDs into `turn_prompt_pieces`.

### 4.2 — Python shim surfaces (D15)

| File | Lines | Role |
|---|---|---|
| [`src/dual_research/contract/artifacts.py`](src/dual_research/contract/artifacts.py) | 184 | Legacy single-segment `user_prompt` `ArtifactDef`. Drop entirely. |
| [`src/dual_research/contract/artifacts.py`](src/dual_research/contract/artifacts.py) | 186 | Canonical `user_prompt.message` `ArtifactDef`. Keep. |
| [`src/dual_research/contract/artifacts.py`](src/dual_research/contract/artifacts.py) | 188 | Canonical `user_prompt.attachment.<id>` `ArtifactDef`. Keep. |
| [`src/dual_research/protocol/prompts.py`](src/dual_research/protocol/prompts.py) | 1250–1259 | `LEGACY_INPUT_BUNDLE_KEYS` 8-tuple. Drop. Grep for callers before deletion. |
| [`src/dual_research/ui/server.py`](src/dual_research/ui/server.py) | 1239–1247 | `build_phase0_input_bundle()` synth fallback for missing `inputs/input.json`. Drop after §2.2's backfill completes. |

After deletion: zero Python readers of the legacy aggregate, the legacy 8-tuple, or the synth fallback. The post-0148 `_CANONICAL_SINGLE_SEGMENT_IDS` allowlist self-prunes the `user_prompt` entry (was `{user_prompt, current_draft, all_p2_turns, all_carry_forward}`; becomes `{current_draft, all_p2_turns, all_carry_forward}`).

### 4.3 — Supabase backfill source/target (D15 §2.1)

| Layer | File | Lines | Role |
|---|---|---|---|
| Source (JSONB) | [`src/dual_research/persistence/remote.py`](src/dual_research/persistence/remote.py) | 474 | Reads `payload.get("prompt_pieces")` from `events` rows where `kind = 'turn_ended'`. The JSONB structure the backfill iterates. |
| Target (table) | [`src/dual_research/persistence/remote.py`](src/dual_research/persistence/remote.py) | 417–452 | `_push_turn_prompt_pieces()` — the existing upsert helper that writes one row per `(run_id, turn_key, artifact_id)`. The backfill reuses this. |
| Target driver | [`src/dual_research/persistence/remote.py`](src/dual_research/persistence/remote.py) | 455 | `_iter_turn_prompt_pieces_rows()` — yields the row tuples the upsert helper consumes. The backfill mirrors its row-yielding logic. |

Supabase table shape (from migration `0006_turn_prompt_pieces.sql`, applied 2026-05-22):

```
turn_prompt_pieces (
    run_id          TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    turn_key        TEXT NOT NULL,
    artifact_id     TEXT NOT NULL,
    tokens          INT NOT NULL,
    attachment_id   TEXT,
    display_title   TEXT,
    PRIMARY KEY (run_id, turn_key, artifact_id)
)
```

### 4.4 — Input-bundle backfill source/target (D05 §2.2)

| Layer | File | Lines | Role |
|---|---|---|---|
| Backfill function | [`src/dual_research/orchestrator/run.py`](src/dual_research/orchestrator/run.py) | 253–277 | `_persist_initial_brief_bundle()` — writes `inputs/input.json` once at session setup. Idempotent on resume. |
| Source file | (per session dir) | — | `<session_dir>/brief.md` — confirmed at `<session_dir>/brief.md` per [aggregator.py:601](src/dual_research/ui/aggregator.py), [cli.py:288, :395, :399](src/dual_research/cli.py). |
| Target file | (per session dir) | — | `<session_dir>/inputs/input.json`. Absence is the signal the synth fallback triggers on. |

### 4.5 — Allowlist self-pruning (D16 carry-over from 0148)

| File | Lines | Role |
|---|---|---|
| [`src/dual_research/ui/server.py`](src/dual_research/ui/server.py) | (search at impl time — `_CANONICAL_SINGLE_SEGMENT_IDS`) | Derived at import time from `contract.artifacts.REGISTRY` by filtering for `ArtifactDef.id` without a `.` and without a `<...>` placeholder. Dropping the legacy `user_prompt` entry auto-prunes it from the allowlist without code change. Verification: post-deletion, the allowlist contains exactly `{current_draft, all_p2_turns, all_carry_forward}`. |

---

## 5. Proposed change

### 5.1 — Phase A: write the backfill script (no production reads/writes yet)

New script at `scripts/backfill_legacy_shim.py`:

```python
#!/usr/bin/env python3
"""Spec 0150 — backfill historical runs into canonical schema.

Two passes:
  1. (D15) Read `events.payload.prompt_pieces` JSONB on Supabase for every
     run with at least one `turn_ended` event; write canonical-ID rows into
     `turn_prompt_pieces` for any (run_id, turn_key) pair that has zero rows
     today. Idempotent: re-runs skip already-backfilled pairs.
  2. (D05) Loop `runs/*/`; for each session dir with `brief.md` AND no
     `inputs/input.json`, call `_persist_initial_brief_bundle()` to write
     the persisted bundle. Idempotent: re-runs skip already-persisted dirs.

Flags:
  --dry-run   : enumerate work but write nothing
  --pass=1    : run only D15 pass
  --pass=2    : run only D05 pass
  --limit=N   : process at most N runs (D15 pass; for incremental rollout)
"""
```

Translation policy for legacy keys (D15 pass): apply the same mapping `LEGACY_KEY_TO_CANONICAL` performs today, mirrored from [artifacts.jsx:169–191](src/dual_research/ui/static/artifacts.jsx) into a Python `LEGACY_KEY_TO_CANONICAL` dict alongside the script. Phase-aware resolution for the `system` key uses the event's `phase` field.

Edge case: an event whose `prompt_pieces` dict contains BOTH legacy and canonical keys (a transitional state from runs that straddled the 0145 deploy boundary). Policy: prefer canonical when both are present for the same conceptual artifact; otherwise translate the legacy key. The unit test pins this policy.

### 5.2 — Phase B: dry-run + audit

Run `scripts/backfill_legacy_shim.py --dry-run --pass=1` against production Supabase. Capture the count of:
- Total runs with `turn_ended` events
- Runs with zero `turn_prompt_pieces` rows (the backfill candidates)
- Total `(run_id, turn_key)` pairs to backfill
- Total artifact rows to write

Run `scripts/backfill_legacy_shim.py --dry-run --pass=2`. Capture:
- Total `runs/*/` directories with `brief.md`
- Of those, how many lack `inputs/input.json`

Surface both counts to the operator in the impl handover. **No deletions begin until both counts are reviewed and approved.**

### 5.3 — Phase C: execute the backfill

Run `scripts/backfill_legacy_shim.py --pass=1` (no `--dry-run`) against production Supabase. Capture output for the handover.

Re-run the dry-run; the candidate count must drop to zero (idempotency check).

Run `scripts/backfill_legacy_shim.py --pass=2`. Capture output for the handover.

### 5.4 — Phase D: post-backfill rendering smoke (pre-deletion)

Pin a small set (3–5) of pre-0145 historical runs. For each, open the hosted UI (still serving the shim-enabled v1.14.0 bundle) and screenshot:
- Run-detail page top-bar
- Consumption-card unfolded view (CcxCard) for one Claude turn + one OpenAI turn
- Initial Brief modal
- The first Phase 0 / Phase 2 / Phase 4 timeline card with critique items

**These are the pre-deletion baseline screenshots.** Used in §5.6 as the diff target.

### 5.5 — Phase E: delete the shim code

In one PR, delete in order:

1. **Frontend** (in [artifacts.jsx](src/dual_research/ui/static/artifacts.jsx)): `LEGACY_KEY_TO_CANONICAL` (lines 169–178), phase-aware `system` resolver (lines 185–191), `canonicaliseLegacyKey()` (line 193). Grep all callers; expected to be referenced only from the legacy-detection branch in `run-detail.jsx` (which §5.5.2 deletes in the same change).
2. **Frontend** (in [run-detail.jsx](src/dual_research/ui/static/run-detail.jsx)): the legacy-vocab detection branch (line 2134) + `LEGACY_PIECE_LABELS` (lines 2139–2147). Replace with: the canonical-only render path becomes the single render path; no branch.
3. **Python** (in [contract/artifacts.py:184](src/dual_research/contract/artifacts.py)): delete the legacy `user_prompt` `ArtifactDef` entry. Pre-grep: `grep -rn '"user_prompt"' src/` and verify no caller uses the single-segment ID directly (callers should use `user_prompt.message` and `user_prompt.attachment.<id>` instead).
4. **Python** (in [protocol/prompts.py:1250–1259](src/dual_research/protocol/prompts.py)): delete `LEGACY_INPUT_BUNDLE_KEYS`. Pre-grep: `grep -rn 'LEGACY_INPUT_BUNDLE_KEYS' src/` and verify no remaining callers.
5. **Python** (in [ui/server.py:1239–1247](src/dual_research/ui/server.py)): delete `build_phase0_input_bundle()`. The "input.json missing" branch in the consuming endpoint becomes an error path (return 500 or 404 — confirm pattern at impl time) rather than a synth fallback.

Cache-buster bump: `?v=0149a → ?v=0150a` across the 25 static-asset imports in [index.html](src/dual_research/ui/static/index.html).

### 5.6 — Phase F: post-deletion verification (post-deploy)

Re-screenshot the same 3–5 pinned historical runs on the freshly-deployed v1.15.0. Compare against §5.4's baseline:

- Identical content in each surface
- Specifically: the consumption card's `Total tokens` bar, per-piece sub-rows, and totals block match number-for-number
- Initial Brief modal renders the same prompt text
- Timeline cards' critique-item content unchanged

Any divergence is a backfill bug (or shim-deletion bug); rollback path is `git revert` of the shim-deletion PR (the backfilled data stays — it's still correct under the canonical path; only the FE/Python deletion gets unwound).

### 5.7 — Phase G: handover + audit refresh

Standard handover at `handoffs/2026-MM-DD-spec-0150-legacy-shim-sunset-and-input-bundle-backfill.md`. Refresh `specs/_post-batch-cleanup-audit.md` to strike D15 + D05; the audit's open-row count drops from 5 to 3 (D09, D18, D24 remain — all operational).

---

## 6. Test plan

- [ ] **Unit (`tests/scripts/test_backfill_legacy_shim_spec_0150.py`)** — pin the legacy → canonical translation table, including the both-keys-present edge case from §5.1. 8 cases minimum (one per legacy key + edge case).
- [ ] **Unit (`tests/persistence/test_backfill_idempotency_spec_0150.py`)** — fixture Supabase mock; running the backfill twice produces the same row count after the first pass. No duplicate-key errors (the upsert helper handles this, but the test pins behaviour).
- [ ] **Unit (`tests/contract/test_artifact_registry_post_0150.py`)** — after the registry change, `REGISTRY` contains `user_prompt.message` and `user_prompt.attachment.<id>` but NOT a bare `user_prompt` entry. `_CANONICAL_SINGLE_SEGMENT_IDS` import-time derivation produces `{current_draft, all_p2_turns, all_carry_forward}` (exactly 3 items, was 4).
- [ ] **Grep gate (`tests/test_legacy_shim_zero_residue_spec_0150.py` or scripted check)** — after deletion:
  - `grep -rn 'LEGACY_KEY_TO_CANONICAL\|canonicaliseLegacyKey\|LEGACY_PIECE_LABELS\|LEGACY_INPUT_BUNDLE_KEYS\|build_phase0_input_bundle' src/` returns zero hits.
  - `grep -rn 'ArtifactDef("user_prompt"' src/` returns zero hits (the canonical entries use `user_prompt.message` and `user_prompt.attachment.<id>`).
- [ ] **Backfill dry-run** — §5.2's counts are captured and reviewed before §5.3 executes.
- [ ] **Backfill execute** — §5.3 reports completion; idempotency re-run reports zero candidates.
- [ ] **Visual identity** — §5.4 vs §5.6 screenshots diff to zero meaningful changes across the pinned historical-run set.
- [ ] **Full pytest** — passes; expected delta is +~12 new tests (8 translation + 2 idempotency + 1 registry shape + 1 `_CANONICAL_SINGLE_SEGMENT_IDS` size). Minus zero existing tests (the shim deletion doesn't break any existing assertion if the backfill is correct).
- [ ] **Anchor run** — `20260521-010637-dvs-backend-language-choice` is post-0145, so it doesn't carry legacy keys in `events.payload.prompt_pieces`. The backfill pass for the anchor is a no-op; document explicitly in the handover.
- [ ] **D05 spot-check** — pick one pre-0142 run (any session in `runs/` lacking `inputs/input.json`); after §5.3 pass 2, verify the file exists and matches the runtime-synthesised shape that the deleted `build_phase0_input_bundle()` would have produced. Test fixture: load both, assert equal.

---

## 7. Risks

- **Backfill data divergence.** If `LEGACY_KEY_TO_CANONICAL` in the JS shim and the Python translation table in the script disagree, the FE post-deletion will render historical runs with subtly different piece IDs than the FE pre-deletion did with the shim. Mitigation: the Python translation table is a direct copy of the JS map, both pinned by `test_backfill_legacy_shim_spec_0150.py`. The visual identity check in §5.6 catches any residual divergence.
- **Phase-aware `system` resolver edge cases.** The shim's `system` resolver depends on the event's `phase` field. If any historical event has `phase` missing or invalid, the translation produces a wrong canonical ID. Mitigation: the script's dry-run flags events with missing `phase`; surface to operator before the execute pass. Document the count in the handover.
- **Both-keys-present transitional events.** Runs that straddled the 0145 deploy boundary may have events with both legacy and canonical keys for the same artifact. Policy in §5.1: prefer canonical. Risk: a real-world event with conflicting tokens between the two surfaces (e.g. legacy says `system: 1000` and canonical says `system.task.preflight: 1100`) silently drops the legacy count. Mitigation: the dry-run logs every both-present case; operator decides whether to ship the prefer-canonical policy or escalate to a per-run reconciliation.
- **Pre-deletion smoke baseline is too narrow.** 3–5 pinned runs may miss a render edge case. Mitigation: choose the pinned set to span Phase 0 / Phase 2 / Phase 4 critique-heavy runs, Phase 4 deadlock runs, runs with attachments, runs without. Surface the chosen set in the §5.2 audit so the operator can extend if they want.
- **Synth-fallback deletion breaks a pre-0142 run that wasn't in the backfill loop.** Most likely cause: a run dir on disk that the loop in §2.2 missed (e.g. one with `brief.md` symlinked rather than a real file, or one in an unusual subdirectory). Mitigation: §5.3 pass 2 logs every dir it processes AND every dir it skipped-with-reason; operator reviews before §5.5 runs.
- **Atomic deletion vs. rollback granularity.** §5.5 deletes five surfaces in one PR. If any single deletion is wrong, the whole PR reverts. Mitigation: this is intentional — partial rollback (e.g. JS deleted, Python kept) leaves the codebase in an internally-inconsistent state worse than either extreme. The PR is small enough (net negative LOC) that review of all five together is feasible.
- **`?v=0150a` cache-buster vs. browser caching.** Users who hard-reload after the deploy get the fresh bundle and render the canonical-only path. Users on an unrefreshed page still serve the v1.14.0 bundle, which reads `turn_prompt_pieces` (already backfilled) but routes through the shim — should still render identically since the shim's translation is a no-op when the data is already canonical. Verify the no-op behaviour at §5.4.
- **Future single-segment canonical ID addition.** If a future spec adds a new single-segment ID, the `_CANONICAL_SINGLE_SEGMENT_IDS` allowlist auto-picks it up. The risk is if the FE expects a snake_case form for the new ID — which would be a per-spec design decision, not a 0150 regression. Out of scope to pre-engineer.
- **Eighth-consecutive (ninth, after this deploy) `machines.dev` timeout.** D24 still un-filed. Risk profile unchanged from 0149's handover; mitigation is the same `fly machine start <id>` recovery. The 0150 deploy will be the ninth-in-a-row if it fires.

---

## 8. Open questions

- **`build_phase0_input_bundle()`'s consumer error path.** When the file is missing post-deletion, what HTTP status should the endpoint return? Likely 404 (resource genuinely doesn't exist) vs 500 (server can't serve what's missing). Confirm at impl time by checking the FE behaviour against both — whichever produces a clean "this run has no input bundle" UI without spurious error toasts is the right answer.
- **Translation table location.** The Python `LEGACY_KEY_TO_CANONICAL` in the backfill script could live (a) inline in the script, (b) in `contract/artifacts.py` as a module-level constant, (c) in a one-off `scripts/_legacy_translation.py`. Lean toward (a) — the script is one-shot and the table is dead code after deletion; keeping it in `contract/` would survive the cleanup. Confirm at impl time.
- **Supabase `runs` table column for last-backfill timestamp.** Optional: add a column to track which runs have been through the backfill so re-runs can short-circuit. Likely not worth it — the idempotency check already short-circuits via "zero `turn_prompt_pieces` rows" detection. Confirm at impl time.
- **Rollback policy if §5.6 finds divergence.** Two choices: (a) `git revert` the deletion PR but leave backfilled data in place (cheap), or (b) `git revert` AND surgically delete the backfilled rows (expensive but cleaner). Lean (a) — the backfilled data is correct under the canonical path; the only thing wrong post-revert is the FE/Python still expecting the shim. Confirm with operator before deletion.
- **Phase 0 empty-turn check follow-up timing.** Out of scope per §3, but: should the follow-up spec land before or after D09's fresh-run smoke? The smoke needs to actually fire `EmptyTurnDetected` on Phase 0 for the follow-up to have data; D09 is the gate. Confirm timing with operator after 0150 ships.

---
