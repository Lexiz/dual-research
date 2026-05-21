"""Spec 0143 §5.1 — re-price the anchor run under the bumped PRICING table.

The dispositive test for the spec's headline claim: with the corrected
GPT-5.5 rates ($5/M input, $30/M output, $0.50/M cached input, $0.010
per web_search call), the captured per-call tokens for the anchor run
reconcile to the recorded 2026-05-21 provider invoice values:

- OpenAI tokens:     $4.81 (was $1.33 under stale rates — 72% drift)
- OpenAI web search: $0.17 (was $0.475 under stale rate — 179% drift)

Tolerance is ±$0.05 because the invoice carries the residual "search
content tokens billed at model rates" overhead — already folded into
``input_tokens`` via the ``include=["web_search_call.action.sources"]``
plumbing, but the precise split depends on the provider-side accounting.

This test reads from the actual on-disk anchor run if present; skips
otherwise (clean clones / CI). Pins the rate table against the only
piece of ground truth we have.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.agents.base import TokenUsage
from dual_research.agents.pricing import (
    compute_search_cost,
    compute_token_cost,
)


ANCHOR_RUN_DIR = (
    Path(__file__).resolve().parents[2]
    / "runs"
    / "20260521-010637-dvs-backend-language-choice"
)


def _load_calls() -> list[dict]:
    metrics_path = ANCHOR_RUN_DIR / "metrics.json"
    if not metrics_path.exists():
        pytest.skip(f"anchor run not on disk at {metrics_path}")
    return json.loads(metrics_path.read_text())["calls"]


def test_openai_reconcile_against_invoice_post_spec_0143() -> None:
    """Re-price the anchor run's OpenAI calls under the bumped rates.

    Invoice (recorded in spec 0049's reconcile_results.payload for date
    2026-05-21): tokens $4.81, web_search $0.17. With the OLD rates
    ($1.25/M input, $10/M output, $0.125/M cache, $0.025/call search),
    local sums to $1.33 + $0.475 = drift of 72% / 179%. Post-spec-0143
    bump to the published rates, both reconcile within $0.05.
    """
    calls = _load_calls()
    openai_calls = [c for c in calls if c["agent"] == "openai"]
    assert openai_calls, "anchor run carries no OpenAI calls"

    token_cost = 0.0
    search_cost = 0.0
    for c in openai_calls:
        usage = TokenUsage(
            input_tokens=c["input_tokens"],
            output_tokens=c["output_tokens"],
            cache_read_tokens=c["cache_read_tokens"],
        )
        # Strip the dated suffix for pricing lookup (gpt-5.5-2026-04-23
        # falls through to the gpt-5.5 entry via lookup_pricing's
        # prefix-match clause).
        token_cost += compute_token_cost(c["model_id"], usage)
        search_cost += compute_search_cost(c["model_id"], int(c.get("searches", 0)))

    # Recorded invoice values per spec 0049's reconcile_results payload.
    INVOICE_TOKENS_USD = 4.81
    INVOICE_SEARCH_USD = 0.17

    # ±$0.05 tolerance: covers residual rounding and the "search content
    # tokens at model rate" overhead in the invoice that's already
    # folded into input_tokens by the include=action.sources plumbing.
    assert token_cost == pytest.approx(INVOICE_TOKENS_USD, abs=0.05), (
        f"OpenAI token cost {token_cost:.4f} should reconcile to invoice "
        f"{INVOICE_TOKENS_USD:.4f} under the spec-0143 pricing bump"
    )
    assert search_cost == pytest.approx(INVOICE_SEARCH_USD, abs=0.05), (
        f"OpenAI search cost {search_cost:.4f} should reconcile to invoice "
        f"{INVOICE_SEARCH_USD:.4f} under the spec-0143 search-rate bump"
    )


def test_openai_pre_spec_0143_rates_would_drift() -> None:
    """Sanity-check the test's premise: under the OLD rates, the anchor
    run would NOT reconcile. If this stops failing, someone has either
    (a) regressed the PRICING table back to the old values, or (b) the
    anchor metrics changed materially. Either way: investigate.
    """
    calls = _load_calls()
    openai_calls = [c for c in calls if c["agent"] == "openai"]

    OLD_INPUT = 1.25
    OLD_OUTPUT = 10.0
    OLD_CACHE = 0.125
    OLD_SEARCH = 0.025

    token_cost = 0.0
    search_cost = 0.0
    for c in openai_calls:
        token_cost += (
            c["input_tokens"] * OLD_INPUT
            + c["output_tokens"] * OLD_OUTPUT
            + c["cache_read_tokens"] * OLD_CACHE
        ) / 1_000_000
        search_cost += int(c.get("searches", 0)) * OLD_SEARCH

    # Under the OLD rates these sum to ~$1.33 / ~$0.475 — both should be
    # well outside the 5¢ window vs the invoice ($4.81 / $0.17).
    assert token_cost < 2.0, (
        "old rates should drift LOW vs invoice ($4.81); "
        f"got {token_cost:.4f} which is suspiciously close to invoice — "
        "did the test fixture or PRICING table change?"
    )
    assert search_cost > 0.30, (
        "old rates should drift HIGH vs invoice ($0.17); "
        f"got {search_cost:.4f}"
    )


def test_anchor_run_metrics_pinned_to_old_pricing_version() -> None:
    """The anchor run's metrics.json carries the pricing_version that
    priced it — spec 0048's compact for old-vs-new rate-table
    disambiguation.

    Originally pinned to 2026-05-17 (pre-spec-0143). Spec 0143's
    post-merge `recompute-costs --all --push` backfill re-priced every
    local run under the new table and rewrote pricing_version to
    2026-05-21. This pin now tracks that post-backfill reality.
    """
    metrics_path = ANCHOR_RUN_DIR / "metrics.json"
    if not metrics_path.exists():
        pytest.skip(f"anchor run not on disk at {metrics_path}")
    m = json.loads(metrics_path.read_text())
    assert m.get("pricing_version") == "2026-05-21", (
        "anchor run should be pinned to the post-0143-backfill pricing version"
    )
