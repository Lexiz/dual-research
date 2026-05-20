"""Spec 0118 — per-piece token-size estimators emit canonical artifact IDs.

Every key emitted by ``pieces_for_*`` must be a recognised artifact ID
in spec 0117's registry (``dual_research.contract.artifacts``). The
``TestRegistryMembership`` class is the regression that catches drift.
"""

from __future__ import annotations

from dataclasses import dataclass

from dual_research.contract.artifacts import is_known
from dual_research.protocol.prompt_pieces import (
    estimate_tokens,
    pieces_for_drafting,
    pieces_for_plan_negotiation,
    pieces_for_preflight,
    pieces_for_research_plan,
    pieces_for_review,
    renormalize,
)


@dataclass(frozen=True)
class _Turn:
    """Minimal stand-in for protocol.prompts.PriorTurn."""
    agent: str
    round: int
    content: str


class TestEstimateTokens:
    def test_empty_returns_zero(self) -> None:
        assert estimate_tokens("") == 0
        assert estimate_tokens(None) == 0

    def test_nonempty_returns_positive_int(self) -> None:
        # ~3.5 chars/token; "hello world" (11 chars) → 3.
        assert estimate_tokens("hello world") == 3

    def test_long_text_scales_linearly(self) -> None:
        # 7000 / 3.5 = 2000
        assert estimate_tokens("x" * 7000) == 2000


class TestPhase0Preflight:
    def test_round1_minimum(self) -> None:
        pieces = pieces_for_preflight(system_task="sys", user_prompt="brief")
        assert set(pieces.keys()) == {"system.task.input", "user_prompt"}
        assert pieces["system.task.input"] > 0
        assert pieces["user_prompt"] > 0

    def test_round_n_with_history_and_ledger_and_closeout(self) -> None:
        pieces = pieces_for_preflight(
            system_task="sys",
            user_prompt="brief",
            prior_turns=[
                _Turn("claude", 1, "a" * 350),
                _Turn("openai", 1, "b" * 350),
            ],
            ledger="standing items text",
            closeout_request="closeout text",
        )
        assert set(pieces.keys()) == {
            "system.task.input",
            "user_prompt",
            "prior_turns.phase0",
            "ledger.standing_items",
            "closeout.request",
        }
        # 700 chars / 3.5 = 200
        assert pieces["prior_turns.phase0"] == 200

    def test_empty_prior_omits_key(self) -> None:
        pieces = pieces_for_preflight(
            system_task="s", user_prompt="b", prior_turns=[],
        )
        assert "prior_turns.phase0" not in pieces


class TestPhase1ResearchPlan:
    def test_emits_three_canonical_keys(self) -> None:
        pieces = pieces_for_research_plan(
            system_task="sys", user_prompt="brief", agreed_interpretation="interp",
        )
        assert set(pieces.keys()) == {
            "system.task.research_plan",
            "user_prompt",
            "phase0.agreement.interpretation",
        }


class TestPhase2PlanNegotiation:
    def test_round1_no_prior_turns(self) -> None:
        pieces = pieces_for_plan_negotiation(
            system_task="sys",
            user_prompt="brief",
            agreed_interpretation="interp",
            phase1_claude="claude plan",
            phase1_openai="gpt plan",
        )
        assert set(pieces.keys()) == {
            "system.task.plan_negotiation",
            "user_prompt",
            "phase0.agreement.interpretation",
            "phase1.claude",
            "phase1.openai",
        }
        assert "prior_turns.phase2" not in pieces

    def test_round_n_with_history_ledger_closeout(self) -> None:
        pieces = pieces_for_plan_negotiation(
            system_task="sys",
            user_prompt="brief",
            agreed_interpretation="interp",
            phase1_claude="c",
            phase1_openai="o",
            prior_turns=[_Turn("claude", 1, "x" * 700)],
            ledger="ledger",
            closeout_request="closeout",
        )
        assert {"prior_turns.phase2", "ledger.standing_items", "closeout.request"} <= set(pieces.keys())
        # 700 / 3.5 = 200
        assert pieces["prior_turns.phase2"] == 200


class TestPhase3Drafting:
    def test_emits_full_input_set(self) -> None:
        pieces = pieces_for_drafting(
            system_task="sys",
            user_prompt="brief",
            agreed_interpretation="interp",
            phase1_claude="claude plan",
            phase1_openai="gpt plan",
            agreed_plan="plan body",
            all_p2_turns=[_Turn("claude", 1, "x" * 700)],
            carry_forward="cf body",
        )
        assert set(pieces.keys()) == {
            "system.task.drafting",
            "user_prompt",
            "phase0.agreement.interpretation",
            "phase1.claude",
            "phase1.openai",
            "phase2.agreement.plan",
            "all_p2_turns",
            "carry_forward.phase2",
        }
        assert pieces["all_p2_turns"] == 200

    def test_omits_optional_when_absent(self) -> None:
        pieces = pieces_for_drafting(
            system_task="s",
            user_prompt="b",
            agreed_interpretation="i",
            phase1_claude="c",
            phase1_openai="o",
            agreed_plan="p",
        )
        assert "all_p2_turns" not in pieces
        assert "carry_forward.phase2" not in pieces


