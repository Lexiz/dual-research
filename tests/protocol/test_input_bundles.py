"""Spec 0033 — per-turn input bundles for the UI Input tab.

These tests assert that ``*_input_bundle()`` siblings produce dicts with
the canonical Tk-vocab key set, and that the ``system`` text is a clean
rendering of the prompt template (no cache marker, preamble present,
placeholders preserved).

Spec 0118 note: the previous bundle-vs-pieces cross-check (sizes can't
drift from text) is gone because the two vocabularies are now deliberately
decoupled — the Input tab keeps the legacy Tk vocab on the bundle side,
while the Consumption tab pieces use spec 0117's canonical artifact IDs.
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


class TestBundleContentKeys:
    """Sanity-check that the bundle includes the expected Tk content keys
    for each phase (the per-phase set of inlined inputs).

    Spec 0118 dropped the previous cross-check against ``pieces_for_*``
    because the two vocabularies no longer share keys; these residual
    assertions still catch bundles that forget to inline a required input.
    """

    def test_drafting_includes_plan(self) -> None:
        b = drafting_input_bundle(
            brief="B", claude_draft="C", openai_draft="O",
            plan="P", prior_turns=[],
        )
        assert "plan" in _content_keys(b)
        # Empty prior still inlines a stub via the prompt builder.
        assert "No prior turns yet" in b["hist"]

    def test_review_uses_histp(self) -> None:
        prior = [PriorTurn(agent="claude", round=1, content="x" * 350)]
        b = review_input_bundle(brief="B", draft="D", prior_turns=prior, round=1)
        # Phase 4 uses `histp` not `hist`.
        assert "histp" in _content_keys(b)


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
