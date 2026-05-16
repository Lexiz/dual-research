"""Spec 0033 — ``TurnInputs`` event shape.

Smoke-tests the dataclass + event-bus round-trip. The aggregator and
server tests cover the downstream behaviour.
"""

from __future__ import annotations

import asyncio

from dual_research.events import EventBus, TurnInputs


def test_turn_inputs_dataclass_fields() -> None:
    e = TurnInputs(
        agent="claude",
        phase="phase2_round3",
        label="phase2-r3-claude",
        pieces={"system": "S", "brief": "B"},
    )
    assert e.kind == "turn_inputs"
    assert e.agent == "claude"
    assert e.phase == "phase2_round3"
    assert e.label == "phase2-r3-claude"
    assert e.pieces == {"system": "S", "brief": "B"}


def test_turn_inputs_default_pieces_is_empty_dict() -> None:
    e = TurnInputs(agent="openai", phase="phase0", label="phase0-openai")
    assert e.pieces == {}


def test_turn_inputs_round_trips_through_bus() -> None:
    """Subscriber sees the event with payload intact."""
    received: list[TurnInputs] = []

    async def run() -> None:
        bus = EventBus()
        bus.subscribe(lambda ev: received.append(ev) if isinstance(ev, TurnInputs) else None)
        await bus.publish(
            TurnInputs(
                agent="claude",
                phase="phase1",
                label="phase1-claude",
                pieces={"system": "sys text", "brief": "brief text"},
            )
        )

    asyncio.run(run())
    assert len(received) == 1
    assert received[0].pieces["brief"] == "brief text"


def test_turn_inputs_to_dict() -> None:
    """``to_dict`` round-trips for transcript persistence."""
    e = TurnInputs(
        agent="claude",
        phase="phase0",
        label="phase0-claude",
        pieces={"system": "S", "brief": "B"},
    )
    d = e.to_dict()
    assert d["kind"] == "turn_inputs"
    assert d["agent"] == "claude"
    assert d["pieces"] == {"system": "S", "brief": "B"}