class TestPhase4Review:
    def test_round1_emits_three_keys(self) -> None:
        pieces = pieces_for_review(
            system_task="sys", user_prompt="brief", current_draft="draft body",
        )
        assert set(pieces.keys()) == {
            "system.task.review",
            "user_prompt",
            "current_draft",
        }

    def test_round_n_with_history_ledger_closeout(self) -> None:
        pieces = pieces_for_review(
            system_task="sys",
            user_prompt="brief",
            current_draft="draft",
            prior_turns=[_Turn("openai", 1, "z" * 700)],
            ledger="ledger",
            closeout_request="closeout",
        )
        assert {"prior_turns.phase4", "ledger.standing_items", "closeout.request"} <= set(pieces.keys())
        assert pieces["prior_turns.phase4"] == 200


class TestRegistryMembership:
    """Every emitted key must exist in spec 0117's artifact registry.

    Regression that catches drift between this module and the registry.
    """

    def test_preflight_keys_in_registry(self) -> None:
        pieces = pieces_for_preflight(
            system_task="s",
            user_prompt="u",
            prior_turns=[_Turn("c", 1, "x" * 10)],
            ledger="l",
            closeout_request="c",
        )
        for k in pieces:
            assert is_known(k), f"unknown artifact ID: {k!r}"

    def test_research_plan_keys_in_registry(self) -> None:
        pieces = pieces_for_research_plan(
            system_task="s", user_prompt="u", agreed_interpretation="i",
        )
        for k in pieces:
            assert is_known(k), f"unknown artifact ID: {k!r}"

    def test_plan_negotiation_keys_in_registry(self) -> None:
        pieces = pieces_for_plan_negotiation(
            system_task="s",
            user_prompt="u",
            agreed_interpretation="i",
            phase1_claude="c",
            phase1_openai="o",
            prior_turns=[_Turn("c", 1, "x" * 10)],
            ledger="l",
            closeout_request="c",
        )
        for k in pieces:
            assert is_known(k), f"unknown artifact ID: {k!r}"

    def test_drafting_keys_in_registry(self) -> None:
        pieces = pieces_for_drafting(
            system_task="s",
            user_prompt="u",
            agreed_interpretation="i",
            phase1_claude="c",
            phase1_openai="o",
            agreed_plan="p",
            all_p2_turns=[_Turn("c", 1, "x" * 10)],
            carry_forward="cf",
        )
        for k in pieces:
            assert is_known(k), f"unknown artifact ID: {k!r}"

    def test_review_keys_in_registry(self) -> None:
        pieces = pieces_for_review(
            system_task="s",
            user_prompt="u",
            current_draft="d",
            prior_turns=[_Turn("c", 1, "x" * 10)],
            ledger="l",
            closeout_request="c",
        )
        for k in pieces:
            assert is_known(k), f"unknown artifact ID: {k!r}"


class TestRenormalize:
    def test_sums_to_target(self) -> None:
        pieces = {"user_prompt": 100, "phase1.claude": 200, "phase1.openai": 100}
        out = renormalize(pieces, target_total=1000)
        # 400 raw → 1000 target, scale 2.5. Allow rounding drift ±1 token
        # per piece.
        assert abs(out["user_prompt"] - 250) <= 1
        assert abs(out["phase1.claude"] - 500) <= 1
        assert abs(out["phase1.openai"] - 250) <= 1

    def test_zero_target_passes_through(self) -> None:
        pieces = {"user_prompt": 100, "phase1.claude": 50}
        assert renormalize(pieces, target_total=0) == pieces

    def test_all_zero_pieces_unchanged(self) -> None:
        pieces = {"user_prompt": 0, "phase1.claude": 0}
        assert renormalize(pieces, target_total=1000) == pieces

    def test_zero_entries_stay_zero(self) -> None:
        pieces = {"user_prompt": 100, "phase1.claude": 0, "phase1.openai": 0}
        out = renormalize(pieces, target_total=500)
        assert out["phase1.claude"] == 0
        assert out["phase1.openai"] == 0
        # The non-zero piece absorbs the full target.
        assert out["user_prompt"] == 500
