"""Hydrate a session-dir-shaped tmp directory from Supabase.

Spec 0020. The aggregator (`ui/aggregator.py`) reads a session directory from
disk — `brief.md`, `state.json`, `transcript.jsonl`, phase files, etc.
On the hosted server the same data lives in three Supabase tables (spec 0019):
`runs`, `events`, `session_files`. This module bridges the two by writing
the run's files (plus a reconstructed `transcript.jsonl`) into a tmp dir
that looks identical to a real session-dir.

Caller pattern:

    with SupabaseSessionData(client, run_id).materialize() as tmp:
        run = load_run_snapshot(tmp)

`materialize()` returns a `tempfile.TemporaryDirectory`-style context
manager; exiting the `with` block deletes the tmp dir.
"""

from __future__ import annotations

import json
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol


SESSION_FILE_PAGE_SIZE = 200
EVENT_PAGE_SIZE = 1000


class _Builder(Protocol):
    def select(self, columns: str, **kwargs: Any) -> "_Builder": ...
    def eq(self, column: str, value: Any) -> "_Builder": ...
    def order(self, column: str, **kwargs: Any) -> "_Builder": ...
    def range(self, start: int, end: int) -> "_Builder": ...
    def limit(self, n: int) -> "_Builder": ...
    def execute(self) -> Any: ...


class _Table(Protocol):
    def select(self, columns: str, **kwargs: Any) -> _Builder: ...


class _Client(Protocol):
    def table(self, name: str) -> _Table: ...


class SupabaseSessionData:
    """Read-only adapter that hydrates a tmp session-dir for one run id."""

    def __init__(self, client: _Client, run_id: str):
        self._client = client
        self._run_id = run_id

    @contextmanager
    def materialize(self) -> Iterator[Path]:
        """Write the run's files + transcript to a fresh tmp dir.

        Yields the tmp dir as a `Path` for the duration of the `with` block,
        then deletes it. Aggregator-friendly shape: `<tmp>/<rel_path>` matches
        exactly what the on-disk session-dir has.
        """
        tmp = tempfile.TemporaryDirectory(prefix=f"dr-{self._run_id}-")
        try:
            dest = Path(tmp.name)
            self._write_files(dest)
            self._write_transcript(dest)
            yield dest
        finally:
            tmp.cleanup()

    def _write_files(self, dest: Path) -> None:
        offset = 0
        while True:
            res = (
                self._client.table("session_files")
                .select("path,content")
                .eq("run_id", self._run_id)
                .order("path")
                .range(offset, offset + SESSION_FILE_PAGE_SIZE - 1)
                .execute()
            )
            rows = res.data or []
            for row in rows:
                target = dest / row["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(row["content"], encoding="utf-8")
            if len(rows) < SESSION_FILE_PAGE_SIZE:
                break
            offset += SESSION_FILE_PAGE_SIZE

    def _write_transcript(self, dest: Path) -> None:
        """Reconstruct transcript.jsonl from the events table.

        Always writes the file (even if zero rows) so the aggregator's
        `_read_transcript` doesn't trip on a missing file.
        """
        target = dest / "transcript.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as f:
            offset = 0
            while True:
                res = (
                    self._client.table("events")
                    .select("seq,ts,kind,payload")
                    .eq("run_id", self._run_id)
                    .order("seq")
                    .range(offset, offset + EVENT_PAGE_SIZE - 1)
                    .execute()
                )
                rows = res.data or []
                for row in rows:
                    record = dict(row.get("payload") or {})
                    record["ts"] = row["ts"]
                    record["event"] = row["kind"]
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                if len(rows) < EVENT_PAGE_SIZE:
                    break
                offset += EVENT_PAGE_SIZE


def latest_event_seq(client: _Client, run_id: str) -> int:
    """Return the largest `seq` for `run_id`, or -1 if no events.

    Used by the polled-SSE loop to detect "anything new since last snapshot".
    """
    res = (
        client.table("events")
        .select("seq")
        .eq("run_id", run_id)
        .order("seq", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return -1
    return int(rows[0]["seq"])
