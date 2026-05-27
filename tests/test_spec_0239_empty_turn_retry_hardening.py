"""Spec 0239 — `empty_turn_detected` retry hardening tests.

Layer 1 (helper + state): byte-identical input fail-fast, hard cap at
``MAX_EMPTY_TURN_RETRIES=2`` per ``(agent, phase, round)``, counter reset
semantics across round / phase / agent.

Layer 2 (verifier I2.7): reporting-only invariant that surfaces the same
two failure modes from a recorded transcript.

Integration: ``_check_i2_7`` against the captured ``transcript.captured.jsonl``
of the ``20260527-142625-backend-language-choice`` fixture — verifies the
new invariant returns ``pass`` on the dead state (one ``empty_turn_detected``
event recorded before the user killed the process; cap not breached).
"""
from __future__ import annotations

import json
from pathlib import Path

from dual_research.contract.verifier import _check_i2_7
from dual_research.events.types import ProtocolViolation
from dual_research.orchestrator.empty_turn_retry import (
    MAX_EMPTY_TURN_RETRIES,
    EmptyTurnRetryRecord,
    compute_input_sha256,
    on_empty_turn,
)


FIXTURE_DIR = (
    Path(__file__).parent
    / "fixtures"
    / "anchor-runs"
    / "20260527-142625-backend-language-choice"
)


# ─── Layer 1 — helper unit tests ──────────────────────────────────────


def test_identical_input_fail_fast_returns_protocol_violation():
    """Two empty turns for the same (agent, phase, round) with byte-
    identical inputs → second observation returns ProtocolViolation
    with violation_code=empty_turn_persistent_identical_input rather
    than letting the retry proceed."""
    state: dict = {}
    hash_a = compute_input_sha256("prompt body")

    first = on_empty_turn(
        state, agent="claude", phase=2, round=1, input_sha256=hash_a,
    )
    assert first is None, "first observation must be within budget"
    assert state[("claude", 2, 1)] == EmptyTurnRetryRecord(
        count=1, last_input_sha256=hash_a,
    )

    second = on_empty_turn(
        state, agent="claude", phase=2, round=1, input_sha256=hash_a,
    )
    assert isinstance(second, ProtocolViolation)
    assert second.violation_code == "empty_turn_persistent_identical_input"
    assert second.agent == "claude"
    assert second.phase == 2
    assert second.round == 1
    # Bucket must NOT have advanced on the fail-fast path.
    assert state[("claude", 2, 1)].count == 1


def test_cap_at_n_2_with_varying_inputs_third_observation_fails():
    """Three empty turns for the same (agent, phase, round) with three
    different inputs → first two within budget, third returns
    ProtocolViolation(empty_turn_retry_cap_exceeded)."""
    state: dict = {}
    h1 = compute_input_sha256("prompt 1")
    h2 = compute_input_sha256("prompt 2")
    h3 = compute_input_sha256("prompt 3")

    assert on_empty_turn(state, agent="claude", phase=0, round=3, input_sha256=h1) is None
    assert on_empty_turn(state, agent="claude", phase=0, round=3, input_sha256=h2) is None
    assert state[("claude", 0, 3)].count == MAX_EMPTY_TURN_RETRIES

    third = on_empty_turn(state, agent="claude", phase=0, round=3, input_sha256=h3)
    assert isinstance(third, ProtocolViolation)
    assert third.violation_code == "empty_turn_retry_cap_exceeded"
    # Bucket count was not advanced past the cap.
    assert state[("claude", 0, 3)].count == MAX_EMPTY_TURN_RETRIES


def test_counter_resets_on_round_boundary():
    """Two empty turns at (claude, phase=2, round=1) followed by an
    empty turn at (claude, phase=2, round=2) → the round-2 turn sees
    retry-count 0, not 2. Cap is per (agent, phase, round), not
    cumulative across rounds."""
    state: dict = {}
    h1 = compute_input_sha256("r1 prompt a")
    h2 = compute_input_sha256("r1 prompt b")
    h3 = compute_input_sha256("r2 prompt a")

    assert on_empty_turn(state, agent="claude", phase=2, round=1, input_sha256=h1) is None
    assert on_empty_turn(state, agent="claude", phase=2, round=1, input_sha256=h2) is None
    assert state[("claude", 2, 1)].count == 2

    # Same agent/phase but new round → fresh bucket, no PV.
    third = on_empty_turn(state, agent="claude", phase=2, round=2, input_sha256=h3)
    assert third is None
    assert state[("claude", 2, 2)].count == 1


def test_counter_resets_on_phase_boundary():
    """Empty turns at (claude, phase=1, …) do not consume budget for
    (claude, phase=2, …). Distinct phase ⇒ distinct bucket."""
    state: dict = {}
    h_phase1 = compute_input_sha256("phase1 prompt")
    h_phase2 = compute_input_sha256("phase2 prompt")

    assert on_empty_turn(state, agent="claude", phase=1, round=1, input_sha256=h_phase1) is None
    assert on_empty_turn(state, agent="claude", phase=1, round=1, input_sha256=h_phase1 + "x") is None
    assert state[("claude", 1, 1)].count == 2

    # Same agent, same round number, different phase → fresh bucket.
    third = on_empty_turn(state, agent="claude", phase=2, round=1, input_sha256=h_phase2)
    assert third is None
    assert state[("claude", 2, 1)].count == 1


