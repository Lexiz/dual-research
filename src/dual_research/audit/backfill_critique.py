"""Spec 0252 — one-shot backfill that populates ``critique_by_agent``.

Every run displayed in production that predates spec 0248's write-time
tally carries ``critique_by_agent: null`` in its ``metrics.json``; the
All Runs provider band (spec 0248 §2.5) then renders all critique
counters as ``0`` (the read path ``derive_agent_breakdowns`` correctly
degrades to zeros when the payload is absent — spec 0248 §7). This is a
**data-backfill** problem, not a compute bug: ``compute_critique_by_agent``
is correct; the old runs simply never had it computed.

This module mirrors :mod:`dual_research.audit.recompute` exactly. It
recomputes ``critique_by_agent`` for an existing run from its on-disk
artifacts and persists it back into ``metrics.json`` (and, via the CLI's
``--push``, the Supabase ``metrics`` JSONB column so the *deployed* cards
reflect the recomputed tally).

The list path's cheap-path guarantee (spec 0248 §1/§7 — ``/api/runs``
never replays transcripts) is untouched: the backfill is an explicit,
out-of-band command, never the read path.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dual_research.persistence.metrics import Metrics
from dual_research.ui.critique_tally import compute_critique_by_agent


@dataclass
class BackfillReport:
    run_id: str
    before_nonempty: bool = False
    after_nonempty: bool = False
    metrics_written: bool = False
    # Per-agent raised counts after the recompute, e.g.
    # {"claude": {"questions": 5, "disagreements": 5, "issues": 3,
    # "comments": 2}, "openai": {…}} — the "raised" half of each pair.
    raised_counts: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


_CATEGORIES = ("questions", "disagreements", "issues", "comments")


def _raised_counts(critique_by_agent: dict) -> dict:
    """Extract the per-agent raised half of each category pair."""
    out: dict = {}
    for agent, bucket in (critique_by_agent or {}).items():
        per_cat: dict = {}
        for cat in _CATEGORIES:
            pair = bucket.get(cat)
            if pair and len(pair) == 2:
                per_cat[cat] = int(pair[0] or 0)
        out[agent] = per_cat
    return out


def backfill_critique_run(session_dir: Path, *, write: bool = True) -> BackfillReport:
    """Recompute and persist ``critique_by_agent`` for a single run.

    Loads ``Metrics`` from ``session_dir/metrics.json``, recomputes the
    tally via :func:`compute_critique_by_agent` (which replays the run's
    items once — heavy, but this is an out-of-band command), assigns it
    back onto the metrics, and rewrites ``metrics.json`` when ``write``.
    Returns a :class:`BackfillReport`.

    Idempotent: re-running yields the same tally (recompute is
    deterministic from the run's artifacts).
    """
    metrics_path = session_dir / "metrics.json"
    metrics = Metrics.load(metrics_path)

    before = metrics.critique_by_agent or {}
    recomputed = compute_critique_by_agent(session_dir, metrics.totals_by_agent())

    report = BackfillReport(
        run_id=session_dir.name,
        before_nonempty=bool(before),
        after_nonempty=bool(recomputed),
        raised_counts=_raised_counts(recomputed),
    )

    if not write:
        return report

    metrics.critique_by_agent = recomputed
    metrics.save(metrics_path)
    report.metrics_written = True
    return report


def backfill_all(runs_dir: Path, *, write: bool = True) -> list[BackfillReport]:
    """Backfill every run under ``runs_dir`` that has a ``metrics.json``."""
    reports: list[BackfillReport] = []
    if not runs_dir.exists():
        return reports
    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not (entry / "metrics.json").exists():
            continue
        reports.append(backfill_critique_run(entry, write=write))
    return reports


__all__ = [
    "BackfillReport",
    "backfill_all",
    "backfill_critique_run",
]
