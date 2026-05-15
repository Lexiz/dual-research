from __future__ import annotations

import asyncio

import pytest

from dual_research.agents.base import (
    _extract_retry_after,
    _is_rate_limit,
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
