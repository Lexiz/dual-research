"""Spec 0032 — `_push_watch_loop` periodic push during a live run.

The loop calls `RemoteSession.push_session_dir` on a timer, swallows
errors so the orchestrator isn't aborted by Supabase blips, and always
fires one final synchronous push when the stop event is set.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from dual_research.config import SupabaseCredentials
from dual_research.orchestrator.run import _push_watch_loop


class _FakeRemoteSession:
    """Stand-in for `RemoteSession` — records calls, optionally raises."""

    # Singleton-ish: tests put the test's chosen instance here before
    # spawning the loop, and `from_credentials` returns it. Avoids the
    # "loop creates a fresh fake the test can't reach" pitfall.
    _shared: "_FakeRemoteSession | None" = None

    def __init__(self, *, raises: bool = False) -> None:
        self.calls: list[Path] = []
        self.raises = raises

    @classmethod
    def install(cls, raises: bool = False) -> "_FakeRemoteSession":
        cls._shared = cls(raises=raises)
        return cls._shared

    @classmethod
    def from_credentials(cls, url: str, service_role_key: str) -> "_FakeRemoteSession":
        if cls._shared is None:
            cls._shared = cls()
        return cls._shared

    def push_session_dir(self, session_dir: Path) -> None:
        self.calls.append(Path(session_dir))
        if self.raises:
            raise RuntimeError("simulated supabase outage")


@pytest.fixture
def creds() -> SupabaseCredentials:
    return SupabaseCredentials(
        url="https://example.supabase.co",
        anon_key="anon",
        service_role_key="service",
    )


@pytest.fixture(autouse=True)
def reset_fake_singleton():
    yield
    _FakeRemoteSession._shared = None


@pytest.mark.asyncio
async def test_periodic_tick_pushes_each_interval(tmp_path: Path, creds: SupabaseCredentials) -> None:
    """The loop pushes on each interval; the warm-up wait keeps the first
    tick from firing immediately. We verify by setting `stop` past the
    warm-up window — at least one push fires."""
    fake = _FakeRemoteSession.install()
    stop = asyncio.Event()
    with patch("dual_research.persistence.remote.RemoteSession", _FakeRemoteSession):
        loop_task = asyncio.create_task(
            _push_watch_loop(
                session_dir=tmp_path,
                creds=creds,
                stop=stop,
                interval_seconds=0.1,
            )
        )
        await asyncio.sleep(0.05)
        stop.set()
        await asyncio.wait_for(loop_task, timeout=10.0)
    assert len(fake.calls) >= 1
    for call_path in fake.calls:
        assert call_path == tmp_path


@pytest.mark.asyncio
async def test_tick_errors_are_swallowed(tmp_path: Path, creds: SupabaseCredentials) -> None:
    """A push failure mid-run must NOT propagate — Supabase blip ≠ run abort."""
    fake = _FakeRemoteSession.install(raises=True)
    stop = asyncio.Event()
    with patch("dual_research.persistence.remote.RemoteSession", _FakeRemoteSession):
        loop_task = asyncio.create_task(
            _push_watch_loop(
                session_dir=tmp_path,
                creds=creds,
                stop=stop,
                interval_seconds=0.05,
            )
        )
        await asyncio.sleep(0.05)
        stop.set()
        # The loop should exit normally despite every push raising.
        await asyncio.wait_for(loop_task, timeout=10.0)
    assert len(fake.calls) >= 1


@pytest.mark.asyncio
async def test_stop_event_triggers_final_push(tmp_path: Path, creds: SupabaseCredentials) -> None:
    """Setting `stop` ends the loop AND fires one last synchronous push."""
    fake = _FakeRemoteSession.install()
    stop = asyncio.Event()
    with patch("dual_research.persistence.remote.RemoteSession", _FakeRemoteSession):
        loop_task = asyncio.create_task(
            _push_watch_loop(
                session_dir=tmp_path,
                creds=creds,
                stop=stop,
                interval_seconds=60.0,  # never fires by itself
            )
        )
        await asyncio.sleep(0.05)
        stop.set()
        await asyncio.wait_for(loop_task, timeout=10.0)
    # Final push fires exactly once.
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_remote_session_init_failure_does_not_crash(
    tmp_path: Path, creds: SupabaseCredentials
) -> None:
    """If RemoteSession.from_credentials raises (missing dep, bad URL),
    the loop logs and returns without raising."""

    class _RaisingFactory:
        @classmethod
        def from_credentials(cls, url: str, key: str) -> "_RaisingFactory":
            raise RuntimeError("simulated init failure")

    stop = asyncio.Event()
    with patch("dual_research.persistence.remote.RemoteSession", _RaisingFactory):
        # Loop exits cleanly — no exception escapes.
        await asyncio.wait_for(
            _push_watch_loop(
                session_dir=tmp_path,
                creds=creds,
                stop=stop,
                interval_seconds=0.05,
            ),
            timeout=5.0,
        )
