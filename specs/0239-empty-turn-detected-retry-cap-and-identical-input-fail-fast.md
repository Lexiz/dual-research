---
kind: dev
spec: "0239"
slug: empty-turn-detected-retry-cap-and-identical-input-fail-fast
title: "Orchestrator: bound `empty_turn_detected` retries — fail-fast on byte-identical retry input; hard-cap at N=2 per (agent, phase, round)"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-27
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Current orchestrator retries `empty_turn_detected` immediately with no observable cap (verified: empty_turn_events.append at deep_research.py:760 is bookkeeping only; no counter gates further retries). On any future parser-fragility regression the loop burns unbounded budget before a human notices. Identical-input retry can't succeed at fixed temperature, so the fail-fast path is also a correctness win, not just hardening. Live evidence: 20260527-142625 burned ~$0 on the retry only because the user killed the process; the design admits unbounded runaway."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0239 — `empty_turn_detected` retry hardening: identical-input fail-fast + N=2 cap

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** —  (lands in parallel with 0238)
> **Bump:** MINOR — adds a new `ProtocolViolation` kind, a new verifier invariant (I2.7, reporting), and orchestrator state for the retry counter. Verifier invariants ARE the contract per the CLAUDE.md "contract-changing specs are not bugs" rule.
> **Evidence:** failing-run fixture [`tests/fixtures/anchor-runs/20260527-142625-backend-language-choice/`](tests/fixtures/anchor-runs/20260527-142625-backend-language-choice/) (the captured retry-without-cap pattern); Cowork design-answers brief `cowork/briefs/2026-05-27-0238-0239-design-answers.md`; orchestrator source [`src/dual_research/orchestrator/deep_research.py:760`](src/dual_research/orchestrator/deep_research.py:760) (the unbounded append).

---

## 1. Context

When the orchestrator's parser registers zero structured items from an agent turn, it emits an `empty_turn_detected` event and immediately retries the same turn with the same inputs. Inspection of the codepath:

- [`src/dual_research/orchestrator/deep_research.py:760`](src/dual_research/orchestrator/deep_research.py:760) — `empty_turn_events.append(EmptyTurnDetected(...))` appends the event.
- No counter is incremented, no backoff is taken, no cap is consulted before the next `turn_started` is issued.
- The retry is invoked with the same input prompt the original turn used.

In the captured failing run `20260527-142625-backend-language-choice`, the transcript shows:

```
14:41:21.332Z  empty_turn_detected   agent=claude phase=2 round=1
14:41:21.334Z  turn_started          agent=claude phase=phase2          (2 ms later — retry)
14:41:21.335Z  turn_inputs           agent=claude phase=phase2
(silence — process killed mid-API-call)
```

The retry was killed externally before it could complete. The design as observed admits two independent failure modes:

1. **Identical-input retry on a deterministic parser fragility.** When the cause of the empty turn is a parser failure (as in this run), retrying the same input through the same model at the same temperature produces the same (parser-defeating) output. The retry cannot succeed. The orchestrator will loop until budget cap or wall-clock cap fires — both run-level, not turn-level — burning unbounded budget invisibly between transcript flushes.
2. **Bounded retry on a model-side variation surface.** Even with variable model outputs (temperature > 0, or non-deterministic post-processing), there is no `N`-bounded retry cap. A run that genuinely benefits from one retry but happens to produce two consecutive empties for unrelated reasons will retry indefinitely.

Cowork's design-answers brief authorises a two-layer fix: fail-fast on byte-identical retry input (catches mode 1), and a per-`(agent, phase, round)` cap of `N=2` otherwise (catches mode 2). Both go behind structured `ProtocolViolation` emissions and a new reporting-only verifier invariant (I2.7).

## 2. Proposed change

Three layers, one PR.

### Layer 1 — Per-`(agent, phase, round)` retry counter + byte-identical-input fail-fast

In [`src/dual_research/orchestrator/deep_research.py`](src/dual_research/orchestrator/deep_research.py), augment the empty-turn handling path at and around line 760:

