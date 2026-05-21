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
PIECE_BATCH_SIZE = 200
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
    # Spec 0145 — count of rows upserted into turn_prompt_pieces.
    prompt_pieces_upserted: int = 0


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
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
        else:
            # Spec 0032 — tolerate a missing state.json so --push-while-running
            # can publish in-flight runs that haven't reached their first
            # phase-boundary save yet. The orchestrator now writes an initial
            # state.json at session setup (run.py); this fallback covers
            # the edge case where a run crashes before that write lands.
            # Initial state mirrors SessionState() defaults: phase="phase0".
            state = {"phase": "phase0"}

        metrics_path = session_dir / "metrics.json"
        metrics: dict[str, Any] | None = (
            json.loads(metrics_path.read_text(encoding="utf-8"))
            if metrics_path.exists()
            else None
        )

        final_path = session_dir / "final.md"
        final_md = final_path.read_text(encoding="utf-8") if final_path.exists() else ""

        transcript_path = session_dir / "transcript.jsonl"
        event_rows, run_started, run_completed, run_failed = _read_transcript(run_id, transcript_path)

        run_row = _build_run_row(
            run_id, state, metrics, final_md, run_started, run_completed, run_failed
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

        # Spec 0145 — per-piece token attribution into turn_prompt_pieces.
        # One row per (artifact_id, tokens) pair on every turn_ended event
        # carrying a non-empty prompt_pieces dict. Attachment IDs are
        # parsed from canonical artifact_ids; display_title is resolved
        # via the contemporaneous attachments.json at push time.
        pieces_count = 0
        for batch in _batch(
            _iter_turn_prompt_pieces_rows(run_id, session_dir, event_rows),
            PIECE_BATCH_SIZE,
        ):
            self._client.table("turn_prompt_pieces").upsert(
                batch, on_conflict="run_id,turn_key,artifact_id"
            ).execute()
            pieces_count += len(batch)

        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return PushSummary(
            run_id=run_id,
            runs_upserted=1,
            events_upserted=events_count,
            files_upserted=files_count,
            blobs_upserted=blobs_count,
            prompt_pieces_upserted=pieces_count,
            duration_ms=duration_ms,
        )

    # ─── Spec 0048 — reconcile snapshots ──────────────────────────────────

    def push_reconcile_report(self, *, date: str, payload: dict[str, Any]) -> None:
        """Upsert a single ReconcileReport into the reconcile_results table.

        The table is keyed by ``date`` (UTC ISO ``YYYY-MM-DD``); re-running
        reconciliation for the same date overwrites the row, so the latest
        snapshot always wins.
        """
        row = {
            "date": date,
            "payload": payload,
            "checked_at": payload.get("checked_at")
                or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self._client.table("reconcile_results").upsert(
            [row], on_conflict="date"
        ).execute()


def _build_run_row(
    run_id: str,
    state: dict[str, Any],
    metrics: dict[str, Any] | None,
    final_md: str,
    run_started: dict[str, Any] | None,
    run_completed: dict[str, Any] | None,
    run_failed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    created_at = _parse_session_dir_timestamp(run_id)
    slug = _slug_from_session_dir(run_id)

    # Prefer run_completed values (canonical end-of-run truth); fall back to
    # run_failed when the run errored; finally to state / metrics derivation
    # when the transcript is incomplete.
    phase_reached = (
        (run_completed and run_completed.get("phase_reached"))
        or (run_failed and run_failed.get("phase_reached"))
        or state.get("phase")
    )
    # exit_code is the canonical "did the run terminate, and how" signal
    # consumed by the list-view's ``_status_from_columns``. For a clean
    # success it comes from run_completed (0 or 51 for hard-cap deadlock).
    # For a run_failed event we synthesise ``exit_code=1`` — a non-zero,
    # non-51 sentinel that maps to "errored" in the UI's derive_run_status
    # precedence (errored > deadlocked > completed > running).
    if run_completed:
        exit_code = run_completed.get("exit_code")
    elif run_failed:
        exit_code = 1
    else:
        exit_code = None
    duration_ms = (
        (run_completed and run_completed.get("duration_ms"))
        or (run_failed and run_failed.get("duration_ms"))
        or (_metrics_duration_ms(metrics) if metrics else None)
    )
    total_cost = (
        (run_completed and run_completed.get("total_cost_usd"))
        or (run_failed and run_failed.get("total_cost_usd"))
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
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """One-pass scan: build event rows; capture run_started / run_completed /
    run_failed payloads.

    ``run_failed`` is captured (alongside ``run_completed``) so the runs row
    can carry a non-None ``exit_code`` for errored runs. Without this, the
    list-view's ``_status_from_columns`` saw ``exit_code=None`` and fell
    through to "running" — the bug where the run-list said "running" while
    the run-detail view (via the aggregator that reads transcript events
    directly) said "errored"."""
    rows: list[dict[str, Any]] = []
    run_started: dict[str, Any] | None = None
    run_completed: dict[str, Any] | None = None
    run_failed: dict[str, Any] | None = None

    if not transcript_path.exists():
        return rows, run_started, run_completed, run_failed

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
            elif kind == "run_failed":
                run_failed = dict(record)
                # Preserve the originating timestamp so duration can be derived.
                if ts is not None and "ts" not in run_failed:
                    run_failed["ts"] = ts
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

    return rows, run_started, run_completed, run_failed


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


# ─── Spec 0145 — per-piece token-attribution push ─────────────────────


_ATTACHMENT_ID_PREFIX = "user_prompt.attachment."


def _load_attachments_title_map(session_dir: Path) -> dict[str, str]:
    """Read attachments.json and build a `{attachment_id: title}` map for
    `display_name()`'s `<id>` template substitution.

    Spec 0145 §5.2 — the `attachment_id` we persist in `turn_prompt_pieces`
    is derived in the orchestrator (`run.py::_attachment_id`) via the
    same logic — sha256[:8] preferred, slugified basename fallback. This
    function recomputes it from on-disk metadata so push-from-cold-disk
    yields the same IDs the live run emitted.
    """
    path = session_dir / "attachments.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    from dual_research.ingest import AttachmentBundle
    from dual_research.orchestrator.run import _attachment_id

    bundle = AttachmentBundle.from_dict(data)
    out: dict[str, str] = {}
    for ing in bundle.attachments:
        aid = _attachment_id(ing)
        out[aid] = (
            ing.title
            or Path(ing.rel_path or ing.source or "").name
            or "attachment"
        )
    return out


def _push_turn_prompt_pieces(
    run_id: str,
    turn_key: str,
    prompt_pieces: dict[str, Any],
    title_for_id: dict[str, str],
) -> Iterator[dict[str, Any]]:
    """Yield one `turn_prompt_pieces` row per `(artifact_id, tokens)` pair.

    Spec 0145 §5.2 — the helper exists separately from the inline
    iteration (Q1 resolution) so unit tests can drive it directly with
    a fake event. `attachment_id` is parsed from artifact IDs matching
    the `user_prompt.attachment.<id>` template; `display_title` is the
    `display_name()` resolution at push time.
    """
    from dual_research.contract.artifacts import display_name

    for artifact_id, raw_tokens in (prompt_pieces or {}).items():
        try:
            tokens = int(raw_tokens)
        except (TypeError, ValueError):
            continue
        attachment_id: str | None = None
        if artifact_id.startswith(_ATTACHMENT_ID_PREFIX):
            attachment_id = artifact_id[len(_ATTACHMENT_ID_PREFIX):]
        try:
            title = display_name(artifact_id, title_for_id=title_for_id)
        except Exception:
            title = artifact_id
        yield {
            "run_id": run_id,
            "turn_key": turn_key,
            "artifact_id": artifact_id,
            "tokens": tokens,
            "attachment_id": attachment_id,
            "display_title": title,
        }


def _iter_turn_prompt_pieces_rows(
    run_id: str,
    session_dir: Path,
    event_rows: list[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    """Spec 0145 §5.2 — walk the in-memory event_rows produced by
    ``_read_transcript`` and emit one row per `(turn_key, artifact_id)`
    pair extracted from every ``turn_ended`` event.

    The title map is loaded once per push (cheap — attachments.json is
    typically < 100 entries).
    """
    from dual_research.orchestrator._call import _derive_turn_key

    title_for_id = _load_attachments_title_map(session_dir)
    for row in event_rows:
        if row.get("kind") != "turn_ended":
            continue
        payload = row.get("payload") or {}
        prompt_pieces = payload.get("prompt_pieces") or {}
        if not prompt_pieces:
            continue
        agent_label = payload.get("agent") or ""
        phase = payload.get("phase") or ""
        label = payload.get("label") or ""
        if not (agent_label and phase and label):
            continue
        turn_key = _derive_turn_key(
            agent_label=agent_label, phase=phase, label=label,
        )
        yield from _push_turn_prompt_pieces(
            run_id, turn_key, prompt_pieces, title_for_id,
        )
