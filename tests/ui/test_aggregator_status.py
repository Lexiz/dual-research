"""Spec 0136 — unified run-status derivation tests.

Both ``summarize_run`` (All-Runs list) and ``load_run_snapshot`` (run-detail
page) must agree on ``Run.status`` for the same transcript + state. These
tests exercise the canonical truth table directly and the on-disk
DVS-backend regression that motivated the spec.
"""

from __future__ import annotations

import json
from pathlib import Path

from dual_research.ui.aggregator import load_run_snapshot, summarize_run
from dual_research.ui.labels import derive_run_status


def _write_transcript(session_dir: Path, events: list[dict]) -> None:
    (session_dir / "transcript.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n",
        encoding="utf-8",
    )


def _write_state(session_dir: Path, **kwargs) -> None:
    payload = {
        "phase": "phase0",
        "drafter": None,
        "agreed_plan": None,
        "final_surfaced_disagreements": [],
        "draft_round": 1,
        "final_emitted_to": None,
        "agreed_interpretation": None,
        "carry_forward_phase0": [],
        "carry_forward_phase2": [],
        "carry_forward_phase4": [],
        "closeout_budgets": {},
        **kwargs,
    }
    (session_dir / "state.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_brief(session_dir: Path, topic: str = "Test brief") -> None:
    (session_dir / "brief.md").write_text(f"# {topic}\n", encoding="utf-8")


def _scenario(tmp_path: Path, *, transcript_events: list[dict], state_kwargs: dict) -> Path:
    session_dir = tmp_path / "test-run"
    session_dir.mkdir()
    _write_brief(session_dir)
    _write_transcript(session_dir, transcript_events)
    _write_state(session_dir, **state_kwargs)
    return session_dir


def _both_paths_agree(session_dir: Path, expected: str) -> None:
    """Assert ``summarize_run`` and ``load_run_snapshot`` both report the
    same status. The whole spec exists to make these two paths agree."""
    list_row = summarize_run(session_dir)
    detail = load_run_snapshot(session_dir)
    assert list_row.status == expected, (
        f"All-Runs list says {list_row.status!r}, expected {expected!r}"
    )
    assert detail.status == expected, (
        f"Run-detail page says {detail.status!r}, expected {expected!r}"
    )


# ─── derive_run_status truth-table (pure) ─────────────────────────────────────


class TestDeriveRunStatusTruthTable:
    """Direct tests on the pure helper. Same precedence the integration
    tests below verify against the aggregator paths."""

    def test_run_failed_beats_everything(self):
        assert derive_run_status(
            state_phase="done",
            final_emitted=True,
            hard_cap_hit=True,
            run_failed=True,
            run_completed_exit_code=0,
        ) == "errored"

    def test_exit_code_runtime_or_parse_failure_is_errored(self):
        for code in (2, 52):
            assert derive_run_status(
                state_phase="phase2",
                final_emitted=False,
                hard_cap_hit=False,
                run_failed=False,
                run_completed_exit_code=code,
            ) == "errored"

    def test_unknown_nonzero_exit_code_is_errored(self):
        # Spec 0136 follow-up — any non-zero exit code that isn't the
        # hard-cap signal (51) maps to errored. Catches exit 1 from a
        # Python uncaught exception, exit 137 from a SIGKILL, etc.
        for code in (1, 3, 137, 143):
            assert derive_run_status(
                state_phase="phase2",
                final_emitted=False,
                hard_cap_hit=False,
                run_failed=False,
                run_completed_exit_code=code,
            ) == "errored"

    def test_hard_cap_hit_marks_deadlocked(self):
        assert derive_run_status(
            state_phase="phase2",
            final_emitted=False,
            hard_cap_hit=True,
            run_failed=False,
            run_completed_exit_code=51,
        ) == "deadlocked"

    def test_exit_code_hard_cap_marks_deadlocked_even_without_event(self):
        assert derive_run_status(
            state_phase="phase2",
            final_emitted=False,
            hard_cap_hit=False,
            run_failed=False,
            run_completed_exit_code=51,
        ) == "deadlocked"

    def test_done_state_marks_completed(self):
        assert derive_run_status(
            state_phase="done",
            final_emitted=True,
            hard_cap_hit=False,
            run_failed=False,
            run_completed_exit_code=0,
        ) == "completed"

    def test_silent_exit_defence_branch(self):
        # The DVS-backend regression: orchestrator exited cleanly
        # (exit_code 0) but the run never reached "done" — neither
        # final_emitted nor state.phase advanced. Truth-table branch #5
        # routes this to "deadlocked" so the UI doesn't lie about it.
        assert derive_run_status(
            state_phase="phase2",
            final_emitted=False,
            hard_cap_hit=False,
            run_failed=False,
            run_completed_exit_code=0,
        ) == "deadlocked"

    def test_in_flight_no_terminal(self):
        assert derive_run_status(
            state_phase="phase2",
            final_emitted=False,
            hard_cap_hit=False,
            run_failed=False,
            run_completed_exit_code=None,
        ) == "running"


# ─── Integration: both paths agree on the same on-disk transcript ─────────────


class TestPathsAgree:
    """Build a session directory, then assert ``summarize_run`` and
    ``load_run_snapshot`` produce the same ``Run.status``. Pre-spec
    these two paths used different rules and occasionally disagreed."""

    def test_healthy_completion(self, tmp_path):
        events = [
            {"ts": "t1", "event": "run_started", "session_dir": "x", "slug": "x",
             "model_tier": "test", "claude_model": "c", "openai_model": "o",
             "soft_cap": 6, "hard_cap": 8},
            {"ts": "t2", "event": "phase_entered", "phase": "phase4"},
            {"ts": "t3", "event": "final_emitted", "session_final_path": "final.md",
             "out_path": "out.md", "char_count": 1234, "confidence": "HIGH"},
            {"ts": "t4", "event": "run_completed", "phase_reached": "done",
             "exit_code": 0, "total_cost_usd": 1.0, "duration_ms": 1000},
        ]
        session_dir = _scenario(
            tmp_path,
            transcript_events=events,
            state_kwargs={"phase": "done", "final_emitted_to": "out.md"},
        )
        _both_paths_agree(session_dir, "completed")

    def test_hard_cap_deadlock(self, tmp_path):
        events = [
            {"ts": "t1", "event": "run_started", "session_dir": "x", "slug": "x",
             "model_tier": "test", "claude_model": "c", "openai_model": "o",
             "soft_cap": 6, "hard_cap": 8},
            {"ts": "t2", "event": "phase_entered", "phase": "phase2"},
            {"ts": "t3", "event": "hard_cap_hit", "phase": "phase2", "round": 8, "cap": 8},
            {"ts": "t4", "event": "run_completed", "phase_reached": "phase2",
             "exit_code": 51, "total_cost_usd": 1.0, "duration_ms": 1000},
        ]
        session_dir = _scenario(
            tmp_path,
            transcript_events=events,
            state_kwargs={"phase": "phase2"},
        )
        _both_paths_agree(session_dir, "deadlocked")

    def test_silent_exit_deadlock_regression(self, tmp_path):
        # The DVS-backend transcript shape: run_completed{exit_code: 0}
        # without any hard_cap_hit, state.phase == "phase2",
        # final_emitted_to == null. Pre-spec the list said "running"
        # and the detail page said "completed". Post-spec both say
        # "deadlocked" (silent-exit defence branch).
        events = [
            {"ts": "t1", "event": "run_started", "session_dir": "x", "slug": "x",
             "model_tier": "prod", "claude_model": "c", "openai_model": "o",
             "soft_cap": 6, "hard_cap": 8},
            {"ts": "t2", "event": "phase_entered", "phase": "phase2"},
            {"ts": "t3", "event": "phase_exited", "phase": "phase2", "duration_ms": 1000},
            {"ts": "t4", "event": "phase2_complete", "rounds": 8, "converged": False,
             "drafter": None, "fsd_count": 0},
            {"ts": "t5", "event": "run_completed", "phase_reached": "phase2",
             "exit_code": 0, "total_cost_usd": 5.47, "duration_ms": 2362017},
        ]
        session_dir = _scenario(
            tmp_path,
            transcript_events=events,
            state_kwargs={"phase": "phase2"},
        )
        _both_paths_agree(session_dir, "deadlocked")

    def test_runtime_error(self, tmp_path):
        events = [
            {"ts": "t1", "event": "run_started", "session_dir": "x", "slug": "x",
             "model_tier": "test", "claude_model": "c", "openai_model": "o",
             "soft_cap": 6, "hard_cap": 8},
            {"ts": "t2", "event": "phase_entered", "phase": "phase2"},
            {"ts": "t3", "event": "run_failed", "phase_reached": "phase2",
             "error_type": "ValueError", "message": "boom"},
        ]
        session_dir = _scenario(
            tmp_path,
            transcript_events=events,
            state_kwargs={"phase": "phase2"},
        )
        _both_paths_agree(session_dir, "errored")

    def test_parse_failure_exit(self, tmp_path):
        events = [
            {"ts": "t1", "event": "run_started", "session_dir": "x", "slug": "x",
             "model_tier": "test", "claude_model": "c", "openai_model": "o",
             "soft_cap": 6, "hard_cap": 8},
            {"ts": "t2", "event": "phase_entered", "phase": "phase4"},
            {"ts": "t3", "event": "run_completed", "phase_reached": "phase4",
             "exit_code": 52, "total_cost_usd": 1.0, "duration_ms": 1000},
        ]
        session_dir = _scenario(
            tmp_path,
            transcript_events=events,
            state_kwargs={"phase": "phase4"},
        )
        _both_paths_agree(session_dir, "errored")

    def test_in_flight_running(self, tmp_path):
        events = [
            {"ts": "t1", "event": "run_started", "session_dir": "x", "slug": "x",
             "model_tier": "test", "claude_model": "c", "openai_model": "o",
             "soft_cap": 6, "hard_cap": 8},
            {"ts": "t2", "event": "phase_entered", "phase": "phase2"},
        ]
        session_dir = _scenario(
            tmp_path,
            transcript_events=events,
            state_kwargs={"phase": "phase2"},
        )
        _both_paths_agree(session_dir, "running")


# ─── DVS-backend on-disk regression ───────────────────────────────────────────


_FIXTURE_DVS = Path(__file__).resolve().parents[2] / "runs" / "20260520-170146-dvs-backend-language-choice"


class TestSupabaseListStatusHelper:
    """Spec 0136 follow-up — the Supabase ``_status_from_columns`` helper
    fed pushed-run columns into ``derive_run_status``. Pre-fix it
    flattened exit_code into derived ``run_failed`` / ``hard_cap_hit``
    booleans before the truth table saw it, which discarded the
    ``exit_code == 0`` + not-done signal and left the All-Runs list
    reading ``running`` forever on the hosted surface (exactly what the
    user surfaced after the v1.8.1 deploy)."""

    def _status(self, *, phase_reached: str, exit_code, state):
        # Import the private helper directly — it's not part of the
        # public surface but it's the choke-point the bug lived in.
        from dual_research.ui.server import _status_from_columns
        return _status_from_columns(
            phase_reached=phase_reached, exit_code=exit_code, state=state,
        )

    def test_silent_exit_deadlock_on_hosted_pattern(self):
        # The DVS-backend / LLM-vs-human-grading row shape on the
        # hosted ``runs`` table: phase_reached='phase2', exit_code=0,
        # state.final_emitted_to=null. Pre-fix returned 'running';
        # post-fix returns 'deadlocked' via the silent-exit branch.
        assert self._status(
            phase_reached="phase2", exit_code=0, state={"final_emitted_to": None},
        ) == "deadlocked"

    def test_healthy_completion_on_hosted_pattern(self):
        assert self._status(
            phase_reached="done", exit_code=0,
            state={"final_emitted_to": "out.md"},
        ) == "completed"

    def test_hard_cap_on_hosted_pattern(self):
        assert self._status(
            phase_reached="phase2", exit_code=51, state={"final_emitted_to": None},
        ) == "deadlocked"

    def test_runtime_error_on_hosted_pattern(self):
        for code in (1, 2, 52, 137):
            assert self._status(
                phase_reached="phase2", exit_code=code, state={"final_emitted_to": None},
            ) == "errored", f"exit_code={code}"

    def test_in_flight_pushed_run(self):
        # Push-while-running emits intermediate rows with exit_code=None
        # until the orchestrator finishes. Should read as running.
        assert self._status(
            phase_reached="phase2", exit_code=None, state={"final_emitted_to": None},
        ) == "running"


def test_dvs_backend_run_resolves_to_deadlocked():
    """The on-disk run that motivated the spec. Asserts both paths agree
    on "deadlocked" once the unified truth table replaces the divergent
    derivers. Skipped if the fixture isn't present (CI does not ship
    historical hosted-run data)."""
    if not _FIXTURE_DVS.exists():
        return
    list_row = summarize_run(_FIXTURE_DVS)
    detail = load_run_snapshot(_FIXTURE_DVS)
    assert list_row.status == "deadlocked", (
        f"All-Runs list says {list_row.status!r}, expected 'deadlocked'"
    )
    assert detail.status == "deadlocked", (
        f"Run-detail page says {detail.status!r}, expected 'deadlocked'"
    )
