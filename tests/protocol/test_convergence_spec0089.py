"""Spec 0089 — convergence escape hatches for stuck-AGREED loops.

Covers:
  - § A canonical-FSD synthesis: helper detection + synthesis + splice.
  - § B lenient checks: is_plan_agreed_lenient + is_review_approved_lenient.

The blocked-convergence warning text helper (§ C) lives in
`ledger/prompt.py` and is tested in `tests/ledger/test_prompt.py`.
"""

from __future__ import annotations

import pytest

from dual_research.protocol.convergence import (
    CanonicalFsdMissing,
    CanonicalFsdSynthesisError,
    all_substantive_gates_pass_except_canonical_fsd,
    is_plan_agreed,
    is_plan_agreed_lenient,
    is_review_approved,
    is_review_approved_lenient,
    normalized_hash,
    splice_canonical_into_agreed_plan,
    synthesize_canonical_fsd_section_from_standalone,
)
from tests.protocol.fixtures import (
    CANONICAL_AGREED_PLAN,
    REVIEW_TURN_APPROVED,
    REVIEW_TURN_REVIEWING,
    plan_turn_agreed,
)


# ─── Test fixtures: AGREED turns with FSDs ──────────────────────────────────


STANDALONE_FSD_ONE = """## Final-surfaced disagreements

### FSD-1: scope of caveat C

- Claude position: limited to enterprise tier
- GPT position: applies to all tiers
- Evidence for Claude position: industry survey citing tier-specific adoption
- Evidence for GPT position: regulatory note covering all tiers
- Why this could not or should not be resolved within this run: requires field interviews beyond run scope
- Why this is still material to the final document: changes recommended deployment shape
- Exact final-document treatment: state both positions; recommend enterprise-only as starting point
- Does this affect the final recommendation? yes
"""


CANONICAL_FSD_SECTION_ONE = """## Final-surfaced disagreements (canonical)

### FSD-1: scope of caveat C

- Claude position: limited to enterprise tier
- GPT position: applies to all tiers
- Exact final-document treatment: state both positions; recommend enterprise-only as starting point
- Affects final recommendation? yes
"""


STANDALONE_FSD_TWO = """## Final-surfaced disagreements

### FSD-1: scope of caveat C

- Claude position: limited to enterprise tier
- GPT position: applies to all tiers
- Evidence for Claude position: industry survey
- Evidence for GPT position: regulatory note
- Why this could not or should not be resolved within this run: needs interviews
- Why this is still material to the final document: changes deployment shape
- Exact final-document treatment: present both positions; recommend enterprise-only
- Does this affect the final recommendation? yes

### FSD-2: timeline for adoption

- Claude position: 6-month rollout
- GPT position: 12-month rollout
- Evidence for Claude position: vendor benchmarks
- Evidence for GPT position: case studies from peer companies
- Why this could not or should not be resolved within this run: depends on internal staffing
- Why this is still material to the final document: affects planning sections
- Exact final-document treatment: present both timelines; ask the reader to pick based on internal capacity
- Does this affect the final recommendation? no
"""


def _agreed_turn_with_fsd(
    *,
    drafter: str = "claude",
    fsd_count: int,
    standalone_section: str | None,
    canonical_section_in_plan: str | None,
) -> str:
    """Build an AGREED plan turn with controllable FSD bits.

    `standalone_section` — pasted under "## Final-surfaced disagreements"
    inside the turn body (replaces the `(none)`/zero-FSD wording).
    `canonical_section_in_plan` — emitted as a top-level ``## Final-surfaced
    disagreements (canonical)`` section in the turn body (sibling to
    ``## AGREED_PLAN``), matching real agent output and the parse-turn
    truncation semantics documented in spec 0089. None means "agents
    did NOT emit the canonical sub-section" — the failure mode the
    § A escape exists to recover from.
    `fsd_count` — what FINAL_SURFACED_DISAGREEMENTS: N reports.
    """
    base = plan_turn_agreed(drafter=drafter)
    out = base.replace(
        "FINAL_SURFACED_DISAGREEMENTS: 0",
        f"FINAL_SURFACED_DISAGREEMENTS: {fsd_count}",
    )
    if standalone_section is not None:
        # Insert right before "## Drafter recommendation"
        out = out.replace(
            "## Drafter recommendation",
            standalone_section + "\n## Drafter recommendation",
        )
    if canonical_section_in_plan is not None:
        # Top-level sibling to ## AGREED_PLAN. Inserted just before
        # ## Drafter recommendation so it sits between AGREED_PLAN's
        # closing and the drafter recommendation block — exactly the
        # spot real agents emit it.
        out = out.replace(
            "## Drafter recommendation",
            canonical_section_in_plan.rstrip() + "\n\n## Drafter recommendation",
        )
    return out


