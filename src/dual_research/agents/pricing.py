from __future__ import annotations

from dataclasses import dataclass

from dual_research.agents.base import TokenUsage


@dataclass(frozen=True)
class ModelPricing:
    """USD per 1M tokens. Best-effort, not an invoice. Update as vendors change rates."""
    input_per_mtok: float
    output_per_mtok: float
    cache_read_per_mtok: float = 0.0
    cache_write_per_mtok: float = 0.0
    notes: str = ""


PRICING: dict[str, ModelPricing] = {
    "claude-sonnet-4-6": ModelPricing(
        input_per_mtok=3.00,
        output_per_mtok=15.00,
        cache_read_per_mtok=0.30,
        cache_write_per_mtok=3.75,
        notes="Sonnet 4.6 standard tier. 1M-context calls may incur premium.",
    ),
    "claude-haiku-4-5": ModelPricing(
        input_per_mtok=1.00,
        output_per_mtok=5.00,
        cache_read_per_mtok=0.10,
        cache_write_per_mtok=1.25,
        notes="Haiku 4.5 standard tier.",
    ),
    "gpt-5.5": ModelPricing(
        input_per_mtok=1.25,
        output_per_mtok=10.00,
        cache_read_per_mtok=0.125,
        notes="GPT-5.5 standard tier (estimated).",
    ),
    "gpt-5-mini": ModelPricing(
        input_per_mtok=0.25,
        output_per_mtok=2.00,
        cache_read_per_mtok=0.025,
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


def compute_cost(model_id: str, usage: TokenUsage) -> float:
    p = lookup_pricing(model_id)
    if p is None:
        return 0.0
    return (
        usage.input_tokens * p.input_per_mtok
        + usage.output_tokens * p.output_per_mtok
        + usage.cache_read_tokens * p.cache_read_per_mtok
        + usage.cache_write_tokens * p.cache_write_per_mtok
    ) / 1_000_000
