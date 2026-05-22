"""Append an event to a spec's sidecar JSONL log.

Skills call this from the dev cycle (and the spec-creation flows for `queued`
events). Events on `main` get committed inline by the caller; events on a
feature branch buffer and flush at end-of-cycle.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def event_log_path(events_dir: str | Path, spec_id: str) -> Path:
    p = Path(events_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{spec_id}.jsonl"


def append_event(
    events_dir: str | Path,
    spec_id: str,
    step: str,
    data: dict[str, Any] | None = None,
    *,
    ts: str | None = None,
) -> Path:
    """Append one event line. Returns the file path."""
    if ts is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = json.dumps(
        {"ts": ts, "step": step, "data": data or {}}, separators=(",", ":"), ensure_ascii=False
    )
    log = event_log_path(events_dir, spec_id)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return log


def read_events(events_dir: str | Path, spec_id: str) -> list[dict[str, Any]]:
    """Read all events for a spec; returns [] if no log exists."""
    log = Path(events_dir) / f"{spec_id}.jsonl"
    if not log.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in log.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            # Skip malformed lines rather than crash the dashboard render
            continue
    return out


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) < 3 or args[0] in {"-h", "--help"}:
        print("Usage: append_event.py <events_dir> <spec_id> <step> [data_json]")
        return 1
    events_dir, spec_id, step = args[0], args[1], args[2]
    data = json.loads(args[3]) if len(args) > 3 else None
    path = append_event(events_dir, spec_id, step, data)
    print(f"wrote event to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
