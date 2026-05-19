"""Spec 0115 — unified Item aggregation tests."""

from __future__ import annotations

from dual_research.ui.items import aggregate_items


def _raised(*, id: str, kind: str, phase: int, round: int, raiser: str,
            body: str = "x", evidence_required: bool = False) -> dict:
    return {
        "kind": "item_raised",
        "id": id,
        "item_kind": kind,
        "phase": phase,
        "round": round,
        "raiser": raiser,
        "body": body,
        "anchor_type": "none",
        "anchor_text": "",
        "evidence_required": evidence_required,
    }


def _transitioned(*, id: str, from_state: str, to_state: str, actor: str,
                  phase: int, round: int, reason: str = "", via: str | None = None,
                  evidence: list[dict] | None = None) -> dict:
    return {
        "kind": "item_transitioned",
        "id": id,
        "from_state": from_state,
        "to_state": to_state,
        "actor": actor,
        "phase": phase,
        "round": round,
        "reason": reason,
        "via": via,
        "evidence_records": evidence or [],
    }


def test_one_question_raised_then_resolved():
    events = [
        _raised(id="Q-plan-c-01", kind="question", phase=2, round=1, raiser="claude"),
        _transitioned(
            id="Q-plan-c-01", from_state="open", to_state="addressed",
            actor="openai", phase=2, round=2, reason="here is my answer.",
        ),
        _transitioned(
            id="Q-plan-c-01", from_state="addressed", to_state="resolved",
            actor="claude", phase=2, round=3, reason="i accept.",
        ),
    ]
    bundle = aggregate_items(events)

    assert len(bundle.items) == 1
    item = bundle.items[0]
    assert item.current_state == "resolved"
    assert item.raised_round == 1
    assert len(item.transitions) == 2

    # Round 1: claude raised 1 question (standing += 1, raised += 1).
    r1_claude = bundle.turn_category_stats[2][1]["claude"]
    assert r1_claude.questions.standing == 1
    assert r1_claude.questions.raised == 1
    assert r1_claude.questions.closed == 0
    # Round 2: openai addressed claude's question — but the
    # transition is recorded against claude's raiser column (it's
    # CLAUDE's standing being changed). Actually addressed doesn't
    # close it. Standing change goes to claude's slot at round 2.
    # The aggregator credits transitions to the raiser at the round
    # the transition fired. Open → addressed stays non-terminal so
    # standing is unchanged. closed/raised both stay 0 at r2.
    r2_claude = bundle.turn_category_stats[2][2]["claude"]
    assert r2_claude.questions.raised == 0
    assert r2_claude.questions.closed == 0
    # Round 3: claude resolved his own question (addressed → resolved
    # is non-terminal → terminal, so closed += 1, standing -= 1).
    r3_claude = bundle.turn_category_stats[2][3]["claude"]
    assert r3_claude.questions.closed == 1
    assert r3_claude.questions.standing == -1  # delta only; UI sums for absolute


def test_phase_totals_sum_correctly():
    events = [
        _raised(id="Q-plan-c-01", kind="question", phase=2, round=1, raiser="claude"),
        _raised(id="Q-plan-c-02", kind="question", phase=2, round=1, raiser="claude"),
        _raised(id="D-plan-c-01", kind="disagreement", phase=2, round=1, raiser="claude"),
        _raised(id="D-plan-g-01", kind="disagreement", phase=2, round=1, raiser="openai"),
        _transitioned(
            id="Q-plan-c-01", from_state="open", to_state="addressed",
            actor="openai", phase=2, round=2,
        ),
        _transitioned(
            id="Q-plan-c-01", from_state="addressed", to_state="resolved",
            actor="claude", phase=2, round=3, reason="ok",
        ),
        _transitioned(
            id="D-plan-c-01", from_state="open", to_state="capped",
            actor="orchestrator", phase=2, round=8, reason="hard cap", via="hard_cap",
        ),
    ]
    bundle = aggregate_items(events)

    phase2 = bundle.phase_category_stats[2]
    # 2 questions raised + 1 closed (resolved); standing = 2 - 1 = 1
    assert phase2.questions.raised == 2
    assert phase2.questions.closed == 1
    assert phase2.questions.standing == 1
    # 2 disagreements raised + 1 closed (hard-capped); standing = 1
    assert phase2.disagreements.raised == 2
    assert phase2.disagreements.closed == 1
    assert phase2.disagreements.capped == 1
    assert phase2.disagreements.standing == 1