```python
# New module-level state (or per-run state on the orchestrator
# context object — placement TBD in implementation, behaviour is
# what's specified):
#
#   empty_turn_retry_state: dict[tuple[str, int, int], _RetryState]
#       key:   (agent.label, phase_int, round_int)
#       value: _RetryState(count: int, last_input_sha256: str)
#
# Reset semantics:
#   - Counter and hash both reset when (agent, phase, round) changes.
#   - This means crossing a round boundary or a phase boundary
#     discards the prior counter — independent turns get independent
#     budgets, per Cowork's Ask-3 reasoning.

def _on_empty_turn(agent, phase, round, next_turn_input):
    key = (agent.label, _phase_to_int(phase), round)
    state = empty_turn_retry_state.get(key, _RetryState(count=0, last_input_sha256=None))

    new_hash = sha256(next_turn_input.encode("utf-8")).hexdigest()

    if state.last_input_sha256 == new_hash:
        # Same input that produced the prior empty turn. Retrying
        # at fixed temperature cannot succeed. Fail fast.
        raise ProtocolViolation(
            kind="empty_turn_persistent_identical_input",
            agent=agent.label, phase=phase, round=round,
            data={
                "retry_count": state.count,
                "input_sha256": new_hash,
            },
        )

    if state.count + 1 > MAX_EMPTY_TURN_RETRIES:  # MAX_EMPTY_TURN_RETRIES = 2
        raise ProtocolViolation(
            kind="empty_turn_retry_cap_exceeded",
            agent=agent.label, phase=phase, round=round,
            data={
                "retry_count": state.count + 1,
                "cap": MAX_EMPTY_TURN_RETRIES,
            },
        )

    empty_turn_retry_state[key] = _RetryState(
        count=state.count + 1,
        last_input_sha256=new_hash,
    )
    # ...proceed with retry as today
```

`MAX_EMPTY_TURN_RETRIES = 2` is the cap. The constant lives in the same module as the handler; not promoted to config (no caller asked for tunability; YAGNI).

Two new `ProtocolViolation` kinds register in [`src/dual_research/events/types.py`](src/dual_research/events/types.py):
- `"empty_turn_persistent_identical_input"`
- `"empty_turn_retry_cap_exceeded"`

Both route through the existing `ProtocolViolation` emission flow (the same one spec 0228 wired). They fail the affected turn fast; the orchestrator's run loop continues to its normal hard-cap exit (no behavioural change to the loop, just to the retry layer).

### Layer 2 — Verifier invariant I2.7 (reporting)

Add `_check_i2_7` to [`src/dual_research/contract/verifier.py`](src/dual_research/contract/verifier.py), landing directly after `_check_i2_6` (which spec 0232 introduces) and registered in the aggregator the same way.

**Invariant I2.7 — `empty_turn_detected` retry hardening (Area 2: self-report ⇄ ledger).**

For every captured run transcript:

