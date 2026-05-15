from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.persistence import (
    Metrics,
    SessionDirectory,
    SessionState,
    Transcript,
    load_state,
    save_state,
    write_atomic,
)


def test_session_state_round_trip(tmp_path: Path) -> None:
    s = SessionState(
        phase="phase2",
        drafter="claude",
        agreed_plan="some plan",
        final_surfaced_disagreements=[{"id": "FSD-1", "title": "scope"}],
        draft_round=2,
        final_emitted_to="/tmp/foo.md",
    )
    p = tmp_path / "state.json"
    save_state(p, s)
    s2 = load_state(p)
    assert s2 == s


def test_load_state_returns_default_when_missing(tmp_path: Path) -> None:
    s = load_state(tmp_path / "absent.json")
    assert s.phase == "phase0"
    assert s.drafter is None


def test_write_atomic_does_not_leave_temp_files(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    write_atomic(p, "hello")
    write_atomic(p, "hello again")
    # No leftover .state.json.* tempfiles
    leftovers = [f for f in tmp_path.iterdir() if f.name.startswith(".state.json.")]
    assert leftovers == []
    assert p.read_text() == "hello again"


def test_transcript_append_and_read(tmp_path: Path) -> None:
    t = Transcript(tmp_path / "transcript.jsonl")
    t.write("hello", a=1)
    t.write("world", b="two")
    events = t.read_events()
    assert len(events) == 2
    assert events[0]["event"] == "hello" and events[0]["a"] == 1
    assert events[1]["event"] == "world" and events[1]["b"] == "two"
    assert "ts" in events[0] and "ts" in events[1]


def test_metrics_record_and_totals(tmp_path: Path) -> None:
    m = Metrics()
    r1 = AgentResult(
        text="x",
        usage=TokenUsage(input_tokens=100, output_tokens=200, cache_read_tokens=10, cache_write_tokens=20),
        cost_usd=0.123,
        duration_ms=1500,
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        label="claude",
    )
    r2 = AgentResult(
        text="y",
        usage=TokenUsage(input_tokens=50, output_tokens=100),
        cost_usd=0.05,
        duration_ms=800,
        model_id="gpt-5.5",
        provider="openai",
        label="openai",
    )
    m.record(label="phase0-claude", result=r1)
    m.record(label="phase0-openai", result=r2)
    assert m.total_cost_usd() == pytest.approx(0.173)
    totals = m.totals_by_agent()
    assert totals["claude"]["input_tokens"] == 100
    assert totals["openai"]["output_tokens"] == 100
    assert totals["claude"]["calls"] == 1
    p = tmp_path / "metrics.json"
    m.save(p)
    loaded = json.loads(p.read_text())
    assert loaded["total_cost_usd"] == pytest.approx(0.173)
    assert "calls" in loaded and len(loaded["calls"]) == 2


def test_session_directory_layout(tmp_path: Path) -> None:
    sess = SessionDirectory(root=tmp_path / "run1").ensure()
    assert (tmp_path / "run1").is_dir()
    assert sess.brief_path == tmp_path / "run1" / "brief.md"
    assert sess.state_path == tmp_path / "run1" / "state.json"
    sess.write_brief("hi")
    assert sess.brief_path.read_text() == "hi"
    phase_dir = sess.phase_dir("phase0")
    assert phase_dir.is_dir() and phase_dir.name == "phase0"
