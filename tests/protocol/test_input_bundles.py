"""Spec 0033 — per-turn input bundles for the UI Input tab.

These tests assert that ``*_input_bundle()`` siblings produce dicts with
the canonical Tk-vocab key set, that content keys match the
corresponding ``pieces_for_*`` size dict (so sizes and text can never
drift), and that the ``system`` text is a clean rendering of the prompt
template (no cache marker, preamble present, placeholders preserved).
"""

from __future__ import annotations

from dual_research.protocol.prompts import (
    INPUT_BUNDLE_KEY_ORDER,
    PriorTurn,
    drafting_input_bundle,
    force_verbatim_copy_input_bundle,
    negotiation_round1_input_bundle,
    negotiation_turn_input_bundle,
    preflight_input_bundle,
    repair_input_bundle,
    research_input_bundle,
    review_input_bundle,
)
from dual_research.protocol.prompt_pieces import (
    pieces_for_drafting,
    pieces_for_negotiation_round1,
    pieces_for_negotiation_turn,
    pieces_for_preflight,
    pieces_for_research,
    pieces_for_review,
)


CANONICAL_KEYS = set(INPUT_BUNDLE_KEY_ORDER)


def _content_keys(bundle: dict[str, str]) -> set[str]:
    """Keys whose value is non-empty (i.e. the phase actually inlines them)."""
    return {k for k, v in bundle.items() if v}


class TestBundleKeySetIsCanonical:
    """Every bundle has exactly the eight Tk-vocab keys (system + 7)."""

    def test_preflight(self) -> None:
        b = preflight_input_bundle(brief="B")
        assert set(b.keys()) == CANONICAL_KEYS

    def test_research(self) -> None:
        b = research_input_bundle(brief="B")
        assert set(b.keys()) == CANONICAL_KEYS

    def test_negotiation_round1(self) -> None:
        b = negotiation_round1_input_bundle(brief="B", claude_draft="C", openai_draft="O")
        assert set(b.keys()) == CANONICAL_KEYS

    def test_negotiation_turn(self) -> None:
        b = negotiation_turn_input_bundle(
            brief="B", claude_draft="C", openai_draft="O",
            prior_turns=[PriorTurn(agent="claude", round=1, content="x")],
            round=2,
        )
        assert set(b.keys()) == CANONICAL_KEYS

    def test_drafting(self) -> None:
        b = drafting_input_bundle(
            brief="B", claude_draft="C", openai_draft="O",
            plan="P", prior_turns=[],
        )
        assert set(b.keys()) == CANONICAL_KEYS

    def test_review(self) -> None:
        b = review_input_bundle(brief="B", draft="D", prior_turns=[], round=1)
        assert set(b.keys()) == CANONICAL_KEYS

    def test_repair(self) -> None:
        b = repair_input_bundle(phase=2, errors=["e"], malformed_content="m")
        assert set(b.keys()) == CANONICAL_KEYS

    def test_force_verbatim_copy(self) -> None:
        b = force_verbatim_copy_input_bundle(canonical_plan="P", round=3)
        assert set(b.keys()) == CANONICAL_KEYS


