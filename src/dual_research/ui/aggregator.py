"""Read a session directory and produce a UI-shaped ``Run``.

Three entry points:

- :func:`load_run_snapshot` — full replay; call once per fresh request.
- :func:`apply_event` — incremental update; one transcript event at a time.
- :func:`summarize_run` — cheap one-row summary for the runs list.

The aggregator is the single seam where backend vocabulary (``"openai"``,
``"phase2"``) is translated to UI vocabulary (``"gpt"``, ``2``).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from dual_research.persistence.state import SessionState
from dual_research.protocol.parse import extract_summary, synthesise_brief_tldr
from dual_research.ui.disagreements import mark_deadlocked_open, reconstruct
from dual_research.ui.errors import derive_errors
from dual_research.ui.labels import (
    derive_agent_status,
    derive_run_status,
    display_id_for,
    phase_to_int,
    ui_agent,
)
from dual_research.ui.turn_stats import build_phase_stats
from dual_research.ui.models import (
    AgentState,
    Disagreement,
    Run,
    RunListRow,
    TopLevelError,
    Turn,
)

# ─── Public entry points ──────────────────────────────────────────────────────


def load_run_snapshot(session_dir: Path) -> Run:
    """Build a complete ``Run`` for ``session_dir`` by replaying its transcript.

    Works for both in-flight and completed runs (it just reads disk state).
    """
    run = _empty_run(session_dir)
    run.topic = _read_topic(session_dir / "brief.md")
    run.started_at = _earliest_event_ts(session_dir / "transcript.jsonl")

    transcript = _read_transcript(session_dir / "transcript.jsonl")
    for event in transcript:
        apply_event(run, event, session_dir)

    _augment_from_state_json(run, session_dir / "state.json")
    _populate_current_bodies(run, session_dir)

    # Disagreements: reconstruct after replay so all rounds are visible.
    p2 = reconstruct(session_dir, phase=2)
    p4 = reconstruct(session_dir, phase=4)
    hard_cap_hit = any(e.get("event") == "hard_cap_hit" for e in transcript)
    run.disagreements = mark_deadlocked_open(p2 + p4, hard_cap_hit=hard_cap_hit)

    # When the parser found nothing, scan the round files for raw `D-<digit>`
    # anchors. If any are present, the agents *did* emit disagreements that we
    # failed to recognise — the UI surfaces a one-line footer in that case so
    # the empty explorer doesn't masquerade as "no disagreements at all".
    if not run.disagreements:
        run.disagreements_parse_suspected_miss = _scan_disagreement_anchors(session_dir)

    run.errors = derive_errors(
        transcript=transcript, run_id=run.id, display_id=run.display_id
    )

    run.phase_stats = build_phase_stats(session_dir)

    # Summary cards (spec 0025): heuristic TL;DR of brief.md + extracted
    # `## Summary` sections from every completed turn file.
    run.brief_summary = _read_brief_summary(session_dir)
    run.phase_summaries = _read_phase_summaries(session_dir)

    # started_at_ago is "now" relative to the earliest event.
    run.started_at_ago = _seconds_since(run.started_at)
    return run


def apply_event(run: Run, event: dict, session_dir: Path) -> Run:
    """Mutate ``run`` in place with a single transcript event.

    Returns the same ``run`` for ergonomic chaining. Unknown events are
    ignored (the backend may add new ones without breaking this layer).
    """
    kind = event.get("event")

    if kind == "run_started":
        _on_run_started(run, event)
    elif kind == "phase_entered":
        _on_phase_entered(run, event)
    elif kind == "phase_exited":
        _on_phase_exited(run, event)
    elif kind == "turn_started":
        _on_turn_started(run, event)
    elif kind == "turn_ended":
        _on_turn_ended(run, event)
    elif kind in ("phase2_round_complete", "phase4_round_complete"):
        _on_round_complete(run, event)
    elif kind == "phase2_complete":
        _on_phase2_complete(run, event)
    elif kind == "phase4_draft_revised":
        # Drafter emitted a new draft version mid-phase 4.
        # We don't store the draft index on the Run; the UI fetches the file
        # bodies directly via /api/runs/:id/files/...
        pass
    elif kind == "final_emitted":
        _on_final_emitted(run, event)
    elif kind == "run_completed":
        _on_run_completed(run, event)
    elif kind == "run_failed":
        _on_run_failed(run, event)
    elif kind == "hard_cap_hit":
        run.status = "deadlocked"
    # Other events (cost_update, soft_cap_hit, repair_invoked,
    # drafter_tiebreak_resolved, phase{0,1,3}_complete) carry information
    # already covered by other code paths.

    return run


def summarize_run(session_dir: Path) -> RunListRow:
    """Cheap summary row — no transcript replay, no disagreement parse.

    Reads ``state.json`` + ``metrics.json`` + ``brief.md`` (H1 only).
    """
    state = _read_state(session_dir / "state.json")
    metrics = _read_metrics(session_dir / "metrics.json")
    topic = _read_topic(session_dir / "brief.md")

    phase_int = phase_to_int(state.phase if state else "phase0")
    started_at = _earliest_event_ts(session_dir / "transcript.jsonl")
    duration = _duration_seconds(session_dir / "transcript.jsonl")

    final_emitted = bool(state and state.final_emitted_to)
    # Detect hard-cap / failure cheaply by scanning the transcript tail.
    hard_cap_hit, run_failed = _scan_terminal_signals(session_dir / "transcript.jsonl")
    status = derive_run_status(
        state_phase=state.phase if state else "phase0",
        final_emitted=final_emitted,
        hard_cap_hit=hard_cap_hit,
        run_failed=run_failed,
    )

    cost = float(metrics.get("total_cost_usd", 0.0)) if metrics else 0.0
    if cost == 0.0:
        # metrics.json may reflect only a resume window with no new calls;
        # fall back to scanning the transcript for turn_ended cost_usd.
        cost = _sum_transcript_cost(session_dir / "transcript.jsonl")

    # Round counter for Phase 2/4 rows. Soft cap isn't in state.json; we
    # default to 6 (the CLI default). A Phase 2/4 row with no round files yet
    # shows "0/6" rather than dropping the cell.
    rounds: str | None = None
    if phase_int in (2, 4):
        cur = _latest_round_for(session_dir, phase_int) or 0
        rounds = f"{cur}/6"

    return RunListRow(
        id=session_dir.name,
        display_id=display_id_for(session_dir),
        status=status,  # type: ignore[arg-type]
        phase=phase_int,
        topic=topic,
        started_at_ago=_seconds_since(started_at),
        started_at=started_at,
        duration=duration,
        cost=cost,
        rounds=rounds,
    )


# ─── Event handlers (mutate ``run`` in place) ─────────────────────────────────


def _on_run_started(run: Run, event: dict) -> None:
    # ``session_dir`` in the event is the absolute path; we already have id/display_id.
    run.round.soft = int(event.get("soft_cap", run.round.soft))
    run.round.hard = int(event.get("hard_cap", run.round.hard))
    # Stash model ids on each agent so the UI can show real names.
    run.agents["claude"].model_id = event.get("claude_model")
    run.agents["gpt"].model_id = event.get("openai_model")
    run.status = "running"


def _on_phase_entered(run: Run, event: dict) -> None:
    phase_str = event.get("phase", "phase0")
    run.phase = phase_to_int(phase_str)
    # Reset round counter when entering a new round-based phase.
    if phase_str in ("phase2", "phase4"):
        run.round.current = 0
    _refresh_agent_statuses(run, phase_str)


def _on_phase_exited(run: Run, event: dict) -> None:
    phase_str = event.get("phase", "phase0")
    duration_ms = int(event.get("duration_ms", 0))
    phase_int = phase_to_int(phase_str)
    if phase_int in run.phase_timings:
        run.phase_timings[phase_int] = duration_ms // 1000


def _on_turn_started(run: Run, event: dict) -> None:
    backend_ag = event.get("agent")
    if backend_ag not in ("claude", "openai"):
        return
    ag = ui_agent(backend_ag)
    other = "gpt" if ag == "claude" else "claude"
    phase_str = event.get("phase", "phase0")
    is_drafter = (run.drafter == ag) if run.drafter else False
    run.agents[ag].status = derive_agent_status(
        phase=phase_str, agent_active=True, is_drafter=is_drafter
    )
    # The other agent steps to "waiting" unless they're also running
    # (Phase 0/1 are parallel — handled by their own turn_started events).
    if run.agents[other].status not in ("thinking", "drafting", "responding", "reviewing"):
        run.agents[other].status = derive_agent_status(
            phase=phase_str,
            agent_active=False,
            is_drafter=(run.drafter == other) if run.drafter else False,
        )


def _on_turn_ended(run: Run, event: dict) -> None:
    backend_ag = event.get("agent")
    if backend_ag not in ("claude", "openai"):
        return
    ag = ui_agent(backend_ag)
    state = run.agents[ag]
    state.tokens.in_ += int(event.get("input_tokens", 0))
    state.tokens.out += int(event.get("output_tokens", 0))
    state.cost += float(event.get("cost_usd", 0.0))
    phase_str = event.get("phase", "phase0")
    is_drafter = (run.drafter == ag) if run.drafter else False
    state.status = derive_agent_status(
        phase=phase_str, agent_active=False, is_drafter=is_drafter
    )
    # last_turn placeholder — body is filled by _populate_current_bodies.
    label = event.get("label") or ""
    idx = _round_index_from_label(label)
    state.last_turn = Turn(
        kind=_turn_kind_for_phase(phase_str, ag, is_drafter=is_drafter),
        index=idx,
    )


def _on_round_complete(run: Run, event: dict) -> None:
    run.round.current = int(event.get("round", run.round.current))
    # Capture drafter when phase2_round_complete carries a stable signal.
    if event.get("event") == "phase2_round_complete":
        # Backend reports per-agent proposed drafter; the canonical drafter
        # is set on phase2_complete. Ignore mid-round proposals here.
        pass


def _on_phase2_complete(run: Run, event: dict) -> None:
    drafter_be = event.get("drafter")
    if drafter_be in ("claude", "openai"):
        run.drafter = ui_agent(drafter_be)


def _on_final_emitted(run: Run, event: dict) -> None:
    # confidence: 'HIGH' | 'MODERATE' | 'LOW' — not currently displayed but
    # could feed a future "confidence" pill. Ignored for now.
    pass


def _on_run_completed(run: Run, event: dict) -> None:
    exit_code = int(event.get("exit_code", 0))
    if exit_code == 0:
        run.status = "completed"
    elif exit_code == 51:
        run.status = "deadlocked"
    elif exit_code in (1, 2, 52):
        run.status = "errored"
    # All agents go idle on terminal.
    for ag in run.agents.values():
        ag.status = "idle"


def _on_run_failed(run: Run, event: dict) -> None:
    run.status = "errored"
    run.error = TopLevelError(
        when=event.get("ts", ""),
        where=event.get("phase_reached", "orchestrator"),
        code=event.get("error_type", "ORCHESTRATOR_PANIC"),
        detail=event.get("message", ""),
    )
    for ag in run.agents.values():
        ag.status = "idle"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _empty_run(session_dir: Path) -> Run:
    return Run(
        id=session_dir.name,
        display_id=display_id_for(session_dir),
    )


def _read_topic(brief_path: Path) -> str:
    """First H1 in brief.md; falls back to first non-empty line; finally empty."""
    if not brief_path.exists():
        return ""
    try:
        text = brief_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    # Fallback: first non-empty line.
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:200]
    return ""


def _read_transcript(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return out


def _read_state(state_path: Path) -> SessionState | None:
    if not state_path.exists():
        return None
    try:
        return SessionState.from_json(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, KeyError, ValueError):
        return None


def _read_metrics(metrics_path: Path) -> dict | None:
    if not metrics_path.exists():
        return None
    try:
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _augment_from_state_json(run: Run, state_path: Path) -> None:
    """Pick up drafter / phase from state.json after the replay (state.json
    is more authoritative than transcript order for the final drafter).
    """
    state = _read_state(state_path)
    if state is None:
        return
    if state.drafter in ("claude", "openai"):
        run.drafter = ui_agent(state.drafter)
    if state.phase == "done":
        run.phase = 5
        # final_emitted_to set means a final.md was written.
        if state.final_emitted_to and run.status not in ("errored", "deadlocked"):
            run.status = "completed"


def _earliest_event_ts(transcript_path: Path) -> str | None:
    """ISO timestamp of the first event in transcript.jsonl."""
    if not transcript_path.exists():
        return None
    try:
        with transcript_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    return json.loads(line).get("ts")
                except json.JSONDecodeError:
                    continue
    except OSError:
        return None
    return None


def _seconds_since(ts: str | None) -> int:
    if not ts:
        return 0
    try:
        dt = datetime.fromisoformat(ts)
        now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
        return max(0, int((now - dt).total_seconds()))
    except ValueError:
        return 0


def _duration_seconds(transcript_path: Path) -> int:
    """Seconds between the earliest and latest event in transcript.jsonl."""
    if not transcript_path.exists():
        return 0
    earliest: str | None = None
    latest: str | None = None
    try:
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ts = json.loads(line).get("ts")
            except json.JSONDecodeError:
                continue
            if ts is None:
                continue
            if earliest is None:
                earliest = ts
            latest = ts
    except OSError:
        return 0
    if not earliest or not latest:
        return 0
    try:
        a = datetime.fromisoformat(earliest)
        b = datetime.fromisoformat(latest)
        return max(0, int((b - a).total_seconds()))
    except ValueError:
        return 0


def _sum_transcript_cost(transcript_path: Path) -> float:
    """Sum ``cost_usd`` across all ``turn_ended`` events in the transcript."""
    if not transcript_path.exists():
        return 0.0
    total = 0.0
    try:
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event") == "turn_ended":
                total += float(event.get("cost_usd", 0.0))
    except OSError:
        return 0.0
    return total


def _scan_terminal_signals(transcript_path: Path) -> tuple[bool, bool]:
    """Tail-scan the transcript for ``hard_cap_hit`` / ``run_failed`` markers."""
    hard_cap = False
    run_failed = False
    if not transcript_path.exists():
        return False, False
    try:
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event") == "hard_cap_hit":
                hard_cap = True
            elif event.get("event") == "run_failed":
                run_failed = True
    except OSError:
        return False, False
    return hard_cap, run_failed


_ROUND_RE = re.compile(r"round-(\d+)-(?:claude|openai)\.md$")


def _latest_round_for(session_dir: Path, phase_int: int) -> int | None:
    phase_dir = session_dir / f"phase{phase_int}"
    if not phase_dir.exists():
        return None
    best: int | None = None
    for entry in phase_dir.iterdir():
        m = _ROUND_RE.search(entry.name)
        if not m:
            continue
        n = int(m.group(1))
        if best is None or n > best:
            best = n
    return best


# Map phase + role → the ``Turn.kind`` string the UI consumes.
def _turn_kind_for_phase(phase: str, ui_ag: str, *, is_drafter: bool) -> str:
    if phase == "phase0":
        return "thinking"
    if phase == "phase1":
        return "plan-draft"
    if phase == "phase2":
        return "response"
    if phase == "phase3":
        return "doc-draft" if is_drafter else "idle"
    if phase == "phase4":
        return "doc-draft" if is_drafter else "review"
    return "idle"


def _round_index_from_label(label: str) -> int:
    """Extract the round number from a turn label like ``"phase2-claude-round-3"``."""
    m = re.search(r"round[-_](\d+)", label)
    return int(m.group(1)) if m else 0


def _refresh_agent_statuses(run: Run, phase_str: str) -> None:
    """Recompute both agents' status when the phase changes (no turn is active)."""
    for ui_ag in ("claude", "gpt"):
        is_drafter = (run.drafter == ui_ag) if run.drafter else False
        run.agents[ui_ag].status = derive_agent_status(
            phase=phase_str, agent_active=False, is_drafter=is_drafter
        )


