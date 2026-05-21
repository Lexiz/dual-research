"""Pricing module — token cost + web-search cost (spec 0031 + 0039)."""

from __future__ import annotations

import pytest

from dual_research.agents.base import TokenUsage
from dual_research.agents.pricing import (
    CACHE_WRITE_1H_MULTIPLIER,
    CACHE_WRITE_5M_MULTIPLIER,
    PRICING,
    compute_cost,
    compute_full_cost,
    compute_search_cost,
    compute_token_cost,
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
            # Spec 0143 — GPT-5.5 search rate bumped from $0.025 to $0.010
            # to match OpenAI's published $10/1k and the anchor-run invoice
            # ratio (19 × $0.010 = $0.19 vs invoice $0.17, within rounding).
            ("gpt-5.5", 0.010),
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
        # Spec 0143 — 4 searches × $0.010 = $0.04 (was $0.025 → $0.10).
        assert compute_search_cost("gpt-5.5", 4) == pytest.approx(0.040)

    def test_compute_search_cost_zero_for_unknown_model(self) -> None:
        assert compute_search_cost("not-a-real-model", 10) == 0.0

    def test_compute_search_cost_zero_for_no_searches(self) -> None:
        assert compute_search_cost("claude-sonnet-4-6", 0) == 0.0
        # Negative count is also coerced to 0 (defensive).
        assert compute_search_cost("claude-sonnet-4-6", -3) == 0.0

    def test_does_not_join_compute_cost(self) -> None:
        """`compute_cost` / `compute_token_cost` are strictly token-cost.

        Spec 0039 introduces ``compute_full_cost`` which adds search
        fees — but the token-only helpers must continue to return only
        the token component (the Consumption tab's "of which" line
        depends on the separation).
        """
        usage = TokenUsage(input_tokens=0, output_tokens=0)
        assert compute_cost("claude-sonnet-4-6", usage) == 0.0
        assert compute_token_cost("claude-sonnet-4-6", usage) == 0.0


class TestSpec0039Pricing:
    """Spec 0039 — split cache writes by TTL, fold search into the headline."""

    def test_cache_write_multipliers_match_anthropic_published(self) -> None:
        """1.25× input for 5m, 2× input for 1h — verify the constants and
        that each model's per-TTL rate matches its input rate times the
        constant. Anthropic published rates per
        https://platform.claude.com/docs/en/build-with-claude/prompt-caching
        (verified 2026-05-16)."""
        assert CACHE_WRITE_5M_MULTIPLIER == 1.25
        assert CACHE_WRITE_1H_MULTIPLIER == 2.0
        sonnet = PRICING["claude-sonnet-4-6"]
        assert sonnet.cache_write_5m_per_mtok == pytest.approx(
            sonnet.input_per_mtok * CACHE_WRITE_5M_MULTIPLIER
        )
        assert sonnet.cache_write_1h_per_mtok == pytest.approx(
            sonnet.input_per_mtok * CACHE_WRITE_1H_MULTIPLIER
        )
        haiku = PRICING["claude-haiku-4-5"]
        assert haiku.cache_write_5m_per_mtok == pytest.approx(
            haiku.input_per_mtok * CACHE_WRITE_5M_MULTIPLIER
        )
        assert haiku.cache_write_1h_per_mtok == pytest.approx(
            haiku.input_per_mtok * CACHE_WRITE_1H_MULTIPLIER
        )

    def test_compute_token_cost_prices_1h_cache_writes_higher(self) -> None:
        """1h cache writes cost more (2× input vs 1.25× for 5m). The
        partner-vetting bug was that all cache writes were priced at
        5m even though the agent requested 1h."""
        usage_5m = TokenUsage(input_tokens=0, cache_write_5m_tokens=1_000_000)
        usage_1h = TokenUsage(input_tokens=0, cache_write_1h_tokens=1_000_000)
        # Sonnet: $3.75/Mtok 5m, $6.00/Mtok 1h
        assert compute_token_cost("claude-sonnet-4-6", usage_5m) == pytest.approx(3.75)
        assert compute_token_cost("claude-sonnet-4-6", usage_1h) == pytest.approx(6.00)

    def test_compute_token_cost_split_summed_correctly(self) -> None:
        """When both tiers are present, each is priced at its own rate."""
        usage = TokenUsage(
            input_tokens=0,
            cache_write_5m_tokens=400_000,
            cache_write_1h_tokens=600_000,
        )
        # 0.4 × $3.75 + 0.6 × $6.00 = $1.50 + $3.60 = $5.10
        assert compute_token_cost("claude-sonnet-4-6", usage) == pytest.approx(5.10)

    def test_compute_token_cost_back_compat_falls_to_5m(self) -> None:
        """Older transcripts that only carry the aggregate
        ``cache_write_tokens`` must be credited to the 5m bucket so
        pre-spec totals don't change — except for the pricing bugfix."""
        old_usage = TokenUsage(
            input_tokens=0,
            cache_write_tokens=1_000_000,  # only aggregate, no per-TTL
        )
        # Should equal the pre-spec compute_cost result — i.e. 5m rate.
        assert compute_token_cost("claude-sonnet-4-6", old_usage) == pytest.approx(3.75)
        # And compute_cost (the back-compat shim) returns the same.
        assert compute_cost("claude-sonnet-4-6", old_usage) == pytest.approx(3.75)

    def test_compute_full_cost_equals_token_plus_search(self) -> None:
        """``compute_full_cost`` is the canonical headline — it equals
        token cost plus search cost. This is the invariant the
        Consumption tab's "of which" breakdown relies on."""
        usage = TokenUsage(
            input_tokens=500_000, output_tokens=100_000,
            cache_write_5m_tokens=100_000, cache_write_1h_tokens=50_000,
        )
        for model_id, n_searches in [
            ("claude-sonnet-4-6", 5),
            ("gpt-5.5", 4),
            ("gpt-5-mini", 0),
        ]:
            token = compute_token_cost(model_id, usage)
            search = compute_search_cost(model_id, n_searches)
            full = compute_full_cost(model_id, usage, n_searches)
            assert full == pytest.approx(token + search), model_id

    def test_compute_full_cost_unknown_model_returns_zero(self) -> None:
        usage = TokenUsage(input_tokens=1_000_000)
        assert compute_full_cost("not-a-real-model", usage, 10) == 0.0

    def test_pricing_snapshot_table(self) -> None:
        """Snapshot the per-model rates so a vendor-rate edit is loud.

        Update intentionally when Anthropic / OpenAI publishes new
        rates — and propagate the change to the partner-vetting test
        plan in the spec at the same time.
        """
        sonnet = PRICING["claude-sonnet-4-6"]
        assert sonnet.input_per_mtok == 3.00
        assert sonnet.output_per_mtok == 15.00
        assert sonnet.cache_read_per_mtok == 0.30
        assert sonnet.cache_write_5m_per_mtok == 3.75
        assert sonnet.cache_write_1h_per_mtok == 6.00
        assert sonnet.web_search_per_request == 0.010
