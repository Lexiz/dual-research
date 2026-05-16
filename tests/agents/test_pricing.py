"""Pricing module — token cost + web-search cost (spec 0031)."""

from __future__ import annotations

import pytest

from dual_research.agents.base import TokenUsage
from dual_research.agents.pricing import (
    PRICING,
    compute_cost,
    compute_search_cost,
    lookup_pricing,
)


class TestLookupPricing:
    def test_exact_match(self) -> None:
        assert lookup_pricing("claude-sonnet-4-6") is PRICING["claude-sonnet-4-6"]

    def test_prefix_match(self) -> None:
        """Dated-variant ids should fall through to the stem entry."""
        assert lookup_pricing("claude-sonnet-4-6-20260301") is PRICING["claude-sonnet-4-6"]

    def test_unknown_returns_none(self) -> None:
        assert lookup_pricing("not-a-real-model") is None


class TestComputeCost:
    def test_basic(self) -> None:
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        # claude-sonnet-4-6: $3 in + $15 out per Mtok
        assert compute_cost("claude-sonnet-4-6", usage) == pytest.approx(18.0)

    def test_unknown_returns_zero(self) -> None:
        usage = TokenUsage(input_tokens=1_000_000)
        assert compute_cost("not-a-real-model", usage) == 0.0


class TestWebSearchPricing:
    """Spec 0031 — `web_search_per_request` rate + `compute_search_cost`."""

    @pytest.mark.parametrize(
        "model_id,expected_per_req",
        [
            ("claude-sonnet-4-6", 0.010),
            ("claude-haiku-4-5", 0.010),
            ("gpt-5.5", 0.025),
            ("gpt-5-mini", 0.025),
        ],
    )
    def test_rates_present_for_priced_models(
        self, model_id: str, expected_per_req: float
    ) -> None:
        p = lookup_pricing(model_id)
        assert p is not None
        assert p.web_search_per_request == pytest.approx(expected_per_req)

    def test_compute_search_cost_basic(self) -> None:
        # 5 searches × $0.010 = $0.05
        assert compute_search_cost("claude-sonnet-4-6", 5) == pytest.approx(0.050)
        # 4 searches × $0.025 = $0.10
        assert compute_search_cost("gpt-5.5", 4) == pytest.approx(0.100)

    def test_compute_search_cost_zero_for_unknown_model(self) -> None:
        assert compute_search_cost("not-a-real-model", 10) == 0.0

    def test_compute_search_cost_zero_for_no_searches(self) -> None:
        assert compute_search_cost("claude-sonnet-4-6", 0) == 0.0
        # Negative count is also coerced to 0 (defensive).
        assert compute_search_cost("claude-sonnet-4-6", -3) == 0.0

    def test_does_not_join_compute_cost(self) -> None:
        """`compute_cost` is strictly token-cost — search cost is a
        separate side-channel per spec 0031 D7."""
        usage = TokenUsage(input_tokens=0, output_tokens=0)
        # No tokens spent → token cost is 0, regardless of how many
        # searches happened (search cost lives on compute_search_cost
        # only).
        assert compute_cost("claude-sonnet-4-6", usage) == 0.0