def test_separate_agents_track_independently():
    """An empty turn for (claude, phase=2, round=1) does not affect
    (openai, phase=2, round=1). Same phase + round + different agent ⇒
    independent budget."""
    state: dict = {}
    h_claude_a = compute_input_sha256("claude a")
    h_claude_b = compute_input_sha256("claude b")
    h_openai = compute_input_sha256("openai prompt")

    assert on_empty_turn(state, agent="claude", phase=2, round=1, input_sha256=h_claude_a) is None
    assert on_empty_turn(state, agent="claude", phase=2, round=1, input_sha256=h_claude_b) is None
    assert state[("claude", 2, 1)].count == 2

    # openai's bucket is untouched — cap not consumed.
    openai_first = on_empty_turn(
        state, agent="openai", phase=2, round=1, input_sha256=h_openai,
    )
    assert openai_first is None
    assert state[("openai", 2, 1)].count == 1


# ─── Layer 2 — verifier I2.7 unit tests ───────────────────────────────


def _evt(**kwargs) -> dict:
    return {"event": "empty_turn_detected", **kwargs}


def test_i2_7_pass_one_event_per_key():
    """Synthetic transcript with one empty_turn_detected per key →
    I2.7 returns pass."""
    events = [
        _evt(phase=2, round=1, agent="claude", input_sha256="aaa"),
        _evt(phase=2, round=2, agent="claude", input_sha256="bbb"),
        _evt(phase=2, round=1, agent="openai", input_sha256="ccc"),
    ]
    result = _check_i2_7(events)
    assert result.id == "I2.7"
    assert result.severity == "reporting"
    assert result.verdict == "pass"


def test_i2_7_not_applicable_when_no_empty_turn_events():
    """No empty_turn_detected events in the transcript → I2.7 is
    not_applicable (the invariant has nothing to assert against)."""
    events = [
        {"event": "turn_started", "phase": 0, "round": 1, "agent": "claude"},
        {"event": "item_raised", "phase": 0, "round": 1, "id": "P0-q-c-01"},
    ]
    result = _check_i2_7(events)
    assert result.verdict == "not_applicable"


def test_i2_7_fail_on_cap_exceeded():
    """Synthetic transcript with three empty_turn_detected events for
    the same (agent, phase, round) → I2.7 returns fail with the
    cap-exceeded Evidence row."""
    events = [
        _evt(phase=2, round=1, agent="claude", input_sha256="aaa"),
        _evt(phase=2, round=1, agent="claude", input_sha256="bbb"),
        _evt(phase=2, round=1, agent="claude", input_sha256="ccc"),
    ]
    result = _check_i2_7(events)
    assert result.verdict == "fail"
    assert any(
        "exceeds cap" in ev.detail and "phase2/r1/claude" in ev.location
        for ev in result.evidence
    )


def test_i2_7_fail_on_identical_input_consecutive():
    """Two consecutive empty_turn_detected events for the same key
    carrying the same input_sha256 → I2.7 returns fail with the
    identical-input Evidence row."""
    events = [
        _evt(phase=0, round=2, agent="openai", input_sha256="deadbeef"),
        _evt(phase=0, round=2, agent="openai", input_sha256="deadbeef"),
    ]
    result = _check_i2_7(events)
    assert result.verdict == "fail"
    assert any(
        "identical input_sha256" in ev.detail and "deadbeef" in ev.detail
        for ev in result.evidence
    )


def test_i2_7_skips_identical_check_when_hash_is_none():
    """Groups where any event has input_sha256=None are skipped for the
    identical-input check (pre-0239 historical fixtures). The cap check
    still applies — that one only counts occurrences."""
    events = [
        _evt(phase=0, round=1, agent="claude"),                       # no input_sha256
        _evt(phase=0, round=1, agent="claude", input_sha256="aaaa"),  # would otherwise compare
    ]
    result = _check_i2_7(events)
    # Cap = 2, only 2 events for the key → cap not breached. And the
    # identical-input check is skipped because one hash is None.
    assert result.verdict == "pass"


# ─── Layer 3 — integration on the captured 142625 fixture ────────────


def test_i2_7_pass_on_captured_142625_transcript():
    """Run the verifier check against the captured transcript of the
    20260527-142625 backend-language-choice fixture.

    The captured transcript has exactly one empty_turn_detected event
    (claude phase=2 round=1) before the user killed the process. With
    only one event for the key, neither the cap (≤2) nor the
    identical-input check fires. I2.7 must report pass.

    This is the live-failure-fix-discipline test per the CLAUDE.md
    rule added in spec 0238: spec 0239's stated cause-of-death is the
    unbounded retry pattern visible in this fixture, so the regression
    guard must exercise the real verifier entry point against the
    captured artifact."""
    transcript_path = FIXTURE_DIR / "transcript.captured.jsonl"
    assert transcript_path.exists(), (
        f"captured transcript missing at {transcript_path} — fixture "
        f"must carry the immutable evidence anchor for the dead-state run"
    )

    events: list[dict] = []
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))

    # Sanity: at least one empty_turn_detected event must be present —
    # that's the whole reason this is the 0239 anchor fixture.
    empty_turn_events = [
        ev for ev in events if ev.get("event") == "empty_turn_detected"
    ]
    assert empty_turn_events, (
        "captured transcript must contain at least one "
        "empty_turn_detected event"
    )
    assert len(empty_turn_events) <= MAX_EMPTY_TURN_RETRIES, (
        "captured fixture is the pre-fix dead state — the cap should not "
        "be breached in the recorded events (the user killed the process)"
    )

    result = _check_i2_7(events)
    assert result.id == "I2.7"
    assert result.severity == "reporting"
    assert result.verdict == "pass", (
        f"captured fixture must produce a clean I2.7 pass — saw "
        f"{result.verdict} with evidence: {result.evidence}"
    )
