from __future__ import annotations

from dual_research.protocol import parse_turn, pick_drafter
from tests.protocol.fixtures import plan_turn_agreed


def _turn(drafter: str, self_fit: int, other_fit: int):
    return parse_turn(plan_turn_agreed(drafter, fit_self=self_fit, fit_other=other_fit))


def test_matching_recommendations_short_circuits() -> None:
    choice = pick_drafter(
        claude_phase2_turns=[_turn("openai", 3, 5)],
        openai_phase2_turns=[_turn("openai", 5, 2)],
        phase1_drafts={"claude": "", "openai": ""},
        agreed_plan_text=None,
        brief_content="brief",
    )
    assert choice.drafter == "openai"
    assert choice.reason == "matching-recommendations"


def test_domain_fit_decides_when_recommendations_diverge() -> None:
    # claude self=5, openai other-rates claude=2 → claude total 7
    # openai self=3, claude other-rates openai=4 → openai total 7
    # tied → falls through to plan alignment (no plan) → hash
    choice = pick_drafter(
        claude_phase2_turns=[_turn("claude", 5, 4)],
        openai_phase2_turns=[_turn("openai", 3, 2)],
        phase1_drafts={"claude": "", "openai": ""},
        agreed_plan_text=None,
        brief_content="brief",
    )
    # tied on domain fit (claude_score = 5+2 = 7, openai_score = 3+4 = 7); no plan → hash
    assert choice.reason in {"hash-of-brief", "domain-fit"}


def test_domain_fit_with_clear_winner() -> None:
    # claude self=5, openai other-rates claude=5 → claude total 10
    # openai self=2, claude other-rates openai=2 → openai total 4
    choice = pick_drafter(
        claude_phase2_turns=[_turn("claude", 5, 2)],
        openai_phase2_turns=[_turn("openai", 2, 5)],
        phase1_drafts={"claude": "", "openai": ""},
        agreed_plan_text=None,
        brief_content="brief",
    )
    assert choice.reason == "domain-fit"
    assert choice.drafter == "claude"
    assert choice.domain_fit_scores == {"claude": 10, "openai": 4}


def test_plan_alignment_when_domain_fit_ties() -> None:
    # Domain fit ties at 4/4 each. Plan alignment should decide.
    plan = "background analysis recommendation methodology"
    choice = pick_drafter(
        claude_phase2_turns=[_turn("claude", 2, 2)],
        openai_phase2_turns=[_turn("openai", 2, 2)],
        phase1_drafts={
            "claude": "background analysis recommendation methodology framework",
            "openai": "totally unrelated content here words",
        },
        agreed_plan_text=plan,
        brief_content="brief",
    )
    assert choice.reason == "plan-alignment"
    assert choice.drafter == "claude"


def test_hash_of_brief_when_everything_ties() -> None:
    choice = pick_drafter(
        claude_phase2_turns=[_turn("claude", 3, 3)],
        openai_phase2_turns=[_turn("openai", 3, 3)],
        phase1_drafts={"claude": "same words same", "openai": "same words same"},
        agreed_plan_text="same words same",
        brief_content="deterministic brief content",
    )
    assert choice.reason == "hash-of-brief"
    assert choice.drafter in {"claude", "openai"}


def test_hash_of_brief_deterministic_for_same_brief() -> None:
    c1 = pick_drafter(
        claude_phase2_turns=[_turn("claude", 3, 3)],
        openai_phase2_turns=[_turn("openai", 3, 3)],
        phase1_drafts={"claude": "x", "openai": "x"},
        agreed_plan_text="x",
        brief_content="exact same brief",
    )
    c2 = pick_drafter(
        claude_phase2_turns=[_turn("claude", 3, 3)],
        openai_phase2_turns=[_turn("openai", 3, 3)],
        phase1_drafts={"claude": "x", "openai": "x"},
        agreed_plan_text="x",
        brief_content="exact same brief",
    )
    assert c1.drafter == c2.drafter
