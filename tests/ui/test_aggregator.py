"""Tests for the run aggregator end-to-end.

Golden tests use the checked-in fixture session directories under ``runs/``.
Synthetic tests build their own transcripts in ``tmp_path``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import pytest

from dual_research.ui import (
    apply_event,
    load_run_snapshot,
    summarize_run,
)
from dual_research.ui.models import Run

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "runs"
FIXTURE_CACHE_RUN = FIXTURE_ROOT / "20260515-124552-cache-multi-round"

# Fixture runs/ is gitignored — skip golden tests if absent. Synthetic tests
# below still run.
requires_fixture = pytest.mark.skipif(
    not FIXTURE_CACHE_RUN.exists(),
    reason="cache-multi-round fixture run not present",
)


# ─── load_run_snapshot — golden tests against fixture runs ───────────────────


@requires_fixture
class TestLoadCompletedRun:
    def test_top_level_shape(self):
        r = load_run_snapshot(FIXTURE_CACHE_RUN)
        assert r.id == FIXTURE_CACHE_RUN.name
        assert len(r.display_id) == 4
        assert r.status == "completed"
        assert r.phase == 5
        assert r.drafter in ("claude", "gpt")
        assert r.topic
        # The brief.md H1 is "Should a startup use TypeScript or JavaScript...".
        assert "TypeScript" in r.topic or "JavaScript" in r.topic

    def test_phase_timings_populated(self):
        r = load_run_snapshot(FIXTURE_CACHE_RUN)
        for phase_int in (0, 1, 2, 3, 4):
            assert r.phase_timings[phase_int] is not None
            assert r.phase_timings[phase_int] > 0

    def test_agent_token_costs(self):
        r = load_run_snapshot(FIXTURE_CACHE_RUN)
        # Both agents should have non-zero usage.
        for ag_name in ("claude", "gpt"):
            ag = r.agents[ag_name]
            assert ag.tokens.in_ > 0
            assert ag.tokens.out > 0
            assert ag.cost > 0
            assert ag.status == "idle"
        # model_id was set from RunStarted.
        assert r.agents["claude"].model_id == "claude-haiku-4-5"
        assert r.agents["gpt"].model_id == "gpt-5-mini"

    def test_disagreements_present(self):
        r = load_run_snapshot(FIXTURE_CACHE_RUN)
        assert len(r.disagreements) >= 6
        # All should be marked resolved (the run completed cleanly).
        for d in r.disagreements:
            assert d.status.startswith("resolved-")

    def test_drafter_translated_from_state_json(self):
        r = load_run_snapshot(FIXTURE_CACHE_RUN)
        # state.json says drafter="openai" → UI sees "gpt".
        assert r.drafter == "gpt"

    def test_round_caps_set(self):
        r = load_run_snapshot(FIXTURE_CACHE_RUN)
        # Caps come from the LATEST run_started in the transcript (resume case
        # can append a second run_started). Either way both should be sane.
        assert r.round.soft >= 1
        assert r.round.hard >= r.round.soft

    def test_phase_stats_populated(self):
        # Spec 0013: load_run_snapshot must surface phase_stats so the UI
        # timeline cards can render inline chips.
        r = load_run_snapshot(FIXTURE_CACHE_RUN)
        # Phase 0 preflight present for both agents.
        assert "claude" in r.phase_stats.phase0
        assert "gpt" in r.phase_stats.phase0
        # Phase 2 has all five rounds parsed.
        assert sorted(r.phase_stats.phase2.keys()) == [1, 2, 3, 4, 5]
        # Phase 2 round 1 was NEGOTIATING for both agents.
        assert r.phase_stats.phase2[1]["claude"].status == "NEGOTIATING"
        # Phase 4 final round was APPROVED for both agents.
        last_p4 = max(r.phase_stats.phase4.keys())
        assert r.phase_stats.phase4[last_p4]["claude"].status == "APPROVED"
        assert r.phase_stats.phase4[last_p4]["gpt"].status == "APPROVED"


@requires_fixture
class TestSummarizeRun:
    def test_completed_row(self):
        row = summarize_run(FIXTURE_CACHE_RUN)
        assert row.id == FIXTURE_CACHE_RUN.name
        assert row.status == "completed"
        assert row.phase == 5
        assert row.topic
        assert row.duration > 0
        # Phase 5 row: no rounds string.
        assert row.rounds is None

    def test_does_not_require_full_replay(self):
        # summarize_run should work even for runs with no disagreement parsing.
        row = summarize_run(FIXTURE_CACHE_RUN)
        assert isinstance(row.cost, float)


# ─── apply_event — synthetic incremental updates ─────────────────────────────


def _empty_run() -> Run:
    return Run(id="r-1", display_id="abcd")


class TestApplyEvent:
    def test_run_started_sets_caps_and_models(self, tmp_path):
        run = _empty_run()
        apply_event(
            run,
            {
                "event": "run_started",
                "soft_cap": 4,
                "hard_cap": 8,
                "claude_model": "claude-sonnet-4-6",
                "openai_model": "gpt-5.5",
            },
            tmp_path,
        )
        assert run.round.soft == 4
        assert run.round.hard == 8
        assert run.agents["claude"].model_id == "claude-sonnet-4-6"
        assert run.agents["gpt"].model_id == "gpt-5.5"
        assert run.status == "running"

    def test_phase_entered_translates_string(self, tmp_path):
        run = _empty_run()
        apply_event(run, {"event": "phase_entered", "phase": "phase3"}, tmp_path)
        assert run.phase == 3

    def test_phase_exited_records_timing(self, tmp_path):
        run = _empty_run()
        apply_event(
            run,
            {"event": "phase_exited", "phase": "phase2", "duration_ms": 358_000},
            tmp_path,
        )
        assert run.phase_timings[2] == 358

    def test_turn_started_sets_active_status(self, tmp_path):
        run = _empty_run()
        apply_event(
            run,
            {
                "event": "turn_started",
                "agent": "openai",
                "phase": "phase2",
                "label": "phase2-openai-round-1",
            },
            tmp_path,
        )
        # openai is "gpt" in UI vocabulary.
        assert run.agents["gpt"].status == "responding"
        # claude is not active → waiting.
        assert run.agents["claude"].status == "waiting"

    def test_turn_ended_accumulates_tokens_and_cost(self, tmp_path):
        run = _empty_run()
        apply_event(
            run,
            {
                "event": "turn_ended",
                "agent": "claude",
                "phase": "phase1",
                "label": "phase1-claude",
                "input_tokens": 100,
                "output_tokens": 200,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "cost_usd": 0.05,
                "duration_ms": 1000,
                "finish_reason": "end_turn",
                "model_id": "claude-haiku-4-5",
            },
            tmp_path,
        )
        # Second turn should accumulate.
        apply_event(
            run,
            {
                "event": "turn_ended",
                "agent": "claude",
                "phase": "phase2",
                "label": "phase2-claude-round-1",
                "input_tokens": 50,
                "output_tokens": 80,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "cost_usd": 0.03,
                "duration_ms": 800,
                "finish_reason": "end_turn",
                "model_id": "claude-haiku-4-5",
            },
            tmp_path,
        )
        assert run.agents["claude"].tokens.in_ == 150
        assert run.agents["claude"].tokens.out == 280
        assert run.agents["claude"].cost == pytest.approx(0.08)

    def test_phase2_complete_translates_drafter(self, tmp_path):
        run = _empty_run()
        apply_event(
            run,
            {
                "event": "phase2_complete",
                "rounds": 3,
                "converged": True,
                "drafter": "openai",
                "fsd_count": 0,
                "via_tiebreak": False,
            },
            tmp_path,
        )
        assert run.drafter == "gpt"

    def test_run_failed_sets_errored_status(self, tmp_path):
        run = _empty_run()
        apply_event(
            run,
            {
                "event": "run_failed",
                "ts": "2026-05-15T12:00:00+00:00",
                "phase_reached": "phase2",
                "error_type": "ValueError",
                "message": "boom",
            },
            tmp_path,
        )
        assert run.status == "errored"
        assert run.error is not None
        assert run.error.code == "ValueError"
        assert "boom" in run.error.detail
        # Agents should be idle.
        assert run.agents["claude"].status == "idle"
        assert run.agents["gpt"].status == "idle"

    def test_run_completed_exit_codes(self, tmp_path):
        for exit_code, expected_status in [
            (0, "completed"),
            (51, "deadlocked"),
            (1, "errored"),
            (2, "errored"),
            (52, "errored"),
        ]:
            run = _empty_run()
            apply_event(
                run,
                {
                    "event": "run_completed",
                    "phase_reached": "phase4",
                    "exit_code": exit_code,
                    "total_cost_usd": 1.0,
                    "duration_ms": 1000,
                },
                tmp_path,
            )
            assert run.status == expected_status, (
                f"exit_code={exit_code} expected {expected_status}, got {run.status}"
            )

    def test_unknown_event_is_ignored(self, tmp_path):
        run = _empty_run()
        # Future event types should be silently ignored.
        apply_event(run, {"event": "some_future_event", "foo": "bar"}, tmp_path)
        # No mutation observable.
        assert run.status == "running"
        assert run.phase == 0


# ─── Synthetic full session ──────────────────────────────────────────────────


def _write_session_skeleton(tmp_path: Path) -> Path:
    """Create a minimal session directory with brief.md and an empty transcript."""
    session = tmp_path / "20260515-130000-mini"
    session.mkdir()
    (session / "brief.md").write_text("# Mini topic\n\nbody\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps(
            {
                "phase": "phase2",
                "drafter": None,
                "agreed_plan": None,
                "final_surfaced_disagreements": [],
                "draft_round": 1,
                "final_emitted_to": None,
            }
        ),
        encoding="utf-8",
    )
    (session / "metrics.json").write_text(
        json.dumps({"total_cost_usd": 0.42}), encoding="utf-8"
    )
    return session


def _append_event(session: Path, **kwargs) -> None:
    line = json.dumps({"ts": datetime.now(timezone.utc).isoformat(), **kwargs})
    with (session / "transcript.jsonl").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


class TestLoadSyntheticSession:
    def test_brief_topic_extraction(self, tmp_path):
        session = _write_session_skeleton(tmp_path)
        _append_event(
            session,
            event="run_started",
            session_dir=str(session),
            slug="mini",
            model_tier="test",
            claude_model="claude-haiku-4-5",
            openai_model="gpt-5-mini",
            soft_cap=3,
            hard_cap=5,
        )
        r = load_run_snapshot(session)
        assert r.topic == "Mini topic"
        assert r.display_id == r.display_id  # stable
        assert r.agents["claude"].model_id == "claude-haiku-4-5"
        assert r.round.soft == 3 and r.round.hard == 5

    def test_status_derives_from_state_done(self, tmp_path):
        session = _write_session_skeleton(tmp_path)
        # Flip state.json to "done" with final emitted.
        (session / "state.json").write_text(
            json.dumps(
                {
                    "phase": "done",
                    "drafter": "claude",
                    "agreed_plan": "x",
                    "final_surfaced_disagreements": [],
                    "draft_round": 1,
                    "final_emitted_to": "/tmp/x",
                }
            ),
            encoding="utf-8",
        )
        _append_event(
            session,
            event="run_started",
            session_dir=str(session),
            slug="mini",
            model_tier="test",
            claude_model="m1",
            openai_model="m2",
            soft_cap=3,
            hard_cap=5,
        )
        r = load_run_snapshot(session)
        assert r.status == "completed"
        assert r.phase == 5
        assert r.drafter == "claude"

    def test_summarize_synthetic(self, tmp_path):
        session = _write_session_skeleton(tmp_path)
        row = summarize_run(session)
        assert row.id == session.name
        assert row.phase == 2  # state.json says phase2
        assert row.topic == "Mini topic"
        assert row.cost == 0.42
        # Phase 2 row has rounds string.
        assert row.rounds is not None
