"""Spec 0145 — per-piece token-size estimators emit canonical artifact IDs.

Every key emitted by ``pieces_for_*`` must be a recognised artifact ID
in spec 0117's registry (``dual_research.contract.artifacts``). The
``TestRegistryMembership`` class is the regression that catches drift.
The single ``user_prompt`` aggregate key is replaced by
``user_prompt.message`` plus zero-or-more ``user_prompt.attachment.<id>``
rows; ``TestAttachmentDecomposition`` pins that behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass

from dual_research.contract.artifacts import is_known
from dual_research.protocol.prompt_pieces import (
    Attachment,
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
        pieces = pieces_for_preflight(system_task="sys", user_prompt_message="brief")
        assert set(pieces.keys()) == {"system.task.input", "user_prompt.message"}
        assert pieces["system.task.input"] > 0
        assert pieces["user_prompt.message"] > 0

    def test_round_n_with_history_and_ledger_and_closeout(self) -> None:
        pieces = pieces_for_preflight(
            system_task="sys",
            user_prompt_message="brief",
            prior_turns=[
                _Turn("claude", 1, "a" * 350),
                _Turn("openai", 1, "b" * 350),
            ],
            ledger="standing items text",
            closeout_request="closeout text",
        )
        assert set(pieces.keys()) == {
            "system.task.input",
            "user_prompt.message",
            "prior_turns.phase0",
            "ledger.standing_items",
            "closeout.request",
        }
        # 700 chars / 3.5 = 200
        assert pieces["prior_turns.phase0"] == 200

    def test_empty_prior_omits_key(self) -> None:
        pieces = pieces_for_preflight(
            system_task="s", user_prompt_message="b", prior_turns=[],
        )
        assert "prior_turns.phase0" not in pieces


class TestPhase1ResearchPlan:
    def test_emits_three_canonical_keys(self) -> None:
        pieces = pieces_for_research_plan(
            system_task="sys",
            user_prompt_message="brief",
            agreed_interpretation="interp",
        )
        assert set(pieces.keys()) == {
            "system.task.research_plan",
            "user_prompt.message",
            "phase0.agreement.interpretation",
        }


class TestPhase2PlanNegotiation:
    def test_round1_no_prior_turns(self) -> None:
        pieces = pieces_for_plan_negotiation(
            system_task="sys",
            user_prompt_message="brief",
            agreed_interpretation="interp",
            phase1_claude="claude plan",
            phase1_openai="gpt plan",
        )
        assert set(pieces.keys()) == {
            "system.task.plan_negotiation",
            "user_prompt.message",
            "phase0.agreement.interpretation",
            "phase1.claude",
            "phase1.openai",
        }
        assert "prior_turns.phase2" not in pieces

    def test_round_n_with_history_ledger_closeout(self) -> None:
        pieces = pieces_for_plan_negotiation(
            system_task="sys",
            user_prompt_message="brief",
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
            user_prompt_message="brief",
            agreed_interpretation="interp",
            phase1_claude="claude plan",
            phase1_openai="gpt plan",
            agreed_plan="plan body",
            all_p2_turns=[_Turn("claude", 1, "x" * 700)],
            carry_forward="cf body",
        )
        assert set(pieces.keys()) == {
            "system.task.drafting",
            "user_prompt.message",
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
            user_prompt_message="b",
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
            system_task="sys", user_prompt_message="brief", current_draft="draft body",
        )
        assert set(pieces.keys()) == {
            "system.task.review",
            "user_prompt.message",
            "current_draft",
        }

    def test_round_n_with_history_ledger_closeout(self) -> None:
        pieces = pieces_for_review(
            system_task="sys",
            user_prompt_message="brief",
            current_draft="draft",
            prior_turns=[_Turn("openai", 1, "z" * 700)],
            ledger="ledger",
            closeout_request="closeout",
        )
        assert {"prior_turns.phase4", "ledger.standing_items", "closeout.request"} <= set(pieces.keys())
        assert pieces["prior_turns.phase4"] == 200


class TestAttachmentDecomposition:
    """Spec 0145 §5.1 — `user_prompt` is decomposed into `user_prompt.message`
    plus one `user_prompt.attachment.<id>` row per attachment."""

    def test_zero_attachments_emits_no_attachment_rows(self) -> None:
        pieces = pieces_for_preflight(
            system_task="sys",
            user_prompt_message="brief",
            attachments=(),
        )
        assert "user_prompt.message" in pieces
        assert not any(k.startswith("user_prompt.attachment.") for k in pieces)
        # The legacy aggregate `user_prompt` key is never emitted by the
        # new producer; only the read-shim resolves it for historical
        # data on the JS side.
        assert "user_prompt" not in pieces

    def test_two_attachments_emit_two_canonical_rows(self) -> None:
        atts = [
            Attachment(id="a", title="Foo", content="hello world " * 20),
            Attachment(id="b", title="Bar", content="x" * 350),
        ]
        pieces = pieces_for_preflight(
            system_task="sys",
            user_prompt_message="brief",
            attachments=atts,
        )
        assert "user_prompt.attachment.a" in pieces
        assert "user_prompt.attachment.b" in pieces
        assert pieces["user_prompt.attachment.b"] == 100  # 350 / 3.5

    def test_attachment_ordering_matches_input_order(self) -> None:
        atts = [
            Attachment(id="z", title="z", content="x"),
            Attachment(id="a", title="a", content="x"),
            Attachment(id="m", title="m", content="x"),
        ]
        pieces = pieces_for_preflight(
            system_task="sys",
            user_prompt_message="brief",
            attachments=atts,
        )
        attachment_keys = [k for k in pieces if k.startswith("user_prompt.attachment.")]
        assert attachment_keys == [
            "user_prompt.attachment.z",
            "user_prompt.attachment.a",
            "user_prompt.attachment.m",
        ]

    def test_idempotency_across_repeated_calls(self) -> None:
        atts = [Attachment(id="a", title="A", content="payload")]
        kw = dict(system_task="sys", user_prompt_message="brief", attachments=atts)
        first = pieces_for_preflight(**kw)
        second = pieces_for_preflight(**kw)
        assert first == second

    def test_binary_attachment_with_empty_content_contributes_zero(self) -> None:
        atts = [Attachment(id="bin", title="binary.pdf", content="")]
        pieces = pieces_for_preflight(
            system_task="sys",
            user_prompt_message="brief",
            attachments=atts,
        )
        assert pieces["user_prompt.attachment.bin"] == 0

    def test_attachment_keys_are_registry_known(self) -> None:
        atts = [
            Attachment(id="abc123", title="A", content="x"),
            Attachment(id="def456", title="B", content="x"),
        ]
        pieces = pieces_for_preflight(
            system_task="sys",
            user_prompt_message="brief",
            attachments=atts,
        )
        for key in pieces:
            assert is_known(key), f"unknown artifact ID: {key!r}"


class TestRegistryMembership:
    """Every emitted key must exist in spec 0117's artifact registry.

    Regression that catches drift between this module and the registry.
    """

    def test_preflight_keys_in_registry(self) -> None:
        pieces = pieces_for_preflight(
            system_task="s",
            user_prompt_message="u",
            prior_turns=[_Turn("c", 1, "x" * 10)],
            ledger="l",
            closeout_request="c",
        )
        for k in pieces:
            assert is_known(k), f"unknown artifact ID: {k!r}"

    def test_research_plan_keys_in_registry(self) -> None:
        pieces = pieces_for_research_plan(
            system_task="s", user_prompt_message="u", agreed_interpretation="i",
        )
        for k in pieces:
            assert is_known(k), f"unknown artifact ID: {k!r}"

    def test_plan_negotiation_keys_in_registry(self) -> None:
        pieces = pieces_for_plan_negotiation(
            system_task="s",
            user_prompt_message="u",
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
            user_prompt_message="u",
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
            user_prompt_message="u",
            current_draft="d",
            prior_turns=[_Turn("c", 1, "x" * 10)],
            ledger="l",
            closeout_request="c",
        )
        for k in pieces:
            assert is_known(k), f"unknown artifact ID: {k!r}"


class TestSumInvariant:
    """Spec 0145 §7.3 — the sum of all piece tokens (post-decomposition)
    equals the legacy aggregate `user_prompt` value for the no-attachment
    case. Guarantees no token-counting regression for the anchor run."""

    def test_no_attachment_sum_matches_legacy_aggregate(self) -> None:
        pieces = pieces_for_preflight(
            system_task="sys" * 100,
            user_prompt_message="brief" * 100,
            prior_turns=[_Turn("c", 1, "x" * 700)],
            ledger="ledger" * 50,
        )
        # Pre-spec, `user_prompt` carried estimate_tokens("brief" * 100).
        # Post-spec, `user_prompt.message` carries the same value (no
        # attachments) and the other rows are unchanged.
        assert pieces["user_prompt.message"] == estimate_tokens("brief" * 100)


class TestRenormalize:
    def test_sums_to_target(self) -> None:
        pieces = {"user_prompt.message": 100, "phase1.claude": 200, "phase1.openai": 100}
        out = renormalize(pieces, target_total=1000)
        # 400 raw → 1000 target, scale 2.5. Allow rounding drift ±1 token
        # per piece.
        assert abs(out["user_prompt.message"] - 250) <= 1
        assert abs(out["phase1.claude"] - 500) <= 1
        assert abs(out["phase1.openai"] - 250) <= 1

    def test_zero_target_passes_through(self) -> None:
        pieces = {"user_prompt.message": 100, "phase1.claude": 50}
        assert renormalize(pieces, target_total=0) == pieces

    def test_all_zero_pieces_unchanged(self) -> None:
        pieces = {"user_prompt.message": 0, "phase1.claude": 0}
        assert renormalize(pieces, target_total=1000) == pieces

    def test_zero_entries_stay_zero(self) -> None:
        pieces = {"user_prompt.message": 100, "phase1.claude": 0, "phase1.openai": 0}
        out = renormalize(pieces, target_total=500)
        assert out["phase1.claude"] == 0
        assert out["phase1.openai"] == 0
        # The non-zero piece absorbs the full target.
        assert out["user_prompt.message"] == 500
