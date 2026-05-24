"""Compute canonical dev-cycle stage states from event sidecar data.

Used by ``render_dashboard.py`` to populate the in-flight hero's stage timeline
(spec 0153). The eleven canonical stages map 1:1 to the breakpoints in the
``/dev-next`` skill flow (spec 0152 §2.7).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Literal

StageStatus = Literal["done", "curr", "queued", "fail"]


@dataclass(frozen=True)
class StageDef:
    name: str
    event: str
    failure_event: str | None = None
    failure_aliases: tuple[str, ...] = ()


STAGES: tuple[StageDef, ...] = (
    StageDef("Pre-flight", "preflight_ok", failure_aliases=("preflight", "pre-flight")),
    StageDef("Read handoff", "handoff_read", failure_aliases=("read_handoff",)),
    StageDef("Read spec", "spec_read", failure_aliases=("read_spec",)),
    StageDef("Reconcile", "reconcile_complete", "reconcile_failed", failure_aliases=("reconcile",)),
    StageDef("Branch", "branched", failure_aliases=("branch",)),
    StageDef("Implement", "implement_complete", failure_aliases=("implement",)),
    StageDef("Test", "tests_green", "tests_failed", failure_aliases=("tests", "test")),
    StageDef("PR", "pr_opened", failure_aliases=("pr",)),
    StageDef("Merge", "merged", failure_aliases=("merge",)),
    StageDef("Deploy", "deployed", failure_aliases=("deploy",)),
    StageDef("Handoff", "handoff_written", failure_aliases=("handoff",)),
)

TOLERATED_NON_STAGE_STEPS: frozenset[str] = frozenset(
    {
        "queued",
        "in_progress",
        "failed",
        "cycle_started",
        # Spec 0163 — informational markers within existing stages, pushed
        # live to main during the branch phase. They don't anchor new stages.
        "planning_started",
        "implementing_started",
        "tests_started",
        "deploy_started",
        "deploy_health_check_ok",
        # Spec 0186 / 0192 — L-spec checkpoint cadence: a session may halt
        # mid-implement and a later session resumes from the recorded
        # subsection. Neither event anchors a canonical stage.
        "checkpoint_written",
        "resume_started",
        # Spec 0199 — `/spec-next` re-IDs a queued spec as a decimal child
        # of the in-flight spec; the emitted event marks the renaming.
        "promoted_as_next",
    }
)

# Spec 0163 §2.3 — human-readable labels for the "currently: ..." tag on the
# in-flight hero. Kept in sync with STEP_LABELS at the top of
# DASHBOARD_BOOTSTRAP_JS in render_dashboard.py.
STEP_LABELS: dict[str, str] = {
    "queued": "queued",
    "cycle_started": "starting",
    "preflight_ok": "pre-flight",
    "handoff_read": "reading handoff",
    "spec_read": "reading spec",
    "planning_started": "planning",
    "reconcile_complete": "reconciled",
    "in_progress": "starting",
    "branched": "branched",
    "implementing_started": "implementing",
    "implement_complete": "implement done",
    "tests_started": "testing",
    "tests_green": "tests green",
    "pr_opened": "PR opened",
    "merged": "merged",
    "deploy_started": "deploying",
    "deployed": "deployed",
    "deploy_health_check_ok": "health check ok",
    "handoff_written": "handoff written",
    "checkpoint_written": "checkpoint",
    "resume_started": "resuming",
    "promoted_as_next": "promoted as next",
}


@dataclass
class StageState:
    name: str
    status: StageStatus
    event: dict[str, Any] | None
    duration_seconds: int | None
    note: str
    # Wall-clock instant this stage began — equal to the prior stage's event
    # timestamp (or the cycle anchor for stage 0). Used by the live ticker in
    # render_dashboard.py (spec 0156) to compute incrementing durations
    # client-side without a server roundtrip.
    started_at: dt.datetime | None = None


def _parse_ts(raw: str | None) -> dt.datetime | None:
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _note_for(stage: StageDef, ev: dict[str, Any] | None) -> str:
    if ev is None:
        return ""
    data = ev.get("data") or {}
    if stage.event == "preflight_ok":
        return "main clean · no open spec/* PRs · no in-flight specs"
    if stage.event == "handoff_read":
        return str(data.get("path", ""))
    if stage.event == "spec_read":
        path = data.get("path", "")
        lines = data.get("lines")
        type_ = data.get("type", "")
        bits = [str(path)]
        if lines:
            bits.append(f"{lines} lines")
        if type_:
            bits.append(str(type_))
        return " · ".join(b for b in bits if b)
    if stage.event == "reconcile_complete":
        mech = data.get("mechanical", 0)
        sem = data.get("semantic", 0)
        verdict = data.get("verdict", "")
        return f"{mech} mechanical patches · {sem} semantic drift · {verdict}".rstrip(" ·")
    if stage.event == "branched":
        branch = data.get("branch", "")
        frm = data.get("from", "")
        if frm:
            return f"{branch} from {frm}"
        return str(branch)
    if stage.event == "implement_complete":
        lines = data.get("lines_changed")
        files = data.get("files_changed")
        commits = data.get("commits")
        parts = []
        if lines is not None and files is not None:
            parts.append(f"{lines} lines changed across {files} files")
        if commits is not None:
            parts.append(f"{commits} commits on branch")
        return " · ".join(parts)
    if stage.event == "tests_green":
        passed = data.get("passed")
        failed = data.get("failed", 0)
        if passed is not None:
            return f"{passed} passed · {failed} failed"
        return "all tests passed"
    if stage.event == "pr_opened":
        return str(data.get("url", ""))
    if stage.event == "merged":
        return "admin squash + delete branch"
    if stage.event == "deployed":
        v = data.get("version")
        return f"fly deploy · v{v} live" if v else "fly deploy"
    if stage.event == "handoff_written":
        return str(data.get("path", ""))
    return ""


def _normalize_failure(failure_step: str | None) -> int | None:
    if not failure_step:
        return None
    key = failure_step.strip().lower().replace(" ", "_").replace("-", "_")
    for i, stage in enumerate(STAGES):
        norm_name = stage.name.lower().replace(" ", "_").replace("-", "_")
        if key == norm_name or key in stage.failure_aliases:
            return i
    return None


def compute_stages(
    spec_id: str,
    events: list[dict[str, Any]],
    *,
    failure_step: str | None = None,
    now: dt.datetime | None = None,
) -> tuple[list[StageState], list[str]]:
    """Return one StageState per canonical stage, plus a list of unknown event step names.

    Algorithm:

    - A stage is ``done`` when its ``event`` step appears in ``events``.
    - The ``curr`` (current) stage is the lowest-indexed stage that hasn't fired
      *and* whose prior stage either has fired or is the first stage.
    - All stages after ``curr`` are ``queued``.
    - If ``failure_step`` is set, that stage becomes ``fail`` and all later
      stages stay ``queued``. There is no ``curr`` in a failed cycle.

    Duration heuristic: a stage's ``duration_seconds`` is the elapsed time
    between the prior stage's event timestamp and this stage's event timestamp.
    For the current stage, if ``now`` is provided, duration is ``now`` minus the
    prior stage's timestamp (live elapsed).
    """
    known_steps: set[str] = set()
    for s in STAGES:
        known_steps.add(s.event)
        if s.failure_event:
            known_steps.add(s.failure_event)

    by_step: dict[str, dict[str, Any]] = {}
    unknown_events: list[str] = []
    for ev in events:
        step = ev.get("step", "")
        if not step:
            continue
        if step in known_steps or step in TOLERATED_NON_STAGE_STEPS:
            by_step.setdefault(step, ev)
        else:
            unknown_events.append(step)

    fail_idx = _normalize_failure(failure_step)

    # Cycle anchor for stage 0's prior timestamp. Preference order (spec 0156):
    #   1. `cycle_started` — emitted at the top of /dev-next step 1, the
    #      canonical "agent began work" marker. Set this and the pre-flight
    #      stage gets a real, non-zero duration.
    #   2. `queued` — fallback for specs that pre-date `cycle_started`. Mixes
    #      queue-dwell time into pre-flight duration but is non-zero and
    #      broadly correct for historical specs.
    #   3. `in_progress` — last-resort fallback. Before spec 0156 this was
    #      the only anchor; /dev-next emits it in step 12 *alongside* the
    #      buffered early events, so anchoring here clipped pre-flight,
    #      read-handoff, and read-spec durations to 0.
    anchor_ev = (
        by_step.get("cycle_started")
        or by_step.get("queued")
        or by_step.get("in_progress")
    )
    prev_ts = _parse_ts(anchor_ev.get("ts")) if anchor_ev else None

    # Find current stage index (lowest-index stage not done, where prior is done or i==0).
    curr_idx: int | None = None
    if fail_idx is None:
        for i, stage in enumerate(STAGES):
            if stage.event in by_step:
                continue
            if i == 0 or STAGES[i - 1].event in by_step:
                curr_idx = i
                break

    states: list[StageState] = []
    for i, stage in enumerate(STAGES):
        ev = by_step.get(stage.event)
        if ev:
            status: StageStatus = "done"
        elif fail_idx is not None and i == fail_idx:
            status = "fail"
        elif curr_idx is not None and i == curr_idx:
            status = "curr"
        else:
            status = "queued"

        stage_started_at = prev_ts  # The instant this stage began.
        duration: int | None = None
        if ev is not None:
            ev_ts = _parse_ts(ev.get("ts"))
            if ev_ts and prev_ts:
                duration = max(0, int((ev_ts - prev_ts).total_seconds()))
            if ev_ts:
                prev_ts = ev_ts
        elif status == "curr" and now is not None and prev_ts is not None:
            duration = max(0, int((now - prev_ts).total_seconds()))

        states.append(
            StageState(
                name=stage.name,
                status=status,
                event=ev,
                duration_seconds=duration,
                note=_note_for(stage, ev),
                started_at=stage_started_at,
            )
        )

    return states, unknown_events


def current_stage_label(states: list[StageState]) -> tuple[int, str] | None:
    """Return (1-based step number, stage name) for the current stage, or None."""
    for i, s in enumerate(states, start=1):
        if s.status == "curr":
            return i, s.name
        if s.status == "fail":
            return i, s.name
    return None
