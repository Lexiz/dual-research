"""FastAPI server that exposes the UI aggregator over HTTP + SSE.

Boots with::

    dual-research serve [--port 6173] [--host 127.0.0.1] [--runs-dir PATH]

Endpoints
---------

- ``GET  /api/health``                                  liveness + version
- ``GET  /api/runs``                                    list rows
- ``GET  /api/runs/{run_id}``                           full Run snapshot
- ``GET  /api/runs/{run_id}/stream``                    SSE; full snapshot per
                                                        transcript-file change
- ``GET  /api/runs/{run_id}/files/{path:path}``         markdown body
- ``GET  /``  + ``/static/*``                           UI bundle (spec 0011)

JSON wire format
----------------

Python uses snake_case throughout. The wire format is camelCase, applied as a
recursive translation at the JSON boundary. ``TokenUsage.in_`` becomes ``in``.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

try:
    from watchfiles import awatch  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover — dependency declared in pyproject
    awatch = None  # type: ignore[assignment]

from dual_research import __version__
from dual_research.config import resolve_paths
from dual_research.ui import load_run_snapshot, summarize_run
from dual_research.ui.models import to_jsonable

# ─── App + state ──────────────────────────────────────────────────────────────


def _make_app(runs_dir: Path) -> FastAPI:
    """Build a FastAPI app bound to a specific ``runs_dir``.

    Factory style so tests can spin up multiple apps over tmp directories
    without leaking state between tests.
    """
    app = FastAPI(
        title="dual-research UI",
        version=__version__,
        docs_url=None,  # no Swagger UI in v1; the API surface is small
        redoc_url=None,
    )
    app.state.runs_dir = runs_dir

    # ─── API routes ───────────────────────────────────────────────────────────

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "runsDir": str(runs_dir),
        }

    @app.get("/api/runs")
    async def list_runs() -> JSONResponse:
        rows: list[dict[str, Any]] = []
        if runs_dir.exists():
            for entry in sorted(runs_dir.iterdir(), reverse=True):
                if not entry.is_dir():
                    continue
                if not (entry / "state.json").exists() and not (entry / "brief.md").exists():
                    # Not a session dir — skip stray folders.
                    continue
                try:
                    row = summarize_run(entry)
                    rows.append(_to_camel(dataclasses.asdict(row)))
                except Exception:
                    # Defensive: one malformed session dir shouldn't 500 the list.
                    continue
        return JSONResponse(rows)

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> JSONResponse:
        session = _resolve_session(runs_dir, run_id)
        run = load_run_snapshot(session)
        return JSONResponse(_to_camel(to_jsonable(run)))

    @app.get("/api/runs/{run_id}/stream")
    async def stream_run(run_id: str, request: Request) -> EventSourceResponse:
        session = _resolve_session(runs_dir, run_id)
        return EventSourceResponse(_run_event_stream(session, request))

    @app.get("/api/runs/{run_id}/files/{path:path}")
    async def get_file(run_id: str, path: str) -> PlainTextResponse:
        session = _resolve_session(runs_dir, run_id)
        body = _read_scoped_file(session, path)
        return PlainTextResponse(body, media_type="text/plain; charset=utf-8")

    # ─── Static UI ────────────────────────────────────────────────────────────

    # Mount LAST so it doesn't shadow the API routes above.
    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _resolve_session(runs_dir: Path, run_id: str) -> Path:
    """Resolve a run id to its session directory, with path-traversal guards."""
    if not run_id or run_id in ("..", ".") or "/" in run_id or "\\" in run_id:
        raise HTTPException(status_code=404, detail="not found")
    session = (runs_dir / run_id).resolve()
    base = runs_dir.resolve()
    if not str(session).startswith(str(base) + os.sep) and session != base:
        raise HTTPException(status_code=404, detail="not found")
    if not session.is_dir():
        raise HTTPException(status_code=404, detail="not found")
    return session


_ALLOWED_FILE_EXT = {".md", ".json", ".jsonl", ".txt"}


def _read_scoped_file(session: Path, rel_path: str) -> str:
    """Read ``session/rel_path`` after verifying it stays inside ``session``.

    404s on traversal, non-allowed extensions, missing files, and binaries.
    """
    target = (session / rel_path).resolve()
    base = session.resolve()
    if not str(target).startswith(str(base) + os.sep) and target != base:
        raise HTTPException(status_code=404, detail="not found")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="not found")
    if target.suffix not in _ALLOWED_FILE_EXT:
        raise HTTPException(status_code=404, detail="not found")
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise HTTPException(status_code=404, detail="not found")


async def _run_event_stream(session: Path, request: Request) -> AsyncIterator[dict]:
    """Yield ``snapshot`` SSE frames whenever the transcript file changes."""
    # Initial frame: whatever is on disk right now.
    yield _snapshot_frame(session)

    if awatch is None:  # pragma: no cover — watchfiles is a declared dep
        return

    # awatch yields a set of (Change, path) tuples per batch.
    try:
        async for changes in awatch(session, stop_event=None):
            if await request.is_disconnected():
                break
            if any(p.endswith("transcript.jsonl") for _, p in changes):
                yield _snapshot_frame(session)
    except asyncio.CancelledError:
        # Client disconnected mid-await — normal termination.
        return


def _snapshot_frame(session: Path) -> dict:
    """Build one SSE frame containing a full ``Run`` snapshot."""
    run = load_run_snapshot(session)
    return {
        "event": "snapshot",
        "data": json.dumps(_to_camel(to_jsonable(run))),
    }


# ─── snake_case → camelCase translation ──────────────────────────────────────


_SNAKE_RE = re.compile(r"_([a-zA-Z])")


def _snake_to_camel(name: str) -> str:
    """``"phase_timings"`` → ``"phaseTimings"``. Single-trailing-underscore
    fields (``in_``) lose the trailing underscore."""
    if name.endswith("_") and not name.endswith("__"):
        name = name[:-1]
    return _SNAKE_RE.sub(lambda m: m.group(1).upper(), name)


def _to_camel(obj: Any) -> Any:
    """Recursively rewrite string dict keys snake_case → camelCase.

    Non-string keys (e.g. the ``int`` keys in ``phase_timings``) are coerced
    to ``str`` so the result is JSON-serializable directly. List order and
    primitive values are preserved.
    """
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str):
                out[_snake_to_camel(k)] = _to_camel(v)
            else:
                out[str(k)] = _to_camel(v)
        return out
    if isinstance(obj, list):
        return [_to_camel(v) for v in obj]
    return obj


# ─── CLI entry point ──────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dual-research serve",
        description="Run the dual-research monitoring UI server.",
    )
    p.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1).")
    p.add_argument("--port", type=int, default=6173, help="Bind port (default 6173).")
    p.add_argument(
        "--runs-dir",
        metavar="PATH",
        help="Where to read session directories from. Default: <project>/runs/.",
    )
    p.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload (dev only).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``dual-research serve``."""
    import uvicorn

    parser = _build_parser()
    args = parser.parse_args(argv)

    paths = resolve_paths(args.runs_dir)
    runs_dir = paths.runs_dir.resolve()

    print(
        f"dual-research UI server v{__version__}\n"
        f"  runs-dir: {runs_dir}\n"
        f"  listening on http://{args.host}:{args.port}\n",
        file=sys.stderr,
    )

    # Build the app eagerly (catches config errors before uvicorn starts).
    app = _make_app(runs_dir)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


__all__ = ["main", "_make_app"]
