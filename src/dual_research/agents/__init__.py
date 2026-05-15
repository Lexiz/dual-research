from __future__ import annotations

from dual_research.agents.anthropic_agent import ClaudeAgent
from dual_research.agents.base import (
    AgentCall,
    AgentError,
    AgentResult,
    TokenUsage,
)
from dual_research.agents.openai_agent import GptAgent
from dual_research.agents.pricing import ModelPricing, PRICING, compute_cost
from dual_research.config import Credentials, ModelTier


def make_agents(*, tier: ModelTier, creds: Credentials) -> tuple[ClaudeAgent, GptAgent]:
    claude = ClaudeAgent(api_key=creds.anthropic_api_key, spec=tier.claude)
    gpt = GptAgent(api_key=creds.openai_api_key, spec=tier.openai)
    return claude, gpt


__all__ = [
    "AgentCall",
    "AgentError",
    "AgentResult",
    "ClaudeAgent",
    "GptAgent",
    "ModelPricing",
    "PRICING",
    "TokenUsage",
    "compute_cost",
    "make_agents",
]
