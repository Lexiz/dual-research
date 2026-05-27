---
spec: 0122
title: Persist item lifecycle events to the transcript + backfill historical runs
label: bug
version-bump: PATCH
status: proposed
target-version: 1.4.2
created: 2026-05-20
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0122 — Persist item lifecycle events to the transcript + backfill historical runs

## Context

Spec 0114 introduced the Deep Research operation-block protocol
(`### RAISE` / `### ADDRESS` / `### RESOLVE` / `### ACKNOWLEDGE` /
`### WITHDRAW`). Spec 0115 introduced the unified `Item` model and the
`aggregate_items_from_transcript` UI path that builds per-turn / per-
phase category stats from `item_raised` and `item_transitioned` events
in `transcript.jsonl`. Spec 0119 retired the legacy chip components in
favour of the `phaseLedgers`-backed UI surface, which also derives from
the event stream.

In practice, no item-stream events are landing in `transcript.jsonl`.
`DeepResearchPhase.apply_turn` in
[orchestrator/deep_research.py](src/dual_research/orchestrator/deep_research.py)
produces `ItemRaised` and `ItemTransitioned` objects correctly. The
async driver in
[orchestrator/dr_run.py](src/dual_research/orchestrator/dr_run.py)
publishes them to the `EventBus` via `_publish_round_events`. But the
only `EventBus` subscriber installed in
[orchestrator/run.py](src/dual_research/orchestrator/run.py) is
`_install_transcript_publisher`, which is a misnamed stub that only
re-saves `metrics.json`. Nothing translates published events into
`Transcript.write(...)` calls.

The user-visible symptom: every negotiation-round card in Phase 0 / 2 /
4, every critique-pane filter, and every "open issues / open
disagreements / comments" badge shows zero. The legacy fallback
reconstructors in `ui/disagreements.py`, `ui/issues.py`,
`ui/comments.py`, `ui/questions.py` also return zero, because the round
files now use the spec-0114 section schema
(`## Stance / ## Addressing items raised against me / ## Ratifying my
own items / ## New items I'm raising / ## Status`) which their legacy
regexes don't match.

Concrete evidence (the most recent run,
`runs/20260520-025406-pv-backend-language-choice`):

- `grep -c '"event":"item_raised"' transcript.jsonl` → `0`.
- `grep -c '"event":"item_transitioned"' transcript.jsonl` → `0`.
- `build_run_snapshot(...).phase_ledgers` → `{2: [], 4: []}`.
- `run.questions / disagreements / issues / comments` → all `[]`.
- The round files DO contain well-formed operation blocks plus footers
  like `RAISED_THIS_TURN: [D-plan-c-01, ...]` — the data exists, just
  not in the place the UI looks for it.

## Proposed change

Two cooperating fixes — a bridge for live runs, a backfill for historical
runs. Both feed the same downstream consumer
(`aggregate_items_from_transcript`).

### A. Event-bus → transcript bridge (live runs)

Replace the no-op `_install_transcript_publisher` in
[`orchestrator/run.py`](src/dual_research/orchestrator/run.py) with
`_install_transcript_bridge(bus, transcript)`. It subscribes a single
callback that serialises an allowlist of event types via
`event.to_dict()` and forwards them to `transcript.write(event.kind,
**fields)` (with the `kind` key removed before splat).

Allowlisted event types — chosen because the current code does NOT
already double-write them via direct `transcript.write` calls:

- `ItemRaised`
- `ItemTransitioned`
- `CloseoutUrged`
- `CloseoutViolation`
- `PhaseConverged`

Events that the orchestrator already writes directly (`RunStarted`,
`PhaseEntered`, `PhaseExited`, `TurnStarted`, `TurnEnded`,
`TurnInputs`, `TurnSearches`, `SoftCapHit`, `HardCapHit`,
`Phase{N}Complete`, `RunCompleted`, `RunFailed`, etc.) stay on the
direct path to avoid double-write. The bridge is additive only.

The bridge does NOT change `metrics.json` save-on-event behaviour;
that callback stays installed alongside.

### B. Replay-from-disk backfill (historical + crash-recovered runs)

Add a new module
[`src/dual_research/ledger/replay.py`](src/dual_research/ledger/replay.py)
exposing one public function:

```python
def replay_items_from_disk(session_dir: Path) -> AggregatedItems:
    """Reconstruct the canonical AggregatedItems bundle for a session
    by re-driving DeepResearchPhase over the on-disk round files."""
```

For each phase in `(0, 2, 4)`:

1. Construct a `DeepResearchPhase(phase=N)`.
2. Discover round files (`round-NN-{claude,openai}.md` under
   `phase{N}/`) in round order.
