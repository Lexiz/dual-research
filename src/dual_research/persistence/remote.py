"""Push a completed session directory to Supabase.

Spec 0019. Mirrors the on-disk session-dir into three tables:
- runs           — metadata (state.json + metrics.json folded in as JSONB)
- events         — append-only mirror of transcript.jsonl, one row per line
- session_files  — every text artifact under the dir (markdown, json, jsonl)

Idempotent: re-pushing the same session-dir upserts every row by primary key,
so partial-push retries are safe.

The supabase-py client is injected (rather than constructed inside the class)
so unit tests can pass a fake in-memory client. See tests/persistence/test_remote.py.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Protocol


EVENT_BATCH_SIZE = 500
FILE_BATCH_SIZE = 50
BLOB_BATCH_SIZE = 20
SESSION_FILE_GLOBS = ("*.md", "*.json", "*.jsonl")

_SESSION_ID_RE = re.compile(r"^(\d{8})-(\d{6})-(.+)$")
_CONFIDENCE_RE = re.compile(r"\*\*(HIGH|MODERATE|LOW)\s+confidence\*\*", re.IGNORECASE)


class _Table(Protocol):
    def upsert(self, rows: list[dict[str, Any]], on_conflict: str) -> Any: ...


class _Client(Protocol):
    def table(self, name: str) -> _Table: ...


@dataclass(frozen=True)
class PushSummary:
    run_id: str
    runs_upserted: int
    events_upserted: int
    files_upserted: int
    duration_ms: int
    blobs_upserted: int = 0


class RemoteSession:
    """Bulk-push a session-dir to Supabase via the supabase-py client."""

    def __init__(self, client: _Client):
        self._client = client

    @classmethod
    def from_credentials(cls, url: str, service_role_key: str) -> "RemoteSession":
        # Imported lazily so the test suite can run without the dep present.
        from supabase import create_client

        return cls(create_client(url, service_role_key))

    def push_session_dir(self, session_dir: Path) -> PushSummary:
        session_dir = session_dir.resolve()
        if not session_dir.is_dir():
            raise FileNotFoundError(f"Not a directory: {session_dir}")

        run_id = session_dir.name
        started = datetime.now(timezone.utc)

        state_path = session_dir / "state.json"
        if not state_path.exists():
            raise FileNotFoundError(
                f"Missing state.json in {session_dir} — not a completed session dir."
            )
        state = json.loads(state_path.read_text(encoding="utf-8"))

        metrics_path = session_dir / "metrics.json"
        metrics: dict[str, Any] | None = (
            json.loads(metrics_path.read_text(encoding="utf-8"))
            if metrics_path.exists()
            else None
        )

        final_path = session_dir / "final.md"
        final_md = final_path.read_text(encoding="utf-8") if final_path.exists() else ""

        transcript_path = session_dir / "transcript.jsonl"
        event_rows, run_started, run_completed = _read_transcript(run_id, transcript_path)

        run_row = _build_run_row(
            run_id, state, metrics, final_md, run_started, run_completed
        )
        self._client.table("runs").upsert([run_row], on_conflict="id").execute()

        events_count = 0
        for batch in _batch(iter(event_rows), EVENT_BATCH_SIZE):
            self._client.table("events").upsert(
                batch, on_conflict="run_id,seq"
            ).execute()
            events_count += len(batch)

        files_count = 0
        for batch in _batch(_iter_file_rows(run_id, session_dir), FILE_BATCH_SIZE):
            self._client.table("session_files").upsert(
                batch, on_conflict="run_id,path"
            ).execute()
            files_count += len(batch)

        # Spec 0025 — binary attachment blobs under session_dir/attachments/.
        # attachments.json (the metadata index) is already a .json under
        # the session-dir and flows through session_files above.
        blobs_count = 0
        for batch in _batch(_iter_blob_rows(run_id, session_dir), BLOB_BATCH_SIZE):
            self._client.table("attachment_blobs").upsert(
                batch, on_conflict="run_id,rel_path"
            ).execute()
            blobs_count += len(batch)

        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return PushSummary(
            run_id=run_id,
            runs_upserted=1,
            events_upserted=events_count,
            files_upserted=files_count,
            blobs_upserted=blobs_count,
            duration_ms=duration_ms,
        )


def _build_run_row(
    run_id: str,
    state: dict[str, Any],
    metrics: dict[str, Any] | None,
    final_md: str,
    run_started: dict[str, Any] | None,
    run_completed: dict[str, Any] | None,
) -> dict[str, Any]:
    created_at = _parse_session_dir_timestamp(run_id)
    slug = _slug_from_session_dir(run_id)

    # Prefer run_completed values (canonical end-of-run truth); fall back to
    # state / metrics derivation when the transcript is incomplete.
    phase_reached = (
        (run_completed and run_completed.get("phase_reached"))
        or state.get("phase")
    )
    exit_code = run_completed.get("exit_code") if run_completed else None
    duration_ms = (
        (run_completed and run_completed.get("duration_ms"))
        or (_metrics_duration_ms(metrics) if metrics else None)
    )
    total_cost = (
        (run_completed and run_completed.get("total_cost_usd"))
        or (float(metrics["total_cost_usd"]) if metrics and "total_cost_usd" in metrics else None)
    )

    model_tier = run_started.get("model_tier") if run_started else None
    claude_model = run_started.get("claude_model") if run_started else None
    openai_model = run_started.get("openai_model") if run_started else None

    confidence_match = _CONFIDENCE_RE.search(final_md)
    confidence = confidence_match.group(1).upper() if confidence_match else None

    return {
        "id": run_id,
        "slug": slug,
        "created_at": created_at.isoformat(),
        "model_tier": model_tier,
        "claude_model": claude_model,
        "openai_model": openai_model,
        "phase_reached": phase_reached,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "total_cost_usd": total_cost,
        "confidence": confidence,
        "state": state,
        "metrics": metrics,
    }


def _parse_session_dir_timestamp(run_id: str) -> datetime:
    m = _SESSION_ID_RE.match(run_id)
    if not m:
        raise ValueError(f"Session dir name not in YYYYMMDD-HHMMSS-<slug> form: {run_id}")
    date_part, time_part, _ = m.groups()
    return datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def _slug_from_session_dir(run_id: str) -> str:
    m = _SESSION_ID_RE.match(run_id)
    return m.group(3) if m else run_id


def _metrics_duration_ms(metrics: dict[str, Any]) -> int | None:
    started_raw = metrics.get("started_at")
    ended_raw = metrics.get("ended_at")
    if not started_raw or not ended_raw:
        return None
    started = datetime.fromisoformat(started_raw)
    ended = datetime.fromisoformat(ended_raw)
    return int((ended - started).total_seconds() * 1000)


def _read_transcript(
    run_id: str,
    transcript_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[str, Any] | None]:
    """One-pass scan: build event rows; capture run_started / run_completed payloads."""
    rows: list[dict[str, Any]] = []
    run_started: dict[str, Any] | None = None
    run_completed: dict[str, Any] | None = None

    if not transcript_path.exists():
        return rows, run_started, run_completed

    with transcript_path.open("r", encoding="utf-8") as f:
        seq = 0
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            ts = record.pop("ts", None)
            kind = record.pop("event", "unknown")
            if kind == "run_started" and run_started is None:
                run_started = dict(record)
            elif kind == "run_completed":
                run_completed = dict(record)
            rows.append(
                {
                    "run_id": run_id,
                    "seq": seq,
                    "ts": ts,
                    "kind": kind,
                    "payload": record,
                }
            )
            seq += 1

    return rows, run_started, run_completed


def _iter_file_rows(run_id: str, session_dir: Path) -> Iterator[dict[str, Any]]:
    seen: set[Path] = set()
    for pattern in SESSION_FILE_GLOBS:
        for path in sorted(session_dir.rglob(pattern)):
            if path in seen:
                continue
            # Skip atomic-write tempfiles (`.<name>.<rand>`) — they aren't artifacts.
            if any(part.startswith(".") for part in path.relative_to(session_dir).parts):
                continue
            seen.add(path)
            content = path.read_text(encoding="utf-8")
            yield {
                "run_id": run_id,
                "path": str(path.relative_to(session_dir)),
                "content": content,
                "size_bytes": len(content.encode("utf-8")),
            }


def _iter_blob_rows(run_id: str, session_dir: Path) -> Iterator[dict[str, Any]]:
    """Yield rows for every file under session_dir/attachments/.

    The file is read as bytes and base64-encoded. Mime type is best-
    effort from the filename extension. The on-disk path is recorded
    as `attachments/<basename>` — `attach_local_file` already names
    files as `<sha8>-<basename>` so collisions across runs are unlikely.
    """
    import mimetypes

    att_dir = session_dir / "attachments"
    if not att_dir.exists() or not att_dir.is_dir():
        return
    for path in sorted(att_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        data = path.read_bytes()
        mime, _ = mimetypes.guess_type(path.name)
        yield {
            "run_id": run_id,
            "rel_path": f"attachments/{path.name}",
            "mime": mime or "application/octet-stream",
            "size_bytes": len(data),
            "content_b64": base64.b64encode(data).decode("ascii"),
        }


def _batch(items: Iterator[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    chunk: list[dict[str, Any]] = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
