"""Spec 0148 D12 — ``compute_cache_savings_usd`` arithmetic.

The helper returns the USD saved on cache-read tokens vs. paying the
full input rate. It backs the totals-block ``cache savings · ×N reuse``
line in the Consumption card.
"""

from __future__ import annotations

import pytest

from dual_research.agents.pricing import (
    PRICING,
    PRICING_VERSION,
    compute_cache_savings_usd,
)


def test_returns_zero_for_unknown_model() -> None:
    assert compute_cache_savings_usd("not-a-model", 100_000) == 0.0


def test_returns_zero_for_non_positive_token_counts() -> None:
    assert compute_cache_savings_usd("gpt-5.5", 0) == 0.0
    assert compute_cache_savings_usd("gpt-5.5", -1) == 0.0
    assert compute_cache_savings_usd("claude-sonnet-4-6", 0) == 0.0


def test_gpt_5_5_rate_delta() -> None:
    # Pinned against the current PRICING table (PRICING_VERSION 2026-05-21).
    # gpt-5.5: input 5.00/Mtok, cache_read 0.50/Mtok → rate delta 4.50/Mtok.
    # 100_000 tokens × 4.50 / 1_000_000 = 0.45 exactly.
    assert compute_cache_savings_usd("gpt-5.5", 100_000) == pytest.approx(0.45, abs=1e-6)


def test_claude_sonnet_rate_delta() -> None:
    # claude-sonnet-4-6: input 3.00/Mtok, cache_read 0.30/Mtok → delta 2.70.
    # 50_000 × 2.70 / 1_000_000 = 0.135.
    assert compute_cache_savings_usd("claude-sonnet-4-6", 50_000) == pytest.approx(
        0.135, abs=1e-6
    )


def test_arithmetic_matches_pricing_table() -> None:
    # Defensive: the helper's arithmetic agrees with the table directly.
    for model_id, p in PRICING.items():
        # Use 1M tokens so the result is the rate delta directly.
        delta = max(0.0, p.input_per_mtok - p.cache_read_per_mtok)
        assert compute_cache_savings_usd(model_id, 1_000_000) == pytest.approx(
            delta, abs=1e-6
        )


def test_pricing_version_pin_unchanged() -> None:
    # If a rate edit changes the savings, the version must bump too.
    # This test isn't strict (any string is allowed) but documents the
    # cross-test dependency: if test_gpt_5_5_rate_delta starts failing,
    # check that PRICING_VERSION moved.
    assert PRICING_VERSION == "2026-05-21"