# ─── § A: detection helper ──────────────────────────────────────────────────


class TestSpec0089AllSubstantiveGatesPassExceptCanonicalFsd:
    def test_detected_when_canonical_missing_and_standalone_matches(self) -> None:
        # The 2c4f failure mode exactly: both AGREED, matching plan hash,
        # matching standalone FSD IDs, but the AGREED_PLAN block lacks
        # the ## Final-surfaced disagreements (canonical) sub-section.
        claude = _agreed_turn_with_fsd(
            drafter="claude",
            fsd_count=1,
            standalone_section=STANDALONE_FSD_ONE,
            canonical_section_in_plan=None,
        )
        openai = _agreed_turn_with_fsd(
            drafter="claude",
            fsd_count=1,
            standalone_section=STANDALONE_FSD_ONE,
            canonical_section_in_plan=None,
        )
        gap = all_substantive_gates_pass_except_canonical_fsd(claude, openai)
        assert gap.detected
        assert gap.drafter == "claude"
        assert gap.fsd_ids == ("FSD-1",)
        assert gap.canonical_plan is not None
        assert gap.synthesized_section is not None
        assert "FSD-1" in gap.synthesized_section
        assert "Affects final recommendation?" in gap.synthesized_section

    def test_not_detected_when_canonical_is_already_present(self) -> None:
        # When both plans already have the canonical sub-section,
        # is_plan_agreed should pass — this escape isn't the right fix.
        claude = _agreed_turn_with_fsd(
            drafter="claude", fsd_count=1,
            standalone_section=STANDALONE_FSD_ONE,
            canonical_section_in_plan=CANONICAL_FSD_SECTION_ONE,
        )
        openai = _agreed_turn_with_fsd(
            drafter="claude", fsd_count=1,
            standalone_section=STANDALONE_FSD_ONE,
            canonical_section_in_plan=CANONICAL_FSD_SECTION_ONE,
        )
        gap = all_substantive_gates_pass_except_canonical_fsd(claude, openai)
        assert not gap.detected

    def test_not_detected_when_fsd_count_zero(self) -> None:
        # FSD=0 means no canonical sub-section is required by the protocol;
        # this escape doesn't apply (is_plan_agreed would succeed if other
        # gates pass).
        claude = plan_turn_agreed(drafter="claude")  # default FSD=0
        openai = plan_turn_agreed(drafter="claude")
        gap = all_substantive_gates_pass_except_canonical_fsd(claude, openai)
        assert not gap.detected

    def test_not_detected_when_standalone_ids_mismatch(self) -> None:
        # Claude reports FSD-1; gpt's standalone has FSD-2 — real disagreement,
        # not a missing-canonical case.
        claude = _agreed_turn_with_fsd(
            drafter="claude", fsd_count=1,
            standalone_section=STANDALONE_FSD_ONE,
            canonical_section_in_plan=None,
        )
        # Swap FSD-1 IDs out for FSD-2 in the OTHER agent's standalone.
        other_standalone = STANDALONE_FSD_ONE.replace("FSD-1", "FSD-2")
        openai = _agreed_turn_with_fsd(
            drafter="claude", fsd_count=1,
            standalone_section=other_standalone,
            canonical_section_in_plan=None,
        )
        gap = all_substantive_gates_pass_except_canonical_fsd(claude, openai)
        assert not gap.detected

    def test_not_detected_when_one_side_negotiating(self) -> None:
        from tests.protocol.fixtures import PLAN_TURN_NEGOTIATING
        agreed = _agreed_turn_with_fsd(
            drafter="claude", fsd_count=1,
            standalone_section=STANDALONE_FSD_ONE,
            canonical_section_in_plan=None,
        )
        gap = all_substantive_gates_pass_except_canonical_fsd(
            agreed, PLAN_TURN_NEGOTIATING,
        )
        assert not gap.detected


