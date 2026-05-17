"""Spec 0043 — LedgerEntry / LedgerState model tests."""

from __future__ import annotations

from dual_research.ledger.models import (
    CLAIM_STATUSES,
    DISAGREEMENT_STATUSES,
    ISSUE_STATUSES,
    QUESTION_STATUSES,
    LedgerDrift,
    LedgerEntry,
    LedgerState,
    LedgerStatusTransition,
)


def test_status_enums_exposed_as_tuples() -> None:
    assert "open" in QUESTION_STATUSES
    assert "answered" in QUESTION_STATUSES
    assert "open" in DISAGREEMENT_STATUSES
    assert "final_surfaced" in DISAGREEMENT_STATUSES
    assert "open" in CLAIM_STATUSES
    assert "escalated" in CLAIM_STATUSES
    assert "fixed" in ISSUE_STATUSES


def test_entry_is_open_only_for_open_status() -> None:
    entry = LedgerEntry(
        id="Q-c-r1-01", kind="question", raised_round=1,
        raised_by="claude", raised_turn_key="phase2_round1_claude",
        current_status="open",
    )
    assert entry.is_open() is True
    entry.current_status = "answered"
    assert entry.is_open() is False


def test_state_open_count_filters_by_kind() -> None:
    s = LedgerState(phase=2, entries=[
        LedgerEntry(id="Q-c-r1-01", kind="question", raised_round=1,
                    raised_by="claude", raised_turn_key="phase2_round1_claude",
                    current_status="open"),
        LedgerEntry(id="Q-g-r1-01", kind="question", raised_round=1,
                    raised_by="gpt", raised_turn_key="phase2_round1_gpt",
                    current_status="answered"),
        LedgerEntry(id="D-1", kind="disagreement", raised_round=2,
                    raised_by="claude", raised_turn_key="phase2_round2_claude",
                    current_status="open"),
    ])
    assert s.open_count() == 2
    assert s.open_count(kind="question") == 1
    assert s.open_count(kind="disagreement") == 1
    assert s.open_count(kind="issue") == 0


def test_state_find_by_id() -> None:
    s = LedgerState(phase=2, entries=[
        LedgerEntry(id="D-1", kind="disagreement", raised_round=2,
                    raised_by="claude", raised_turn_key="phase2_round2_claude",
                    current_status="open"),
    ])
    assert s.find_by_id("D-1") is not None
    assert s.find_by_id("D-99") is None


def test_drift_default_severity_is_warn() -> None:
    d = LedgerDrift(turn_key="phase2_round5_summary", kind="question",
                    agent_count=0, ledger_count=3)
    assert d.severity == "warn"


def test_transition_carries_turn_key_and_reason() -> None:
    t = LedgerStatusTransition(
        round=3, status="answered",
        reason="answered in phase2_round3_gpt", turn_key="phase2_round3_gpt",
    )
    assert t.round == 3
    assert t.turn_key == "phase2_round3_gpt"
