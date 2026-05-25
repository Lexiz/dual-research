"""Compute canonical dev-cycle stage states from event sidecar data.

Used by ``render_dashboard.py`` to populate the in-flight hero's stage timeline
(spec 0153). Seven canonical stages map 1:1 to the spans the ``/dev-next`` skill
actually emits after specs 0211 + 0212 (spec 0213 §2.1).

Each ``StageDef`` carries a ``(start_event, end_event)`` pair. A stage's duration
is ``end_event.ts − start_event.ts``. The single-event-per-stage model used
pre-0213 is gone: it dishonestly collapsed three rows that ticked in one refresh
(Read handoff / Read spec / Reconcile — buffered, then flushed at the branch
push) and misattributed the Branch row's duration when the prior row's anchor
moved underneath it.

**Spec 0212 buffer-events doctrine — intentional simultaneity.** The post-merge
events ``deploy_started``, ``deployed``, ``deploy_health_check_ok``, and
``handoff_written`` are buffered local-only and flushed atomically at /dev-next
step 23. The dashboard regenerates from a single push, so the Deploy and Handoff
rows necessarily tick at the same ``/api/data`` refresh. This is correct
behavior — do not try to interleave them.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Literal

StageStatus = Literal["done", "curr", "queued", "fail"]


@dataclass(frozen=True)
class StageDef:
    name: str
    start_event: str
    end_event: str
    failure_event: str | None = None
    failure_aliases: tuple[str, ...] = ()


# Seven honest spans, one ``(start_event, end_event)`` pair per row.
# Pre-flight's start anchor (`cycle_started`) is also the cycle anchor so
# the first row works under the same algorithm as the rest. Each row's bar
# duration is ``end_ts − start_ts``; the legacy "cumulative chain" fallback
# only kicks in for historical specs missing the new start_event (see
# ``compute_stages``).
STAGES: tuple[StageDef, ...] = (
    StageDef("Pre-flight",  "cycle_started", "preflight_ok",       failure_aliases=("preflight", "pre-flight")),
    StageDef("Read & plan", "handoff_read",  "reconcile_complete", "reconcile_failed",
             failure_aliases=("read_handoff", "read_spec", "reconcile", "read_plan", "read_&_plan")),
    StageDef("Implement",   "branched",      "implement_complete",
             failure_aliases=("branch", "branched", "implement")),
    StageDef("Test",        "tests_started", "tests_green",        "tests_failed",
             failure_aliases=("tests", "test")),
    StageDef("Ship",        "pr_opened",     "merged",
             failure_aliases=("pr", "merge", "ship")),
    StageDef("Deploy",      "merged",        "deployed",           failure_aliases=("deploy",)),
    StageDef("Handoff",     "deployed",      "handoff_written",    failure_aliases=("handoff",)),
)

TOLERATED_NON_STAGE_STEPS: frozenset[str] = frozenset(
    {
        "queued",
        "in_progress",
        "failed",
        "cycle_started",
        # Spec 0213 — `spec_read` no longer anchors a stage (Read & plan
        # spans `handoff_read → reconcile_complete`), but /dev-next still
        # emits it during the read-and-plan phase. Tolerate so it doesn't
        # show up in `unknown_events`.
        "spec_read",
        # Spec 0163 — informational markers within existing stages, pushed
        # live to main during the branch phase. They don't anchor new stages.
        "planning_started",
        "implementing_started",
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


def _note_for(stage: StageDef, by_step: dict[str, dict[str, Any]]) -> str:
    """Compose the per-row "currently/last:" note keyed off the row's end_event.

    Notes consolidate when subspans merged in spec 0213:
      - Read & plan: handoff path + spec path + reconcile verdict in one line.
      - Implement: branch name prepended to the lines/files/commits summary.
      - Ship: PR url + admin-squash note.
      - Deploy: ``fly deploy · vN.N.N live`` (spec 0211 left this wording
        accurate — the dashboard names the build, not the deployer).
    """
    end_ev = by_step.get(stage.end_event)
    if end_ev is None:
        return ""
    end_data = end_ev.get("data") or {}

    if stage.end_event == "preflight_ok":
        return "main clean · no open spec/* PRs · no in-flight specs"

    if stage.end_event == "reconcile_complete":
        # Spec 0213 §2.5 — consolidate handoff_read + spec_read + reconcile
        # notes into one Read & plan summary keyed off the end_event.
        handoff_data = (by_step.get("handoff_read") or {}).get("data") or {}
        spec_data = (by_step.get("spec_read") or {}).get("data") or {}
        bits: list[str] = []
        if handoff_path := handoff_data.get("path"):
            bits.append(f"handoff: {handoff_path}")
        if spec_path := spec_data.get("path"):
            bits.append(f"spec: {spec_path}")
        mech = end_data.get("mechanical", 0)
        sem = end_data.get("semantic", 0)
        verdict = end_data.get("verdict", "")
        bits.append(f"{mech} mechanical · {sem} semantic")
        if verdict:
            bits.append(str(verdict))
        return " · ".join(bits)

    if stage.end_event == "implement_complete":
        # Spec 0213 §2.5 — prepend the branch name to the implement summary.
        branch_data = (by_step.get("branched") or {}).get("data") or {}
        branch = branch_data.get("branch", "")
        lines = end_data.get("lines_changed")
        files = end_data.get("files_changed")
        commits = end_data.get("commits")
        bits: list[str] = []
        if branch:
            bits.append(str(branch))
        if lines is not None and files is not None:
            bits.append(f"{lines} lines / {files} files")
        elif files is not None:
            bits.append(f"{files} files")
        if commits is not None:
            bits.append(f"{commits} commits")
        return " · ".join(bits)

    if stage.end_event == "tests_green":
        passed = end_data.get("passed")
        failed = end_data.get("failed", 0)
        if passed is not None:
            return f"{passed} passed · {failed} failed"
        return "all tests passed"

    if stage.end_event == "merged":
        # Spec 0213 §2.5 — Ship row consolidates pr_opened + merged.
        pr_data = (by_step.get("pr_opened") or {}).get("data") or {}
        url = pr_data.get("url") or end_data.get("pr") or ""
        if url:
            return f"PR {url} · admin squash + delete branch"
        return "admin squash + delete branch"

    if stage.end_event == "deployed":
        v = end_data.get("version")
        return f"fly deploy · v{v} live" if v else "fly deploy"

    if stage.end_event == "handoff_written":
        return str(end_data.get("path", ""))

    return ""


def _normalize_failure(failure_step: str | None) -> int | None:
    if not failure_step:
        return None
    key = failure_step.strip().lower().replace(" ", "_").replace("-", "_")
    for i, stage in enumerate(STAGES):
        norm_name = stage.name.lower().replace(" ", "_").replace("-", "_").replace("&", "and")
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

    Algorithm (spec 0213 §2.2):

    - A stage is ``done`` when its ``end_event`` step appears in ``events``.
    - The ``curr`` (current) stage is the lowest-indexed stage that hasn't
      ended *and* whose prior stage either has ended or is the first stage.
    - All stages after ``curr`` are ``queued``.
    - If ``failure_step`` is set, that stage becomes ``fail`` and all later
      stages stay ``queued``. There is no ``curr`` in a failed cycle.

    Duration model: each row is a span ``end_event.ts − start_event.ts``.
    For the current stage, if ``now`` is provided, duration is ``now`` minus
    the stage's start anchor (live elapsed).

    Legacy fallback: if ``start_event`` is missing on a historical or
    in-flight spec (events emitted before spec 0213 landed), use the prior
    row's ``end_event`` timestamp as the start anchor — preserves non-zero
    durations on historical spec pages instead of clipping every row to 0.
    """
    known_steps: set[str] = set()
    for s in STAGES:
        known_steps.add(s.start_event)
        known_steps.add(s.end_event)
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

    # Cycle anchor — used both as Pre-flight's start_event (it is
    # `cycle_started` by definition in the new model) and as the legacy
    # fallback when a stage's start_event is missing. Preference order
    # (spec 0156 carried forward):
    #   1. `cycle_started` — emitted at the top of /dev-next step 1.
    #   2. `queued` — fallback for specs that pre-date `cycle_started`.
    #   3. `in_progress` — last-resort fallback.
    cycle_anchor_ev = (
        by_step.get("cycle_started")
        or by_step.get("queued")
        or by_step.get("in_progress")
    )
    cycle_anchor_ts = _parse_ts(cycle_anchor_ev.get("ts")) if cycle_anchor_ev else None

    # Find current stage index (lowest-index stage whose end_event hasn't
    # fired, where prior is done or i==0).
    curr_idx: int | None = None
    if fail_idx is None:
        for i, stage in enumerate(STAGES):
            if stage.end_event in by_step:
                continue
            if i == 0 or STAGES[i - 1].end_event in by_step:
                curr_idx = i
                break

    states: list[StageState] = []
    prev_end_ts: dt.datetime | None = cycle_anchor_ts
    for i, stage in enumerate(STAGES):
        end_ev = by_step.get(stage.end_event)
        if end_ev:
            status: StageStatus = "done"
        elif fail_idx is not None and i == fail_idx:
            status = "fail"
        elif curr_idx is not None and i == curr_idx:
            status = "curr"
        else:
            status = "queued"

        # Start anchor preference (spec 0213 §2.2):
        #   1. The stage's own `start_event` from `by_step`.
        #   2. Legacy fallback: prior row's end_event timestamp (cumulative
        #      chain) for historical specs that pre-date spec 0213.
        #   3. Pre-flight specifically uses the cycle anchor as start.
        start_ev = by_step.get(stage.start_event)
        if start_ev is not None:
            start_ts = _parse_ts(start_ev.get("ts"))
        elif i == 0:
            start_ts = cycle_anchor_ts
        else:
            start_ts = prev_end_ts

        end_ts: dt.datetime | None = None
        duration: int | None = None
        if end_ev is not None:
            end_ts = _parse_ts(end_ev.get("ts"))
            if end_ts and start_ts:
                duration = max(0, int((end_ts - start_ts).total_seconds()))
        elif status == "curr" and now is not None and start_ts is not None:
            duration = max(0, int((now - start_ts).total_seconds()))

        states.append(
            StageState(
                name=stage.name,
                status=status,
                event=end_ev,
                duration_seconds=duration,
                note=_note_for(stage, by_step),
                started_at=start_ts,
            )
        )

        # Advance the prior-end anchor for the next iteration's legacy
        # fallback. Use the end_event if present, else fall back to keeping
        # the previous anchor (so a missing middle stage doesn't reset to
        # None and cascade-zero subsequent durations).
        if end_ts is not None:
            prev_end_ts = end_ts

    return states, unknown_events


def current_stage_label(states: list[StageState]) -> tuple[int, str] | None:
    """Return (1-based step number, stage name) for the current stage, or None."""
    for i, s in enumerate(states, start=1):
        if s.status == "curr":
            return i, s.name
        if s.status == "fail":
            return i, s.name
    return None
