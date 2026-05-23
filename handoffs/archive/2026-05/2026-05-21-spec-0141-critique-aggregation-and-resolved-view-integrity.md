# Handover — Spec 0141 — Critique aggregation invariants + resolved-view integrity (v1.9.2)

- **Date:** 2026-05-21
- **PR:** [Lexiz/dual-research#163](https://github.com/Lexiz/dual-research/pull/163) (merged, squash, branch deleted)
- **Spec:** [specs/0141-critique-aggregation-and-resolved-view-integrity.md](../specs/0141-critique-aggregation-and-resolved-view-integrity.md)
- **Anchor run:** `20260521-010637-dvs-backend-language-choice`
- **Backlog rows fixed:** B02 (closed > raised invariant) + B06 (zero-movement turns), B10 verified as derived
- **Version:** `1.9.1 → 1.9.2` (PATCH — bug fixes only; no surface change)

## What landed

Two orchestrator-side fixes plus a derived-symptom verification that close the three Notion-backlog bugs that all traced to the item-state pipeline: the orchestrator now refuses to re-open a terminal item (B02), surfaces zero-block negotiate turns as a first-class event (B06), and the resolved-view aggregation arrives at consistent counts once the upstream events are clean (B10).

### Edit 1 — Terminal-state guard on `AddressBlock` (B02 fix)

[`src/dual_research/orchestrator/deep_research.py::apply_turn`](../src/dual_research/orchestrator/deep_research.py) — the `AddressBlock` branch gained an `is_terminal(ent.current_state)` short-circuit immediately after the `ent.raiser == agent` check, mirroring the existing pattern on `WithdrawBlock` (line 435) and `AcknowledgeBlock` (line 460). A late-arriving ADDRESS targeting an already-terminal item (resolved / acknowledged / withdrawn / capped) is silently dropped at the orchestrator and recorded as a new `ProtocolViolation` event with `violation_code="terminal_state_re_address"` for the audit trail.

Anchor-run smoking gun: item `D-plan-g-01`, transcript seqs 121 / 137 / 144 — r2.1 claude ADDRESSED → r2.2 openai RESOLVED → r2.3 claude ADDRESSED the resolved item (pre-fix: leaks back to ADDRESSED) → r2.3 openai RESOLVED a second time (pre-fix: closes the same item twice; aggregator counts 1 raise / 2 closes). Post-fix the r2.3 ADDRESS is dropped, the subsequent RESOLVE no-ops at the existing `current_state != ADDRESSED` guard, and the aggregator sees the expected 1 raise / 1 close. Anchor-run disagreement totals: pre-fix **15 raised / 16 closed**, post-fix **15 / 15**.

### Edit 2 — `EmptyTurnDetected` signal scoped to phases 0/2/4 (B06 fix)

[`src/dual_research/orchestrator/deep_research.py::apply_turn`](../src/dual_research/orchestrator/deep_research.py) — at the end of the per-block loop, if `self.phase in (0, 2, 4)` and the parsed turn carried zero ledger-affecting blocks (no RAISE / ADDRESS / RESOLVE / WITHDRAW / ACKNOWLEDGE), emit a new `EmptyTurnDetected` event. Phases 1 (parallel drafts) and 3 (single-agent drafting) are by-design item-silent and skip the check — no false positives on legit drafter turns.

The event carries `finish_reason` and `output_tokens` plumbed via keyword arguments from the upstream `turn_ended` payload into `apply_turn` (resolved §9 open question #1 — keyword-argument route, not `ParsedTurnV2` stash). The anchor-run dispositive shape is phase4-r6-claude: `finish_reason="max_tokens", output_tokens=8750, duration_ms=185_844` — the model was actively producing output for ~3 minutes but ran out of room before emitting any parseable operation block. Informational only; the event does not abort the turn or advance any retry counter. A follow-up spec can lean on this signal for prompt-tightening or re-prompt policy.

### Edit 3 — B10 verification (resolved-view consistency)

No code change. The replay test in [`tests/ledger/test_replay_spec_0141.py`](../tests/ledger/test_replay_spec_0141.py) drives the on-disk anchor run through the patched orchestrator and asserts per-kind terminal-transition count equals raise count — which is exactly the upstream condition the `item.closedRound` projection (in [`ui/items.py`](../src/dual_research/ui/items.py) + `ui/aggregator.py::closed_turn_key` at line 1661) and the `CritiquePhaseContent` Resolved-group renderer at [`run-detail.jsx:6576`](../src/dual_research/ui/static/run-detail.jsx) need to render the right view. B10 self-resolved cleanly — no follow-up spec required, no `closedRound` projection adjustment needed.

## Files touched

- `src/dual_research/events/types.py` — added `ProtocolViolation` + `EmptyTurnDetected` (both follow the existing `CloseoutViolation` `kw_only=True` shape with `kind` as last field).
- `src/dual_research/events/__init__.py` — exports.
- `src/dual_research/orchestrator/deep_research.py` — `apply_turn` signature widened (`finish_reason`, `output_tokens` kwargs; return tuple 3 → 4 lists), AddressBlock terminal-state guard, empty-turn detector at end of method, `RoundResult.empty_turn_events`, `process_round_end` accepts the new list, sync `run_round` unpacks the new 4-tuple.
- `src/dual_research/orchestrator/dr_run.py` — production callsite extracts `finish_reason` / `output_tokens` from `result.extras` + `result.usage`, threads through `apply_turn`, publishes new events via `_publish_round_events`.
- `src/dual_research/orchestrator/run.py` — `_TRANSCRIPT_MIRRORED_EVENTS` extended with `ProtocolViolation` + `EmptyTurnDetected` so the spec-0122 transcript bridge persists them.
- `src/dual_research/ledger/replay.py` — replay callsite unpacks the new 4-tuple; finish_reason / output_tokens defaults to `None` / `0` since the on-disk path can't see the live turn_ended payload.
- `tests/orchestrator/test_deep_research.py` — 14 new tests covering the parameterised terminal-state guard, the no-op-address regression-pin, the end-to-end anchor-run double-close shape, and the EmptyTurnDetected behaviour matrix (phase-gating, finish_reason plumbing, block-count gating, replay default behaviour).
- `tests/ledger/test_replay_spec_0141.py` — new file; 3 anchor-run replay tests (per-kind invariant, ProtocolViolation surfaced, EmptyTurnDetected surfaced in Phase 4). Skip when the run directory is absent.
- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — `1.9.1 → 1.9.2`.
- `CHANGELOG.md` — `[1.9.2]` entry.

## Schema / env / token changes

None. `ProtocolViolation` and `EmptyTurnDetected` are append-only event types; no existing event payload changed shape. No DB migration, no env var, no token, no cache-bust.

## Tests

```
1245 passed in 10.18s
```

Up from 1228 (Spec 0140 baseline) — +17 new tests:

- 4 × parameterised terminal-state guard (one each for RESOLVED / ACKNOWLEDGED / WITHDRAWN / CAPPED)
- 1 × happy-path regression (open → addressed still transitions; no violation)
- 1 × no-op address regression (addressed → addressed still short-circuits silently)
- 1 × end-to-end anchor-run double-close (RAISE → ADDRESS → RESOLVE → ADDRESS [blocked] → RESOLVE [no-op])
- 3 × parameterised EmptyTurnDetected fires in phases 0 / 2 / 4
- 2 × parameterised EmptyTurnDetected does NOT fire in phases 1 / 3
- 1 × EmptyTurnDetected does not fire when any block is present
- 1 × EmptyTurnDetected handles missing finish_reason / output_tokens (replay path)
- 3 × anchor-run replay invariants (raise == close per kind, ProtocolViolation on D-plan-g-01, EmptyTurnDetected on Phase 4)

## Deploy

```
fly deploy
…
✔ [1/2] Machine 148ee320f427e8 is now in a good state
✖ [2/2] Unrecoverable error: timeout reached waiting for health checks  (fly machines.dev API timed out mid-rolling-deploy)
```

The first machine reached good state on version 182. The second machine (replacement `7845e17c221738` of `2870612f037368`) was created and reached `stopped` state when the fly machines.dev API timed out waiting on health checks — a fly-side transient, not a code issue. Resolved by `fly machine start 7845e17c221738`; both machines now `started` on version 182 with 1/1 health check passing.

Live: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.9.2","backend":"supabase"}`.

## Open questions resolved

All three §9 questions resolved with the spec's recommended defaults (low-reversal-cost calls, per the user's standing rule):

1. **`finish_reason` / `output_tokens` plumbing site.** Chose the keyword-argument route into `apply_turn`. Production callsite in `dr_run.py::_drive_interaction_phase` extracts from `result.extras["stop_reason"|"finish_reason"]` + `result.usage.output_tokens` (the same fields the existing `TurnEnded` event reads). Replay path passes the defaults (`None` / `0`) because the on-disk reconstruction can't see the live `turn_ended` payload. Did **not** stash on `ParsedTurnV2` — parser output stays separate from turn-execution state.

2. **`ProtocolViolation` vs reuse `CloseoutViolation`.** Shipped a new `ProtocolViolation` event class. Reasoning: closeout violations are a phase-end protocol concern (a specific round's "no RAISE blocks allowed" gate); invariant violations are a generic data-integrity concern that should accumulate independently in the audit trail. Cost of the new class is one more entry in `_TRANSCRIPT_MIRRORED_EVENTS`. Both classes follow the same `@dataclass(frozen=True, kw_only=True)` shape with `kind` as the last field with a default.

3. **B10 ship-or-hold timing.** Shipped — B02 + B06 are independent wins and the §5.3 anchor-run replay confirms B10 self-resolves cleanly. No `closedRound` projection adjustment needed; the existing UI rendering produces the right view once the upstream events are clean.

## B10 verification outcome

**Self-resolved cleanly.** The replay test [`test_anchor_run_replay_raise_close_invariant_holds_post_fix`](../tests/ledger/test_replay_spec_0141.py) drives the on-disk anchor run through the patched orchestrator and asserts per-kind raises == closes for every kind. Pre-fix disagreement row read 15 raised / 16 closed; post-fix reads 15 / 15. No follow-up spec required.

The visual smoke (`open the anchor run on the hosted UI and confirm the Resolved view matches the Phase 4 timeline turn-by-turn`) is left as a user-side check — the hosted `/api/runs` endpoint requires an auth token I don't have. The data-layer correctness check (replay test) is the definitive verification; the UI is purely deterministic given clean upstream data (no JSX changes in this spec).

## Known follow-ups

- **UI surface for `ProtocolViolation` / `EmptyTurnDetected`.** Per spec §6 (out of scope). Both events ride the spec-0122 transcript bridge and persist to `transcript.jsonl`, but no warning chip / badge / audit-log surface in this spec. A follow-up may render a small warning chip on affected turn cards once the events accumulate enough signal across real runs (especially Phase 4, which carries most of the empty-turn population).
- **Retry-on-empty-turn / prompt-tightening.** Spec §6 keeps this out of scope. The fix is a signal, not a behaviour change; the spec-0114 prompt body for phases 0 / 2 / 4 stays unchanged. A follow-up that tightens "you must surface at least one block per turn or explicitly STATUS: AGREED" can lean on the new `EmptyTurnDetected` data once it's collected across multiple production runs.
- **`ProtocolViolation` accumulation.** Today only one `violation_code` exists (`terminal_state_re_address`). Future invariants (e.g. `addressing_own_item` if that ever leaks past the existing line-353 short-circuit) reuse the same event class with a different code. The `violation_code` field discriminates; per-code tallies are trivially derivable in the aggregator.
- **Fly machines.dev API timeout.** The mid-rolling-deploy timeout that left machine 2 in `stopped` state is a fly-side flake; the repro is the API silently stalling while waiting on health checks. Manually starting the machine after deploy fixed it; nothing to do on our end unless this happens repeatedly, at which point a fly support ticket is warranted.
- **Spec 0140's "End-to-end smoke run" follow-up** carries over — running a fresh `/dual-research-run` on a brief known to drift in Phase 4 (confirming both 0140's Phase-4-extractor fix and 0141's empty-turn detection on a fresh transcript) is still a user-side smoke since it costs ~$10 of LLM spend.
