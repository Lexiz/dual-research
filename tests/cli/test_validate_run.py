"""Spec 0115 — validate-run CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.validate_cli import main, validate_session


def _write_transcript(session_dir: Path, events: list[dict]) -> None:
    transcript = session_dir / "transcript.jsonl"
    transcript.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _make_session(tmp_path: Path) -> Path:
    session_dir = tmp_path / "run-test"
    session_dir.mkdir()
    for phase in (0, 2, 4):
        (session_dir / f"phase{phase}").mkdir()
    return session_dir


def test_not_a_directory_returns_exit_2(tmp_path: Path, capsys):
    nonexistent = tmp_path / "nope"
    code = main([str(nonexistent)])
    assert code == 2


def test_directory_without_transcript_returns_exit_2(tmp_path: Path):
    bad = tmp_path / "bad"
    bad.mkdir()
    code = main([str(bad)])
    assert code == 2


def test_clean_run_returns_exit_0(tmp_path: Path):
    session_dir = _make_session(tmp_path)
    events = [
        {"kind": "item_raised", "id": "Q-plan-c-01", "item_kind": "question",
         "phase": 2, "round": 1, "raiser": "claude", "body": "what?",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"kind": "item_transitioned", "id": "Q-plan-c-01",
         "from_state": "open", "to_state": "addressed", "actor": "openai",
         "phase": 2, "round": 2, "reason": "answer", "via": None,
         "evidence_records": []},
        {"kind": "item_transitioned", "id": "Q-plan-c-01",
         "from_state": "addressed", "to_state": "resolved", "actor": "claude",
         "phase": 2, "round": 3, "reason": "satisfied with the answer", "via": None,
         "evidence_records": []},
        {"kind": "phase_converged", "phase": 2, "final_round": 3,
         "via_closeout": False, "via_ghost_cap": False, "via_hard_cap": False},
    ]
    _write_transcript(session_dir, events)
    report = validate_session(session_dir)
    assert report.has_errors is False
    assert any("phase 2 organically" in p for p in report.converged_phases)


def test_terminal_without_reason_is_error(tmp_path: Path):
    session_dir = _make_session(tmp_path)
    events = [
        {"kind": "item_raised", "id": "Q-plan-c-01", "item_kind": "question",
         "phase": 2, "round": 1, "raiser": "claude", "body": "x",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"kind": "item_transitioned", "id": "Q-plan-c-01",
         "from_state": "open", "to_state": "addressed", "actor": "openai",
         "phase": 2, "round": 2, "reason": "ok", "via": None,
         "evidence_records": []},
        # Resolved WITHOUT a reason (empty string).
        {"kind": "item_transitioned", "id": "Q-plan-c-01",
         "from_state": "addressed", "to_state": "resolved", "actor": "claude",
         "phase": 2, "round": 3, "reason": "", "via": None,
         "evidence_records": []},
    ]
    _write_transcript(session_dir, events)
    report = validate_session(session_dir)
    codes = {f.code for f in report.errors}
    assert "terminal_missing_reason" in codes


def test_capped_without_via_is_error(tmp_path: Path):
    session_dir = _make_session(tmp_path)
    events = [
        {"kind": "item_raised", "id": "D-plan-c-01", "item_kind": "disagreement",
         "phase": 2, "round": 1, "raiser": "claude", "body": "x",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        # Capped but no via — should error.
        {"kind": "item_transitioned", "id": "D-plan-c-01",
         "from_state": "open", "to_state": "capped", "actor": "orchestrator",
         "phase": 2, "round": 8, "reason": "hit cap", "via": None,
         "evidence_records": []},
    ]
    _write_transcript(session_dir, events)
    report = validate_session(session_dir)
    codes = {f.code for f in report.errors}
    assert "capped_missing_via" in codes


def test_evidence_required_resolved_without_evidence_is_error(tmp_path: Path):
    session_dir = _make_session(tmp_path)
    events = [
        {"kind": "item_raised", "id": "D-plan-c-01", "item_kind": "disagreement",
         "phase": 2, "round": 1, "raiser": "claude", "body": "x",
         "anchor_type": "none", "anchor_text": "", "evidence_required": True},
        {"kind": "item_transitioned", "id": "D-plan-c-01",
         "from_state": "open", "to_state": "addressed", "actor": "openai",
         "phase": 2, "round": 2, "reason": "ok", "via": None,
         "evidence_records": []},  # ← no evidence!
        {"kind": "item_transitioned", "id": "D-plan-c-01",
         "from_state": "addressed", "to_state": "resolved", "actor": "claude",
         "phase": 2, "round": 3, "reason": "accepted", "via": None,
         "evidence_records": []},
    ]
    _write_transcript(session_dir, events)
    report = validate_session(session_dir)
    codes = {f.code for f in report.errors}
    assert "evidence_missing_on_resolved" in codes


def test_non_terminal_item_is_warning_not_error(tmp_path: Path):
    session_dir = _make_session(tmp_path)
    events = [
        # Raised but never closed — interrupted run.
        {"kind": "item_raised", "id": "Q-plan-c-01", "item_kind": "question",
         "phase": 2, "round": 1, "raiser": "claude", "body": "x",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
    ]
    _write_transcript(session_dir, events)
    report = validate_session(session_dir)
    assert report.has_errors is False
    codes = {f.code for f in report.warnings}
    assert "item_non_terminal" in codes


def test_main_exit_1_on_errors(tmp_path: Path, capsys):
    session_dir = _make_session(tmp_path)
    events = [
        {"kind": "item_raised", "id": "D-plan-c-01", "item_kind": "disagreement",
         "phase": 2, "round": 1, "raiser": "claude", "body": "x",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"kind": "item_transitioned", "id": "D-plan-c-01",
         "from_state": "open", "to_state": "capped", "actor": "orchestrator",
         "phase": 2, "round": 8, "reason": "hit cap", "via": None,
         "evidence_records": []},
    ]
    _write_transcript(session_dir, events)
    code = main([str(session_dir)])
    assert code == 1
    captured = capsys.readouterr()
    assert "capped_missing_via" in captured.out


def test_main_json_format(tmp_path: Path, capsys):
    session_dir = _make_session(tmp_path)
    events = [
        {"kind": "item_raised", "id": "Q-plan-c-01", "item_kind": "question",
         "phase": 2, "round": 1, "raiser": "claude", "body": "x",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"kind": "item_transitioned", "id": "Q-plan-c-01",
         "from_state": "open", "to_state": "withdrawn", "actor": "claude",
         "phase": 2, "round": 2, "reason": "duplicate", "via": None,
         "evidence_records": []},
    ]
    _write_transcript(session_dir, events)
    code = main([str(session_dir), "--json"])
    assert code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["session_dir"] == str(session_dir.resolve())
    assert payload["errors"] == []
