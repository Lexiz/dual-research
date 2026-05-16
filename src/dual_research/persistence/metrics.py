from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.agents.pricing import compute_search_cost
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
    # Spec 0039 — per-TTL cache-write split (5m bills at 1.25× input,
    # 1h at 2× input). ``cache_write_tokens`` stays as the aggregate so
    # older readers still work; the split is what the new pricing
    # function consumes. Older metrics.json files load with zeroes here
    # and the aggregate going to 5m at recompute time (see
    # pricing.compute_token_cost).
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0
    # Spec 0039 — fold search fees into the invoice. ``cost_usd`` is
    # now the full per-call cost (tokens + searches); ``search_cost``
    # is preserved alongside as a breakdown number so the UI can show
    # "of which web search". ``searches`` is the count that ``search_cost``
    # was derived from.
    searches: int = 0
    search_cost: float = 0.0


@dataclass
class Metrics:
    calls: list[CallRecord] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: str | None = None

    def record(self, *, label: str, result: AgentResult) -> None:
        u = result.usage
        extras = result.extras or {}
        searches = int(extras.get("searches", 0) or 0)
        search_cost = compute_search_cost(result.model_id, searches)
        self.calls.append(
            CallRecord(
                label=label,
                agent=result.label,
                model_id=result.model_id,
                input_tokens=u.input_tokens,
                output_tokens=u.output_tokens,
                cache_read_tokens=u.cache_read_tokens,
                cache_write_tokens=u.cache_write_tokens,
                cache_write_5m_tokens=u.cache_write_5m_tokens,
                cache_write_1h_tokens=u.cache_write_1h_tokens,
                cost_usd=result.cost_usd,
                duration_ms=result.duration_ms,
                searches=searches,
                search_cost=search_cost,
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
                    "cache_write_5m_tokens": 0,
                    "cache_write_1h_tokens": 0,
                    "cost_usd": 0.0,
                    "search_cost": 0.0,
                    "searches": 0,
                    "duration_ms": 0,
                    "calls": 0,
                },
            )
            bucket["input_tokens"] += c.input_tokens
            bucket["output_tokens"] += c.output_tokens
            bucket["cache_read_tokens"] += c.cache_read_tokens
            bucket["cache_write_tokens"] += c.cache_write_tokens
            bucket["cache_write_5m_tokens"] += c.cache_write_5m_tokens
            bucket["cache_write_1h_tokens"] += c.cache_write_1h_tokens
            bucket["cost_usd"] += c.cost_usd
            bucket["search_cost"] += c.search_cost
            bucket["searches"] += c.searches
            bucket["duration_ms"] += c.duration_ms
            bucket["calls"] += 1
        return out

    def total_cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    def total_search_cost_usd(self) -> float:
        return sum(c.search_cost for c in self.calls)

    def to_json(self) -> str:
        payload = {
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "calls": [asdict(c) for c in self.calls],
            "totals_by_agent": self.totals_by_agent(),
            "total_cost_usd": self.total_cost_usd(),
            "total_search_cost_usd": self.total_search_cost_usd(),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def save(self, path: Path) -> None:
        write_atomic(path, self.to_json())

    def mark_done(self) -> None:
        self.ended_at = datetime.now(timezone.utc).isoformat()

    # ─── Spec 0039 — rehydrate on resume ────────────────────────────────

    @classmethod
    def load(cls, path: Path) -> "Metrics":
        """Reconstruct a ``Metrics`` from a previously-saved ``metrics.json``.

        Tolerant of older-shape files: missing per-TTL cache-write fields
        default to zero (the aggregate ``cache_write_tokens`` is still
        read), and missing ``searches`` / ``search_cost`` default to zero
        as well. The CallRecord dataclass defaults handle this directly.
        """
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_calls = payload.get("calls", []) or []
        valid_fields = {f for f in CallRecord.__dataclass_fields__}
        calls: list[CallRecord] = []
        for c in raw_calls:
            kwargs = {k: v for k, v in c.items() if k in valid_fields}
            calls.append(CallRecord(**kwargs))
        started_at = payload.get("started_at") or datetime.now(timezone.utc).isoformat()
        ended_at = payload.get("ended_at")
        m = cls(calls=calls, started_at=started_at)
        m.ended_at = ended_at
        return m

    @classmethod
    def load_or_new(cls, path: Path) -> "Metrics":
        """Like ``load`` but returns a fresh ``Metrics`` when the file is
        missing or unparseable.

        Used by the orchestrator at session entry so a resumed run
        accumulates new turns onto the prior cost record instead of
        overwriting it (the spec-0039 bug 1 fix). A corrupted file is
        treated as missing — the transcript-primary aggregator path
        (D3) still produces correct UI numbers.
        """
        try:
            return cls.load(path)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return cls()