3. For each round, read both agents' files (if present), call
   `parse_turn_v2(text)` on each, then `phase.apply_turn(text=...,
   parsed=..., agent=..., round=..., is_closeout_round=...)`.
4. Call `phase.process_round_end(...)` to detect convergence /
   closeout-urge / ghost-cap / hard-cap transitions; this returns a
   `RoundResult` whose `transition_events` capture orchestrator-
   driven (cap) transitions in addition to the agent-driven ones from
   `apply_turn`.
5. Accumulate every `ItemRaised`, `ItemTransitioned`,
   `CloseoutUrged`, `CloseoutViolation` into the in-memory event list.

After all phases are walked, serialise the events to dicts and feed
them into `aggregate_items(...)` (the same function the live path
uses), returning the resulting `AggregatedItems` bundle.

Update [`ui/aggregator.py`](src/dual_research/ui/aggregator.py)'s
`_attach_item_aggregation` to fall back to the replay path when the
transcript yielded zero items but on-disk round files exist:

```python
bundle = aggregate_items_from_transcript(transcript_path)
if not bundle.items:
    from dual_research.ledger.replay import replay_items_from_disk
    bundle = replay_items_from_disk(session_dir)
```

This makes runs that pre-date the bridge (like the
2026-05-20 run that prompted this spec) light up immediately on UI
reload, without backfilling the transcript file itself.

### C. Reproject `Item` → legacy typed lists + `phase_ledgers`

The frontend still reads `run.questions`, `run.disagreements`,
`run.issues`, `run.comments`, and `run.phaseLedgers[phase]`. These were
populated from the legacy section-schema reconstructors, which now
return `[]`.

Add a single projection step in
[`ui/aggregator.py`](src/dual_research/ui/aggregator.py): when `bundle.items`
is non-empty, derive the four typed lists and the two
`phase_ledgers` entries directly from `bundle.items`. The legacy
reconstructors stay in place for pre-0114 runs (detected by the
absence of any v2 section header on any round file).

Mapping (each `Item` projects into exactly one legacy typed object):

- `Item.kind == "question"` → `Question` (`models.py:180`). Status
  derived from `current_state` (`open` → `open`,
  `addressed`/`resolved` → `answered`, `withdrawn` → `withdrawn`).
- `Item.kind == "disagreement"` → `Disagreement` (`models.py:147`).
  Status: `open` if `current_state == "open"`; otherwise
  `resolved-{raiser}` for `resolved`/`acknowledged`/`withdrawn`. The
  `progression` field is derived from `Item.transitions` (one
  `ProgressionStep` per transition).
- `Item.kind == "issue"` → `Issue` (`models.py:225`). Status: `open` →
  `open`, `resolved` → `fixed`, `addressed` → `addressed`, `withdrawn`
  → `withdrawn`, `acknowledged` → `non_blocking`.
- `Item.kind == "comment"` → `Comment` (`models.py:263`). Always
  `noted`.

`phase_ledgers` is built directly from `bundle.items`: one
`LedgerEntry` per `Item`, with `status_history` mapped 1-to-1 from
`Item.transitions` (`from_state` → `status` of the previous step,
`to_state` → `status` of the new step, `round` / `actor` / `reason`
carried as-is). Phase 1 `claim` entries no longer exist in the spec-
0114 vocabulary (`categories.py:9` lists only Q/D/I/C), so the Phase 1
seed path is dropped for v2 runs.

### D. Per-turn review items (right-pane card body)

`_read_phase_review_items` in
[`ui/aggregator.py`](src/dual_research/ui/aggregator.py:1282) currently
calls the legacy `resolve_review_items` → `extract_review_items`.
Replace its body for v2 turn files with a `parse_turn_v2(text)` walk
that:

1. Reads `parsed.blocks` and `parsed.raised_this_turn`.
2. Pairs each `RaiseBlock` with the matching ID from
   `raised_this_turn` (positional: Nth RAISE block ↔ Nth ID in the
   array).
3. Emits one `ReviewItem` per RaiseBlock with
   `kind = blk.kind.value`, `body = blk.body`,
   `quote = blk.anchor_text if blk.anchor_type == "quote" else None`,
   `after = blk.anchor_text if blk.anchor_type == "after" else None`,
   `item_id = stamped_id`.

`block_id` (anchor pre-resolution) keeps the existing
`assign_block_ids` lookup against prior content.

For legacy section-schema files, the function falls back to
`resolve_review_items` unchanged.

### E. Retire `disagreements_parse_suspected_miss` for v2 runs

