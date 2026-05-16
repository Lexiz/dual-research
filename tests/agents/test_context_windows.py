"""Spec 0029 — model-id → context-window lookup.

The Consumption tab's progress-bar denominator comes from this registry.
We test that:

  - known model ids resolve to their declared window,
  - unknown / None ids fall back to ``DEFAULT_CONTEXT_WINDOW``,
  - the lenient prefix match works (mirroring ``lookup_pricing``),
  - every model id in ``PRICING`` has SOME resolution (either a direct
    entry or a successful prefix match — the test fails loudly when a
    new priced model is added without a context-window entry).
"""

from __future__ import annotations

import pytest

from dual_research.agents.context_windows import (
    CONTEXT_WINDOWS,
    DEFAULT_CONTEXT_WINDOW,
    context_window_for,
)
from dual_research.agents.pricing import PRICING


class TestContextWindowFor:
    def test_returns_default_for_none(self) -> None:
        assert context_window_for(None) == DEFAULT_CONTEXT_WINDOW

    def test_returns_default_for_unknown(self) -> None:
        assert context_window_for("not-a-real-model") == DEFAULT_CONTEXT_WINDOW

    @pytest.mark.parametrize(
        "model_id,expected",
        [
            ("claude-sonnet-4-6", 200_000),
            ("claude-haiku-4-5", 200_000),
            ("gpt-5.5", 200_000),
            ("gpt-5-mini", 128_000),
        ],
    )
    def test_direct_entries_resolve(self, model_id: str, expected: int) -> None:
        assert context_window_for(model_id) == expected

    def test_prefix_match_for_dated_variant(self) -> None:
        """API responses often include a dated suffix (e.g. ``-20260301``).
        Prefix-match keeps lookup working without a registry update per
        snapshot.
        """
        assert context_window_for("claude-sonnet-4-6-20260301") == 200_000


class TestRegistryCoverage:
    def test_every_priced_model_resolves(self) -> None:
        """Every model in ``PRICING`` should land on something other than
        the bare default — either via direct entry or prefix match.

        If a new model is added to ``PRICING`` without a context-window
        entry, this test fails so the registry stays in lockstep.
        """
        missing: list[str] = []
        for model_id in PRICING.keys():
            window = context_window_for(model_id)
            # A direct entry or a prefix entry that yields the same value
            # is the signal. A bare-default fall-through means we didn't
            # cover this model — flag it.
            if model_id not in CONTEXT_WINDOWS and not any(
                model_id.startswith(k) for k in CONTEXT_WINDOWS
            ):
                missing.append(model_id)
            # Sanity: every resolved window is positive.
            assert window > 0
        assert (
            not missing
        ), f"PRICING entries without a context_window entry: {missing}"
