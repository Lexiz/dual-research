"""Spec 0241 — per-turn liveness instrumentation.

Three layers that together make the wall-clock behaviour of a per-turn
API call observable, structured, and bounded:

* **Layer 1** — :class:`HeartbeatThread`. A separate OS thread emits a
  ``turn_heartbeat`` transcript event every
  :data:`TURN_HEARTBEAT_INTERVAL_SECONDS`. The thread is daemon so it
  never blocks process exit, and writes go through the
  :class:`~dual_research.persistence.transcript.Transcript`'s
  atomic-append pattern so concurrent heartbeats from sibling turns do
  not corrupt the JSONL. Using a separate OS thread (not an asyncio
  task) is load-bearing: if the event loop itself is blocked, an
  asyncio-scheduled heartbeat would never run.

* **Layer 2 / 3** — the wrapper helpers in
  :mod:`dual_research.orchestrator._call` use
  :data:`TURN_WALLCLOCK_CAP_SECONDS` and emit the two new
  :class:`~dual_research.events.types.ProtocolViolation` codes
  registered on the event dataclass:
  ``turn_api_call_timeout`` (wall-clock cap fired) and
  ``turn_api_call_exception`` (raw ``BaseException`` escaped the per-
  turn API call).

The constants are module-level by design; until a real call site asks
for a runtime override, hardcoded is correct (spec 0241 §5).
"""
from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dual_research.persistence.transcript import Transcript


__all__ = [
    "TURN_HEARTBEAT_INTERVAL_SECONDS",
    "TURN_WALLCLOCK_CAP_SECONDS",
    "HeartbeatThread",
]


# Spec 0241 §2.1 — one heartbeat every 30s per active turn. One syscall
# per interval per active turn; budget is negligible against transcripts
# that already carry hundreds of events.
TURN_HEARTBEAT_INTERVAL_SECONDS = 30

# Spec 0241 §2.3 — whole-turn wall-clock cap. 900s gives a 300s margin
# above the SDK's 600s request-establishment timeout so the two never
# race: a fired ``turn_api_call_timeout`` is unambiguously a stream-
# consumption stall, and the SDK's 600s would have surfaced first on a
# request-establishment hang via the Layer 2 BaseException capture.
TURN_WALLCLOCK_CAP_SECONDS = 900


class HeartbeatThread:
    """Spec 0241 §2.1 — separate-OS-thread heartbeat emitter.

    Lifecycle: :meth:`start` launches a daemon thread that wakes every
    ``interval`` seconds and writes one ``turn_heartbeat`` event to
    ``transcript``. :meth:`stop` signals the thread to exit and joins.
    The thread is daemon=True so a hung join never blocks interpreter
    shutdown.

    Heartbeat writes use the transcript's append-mode pattern; POSIX
    ``write(2)`` on an O_APPEND file is atomic up to ``PIPE_BUF`` (≥ 4KB
    on every supported platform), and a single heartbeat line is well
    under that. No extra locking is required between concurrent
    sibling-turn heartbeats.
    """

    def __init__(
        self,
        *,
        transcript: "Transcript",
        agent: str,
        phase: str,
        round: int,
        interval: float = TURN_HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        self._transcript = transcript
        self._agent = agent
        self._phase = phase
        self._round = round
        self._interval = interval
        self._stop = threading.Event()
        self._start_monotonic: float | None = None
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"hb-{agent}-{phase}-r{round}",
        )

    def start(self) -> None:
        self._start_monotonic = time.monotonic()
        self._thread.start()

    def stop(self, *, join_timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=join_timeout)

    def _run(self) -> None:
        assert self._start_monotonic is not None
        while not self._stop.wait(self._interval):
            elapsed = int(time.monotonic() - self._start_monotonic)
            try:
                self._transcript.write(
                    "turn_heartbeat",
                    agent=self._agent,
                    phase=self._phase,
                    round=self._round,
                    elapsed_seconds=elapsed,
                )
            except Exception:
                # Defensive — a transcript write failure on the heartbeat
                # path must never crash the thread (it would silently stop
                # heartbeats, defeating the diagnostic purpose). The next
                # interval retries.
                pass
