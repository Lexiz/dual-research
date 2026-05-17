"""Spec 0043 — build_standing_items_section tests."""

from __future__ import annotations

from dual_research.ledger.models import LedgerEntry, LedgerState
from dual_research.ledger.prompt import build_standing_items_section


def _open_entry(*, kind: str, raised_by: str, raised_round: int, idx: int,
                body: str = "body") -> LedgerEntry:
    return LedgerEntry(
        id=f"{kind[:1].upper()}-{raised_by[0]}-r{raised_round}-{idx:02d}",
        kind=kind,
        raised_round=raised_round,
        raised_by=raised_by,
        raised_turn_key=f"phase2_round{raised_round}_{raised_by}",
        current_status="open",
        body_snippet=body,
    )


def test_empty_ledger_returns_empty_string() -> None:
    s = LedgerState(phase=2, entries=[])
    assert build_standing_items_section(s, perspective="claude") == ""


def test_only_closed_entries_returns_empty_string() -> None:
    s = LedgerState(phase=2, entries=[
        LedgerEntry(id="Q-g-r1-01", kind="question", raised_round=1,
                    raised_by="gpt", raised_turn_key="phase2_round1_gpt",
                    current_status="answered"),
    ])
    assert build_standing_items_section(s, perspective="claude") == ""


def test_groups_by_raiser_them_first() -> None:
    s = LedgerState(phase=2, entries=[
        _open_entry(kind="question", raised_by="gpt", raised_round=1, idx=1),
        _open_entry(kind="question", raised_by="claude", raised_round=1, idx=2),
    ])
    out = build_standing_items_section(s, perspective="claude")
    them_pos = out.find("Raised by gpt")
    you_pos = out.find("Raised by you")
    assert them_pos > 0
    assert you_pos > them_pos


def test_header_and_instruction_present() -> None:
    s = LedgerState(phase=2, entries=[
        _open_entry(kind="question", raised_by="gpt", raised_round=1, idx=1),
    ])
    out = build_standing_items_section(s, perspective="claude")
    assert "## Standing items from prior rounds" in out
    assert "flagged to the user as ghosted" in out


def test_entry_line_format_includes_id_kind_round_status() -> None:
    s = LedgerState(phase=2, entries=[
        _open_entry(kind="question", raised_by="gpt", raised_round=2, idx=3,
                    body="What is the threshold?"),
    ])
    out = build_standing_items_section(s, perspective="claude")
    assert "[Q-g-r2-03]" in out
    assert "question raised in r2" in out
    assert "What is the threshold?" in out
    assert "status: open" in out


def test_truncation_emits_omitted_footnote() -> None:
    entries = [
        _open_entry(kind="question", raised_by="gpt", raised_round=1, idx=i,
                    body=f"Question body {i}")
        for i in range(1, 50)
    ]
    s = LedgerState(phase=2, entries=entries)
    out = build_standing_items_section(s, perspective="claude", max_items=5)
    assert "more open item(s) omitted" in out
    # Body should include at most 5 [Q- entries (one per included item).
    rendered = out.count("[Q-")
    assert rendered == 5


def test_phase1_seed_claim_shows_p1_label() -> None:
    """A claim with raised_round=0 (Phase 1 seed) renders as ``raised
    in p1`` not ``raised in r0``."""
    s = LedgerState(phase=2, entries=[
        LedgerEntry(id="Cl-c-p1-01", kind="claim", raised_round=0,
                    raised_by="claude", raised_turn_key="phase1_claude",
                    current_status="open", body_snippet="P1 claim"),
    ])
    out = build_standing_items_section(s, perspective="gpt")
    assert "raised in p1" in out