# ─── § A: synthesise + splice helpers ───────────────────────────────────────


class TestSpec0089SynthesizeCanonicalFsdFromStandalone:
    def test_synthesises_single_fsd(self) -> None:
        out = synthesize_canonical_fsd_section_from_standalone(
            STANDALONE_FSD_ONE
        )
        assert "## Final-surfaced disagreements (canonical)" in out
        assert "### FSD-1: scope of caveat C" in out
        assert "- Claude position: limited to enterprise tier" in out
        assert "- GPT position: applies to all tiers" in out
        assert "- Exact final-document treatment: state both positions" in out
        assert "- Affects final recommendation? yes" in out
        # Does NOT include the standalone-only fields.
        assert "Evidence for Claude position" not in out
        assert "Why this could not or should not be resolved" not in out

    def test_synthesises_multiple_fsds_preserving_order(self) -> None:
        out = synthesize_canonical_fsd_section_from_standalone(
            STANDALONE_FSD_TWO
        )
        fsd1_idx = out.index("FSD-1")
        fsd2_idx = out.index("FSD-2")
        assert fsd1_idx < fsd2_idx
        assert "Affects final recommendation? yes" in out  # FSD-1
        assert "Affects final recommendation? no" in out   # FSD-2

    def test_restricts_to_requested_ids(self) -> None:
        out = synthesize_canonical_fsd_section_from_standalone(
            STANDALONE_FSD_TWO, fsd_ids=("FSD-2",),
        )
        assert "FSD-2" in out
        assert "FSD-1" not in out

    def test_raises_when_required_field_missing(self) -> None:
        broken = STANDALONE_FSD_ONE.replace(
            "- Exact final-document treatment: state both positions; recommend enterprise-only as starting point\n",
            "",
        )
        with pytest.raises(CanonicalFsdSynthesisError) as exc:
            synthesize_canonical_fsd_section_from_standalone(broken)
        assert "Exact final-document treatment" in str(exc.value)

    def test_raises_on_empty_section(self) -> None:
        with pytest.raises(CanonicalFsdSynthesisError):
            synthesize_canonical_fsd_section_from_standalone("")
        with pytest.raises(CanonicalFsdSynthesisError):
            synthesize_canonical_fsd_section_from_standalone("   \n\n")

    def test_idempotent(self) -> None:
        once = synthesize_canonical_fsd_section_from_standalone(
            STANDALONE_FSD_ONE
        )
        twice = synthesize_canonical_fsd_section_from_standalone(once)
        assert once == twice

    def test_raises_when_requested_id_missing(self) -> None:
        with pytest.raises(CanonicalFsdSynthesisError) as exc:
            synthesize_canonical_fsd_section_from_standalone(
                STANDALONE_FSD_ONE, fsd_ids=("FSD-99",),
            )
        assert "FSD-99" in str(exc.value)


class TestSpec0089SpliceCanonicalIntoAgreedPlan:
    def test_appends_when_no_canonical_section_exists(self) -> None:
        result = splice_canonical_into_agreed_plan(
            CANONICAL_AGREED_PLAN, CANONICAL_FSD_SECTION_ONE,
        )
        assert "## Final-surfaced disagreements (canonical)" in result
        # Plan content preserved.
        assert "1. **Title:** Background" in result
        assert "Adopt A with caveat C." in result

    def test_idempotent_when_canonical_already_present(self) -> None:
        plan_with = splice_canonical_into_agreed_plan(
            CANONICAL_AGREED_PLAN, CANONICAL_FSD_SECTION_ONE,
        )
        plan_with_again = splice_canonical_into_agreed_plan(
            plan_with, CANONICAL_FSD_SECTION_ONE,
        )
        # Hash equivalence is what matters for the convergence check.
        assert normalized_hash(plan_with) == normalized_hash(plan_with_again)

    def test_replaces_existing_canonical_section(self) -> None:
        plan_v1 = splice_canonical_into_agreed_plan(
            CANONICAL_AGREED_PLAN, CANONICAL_FSD_SECTION_ONE,
        )
        # Splice in a different canonical (e.g., with a different title).
        canonical_v2 = CANONICAL_FSD_SECTION_ONE.replace(
            "scope of caveat C", "scope of caveat C (v2)",
        )
        plan_v2 = splice_canonical_into_agreed_plan(plan_v1, canonical_v2)
        assert "(v2)" in plan_v2
        # The v1 title should be gone from the canonical section. Original
        # plan content (Background, Analysis, Recommendation) preserved.
        # We accept the v1 title still appearing elsewhere only if no
        # original plan section happens to use it — which it doesn't.
        assert plan_v2.count("scope of caveat C (v2)") == 1