class TestContentKeysMatchPieces:
    """The cross-check: bundle's non-empty Tk keys equal pieces_for_*'s keys.

    This is the test that prevents sizes-vs-text drift. ``system`` is added
    by the bundle (no analogue on the sizes side) and is excluded from the
    comparison.
    """

    def test_preflight(self) -> None:
        b = preflight_input_bundle(brief="B")
        pieces = pieces_for_preflight(brief="B")
        assert _content_keys(b) - {"system"} == set(pieces.keys())

    def test_research(self) -> None:
        b = research_input_bundle(brief="B")
        pieces = pieces_for_research(brief="B")
        assert _content_keys(b) - {"system"} == set(pieces.keys())

    def test_negotiation_round1(self) -> None:
        b = negotiation_round1_input_bundle(brief="B", claude_draft="C", openai_draft="O")
        pieces = pieces_for_negotiation_round1(brief="B", claude_draft="C", openai_draft="O")
        assert _content_keys(b) - {"system"} == set(pieces.keys())

    def test_negotiation_turn_with_history(self) -> None:
        prior = [PriorTurn(agent="claude", round=1, content="x" * 350)]
        b = negotiation_turn_input_bundle(
            brief="B", claude_draft="C", openai_draft="O",
            prior_turns=prior, round=2,
        )
        pieces = pieces_for_negotiation_turn(
            brief="B", claude_draft="C", openai_draft="O", prior_turns=prior,
        )
        # `pieces_for_negotiation_turn` always emits a `hist` key (zero
        # when prior is empty); the bundle's `hist` is non-empty when
        # there's prior content. Equality holds when both are non-empty.
        non_zero_pieces = {k for k, v in pieces.items() if v}
        assert _content_keys(b) - {"system"} == non_zero_pieces

    def test_drafting_includes_plan(self) -> None:
        b = drafting_input_bundle(
            brief="B", claude_draft="C", openai_draft="O",
            plan="P", prior_turns=[],
        )
        # The bundle has `plan` because we pass one in. `hist` still
        # carries the "(No prior turns yet.)" stub the prompt builder
        # emits — the bundle deliberately mirrors what the model saw,
        # not the heuristic char-count from pieces_for_*.
        assert "plan" in _content_keys(b)
        assert "No prior turns yet" in b["hist"]

    def test_review(self) -> None:
        prior = [PriorTurn(agent="claude", round=1, content="x" * 350)]
        b = review_input_bundle(brief="B", draft="D", prior_turns=prior, round=1)
        pieces = pieces_for_review(brief="B", draft="D", prior_turns=prior)
        # Phase 4 uses `histp` not `hist`; check it shows up in the bundle.
        assert "histp" in _content_keys(b)
        non_zero_pieces = {k for k, v in pieces.items() if v}
        assert _content_keys(b) - {"system"} == non_zero_pieces


class TestSystemText:
    """The system value is the rendered prompt template (no cache marker,
    preamble present, placeholders for inlined content)."""

    def test_no_cache_marker(self) -> None:
        b = preflight_input_bundle(brief="anything")
        assert "<<<CACHE_BREAKPOINT>>>" not in b["system"]

    def test_preamble_present(self) -> None:
        b = preflight_input_bundle(brief="anything")
        # The IP-preserving epistemic-duty preamble is the first thing in
        # every prompt; presence implies the template renders fully.
        assert "epistemic" in b["system"]

    def test_placeholder_replaces_brief(self) -> None:
        """Inline content blobs are replaced by a placeholder so the
        Input tab can render each piece separately without duplication."""
        b = preflight_input_bundle(brief="UNIQUE_BRIEF_BODY_42")
        assert "UNIQUE_BRIEF_BODY_42" not in b["system"]
        assert "UNIQUE_BRIEF_BODY_42" == b["brief"]

    def test_phase2_round1_placeholders_for_drafts(self) -> None:
        b = negotiation_round1_input_bundle(
            brief="B_UNIQ", claude_draft="CLAUDE_UNIQ", openai_draft="OPENAI_UNIQ",
        )
        for marker in ("B_UNIQ", "CLAUDE_UNIQ", "OPENAI_UNIQ"):
            assert marker not in b["system"]


class TestPhase2HistRendering:
    """The `hist` text in the bundle is byte-equal to what the prompt
    builder produces (via the same ``_inline_prior_turns`` helper)."""

    def test_inlines_prior_turn_content(self) -> None:
        prior = [
            PriorTurn(agent="claude", round=1, content="CLAUDE_R1_BODY"),
            PriorTurn(agent="openai", round=1, content="OPENAI_R1_BODY"),
        ]
        b = negotiation_turn_input_bundle(
            brief="B", claude_draft="C", openai_draft="O",
            prior_turns=prior, round=2,
        )
        assert "CLAUDE_R1_BODY" in b["hist"]
        assert "OPENAI_R1_BODY" in b["hist"]
        # The section header from `_inline_prior_turns` is also present.
        assert "Prior Phase 2 conversation" in b["hist"]
