"""Spec 0241 — per-turn liveness tests.

Layer 1 (heartbeat): separate-OS-thread emission, atomic concurrent
writes, survival across an event-loop block, clean stop on turn end.

Layer 2 (per-turn BaseException capture): the wrapper at
``_call.py::run_one_call`` emits a ``protocol_violation`` with
``violation_code="turn_api_call_exception"`` BEFORE the exception
propagates upward to 0222's run-loop tombstone. Exception-type fidelity
is preserved by unwrapping :class:`AgentError` to its ``__cause__``.

Layer 3 (whole-turn wall-clock cap): :func:`asyncio.timeout` wraps the
entire ``agent.run`` await, so a mid-stream stall (the 20260527-200213
failure mode) is bounded by ``TURN_WALLCLOCK_CAP_SECONDS`` rather than
the SDK's request-establishment timeout.

Layer 4 (verifier I2.8): every ``turn_started`` has a terminal
counterpart (``turn_ended`` / matching ProtocolViolation / tombstone).

Layer 5 (retry-budget unification): ``on_turn_api_call_timeout`` ticks
the same ``empty_turn_retry_state`` counter ``on_empty_turn`` does, and
always signals fail-fast (returns a ProtocolViolation).
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import pytest

from dual_research.agents.base import AgentError, AgentResult, TokenUsage
from dual_research.contract.verifier import _check_i2_8
from dual_research.events import EventBus
from dual_research.events.types import (
    ProtocolViolation,
    TurnHeartbeat,
)
from dual_research.orchestrator._call import run_one_call
from dual_research.orchestrator.empty_turn_retry import (
    EmptyTurnRetryRecord,
    compute_input_sha256,
    on_empty_turn,
    on_turn_api_call_timeout,
)
from dual_research.orchestrator.per_turn_liveness import (
    TURN_HEARTBEAT_INTERVAL_SECONDS,
    TURN_WALLCLOCK_CAP_SECONDS,
    HeartbeatThread,
)
from dual_research.persistence import Metrics, Transcript


# ─── Fakes ────────────────────────────────────────────────────────────


@dataclass
class _FakeAgent:
    """Minimal :class:`AgentCall` impl that drives ``run_one_call`` end-to-end.

    The fake mirrors the production agents' surface: it returns an
    :class:`AgentResult` or raises whatever the test wires it to. The
    ``run`` coroutine awaits whatever ``runner`` returns, so tests can
    plug in (a) instant returns, (b) ``asyncio.sleep`` to simulate a
    long turn, (c) ``raise`` to drive Layer 2, or (d) a never-completing
    sleep to drive Layer 3.
    """

    label: str = "claude"
    model_id: str = "fake-model"
    provider: str = "fake"

    async def run(
        self,
        prompt: str,
        *,
        max_output_tokens: int = 8192,
        stream_to: TextIO | None = None,
        stream_prefix: str = "",
        audit_context: dict | None = None,
    ) -> AgentResult:
        return await self._runner(prompt)

    async def _runner(self, prompt: str) -> AgentResult:
        return _fake_result(self.label)


def _fake_result(label: str) -> AgentResult:
    return AgentResult(
        text="ok",
        usage=TokenUsage(input_tokens=10, output_tokens=5),
        cost_usd=0.0,
        duration_ms=1,
        model_id="fake-model",
        provider="fake",
        label=label,
        extras={"stop_reason": "end_turn", "searches": 0},
    )


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ─── Layer 1 — heartbeat thread ───────────────────────────────────────


def test_heartbeat_emitted_periodically(tmp_path: Path):
    """Spec §2.1 — heartbeat thread emits transcript events on its
    interval. We use a short interval (0.1s) and let the thread tick a
    handful of times so the test stays fast."""
    transcript = Transcript(tmp_path / "transcript.jsonl")
    hb = HeartbeatThread(
        transcript=transcript,
        agent="claude",
        phase="phase2",
        round=1,
        interval=0.1,
    )
    hb.start()
    time.sleep(0.35)
    hb.stop()

    events = _read_jsonl(transcript.path)
    hbs = [e for e in events if e["event"] == "turn_heartbeat"]
    assert len(hbs) >= 2, (
        f"expected ≥2 heartbeats in ~0.35s at 0.1s interval; got {len(hbs)}"
    )
    # elapsed_seconds is monotonically non-decreasing.
    elapsed = [hb["elapsed_seconds"] for hb in hbs]
    assert elapsed == sorted(elapsed)
    # Agent/phase/round echo through.
    for hb in hbs:
        assert hb["agent"] == "claude"
        assert hb["phase"] == "phase2"
        assert hb["round"] == 1


def test_heartbeat_thread_survives_blocked_event_loop(tmp_path: Path):
    """Spec §2.1 — load-bearing claim: an OS-thread heartbeat continues
    firing even when the event loop is blocked by a synchronous busy
    loop. This is the differential diagnostic that distinguishes
    "event loop blocked" from "process dead" on the next silent death."""
    transcript = Transcript(tmp_path / "transcript.jsonl")
    hb = HeartbeatThread(
        transcript=transcript,
        agent="openai",
        phase="phase4",
        round=2,
        interval=0.05,
    )
    hb.start()

    # Synchronous busy loop on the main thread for ~0.25s — would block
    # any asyncio-scheduled task scheduled on this thread's loop. The
    # heartbeat is on a separate OS thread, so it continues firing.
    deadline = time.monotonic() + 0.25
    while time.monotonic() < deadline:
        pass

    hb.stop()
    events = _read_jsonl(transcript.path)
    hbs = [e for e in events if e["event"] == "turn_heartbeat"]
    assert len(hbs) >= 2, (
        "heartbeat thread MUST survive a blocked main-thread busy loop "
        "— if it doesn't, the threading choice is not load-bearing"
    )


def test_heartbeat_writes_atomic_under_concurrent_writers(tmp_path: Path):
    """Spec §2.1 — POSIX append is atomic up to PIPE_BUF; concurrent
    heartbeat threads must not corrupt the JSONL. Spawn two heartbeats
    targeting the same transcript and assert every recorded line is
    valid JSON."""
    transcript = Transcript(tmp_path / "transcript.jsonl")
    hb_a = HeartbeatThread(
        transcript=transcript, agent="claude", phase="phase2", round=1,
        interval=0.02,
    )
    hb_b = HeartbeatThread(
        transcript=transcript, agent="openai", phase="phase2", round=1,
        interval=0.02,
    )
    hb_a.start()
    hb_b.start()
    time.sleep(0.3)
    hb_a.stop()
    hb_b.stop()

    raw_lines = transcript.path.read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in raw_lines if line.strip()]
    # Every line must parse — no torn writes. Both agents must be seen.
    assert all(p["event"] == "turn_heartbeat" for p in parsed)
    agents = {p["agent"] for p in parsed}
    assert agents == {"claude", "openai"}


def test_heartbeat_thread_is_daemon(tmp_path: Path):
    """Spec §7 — heartbeat thread must be daemon so it never blocks
    interpreter shutdown."""
    transcript = Transcript(tmp_path / "transcript.jsonl")
    hb = HeartbeatThread(
        transcript=transcript, agent="claude", phase="phase0", round=1,
        interval=10.0,
    )
    hb.start()
    try:
        assert hb._thread.daemon, (
            "heartbeat thread must be daemon=True — otherwise a hung "
            "thread could block process exit"
        )
    finally:
        hb.stop()


def test_turn_heartbeat_event_dataclass_shape():
    """Spec §4 — TurnHeartbeat dataclass kind + fields."""
    ev = TurnHeartbeat(
        agent="claude", phase="phase2", round=1, elapsed_seconds=30,
    )
    assert ev.kind == "turn_heartbeat"
    d = ev.to_dict()
    assert d == {
        "kind": "turn_heartbeat",
        "agent": "claude",
        "phase": "phase2",
        "round": 1,
        "elapsed_seconds": 30,
    }


# ─── Layer 2 — per-turn BaseException capture ─────────────────────────


async def _run_one_call(agent, *, transcript: Transcript) -> AgentResult:
    bus = EventBus()
    return await run_one_call(
        agent=agent,
        prompt="prompt body",
        label="phase2-r1-claude",
        phase="phase2",
        metrics=Metrics(),
        transcript=transcript,
        event_bus=bus,
        stream_to=None,
        max_output_tokens=4096,
    )


def _fake_agent_raising(exc: BaseException) -> _FakeAgent:
    agent = _FakeAgent()

    async def runner(prompt: str) -> AgentResult:
        raise exc

    agent._runner = runner  # type: ignore[method-assign]
    return agent


def test_turn_api_exception_emits_violation_before_propagating(tmp_path: Path):
    """Spec §2.2 — wrapper emits a ``turn_api_call_exception`` violation
    BEFORE the exception propagates. The transcript carries the
    structured violation; the caller still sees the exception."""
    transcript = Transcript(tmp_path / "transcript.jsonl")
    agent = _fake_agent_raising(RuntimeError("simulated mid-stream blowup"))

    with pytest.raises(RuntimeError, match="simulated mid-stream blowup"):
        asyncio.run(_run_one_call(agent, transcript=transcript))

    events = _read_jsonl(transcript.path)
    pvs = [
        e for e in events
        if e["event"] == "protocol_violation"
        and e.get("violation_code") == "turn_api_call_exception"
    ]
    assert len(pvs) == 1
    pv = pvs[0]
    assert pv["agent"] == "claude"
    assert pv["phase"] == 2
    assert pv["round"] == 1
    assert "exception_type=RuntimeError" in pv["reason"]
    assert "simulated mid-stream blowup" in pv["reason"]
    # The violation must be written BEFORE turn_ended (which never fires
    # on a raising turn) — order property: violation appears in the
    # transcript, no turn_ended for the same key.
    assert not any(
        e["event"] == "turn_ended" and e.get("agent") == "claude"
        for e in events
    )


def test_turn_api_exception_unwraps_agent_error_cause(tmp_path: Path):
    """Spec §2.2 — exception-type fidelity. The agent wrappers catch
    ``anthropic.APIError`` and rewrap as :class:`AgentError`; the
    per-turn violation must record the UNDERLYING type so the diagnostic
    isn't masked."""
    transcript = Transcript(tmp_path / "transcript.jsonl")
    underlying = ValueError("underlying SDK shape")
    agent = _fake_agent_raising(AgentError("wrapped") )

    async def runner_with_cause(prompt: str) -> AgentResult:
        try:
            raise underlying
        except ValueError as e:
            raise AgentError("wrapped") from e

    agent._runner = runner_with_cause  # type: ignore[method-assign]

    with pytest.raises(AgentError):
        asyncio.run(_run_one_call(agent, transcript=transcript))

    events = _read_jsonl(transcript.path)
    pv = next(
        e for e in events
        if e["event"] == "protocol_violation"
        and e.get("violation_code") == "turn_api_call_exception"
    )
    # The diagnostic shows the original ValueError, not the wrapping
    # AgentError — that's the spec §2.2 "preserves exception type
    # fidelity" requirement.
    assert "exception_type=ValueError" in pv["reason"]
    assert "underlying SDK shape" in pv["reason"]


