"""Spec 0143 §3.1 Step 3 — DUAL_RESEARCH_DEBUG_USAGE env flag honoured.

The instrumentation is the load-bearing piece for diagnosing the next
Anthropic cache-non-engagement: when the flag is on, every LLM call
appends its raw SDK usage payload to ``<session>/usage-debug.jsonl`` so
a future reviewer can see exactly what shape the wire returned. When the
flag is off, the file must NOT be created — the instrumentation is
strictly opt-in, off by default.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from dual_research.agents.base import (
    append_usage_debug,
    debug_usage_enabled,
)


def test_debug_usage_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DUAL_RESEARCH_DEBUG_USAGE", raising=False)
    assert debug_usage_enabled() is False


@pytest.mark.parametrize("val", ["1", "true", "yes", "TRUE", "Yes"])
def test_debug_usage_enabled_truthy(
    monkeypatch: pytest.MonkeyPatch, val: str
) -> None:
    monkeypatch.setenv("DUAL_RESEARCH_DEBUG_USAGE", val)
    assert debug_usage_enabled() is True


def test_append_usage_debug_off_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("DUAL_RESEARCH_DEBUG_USAGE", raising=False)
    usage = SimpleNamespace(input_tokens=10, output_tokens=5)
    append_usage_debug(
        session_dir=str(tmp_path),
        provider="anthropic",
        model_id="claude-sonnet-4-6",
        label="phase0-r1-claude",
        usage_payload=usage,
    )
    assert not (tmp_path / "usage-debug.jsonl").exists()


def test_append_usage_debug_on_appends_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DUAL_RESEARCH_DEBUG_USAGE", "1")
    usage = SimpleNamespace(
        input_tokens=100,
        output_tokens=50,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    append_usage_debug(
        session_dir=str(tmp_path),
        provider="anthropic",
        model_id="claude-sonnet-4-6",
        label="phase0-r1-claude",
        usage_payload=usage,
        extra={"cache_intended": True, "stop_reason": "end_turn"},
    )
    path = tmp_path / "usage-debug.jsonl"
    assert path.exists()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["provider"] == "anthropic"
    assert rows[0]["model_id"] == "claude-sonnet-4-6"
    assert rows[0]["label"] == "phase0-r1-claude"
    assert rows[0]["usage"]["input_tokens"] == 100
    assert rows[0]["usage"]["cache_read_input_tokens"] == 0
    assert rows[0]["cache_intended"] is True
    assert rows[0]["stop_reason"] == "end_turn"


def test_append_usage_debug_no_session_dir_noops(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If session_dir is None (replay path / fixture path), silently skip."""
    monkeypatch.setenv("DUAL_RESEARCH_DEBUG_USAGE", "1")
    usage = SimpleNamespace(input_tokens=10)
    # Must not raise.
    append_usage_debug(
        session_dir=None,
        provider="anthropic",
        model_id="x",
        label="y",
        usage_payload=usage,
    )
    assert list(tmp_path.iterdir()) == []


def test_append_usage_debug_swallows_serialisation_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A payload that can't be serialised must NOT break the run."""
    monkeypatch.setenv("DUAL_RESEARCH_DEBUG_USAGE", "1")

    class _Unserialisable:
        def __init__(self):
            self.circular = self

    # Even with a degenerate payload, the helper falls back to repr() and
    # writes something. Critical contract: never raise.
    append_usage_debug(
        session_dir=str(tmp_path),
        provider="anthropic",
        model_id="x",
        label="y",
        usage_payload=_Unserialisable(),
    )
    # Whether or not a row was written, the call must have returned cleanly.
