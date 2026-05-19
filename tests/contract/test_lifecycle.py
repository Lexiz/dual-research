"""Spec 0114 — lifecycle transition tests."""

from __future__ import annotations

from dual_research.contract.lifecycle import (
    State,
    TERMINAL_STATES,
    is_terminal,
    is_valid_transition,
)


def test_terminal_states():
    assert State.RESOLVED in TERMINAL_STATES
    assert State.ACKNOWLEDGED in TERMINAL_STATES
    assert State.WITHDRAWN in TERMINAL_STATES
    assert State.CAPPED in TERMINAL_STATES
    assert State.OPEN not in TERMINAL_STATES
    assert State.ADDRESSED not in TERMINAL_STATES


def test_is_terminal_accepts_str():
    assert is_terminal("resolved") is True
    assert is_terminal("open") is False
    assert is_terminal("nonsense") is False


def test_open_to_addressed_by_addressee():
    assert is_valid_transition(State.OPEN, State.ADDRESSED, actor="addressee") is True
    # Raiser cannot drive the open → addressed transition
    assert is_valid_transition(State.OPEN, State.ADDRESSED, actor="raiser") is False


def test_open_to_withdrawn_by_raiser():
    assert is_valid_transition(State.OPEN, State.WITHDRAWN, actor="raiser") is True
    assert is_valid_transition(State.OPEN, State.WITHDRAWN, actor="addressee") is False


def test_addressed_to_resolved_by_raiser():
    assert is_valid_transition(State.ADDRESSED, State.RESOLVED, actor="raiser") is True
    assert is_valid_transition(State.ADDRESSED, State.RESOLVED, actor="addressee") is False


def test_addressed_to_open_counter_argument():
    """Raiser can flip an addressed item back to open via counter-arg."""
    assert is_valid_transition(State.ADDRESSED, State.OPEN, actor="raiser") is True


def test_addressed_to_acknowledged_mutual():
    """Either raiser or addressee can propose; mutual handshake required."""
    assert is_valid_transition(
        State.ADDRESSED, State.ACKNOWLEDGED, actor="raiser"
    ) is True
    assert is_valid_transition(
        State.ADDRESSED, State.ACKNOWLEDGED, actor="addressee"
    ) is True
    # Pure mutual is also accepted as an actor identifier in the validator
    assert is_valid_transition(
        State.ADDRESSED, State.ACKNOWLEDGED, actor="mutual"
    ) is False  # mutual is not raiser/addressee — orchestrator post-check


def test_addressed_to_withdrawn_by_raiser():
    assert is_valid_transition(State.ADDRESSED, State.WITHDRAWN, actor="raiser") is True
    assert is_valid_transition(
        State.ADDRESSED, State.WITHDRAWN, actor="addressee"
    ) is False


def test_capped_orchestrator_only():
    """Capped is reachable from any non-terminal state by the orchestrator
    only — never by an agent."""
    assert is_valid_transition(
        State.OPEN, State.CAPPED, actor="orchestrator"
    ) is True
    assert is_valid_transition(
        State.ADDRESSED, State.CAPPED, actor="orchestrator"
    ) is True
    # Agents cannot drive capping
    assert is_valid_transition(State.OPEN, State.CAPPED, actor="raiser") is False
    assert is_valid_transition(State.OPEN, State.CAPPED, actor="addressee") is False
    # Cannot re-cap a terminal item
    assert is_valid_transition(
        State.RESOLVED, State.CAPPED, actor="orchestrator"
    ) is False


def test_no_unspecified_transitions_allowed():
    """Spot-check a few transitions that should NOT be in the table."""
    # Cannot resolve directly from open without first being addressed
    assert is_valid_transition(State.OPEN, State.RESOLVED, actor="raiser") is False
    # Cannot acknowledge an open item directly
    assert is_valid_transition(
        State.OPEN, State.ACKNOWLEDGED, actor="raiser"
    ) is False
    # Cannot un-resolve
    assert is_valid_transition(
        State.RESOLVED, State.OPEN, actor="raiser"
    ) is False
    # Cannot transition out of any terminal state
    assert is_valid_transition(
        State.WITHDRAWN, State.OPEN, actor="raiser"
    ) is False
