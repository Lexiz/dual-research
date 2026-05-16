"""Spec 0032 — Phase 2 hash-drift escape.

`all_substantive_gates_pass_except_plan_hash` detects the "agreed on
everything except the AGREED_PLAN hash" state — the exact failure mode
that caused the web-components-catalogue test run to loop until manual
stop.
"""

from __future__ import annotations

from dual_research.protocol.convergence import (
    PlanHashDrift,
    all_substantive_gates_pass_except_plan_hash,
    normalized_hash,
)
from tests.protocol.fixtures import (
    CANONICAL_AGREED_PLAN,
    plan_turn_agreed,
)


# A second valid plan body that hashes differently from CANONICAL_AGREED_PLAN.
# Same structure, paraphrased content — mirrors what the failing test run saw.
PARAPHRASED_AGREED_PLAN = """1. **Title:** Background
   **Key claims:**
   - Topic X has changed materially in the past 18 months because of regulation Y.

2. **Title:** Analysis
   **Key claims:**
   - Approach A wins over B on metric M for use-case U.

3. **Title:** Recommendation
   **Key claims:**
   - Pick A; note caveat C.
"""


def _turn_with_plan(plan: str, *, drafter: str = "claude") -> str:
    """Replace the canonical plan block inside PLAN_TURN_AGREED with `plan`."""
    return plan_turn_agreed(drafter=drafter).replace(CANONICAL_AGREED_PLAN, plan)


class TestHashDriftDetection:
    def test_detected_when_only_hashes_differ(self) -> None:
        claude = plan_turn_agreed(drafter="claude")  # uses CANONICAL plan
        openai = _turn_with_plan(PARAPHRASED_AGREED_PLAN, drafter="claude")
        drift = all_substantive_gates_pass_except_plan_hash(claude, openai)
        assert drift.detected
        assert drift.drafter == "claude"
        # Drafter is claude → canonical plan is claude's plan (hash-equal to
        # the fixture). `parse_turn`'s extracted section can carry trailing
        # whitespace differences; hash-compare to match the convergence-gate
        # contract instead.
        assert normalized_hash(drift.canonical_plan) == normalized_hash(CANONICAL_AGREED_PLAN)
        # Non-drafter is gpt → that's the one to repair.
        assert drift.other_agent == "gpt"
        # Hashes are distinct, both populated.
        assert drift.canonical_hash and drift.other_hash
        assert drift.canonical_hash != drift.other_hash

    def test_not_detected_when_plans_match(self) -> None:
        """The success path of is_plan_agreed must NOT fire as drift."""
        claude = plan_turn_agreed(drafter="claude")
        openai = plan_turn_agreed(drafter="claude")
        drift = all_substantive_gates_pass_except_plan_hash(claude, openai)
        assert not drift.detected

    def test_not_detected_when_drafters_disagree(self) -> None:
        """That case is handled by all_substantive_gates_pass_except_drafter,
        not the new helper. Drafter mismatch + hash mismatch → return False
        from the new helper so the drafter-tiebreak path wins."""
        claude = plan_turn_agreed(drafter="claude")
        openai = _turn_with_plan(PARAPHRASED_AGREED_PLAN, drafter="gpt")
        drift = all_substantive_gates_pass_except_plan_hash(claude, openai)
        assert not drift.detected

    def test_not_detected_when_one_side_negotiating(self) -> None:
        """If either turn isn't AGREED, drift doesn't apply yet."""
        from tests.protocol.fixtures import PLAN_TURN_NEGOTIATING
        claude = plan_turn_agreed(drafter="claude")
        openai = PLAN_TURN_NEGOTIATING
        drift = all_substantive_gates_pass_except_plan_hash(claude, openai)
        assert not drift.detected

    def test_canonical_plan_is_openai_when_drafter_is_gpt(self) -> None:
        """The named drafter's plan is canonical — even when that's gpt."""
        # Both turns agree drafter=gpt, but each has its own plan body.
        claude = _turn_with_plan(PARAPHRASED_AGREED_PLAN, drafter="gpt")
        openai = plan_turn_agreed(drafter="gpt")  # canonical plan
        drift = all_substantive_gates_pass_except_plan_hash(claude, openai)
        assert drift.detected
        assert drift.drafter == "gpt"
        assert normalized_hash(drift.canonical_plan) == normalized_hash(CANONICAL_AGREED_PLAN)
        assert drift.other_agent == "claude"


class TestPlanHashDriftDataclass:
    def test_default_undetected_state(self) -> None:
        d = PlanHashDrift(detected=False)
        assert d.detected is False
        assert d.drafter is None
        assert d.canonical_plan is None
        assert d.other_agent is None
        assert d.canonical_hash is None
        assert d.other_hash is None