@pytest.mark.parametrize(
    "exc",
    [
        KeyboardInterrupt(),
        SystemExit(),
        MemoryError(),
        asyncio.CancelledError(),
    ],
)
def test_baseexception_subclasses_captured(exc: BaseException, tmp_path: Path):
    """Spec §2.2 — the wrap is ``except BaseException``, not
    ``except Exception``. Each of these escapes ``except Exception`` but
    must still produce a structured violation before propagating."""
    transcript = Transcript(tmp_path / "transcript.jsonl")
    agent = _fake_agent_raising(exc)

    with pytest.raises(type(exc)):
        asyncio.run(_run_one_call(agent, transcript=transcript))

    events = _read_jsonl(transcript.path)
    pvs = [
        e for e in events
        if e["event"] == "protocol_violation"
        and e.get("violation_code") == "turn_api_call_exception"
    ]
    assert len(pvs) == 1
    assert type(exc).__name__ in pvs[0]["reason"]


# ─── Layer 3 — whole-turn wall-clock cap ──────────────────────────────


def test_turn_under_cap_completes_normally(tmp_path: Path):
    """Sanity — a fast turn produces ``turn_ended`` and zero
    ``turn_api_call_timeout`` violations."""
    transcript = Transcript(tmp_path / "transcript.jsonl")
    agent = _FakeAgent()
    result = asyncio.run(_run_one_call(agent, transcript=transcript))
    assert result.text == "ok"

    events = _read_jsonl(transcript.path)
    assert any(e["event"] == "turn_started" for e in events)
    assert any(e["event"] == "turn_ended" for e in events)
    assert not any(
        e["event"] == "protocol_violation"
        and e.get("violation_code") == "turn_api_call_timeout"
        for e in events
    )


