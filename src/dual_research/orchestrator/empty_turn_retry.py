"""Spec 0239 — `empty_turn_detected` retry hardening.

Per-``(agent, phase, round)`` budget for empty-turn retries. Two failure
modes are caught and surfaced as :class:`ProtocolViolation` events:

* ``empty_turn_persistent_identical_input`` — the retry would feed the
  same prompt that already produced an empty turn. At fixed temperature
  this cannot succeed; the orchestrator must fail fast rather than burn
  budget on a deterministic miss.
* ``empty_turn_retry_cap_exceeded`` — more than
  :data:`MAX_EMPTY_TURN_RETRIES` empty turns observed for the same
  ``(agent, phase, round)``. The cap is per turn-attempt context per
  Cowork's Ask-3 reasoning: an empty turn and any same-key retries are
  one budget; a new round/phase/agent gets a fresh budget.

The helper is a pure mutation over a caller-owned state dict — the
orchestrator scopes lifetime by holding the dict on the
:class:`DeepResearchPhase` instance. State leaks across phases would be
incorrect (per Cowork: "per-run conflates independent turns"); a fresh
``DeepResearchPhase`` per phase keeps the scope honest.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from dual_research.events.types import ProtocolViolation

__all__ = [
    "MAX_EMPTY_TURN_RETRIES",
    "EmptyTurnRetryRecord",
    "EmptyTurnRetryState",
    "compute_input_sha256",
    "on_empty_turn",
    "on_turn_api_call_timeout",
]


MAX_EMPTY_TURN_RETRIES = 2


@dataclass
class EmptyTurnRetryRecord:
    """One ``(agent, phase, round)`` bucket's retry state.

    ``count`` is the number of empty turns observed for this key.
    ``last_input_sha256`` is the prompt hash of the most recent empty
    turn; it gates the identical-input fail-fast on the next observation.
    """

    count: int = 0
    last_input_sha256: str | None = None


EmptyTurnRetryState = dict[tuple[str, int, int], EmptyTurnRetryRecord]


def compute_input_sha256(text: str) -> str:
    """Stable hex SHA-256 of ``text`` encoded as UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def on_empty_turn(
    state: EmptyTurnRetryState,
    *,
    agent: str,
    phase: int,
    round: int,
    input_sha256: str,
) -> ProtocolViolation | None:
    """Update ``state`` for an observed empty turn.

    Returns ``None`` when the empty turn is within budget — the bucket
    is mutated in place to reflect the new count and hash. Returns a
    :class:`ProtocolViolation` (without mutating the bucket) when the
    empty turn would exceed the retry cap or repeats a byte-identical
    input. The caller appends the returned violation to the
    orchestrator's per-turn violations list.

    Identical-input check fires before the cap check: a second
    same-input observation at count==1 (still within cap) is still a
    deterministic miss and must fail fast.
    """
    key = (agent, phase, round)
    record = state.get(key, EmptyTurnRetryRecord())

    if (
        record.last_input_sha256 is not None
        and record.last_input_sha256 == input_sha256
    ):
        return ProtocolViolation(
            phase=phase,
            round=round,
            agent=agent,
            violation_code="empty_turn_persistent_identical_input",
            item_id="",
            from_state="",
            dropped_block="",
            op_kind="",
            expected_state="",
            reason=(
                f"empty_turn_detected fired with byte-identical "
                f"input_sha256={input_sha256} after a prior empty turn for "
                f"(agent={agent}, phase={phase}, round={round}); retry "
                f"cannot succeed at fixed temperature"
            ),
        )

    next_count = record.count + 1
    if next_count > MAX_EMPTY_TURN_RETRIES:
        return ProtocolViolation(
            phase=phase,
            round=round,
            agent=agent,
            violation_code="empty_turn_retry_cap_exceeded",
            item_id="",
            from_state="",
            dropped_block="",
            op_kind="",
            expected_state="",
            reason=(
                f"empty_turn_detected count {next_count} exceeds cap of "
                f"{MAX_EMPTY_TURN_RETRIES} per (agent, phase, round); "
                f"key=(agent={agent}, phase={phase}, round={round})"
            ),
        )

    state[key] = EmptyTurnRetryRecord(
        count=next_count,
        last_input_sha256=input_sha256,
    )
    return None


def on_turn_api_call_timeout(
    state: EmptyTurnRetryState,
    *,
    agent: str,
    phase: int,
    round: int,
) -> ProtocolViolation:
    """Spec 0241 §2.5 — tick the unified retry counter for a timeout.

    A ``turn_api_call_timeout`` is always fail-fast: re-issuing a byte-
    identical call that just hung for 900s would mean back-to-back
    15-minute hangs. We tick the counter (so a subsequent
    ``empty_turn_detected`` for the same key sees the elevated count
    and trips the existing cap sooner), then return a structured
    :class:`ProtocolViolation` so the caller can record it. The
    last-input hash is preserved as-is — the timeout case has no
    "input that produced the empty turn" to compare against; mutating
    only the count keeps :func:`on_empty_turn`'s identical-input check
    well-defined.
    """
    key = (agent, phase, round)
    record = state.get(key, EmptyTurnRetryRecord())
    next_count = record.count + 1
    state[key] = EmptyTurnRetryRecord(
        count=next_count,
        last_input_sha256=record.last_input_sha256,
    )
    return ProtocolViolation(
        phase=phase,
        round=round,
        agent=agent,
        violation_code="turn_api_call_timeout",
        item_id="",
        from_state="",
        dropped_block="",
        op_kind="",
        expected_state="",
        reason=(
            f"turn_api_call_timeout for (agent={agent}, phase={phase}, "
            f"round={round}); count={next_count}; fail-fast no retry"
        ),
    )
