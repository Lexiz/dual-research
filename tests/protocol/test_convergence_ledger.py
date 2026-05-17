"""Spec 0043 — convergence ledger cross-check tests."""

from __future__ import annotations

from dual_research.protocol.convergence import is_plan_agreed, is_review_approved
from tests.protocol.fixtures import PLAN_TURN_AGREED, REVIEW_TURN_APPROVED


def test_is_plan_agreed_with_ledger_zero_terminates() -> None:
    """Self-counters say AGREED + 0 + 0, ledger says 0 → terminates."""
    assert is_plan_agreed(PLAN_TURN_AGREED, PLAN_TURN_AGREED, ledger_open_count=0) is True


def test_is_plan_agreed_with_ledger_nonzero_blocks_termination() -> None:
    """Self-counters say AGREED + 0 + 0 but ledger says 3 items still
    open → blocks convergence. This is the spec 0043 D7 semantic:
    the system requires BOTH signals to agree, and the conservative
    side wins."""
    assert is_plan_agreed(PLAN_TURN_AGREED, PLAN_TURN_AGREED, ledger_open_count=3) is False


def test_is_plan_agreed_ledger_none_skips_check_legacy() -> None:
    """When ledger_open_count is None (kill-switch / legacy), only the
    self-counter check applies — pre-spec behaviour preserved."""
    assert is_plan_agreed(PLAN_TURN_AGREED, PLAN_TURN_AGREED, ledger_open_count=None) is True


def test_is_review_approved_with_ledger_zero_terminates() -> None:
    """Phase 4: agents APPROVED + 0 issues + ledger 0 → terminates."""
    assert is_review_approved(REVIEW_TURN_APPROVED, REVIEW_TURN_APPROVED,
                              round=1, ledger_open_count=0) is True


def test_is_review_approved_with_ledger_nonzero_blocks() -> None:
    assert is_review_approved(REVIEW_TURN_APPROVED, REVIEW_TURN_APPROVED,
                              round=1, ledger_open_count=5) is False


def test_is_review_approved_ledger_none_skips_check_legacy() -> None:
    assert is_review_approved(REVIEW_TURN_APPROVED, REVIEW_TURN_APPROVED,
                              round=1, ledger_open_count=None) is True
