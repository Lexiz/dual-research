"""Spec 0224 — CLI signal-handler tombstone regression-prevention tests.

Locks in the contract that raw SIGTERM / SIGHUP / SIGINT delivered to the
local-CLI orchestrator routes into Python's exception machinery as
``asyncio.CancelledError``, which spec 0222's ``except BaseException`` at
``orchestrator/run.py`` already tombstones. Without the cli-side
``_run_with_signal_handlers`` wrapper, SIGTERM and SIGHUP take CPython's
default disposition (immediate process termination, no exception raised),
bypassing both the except block and the ``_terminal_written`` finally
fallback — the run dies silently with no terminal event and
``metrics.ended_at == null``.

Each test:
  - Patches ``orch_run.run_phase0`` to a long sleep so the run is mid-flight.
  - Fires ``os.kill(os.getpid(), <signal>)`` after a short delay.
  - Awaits ``cli._run_with_signal_handlers(orch_run.run_session(...))``.
  - Asserts (a) exactly one terminal event on disk, (b) it is
    ``run_failed`` or ``run_aborted``, (c) ``metrics.ended_at`` is non-null.

All three tests fail against pre-fix ``cli.py`` (the wrapper does not exist
— ``AttributeError`` on import) and pass after spec 0224 lands.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
from pathlib import Path

import pytest

from dual_research import cli
from dual_research.config import Credentials, TEST_TIER
from dual_research.orchestrator import run as orch_run


_FAKE_CREDS = Credentials(
    anthropic_api_key="sk-test-anthropic",
    openai_api_key="sk-test-openai",
    notion_token=None,
)


def _make_session(tmp_path: Path) -> Path:
    root = tmp_path / "session"
    root.mkdir()
    (root / "brief.md").write_text(
        "# Test brief\n\nSpec 0224 signal-handler test.", encoding="utf-8"
    )
    return root


def _read_events(session_root: Path) -> list[dict]:
    text = (session_root / "transcript.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


async def _drive_signal_run(
    session_root: Path,
    sig: int,
    slug: str,
) -> None:
    async def slow_phase(**_kw):
        await asyncio.sleep(30)

    # Trigger the signal once the run is in-flight. asyncio's signal
    # handler delivers via the loop's wakeup fd; the running task's await
    # raises CancelledError on the next iteration.
    async def trigger():
        await asyncio.sleep(0.1)
        os.kill(os.getpid(), sig)

    asyncio.create_task(trigger())

    with pytest.raises(asyncio.CancelledError):
        await cli._run_with_signal_handlers(
            orch_run.run_session(
                session_root=session_root,
                slug=slug,
                creds=_FAKE_CREDS,
                tier=TEST_TIER,
                soft_cap=6,
                hard_cap=12,
            )
        )


@pytest.mark.asyncio
async def test_sigterm_tombstone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec 0224 §5 Test 1 — SIGTERM during a mid-phase run produces a
    terminal event and non-null ``metrics.ended_at``."""
    session_root = _make_session(tmp_path)

    async def slow_phase(**_kw):
        await asyncio.sleep(30)

    monkeypatch.setattr(orch_run, "run_phase0", slow_phase)

    await _drive_signal_run(session_root, signal.SIGTERM, "test-0224-sigterm")

    events = _read_events(session_root)
    terminal = [
        e for e in events if e["event"] in ("run_completed", "run_failed", "run_aborted")
    ]
    assert len(terminal) == 1, (
        f"liveness invariant violated: expected exactly one terminal event, "
        f"got {[e['event'] for e in terminal]}"
    )
    assert terminal[0]["event"] in ("run_failed", "run_aborted")

    metrics_payload = json.loads(
        (session_root / "metrics.json").read_text(encoding="utf-8")
    )
    assert metrics_payload.get("ended_at") is not None, (
        "metrics.ended_at must be set on the signal-cancel tombstone path"
    )


@pytest.mark.asyncio
async def test_sighup_tombstone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec 0224 §5 Test 2 — SIGHUP (terminal close, SSH disconnect,
    laptop sleep) produces a terminal event. Locks in the mac-local-CLI
    most-likely-death case."""
    session_root = _make_session(tmp_path)

    async def slow_phase(**_kw):
        await asyncio.sleep(30)

    monkeypatch.setattr(orch_run, "run_phase0", slow_phase)

    await _drive_signal_run(session_root, signal.SIGHUP, "test-0224-sighup")

    events = _read_events(session_root)
    terminal = [
        e for e in events if e["event"] in ("run_completed", "run_failed", "run_aborted")
    ]
    assert len(terminal) == 1
    assert terminal[0]["event"] in ("run_failed", "run_aborted")

    metrics_payload = json.loads(
        (session_root / "metrics.json").read_text(encoding="utf-8")
    )
    assert metrics_payload.get("ended_at") is not None


@pytest.mark.asyncio
async def test_sigint_tombstone_via_cancellederror_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec 0224 §5 Test 3 — SIGINT (Ctrl-C) is intentionally swapped
    from the default ``KeyboardInterrupt`` path to the
    ``asyncio.CancelledError`` path. A terminal event is still written
    (both paths flow through ``except BaseException`` at run.py:548), and
    the ``error_type`` field is ``CancelledError`` — confirming the new
    handler path ran, not the legacy default."""
    session_root = _make_session(tmp_path)

    async def slow_phase(**_kw):
        await asyncio.sleep(30)

    monkeypatch.setattr(orch_run, "run_phase0", slow_phase)

    await _drive_signal_run(session_root, signal.SIGINT, "test-0224-sigint")

    events = _read_events(session_root)
    terminal = [
        e for e in events if e["event"] in ("run_completed", "run_failed", "run_aborted")
    ]
    assert len(terminal) == 1
    term = terminal[0]
    assert term["event"] in ("run_failed", "run_aborted")
    # If the new handler path fired, the SIGINT was converted to
    # CancelledError (not KeyboardInterrupt). run_failed carries the
    # ``error_type`` field; run_aborted only fires via the finally
    # fallback and doesn't carry it.
    if term["event"] == "run_failed":
        assert term.get("error_type") == "CancelledError", (
            f"expected SIGINT to surface as CancelledError via the new handler "
            f"path, got error_type={term.get('error_type')!r}"
        )

    metrics_payload = json.loads(
        (session_root / "metrics.json").read_text(encoding="utf-8")
    )
    assert metrics_payload.get("ended_at") is not None