# ─── Current-turn body population ─────────────────────────────────────────────


def _populate_current_bodies(run: Run, session_dir: Path) -> None:
    """Fill ``agents[X].current_turn.body`` from the latest written round file.

    This is the v1 stand-in for live token streaming: as soon as a turn's
    round file is on disk, its body is visible. Earlier turns' bodies are
    served on-demand via the file endpoint (spec 0010).
    """
    if run.phase == 0:
        # Phase 0: each agent's preflight critique.
        _set_body_if_present(run, "claude", session_dir / "phase0" / "preflight-claude.md", kind="thinking")
        _set_body_if_present(run, "gpt", session_dir / "phase0" / "preflight-openai.md", kind="thinking")
    elif run.phase == 1:
        _set_body_if_present(run, "claude", session_dir / "phase1" / "draft-claude.md", kind="plan-draft")
        _set_body_if_present(run, "gpt", session_dir / "phase1" / "draft-openai.md", kind="plan-draft")
    elif run.phase == 2:
        rnd = _latest_round_for(session_dir, 2) or 0
        _set_body_if_present(run, "claude", session_dir / "phase2" / f"round-{rnd:02d}-claude.md", kind="response", index=rnd)
        _set_body_if_present(run, "gpt", session_dir / "phase2" / f"round-{rnd:02d}-openai.md", kind="response", index=rnd)
    elif run.phase == 3:
        # Only the drafter writes in Phase 3.
        if run.drafter:
            be_ag = "claude" if run.drafter == "claude" else "openai"
            _set_body_if_present(
                run,
                run.drafter,
                session_dir / "phase3" / "draft-v1.md",
                kind="doc-draft",
                index=1,
            )
    elif run.phase == 4:
        rnd = _latest_round_for(session_dir, 4) or 0
        _set_body_if_present(run, "claude", session_dir / "phase4" / f"round-{rnd:02d}-claude.md", kind=_turn_kind_for_phase("phase4", "claude", is_drafter=run.drafter == "claude"), index=rnd)
        _set_body_if_present(run, "gpt", session_dir / "phase4" / f"round-{rnd:02d}-openai.md", kind=_turn_kind_for_phase("phase4", "gpt", is_drafter=run.drafter == "gpt"), index=rnd)
    elif run.phase == 5:
        # Show the final draft body on the drafter's slot for the "Done" view.
        if run.drafter:
            _set_body_if_present(
                run,
                run.drafter,
                session_dir / "final.md",
                kind="doc-draft",
            )