def test_turn_over_cap_emits_timeout_violation(tmp_path: Path, monkeypatch):
    """Spec §2.3 — wall-clock cap fires on a turn that exceeds it. We
    monkeypatch the cap down to 0.1s so the test stays fast."""
    monkeypatch.setattr(
        "dual_research.orchestrator._call.TURN_WALLCLOCK_CAP_SECONDS", 0.1,
    )
    transcript = Transcript(tmp_path / "transcript.jsonl")
    agent = _FakeAgent()

    async def runner_stall(prompt: str) -> AgentResult:
        await asyncio.sleep(5.0)  # well past the 0.1s cap
        return _fake_result(agent.label)

    agent._runner = runner_stall  # type: ignore[method-assign]

    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        asyncio.run(_run_one_call(agent, transcript=transcript))

    events = _read_jsonl(transcript.path)
    pvs = [
        e for e in events
        if e["event"] == "protocol_violation"
        and e.get("violation_code") == "turn_api_call_timeout"
    ]
    assert len(pvs) == 1
    pv = pvs[0]
    assert pv["agent"] == "claude"
    assert pv["phase"] == 2
    assert pv["round"] == 1
    assert "wall-clock cap" in pv["reason"]
    assert "sdk_timeout_seconds=600.0" in pv["reason"]
    # No turn_ended for the same key (the turn never completed).
    assert not any(e["event"] == "turn_ended" for e in events)


