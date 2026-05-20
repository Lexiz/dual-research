from __future__ import annotations

import asyncio

import httpx
import pytest

from dual_research.agents.base import (
    _extract_retry_after,
    _is_rate_limit,
    _is_transient_error,
    with_rate_limit_retry,
)


class _FakeHeaders(dict):
    pass


class _FakeResponse:
    def __init__(self, headers):
        self.headers = _FakeHeaders(headers)


class _Fake429(Exception):
    def __init__(self, retry_after=None):
        super().__init__("rate limit")
        self.status_code = 429
        self.response = _FakeResponse(
            {"retry-after": str(retry_after)} if retry_after is not None else {}
        )


@pytest.mark.asyncio
async def test_no_retry_on_non_rate_limit() -> None:
    calls = 0

    async def boom():
        nonlocal calls
        calls += 1
        raise ValueError("not a rate limit")

    with pytest.raises(ValueError):
        await with_rate_limit_retry(boom, agent_label="claude", max_attempts=3)
    assert calls == 1


@pytest.mark.asyncio
async def test_success_on_first_attempt() -> None:
    async def ok():
        return "ok"

    out = await with_rate_limit_retry(ok, agent_label="claude")
    assert out == "ok"


@pytest.mark.asyncio
async def test_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    # Replace sleep with no-op for fast test
    monkeypatch.setattr("dual_research.agents.base.asyncio.sleep", _noop_sleep)
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise _Fake429(retry_after=1)
        return "recovered"

    out = await with_rate_limit_retry(flaky, agent_label="claude", max_attempts=5, min_sleep=0.0)
    assert out == "recovered"
    assert calls == 3


@pytest.mark.asyncio
async def test_exhausts_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dual_research.agents.base.asyncio.sleep", _noop_sleep)
    calls = 0

    async def always_429():
        nonlocal calls
        calls += 1
        raise _Fake429(retry_after=1)

    with pytest.raises(_Fake429):
        await with_rate_limit_retry(always_429, agent_label="claude", max_attempts=3, min_sleep=0.0)
    assert calls == 3


def test_is_rate_limit_by_status_code() -> None:
    assert _is_rate_limit(_Fake429()) is True
    assert _is_rate_limit(ValueError("x")) is False


def test_extract_retry_after_parses_seconds() -> None:
    assert _extract_retry_after(_Fake429(retry_after=42)) == 42.0
    assert _extract_retry_after(_Fake429()) is None


def test_extract_retry_after_handles_bad_value() -> None:
    exc = _Fake429()
    exc.response.headers["retry-after"] = "not-a-number"
    assert _extract_retry_after(exc) is None


async def _noop_sleep(_seconds):
    return None


# ─── Transient (network/streaming) error retry — spec-0032-followup ────


class _Fake5xx(Exception):
    """SDK-style exception carrying an HTTP status_code."""
    def __init__(self, status: int) -> None:
        super().__init__(f"server error {status}")
        self.status_code = status


def test_is_transient_error_catches_httpx_read_error() -> None:
    # This is the exact error class that killed the dvs-backend-language run.
    assert _is_transient_error(httpx.ReadError("connection dropped")) is True


def test_is_transient_error_catches_httpx_remote_protocol_error() -> None:
    assert _is_transient_error(httpx.RemoteProtocolError("server hung up")) is True


def test_is_transient_error_catches_connect_and_timeout_families() -> None:
    assert _is_transient_error(httpx.ConnectError("refused")) is True
    assert _is_transient_error(httpx.ConnectTimeout("slow")) is True
    assert _is_transient_error(httpx.ReadTimeout("slow")) is True
    assert _is_transient_error(httpx.PoolTimeout("pool")) is True


def test_is_transient_error_catches_5xx_status() -> None:
    assert _is_transient_error(_Fake5xx(500)) is True
    assert _is_transient_error(_Fake5xx(502)) is True
    assert _is_transient_error(_Fake5xx(503)) is True
    assert _is_transient_error(_Fake5xx(599)) is True


def test_is_transient_error_rejects_4xx_and_unrelated() -> None:
    assert _is_transient_error(_Fake5xx(404)) is False
    assert _is_transient_error(_Fake5xx(429)) is False  # rate-limit goes through _is_rate_limit
    assert _is_transient_error(ValueError("nope")) is False


@pytest.mark.asyncio
async def test_retries_transient_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """A mid-stream ReadError must be retried, not killed.

    Regression for the dvs-backend-language run (2026-05-20) where phase-0
    completed and phase-1 died on a single httpx.ReadError, losing $1.01."""
    monkeypatch.setattr("dual_research.agents.base.asyncio.sleep", _noop_sleep)
    calls = 0

    async def flaky_stream():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ReadError("stream dropped mid-response")
        return "phase-1 plan text"

    out = await with_rate_limit_retry(
        flaky_stream,
        agent_label="claude",
        transient_min_sleep=0.0,
    )
    assert out == "phase-1 plan text"
    assert calls == 3


@pytest.mark.asyncio
async def test_transient_retry_respects_its_own_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """transient_max_attempts caps the retries; the final error is raised."""
    monkeypatch.setattr("dual_research.agents.base.asyncio.sleep", _noop_sleep)
    calls = 0

    async def always_drops():
        nonlocal calls
        calls += 1
        raise httpx.ReadError("permanently broken")

    with pytest.raises(httpx.ReadError):
        await with_rate_limit_retry(
            always_drops,
            agent_label="claude",
            transient_max_attempts=4,
            transient_min_sleep=0.0,
        )
    assert calls == 4


@pytest.mark.asyncio
async def test_rate_limit_and_transient_budgets_are_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A run that hits both error classes shouldn't exhaust one bucket's
    budget on the other class. Two rate-limits + two transient errors,
    then success — must succeed because neither bucket exceeds its cap."""
    monkeypatch.setattr("dual_research.agents.base.asyncio.sleep", _noop_sleep)
    sequence: list[Exception | str] = [
        _Fake429(retry_after=1),
        httpx.ReadError("drop 1"),
        _Fake429(retry_after=1),
        httpx.ReadError("drop 2"),
        "ok",
    ]
    idx = 0

    async def mixed():
        nonlocal idx
        item = sequence[idx]
        idx += 1
        if isinstance(item, Exception):
            raise item
        return item

    out = await with_rate_limit_retry(
        mixed,
        agent_label="claude",
        max_attempts=3,
        min_sleep=0.0,
        transient_max_attempts=4,
        transient_min_sleep=0.0,
    )
    assert out == "ok"
    assert idx == 5  # all five sequence entries consumed