def _set_body_if_present(
    run: Run, ui_ag: str, path: Path, *, kind: str, index: int = 0
) -> None:
    if not path.exists():
        return
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return
    run.agents[ui_ag].current_turn = Turn(kind=kind, index=index, body=body)


_DASH_DIGIT_RE = re.compile(r"\bD-\d+\b")
_ROUND_FILE_RE = re.compile(r"^round-(\d+)-(claude|openai)\.md$")


def _read_brief_summary(session_dir: Path) -> str | None:
    """Heuristic TL;DR for brief.md — spec 0025."""
    brief_path = session_dir / "brief.md"
    if not brief_path.exists():
        return None
    try:
        text = brief_path.read_text(encoding="utf-8")
    except OSError:
        return None
    # If the brief itself has an explicit `## Summary` heading, prefer that.
    explicit = extract_summary(text)
    if explicit:
        return explicit
    return synthesise_brief_tldr(text)


def _read_phase_summaries(session_dir: Path) -> dict[str, str]:
    """Walk every turn file and pull each agent's `## Summary` section.

    Keys are stable for the UI to look up:
        phase0_<agent>            (preflight critique)
        phase1_<agent>            (research draft)
        phase2_round{R}_<agent>   (negotiate turns)
        phase3                    (converged draft — no agent split)
        phase4_round{R}_<agent>   (review turns)
    """
    out: dict[str, str] = {}

    # Phase 0 — preflight critiques (one per agent).
    for agent in ("claude", "openai"):
        path = session_dir / "phase0" / f"preflight-{agent}.md"
        _maybe_set_summary(out, f"phase0_{_ui_agent(agent)}", path)

    # Phase 1 — research drafts.
    for agent in ("claude", "openai"):
        path = session_dir / "phase1" / f"draft-{agent}.md"
        _maybe_set_summary(out, f"phase1_{_ui_agent(agent)}", path)

    # Phase 2 and 4 — turn-based; enumerate every round file on disk.
    for phase in (2, 4):
        phase_dir = session_dir / f"phase{phase}"
        if not phase_dir.exists():
            continue
        for entry in sorted(phase_dir.iterdir()):
            if not entry.is_file() or not entry.name.endswith(".md"):
                continue
            if ".malformed" in entry.name:
                continue
            m = _ROUND_FILE_RE.match(entry.name)
            if not m:
                continue
            round_n = int(m.group(1))
            agent = m.group(2)
            key = f"phase{phase}_round{round_n}_{_ui_agent(agent)}"
            _maybe_set_summary(out, key, entry)

    # Phase 3 — single converged draft. No agent split; the summary if
    # any is the drafter's.
    p3 = session_dir / "phase3" / "draft-v1.md"
    _maybe_set_summary(out, "phase3", p3)

    # Final.md — synthesise via the same `## Summary` extractor; if the
    # final doc carries one (e.g. an executive summary section), the
    # final card gets a TL;DR for free.
    final_path = session_dir / "final.md"
    _maybe_set_summary(out, "final", final_path)

    return out


def _maybe_set_summary(target: dict[str, str], key: str, path: Path) -> None:
    if not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    summary = extract_summary(text)
    if summary:
        target[key] = summary


def _ui_agent(backend_agent: str) -> str:
    """Backend writes `claude` / `openai`; UI vocabulary is `claude` / `gpt`."""
    return "gpt" if backend_agent == "openai" else backend_agent


def _scan_disagreement_anchors(session_dir: Path) -> bool:
    """Cheap probe: does any Phase 2/4 round file contain a literal ``D-<digit>``?

    Used to distinguish "parser missed everything" from "agents had nothing to
    disagree about". Reads at most ~12 files, opens them once, short-circuits
    on first hit.
    """
    for phase in (2, 4):
        phase_dir = session_dir / f"phase{phase}"
        if not phase_dir.exists():
            continue
        for entry in phase_dir.iterdir():
            if not entry.is_file() or not entry.name.endswith(".md"):
                continue
            if ".malformed" in entry.name:
                continue
            try:
                text = entry.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if _DASH_DIGIT_RE.search(text):
                return True
    return False
