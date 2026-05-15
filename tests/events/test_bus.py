from __future__ import annotations

import pytest

from dual_research.events import EventBus, PhaseEntered


@pytest.mark.asyncio
async def test_publish_delivers_to_subscriber() -> None:
    bus = EventBus()
    received: list[str] = []

    async def sub(ev):
        received.append(ev.phase)

    bus.subscribe(sub)
    await bus.publish(PhaseEntered(phase="phase0"))
    assert received == ["phase0"]


@pytest.mark.asyncio
async def test_sync_subscriber_also_works() -> None:
    bus = EventBus()
    received: list[str] = []

    def sub(ev):
        received.append(ev.phase)

    bus.subscribe(sub)
    await bus.publish(PhaseEntered(phase="phase1"))
    assert received == ["phase1"]


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery() -> None:
    bus = EventBus()
    received: list[str] = []
    unsub = bus.subscribe(lambda ev: received.append(ev.phase))
    await bus.publish(PhaseEntered(phase="a"))
    unsub()
    await bus.publish(PhaseEntered(phase="b"))
    assert received == ["a"]


@pytest.mark.asyncio
async def test_failing_subscriber_does_not_break_others() -> None:
    bus = EventBus()
    received: list[str] = []

    def bad(ev):
        raise RuntimeError("boom")

    def good(ev):
        received.append(ev.phase)

    bus.subscribe(bad)
    bus.subscribe(good)
    await bus.publish(PhaseEntered(phase="x"))
    assert received == ["x"]
