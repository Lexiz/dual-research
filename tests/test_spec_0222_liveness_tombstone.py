"""Spec 0222 — liveness tombstone regression-prevention tests.

Locks in the Area-5 liveness invariant: every ``run_started`` is followed
by exactly one terminal event (``run_completed`` / ``run_failed`` /
``run_aborted``) and ``metrics.ended_at`` is non-null — including when:

  - the run dies from a ``BaseException`` subclass that does **not**
    subclass ``Exception`` (``asyncio.CancelledError``, ``KeyboardInterrupt``,
    ``SystemExit``); covered by Test 1.
  - the success-path and except-path tombstones both fail to land (corrupt
    transcript handle); covered by Test 2's defensive-fallback assertion.

Both tests must fail against the pre-fix ``except Exception`` orchestrator
and pass after Spec 0222 §4.1–§4.4 lands.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from dual_research.config import Credentials, TEST_TIER
from dual_research.orchestrator import run as orch_run
from dual_research.persistence.transcript import Transcript


_FAKE_CREDS = Credentials(
    anthropic_api_key="sk-test-anthropic",
    openai_api_key="sk-test-openai",
    notion_token=None,
)


def _make_session(tmp_path: Path) -> Path:
    root = tmp_path / "session"
    root.mkdir()
    (root / "brief.md").write_text("# Test brief\n\nSpec 0222 liveness test.", encoding="utf-8")
    return root


def _read_events(session_root: Path) -> list[dict]:
    text = (session_root / "transcript.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_baseexception_path_writes_terminal_event_and_re_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec 0222 §4.1 — BaseException kill-test.

    The phase runner raises ``asyncio.CancelledError`` mid-phase. The
    widened ``except BaseException`` catches it, writes ``run_failed``,
    sets ``metrics.ended_at``, and re-raises so structured-concurrency
    cancellation propagates correctly. Pre-fix code (``except Exception``)
    fails this test on (a) and (b) because ``CancelledError`` escapes
    the handler entirely and no tombstone is ever written.
    """
    session_root = _make_session(tmp_path)

    async def cancel_immediately(**_kw):
        raise asyncio.CancelledError("simulated mid-phase kill")

    monkeypatch.setattr(orch_run, "run_phase0", cancel_immediately)

    # (c) The CancelledError is re-raised, not swallowed.
    with pytest.raises(asyncio.CancelledError):
        await orch_run.run_session(
            session_root=session_root,
            slug="test-spec-0222-t1",
            creds=_FAKE_CREDS,
            tier=TEST_TIER,
            soft_cap=6,
            hard_cap=12,
        )

    # (a) Exactly one terminal event is present on disk; it is one of
    # the run_failed / run_aborted pair (the spec accepts either).
    events = _read_events(session_root)
    terminal = [e for e in events if e["event"] in ("run_completed", "run_failed", "run_aborted")]
    assert len(terminal) == 1, (
        f"liveness invariant violated: expected exactly one terminal event, "
        f"got {[e['event'] for e in terminal]}"
    )
    assert terminal[0]["event"] in ("run_failed", "run_aborted")

    # (b) metrics.json's ended_at is non-null.
    metrics_payload = json.loads((session_root / "metrics.json").read_text(encoding="utf-8"))
    assert metrics_payload.get("ended_at") is not None, (
        "metrics.ended_at must be set on the terminal write path"
    )


@pytest.mark.asyncio
async def test_defensive_fallback_writes_run_aborted_when_tombstone_writes_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec 0222 §4.3 — defensive-fallback path.

    Both the success-path ``transcript.write("run_completed", ...)`` and
    the except-path ``transcript.write("run_failed", ...)`` are patched
    to raise (simulates a corrupt transcript handle). The ``finally:``
    fallback must still write ``run_aborted`` with
    ``reason="terminal-event-fallback"`` and call ``metrics.mark_done()``.

    The phase runner raises a regular ``RuntimeError`` (so we exercise
    the new code path through the widened handler without going through
    the cancellation re-raise branch). The ``run_failed`` write inside
    the except handler raises; that propagates out of the handler; the
    ``finally:`` block sees ``_terminal_written == False`` and runs the
    fallback. Pre-fix code has no fallback — no terminal event lands.
    """
    session_root = _make_session(tmp_path)

    async def raise_runtime(**_kw):
        raise RuntimeError("simulated phase failure")

    monkeypatch.setattr(orch_run, "run_phase0", raise_runtime)

    real_write = Transcript.write
    failed_write_events: list[str] = []

    def patched_write(self, event: str, **fields):
        # Simulate the corrupt-transcript handle for the two tombstone
        # writes the spec calls out by name. Everything else (run_started,
        # turn_*, run_aborted from the fallback) passes through to the
        # real implementation so the test can read the on-disk transcript.
        if event in ("run_completed", "run_failed"):
            failed_write_events.append(event)
            raise RuntimeError(f"simulated corrupt transcript handle on {event}")
        real_write(self, event, **fields)

    monkeypatch.setattr(Transcript, "write", patched_write)

    # The transcript.write("run_failed", ...) inside the except handler
    # raises; that propagates out of run_session — but only after the
    # finally fallback has fired.
    with pytest.raises(RuntimeError):
        await orch_run.run_session(
            session_root=session_root,
            slug="test-spec-0222-t2",
            creds=_FAKE_CREDS,
            tier=TEST_TIER,
            soft_cap=6,
            hard_cap=12,
        )

    # The except-path "run_failed" write was attempted (and raised) — the
    # half of the failure mode the spec's §4.3 fallback exists to cover.
    assert "run_failed" in failed_write_events

    # The defensive fallback wrote run_aborted with the documented reason.
    events = _read_events(session_root)
    aborted = [e for e in events if e["event"] == "run_aborted"]
    assert len(aborted) == 1, (
        f"defensive-fallback path did not write run_aborted; events: "
        f"{[e['event'] for e in events]}"
    )
    assert aborted[0].get("reason") == "terminal-event-fallback"

    # The fallback's metrics.mark_done() set ended_at.
    metrics_payload = json.loads((session_root / "metrics.json").read_text(encoding="utf-8"))
    assert metrics_payload.get("ended_at") is not None, (
        "fallback path must set metrics.ended_at via metrics.mark_done()"
    )
