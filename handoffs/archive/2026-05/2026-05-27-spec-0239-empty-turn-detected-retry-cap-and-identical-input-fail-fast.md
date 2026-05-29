---
spec: "0239"
date: 2026-05-27
version: 1.54.0
pr: https://github.com/Lexiz/dual-research/pull/275
---

# Spec 0239 — `empty_turn_detected` retry hardening: identical-input fail-fast + N=2 cap

## What landed

The orchestrator's empty-turn retry budget is now bounded. A new helper module [`src/dual_research/orchestrator/empty_turn_retry.py`](src/dual_research/orchestrator/empty_turn_retry.py) exposes a pure `on_empty_turn(state, *, agent, phase, round, input_sha256)` function plus a `compute_input_sha256(text)` helper. The function maintains per-`(agent, phase, round)` retry state via an `EmptyTurnRetryRecord(count, last_input_sha256)` dataclass and returns a `ProtocolViolation` on two failure modes — byte-identical retry input (`empty_turn_persistent_identical_input`) or count exceeding `MAX_EMPTY_TURN_RETRIES=2` (`empty_turn_retry_cap_exceeded`) — else mutates the caller-owned state dict to advance the bucket. State is owned by the `DeepResearchPhase` instance (fresh dict per phase invocation) so the reset scope at phase boundaries is implicit; round-boundary reset is structural (the dict key includes `round` so a new round starts from a zero-count bucket).

`apply_turn` at [`src/dual_research/orchestrator/deep_research.py`](src/dual_research/orchestrator/deep_research.py) gains an optional `input_sha256: str | None = None` kwarg. When `ledger_block_count == 0`, it appends the `EmptyTurnDetected` event (now carrying the hash) and then invokes the helper; the helper's returned violation, if any, is appended to the same `violations` list the orchestrator publishes. The replay path leaves `input_sha256` as `None` and the helper invocation is skipped — historical fixtures don't trip the contract. The production wiring at [`src/dual_research/orchestrator/dr_run.py`](src/dual_research/orchestrator/dr_run.py) hashes the per-turn `prompt` returned from `build_round_prompt` and threads it to `apply_turn`.

Two new `ProtocolViolation.violation_code` values are registered in the docstring at [`src/dual_research/events/types.py`](src/dual_research/events/types.py): `empty_turn_persistent_identical_input` and `empty_turn_retry_cap_exceeded`. `EmptyTurnDetected` gains an optional `input_sha256: str | None = None` field. Both additions are dataclass fields with defaults — no migration.

The new verifier invariant `I2.7` at [`src/dual_research/contract/verifier.py`](src/dual_research/contract/verifier.py) (registered in the aggregator at line 1267) groups recorded `empty_turn_detected` events by `(agent, phase, round)`, surfaces Evidence rows for cap-exceeded groups and consecutive identical-`input_sha256` pairs, and returns `InvariantResult("I2.7", "reporting", …)`. Reporting-only initially — promotion to gating is gated on a clean reference-run baseline (separate small spec per spec 0239 §5). The identical-input check is skipped on groups where any event has `input_sha256` absent or `None`, so pre-0239 historical fixtures don't false-positive.

## Files touched

- [`src/dual_research/orchestrator/empty_turn_retry.py`](src/dual_research/orchestrator/empty_turn_retry.py) — new module: `MAX_EMPTY_TURN_RETRIES=2`, `EmptyTurnRetryRecord`, `EmptyTurnRetryState`, `compute_input_sha256`, `on_empty_turn`.
- [`src/dual_research/orchestrator/deep_research.py`](src/dual_research/orchestrator/deep_research.py) — `DeepResearchPhase.__init__` initialises `self._empty_turn_retry_state: EmptyTurnRetryState = {}`; `apply_turn` accepts `input_sha256` and invokes the helper at the empty-turn emission site; threads the new optional field onto the constructed `EmptyTurnDetected`.
- [`src/dual_research/orchestrator/dr_run.py`](src/dual_research/orchestrator/dr_run.py) — imports `compute_input_sha256` and passes `input_sha256=compute_input_sha256(prompt)` to `apply_turn`.
- [`src/dual_research/events/types.py`](src/dual_research/events/types.py) — `ProtocolViolation` docstring entry for the two new violation codes; `EmptyTurnDetected` gains `input_sha256: str | None = None`.
- [`src/dual_research/contract/verifier.py`](src/dual_research/contract/verifier.py) — new `_check_i2_7(events)` after `_check_i2_6`; registered in the `verify_run` aggregator.
- [`tests/test_spec_0239_empty_turn_retry_hardening.py`](tests/test_spec_0239_empty_turn_retry_hardening.py) — 11 tests: five Layer-1 unit cases (identical-input fail-fast; N=2 cap with varying inputs; counter reset on round / phase / agent boundary); four I2.7 unit cases (pass / not-applicable / cap-exceeded fail / identical-input fail / `None`-hash skip); the captured-142625 integration test that runs `_check_i2_7` against the fixture's `transcript.captured.jsonl` and asserts `pass` (this is the live-failure-fix-discipline test per the rule added in spec 0238).
- [`CHANGELOG.md`](CHANGELOG.md), [`pyproject.toml`](pyproject.toml), [`src/dual_research/__init__.py`](src/dual_research/__init__.py), [`src/dual_research/ui/static/version-notes.json`](src/dual_research/ui/static/version-notes.json), `uv.lock` — MINOR bump 1.53.0 → 1.54.0.

`uv run pytest tests/ -q` → 2226 passed (11 new + 2215 pre-existing). Deploy `success` on GH Actions run [26534731950](https://github.com/Lexiz/dual-research/actions/runs/26534731950). `/api/health` reports `version: 1.54.0`.

## Notes for follow-ups

- **Cap reset scope vs failure mode it protects against.** The per-`(agent, phase, round)` reset scope was the Cowork Ask-3 answer — `per-run conflates independent turns; per-phase lets an early round drain a later round's budget`. Under the current orchestrator, each round runs each agent's turn exactly once, so the cap never actually fires in the steady-state production path (each `(agent, phase, round)` key sees at most one observation). The contract is in place; future code that adds same-round retry — or a callsite re-invoking `apply_turn` for the same triple — gets the enforcement automatically. The verifier I2.7 reads the recorded events directly, so any future code path that DOES produce multiple empty turns for the same key will surface as a `fail` evidence row regardless of where the retry lives.
- **I2.7 baseline regeneration.** The new invariant lands as `reporting` and is not yet expressed in any anchor-run fixture's `expected.json`. The baseline regen across anchor-run fixtures is owned by spec 0240; this spec deliberately defers it to keep the surface small.
- **Verifier `_check_i2_7` reads `event` key, not `kind`.** The transcript serializer flattens dataclass fields and writes the marker under `event` (e.g. `"event": "empty_turn_detected"`), not `kind`. I2.7 grouping uses `ev.get("event")`. This matches the pattern in `_check_i2_5` / `_check_i2_6` and avoids a class of would-be silent-skip bugs.
