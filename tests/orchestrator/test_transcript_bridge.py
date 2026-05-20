"""Spec 0122 — event-bus → transcript bridge.

Confirms that publishing one of the allowlisted Deep-Research lifecycle
events to the bus results in a matching line in transcript.jsonl, and
that non-allowlisted events do NOT get double-written via the bridge.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.events import (
    CloseoutUrged,
    CloseoutViolation,
    EventBus,
    ItemRaised,
    ItemTransitioned,
    PhaseConverged,
    PhaseEntered,
)
from dual_research.orchestrator.run import _install_transcript_bridge
from dual_research.persistence import (
    Metrics,
    SessionContext,
    SessionDirectory,
    SessionState,
)


def _make_ctx(tmp_path: Path) -> SessionContext:
    sess = SessionDirectory(root=tmp_path / "run").ensure()
    state = SessionState()
    transcript = sess.open_transcript()
    metrics = Metrics()
    return SessionContext(
        session=sess, state=state, transcript=transcript, metrics=metrics,
    )


def _read_events(ctx: SessionContext) -> list[dict]:
    return ctx.transcript.read_events()


@pytest.mark.asyncio
async def test_bridge_mirrors_item_raised(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    bus = EventBus()
    _install_transcript_bridge(bus, ctx)

    await bus.publish(ItemRaised(
        id="D-plan-c-01",
        item_kind="disagreement",
        phase=2,
        round=1,
        raiser="claude",
        body="contested claim",
        anchor_type="quote",
        anchor_text="example anchor",
        evidence_required=True,
    ))

    events = _read_events(ctx)
    assert len(events) == 1
    rec = events[0]
    assert rec["event"] == "item_raised"
    assert rec["id"] == "D-plan-c-01"
    assert rec["item_kind"] == "disagreement"
    assert rec["phase"] == 2
    assert rec["raiser"] == "claude"


@pytest.mark.asyncio
async def test_bridge_mirrors_item_transitioned(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    bus = EventBus()
    _install_transcript_bridge(bus, ctx)

    await bus.publish(ItemTransitioned(
        id="D-plan-c-01",
        from_state="open",
        to_state="addressed",
        actor="openai",
        phase=2,
        round=2,
        reason="responded with counter-evidence",
    ))

    events = _read_events(ctx)
    assert len(events) == 1
    rec = events[0]
    assert rec["event"] == "item_transitioned"
    assert rec["from_state"] == "open"
    assert rec["to_state"] == "addressed"
    assert rec["actor"] == "openai"


@pytest.mark.asyncio
async def test_bridge_mirrors_closeout_and_phase_converged(tmp_path: Path) -> None:
    ctx = _make_ctx(tmp_path)
    bus = EventBus()
    _install_transcript_bridge(bus, ctx)

    await bus.publish(CloseoutUrged(
        phase=2, round=5, affected_items=["D-plan-c-01"],
        affected_raiser_budgets={"claude": 1, "openai": 2},
    ))
    await bus.publish(CloseoutViolation(
        phase=2, round=6, agent="claude",
        violation_code="closeout_violation_raise",
    ))
    await bus.publish(PhaseConverged(
        phase=2, final_round=6, via_closeout=True,
        via_ghost_cap=False, via_hard_cap=False,
    ))

    events = _read_events(ctx)
    names = [e["event"] for e in events]
    assert names == ["closeout_urged", "closeout_violation", "phase_converged"]


@pytest.mark.asyncio
async def test_bridge_ignores_non_allowlisted_events(tmp_path: Path) -> None:
    """``PhaseEntered`` is already written via direct ``transcript.write``
    in the orchestrator; the bridge must not double-write it.
    """
    ctx = _make_ctx(tmp_path)
    bus = EventBus()
    _install_transcript_bridge(bus, ctx)

    await bus.publish(PhaseEntered(phase="phase2"))

    events = _read_events(ctx)
    assert events == []
