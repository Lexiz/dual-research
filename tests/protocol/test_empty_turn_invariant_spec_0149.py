"""Spec 0149 §5.4 (D04) — every multi-round phase prompt must carry
the empty-turn invariant line that lists the ledger operation blocks
(including the spec-0149 §5.5 ``REQUEST_EVIDENCE`` op) and the terminal
status that lets the model exit the phase cleanly.

The orchestrator's ``EmptyTurnDetected`` check at
``deep_research.py:557`` fires when zero ledger blocks land in a phase
2/4 turn. The prompt-side fix is structural — the language below
prevents the no-op turn from being structurally valid.
"""

from __future__ import annotations

from dual_research.protocol import (
    negotiation_round1_prompt,
    negotiation_turn_prompt,
    review_turn_prompt,
)


_EMPTY_TURN_HEADING = "Empty-turn invariant (spec 0149 §5.4 — D04)"
_LEDGER_OPS = (
    "`### RAISE`",
    "`### ADDRESS`",
    "`### RESOLVE`",
    "`### ACKNOWLEDGE`",
    "`### WITHDRAW`",
    "`### REQUEST_EVIDENCE`",
)


def test_phase2_round1_prompt_carries_empty_turn_invariant() -> None:
    p = negotiation_round1_prompt(
        brief_content="brief",
        own_draft="own",
        other_draft="other",
        agent_name="claude",
        other_name="openai",
    )
    assert _EMPTY_TURN_HEADING in p
    for op in _LEDGER_OPS:
        assert op in p, f"missing op token {op}"
    # Round 1 cannot agree — language must say so.
    assert "Round 1 cannot terminate the phase" in p


def test_phase2_round_n_prompt_carries_empty_turn_invariant() -> None:
    p = negotiation_turn_prompt(
        brief_content="brief",
        own_draft="own",
        other_draft="other",
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        round=2,
        soft_cap=6,
        hard_cap=12,
    )
    assert _EMPTY_TURN_HEADING in p
    for op in _LEDGER_OPS:
        assert op in p, f"missing op token {op}"
    # Round N can terminate via STATUS: AGREED.
    assert "`STATUS: AGREED`" in p


def test_phase4_review_prompt_carries_empty_turn_invariant() -> None:
    p = review_turn_prompt(
        brief_content="brief",
        draft_content="draft",
        prior_turns=[],
        agent_name="claude",
        other_name="openai",
        drafter_name="claude",
        round=2,
        soft_cap=6,
        hard_cap=12,
    )
    assert _EMPTY_TURN_HEADING in p
    for op in _LEDGER_OPS:
        assert op in p, f"missing op token {op}"
    # Phase 4 terminates via STATUS: APPROVED.
    assert "`STATUS: APPROVED`" in p