# ─── § B: lenient convergence checks ────────────────────────────────────────


class TestSpec0089IsPlanAgreedLenient:
    def test_passes_when_strict_passes(self) -> None:
        claude = plan_turn_agreed(drafter="claude")
        openai = plan_turn_agreed(drafter="claude")
        assert is_plan_agreed(claude, openai, ledger_open_count=0)
        assert is_plan_agreed_lenient(claude, openai)

    def test_passes_when_only_ledger_blocks(self) -> None:
        # Exactly the 27de scenario: agents fully aligned, ledger says 10
        # questions are still open.
        claude = plan_turn_agreed(drafter="claude")
        openai = plan_turn_agreed(drafter="claude")
        assert not is_plan_agreed(claude, openai, ledger_open_count=10)
        assert is_plan_agreed_lenient(claude, openai)

    def test_fails_on_real_drafter_mismatch(self) -> None:
        claude = plan_turn_agreed(drafter="claude")
        openai = plan_turn_agreed(drafter="gpt")
        assert not is_plan_agreed_lenient(claude, openai)

    def test_fails_on_hash_mismatch(self) -> None:
        # Reuse the hash-drift fixture pattern: same outer shape, different
        # plan body → different normalised hashes.
        from tests.protocol.test_convergence_hash_drift import PARAPHRASED_AGREED_PLAN
        claude = plan_turn_agreed(drafter="claude")
        openai = plan_turn_agreed(drafter="claude").replace(
            CANONICAL_AGREED_PLAN, PARAPHRASED_AGREED_PLAN,
        )
        assert not is_plan_agreed_lenient(claude, openai)

    def test_fails_when_one_side_negotiating(self) -> None:
        from tests.protocol.fixtures import PLAN_TURN_NEGOTIATING
        claude = plan_turn_agreed(drafter="claude")
        assert not is_plan_agreed_lenient(claude, PLAN_TURN_NEGOTIATING)


class TestSpec0089IsReviewApprovedLenient:
    def test_passes_when_strict_passes(self) -> None:
        assert is_review_approved(
            REVIEW_TURN_APPROVED, REVIEW_TURN_APPROVED,
            round=1, ledger_open_count=0,
        )
        assert is_review_approved_lenient(
            REVIEW_TURN_APPROVED, REVIEW_TURN_APPROVED, round=1,
        )

    def test_passes_when_only_ledger_blocks(self) -> None:
        # Strict blocks because ledger_open_count > 0; lenient ignores it.
        assert not is_review_approved(
            REVIEW_TURN_APPROVED, REVIEW_TURN_APPROVED,
            round=1, ledger_open_count=5,
        )
        assert is_review_approved_lenient(
            REVIEW_TURN_APPROVED, REVIEW_TURN_APPROVED, round=1,
        )

    def test_fails_when_one_side_reviewing(self) -> None:
        assert not is_review_approved_lenient(
            REVIEW_TURN_APPROVED, REVIEW_TURN_REVIEWING, round=1,
        )


class TestSpec0089CanonicalFsdMissingDataclass:
    def test_default_undetected_state(self) -> None:
        m = CanonicalFsdMissing(detected=False)
        assert m.detected is False
        assert m.drafter is None
        assert m.canonical_plan is None
        assert m.synthesized_section is None
        assert m.fsd_ids == ()
