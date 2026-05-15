"""Tests for the transcript-event → UI ``RunError`` mapping."""

from __future__ import annotations

from dual_research.ui.errors import derive_errors


def _make_event(kind: str, **fields) -> dict:
    base = {"ts": "2026-05-15T13:00:00+00:00", "event": kind}
    base.update(fields)
    return base


class TestDeriveErrors:
    def test_empty_transcript(self):
        out = derive_errors(transcript=[], run_id="run-foo", display_id="abcd")
        assert out == []

    def test_repair_invoked_to_invalid_format(self):
        events = [
            _make_event(
                "repair_invoked",
                agent="claude",
                phase="phase2",
                round=3,
                errors=["missing STATUS"],
                budget_remaining=1,
            )
        ]
        errs = derive_errors(transcript=events, run_id="run-1", display_id="abcd")
        assert len(errs) == 1
        e = errs[0]
        assert e.code == "INVALID_TURN_FORMAT"
        assert e.severity == "error"
        assert e.resolved == "recovered"
        assert e.agent == "claude"
        assert e.phase == 2
        assert e.run_id == "abcd"
        assert "phase-2" in e.where and "round-3" in e.where and "claude" in e.where
        assert e.retried == 1  # budget_remaining
        assert "missing STATUS" in e.detail

    def test_openai_event_translates_to_gpt_in_error_agent(self):
        events = [
            _make_event(
                "repair_invoked",
                agent="openai",
                phase="phase4",
                round=2,
                errors=[],
                budget_remaining=0,
            )
        ]
        errs = derive_errors(transcript=events, run_id="r", display_id="0001")
        assert len(errs) == 1
        assert errs[0].agent == "gpt"
        assert "gpt" in errs[0].where

    def test_soft_cap_hit_maps_to_warning(self):
        events = [_make_event("soft_cap_hit", phase="phase2", round=6, cap=6)]
        errs = derive_errors(transcript=events, run_id="r", display_id="0001")
        assert len(errs) == 1
        assert errs[0].code == "SOFT_CAP_HIT"
        assert errs[0].severity == "warning"
        assert errs[0].resolved == "recovered"

    def test_hard_cap_hit_halts(self):
        events = [_make_event("hard_cap_hit", phase="phase2", round=12, cap=12)]
        errs = derive_errors(transcript=events, run_id="r", display_id="0001")
        assert len(errs) == 1
        assert errs[0].code == "HARD_CAP_HIT"
        assert errs[0].resolved == "halted"
        assert errs[0].severity == "warning"

    def test_run_failed_to_orchestrator_panic(self):
        events = [
            _make_event(
                "run_failed",
                phase_reached="phase3",
                error_type="ValueError",
                message="boom",
            )
        ]
        errs = derive_errors(transcript=events, run_id="r", display_id="0001")
        assert len(errs) == 1
        e = errs[0]
        assert e.code == "ORCHESTRATOR_PANIC"
        assert e.severity == "critical"
        assert e.resolved == "halted"
        assert "ValueError" in e.detail and "boom" in e.detail

    def test_unrelated_events_skipped(self):
        events = [
            _make_event("turn_started", agent="claude", phase="phase2"),
            _make_event("phase_entered", phase="phase2"),
            _make_event("cost_update", total_usd=0.5, by_agent={}),
        ]
        assert derive_errors(transcript=events, run_id="r", display_id="abcd") == []

    def test_sequence_ids_are_unique(self):
        events = [
            _make_event("repair_invoked", agent="claude", phase="phase2", round=1, errors=[], budget_remaining=1),
            _make_event("soft_cap_hit", phase="phase2", round=6, cap=6),
            _make_event("repair_invoked", agent="openai", phase="phase2", round=2, errors=[], budget_remaining=0),
        ]
        errs = derive_errors(transcript=events, run_id="r", display_id="abcd")
        ids = {e.id for e in errs}
        assert len(ids) == 3
        assert all(i.startswith("abcd-e") for i in ids)