1. Group `empty_turn_detected` events by `(agent, phase, round)`.
2. For each group with `count > MAX_EMPTY_TURN_RETRIES` (2): emit an Evidence row `(agent, phase, round): N empty_turn_detected events exceeds cap of 2`.
3. For each group where any two consecutive events have the *same* recorded input hash (post-Layer-1 the input hash is emitted in the event's `data` payload): emit an Evidence row `(agent, phase, round): consecutive empty_turn_detected events with identical input_sha256`.

Return `InvariantResult("I2.7", "reporting", ...)`. Reporting-only initially, mirroring 0232's I2.6 pattern. Promotion to gating is a separate small spec, triggered when a reference-run baseline produces I2.7 = `pass` and we want to enforce going forward.

### Layer 3 — Tests

Tests live in a new file [`tests/test_spec_0239_empty_turn_retry_hardening.py`](tests/test_spec_0239_empty_turn_retry_hardening.py).

- [ ] **Unit: identical-input fail-fast.** Two empty turns for the same `(agent, phase, round)` with byte-identical inputs → second turn raises `ProtocolViolation(empty_turn_persistent_identical_input)` rather than retrying.
- [ ] **Unit: cap at N=2 with varying inputs.** Three empty turns for the same `(agent, phase, round)` with three *different* inputs → first two are allowed (retry counter ticks 1, 2), third raises `ProtocolViolation(empty_turn_retry_cap_exceeded)`.
- [ ] **Unit: counter reset on round boundary.** Two empty turns at `(agent=claude, phase=2, round=1)` followed by an empty turn at `(agent=claude, phase=2, round=2)` → the round-2 turn sees retry-count 0, NOT 2. Cap is per `(agent, phase, round)`, not cumulative.
- [ ] **Unit: counter reset on phase boundary.** Empty turns at `(claude, phase=1, …)` do not consume budget for `(claude, phase=2, …)`.
- [ ] **Unit: separate agents track independently.** An empty turn for `(claude, phase=2, round=1)` does not affect `(openai, phase=2, round=1)`.
- [ ] **Verifier unit: I2.7 negative.** Synthetic transcript with three `empty_turn_detected` events for the same key → `_check_i2_7` returns `fail` with the cap-exceeded Evidence row.
- [ ] **Verifier unit: I2.7 identical-input negative.** Synthetic transcript with two consecutive `empty_turn_detected` events for the same key carrying the same `input_sha256` in `data` → `_check_i2_7` returns `fail` with the identical-input Evidence row.
- [ ] **Verifier unit: I2.7 positive.** Synthetic transcript with one `empty_turn_detected` event per key → `_check_i2_7` returns `pass`.
- [ ] **Integration on captured 142625 fixture.** Replay the fixture through the verifier; I2.7 returns `pass` (only one `empty_turn_detected` event is captured before the kill; cap is not breached, identical-input fail-fast not triggered because retry never completed). This validates the fixture is consistent with the new invariant and is not surfaced as a false positive.
- [ ] **Backwards-compat.** `uv run pytest tests/ -q` passes end-to-end. No pre-existing test changes verdict.
- [ ] **CHANGELOG entry under a new `## [X.Y+1.0] — 2026-05-27` heading** (MINOR bump) with `### Added` bullets for the two ProtocolViolation kinds and I2.7; `pyproject.toml` and `src/dual_research/__init__.py` bumped to the same X.Y+1.0.

## 3. User stories & acceptance criteria

Not a UI spec. §3 is non-applicable per the new-feature template. Acceptance is encoded as falsifiable items in §6.

## 4. Data / Schema deltas

- **Two new `ProtocolViolation` kinds** registered in [`src/dual_research/events/types.py`](src/dual_research/events/types.py): `"empty_turn_persistent_identical_input"`, `"empty_turn_retry_cap_exceeded"`. No new event class — they reuse `ProtocolViolation`'s existing schema.
- **`EmptyTurnDetected` event payload** grows an optional `input_sha256: str | None` field carrying the SHA-256 of the turn input that produced the empty parse. Pre-existing replays without this field continue to work (default `None`); I2.7's identical-input check skips groups where any event has `input_sha256 is None`, so historical fixtures don't false-positive.
- **No migrations.** Both changes are additive on dataclass fields with defaults.

## 5. Out of scope

- **Promotion of I2.7 to `gating`.** Same pattern as I2.6 — reporting-only initially. Promotion lands in a follow-up spec once a clean reference-run shows I2.7 = `pass` and we want to enforce.
- **Backoff or jitter between retries.** Unnecessary if we fail fast on identical input. If a future failure shape suggests backoff helps (e.g. a transient model-side issue where the same input produces empty then non-empty on quick retry), reconsider — but no such evidence exists today.
- **Configurable cap.** `MAX_EMPTY_TURN_RETRIES = 2` is hardcoded. Tunability is YAGNI; if a real callsite ever wants a different cap, promote to config then.
- **Counter persistence across orchestrator restarts.** A killed-and-resumed run gets a fresh counter. This is correct behaviour: the resumed run replays its prior transcript, and any cap violation that was going to fire would fire again. Persistence is misfeature.
- **Replacing the empty-turn detection mechanism.** This spec hardens the response to empty-turn detection; it does not change how the detection itself works. The parser fix that prevents *false* empty-turn detection is spec 0238.

## 6. Test plan

Test plan items above in §2 Layer 3 are the acceptance items. Run as `uv run pytest tests/test_spec_0239_empty_turn_retry_hardening.py -q`. Full-suite regression run `uv run pytest tests/ -q` must pass.

## 7. Risks

- **Counter scope choice (per `(agent, phase, round)`) accidentally hides a real loop.** If an early round legitimately needs 3 empty-turn retries to recover (currently we have no evidence this happens), the cap would now fail the run. Mitigation: the failure surfaces as a structured `ProtocolViolation` event, not a silent stall — the failure is legible. If a real workload turns out to need a higher cap, raising `MAX_EMPTY_TURN_RETRIES` is a one-line change.
- **Hash collision on `input_sha256`.** SHA-256 collisions are not a real-world concern at our input sizes. No mitigation needed.
- **`input_sha256` not carried on pre-fix transcripts.** Historical fixtures don't have this field. Mitigation: I2.7 explicitly skips identical-input checks for groups where any event has `input_sha256 is None`, so historical replays don't false-positive. New runs always populate the field post-merge.
- **Drift between Layer 1's per-key state and the orchestrator's existing per-turn state.** Mitigation: state placement (module-level dict vs context-object field) is decided in implementation; the test plan validates behaviour, not implementation detail. Whichever placement is chosen lives next to the existing empty-turn handling code so the two stay paired in review.
- **Revert path.** Two new ProtocolViolation kinds + one verifier check + a handful of orchestrator lines. Reverting is a single `git revert`; no migration to unwind.
