"""Tests for the agent/phase/status translation tables."""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.ui.labels import (
    BACKEND_TO_UI_AGENT,
    PHASE_MAP,
    backend_agent,
    derive_agent_status,
    derive_run_status,
    display_id,
    display_id_for,
    phase_to_int,
    ui_agent,
)


class TestAgentLabels:
    def test_claude_passes_through(self):
        assert ui_agent("claude") == "claude"
        assert backend_agent("claude") == "claude"

    def test_openai_becomes_gpt(self):
        assert ui_agent("openai") == "gpt"
        assert backend_agent("gpt") == "openai"

    def test_unknown_passes_through(self):
        # Defensive: if a new backend agent appears, we don't drop events.
        assert ui_agent("future-agent") == "future-agent"

    def test_table_is_total(self):
        # Every backend label maps to exactly one UI label and vice versa.
        for be, ui in BACKEND_TO_UI_AGENT.items():
            assert backend_agent(ui) == be


class TestPhaseMap:
    @pytest.mark.parametrize(
        "phase_str,expected",
        [
            ("phase0", 0),
            ("phase1", 1),
            ("phase2", 2),
            ("phase3", 3),
            ("phase4", 4),
            ("done", 5),
        ],
    )
    def test_known_phases(self, phase_str, expected):
        assert phase_to_int(phase_str) == expected
        assert PHASE_MAP[phase_str] == expected

    def test_unknown_falls_back_to_zero(self):
        assert phase_to_int("garbage") == 0


class TestDisplayId:
    def test_deterministic(self):
        # Same input always produces the same display id.
        a = display_id("20260515-124552-cache-multi-round")
        b = display_id("20260515-124552-cache-multi-round")
        assert a == b
        assert len(a) == 4

    def test_different_inputs_different_ids(self):
        assert display_id("foo") != display_id("bar")

    def test_from_path(self):
        p = Path("/some/runs/20260515-124552-cache-multi-round")
        assert display_id_for(p) == display_id(p.name)


class TestDeriveAgentStatus:
    @pytest.mark.parametrize(
        "phase,active,drafter,expected",
        [
            ("phase0", True, False, "thinking"),
            ("phase1", True, False, "drafting"),
            ("phase2", True, False, "responding"),
            ("phase3", True, True, "drafting"),
            ("phase3", True, False, "idle"),
            ("phase4", True, True, "drafting"),
            ("phase4", True, False, "reviewing"),
            ("phase2", False, False, "waiting"),
            ("phase1", False, False, "waiting"),
            ("done", False, False, "idle"),
            ("done", True, True, "idle"),
        ],
    )
    def test_truth_table(self, phase, active, drafter, expected):
        got = derive_agent_status(
            phase=phase, agent_active=active, is_drafter=drafter
        )
        assert got == expected

    def test_phase_done_flag_forces_idle(self):
        # Even if "active" arguments suggest otherwise, phase_done overrides.
        assert derive_agent_status(
            phase="phase2", agent_active=True, is_drafter=False, phase_done=True
        ) == "idle"


class TestDeriveRunStatus:
    def test_running_default(self):
        assert (
            derive_run_status(
                state_phase="phase2",
                final_emitted=False,
                hard_cap_hit=False,
                run_failed=False,
            )
            == "running"
        )

    def test_completed(self):
        assert (
            derive_run_status(
                state_phase="done",
                final_emitted=True,
                hard_cap_hit=False,
                run_failed=False,
            )
            == "completed"
        )

    def test_deadlocked_takes_precedence_over_running(self):
        assert (
            derive_run_status(
                state_phase="phase2",
                final_emitted=False,
                hard_cap_hit=True,
                run_failed=False,
            )
            == "deadlocked"
        )

    def test_errored_trumps_all(self):
        assert (
            derive_run_status(
                state_phase="done",
                final_emitted=True,
                hard_cap_hit=True,
                run_failed=True,
            )
            == "errored"
        )
