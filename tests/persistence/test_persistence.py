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


def test_metrics_record_carries_search_breakdown_and_cache_split(tmp_path: Path) -> None:
    """Spec 0039 — ``CallRecord`` now carries the per-TTL cache split,
    a search count, and the search-cost breakdown so the recompute tool
    can recreate the full payload without re-walking the transcript."""
    m = Metrics()
    r = AgentResult(
        text="x",
        usage=TokenUsage(
            input_tokens=1000,
            output_tokens=200,
            cache_read_tokens=100,
            cache_write_tokens=300,
            cache_write_5m_tokens=100,
            cache_write_1h_tokens=200,
        ),
        cost_usd=0.234,
        duration_ms=1500,
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        label="claude",
        extras={"searches": 3},
    )
    m.record(label="phase4-r1-claude", result=r)
    rec = m.calls[0]
    assert rec.cache_write_5m_tokens == 100
    assert rec.cache_write_1h_tokens == 200
    # 3 Claude searches at $0.010 = $0.030
    assert rec.searches == 3
    assert rec.search_cost == pytest.approx(0.030)
    totals = m.totals_by_agent()["claude"]
    assert totals["cache_write_5m_tokens"] == 100
    assert totals["cache_write_1h_tokens"] == 200
    assert totals["searches"] == 3
    assert totals["search_cost"] == pytest.approx(0.030)
    assert m.total_search_cost_usd() == pytest.approx(0.030)


def test_metrics_load_or_new_returns_empty_when_missing(tmp_path: Path) -> None:
    """Spec 0039 D2 — ``load_or_new`` is the safe-on-resume entry point.

    Missing file → fresh ``Metrics``. Lets the orchestrator unconditionally
    call it on every session entry without special-casing the first run.
    """
    m = Metrics.load_or_new(tmp_path / "missing.json")
    assert m.calls == []
    assert m.total_cost_usd() == 0.0


def test_metrics_load_or_new_rehydrates_prior_calls(tmp_path: Path) -> None:
    """Spec 0039 D2 — resume preserves pre-resume cost record.

    The partner-vetting bug: ``metrics = Metrics()`` on every session
    entry, so the post-resume save() overwrote phase 0-3 with only
    phase 4. With ``load_or_new``, a new record appends onto the prior
    calls and the total reflects both windows.
    """
    path = tmp_path / "metrics.json"
    # Session 1: two pre-resume calls.
    pre = Metrics()
    pre.record(
        label="phase1-claude",
        result=AgentResult(
            text="", usage=TokenUsage(input_tokens=1000),
            cost_usd=0.50, duration_ms=100,
            model_id="claude-sonnet-4-6", provider="anthropic", label="claude",
        ),
    )
    pre.record(
        label="phase1-openai",
        result=AgentResult(
            text="", usage=TokenUsage(input_tokens=1000),
            cost_usd=0.25, duration_ms=100,
            model_id="gpt-5.5", provider="openai", label="openai",
        ),
    )
    pre.mark_done()
    pre.save(path)

    # Session 2 (resume): load_or_new rehydrates + a new call appends.
    resumed = Metrics.load_or_new(path)
    assert len(resumed.calls) == 2
    assert resumed.total_cost_usd() == pytest.approx(0.75)
    resumed.record(
        label="phase4-r1-claude",
        result=AgentResult(
            text="", usage=TokenUsage(input_tokens=2000),
            cost_usd=1.00, duration_ms=100,
            model_id="claude-sonnet-4-6", provider="anthropic", label="claude",
        ),
    )
    resumed.save(path)

    # Final state preserves all three calls.
    final = Metrics.load_or_new(path)
    assert len(final.calls) == 3
    assert final.total_cost_usd() == pytest.approx(1.75)


def test_metrics_load_or_new_tolerates_old_shape(tmp_path: Path) -> None:
    """Spec 0039 — older metrics.json files (pre-spec, no per-TTL split,
    no searches / search_cost fields) load cleanly with defaults applied."""
    path = tmp_path / "metrics.json"
    path.write_text(
        json.dumps({
            "started_at": "2026-05-15T10:00:00+00:00",
            "ended_at": "2026-05-15T11:00:00+00:00",
            "calls": [
                {
                    "label": "phase0-claude",
                    "agent": "claude",
                    "model_id": "claude-sonnet-4-6",
                    "input_tokens": 1000,
                    "output_tokens": 200,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 500,
                    "cost_usd": 0.42,
                    "duration_ms": 1500,
                    # No cache_write_5m_tokens / cache_write_1h_tokens.
                    # No searches / search_cost.
                },
            ],
            "total_cost_usd": 0.42,
        }),
        encoding="utf-8",
    )
    m = Metrics.load_or_new(path)
    assert len(m.calls) == 1
    rec = m.calls[0]
    assert rec.cache_write_tokens == 500
    assert rec.cache_write_5m_tokens == 0  # default
    assert rec.cache_write_1h_tokens == 0  # default
    assert rec.searches == 0
    assert rec.search_cost == 0.0


def test_metrics_load_or_new_tolerates_corrupt_json(tmp_path: Path) -> None:
    """Defensive: a corrupted metrics.json must not crash the
    orchestrator on resume. The transcript-primary aggregator path
    (D3) still produces correct UI numbers from the transcript."""
    path = tmp_path / "metrics.json"
    path.write_text("{not json", encoding="utf-8")
    m = Metrics.load_or_new(path)
    assert m.calls == []


def test_session_directory_layout(tmp_path: Path) -> None:
    sess = SessionDirectory(root=tmp_path / "run1").ensure()
    assert (tmp_path / "run1").is_dir()
    assert sess.brief_path == tmp_path / "run1" / "brief.md"
    assert sess.state_path == tmp_path / "run1" / "state.json"
    sess.write_brief("hi")
    assert sess.brief_path.read_text() == "hi"
    phase_dir = sess.phase_dir("phase0")
    assert phase_dir.is_dir() and phase_dir.name == "phase0"
