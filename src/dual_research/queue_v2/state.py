"""Shared queue state — `queue/state.json` plus per-spec run directories.

state.json shape:

    {
      "queue": ["0092", "0093", ..., "0104"],
      "completed": ["0091"],
      "active": {
        "spec": "0092",
        "slug": "m3-token-foundation",
        "branch": "spec/0092-m3-token-foundation",
        "started_at": "2026-05-19T07:14:02Z",
        "step": "4_implement",
        "step_started_at": "2026-05-19T07:18:11Z",
        "steps": {
          "1_read":      {"status": "done",        "started_at": "...", "ended_at": "...", "duration_s": 3},
          "2_reason":    {"status": "done",        "started_at": "...", "ended_at": "...", "duration_s": 107},
          "3_rewrite":   {"status": "skipped",     "detail": "no rewrite needed"},
          "4_implement": {"status": "in_progress", "started_at": "..."},
          "5_verify":    {"status": "pending"},
          "6_pr":        {"status": "pending"},
          "7_deploy":    {"status": "pending"},
          "8_handover":  {"status": "pending"}
        },
        "detail": {
          "2_reason":    {"alignment_note_count": 0},
          "3_rewrite":   {"reason": "no alignment notes"},
          "4_implement": {"diff": "+342 -89 (4 files)"},
          "5_verify":    {"rows_passed": 0, "rows_total": 6}
        }
      },
      "failure": null
    }

The whole file is replaced atomically on every write (tempfile + rename).
A separate per-spec ``queue/runs/<NNNN>/events.jsonl`` carries the
append-only stream the dashboard tails via SSE.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STEP_ORDER: tuple[str, ...] = (
    "1_read",
    "2_reason",
    "3_rewrite",
    "4_implement",
    "5_verify",
    "6_pr",
    "7_deploy",
    "8_handover",
)
STEP_LABEL: dict[str, str] = {
    "1_read": "Read",
    "2_reason": "Reason",
    "3_rewrite": "Rewrite",
    "4_implement": "Implement",
    "5_verify": "Verify",
    "6_pr": "PR",
    "7_deploy": "Deploy",
    "8_handover": "Handover",
}


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def queue_root(repo_root: Path | None = None) -> Path:
    repo = repo_root or _detect_repo_root()
    out = repo / "queue"
    out.mkdir(parents=True, exist_ok=True)
    return out


def run_dir(spec: str, repo_root: Path | None = None) -> Path:
    out = queue_root(repo_root) / "runs" / spec
    out.mkdir(parents=True, exist_ok=True)
    (out / "screenshots").mkdir(exist_ok=True)
    return out


def state_path(repo_root: Path | None = None) -> Path:
    return queue_root(repo_root) / "state.json"


def _detect_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root from queue_v2.state")


@dataclass
class State:
    queue: list[str]
    completed: list[str]
    active: dict[str, Any] | None
    failure: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "queue": list(self.queue),
            "completed": list(self.completed),
            "active": self.active,
            "failure": self.failure,
        }


def load(repo_root: Path | None = None) -> State:
    p = state_path(repo_root)
    if not p.exists():
        return State(queue=[], completed=[], active=None, failure=None)
    raw = json.loads(p.read_text())
    return State(
        queue=list(raw.get("queue", [])),
        completed=list(raw.get("completed", [])),
        active=raw.get("active"),
        failure=raw.get("failure"),
    )


def save(s: State, repo_root: Path | None = None) -> None:
    p = state_path(repo_root)
    tmp = p.with_suffix(f".tmp.{uuid.uuid4().hex}")
    tmp.write_text(json.dumps(s.to_dict(), indent=2) + "\n")
    os.replace(tmp, p)


def init_queue(specs: list[str], repo_root: Path | None = None) -> State:
    """Seed state.json with the given spec list. Idempotent — preserves
    a previously-started run if state.json already exists and matches."""
    p = state_path(repo_root)
    if p.exists():
        s = load(repo_root)
        existing = set(s.queue) | set(s.completed) | (
            {s.active["spec"]} if s.active else set()
        )
        if set(specs).issubset(existing):
            return s
    s = State(queue=list(specs), completed=[], active=None, failure=None)
    save(s, repo_root)
    return s


def begin_spec(spec: str, slug: str, branch: str, repo_root: Path | None = None) -> State:
    s = load(repo_root)
    if s.active is not None and s.active.get("spec") != spec:
        raise RuntimeError(
            f"spec {s.active['spec']} is already active — finish or fail it first"
        )
    if spec in s.queue:
        s.queue.remove(spec)
    s.active = {
        "spec": spec,
        "slug": slug,
        "branch": branch,
        "started_at": utcnow_iso(),
        "step": None,
        "step_started_at": None,
        "steps": {step: {"status": "pending"} for step in STEP_ORDER},
        "detail": {},
    }
    save(s, repo_root)
    _emit(spec, {"kind": "spec_begin", "spec": spec, "slug": slug, "branch": branch})
    return s


def begin_step(step: str, repo_root: Path | None = None) -> State:
    assert step in STEP_ORDER, f"unknown step {step}"
    s = load(repo_root)
    if s.active is None:
        raise RuntimeError("no active spec — call begin_spec first")
    spec = s.active["spec"]
    s.active["step"] = step
    s.active["step_started_at"] = utcnow_iso()
    s.active["steps"][step] = {
        "status": "in_progress",
        "started_at": utcnow_iso(),
    }
    save(s, repo_root)
    _emit(spec, {"kind": "step_begin", "step": step})
    return s


def end_step(
    step: str,
    status: str = "done",
    detail: dict[str, Any] | None = None,
    repo_root: Path | None = None,
) -> State:
    assert step in STEP_ORDER
    assert status in {"done", "failed", "skipped"}
    s = load(repo_root)
    if s.active is None:
        raise RuntimeError("no active spec — call begin_spec first")
    spec = s.active["spec"]
    step_state = s.active["steps"].get(step, {})
    started = step_state.get("started_at")
    ended = utcnow_iso()
    duration_s = _delta_seconds(started, ended) if started else 0
    step_state.update(
        {
            "status": status,
            "started_at": started,
            "ended_at": ended,
            "duration_s": duration_s,
        }
    )
    s.active["steps"][step] = step_state
    if detail is not None:
        s.active["detail"][step] = detail
    s.active["step"] = None
    s.active["step_started_at"] = None
    if status == "failed":
        s.failure = {"step": step, "spec": spec, "at": ended, "detail": detail}
    save(s, repo_root)
    _emit(
        spec,
        {
            "kind": "step_end",
            "step": step,
            "status": status,
            "duration_s": duration_s,
            "detail": detail or {},
        },
    )
    # Skipped or done steps with non-zero duration feed the rolling-median pool.
    if status == "done" and duration_s > 0:
        from dual_research.queue_v2 import timings as t

        t.record(step, duration_s, repo_root=repo_root)
    return s


def finish_spec(repo_root: Path | None = None) -> State:
    s = load(repo_root)
    if s.active is None:
        raise RuntimeError("no active spec")
    spec = s.active["spec"]
    s.completed.append(spec)
    _emit(spec, {"kind": "spec_end", "spec": spec})
    s.active = None
    save(s, repo_root)
    return s


def _delta_seconds(start_iso: str | None, end_iso: str | None) -> int:
    if not start_iso or not end_iso:
        return 0
    a = datetime.strptime(start_iso, "%Y-%m-%dT%H:%M:%SZ")
    b = datetime.strptime(end_iso, "%Y-%m-%dT%H:%M:%SZ")
    return int((b - a).total_seconds())


def _emit(spec: str, event: dict[str, Any], repo_root: Path | None = None) -> None:
    line = {"at": utcnow_iso(), **event}
    fp = run_dir(spec, repo_root) / "events.jsonl"
    with fp.open("a") as f:
        f.write(json.dumps(line) + "\n")


def elapsed_seconds_for_active_step(repo_root: Path | None = None) -> int | None:
    """Live-counter helper used by the dashboard SSE feed."""
    s = load(repo_root)
    if s.active is None or s.active.get("step_started_at") is None:
        return None
    start_s = datetime.strptime(
        s.active["step_started_at"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    return int((datetime.now(timezone.utc) - start_s).total_seconds())


# Test helper — never use outside tests.
def _reset_for_test(repo_root: Path) -> None:
    p = state_path(repo_root)
    if p.exists():
        p.unlink()


__all__ = [
    "STEP_ORDER",
    "STEP_LABEL",
    "State",
    "begin_spec",
    "begin_step",
    "end_step",
    "finish_spec",
    "init_queue",
    "load",
    "queue_root",
    "run_dir",
    "save",
    "state_path",
    "utcnow_iso",
    "elapsed_seconds_for_active_step",
]
