"""Spec 0114 — Deep Research lifecycle event tests.

Confirms serialization round-trip for the new event types and that
default field values come through cleanly.
"""

from __future__ import annotations

from dual_research.events import (
    CloseoutUrged,
    CloseoutViolation,
    ItemRaised,
    ItemTransitioned,
    PhaseConverged,
)


def test_item_raised_round_trip():
    ev = ItemRaised(
        id="Q-plan-c-04",
        item_kind="question",
        phase=2,
        round=3,
        raiser="claude",
        body="What evidence supports the Go choice?",
        anchor_type="quote",
        anchor_text="Go is the recommended language",
        evidence_required=True,
    )
    assert ev.kind == "item_raised"
    assert ev.id == "Q-plan-c-04"
    payload = ev.to_dict()
    assert payload["kind"] == "item_raised"
    assert payload["item_kind"] == "question"
    assert payload["phase"] == 2
    assert payload["evidence_required"] is True


def test_item_transitioned_agent_actor():
    ev = ItemTransitioned(
        id="D-plan-g-02",
        from_state="addressed",
        to_state="resolved",
        actor="claude",
        phase=2,
        round=4,
        reason="The pkg.go.dev evidence convinced me.",
    )
    assert ev.kind == "item_transitioned"
    assert ev.via is None
    assert ev.evidence_records == []
    payload = ev.to_dict()
    assert payload["actor"] == "claude"
    assert payload["via"] is None


def test_item_transitioned_orchestrator_hard_cap():
    ev = ItemTransitioned(
        id="Q-review-c-05",
        from_state="open",
        to_state="capped",
        actor="orchestrator",
        phase=4,
        round=8,
        reason="Hard cap reached for phase 4.",
        via="hard_cap",
    )
    assert ev.via == "hard_cap"


def test_item_transitioned_ghost_cap_with_evidence():
    """Evidence records populate the field on ADDRESS transitions."""
    record = {
        "item_id": "D-plan-g-04",
        "url": "https://example.com",
        "title": "Example",
        "search_query": "q",
        "fetched_at": "2026-05-19T12:00:00Z",
        "evidence_event_id": "srvtoolu_abc",
        "content_excerpt": "x" * 300,
    }
    ev = ItemTransitioned(
        id="D-plan-g-04",
        from_state="open",
        to_state="addressed",
        actor="claude",
        phase=2,
        round=2,
        reason="response with evidence",
        evidence_records=[record],
    )
    payload = ev.to_dict()
    assert payload["evidence_records"][0]["url"] == "https://example.com"


def test_closeout_urged_payload():
    ev = CloseoutUrged(
        phase=2,
        round=5,
        affected_items=["D-plan-g-02", "Q-plan-c-04"],
        affected_raiser_budgets={"claude": 1, "openai": 2},
    )
    assert ev.kind == "closeout_urged"
    payload = ev.to_dict()
    assert payload["affected_items"] == ["D-plan-g-02", "Q-plan-c-04"]
    assert payload["affected_raiser_budgets"] == {"claude": 1, "openai": 2}


def test_closeout_violation_payload():
    ev = CloseoutViolation(
        phase=2,
        round=5,
        agent="claude",
        violation_code="closeout_violation_raise",
        dropped_block="### RAISE\nkind: question\n…",
    )
    assert ev.kind == "closeout_violation"
    payload = ev.to_dict()
    assert payload["violation_code"] == "closeout_violation_raise"


def test_phase_converged_organic():
    ev = PhaseConverged(phase=2, final_round=4)
    assert ev.kind == "phase_converged"
    assert ev.via_closeout is False
    assert ev.via_ghost_cap is False
    assert ev.via_hard_cap is False


def test_phase_converged_via_closeout():
    ev = PhaseConverged(phase=4, final_round=6, via_closeout=True)
    payload = ev.to_dict()
    assert payload["via_closeout"] is True
    assert payload["via_ghost_cap"] is False
    assert payload["via_hard_cap"] is False


def test_phase_converged_via_ghost_cap():
    ev = PhaseConverged(phase=2, final_round=8, via_ghost_cap=True)
    payload = ev.to_dict()
    assert payload["via_ghost_cap"] is True


def test_phase_converged_via_hard_cap():
    ev = PhaseConverged(phase=2, final_round=8, via_hard_cap=True)
    payload = ev.to_dict()
    assert payload["via_hard_cap"] is True