def test_timeout_cap_is_900_in_production():
    """Spec §2.3 / §7 — the production cap must remain 900s; tests must
    monkeypatch to a small value. This guards the constant against
    accidental drift."""
    assert TURN_WALLCLOCK_CAP_SECONDS == 900


def test_heartbeat_interval_is_30_in_production():
    """Spec §2.1 — production heartbeat interval = 30s."""
    assert TURN_HEARTBEAT_INTERVAL_SECONDS == 30


def test_timeout_ticks_retry_state_when_plumbed(tmp_path: Path, monkeypatch):
    """Spec §2.5 — when ``retry_state`` is threaded through
    ``run_one_call``, a timeout ticks the unified bucket. (Independent
    of whether the orchestrator chooses to retry; the counter is the
    contract.)"""
    monkeypatch.setattr(
        "dual_research.orchestrator._call.TURN_WALLCLOCK_CAP_SECONDS", 0.1,
    )
    transcript = Transcript(tmp_path / "transcript.jsonl")
    agent = _FakeAgent()

    async def runner_stall(prompt: str) -> AgentResult:
        await asyncio.sleep(5.0)
        return _fake_result(agent.label)

    agent._runner = runner_stall  # type: ignore[method-assign]

    state: dict = {}

    async def _go():
        await run_one_call(
            agent=agent,
            prompt="prompt body",
            label="phase4-r1-claude",
            phase="phase4",
            metrics=Metrics(),
            transcript=transcript,
            event_bus=EventBus(),
            stream_to=None,
            retry_state=state,
        )

    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        asyncio.run(_go())

    assert state[("claude", 4, 1)].count == 1


# ─── Layer 4 — verifier I2.8 ──────────────────────────────────────────


def _ts() -> dict:
    return {"event": "turn_started", "agent": "claude", "phase": 2, "round": 1}


def _te() -> dict:
    return {"event": "turn_ended", "agent": "claude", "phase": 2, "round": 1}


def test_i2_8_pass_with_turn_ended_terminal():
    events = [_ts(), _te()]
    res = _check_i2_8(events)
    assert res.id == "I2.8"
    assert res.severity == "reporting"
    assert res.verdict == "pass"


@pytest.mark.parametrize(
    "code",
    [
        "turn_api_call_timeout",
        "turn_api_call_exception",
        "empty_turn_persistent_identical_input",
        "empty_turn_retry_cap_exceeded",
    ],
)
def test_i2_8_pass_with_matching_protocol_violation(code: str):
    """Spec §2.4 — each of the four "this turn died in a structured way"
    violation codes counts as a terminal counterpart."""
    events = [
        _ts(),
        {
            "event": "protocol_violation",
            "agent": "claude",
            "phase": 2,
            "round": 1,
            "violation_code": code,
        },
    ]
    res = _check_i2_8(events)
    assert res.verdict == "pass"


def test_i2_8_pass_with_tombstone_terminal():
    """Spec §2.4 — tombstones may not carry per-turn coordinates so they
    clear every open turn (the run is dying)."""
    events = [_ts(), {"event": "tombstone"}]
    res = _check_i2_8(events)
    assert res.verdict == "pass"


def test_i2_8_fail_on_bare_turn_started():
    """Spec §2.4 — a ``turn_started`` with no terminal counterpart is
    the canonical bare-turn case (the 20260527-200213 phase-4 silent
    death)."""
    events = [
        {**_ts(), "ts": "2026-05-27T20:33:25Z"},
        {"event": "phase_exited", "phase": 2, "duration_ms": 100},
    ]
    res = _check_i2_8(events)
    assert res.verdict == "fail"
    assert any(
        "phase2/r1/claude" in ev.location
        and "no terminal event" in ev.detail
        for ev in res.evidence
    )


