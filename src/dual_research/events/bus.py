from __future__ import annotations

import logging
from typing import Awaitable, Callable

from dual_research.events.types import Event

logger = logging.getLogger(__name__)


Subscriber = Callable[[Event], Awaitable[None] | None]


class EventBus:
    """In-memory async pub/sub.

    Publishers call `publish(event)`. All registered subscribers are invoked
    in registration order. A subscriber failure is caught and logged; it does
    not propagate to the publisher or other subscribers (one bad subscriber
    must not break the run).
    """

    def __init__(self) -> None:
        self._subscribers: list[Subscriber] = []

    def subscribe(self, callback: Subscriber) -> Callable[[], None]:
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

        return unsubscribe

    async def publish(self, event: Event) -> None:
        import inspect

        for sub in list(self._subscribers):
            try:
                result = sub(event)
                if inspect.isawaitable(result):
                    await result
            except Exception as e:
                logger.warning("event-bus subscriber raised: %s", e, exc_info=True)