def test_counter_argument_does_not_count_as_closed():
    """addressed → open (raiser counter-argues) keeps the item
    non-terminal — closed counter should not bump."""
    events = [
        _raised(id="Q-plan-c-01", kind="question", phase=2, round=1, raiser="claude"),
        _transitioned(
            id="Q-plan-c-01", from_state="open", to_state="addressed",
            actor="openai", phase=2, round=2,
        ),
        _transitioned(
            id="Q-plan-c-01", from_state="addressed", to_state="open",
            actor="claude", phase=2, round=3, reason="i counter-argue.",
        ),
    ]
    bundle = aggregate_items(events)

    r3_claude = bundle.turn_category_stats[2][3]["claude"]
    assert r3_claude.questions.closed == 0
    # Standing didn't change (addressed → open both non-terminal)
    assert r3_claude.questions.standing == 0


def test_ghost_cap_increments_capped_subset_of_closed():
    events = [
        _raised(id="Q-plan-c-01", kind="question", phase=2, round=1, raiser="claude"),
        _transitioned(
            id="Q-plan-c-01", from_state="open", to_state="capped",
            actor="orchestrator", phase=2, round=5, reason="ghost", via="ghost_cap",
        ),
    ]
    bundle = aggregate_items(events)
    r5_claude = bundle.turn_category_stats[2][5]["claude"]
    assert r5_claude.questions.closed == 1
    assert r5_claude.questions.capped == 1


def test_phase_4_supports_all_four_categories():
    events = [
        _raised(id="Q-review-c-01", kind="question", phase=4, round=1, raiser="claude"),
        _raised(id="D-review-c-01", kind="disagreement", phase=4, round=1, raiser="claude"),
        _raised(id="I-review-c-01", kind="issue", phase=4, round=1, raiser="claude"),
        _raised(id="C-review-c-01", kind="comment", phase=4, round=1, raiser="claude"),
    ]
    bundle = aggregate_items(events)
    phase4 = bundle.phase_category_stats[4]
    assert phase4.questions.raised == 1
    assert phase4.disagreements.raised == 1
    assert phase4.issues.raised == 1
    assert phase4.comments.raised == 1


def test_evidence_records_attached_to_address_transition():
    events = [
        _raised(
            id="D-plan-g-01", kind="disagreement", phase=2, round=1, raiser="openai",
            evidence_required=True,
        ),
        _transitioned(
            id="D-plan-g-01", from_state="open", to_state="addressed",
            actor="claude", phase=2, round=2,
            evidence=[{
                "url": "https://example.com",
                "title": "Example",
                "search_query": "q",
                "fetched_at": "2026-05-19T12:00:00Z",
                "evidence_event_id": "srvtoolu_abc",
                "content_excerpt": "x" * 250,
            }],
        ),
    ]
    bundle = aggregate_items(events)
    assert len(bundle.items[0].evidence) == 1
    ev = bundle.items[0].evidence[0]
    assert ev.url == "https://example.com"
    assert ev.title == "Example"
    assert ev.evidence_event_id == "srvtoolu_abc"


def test_acknowledged_via_mutual_handshake_recorded():
    events = [
        _raised(id="Q-plan-c-01", kind="question", phase=2, round=1, raiser="claude"),
        _transitioned(
            id="Q-plan-c-01", from_state="open", to_state="addressed",
            actor="openai", phase=2, round=2,
        ),
        _transitioned(
            id="Q-plan-c-01", from_state="addressed", to_state="acknowledged",
            actor="mutual", phase=2, round=4, reason="no path",
        ),
    ]
    bundle = aggregate_items(events)
    item = bundle.items[0]
    assert item.current_state == "acknowledged"
    assert item.transitions[-1].actor == "mutual"
    r4_claude = bundle.turn_category_stats[2][4]["claude"]
    assert r4_claude.questions.closed == 1
    assert r4_claude.questions.capped == 0
