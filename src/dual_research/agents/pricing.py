from __future__ import annotations

from dataclasses import dataclass

from dual_research.agents.base import TokenUsage


# Anthropic prompt-caching write multipliers, relative to base input rate.
# Published at https://platform.claude.com/docs/en/build-with-claude/prompt-caching
# (verified 2026-05-16). Defining them as module constants makes the
# relationship to the input rate self-documenting and keeps the per-model
# tables editable in one place when vendors update rates.
CACHE_WRITE_5M_MULTIPLIER = 1.25
CACHE_WRITE_1H_MULTIPLIER = 2.0
CACHE_READ_MULTIPLIER = 0.1


@dataclass(frozen=True)
class ModelPricing:
    """USD per 1M tokens. Best-effort, not an invoice. Update as vendors change rates.

    Spec 0031 added ``web_search_per_request`` — USD charged per web-search
    tool call, separate from token cost. Anthropic publishes $10/1k for
    Claude server-side search; OpenAI Responses-API web_search is around
    $25/1k for the GPT-5 family. Defaults to 0 for models that don't bill
    a per-request fee.

    Spec 0039 split cache-write pricing by TTL tier: ``cache_write_5m_per_mtok``
    bills at 1.25× input (matches the pre-spec ``cache_write_per_mtok``);
    ``cache_write_1h_per_mtok`` bills at 2× input (the rate Anthropic
    actually charges when the agent requests ``ttl: "1h"`` via the
    ``extended-cache-ttl-2025-04-11`` beta — which `anthropic_agent.py`
    has been doing since spec 0017). OpenAI models leave both fields at 0
    (no separate cache-write billing).
    """
    input_per_mtok: float
    output_per_mtok: float
    cache_read_per_mtok: float = 0.0
    cache_write_5m_per_mtok: float = 0.0
    cache_write_1h_per_mtok: float = 0.0
    web_search_per_request: float = 0.0
    notes: str = ""


PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-4-6": ModelPricing(
        input_per_mtok=3.00,
        output_per_mtok=15.00,
        cache_read_per_mtok=0.30,                       # 0.1× input
        cache_write_5m_per_mtok=3.75,                   # 1.25× input
        cache_write_1h_per_mtok=6.00,                   # 2× input (1h beta)
        web_search_per_request=0.010,                   # $10 / 1k searches (Anthropic published)
        notes="Sonnet 4.6 standard tier. 1M-context calls may incur premium.",
    ),
    "claude-haiku-4-5": ModelPricing(
        input_per_mtok=1.00,
        output_per_mtok=5.00,
        cache_read_per_mtok=0.10,                       # 0.1× input
        cache_write_5m_per_mtok=1.25,                   # 1.25× input
        cache_write_1h_per_mtok=2.00,                   # 2× input (1h beta)
        web_search_per_request=0.010,                   # same as Sonnet
        notes="Haiku 4.5 standard tier.",
    ),
    "gpt-5.5": ModelPricing(
        input_per_mtok=1.25,
        output_per_mtok=10.00,
        cache_read_per_mtok=0.125,
        web_search_per_request=0.025,                   # ~$25 / 1k for GPT-5 family Responses API
        notes="GPT-5.5 standard tier (estimated).",
    ),
    "gpt-5-mini": ModelPricing(
        input_per_mtok=0.25,
        output_per_mtok=2.00,
        cache_read_per_mtok=0.025,
        web_search_per_request=0.025,                   # same as GPT-5.5
        notes="GPT-5-mini (estimated).",
    ),
}


def lookup_pricing(model_id: str) -> ModelPricing | None:
    if model_id in PRICING:
        return PRICING[model_id]
    for key, p in PRICING.items():
        if model_id.startswith(key):
            return p
    return None


def compute_token_cost(model_id: str, usage: TokenUsage) -> float:
    """USD token cost for ``usage`` under ``model_id``'s pricing.

    Splits cache-write tokens between the 5m and 1h tiers. Older
    transcripts that only carry the aggregate ``cache_write_tokens`` (no
    per-TTL split) are credited entirely to the 5m bucket — the pre-beta
    default behaviour. When the split fields are present, the aggregate
    is ignored to avoid double-counting.
    """
    p = lookup_pricing(model_id)
    if p is None:
        return 0.0
    cw_5m = usage.cache_write_5m_tokens
    cw_1h = usage.cache_write_1h_tokens
    if cw_5m == 0 and cw_1h == 0:
        # Older shape — credit the aggregate to 5m (matches pre-spec-0039
        # behaviour, which is what the pre-beta API actually billed).
        cw_5m = usage.cache_write_tokens
    return (
        usage.input_tokens * p.input_per_mtok
        + usage.output_tokens * p.output_per_mtok
        + usage.cache_read_tokens * p.cache_read_per_mtok
        + cw_5m * p.cache_write_5m_per_mtok
        + cw_1h * p.cache_write_1h_per_mtok
    ) / 1_000_000


def compute_search_cost(model_id: str, n: int) -> float:
    """USD cost of ``n`` web-search tool calls under this model's pricing.

    Returns 0.0 for unknown / unpriced models and for ``n <= 0``. Spec
    0031 carved this out as a side-channel; spec 0039 folds the return
    value into the headline via ``compute_full_cost`` (see below) but
    keeps the helper so the breakdown is still cleanly recoverable.
    """
    if n <= 0:
        return 0.0
    p = lookup_pricing(model_id)
    if p is None or p.web_search_per_request <= 0:
        return 0.0
    return n * p.web_search_per_request


def compute_full_cost(model_id: str, usage: TokenUsage, searches: int = 0) -> float:
    """Canonical headline cost: tokens + per-request tool fees.

    This is what stamps every persisted ``cost_usd`` (AgentResult,
    TurnEnded, CallRecord, metrics.json total, RunCompleted, Supabase
    runs.total_cost_usd). ``compute_token_cost`` remains available for
    the breakdown ("of which tokens" / "of which web search") that the
    UI surfaces in the Consumption tab and the CostBadge tooltip.

    Reverses spec 0031 D7 — search cost is now part of the invoice
    everywhere, not a separately-displayed side-channel.
    """
    return compute_token_cost(model_id, usage) + compute_search_cost(model_id, searches)


# Back-compat shim — preserved so any external caller (tests, downstream
# tooling) still works against the pre-0039 name. Internally everyone
# should call `compute_token_cost` or `compute_full_cost`.
def compute_cost(model_id: str, usage: TokenUsage) -> float:
    return compute_token_cost(model_id, usage)
