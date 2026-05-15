"""UI-facing read-only aggregator (spec 0009).

Reads a session directory and produces a single nested ``Run`` object that
matches the Claude Design UI shape verbatim. Pure read-side; no orchestrator
or backend changes.

Public surface:

- :func:`load_run_snapshot` — replay a full transcript into a ``Run``.
- :func:`apply_event` — incremental update for the SSE tail loop.
- :func:`summarize_run` — cheap one-row summary for the ``/api/runs`` list.

Used internally by spec 0010 (HTTP server + SSE). Not exposed on the CLI.
"""

from dual_research.ui.aggregator import (
    apply_event,
    load_run_snapshot,
    summarize_run,
)
from dual_research.ui.models import (
    AgentState,
    Budget,
    Disagreement,
    PhaseStats,
    ProgressionStep,
    Run,
    RunError,
    RunListRow,
    Round,
    Turn,
    TurnStats,
)

__all__ = [
    "AgentState",
    "Budget",
    "Disagreement",
    "PhaseStats",
    "ProgressionStep",
    "Run",
    "RunError",
    "RunListRow",
    "Round",
    "Turn",
    "TurnStats",
    "apply_event",
    "load_run_snapshot",
    "summarize_run",
]
