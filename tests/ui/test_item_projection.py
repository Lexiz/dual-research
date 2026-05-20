"""Spec 0122 — Item → legacy typed list + phase_ledgers projection."""

from __future__ import annotations

from dual_research.ui.item_projection import (
    project_phase_ledgers,
    project_typed_lists,
)
from dual_research.ui.items import AggregatedItems
from dual_research.ui.models import Item, ItemTransition


def _open_question(item_id: str = "Q-plan-c-01") -> Item:
    return Item(
        id=item_id,
        kind="question",
        phase=2,
        raiser="claude",
        body="Will the migration handle nulls correctly?",
        raised_round=1,
        current_state="open",
    )


def _resolved_disagreement(item_id: str = "D-plan-c-01") -> Item:
    return Item(
        id=item_id,
        kind="disagreement",
        phase=2,
        raiser="claude",
        body="Schema choice should favor JSON over Postgres rows.",
        raised_round=1,
        current_state="resolved",
        transitions=[
            ItemTransition(
                from_state="open",
                to_state="addressed",
                actor="openai",
                round=2,
                reason="Counter on async cost.",
            ),
            ItemTransition(
                from_state="addressed",
                to_state="resolved",
                actor="claude",
                round=3,
                reason="JSON adds complexity without payoff.",
            ),
        ],
    )


def _open_issue() -> Item:
    return Item(
        id="I-review-g-04",
        kind="issue",
        phase=4,
        raiser="openai",
        body="Source [3] is unverified.",
        anchor_type="quote",
        anchor_text="convention-over-configuration",
        raised_round=2,
        current_state="open",
    )


def _comment() -> Item:
    return Item(
        id="C-review-g-01",
        kind="comment",
        phase=4,
        raiser="openai",
        body="Consider also covering the resilience axis.",
        raised_round=1,
        current_state="open",
    )


def _bundle(*items: Item) -> AggregatedItems:
    b = AggregatedItems()
    b.items.extend(items)
    return b


def test_project_typed_lists_partitions_by_kind() -> None:
    bundle = _bundle(
        _open_question(),
        _resolved_disagreement(),
        _open_issue(),
        _comment(),
    )
    qs, ds, iss, cms = project_typed_lists(bundle)
    assert [q.id for q in qs] == ["Q-plan-c-01"]
    assert [d.id for d in ds] == ["D-plan-c-01"]
    assert [i.id for i in iss] == ["I-review-g-04"]
    assert [c.id for c in cms] == ["C-review-g-01"]


def test_question_status_and_raised_turn_key() -> None:
    q = project_typed_lists(_bundle(_open_question()))[0][0]
    assert q.status == "open"
    assert q.raised_by == "claude"
    assert q.raised_turn_key == "phase2_round1_claude"


def test_disagreement_carries_progression_and_status() -> None:
    d = project_typed_lists(_bundle(_resolved_disagreement()))[1][0]
    # Resolved by claude (raiser), so the legacy status is "resolved-claude".
    assert d.status == "resolved-claude"
    assert d.opened_round == 1
    assert d.closed_round == 3
    # One initial "raised" step plus one per transition.
    assert len(d.progression) == 3
    assert d.progression[0].action == "raised"
    assert d.progression[1].action == "pushed back"  # open → addressed
    assert d.progression[2].action == "conceded"     # addressed → resolved


def test_issue_status_maps_to_open_when_state_is_open() -> None:
    i = project_typed_lists(_bundle(_open_issue()))[2][0]
    assert i.status == "open"
    assert i.raised_by == "gpt"
    assert i.quote == "convention-over-configuration"


def test_project_phase_ledgers_fills_only_phases_2_and_4() -> None:
    bundle = _bundle(
        _open_question(),
        _resolved_disagreement(),
        _open_issue(),
        _comment(),
    )
    ledgers = project_phase_ledgers(bundle)
    assert set(ledgers) == {2, 4}
    # Phase 2 has the question + the disagreement.
    assert {e["kind"] for e in ledgers[2]} == {"question", "disagreement"}
    # Phase 4 has the issue + the comment.
    assert {e["kind"] for e in ledgers[4]} == {"issue", "comment"}


def test_ledger_entry_status_history_tracks_transitions() -> None:
    bundle = _bundle(_resolved_disagreement())
    ledgers = project_phase_ledgers(bundle)
    entries = ledgers[2]
    assert len(entries) == 1
    e = entries[0]
    # Initial "open" + open→addressed + addressed→resolved = 3 entries.
    assert len(e["status_history"]) == 3
    assert e["status_history"][0]["status"] == "open"
    assert e["status_history"][1]["status"] == "addressed"
    assert e["status_history"][2]["status"] == "resolved"
    # Body snippet is populated and truncated cleanly.
    assert e["body_snippet"].startswith("Schema choice")
