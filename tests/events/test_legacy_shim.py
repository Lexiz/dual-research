"""Spec 0114 — legacy-shim unit tests.

The shim derives legacy event payload fields from a new-protocol
ledger snapshot. Tests assert the counter math is correct for each
legacy event type.
"""

from __future__ import annotations

from dual_research.events.legacy_shim import (
    LedgerSnapshotEntry,
    phase0_complete_legacy_fields,
    phase2_complete_legacy_fields,
    phase2_round_complete_legacy_fields,
    phase4_complete_legacy_fields,
    phase4_round_complete_legacy_fields,
)


def _entry(**kwargs):
    base = {
        "item_id": "X",
        "kind": "question",
        "raiser": "claude",
        "current_state": "open",
    }
    base.update(kwargs)
    return LedgerSnapshotEntry(**base)


def test_phase0_brief_issues_counts_open_plus_addressed():
    ledger = [
        _entry(item_id="Q-input-c-01", raiser="claude", current_state="open"),
        _entry(item_id="Q-input-c-02", raiser="claude", current_state="addressed"),
        _entry(item_id="Q-input-c-03", raiser="claude", current_state="resolved"),
        _entry(item_id="D-input-g-01", raiser="openai", kind="disagreement", current_state="open"),
    ]
    fields = phase0_complete_legacy_fields(
        ledger,
        claude_status="AGREED",
        openai_status="AGREED",
    )
    assert fields["claude_brief_issues"] == 2  # open + addressed
    assert fields["openai_brief_issues"] == 1
    assert fields["brief_needs_input"] is False


def test_phase2_round_complete_counters_split_by_kind_and_raiser():
    ledger = [
        # claude: 1 open Q, 1 addressed Q, 1 resolved Q
        _entry(item_id="Q-plan-c-01", raiser="claude", current_state="open"),
        _entry(item_id="Q-plan-c-02", raiser="claude", current_state="addressed"),
        _entry(item_id="Q-plan-c-03", raiser="claude", current_state="resolved"),
        # claude: 1 open D, 1 ack'd D
        _entry(item_id="D-plan-c-04", raiser="claude", kind="disagreement", current_state="open"),
        _entry(item_id="D-plan-c-05", raiser="claude", kind="disagreement", current_state="acknowledged"),
        # openai: 0 open Q, 1 open D, 2 ack'd D
        _entry(item_id="D-plan-g-01", raiser="openai", kind="disagreement", current_state="open"),
        _entry(item_id="D-plan-g-02", raiser="openai", kind="disagreement", current_state="acknowledged"),
        _entry(item_id="D-plan-g-03", raiser="openai", kind="disagreement", current_state="acknowledged"),
    ]
    fields = phase2_round_complete_legacy_fields(
        ledger,
        round=3,
        agreed=True,
        claude_status="AGREED",
        openai_status="AGREED",
        claude_drafter="claude",
        openai_drafter="claude",
    )
    assert fields["claude_open_questions"] == 2  # 1 open + 1 addressed
    assert fields["openai_open_questions"] == 0
    assert fields["claude_blocking"] == 1
    assert fields["openai_blocking"] == 1
    assert fields["claude_fsd"] == 1
    assert fields["openai_fsd"] == 2
    assert fields["claude_drafter"] == "claude"


def test_phase4_round_complete_open_issues_includes_addressed_and_all_kinds():
    """Phase 4's open_issues counter is the conflated count of every
    open + addressed item raised by that agent in phase 4."""
    ledger = [
        # claude: 1 open issue + 1 addressed comment + 1 resolved disagreement
        _entry(item_id="I-review-c-01", raiser="claude", kind="issue", current_state="open"),
        _entry(item_id="C-review-c-02", raiser="claude", kind="comment", current_state="addressed"),
        _entry(item_id="D-review-c-03", raiser="claude", kind="disagreement", current_state="resolved"),
        # openai: 1 open issue + 1 capped item
        _entry(item_id="I-review-g-01", raiser="openai", kind="issue", current_state="open"),
        _entry(item_id="I-review-g-02", raiser="openai", kind="issue", current_state="capped"),
    ]
    fields = phase4_round_complete_legacy_fields(
        ledger,
        round=4,
        approved=True,
        claude_status="AGREED",
        openai_status="AGREED",
        draft_round=5,
    )
    assert fields["claude_open_issues"] == 2
    assert fields["openai_open_issues"] == 1
    assert fields["draft_round"] == 5


def test_phase2_complete_fsd_count_matches_acknowledged_disagreements():
    ledger = [
        _entry(item_id="D-plan-c-01", raiser="claude", kind="disagreement", current_state="acknowledged"),
        _entry(item_id="D-plan-g-02", raiser="openai", kind="disagreement", current_state="acknowledged"),
        _entry(item_id="D-plan-g-03", raiser="openai", kind="disagreement", current_state="resolved"),
        _entry(item_id="Q-plan-c-04", raiser="claude", kind="question", current_state="acknowledged"),
    ]
    fields = phase2_complete_legacy_fields(
        ledger,
        rounds=5,
        converged=True,
        drafter="claude",
    )
    # Only acknowledged DISAGREEMENTS count toward fsd_count (not questions)
    assert fields["fsd_count"] == 2
    # New escape valves are gone — these all default False
    assert fields["via_canonical_promotion"] is False
    assert fields["via_canonical_fsd_synthesis"] is False
    assert fields["via_stuck_agreed"] is False


def test_phase4_complete_via_stuck_agreed_always_false():
    fields = phase4_complete_legacy_fields(
        rounds=6,
        approved=True,
        final_draft_round=7,
        revisions=3,
    )
    assert fields["via_stuck_agreed"] is False
    assert fields["rounds"] == 6
    assert fields["approved"] is True
    assert fields["revisions"] == 3


def test_phase0_with_brief_needs_input_passthrough():
    """Shim preserves the brief_needs_input flag passed in by the caller."""
    fields = phase0_complete_legacy_fields(
        [],
        claude_status="BRIEF_NEEDS_INPUT",
        openai_status=None,
        brief_needs_input=True,
    )
    assert fields["brief_needs_input"] is True
    assert fields["claude_status"] == "BRIEF_NEEDS_INPUT"