def test_i2_8_unrelated_protocol_violation_does_not_terminate():
    """Spec §2.4 — only the four spec-named violation codes terminate.
    A ``raiser_self_address`` ProtocolViolation does NOT count."""
    events = [
        _ts(),
        {
            "event": "protocol_violation",
            "agent": "claude",
            "phase": 2,
            "round": 1,
            "violation_code": "raiser_self_address",
        },
    ]
    res = _check_i2_8(events)
    assert res.verdict == "fail"


def test_i2_8_not_applicable_when_no_turn_started():
    """No ``turn_started`` events at all → invariant has nothing to
    assert against."""
    events = [{"event": "phase_entered", "phase": "phase0"}]
    res = _check_i2_8(events)
    assert res.verdict == "not_applicable"


def test_i2_8_independent_keys_tracked_independently():
    """Two turns in flight for different keys; only one of them gets a
    terminal counterpart. The other surfaces as a failure row."""
    events = [
        {"event": "turn_started", "agent": "claude", "phase": 2, "round": 1},
        {"event": "turn_started", "agent": "openai", "phase": 2, "round": 1},
        {"event": "turn_ended", "agent": "claude", "phase": 2, "round": 1},
        # openai's turn never ends.
    ]
    res = _check_i2_8(events)
    assert res.verdict == "fail"
    locs = [ev.location for ev in res.evidence]
    assert any("openai" in loc for loc in locs)
    assert not any("claude" in loc for loc in locs)


# ─── Layer 5 — retry-budget unification ───────────────────────────────


def test_on_turn_api_call_timeout_ticks_counter():
    """Spec §2.5 — first timeout ticks the bucket to 1 and returns a
    fail-fast :class:`ProtocolViolation`."""
    state: dict = {}
    pv = on_turn_api_call_timeout(
        state, agent="claude", phase=4, round=1,
    )
    assert isinstance(pv, ProtocolViolation)
    assert pv.violation_code == "turn_api_call_timeout"
    assert pv.agent == "claude"
    assert pv.phase == 4
    assert pv.round == 1
    assert state[("claude", 4, 1)].count == 1
    # The bucket's last_input_sha256 is preserved (timeout has no input
    # hash to compare against).
    assert state[("claude", 4, 1)].last_input_sha256 is None


def test_on_turn_api_call_timeout_always_fail_fast():
    """Spec §2.5 — the helper ALWAYS returns a violation. No retry
    happens because the helper is the fail-fast signal, not a
    "maybe retry" branch."""
    state: dict = {}
    pv1 = on_turn_api_call_timeout(state, agent="claude", phase=4, round=1)
    pv2 = on_turn_api_call_timeout(state, agent="claude", phase=4, round=1)
    assert pv1 is not None
    assert pv2 is not None
    assert "fail-fast" in pv1.reason
    assert "fail-fast" in pv2.reason


def test_mixed_timeout_and_empty_turn_unified_cap():
    """Spec §2.5 — empty-turn observation ticks to 1; subsequent
    timeout for the same key ticks to 2 (sharing the bucket)."""
    state: dict = {}
    hash_a = compute_input_sha256("prompt a")

    first = on_empty_turn(
        state, agent="claude", phase=4, round=1, input_sha256=hash_a,
    )
    assert first is None
    assert state[("claude", 4, 1)].count == 1

    pv = on_turn_api_call_timeout(
        state, agent="claude", phase=4, round=1,
    )
    assert isinstance(pv, ProtocolViolation)
    assert state[("claude", 4, 1)].count == 2
    # The empty-turn's hash is preserved across the timeout — a
    # subsequent identical-input empty turn still fail-fasts via the
    # spec 0239 path.
    assert state[("claude", 4, 1)].last_input_sha256 == hash_a


def test_timeout_buckets_independent_across_keys():
    """Spec §2.5 — per-(agent, phase, round) scoping holds for the
    timeout helper too."""
    state: dict = {}
    on_turn_api_call_timeout(state, agent="claude", phase=4, round=1)
    on_turn_api_call_timeout(state, agent="openai", phase=4, round=1)
    on_turn_api_call_timeout(state, agent="claude", phase=2, round=1)
    assert state[("claude", 4, 1)].count == 1
    assert state[("openai", 4, 1)].count == 1
    assert state[("claude", 2, 1)].count == 1
