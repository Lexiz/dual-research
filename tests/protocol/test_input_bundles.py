"""Spec 0145 — per-turn input bundles emit canonical artifact IDs.

The legacy 8-key short-vocab (``system``/``brief``/``d1``/``d2``/...) is
replaced by canonical artifact IDs from spec 0117's registry. Producers
emit only the keys that are actually populated for the phase; empty-
string filler slots are gone. Historical bundles are translated on the
read path via the JS shim in ``artifact-display.js``.
"""

from __future__ import annotations

from dual_research.contract.artifacts import is_known
from dual_research.protocol.prompt_pieces import Attachment
from dual_research.protocol.prompts import (
    LEGACY_INPUT_BUNDLE_KEYS,
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


class TestBundleKeysAreCanonical:
    """Every key emitted by a bundle is a recognised artifact ID."""

    def test_preflight(self) -> None:
        b = preflight_input_bundle(brief="B")
        assert set(b.keys()) == {"system.task.input", "user_prompt.message"}
        for k in b:
            assert is_known(k), k

    def test_research(self) -> None:
        b = research_input_bundle(brief="B")
        assert set(b.keys()) == {"system.task.research_plan", "user_prompt.message"}
        for k in b:
            assert is_known(k), k

    def test_negotiation_round1(self) -> None:
        b = negotiation_round1_input_bundle(brief="B", claude_draft="C", openai_draft="O")
        assert set(b.keys()) == {
            "system.task.plan_negotiation",
            "user_prompt.message",
            "phase1.claude",
            "phase1.openai",
        }

    def test_negotiation_turn(self) -> None:
        b = negotiation_turn_input_bundle(
            brief="B", claude_draft="C", openai_draft="O",
            prior_turns=[PriorTurn(agent="claude", round=1, content="x")],
            round=2,
        )
        assert set(b.keys()) == {
            "system.task.plan_negotiation",
            "user_prompt.message",
            "phase1.claude",
            "phase1.openai",
            "prior_turns.phase2",
        }

    def test_drafting(self) -> None:
        b = drafting_input_bundle(
            brief="B", claude_draft="C", openai_draft="O",
            plan="P", prior_turns=[],
        )
        assert set(b.keys()) == {
            "system.task.drafting",
            "user_prompt.message",
            "phase1.claude",
            "phase1.openai",
            "phase2.agreement.plan",
            "prior_turns.phase2",
        }

    def test_review(self) -> None:
        b = review_input_bundle(brief="B", draft="D", prior_turns=[], round=1)
        assert set(b.keys()) == {
            "system.task.review",
            "user_prompt.message",
            "current_draft",
            "prior_turns.phase4",
        }

    def test_repair_phase2(self) -> None:
        b = repair_input_bundle(phase=2, errors=["e"], malformed_content="m")
        assert set(b.keys()) == {"system.task.input", "prior_turns.phase2"}

    def test_repair_phase0(self) -> None:
        b = repair_input_bundle(phase=0, errors=["e"], malformed_content="m")
        assert "prior_turns.phase0" in b

    def test_repair_phase4(self) -> None:
        b = repair_input_bundle(phase=4, errors=["e"], malformed_content="m")
        assert "prior_turns.phase4" in b

    def test_force_verbatim_copy(self) -> None:
        b = force_verbatim_copy_input_bundle(canonical_plan="P", round=3)
        assert set(b.keys()) == {"system.task.plan_negotiation", "phase2.agreement.plan"}


class TestAttachmentRows:
    """Spec 0145 §5.1 — `attachments` threads through bundle producers
    and emits one `user_prompt.attachment.<id>` row per attachment."""

    def test_preflight_with_two_text_attachments(self) -> None:
        atts = [
            Attachment(id="a3f4b9c2", title="Spec.md", content="# Heading\n\nbody " * 30),
            Attachment(id="b1e7d8a0", title="Notes.txt", content="x" * 350),
        ]
        b = preflight_input_bundle(brief="B", attachments=atts)
        assert b["user_prompt.attachment.a3f4b9c2"].startswith("# Heading")
        assert b["user_prompt.attachment.b1e7d8a0"] == "x" * 350

    def test_research_with_attachment(self) -> None:
        atts = [Attachment(id="zz", title="z", content="hello")]
        b = research_input_bundle(brief="B", attachments=atts)
        assert b["user_prompt.attachment.zz"] == "hello"

    def test_zero_attachments_emits_only_user_prompt_message(self) -> None:
        b = preflight_input_bundle(brief="B", attachments=())
        attachment_keys = [k for k in b if k.startswith("user_prompt.attachment.")]
        assert attachment_keys == []


class TestSystemText:
    """The system value is the rendered prompt template (no cache marker,
    preamble present, placeholders for inlined content)."""

    def test_no_cache_marker(self) -> None:
        b = preflight_input_bundle(brief="anything")
        assert "<<<CACHE_BREAKPOINT>>>" not in b["system.task.input"]

    def test_preamble_present(self) -> None:
        b = preflight_input_bundle(brief="anything")
        # The IP-preserving epistemic-duty preamble is the first thing in
        # every prompt; presence implies the template renders fully.
        assert "epistemic" in b["system.task.input"]

    def test_placeholder_replaces_brief(self) -> None:
        """Inline content blobs are replaced by a placeholder so the
        Input tab can render each piece separately without duplication."""
        b = preflight_input_bundle(brief="UNIQUE_BRIEF_BODY_42")
        assert "UNIQUE_BRIEF_BODY_42" not in b["system.task.input"]
        assert "UNIQUE_BRIEF_BODY_42" == b["user_prompt.message"]

    def test_phase2_round1_placeholders_for_drafts(self) -> None:
        b = negotiation_round1_input_bundle(
            brief="B_UNIQ", claude_draft="CLAUDE_UNIQ", openai_draft="OPENAI_UNIQ",
        )
        for marker in ("B_UNIQ", "CLAUDE_UNIQ", "OPENAI_UNIQ"):
            assert marker not in b["system.task.plan_negotiation"]


class TestPriorTurnsRendering:
    """The prior-turns text in the bundle is byte-equal to what the
    prompt builder produces (via the same ``_inline_prior_turns`` helper)."""

    def test_phase2_inlines_prior_turn_content(self) -> None:
        prior = [
            PriorTurn(agent="claude", round=1, content="CLAUDE_R1_BODY"),
            PriorTurn(agent="openai", round=1, content="OPENAI_R1_BODY"),
        ]
        b = negotiation_turn_input_bundle(
            brief="B", claude_draft="C", openai_draft="O",
            prior_turns=prior, round=2,
        )
        assert "CLAUDE_R1_BODY" in b["prior_turns.phase2"]
        assert "OPENAI_R1_BODY" in b["prior_turns.phase2"]
        # The section header from `_inline_prior_turns` is also present.
        assert "Prior Phase 2 conversation" in b["prior_turns.phase2"]

    def test_phase4_uses_phase4_prior_key(self) -> None:
        prior = [PriorTurn(agent="claude", round=1, content="P4_BODY")]
        b = review_input_bundle(brief="B", draft="D", prior_turns=prior, round=2)
        assert "P4_BODY" in b["prior_turns.phase4"]


class TestLegacyShimSurface:
    """The `LEGACY_INPUT_BUNDLE_KEYS` tuple is the source of truth for the
    JS read-shim. Pin its membership so any addition is intentional."""

    def test_legacy_keys_are_the_eight_short_vocab_entries(self) -> None:
        assert LEGACY_INPUT_BUNDLE_KEYS == (
            "system", "brief", "d1", "d2", "plan", "hist", "draft", "histp",
        )
