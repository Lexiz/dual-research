"""``queue/timings.json`` — accumulated per-step durations.

Dashboard reads the median of each step's array; new durations append
on every successful step end (state.end_step calls into here).

Schema::

    {"step_durations": {"1_read": [3, 4, 2, ...], "2_reason": [...], ...}}

A missing or empty array means "no history yet" — the dashboard shows
``—`` for the Avg column rather than implying a fake number.
"""

from __future__ import annotations

import json
import os
import statistics
import uuid
from pathlib import Path

from dual_research.queue_v2.state import STEP_ORDER, queue_root


def path(repo_root: Path | None = None) -> Path:
    return queue_root(repo_root) / "timings.json"


def _empty_payload() -> dict[str, dict[str, list[int]]]:
    return {"step_durations": {step: [] for step in STEP_ORDER}}


def load(repo_root: Path | None = None) -> dict[str, dict[str, list[int]]]:
    p = path(repo_root)
    if not p.exists():
        return _empty_payload()
    raw = json.loads(p.read_text())
    sd = raw.get("step_durations", {})
    # Backfill any missing step keys to keep callers simple.
    for step in STEP_ORDER:
        sd.setdefault(step, [])
    return {"step_durations": sd}


def save(payload: dict[str, dict[str, list[int]]], repo_root: Path | None = None) -> None:
    p = path(repo_root)
    tmp = p.with_suffix(f".tmp.{uuid.uuid4().hex}")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(tmp, p)


def record(step: str, duration_s: int, repo_root: Path | None = None) -> None:
    assert step in STEP_ORDER, f"unknown step {step}"
    payload = load(repo_root)
    payload["step_durations"][step].append(int(duration_s))
    save(payload, repo_root)


def median(step: str, repo_root: Path | None = None) -> int | None:
    payload = load(repo_root)
    vals = payload["step_durations"].get(step, [])
    if not vals:
        return None
    return int(statistics.median(vals))


def all_medians(repo_root: Path | None = None) -> dict[str, int | None]:
    return {step: median(step, repo_root) for step in STEP_ORDER}


__all__ = ["all_medians", "load", "median", "path", "record", "save"]
