"""Derive the UI's ``RunError[]`` from transcript events.

The UI taxonomy in ``~/Trimble/handoff/README.md`` §5.3 lists seven codes:
``STREAM_DISCONNECTED``, ``RATE_LIMIT_EXCEEDED``, ``CONTEXT_OVERFLOW``,
``TIMEOUT_EXCEEDED``, ``INVALID_TURN_FORMAT``, ``CHECKPOINT_WRITE_FAILED``,
``ORCHESTRATOR_PANIC``.

The backend at v0.9.0 emits four error-shaped events: ``repair_invoked``,
``soft_cap_hit``, ``hard_cap_hit``, and ``run_failed``. We map these four
into the closest UI codes. The remaining UI codes are placeholders that
don't fire until / unless the backend grows new event types (future spec).

The rate-limit retries inside ``with_rate_limit_retry`` happen silently and
do not surface as events; that's the main thing missing from the live feed
today.
"""

from __future__ import annotations

from dual_research.ui.labels import phase_to_int, ui_agent
from dual_research.ui.models import RunError

# Map transcript ``event`` discriminator → (UI code, severity, resolved).
EVENT_TO_ERROR: dict[str, tuple[str, str, str]] = {
    "repair_invoked": ("INVALID_TURN_FORMAT", "error", "recovered"),
    "soft_cap_hit": ("SOFT_CAP_HIT", "warning", "recovered"),
    "hard_cap_hit": ("HARD_CAP_HIT", "warning", "halted"),
    "run_failed": ("ORCHESTRATOR_PANIC", "critical", "halted"),
}


def derive_errors(
    *, transcript: list[dict], run_id: str, display_id: str
) -> list[RunError]:
    """Build the ``Run.errors`` list from a transcript event log.

    ``run_id`` is the canonical session-dir name; ``display_id`` is what the
    UI shows in the per-row ``runId`` field.
    """
    out: list[RunError] = []
    seq = 0
    for event in transcript:
        kind = event.get("event")
        if kind not in EVENT_TO_ERROR:
            continue
        seq += 1
        code, severity, resolved = EVENT_TO_ERROR[kind]
        agent_be = event.get("agent")
        agent = ui_agent(agent_be) if agent_be else None
        phase_str = event.get("phase")
        phase_int = phase_to_int(phase_str) if isinstance(phase_str, str) else None
        round_n = event.get("round")
        summary, detail = _summary_detail(kind, event)
        retried = int(event.get("budget_remaining", 0)) if kind == "repair_invoked" else 0

        out.append(
            RunError(
                id=f"{display_id}-e{seq:03d}",
                timestamp=event.get("ts", ""),
                rel_ago=0,  # server fills in at serialization
                code=code,
                severity=severity,  # type: ignore[arg-type]
                run_id=display_id,
                agent=agent,
                phase=phase_int,
                where=_where(phase_int, round_n, agent),
                summary=summary,
                detail=detail,
                retried=retried,
                resolved=resolved,  # type: ignore[arg-type]
            )
        )
    return out


def _where(phase: int | None, round_n: int | None, agent: str | None) -> str:
    parts: list[str] = []
    if phase is not None:
        parts.append(f"phase-{phase}")
    if round_n is not None:
        parts.append(f"round-{round_n}")
    if agent is not None:
        parts.append(agent)
    return " / ".join(parts) if parts else "orchestrator"


def _summary_detail(kind: str, event: dict) -> tuple[str, str]:
    """Format the one-line summary and multi-line detail for an event."""
    if kind == "repair_invoked":
        errors = event.get("errors") or []
        if isinstance(errors, list):
            joined = "; ".join(str(e) for e in errors)
        else:
            joined = str(errors)
        summary = "Agent emitted malformed turn; reprompted with format reminder."
        detail = (
            f"Repair turn invoked.\n"
            f"Reported errors: {joined or '(none)'}\n"
            f"Repair budget remaining: {event.get('budget_remaining', '?')}"
        )
        return summary, detail

    if kind == "soft_cap_hit":
        cap = event.get("cap", "?")
        rnd = event.get("round", "?")
        return (
            f"Soft cap reached at round {rnd} (cap={cap}); continuing.",
            (
                f"Soft cap is informational. The phase keeps running until the hard cap.\n"
                f"Round: {rnd}\nCap: {cap}"
            ),
        )

    if kind == "hard_cap_hit":
        cap = event.get("cap", "?")
        rnd = event.get("round", "?")
        return (
            f"Hard cap reached at round {rnd} (cap={cap}); run halted.",
            (
                f"Hard cap reached — the phase failed to converge and the run terminated.\n"
                f"Round: {rnd}\nCap: {cap}\n"
                f"A deadlock-appendix final.md was emitted with the unresolved disagreements."
            ),
        )

    if kind == "run_failed":
        err_type = event.get("error_type", "Unknown")
        message = event.get("message", "")
        phase = event.get("phase_reached", "?")
        return (
            f"Orchestrator failure: {err_type}",
            f"Phase reached: {phase}\nError type: {err_type}\nMessage: {message}",
        )

    return ("", "")
