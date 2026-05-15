"""Translation tables and derivations between backend and UI vocabulary.

The aggregator is the ONLY place that knows the backend uses ``"openai"``
while the UI uses ``"gpt"``. Everything downstream of the aggregator speaks
UI vocabulary.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from dual_research.ui.models import AgentStatus

# ─── Agent label translation ──────────────────────────────────────────────────

BACKEND_TO_UI_AGENT: dict[str, str] = {"claude": "claude", "openai": "gpt"}
UI_TO_BACKEND_AGENT: dict[str, str] = {"claude": "claude", "gpt": "openai"}


def ui_agent(backend_agent: str) -> str:
    """``"claude"`` stays ``"claude"``; ``"openai"`` becomes ``"gpt"``."""
    return BACKEND_TO_UI_AGENT.get(backend_agent, backend_agent)


def backend_agent(ui_agent_label: str) -> str:
    """Reverse translation (used when the server needs to read backend artifacts)."""
    return UI_TO_BACKEND_AGENT.get(ui_agent_label, ui_agent_label)


# ─── Phase string ↔ int ───────────────────────────────────────────────────────

PHASE_MAP: dict[str, int] = {
    "phase0": 0,
    "phase1": 1,
    "phase2": 2,
    "phase3": 3,
    "phase4": 4,
    "done": 5,
}


def phase_to_int(phase: str) -> int:
    return PHASE_MAP.get(phase, 0)


# ─── Display id ───────────────────────────────────────────────────────────────


def display_id(session_dir_name: str) -> str:
    """4-char hex id derived from the session-dir basename.

    The UI's mono cell expects a short id like ``"7f3a"``. The full
    ``YYYYMMDD-HHMMSS-<slug>`` name remains the canonical id for URLs.
    """
    return hashlib.sha1(session_dir_name.encode("utf-8")).hexdigest()[:4]


def display_id_for(session_dir: Path) -> str:
    return display_id(session_dir.name)


# ─── Agent status derivation ──────────────────────────────────────────────────


def derive_agent_status(
    *,
    phase: str,
    agent_active: bool,
    is_drafter: bool,
    phase_done: bool = False,
) -> AgentStatus:
    """Map ``(phase, role, active)`` to the UI's agent activity vocabulary.

    Truth table (matches README §3 / data.jsx sample bodies):

    | Phase | Active           | Status      |
    |-------|------------------|-------------|
    | done  | n/a              | idle        |
    | phase0| yes              | thinking    |
    | phase1| yes              | drafting    |
    | phase2| yes              | responding  |
    | phase3| yes + drafter    | drafting    |
    | phase3| yes + reviewer   | idle        |
    | phase4| yes + drafter    | drafting    |
    | phase4| yes + reviewer   | reviewing   |
    | *     | no, phase live   | waiting     |
    | *     | no, phase done   | idle        |
    """
    if phase_done or phase == "done":
        return "idle"

    if not agent_active:
        return "waiting"

    if phase == "phase0":
        return "thinking"
    if phase == "phase1":
        return "drafting"
    if phase == "phase2":
        return "responding"
    if phase == "phase3":
        return "drafting" if is_drafter else "idle"
    if phase == "phase4":
        return "drafting" if is_drafter else "reviewing"

    return "idle"


# ─── Run status derivation ────────────────────────────────────────────────────


def derive_run_status(
    *,
    state_phase: str,
    final_emitted: bool,
    hard_cap_hit: bool,
    run_failed: bool,
) -> str:
    """Derive the top-level Run.status from terminal-event presence.

    Precedence: errored > deadlocked > completed > running.
    """
    if run_failed:
        return "errored"
    if hard_cap_hit and not final_emitted:
        return "deadlocked"
    if final_emitted or state_phase == "done":
        return "completed"
    return "running"
