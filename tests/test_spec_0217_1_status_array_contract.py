"""Spec 0217.1 — STATUS action arrays carry canonical IDs only.

Three regression tests pinning the §3.3 callout into the rendered prompts.
Each asserts the positive (post-fix) shape — substring ``IDs only`` adjacent
to the STATUS footer — and the antipodal absence of the pre-fix loose
placeholder. See spec 0217.1 §5 for the test plan rationale and
``handoffs/2026-05-25-spec-0217-ledger-status-block-authoritative-for-closures.md``
for the originating incident.
"""

from __future__ import annotations

from dual_research.protocol.prompts import (
    PriorTurn,
    plan_negotiation_round1_prompt_v2,
    plan_negotiation_round_n_prompt_v2,
    review_round1_prompt_v2,
)


def test_phase2_round1_prompt_declares_canonical_id_contract():
    """Test 5.1 — phase-2 round-1 prompt restates the canonical-ID-only rule.

    The §3.3 callout must ship in the rendered prompt so agents read
    "canonical IDs only" right next to the STATUS block they're about to
    populate. The pre-fix ``[list of IDs the orchestrator will assign]``
    phrasing must no longer appear (that wording was the loophole that
    let openai emit descriptive-string arrays in
    tests/fixtures/spec_0217/phase2/round-01-openai.md:81).
    """
    text = plan_negotiation_round1_prompt_v2(
        brief_content="B",
        agreed_interpretation="AI",
        own_plan="P1",
        other_plan="P2",
        agent_name="claude",
        other_name="openai",
    )
    assert "IDs only" in text
    assert "[list of IDs the orchestrator will assign]" not in text


def test_phase2_round_n_prompt_declares_canonical_id_contract():
    """Test 5.2 — phase-2 round-N prompt inherits the constraint via the
    shared ``_status_footer_for_phase`` helper.

    Round-N pulls the footer from the helper, so the §3.2 helper update
    plus the §3.3 inline callout are the two surfaces under test. The bare
    ``RAISED_THIS_TURN: [...]`` ellipsis placeholder (pre-fix shape) must
    no longer appear — the helper now emits ``[<canonical-id>, ...]``.
    """
    text = plan_negotiation_round_n_prompt_v2(
        brief_content="B",
        agreed_interpretation="AI",
        own_plan="P1",
        other_plan="P2",
        prior_turns=[PriorTurn(agent="claude", round=1, content="r1")],
        standing_items="(none)",
        agent_name="openai",
        other_name="claude",
        round=3,
        soft_cap=4,
        hard_cap=8,
    )
    assert "IDs only" in text
    assert "RAISED_THIS_TURN: [...]" not in text


def test_phase4_round1_prompt_declares_canonical_id_contract():
    """Test 5.3 — phase-4 prompt restates the canonical-ID-only rule.

    Phase 4 (review-draft) round 1 has its own inline STATUS footer (it
    does not use the helper at round 1). The §3.1 placeholder tightening
    plus the §3.3 callout are both pinned here.
    """
    text = review_round1_prompt_v2(
        brief_content="B",
        draft_content="THE DRAFT",
        drafter_name="claude",
        agent_name="claude",
        other_name="openai",
    )
    assert "IDs only" in text
    assert "RAISED_THIS_TURN: [...]" not in text
