"""Spec 0030 — per-piece token-size estimators.

The Consumption tab's segmented bars are powered by ``prompt_pieces`` —
a dict-of-int the aggregator records per turn. Each helper here mirrors
one phase's prompt-assembly call site; the test surface confirms shapes
(which kinds appear) and rough magnitude (renormalisation maintains
order, zero-history yields no `hist` segment, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass

from dual_research.protocol.prompt_pieces import (
    estimate_tokens,
    pieces_for_drafting,
    pieces_for_negotiation_round1,
    pieces_for_negotiation_turn,
    pieces_for_preflight,
    pieces_for_research,
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
        big = "x" * 7000
        # 7000 / 3.5 = 2000
        assert estimate_tokens(big) == 2000


class TestPhase0:
    def test_only_brief(self) -> None:
        pieces = pieces_for_preflight(brief="brief text here")
        assert set(pieces.keys()) == {"brief"}
        assert pieces["brief"] > 0


class TestPhase1:
    def test_only_brief(self) -> None:
        pieces = pieces_for_research(brief="another brief")
        assert set(pieces.keys()) == {"brief"}


class TestPhase2:
    def test_round1_has_brief_d1_d2_no_hist(self) -> None:
        pieces = pieces_for_negotiation_round1(
            brief="b", claude_draft="claude says X", openai_draft="gpt says Y"
        )
        assert set(pieces.keys()) == {"brief", "d1", "d2"}
        assert "hist" not in pieces

    def test_round2plus_adds_hist_from_prior_turns(self) -> None:
        prior = [
            _Turn(agent="claude", round=1, content="a" * 350),
            _Turn(agent="openai", round=1, content="b" * 350),
        ]
        pieces = pieces_for_negotiation_turn(
            brief="b",
            claude_draft="d",
            openai_draft="d",
            prior_turns=prior,
        )
        assert set(pieces.keys()) == {"brief", "d1", "d2", "hist"}
        # 700 chars / 3.5 = 200
        assert pieces["hist"] == 200

    def test_round2plus_empty_prior_yields_zero_hist(self) -> None:
        pieces = pieces_for_negotiation_turn(
            brief="b",
            claude_draft="d",
            openai_draft="d",
            prior_turns=[],
        )
        assert pieces["hist"] == 0


class TestPhase3:
    def test_includes_plan_and_hist(self) -> None:
        prior = [_Turn(agent="claude", round=1, content="x" * 70)]
        pieces = pieces_for_drafting(
            brief="b",
            claude_draft="d1",
            openai_draft="d2",
            plan="plan body",
            prior_turns=prior,
        )
        assert set(pieces.keys()) == {"brief", "d1", "d2", "plan", "hist"}
        assert pieces["plan"] > 0
        assert pieces["hist"] > 0

    def test_missing_plan_yields_zero(self) -> None:
        pieces = pieces_for_drafting(
            brief="b",
            claude_draft="d",
            openai_draft="d",
            plan=None,
            prior_turns=[],
        )
        assert pieces["plan"] == 0


class TestPhase4:
    def test_uses_histp_not_hist(self) -> None:
        """Phase 4's history segment must be ``histp`` (matches the Tk
        chip in how-it-works) — distinct from Phase 2's ``hist``."""
        pieces = pieces_for_review(
            brief="b",
            draft="draft text",
            prior_turns=[_Turn(agent="claude", round=1, content="z" * 70)],
        )
        assert "hist" not in pieces
        assert "histp" in pieces
        assert set(pieces.keys()) == {"brief", "draft", "histp"}

    def test_empty_prior_yields_zero_histp(self) -> None:
        pieces = pieces_for_review(brief="b", draft="d", prior_turns=[])
        assert pieces["histp"] == 0


class TestRenormalize:
    def test_sums_to_target(self) -> None:
        pieces = {"brief": 100, "d1": 200, "d2": 100}
        out = renormalize(pieces, target_total=1000)
        # 400 raw → 1000 target, scale 2.5. Allow rounding drift ±1 token
        # per piece.
        assert abs(out["brief"] - 250) <= 1
        assert abs(out["d1"] - 500) <= 1
        assert abs(out["d2"] - 250) <= 1

    def test_zero_target_passes_through(self) -> None:
        pieces = {"brief": 100, "d1": 50}
        assert renormalize(pieces, target_total=0) == pieces

    def test_all_zero_pieces_unchanged(self) -> None:
        pieces = {"brief": 0, "d1": 0}
        assert renormalize(pieces, target_total=1000) == pieces

    def test_zero_entries_stay_zero(self) -> None:
        pieces = {"brief": 100, "d1": 0, "d2": 0, "plan": 0}
        out = renormalize(pieces, target_total=500)
        assert out["d1"] == 0
        assert out["d2"] == 0
        assert out["plan"] == 0
        # brief absorbs the full target.
        assert out["brief"] == 500
