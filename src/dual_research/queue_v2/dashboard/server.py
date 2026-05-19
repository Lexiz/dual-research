"""Queue-v2 dashboard — FastAPI server on port 8089.

Endpoints
---------

    GET  /                — the static dashboard HTML page
    GET  /state.json      — single-shot snapshot of the queue state +
                            per-step medians + per-spec detail
    GET  /events          — Server-Sent Events stream; emits a `tick`
                            every 1s carrying the same snapshot

The left panel reads ``state.queue + state.completed + state.active``
to render the 13-row spec list. The right panel reads
``state.active.steps`` against ``timings.all_medians()`` to render the
8-row lifecycle table with status / avg / elapsed / detail columns.

When the queue is empty (``state.queue == [] and state.active is None``),
the dashboard collapses to a terminal-summary view (computed from
``timings.json``).
"""

from __future__ import annotations

import asyncio
import json
import statistics
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from dual_research.queue_v2 import state, timings

STATIC_DIR = Path(__file__).parent / "static"
PORT = 8089

app = FastAPI(title="dual-research queue v2 dashboard")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/state.json")
def state_json() -> JSONResponse:
    return JSONResponse(_snapshot())


@app.get("/events")
async def events() -> StreamingResponse:
    async def gen():
        last: str = ""
        while True:
            payload = json.dumps(_snapshot())
            # Heartbeat every tick so the live elapsed counter updates client-side.
            if payload != last:
                yield f"event: state\ndata: {payload}\n\n"
                last = payload
            else:
                yield ": tick\n\n"
            await asyncio.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# -- snapshot --------------------------------------------------------------


def _snapshot() -> dict:
    s = state.load()
    medians = timings.all_medians()
    elapsed = state.elapsed_seconds_for_active_step()

    payload: dict = {
        "queue": s.queue,
        "completed": s.completed,
        "active": s.active,
        "failure": s.failure,
        "step_order": list(state.STEP_ORDER),
        "step_labels": dict(state.STEP_LABEL),
        "medians_s": medians,
        "active_step_elapsed_s": elapsed,
        "terminal": _terminal_summary() if s.active is None and not s.queue else None,
    }
    return payload


def _terminal_summary() -> dict | None:
    s = state.load()
    if s.queue or s.active is not None:
        return None
    payload = timings.load()
    summary: dict[str, dict[str, int | None]] = {}
    for step in state.STEP_ORDER:
        vals = payload["step_durations"].get(step, [])
        if not vals:
            summary[step] = {"avg": None, "median": None, "max": None}
            continue
        summary[step] = {
            "avg": int(statistics.mean(vals)),
            "median": int(statistics.median(vals)),
            "max": int(max(vals)),
        }
    total_specs = len(s.completed)
    total_time_s = sum(
        sum(payload["step_durations"].get(st, [])) for st in state.STEP_ORDER
    )
    return {
        "total_specs": total_specs,
        "total_time_s": total_time_s,
        "per_step": summary,
    }


def run(port: int = PORT) -> None:
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


__all__ = ["PORT", "app", "run"]
