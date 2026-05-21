"""Spec 0142 — ``_derive_turn_key`` round-keys Phase 0.

Pre-spec the gate at ``_call.py`` and ``ui/aggregator.py`` only included
the round index for ``phase ∈ {2, 4}``, so per-round Phase-0 bundles
collapsed onto ``phase0_<agent>.json`` and last-write-wins clobbered the
rest. The fix extends the gate to include phase 0.
"""

from __future__ import annotations

from dual_research.orchestrator._call import _derive_turn_key


def test_phase0_round1_claude_round_keyed() -> None:
    assert _derive_turn_key(
        agent_label="claude",
        phase="phase0",
        label="phase0-r1-claude",
    ) == "phase0_round1_claude"


def test_phase0_round2_claude_round_keyed() -> None:
    assert _derive_turn_key(
        agent_label="claude",
        phase="phase0",
        label="phase0-r2-claude",
    ) == "phase0_round2_claude"


def test_phase0_round3_openai_round_keyed_under_gpt_alias() -> None:
    # The backend label is "openai"; the persisted key uses the UI alias "gpt".
    assert _derive_turn_key(
        agent_label="openai",
        phase="phase0",
        label="phase0-r3-openai",
    ) == "phase0_round3_gpt"


def test_phase0_no_round_marker_keeps_legacy_key() -> None:
    """Pre-0114 single-shot Phase 0 labels carry no ``-r{N}-`` segment;
    those continue to map to ``phase0_<agent>`` so legacy fixtures keep
    working."""
    assert _derive_turn_key(
        agent_label="claude",
        phase="phase0",
        label="phase0-claude",
    ) == "phase0_claude"


def test_phase0_repair_suffix_preserved() -> None:
    assert _derive_turn_key(
        agent_label="claude",
        phase="phase0",
        label="phase0-r2-claude-repair",
    ) == "phase0_round2_claude_repair"


def test_phase1_unchanged_no_round_key() -> None:
    """Phase 1 is a single-call phase; it must NOT acquire a round key."""
    assert _derive_turn_key(
        agent_label="claude",
        phase="phase1",
        label="phase1-claude",
    ) == "phase1_claude"


def test_phase2_round1_still_round_keyed() -> None:
    """Regression-pin the Phase 2 / 4 behaviour that was already correct."""
    assert _derive_turn_key(
        agent_label="claude",
        phase="phase2",
        label="phase2-r1-claude",
    ) == "phase2_round1_claude"