This footer banner ("we may have missed some disagreements") only
makes sense for the legacy section schema. For v2 runs, leave it
`False` — the new path either finds items or doesn't, with no false-
positive recovery to surface.

### F. CHANGELOG + cache-bust

- Bump `pyproject.toml` and `src/dual_research/__init__.py` to
  `1.4.2`.
- Add an entry under `[Unreleased]` in `CHANGELOG.md`.
- Cache-bust the UI bundle reference in
  `ui/static/index.html` (per repo convention — append the spec
  identifier to the asset query string).

## Out of scope

- **Reflowing the orchestrator's direct `transcript.write` calls
  through the bus.** That's the natural follow-up cleanup (single
  source of truth for transcript writes), but it touches every phase
  driver and risks regressions; deferred to its own spec.
- **Backfilling `transcript.jsonl` on disk.** The replay path
  reconstructs the bundle in-memory at read time. Persisting the
  reconstructed events into the on-disk transcript would be useful
  for offline analysis but isn't needed for the UI to render.
- **Adding new event types.** The five existing event types
  (`ItemRaised`, `ItemTransitioned`, `CloseoutUrged`,
  `CloseoutViolation`, `PhaseConverged`) are sufficient.
- **Frontend changes.** No `.jsx` / `.css` modifications. The UI
  surfaces already consume `run.phaseLedgers` + the legacy typed
  lists; once those repopulate, the badges and filters light up.

## Test plan

- [ ] **Unit:** `tests/test_transcript_bridge.py` — publish each
  allowlisted event type to a bus with the bridge installed; assert
  the corresponding line appears in `transcript.jsonl` with the right
  `event` field and matching payload.
- [ ] **Unit:** `tests/test_replay_from_disk.py` — fixture session
  with one Phase 2 round file containing two RAISE blocks + one
  Phase 2 round 2 file containing one ADDRESS + one RESOLVE; assert
  `replay_items_from_disk(...)` returns a bundle with the right
  item count, kinds, IDs, and transition history.
- [ ] **Unit:** `tests/test_item_projection.py` — call the new
  projection helper on a synthetic `AggregatedItems` and assert the
  four legacy typed lists and the two `phase_ledgers` entries have
  the expected shape (status mapping, progression count, ledger
  status_history length).
- [ ] **Golden:** load `runs/20260520-025406-pv-backend-language-choice`
  through `build_run_snapshot` and assert:
  - `run.phase_ledgers[2]` is non-empty.
  - `run.phase_ledgers[4]` is non-empty.
  - `len(run.disagreements) > 0`.
  - `len(run.issues) > 0`.
  - `run.phase_stats.items` is non-empty.
- [ ] **Golden:** load a pre-0114 run (e.g.
  `runs/20260519-132908-backend-language-choice`) and assert the
  legacy reconstructor path still populates the typed lists (no
  regression for legacy data).
- [ ] **Manual:** open the local UI against the
  20260520-025406 run; confirm that every Phase 2 + Phase 4 round
  card shows non-zero badge counts and the critique pane filters
  contain entries.
- [ ] **Manual:** fire a fresh end-to-end run (e.g. via the
  `dual-research-run` skill) and confirm `transcript.jsonl` now
  contains `item_raised` / `item_transitioned` lines.

## Risks

- **Double-counting if the orchestrator ever starts emitting item
  events via both the bridge and a future direct `transcript.write`.**
  Mitigated by the allowlist being exclusive — adding the bridge does
  not change any existing direct-write call site.
- **Replay drift.** If `DeepResearchPhase.apply_turn` semantics change
  later (e.g. a future spec changes how an `addressed` item is
  ratified), the replay path stays correct *because it imports the
  orchestrator's actual logic*. The risk is that the orchestrator
  evolves to depend on side-channel state that isn't on disk (e.g.
  evidence-validation backed by a network call). The replay path
  passes a no-op `evidence_validator` so this stays deterministic and
  pure.
- **Closeout-round detection in replay.** Whether a given round was a
  closeout round is decided by the previous round's
  `process_round_end`. The replay path threads that state explicitly
  (it doesn't try to infer closeout from the round file itself), so it
  matches the live path's behaviour.
- **Legacy ID format incompatibility.** The new IDs (`D-plan-c-04`)
  are different from the legacy `D-N` format the `Disagreement.id`
  field carried for old runs. The projection writes the new IDs into
  the `id` field; the frontend treats it as opaque, so this is
  harmless.

## Open questions

None — the data paths and dataclass shapes are all already defined by
specs 0114 / 0115 / 0119; this spec just connects them.
