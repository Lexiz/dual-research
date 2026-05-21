"""Spec 0148 — aggregator threading of D10 (was_closeout), D11
(outputBreakdown), D12 (cacheSavingsUsd), and D03 (run.violations).

The aggregator is event-stream-driven: it consumes ``turn_ended``
events, extracts the new fields, and populates ``TurnTokenUsage``
plus the new ``Run.violations`` list. These tests replay synthetic
events through ``apply_event`` and assert the resulting state.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.ui.aggregator import apply_event, load_run_snapshot
from dual_research.ui.models import Run


def _make_run() -> Run:
    return Run(id="test-run", display_id="test")


def _turn_ended_event(
    *,
    label: str,
    phase: str = "phase0",
    agent: str = "claude",
    input_tokens: int = 1000,
    output_tokens: int = 500,
    cache_read_tokens: int = 0,
    reasoning_tokens: int = 0,
    model_id: str = "claude-sonnet-4-6",
    prompt_pieces: dict | None = None,
    searches: int = 0,
) -> dict:
    return {
        "event": "turn_ended",
        "ts": "2026-05-22T00:00:00Z",
        "agent": agent,
        "phase": phase,
        "label": label,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": 0,
        "cache_write_5m_tokens": 0,
        "cache_write_1h_tokens": 0,
        "cost_usd": 0.01,
        "search_cost": 0.0,
        "duration_ms": 1000,
        "finish_reason": "stop",
        "model_id": model_id,
        "prompt_pieces": prompt_pieces or {},
        "searches": searches,
        "reasoning_tokens": reasoning_tokens,
    }


def test_was_closeout_true_when_closeout_request_in_prompt_pieces(tmp_path: Path) -> None:
    run = _make_run()
    apply_event(
        run,
        _turn_ended_event(
            label="phase0-claude-r2",
            phase="phase0",
            agent="claude",
            prompt_pieces={"system.task.input": 500, "closeout.request": 120},
        ),
        tmp_path,
    )
    usage = run.phase_token_usage.get("phase0_round2_claude")
    assert usage is not None, list(run.phase_token_usage.keys())
    assert usage.was_closeout is True


def test_was_closeout_false_when_closeout_request_absent(tmp_path: Path) -> None:
    run = _make_run()
    apply_event(
        run,
        _turn_ended_event(
            label="phase0-claude-r1",
            prompt_pieces={"system.task.input": 500},
        ),
        tmp_path,
    )
    usage = run.phase_token_usage.get("phase0_round1_claude")
    assert usage is not None
    assert usage.was_closeout is False


def test_was_closeout_false_when_closeout_request_zero(tmp_path: Path) -> None:
    # Defensive: explicit 0 token count still reads as "no closeout".
    run = _make_run()
    apply_event(
        run,
        _turn_ended_event(
            label="phase0-claude-r1",
            prompt_pieces={"closeout.request": 0},
        ),
        tmp_path,
    )
    usage = run.phase_token_usage.get("phase0_round1_claude")
    assert usage is not None
    assert usage.was_closeout is False


def test_output_breakdown_with_reasoning(tmp_path: Path) -> None:
    run = _make_run()
    apply_event(
        run,
        _turn_ended_event(
            label="phase4-openai-r1",
            phase="phase4",
            agent="openai",
            output_tokens=1000,
            reasoning_tokens=300,
            model_id="gpt-5.5",
        ),
        tmp_path,
    )
    usage = run.phase_token_usage.get("phase4_round1_gpt")
    assert usage is not None
    assert usage.output_breakdown == {
        "reasoning": 300,
        "response": 700,
        "tool_calls": 0,
    }


def test_output_breakdown_no_reasoning(tmp_path: Path) -> None:
    run = _make_run()
    apply_event(
        run,
        _turn_ended_event(
            label="phase0-claude-r1",
            output_tokens=600,
            reasoning_tokens=0,
        ),
        tmp_path,
    )
    usage = run.phase_token_usage.get("phase0_round1_claude")
    assert usage is not None
    assert usage.output_breakdown == {
        "reasoning": 0,
        "response": 600,
        "tool_calls": 0,
    }


def test_output_breakdown_underflow_clamps_response(tmp_path: Path) -> None:
    # Defensive: if a provider reports reasoning > output, response
    # clamps at 0 (warn-log emits at runtime).
    run = _make_run()
    apply_event(
        run,
        _turn_ended_event(
            label="phase0-claude-r1",
            output_tokens=100,
            reasoning_tokens=200,
        ),
        tmp_path,
    )
    usage = run.phase_token_usage.get("phase0_round1_claude")
    assert usage is not None
    assert usage.output_breakdown["response"] == 0
    assert usage.output_breakdown["reasoning"] == 200


def test_cache_savings_usd_populates_for_cache_engaged_turn(tmp_path: Path) -> None:
    run = _make_run()
    apply_event(
        run,
        _turn_ended_event(
            label="phase0-claude-r1",
            cache_read_tokens=100_000,
            model_id="claude-sonnet-4-6",
        ),
        tmp_path,
    )
    usage = run.phase_token_usage.get("phase0_round1_claude")
    assert usage is not None
    # claude-sonnet input 3.00, cache_read 0.30 → delta 2.70 / Mtok.
    # 100_000 × 2.70 / 1_000_000 = 0.27.
    assert usage.cache_savings_usd == pytest.approx(0.27, abs=1e-6)


def test_cache_savings_usd_zero_for_non_cached_turn(tmp_path: Path) -> None:
    run = _make_run()
    apply_event(
        run,
        _turn_ended_event(
            label="phase0-claude-r1",
            cache_read_tokens=0,
        ),
        tmp_path,
    )
    usage = run.phase_token_usage.get("phase0_round1_claude")
    assert usage is not None
    assert usage.cache_savings_usd == 0.0


def test_load_run_snapshot_populates_violations(tmp_path: Path) -> None:
    # Synthesize a tiny session with two violation events in transcript.jsonl.
    session = tmp_path / "test-session"
    session.mkdir()
    transcript = session / "transcript.jsonl"
    lines = [
        '{"event":"protocol_violation","ts":"2026-05-22T00:00:00Z","phase":0,"round":2,"agent":"claude","violation_code":"terminal_state_re_address","item_id":"D-plan-g-01","from_state":"resolved"}',
        '{"event":"empty_turn_detected","ts":"2026-05-22T00:01:00Z","phase":2,"round":3,"agent":"openai","parser_block_count":0,"finish_reason":"stop","output_tokens":0}',
        '{"event":"turn_ended","ts":"2026-05-22T00:02:00Z","agent":"claude","phase":"phase0","label":"phase0-claude-r1","input_tokens":100,"output_tokens":50,"cache_read_tokens":0,"cache_write_tokens":0,"cost_usd":0.001,"duration_ms":500,"finish_reason":"stop","model_id":"claude-sonnet-4-6","prompt_pieces":{}}',
    ]
    transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")

    run = load_run_snapshot(session)
    assert len(run.violations) == 2
    kinds = sorted(v["event"] for v in run.violations)
    assert kinds == ["empty_turn_detected", "protocol_violation"]
    # Verbatim passthrough of the join keys.
    pv = next(v for v in run.violations if v["event"] == "protocol_violation")
    assert pv["phase"] == 0 and pv["round"] == 2 and pv["agent"] == "claude"


def test_load_run_snapshot_violations_empty_when_none_present(tmp_path: Path) -> None:
    session = tmp_path / "empty-session"
    session.mkdir()
    (session / "transcript.jsonl").write_text("", encoding="utf-8")
    run = load_run_snapshot(session)
    assert run.violations == []
