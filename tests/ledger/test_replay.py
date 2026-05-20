"""Spec 0122 — replay item-lifecycle events from on-disk round files."""

from __future__ import annotations

import textwrap
from pathlib import Path

from dual_research.ledger.replay import replay_items_from_disk


def _write_round(
    session_dir: Path,
    *,
    phase: int,
    round: int,
    agent: str,
    body: str,
) -> None:
    phase_dir = session_dir / f"phase{phase}"
    phase_dir.mkdir(parents=True, exist_ok=True)
    (phase_dir / f"round-{round:02d}-{agent}.md").write_text(
        textwrap.dedent(body).strip() + "\n", encoding="utf-8"
    )


def _seed_two_round_phase2(session_dir: Path) -> None:
    """Round 1: claude raises Q + D; openai raises D.
    Round 2: openai addresses claude's D; claude resolves their own D.
    """
    _write_round(session_dir, phase=2, round=1, agent="claude", body="""
        ## Stance
        Initial position.

        ## Addressing items raised against me

        ## Ratifying my own items

        ## New items I'm raising

        ### RAISE
        kind: question
        body: |
          Will the migration handle nulls correctly?
        anchor_type: none
        anchor_text: ""
        evidence_required: true

        ### RAISE
        kind: disagreement
        body: |
          Schema choice should favor JSON over Postgres rows.
        anchor_type: none
        anchor_text: ""
        evidence_required: true

        ## Status

        STATUS: IN_PROGRESS
        RAISED_THIS_TURN: [Q-plan-c-01, D-plan-c-01]
        ADDRESSED_THIS_TURN: []
        RESOLVED_THIS_TURN: []
        ACKNOWLEDGED_THIS_TURN: []
        WITHDRAWN_THIS_TURN: []
        OPEN_QUESTIONS: 1
        OPEN_DISAGREEMENTS: 1
    """)

    _write_round(session_dir, phase=2, round=1, agent="openai", body="""
        ## Stance
        Counter-stance.

        ## Addressing items raised against me

        ### ADDRESS D-plan-c-01
        response: |
          I think Postgres rows are the right call given the read patterns.
        evidence: []

        ## Ratifying my own items

        ## New items I'm raising

        ### RAISE
        kind: disagreement
        body: |
          Concurrency model should be async, not threaded.
        anchor_type: none
        anchor_text: ""
        evidence_required: false

        ## Status

        STATUS: IN_PROGRESS
        RAISED_THIS_TURN: [D-plan-g-01]
        ADDRESSED_THIS_TURN: [D-plan-c-01]
        RESOLVED_THIS_TURN: []
        ACKNOWLEDGED_THIS_TURN: []
        WITHDRAWN_THIS_TURN: []
        OPEN_QUESTIONS: 0
        OPEN_DISAGREEMENTS: 1
    """)

    _write_round(session_dir, phase=2, round=2, agent="claude", body="""
        ## Stance
        Holding position.

        ## Addressing items raised against me

        ### ADDRESS D-plan-g-01
        response: |
          I see your point on async, here is my counter.
        evidence: []

        ## Ratifying my own items

        ### RESOLVE D-plan-c-01
        reason: |
          On reflection JSON storage adds complexity without payoff.

        ## New items I'm raising

        ## Status

        STATUS: IN_PROGRESS
        RAISED_THIS_TURN: []
        ADDRESSED_THIS_TURN: [D-plan-g-01]
        RESOLVED_THIS_TURN: [D-plan-c-01]
        ACKNOWLEDGED_THIS_TURN: []
        WITHDRAWN_THIS_TURN: []
        OPEN_QUESTIONS: 1
        OPEN_DISAGREEMENTS: 0
    """)

    _write_round(session_dir, phase=2, round=2, agent="openai", body="""
        ## Stance
        Holding position.

        ## Addressing items raised against me

        ## Ratifying my own items

        ## New items I'm raising

        ## Status

        STATUS: IN_PROGRESS
        RAISED_THIS_TURN: []
        ADDRESSED_THIS_TURN: []
        RESOLVED_THIS_TURN: []
        ACKNOWLEDGED_THIS_TURN: []
        WITHDRAWN_THIS_TURN: []
        OPEN_QUESTIONS: 0
        OPEN_DISAGREEMENTS: 1
    """)


def test_replay_recovers_items_and_transitions(tmp_path: Path) -> None:
    _seed_two_round_phase2(tmp_path)
    bundle = replay_items_from_disk(tmp_path)

    # Three items total: Q, D-plan-c-01, D-plan-g-01.
    assert len(bundle.items) == 3
    by_id = {it.id: it for it in bundle.items}
    assert set(by_id) == {"Q-plan-c-01", "D-plan-c-01", "D-plan-g-01"}

    # Claude's own disagreement: open in round 1, addressed (no-op
    # since the addressee is the raiser), then resolved in round 2.
    d_c = by_id["D-plan-c-01"]
    assert d_c.kind == "disagreement"
    assert d_c.phase == 2
    assert d_c.raiser == "claude"
    assert d_c.raised_round == 1
    assert d_c.current_state == "resolved"

    # The cross-agent disagreement: openai raises in r1, claude
    # addresses in r2.
    d_g = by_id["D-plan-g-01"]
    assert d_g.raiser == "openai"
    assert d_g.current_state == "addressed"
    assert d_g.transitions[-1].actor == "claude"

    # Question stays open across both rounds.
    q = by_id["Q-plan-c-01"]
    assert q.kind == "question"
    assert q.current_state == "open"


def test_replay_returns_empty_for_session_without_v2_files(tmp_path: Path) -> None:
    bundle = replay_items_from_disk(tmp_path)
    assert bundle.items == []
