"""Spec 0114 — closeout module unit tests.

The real parser lands in step 5; tests here mock the parser callable to
produce ``ParsedTurnV2`` results directly, isolating the closeout
mechanism from parser implementation choices.
"""

from __future__ import annotations

from dual_research.contract.categories import Category
from dual_research.contract.operations import (
    AddressBlock,
    RaiseBlock,
    ResolveBlock,
)
from dual_research.orchestrator.closeout import (
    CloseoutTracker,
    _ItemView,
    check_convergence,
    ghost_cap_reason,
    hard_cap_reason,
    items_blocking_convergence,
    parse_with_closeout,
    select_ghost_cap_items,
    should_urge_closeout,
)
from dual_research.protocol.parse_v2 import ParsedTurnV2


# ─── Tracker behavior ─────────────────────────────────────────────────


def test_tracker_default_budget_per_phase():
    t2 = CloseoutTracker.for_phase(2)
    assert t2.initial_budget == 2
    assert t2.remaining("claude") == 2
    assert t2.has_budget("claude") is True


def test_tracker_decrements():
    t = CloseoutTracker(phase=2, initial_budget=2)
    assert t.remaining("claude") == 2
    assert t.decrement_on_fail("claude") == 1
    assert t.decrement_on_fail("claude") == 0
    assert t.has_budget("claude") is False
    # decrementing past zero stays at zero
    assert t.decrement_on_fail("claude") == 0


def test_tracker_per_agent_independent():
    t = CloseoutTracker(phase=2, initial_budget=2)
    t.decrement_on_fail("claude")
    assert t.remaining("claude") == 1
    assert t.remaining("openai") == 2


def test_tracker_tracks_rounds_used():
    t = CloseoutTracker(phase=2, initial_budget=2)
    t.decrement_on_fail("claude")
    t.decrement_on_fail("claude")
    assert t.closeout_rounds_used["claude"] == 2


# ─── Closeout-urge predicate ──────────────────────────────────────────


def test_no_urge_when_one_side_in_progress():
    items = [_ItemView(id="Q-plan-c-01", raiser="claude", current_state="open")]
    assert should_urge_closeout(
        claude_status="AGREED",
        openai_status="IN_PROGRESS",
        items=items,
    ) is False


def test_no_urge_when_all_terminal():
    items = [
        _ItemView(id="Q-plan-c-01", raiser="claude", current_state="resolved"),
        _ItemView(id="D-plan-g-02", raiser="openai", current_state="acknowledged"),
    ]
    assert should_urge_closeout(
        claude_status="AGREED",
        openai_status="AGREED",
        items=items,
    ) is False


def test_urge_when_both_agreed_with_nonterminal():
    items = [
        _ItemView(id="Q-plan-c-01", raiser="claude", current_state="addressed"),
    ]
    assert should_urge_closeout(
        claude_status="AGREED",
        openai_status="AGREED",
        items=items,
    ) is True


# ─── Ghost-cap selection ──────────────────────────────────────────────


def test_select_ghost_cap_only_for_agent():
    items = [
        _ItemView(id="Q-plan-c-01", raiser="claude", current_state="open"),
        _ItemView(id="Q-plan-g-02", raiser="openai", current_state="open"),
        _ItemView(id="D-plan-c-03", raiser="claude", current_state="resolved"),
    ]
    capped = select_ghost_cap_items(agent="claude", items=items)
    assert [it.id for it in capped] == ["Q-plan-c-01"]


def test_ghost_cap_reason_includes_agent_and_round():
    r = ghost_cap_reason("claude", round=7, budget_used=2)
    assert "claude" in r
    assert "round 7" in r
    assert "2 closeout rounds" in r


def test_hard_cap_reason_includes_phase_and_round():
    r = hard_cap_reason(4, round=8)
    assert "phase 4" in r
    assert "round 8" in r


# ─── Convergence cross-check ──────────────────────────────────────────


def test_convergence_all_three_required():
    no_items: list[_ItemView] = []
    c = check_convergence(
        claude_status="AGREED",
        openai_status="AGREED",
        items=no_items,
        artifact_hash_match=True,
    )
    assert c.converged is True
    assert c.both_agreed and c.all_items_terminal and c.artifact_hash_matched


