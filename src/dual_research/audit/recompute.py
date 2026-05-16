"""Spec 0039 — one-shot backfill that re-prices existing runs.

Walks a run's ``transcript.jsonl``, deduplicates ``turn_ended`` events
by ``label`` (keeping the latest occurrence — matching the canonical
"later wins" convention the aggregator uses since spec 0039), then
recomputes every per-turn ``cost_usd`` under the current pricing rules
(1h cache writes priced at 2× input, search fees folded into the
headline). The resulting ``metrics.json`` is rewritten in place; the
original is preserved as ``metrics.json.pre-0039.bak`` so a reviewer
can diff old vs new totals.

Idempotent: re-running produces an empty diff. The ``.bak`` file is
only created on the first invocation — subsequent runs preserve the
original-original.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from dual_research.agents.base import TokenUsage
from dual_research.agents.pricing import (
    compute_full_cost,
    compute_search_cost,
    compute_token_cost,
)
from dual_research.persistence.metrics import CallRecord, Metrics


BACKUP_SUFFIX = "pre-0039.bak"


@dataclass
class TurnDiff:
    label: str
    agent: str
    model_id: str
    old_cost: float
    new_cost: float

    @property
    def delta(self) -> float:
        return self.new_cost - self.old_cost


@dataclass
class RecomputeReport:
    run_id: str
    old_total: float
    new_total: float
    diffs: list[TurnDiff] = field(default_factory=list)
    backed_up: bool = False
    metrics_written: bool = False

    @property
    def delta(self) -> float:
        return self.new_total - self.old_total

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "old_total": self.old_total,
            "new_total": self.new_total,
            "delta": self.delta,
            "diffs": [dataclasses.asdict(d) for d in self.diffs],
            "backed_up": self.backed_up,
            "metrics_written": self.metrics_written,
        }


def _read_transcript(transcript_path: Path) -> Iterable[dict]:
    if not transcript_path.exists():
        return []
    out: list[dict] = []
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _dedup_turn_events(events: Iterable[dict]) -> list[dict]:
    """Return one ``turn_ended`` event per label, keeping the LAST seen.

    A parse-error recovery (or any retry) re-emits the same ``label``;
    the final event for that label is the canonical successful attempt.
    Order is preserved by first-seen so the diff reports read naturally.
    """
    last_by_label: dict[str, dict] = {}
    order: list[str] = []
    for ev in events:
        if ev.get("event") != "turn_ended":
            continue
        label = ev.get("label")
        if not label:
            continue
        if label not in last_by_label:
            order.append(label)
        last_by_label[label] = ev
    return [last_by_label[l] for l in order]


def _usage_from_event(event: dict) -> TokenUsage:
    cw_5m = int(event.get("cache_write_5m_tokens", 0) or 0)
    cw_1h = int(event.get("cache_write_1h_tokens", 0) or 0)
    cw_total = int(event.get("cache_write_tokens", 0) or 0)
    if cw_5m == 0 and cw_1h == 0:
        # Pre-0039 transcript — credit the aggregate to 5m. Matches the
        # pre-beta API behaviour; consistent with what compute_token_cost
        # does when only the aggregate is available.
        cw_5m = cw_total
    return TokenUsage(
        input_tokens=int(event.get("input_tokens", 0) or 0),
        output_tokens=int(event.get("output_tokens", 0) or 0),
        cache_read_tokens=int(event.get("cache_read_tokens", 0) or 0),
        cache_write_tokens=cw_5m + cw_1h,
        cache_write_5m_tokens=cw_5m,
        cache_write_1h_tokens=cw_1h,
    )


def recompute_run(session_dir: Path, *, write: bool = True) -> RecomputeReport:
    """Re-price a single run from its transcript.

    Returns a structured ``RecomputeReport`` describing the change. When
    ``write=True`` (default), rewrites ``metrics.json`` and creates a
    ``metrics.json.pre-0039.bak`` snapshot on the first invocation.
    """
    transcript_path = session_dir / "transcript.jsonl"
    metrics_path = session_dir / "metrics.json"

    old_total = 0.0
    if metrics_path.exists():
        try:
            old_total = float(
                json.loads(metrics_path.read_text(encoding="utf-8")).get("total_cost_usd", 0.0)
                or 0.0
            )
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            old_total = 0.0

    events = _read_transcript(transcript_path)
    canonical = _dedup_turn_events(events)

    diffs: list[TurnDiff] = []
    rebuilt = Metrics()
    for ev in canonical:
        usage = _usage_from_event(ev)
        model_id = str(ev.get("model_id") or "")
        searches = int(ev.get("searches", 0) or 0)
        new_cost = compute_full_cost(model_id, usage, searches)
        old_cost = float(ev.get("cost_usd", 0.0) or 0.0)
        diffs.append(
            TurnDiff(
                label=str(ev.get("label") or ""),
                agent=str(ev.get("agent") or ""),
                model_id=model_id,
                old_cost=old_cost,
                new_cost=new_cost,
            )
        )
        search_cost = compute_search_cost(model_id, searches)
        rebuilt.calls.append(
            CallRecord(
                label=str(ev.get("label") or ""),
                agent=str(ev.get("agent") or ""),
                model_id=model_id,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=usage.cache_read_tokens,
                cache_write_tokens=usage.cache_write_tokens,
                cache_write_5m_tokens=usage.cache_write_5m_tokens,
                cache_write_1h_tokens=usage.cache_write_1h_tokens,
                cost_usd=new_cost,
                duration_ms=int(ev.get("duration_ms", 0) or 0),
                searches=searches,
                search_cost=search_cost,
            )
        )

    new_total = rebuilt.total_cost_usd()
    report = RecomputeReport(
        run_id=session_dir.name,
        old_total=old_total,
        new_total=new_total,
        diffs=diffs,
    )

    if not write:
        return report

    if metrics_path.exists():
        backup_path = metrics_path.with_suffix(metrics_path.suffix + "." + BACKUP_SUFFIX)
        # Only create the backup on the first invocation — re-running
        # the tool should never clobber the *original* metrics.json.
        if not backup_path.exists():
            shutil.copy2(metrics_path, backup_path)
            report.backed_up = True

    # Preserve the original started_at / ended_at if available.
    if metrics_path.exists():
        try:
            original = json.loads(metrics_path.read_text(encoding="utf-8"))
            if original.get("started_at"):
                rebuilt.started_at = str(original["started_at"])
            if original.get("ended_at"):
                rebuilt.ended_at = str(original["ended_at"])
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    rebuilt.save(metrics_path)
    report.metrics_written = True
    return report


def recompute_all(runs_dir: Path, *, write: bool = True) -> list[RecomputeReport]:
    """Recompute every run under ``runs_dir`` that has a transcript."""
    reports: list[RecomputeReport] = []
    if not runs_dir.exists():
        return reports
    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not (entry / "transcript.jsonl").exists():
            continue
        reports.append(recompute_run(entry, write=write))
    return reports


__all__ = [
    "BACKUP_SUFFIX",
    "RecomputeReport",
    "TurnDiff",
    "recompute_all",
    "recompute_run",
]
