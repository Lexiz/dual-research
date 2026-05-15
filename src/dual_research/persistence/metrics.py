from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.persistence.state import write_atomic


@dataclass
class CallRecord:
    label: str
    agent: str
    model_id: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    duration_ms: int


@dataclass
class Metrics:
    calls: list[CallRecord] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: str | None = None

    def record(self, *, label: str, result: AgentResult) -> None:
        u = result.usage
        self.calls.append(
            CallRecord(
                label=label,
                agent=result.label,
                model_id=result.model_id,
                input_tokens=u.input_tokens,
                output_tokens=u.output_tokens,
                cache_read_tokens=u.cache_read_tokens,
                cache_write_tokens=u.cache_write_tokens,
                cost_usd=result.cost_usd,
                duration_ms=result.duration_ms,
            )
        )

    def totals_by_agent(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for c in self.calls:
            bucket = out.setdefault(
                c.agent,
                {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 0,
                    "cost_usd": 0.0,
                    "duration_ms": 0,
                    "calls": 0,
                },
            )
            bucket["input_tokens"] += c.input_tokens
            bucket["output_tokens"] += c.output_tokens
            bucket["cache_read_tokens"] += c.cache_read_tokens
            bucket["cache_write_tokens"] += c.cache_write_tokens
            bucket["cost_usd"] += c.cost_usd
            bucket["duration_ms"] += c.duration_ms
            bucket["calls"] += 1
        return out

    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    def to_json(self) -> str:
        payload = {
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "calls": [asdict(c) for c in self.calls],
            "totals_by_agent": self.totals_by_agent(),
            "total_cost_usd": self.total_cost_usd(),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def save(self, path: Path) -> None:
        write_atomic(path, self.to_json())

    def mark_done(self) -> None:
        self.ended_at = datetime.now(timezone.utc).isoformat()