def test_convergence_fails_on_open_item():
    items = [_ItemView(id="Q-plan-c-01", raiser="claude", current_state="open")]
    c = check_convergence(
        claude_status="AGREED",
        openai_status="AGREED",
        items=items,
        artifact_hash_match=True,
    )
    assert c.converged is False
    assert c.all_items_terminal is False


def test_convergence_fails_on_hash_mismatch():
    c = check_convergence(
        claude_status="AGREED",
        openai_status="AGREED",
        items=[],
        artifact_hash_match=False,
    )
    assert c.converged is False
    assert c.artifact_hash_matched is False


def test_convergence_fails_when_one_side_in_progress():
    c = check_convergence(
        claude_status="AGREED",
        openai_status="IN_PROGRESS",
        items=[],
        artifact_hash_match=True,
    )
    assert c.converged is False
    assert c.both_agreed is False


# ─── parse_with_closeout flow ─────────────────────────────────────────


def _make_parser(blocks, *, status="IN_PROGRESS", raised_this_turn=None):
    """Return a parser callable that ignores its input and yields a fixed
    ``ParsedTurnV2`` for testing."""

    def _parse(text: str) -> ParsedTurnV2:
        return ParsedTurnV2(
            status=status,
            blocks=blocks,
            raised_this_turn=list(raised_this_turn or []),
            counters={},
        )

    return _parse


# A minimal turn text that satisfies the validator's structural gates.
_VALID_TURN_TEXT = """\
## Stance
position.

## Addressing items raised against me
(none)

## Ratifying my own items
(none)

## New items I'm raising
(none)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""


def test_non_closeout_round_passes_through():
    block = AddressBlock(
        item_id="Q-plan-g-02",
        response="here is my answer.",
        proposes_status="addressed",
    )
    parser = _make_parser([block])
    result = parse_with_closeout(
        text=_VALID_TURN_TEXT,
        phase=2,
        round=2,
        agent="claude",
        parser=parser,
        is_closeout_round=False,
    )
    assert result.dropped_count == 0
    assert result.violations == []
    assert result.parsed.blocks == [block]
    assert result.validation.valid is True


def test_closeout_round_drops_raise_blocks():
    raise_block = RaiseBlock(
        kind=Category.QUESTION,
        body="late question",
        anchor_type="none",
        anchor_text="",
        evidence_required=False,
        raw_text="### RAISE\nkind: question\n…",
    )
    resolve_block = ResolveBlock(item_id="Q-plan-c-01", reason="convinced.")
    parser = _make_parser(
        [raise_block, resolve_block],
        raised_this_turn=["Q-plan-c-NEW"],
    )
    result = parse_with_closeout(
        text=_VALID_TURN_TEXT,
        phase=2,
        round=5,
        agent="claude",
        parser=parser,
        is_closeout_round=True,
    )
    assert result.dropped_count == 1
    assert len(result.violations) == 1
    assert result.violations[0].violation_code == "closeout_violation_raise"
    assert result.violations[0].agent == "claude"
    # The kept blocks no longer include the RAISE
    assert resolve_block in result.parsed.blocks
    assert raise_block not in result.parsed.blocks
    # raised_this_turn cleared on closeout-round filter
    assert result.parsed.raised_this_turn == []


def test_closeout_round_with_no_raise_passes_through():
    resolve_block = ResolveBlock(item_id="Q-plan-c-01", reason="convinced.")
    parser = _make_parser([resolve_block])
    result = parse_with_closeout(
        text=_VALID_TURN_TEXT,
        phase=2,
        round=5,
        agent="claude",
        parser=parser,
        is_closeout_round=True,
    )
    assert result.dropped_count == 0
    assert result.violations == []
    assert result.parsed.blocks == [resolve_block]


def test_items_blocking_convergence_helper():
    items = [
        _ItemView(id="a", raiser="claude", current_state="resolved"),
        _ItemView(id="b", raiser="openai", current_state="addressed"),
        _ItemView(id="c", raiser="claude", current_state="capped"),
        _ItemView(id="d", raiser="openai", current_state="open"),
    ]
    blocking = items_blocking_convergence(items)
    assert {it.id for it in blocking} == {"b", "d"}
