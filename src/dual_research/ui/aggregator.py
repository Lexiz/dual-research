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
from dataclasses import asdict

from dual_research.protocol.parse import (
    ReviewItem,
    extract_review_items,
    extract_summary,
    synthesise_brief_tldr,
)
from dual_research.ui.disagreements import mark_deadlocked_open, reconstruct
from dual_research.ledger import build_phase_ledger
from dual_research.ui.claims import reconstruct_claims
from dual_research.ui.comments import reconstruct_comments
from dual_research.ui.issues import reconstruct_issues
from dual_research.ui.questions import reconstruct_questions
from dual_research.ui.errors import derive_errors
from dual_research.ui.labels import (
    derive_agent_status,
    derive_run_status,
    display_id_for,
    phase_to_int,
    ui_agent,
)
from dual_research.ui.turn_stats import build_phase_stats
from dual_research.agents.pricing import compute_cache_savings_usd, compute_search_cost
from dual_research.config import TIERS
from dual_research.ui.models import (
    AgentBreakdown,
    AgentChip,
    AgentState,
    Disagreement,
    Run,
    RunListRow,
    RunNote,
    TopLevelError,
    Turn,
    TurnTokenUsage,
)


def _context_window_from_tier(model_id: str | None) -> int:
    """Spec 0031: derive the context-window for a given ``model_id`` by
    scanning ``config.TIERS``.

    Used as a fallback when ``RunStarted`` didn't carry the explicit
    ``{agent}_context_window`` fields (pre-0030 transcripts). Returns the
    first matching tier's value; 0 if nothing matches. The same model id
    appearing in multiple tiers is currently impossible by design, so the
    iteration order doesn't matter in practice.
    """
    if not model_id:
        return 0
    for tier in TIERS.values():
        if tier.claude.model_id == model_id:
            return tier.claude.context_window
        if tier.openai.model_id == model_id:
            return tier.openai.context_window
    return 0

# ─── Public entry points ──────────────────────────────────────────────────────


def load_run_snapshot(session_dir: Path) -> Run:
    """Build a complete ``Run`` for ``session_dir`` by replaying its transcript.

    Works for both in-flight and completed runs (it just reads disk state).
    """
    run = _empty_run(session_dir)
    run.topic = _read_topic(session_dir / "brief.md")
    run.started_at = _earliest_event_ts(session_dir / "transcript.jsonl")

    transcript = _read_transcript(session_dir / "transcript.jsonl")
    # Spec 0039 — dedupe ``turn_ended`` events by ``label`` so a
    # parse-error retry doesn't double-count its cost on the agent
    # rollup. The last occurrence per label is the canonical
    # successful attempt; earlier occurrences are skipped. Other
    # events (turn_started, turn_inputs, turn_searches, …) replay
    # in full — their dedup happens elsewhere if needed.
    transcript = _dedup_turn_ended_by_label(transcript)
    # Spec 0148 D03 — surface protocol-violation + empty-turn events
    # for the run. Both ride the spec-0122 transcript bridge so they
    # are already in ``transcript.jsonl`` (the orchestrator subscriber
    # at ``_install_transcript_bridge`` mirrors them). Filter to the
    # two kinds and pass through verbatim; the frontend joins by
    # ``phase × round × agent`` against each turn card.
    run.violations = [
        dict(ev) for ev in transcript
        if ev.get("event") in ("protocol_violation", "empty_turn_detected")
    ]
    for event in transcript:
        apply_event(run, event, session_dir)

    _augment_from_state_json(run, session_dir / "state.json")
    # Spec 0136 — re-run the unified truth table once more after state.json
    # augmentation (which can advance ``run.phase`` to 5 for runs whose
    # transcript is missing the ``final_emitted`` event but where
    # ``state.final_emitted_to`` was written). The truth table is idempotent;
    # running it again is a no-op for runs already correctly classified.
    _finalise_status(run)
    _populate_current_bodies(run, session_dir)

    # Disagreements: reconstruct after replay so all rounds are visible.
    p2 = reconstruct(session_dir, phase=2)
    p4 = reconstruct(session_dir, phase=4)
    hard_cap_hit = any(e.get("event") == "hard_cap_hit" for e in transcript)
    run.disagreements = mark_deadlocked_open(p2 + p4, hard_cap_hit=hard_cap_hit)
    # Spec 0034: thread `raised_turn_key` / `closed_turn_key` from the
    # progression steps so the UI's cross-axis click-to-highlight knows
    # which timeline card to flash for each disagreement.
    _populate_disagreement_turn_keys(run.disagreements)

    # Spec 0034: first-class Question objects from Phase 2 + Phase 4
    # ``## Open questions for X`` sections. IDs are parser-assigned;
    # answer linkage is positional with a verbatim-match confidence
    # signal (see ``ui/questions.py``).
    q2 = reconstruct_questions(session_dir, phase=2)
    q4 = reconstruct_questions(session_dir, phase=4)
    run.questions = q2 + q4
    # Spec 0041: Phase 4 Issue ledger + Comments are reconstructed
    # separately and travel on their own ``Run`` lists so the UI can
    # render them as distinct typed groups. Phase 2 occasionally
    # emits issues too; reconstruct both phases for both kinds.
    run.issues = (
        reconstruct_issues(session_dir, phase=2)
        + reconstruct_issues(session_dir, phase=4)
    )
    run.comments = (
        reconstruct_comments(session_dir, phase=2)
        + reconstruct_comments(session_dir, phase=4)
    )
    # Spec 0042 D2 + D3: first-class Claim objects from Phase 1 drafts and
    # Phase 2 R1 difference inventories. ``reconstruct_claims`` walks both
    # sources in one pass and returns them ordered by (phase, agent, idx).
    run.claims = reconstruct_claims(session_dir)

    # Anchor pre-resolution for questions: same prior-content lookup as
    # used by ``_read_phase_review_items``.
    _resolve_question_anchors(session_dir, run.questions)

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
    _item_bundle = _attach_item_aggregation(
        run, session_dir / "transcript.jsonl", session_dir=session_dir
    )

    # Summary cards (spec 0025): heuristic TL;DR of brief.md + extracted
    # `## Summary` sections from every completed turn file.
    run.brief_summary = _read_brief_summary(session_dir)
    run.phase_summaries = _read_phase_summaries(session_dir)

    # Review items (spec 0027 + 0028): structured questions /
    # disagreements extracted from every Phase 2 + Phase 4 turn body.
    run.phase_review_items = _read_phase_review_items(session_dir)
    # Latest converged-document path — used by the Phase 4 side-by-side
    # modal's left pane.
    run.current_draft_path = _find_current_draft_path(session_dir)

    # Spec 0043 D10/D11 — build the per-phase cross-round ledger from the
    # existing reconstructors + claim-escalation linkage + ghosted-rounds
    # bookkeeping. Idempotent: rebuilt on every snapshot from disk. Runs
    # AFTER phase_stats is set so the drift computation can compare
    # ledger counts to agent self-counters.
    from dataclasses import asdict as _asdict
    run.phase_ledgers = {
        2: [_asdict(e) for e in build_phase_ledger(session_dir, phase=2).entries],
        4: [_asdict(e) for e in build_phase_ledger(session_dir, phase=4).entries],
    }

    # Spec 0122 — when the spec-0114 item pipeline produced a non-empty
    # bundle (either via the transcript bridge or via the replay-from-
    # disk fallback), overwrite the legacy typed lists + phase_ledgers
    # with projections derived from the items. The legacy reconstructors
    # always return ``[]`` for v2 runs (their section regexes no longer
    # match), so this is what makes the badges/filters non-empty.
    if _item_bundle is not None and _item_bundle.items:
        from dual_research.ui.item_projection import (
            project_phase_ledgers,
            project_typed_lists,
        )
        questions, disagreements, issues, comments = project_typed_lists(_item_bundle)
        run.questions = questions
        # Preserve the deadlocked-marker pass — once disagreements come
        # from the item pipeline, the hard-cap signal flows through
        # ``Item.current_state == "capped"`` and is already reflected on
        # the projected ``Disagreement.deadlocked`` flag, but we keep
        # the old pipeline's ordering (open first, resolved second) for
        # UI consistency.
        run.disagreements = sorted(
            disagreements,
            key=lambda d: (
                0 if d.status == "open" else 1,
                d.opened_round if d.status == "open" else -(d.closed_round or 0),
            ),
        )
        run.issues = issues
        run.comments = comments
        run.phase_ledgers = project_phase_ledgers(_item_bundle)
        # Spec 0122 — for v2 runs, the "suspected miss" banner is not
        # meaningful (the parser either finds items or there are none).
        run.disagreements_parse_suspected_miss = False
    # Spec 0043 D8 — drift events: end-of-phase self-counter ↔ ledger
    # open-count mismatches, surfaced in the UI as a small ⚠ chip.
    run.drifts = _compute_ledger_drifts(run)

    # started_at_ago is "now" relative to the earliest event.
    run.started_at_ago = _seconds_since(run.started_at)
    return run


def apply_event(run: Run, event: dict, session_dir: Path) -> Run:
    """Mutate ``run`` in place with a single transcript event.

    Returns the same ``run`` for ergonomic chaining. Unknown events are
    ignored (the backend may add new ones without breaking this layer).
    """
    kind = event.get("event")

    # Spec 0181 — stash the latest event ts so ``_finalise_status`` can
    # feed it to ``derive_run_status``'s staleness rule. Every event
    # counts (not just terminal ones) — the truth is "did anything
    # arrive recently."
    ts = event.get("ts")
    if ts:
        run._terminal_signals.last_event_at = ts

    if kind == "run_started":
        _on_run_started(run, event)
    elif kind == "phase_entered":
        _on_phase_entered(run, event)
    elif kind == "phase_exited":
        _on_phase_exited(run, event)
    elif kind == "turn_started":
        _on_turn_started(run, event)
    elif kind == "turn_inputs":
        _on_turn_inputs(run, event, session_dir)
    elif kind == "turn_searches":
        _on_turn_searches(run, event, session_dir)
    elif kind == "turn_ended":
        _on_turn_ended(run, event)
    elif kind in (
        "phase0_round_complete",
        "phase2_round_complete",
        "phase4_round_complete",
    ):
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
        # Spec 0136 — stash the signal on _terminal_signals; the
        # unified _finalise_status pass below applies the truth table.
        # Pre-spec this assigned ``run.status = "deadlocked"`` directly,
        # which raced with the later ``_on_run_completed`` handler that
        # could overwrite it back to ``"completed"`` when the orchestrator
        # emitted ``exit_code 0``.
        run._terminal_signals.hard_cap_hit = True
    # Other events (cost_update, soft_cap_hit, repair_invoked,
    # drafter_tiebreak_resolved, phase{0,1,3}_complete) carry information
    # already covered by other code paths.

    # Spec 0136 — re-derive status after every event so live SSE pushes
    # and replayed transcripts both apply the same truth table. The
    # function is pure dict reads + a 6-row short-circuit; sub-microsecond.
    _finalise_status(run)
    return run


# ─── Spec 0246 — card-layout derivation (shared fs + supabase) ────────────────


def derive_phase_outcomes(phase_int: int, status: str) -> tuple[str, str, str, str, str]:
    """Per-phase outcome tuple for the 5-segment card phase strip (§2.8.5).

    Keyed on the terminal phase ``T = phase_int`` and ``status``. Identical
    in filesystem and supabase modes — both carry terminal phase + status.
    """
    if status in ("completed", "converged"):
        return ("done", "done", "done", "done", "done")
    out: list[str] = []
    for x in range(1, 6):
        if x < phase_int:
            out.append("done")
        elif x == phase_int:
            if status == "errored":
                out.append("failed")
            elif status in ("abandoned", "deadlocked"):
                out.append("abandon")
            elif status == "running":
                out.append("active")
            else:
                out.append("pending")
        else:
            out.append("pending")
    return (out[0], out[1], out[2], out[3], out[4])


def derive_agent_breakdowns(metrics: dict | None) -> dict[str, AgentBreakdown]:
    """Per-agent cost split + the cheaply-derivable ``<N> searches`` chip.

    Reads ``totals_by_agent.{claude,openai}`` from metrics.json (fs) or the
    supabase ``metrics`` JSONB column (same shape). Keys "a"=Claude,
    "b"=GPT (§2.8.6). The richer plan-turns/critiques chips are deferred
    (§5) — only the search count ships now.
    """
    if not metrics:
        return {}
    tba = metrics.get("totals_by_agent") or {}
    out: dict[str, AgentBreakdown] = {}
    for backend_key, ui_key, ui_name in (("claude", "a", "Claude"), ("openai", "b", "GPT")):
        a = tba.get(backend_key)
        if not a:
            continue
        cost = round(float(a.get("cost_usd", 0.0) or 0.0) + float(a.get("search_cost", 0.0) or 0.0), 2)
        chips: list[AgentChip] = []
        searches = int(a.get("searches", 0) or 0)
        if searches > 0:
            chips.append(AgentChip(text=f"{searches} searches", kind="info"))
        out[ui_key] = AgentBreakdown(name=ui_name, cost=cost, chips=chips)
    return out


def derive_run_note(
    status: str,
    phase_int: int,
    *,
    rounds_completed: int = 0,
    error_type: str | None = None,
) -> RunNote | None:
    """Single-line terminal-state note for the card (§2.8.7, generic copy).

    Cause-specific copy (timeout / context-overflow / runaway loop) is
    deferred to §5; this returns the generic form. ``running`` runs get no
    note (the row collapses out).
    """
    code = f"P{phase_int}"
    if status in ("completed", "converged"):
        return RunNote(
            variant="ok",
            icon="check_circle",
            html=f"Converged in <b>{rounds_completed}</b> rounds. {code} reached.",
        )
    if status == "errored":
        et = error_type or "run failed"
        return RunNote(variant="err", icon="error", html=f"Run failed in {code}: <b>{et}</b>.")
    if status in ("abandoned", "deadlocked"):
        return RunNote(
            variant="warn", icon="pause_circle", html=f"Manually stopped / stalled in {code}."
        )
    return None


def _run_failed_error_type(transcript_path: Path) -> str | None:
    """Extract the ``error_type`` from the ``run_failed`` event (fs mode).

    Cheap tail-scan; only invoked for errored rows so the happy path stays
    free of the extra read. Returns ``None`` when absent.
    """
    if not transcript_path.exists():
        return None
    try:
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event") == "run_failed":
                et = event.get("error_type")
                return str(et) if et else None
    except OSError:
        return None
    return None


def summarize_run(session_dir: Path) -> RunListRow:
    """Cheap summary row — no transcript replay, no disagreement parse.

    Reads ``state.json`` + ``metrics.json`` + ``brief.md`` (H1 only).
    """
    state = _read_state(session_dir / "state.json")
    metrics = _read_metrics(session_dir / "metrics.json")
    topic = _read_topic(session_dir / "brief.md")

    phase_int = phase_to_int(state.phase if state else "phase0")
    # Spec 0195 — fall back to the session-dir YYYYMMDD-HHMMSS prefix when
    # no transcript events exist yet (abandoned-before-first-event rows).
    # Without this, summarize_run returns ``started_at=None`` and the list
    # cell rendered ``0s ago`` for genuinely-old rows.
    started_at = _earliest_known_ts(session_dir)
    duration = _duration_seconds(session_dir / "transcript.jsonl")

    final_emitted = bool(state and state.final_emitted_to)
    # Spec 0136 — also pull run_completed.exit_code so the unified
    # derive_run_status truth table can distinguish "exited cleanly,
    # reached done" from "exited cleanly, never reached done"
    # (silent-exit deadlock).
    hard_cap_hit, run_failed, run_completed_exit_code = _scan_terminal_signals(
        session_dir / "transcript.jsonl"
    )
    status = derive_run_status(
        state_phase=state.phase if state else "phase0",
        final_emitted=final_emitted,
        hard_cap_hit=hard_cap_hit,
        run_failed=run_failed,
        run_completed_exit_code=run_completed_exit_code,
        # Spec 0181 — staleness signal for the abandoned rule. Falls
        # back to the dir's mtime / session-dir timestamp when no
        # transcript exists (catches runs that crashed before writing
        # any event — exactly the user-reported four stuck rows).
        last_event_at=_last_activity_ts(session_dir),
    )

    # Spec 0039 D3 — transcript is the canonical truth; metrics.json is
    # the cold-start fallback for runs that haven't emitted any turn
    # yet. The transcript sum dedupes by label (later event wins) so a
    # parse-error recovery's duplicate turns don't double-count.
    cost = _sum_transcript_cost(session_dir / "transcript.jsonl")
    if cost == 0.0 and metrics:
        cost = float(metrics.get("total_cost_usd", 0.0) or 0.0)

    # Round counter for Phase 2/4 rows. Soft cap isn't in state.json; we
    # default to 6 (the CLI default). A Phase 2/4 row with no round files yet
    # shows "0/6" rather than dropping the cell.
    rounds: str | None = None
    rounds_completed = 0
    if phase_int in (2, 4):
        cur = _latest_round_for(session_dir, phase_int) or 0
        rounds = f"{cur}/6"
        rounds_completed = cur

    # Spec 0246 — card-layout payloads. Phase strip reuses the already-computed
    # terminal phase + status (no extra read); agents add a single metrics.json
    # read; the errored-note error_type adds a transcript scan only for errored
    # rows (the happy path skips it).
    phases = derive_phase_outcomes(phase_int, status)
    agents = derive_agent_breakdowns(metrics)
    error_type = (
        _run_failed_error_type(session_dir / "transcript.jsonl") if status == "errored" else None
    )
    note = derive_run_note(
        status, phase_int, rounds_completed=rounds_completed, error_type=error_type
    )

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
        phases=phases,
        rounds_completed=rounds_completed,
        rounds_max=6,
        agents=agents,
        note=note,
    )


# ─── Event handlers (mutate ``run`` in place) ─────────────────────────────────


def _on_run_started(run: Run, event: dict) -> None:
    # ``session_dir`` in the event is the absolute path; we already have id/display_id.
    run.round.soft = int(event.get("soft_cap", run.round.soft))
    run.round.hard = int(event.get("hard_cap", run.round.hard))
    # Stash model ids on each agent so the UI can show real names.
    run.agents["claude"].model_id = event.get("claude_model")
    run.agents["gpt"].model_id = event.get("openai_model")
    # Spec 0030: real context-window caps from the tier's ModelSpec.
    # 0 for pre-0030 transcripts; spec 0031 adds a TIERS-lookup fallback
    # below so old runs render at the right scale without re-running.
    run.agents["claude"].context_window = int(event.get("claude_context_window", 0) or 0)
    run.agents["gpt"].context_window = int(event.get("openai_context_window", 0) or 0)
    # Spec 0031: fallback path — if the event didn't carry an explicit
    # context_window (or it's 0), derive it from the model_id by scanning
    # `config.TIERS`. Pre-0030 transcripts immediately render at 1M after
    # the next deploy without re-running.
    if run.agents["claude"].context_window == 0:
        run.agents["claude"].context_window = _context_window_from_tier(
            run.agents["claude"].model_id
        )
    if run.agents["gpt"].context_window == 0:
        run.agents["gpt"].context_window = _context_window_from_tier(
            run.agents["gpt"].model_id
        )
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
    in_tokens = int(event.get("input_tokens", 0))
    out_tokens = int(event.get("output_tokens", 0))
    cache_read = int(event.get("cache_read_tokens", 0))
    cache_write = int(event.get("cache_write_tokens", 0))
    cost = float(event.get("cost_usd", 0.0))
    phase_str = event.get("phase", "phase0")
    # Spec 0039 — pre-0039 transcripts carry token-only cost in
    # ``cost_usd``. Detect them by the absence of ``search_cost`` on the
    # event and fold the search fee back in so the per-agent + per-turn
    # headline stays consistent with the recompute tool. New events
    # already include search fees in ``cost_usd``, so this branch
    # leaves them untouched.
    if "search_cost" not in event:
        n_searches = int(event.get("searches", 0) or 0)
        if n_searches > 0:
            model_id = event.get("model_id") or ""
            cost += compute_search_cost(model_id, n_searches)
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
    # Per-turn token usage (spec 0029) — keyed the same way as
    # phase_summaries / phase_review_items so the Consumption tab can join
    # cleanly. Single-shot phases (1, 3) use phase{N}_<agent>; round-loop
    # phases (0, 2, 4) use phase{N}_round{R}_<agent>.
    #
    # Spec 0135 — Phase 0 joined the round-loop family when the
    # new-protocol multi-round negotiation landed. Legacy single-shot
    # Phase 0 transcripts emit labels like ``phase0-claude`` (no round
    # marker); ``_round_index_from_label`` returns ``0`` for those, so
    # they keep the legacy ``phase0_<agent>`` key.
    phase_int = phase_to_int(phase_str)
    if phase_int in (0, 2, 4) and idx > 0:
        key = f"phase{phase_int}_round{idx}_{ag}"
    else:
        key = f"phase{phase_int}_{ag}"
    # Spec 0047 — repair siblings (`-repair` / `-hashdrift-repair`) get
    # their own per-turn key so the Consumption tab shows each LLM call
    # individually instead of collapsing original + repair into one card.
    # Matches the suffix convention already established by
    # ``_on_turn_inputs`` and ``_on_turn_searches`` for the input bundle
    # and search audit files.
    if "-repair" in label or "-hashdrift" in label:
        key = f"{key}_repair"
    # Spec 0030: per-piece sizes and the real context-window cap travel with
    # each turn. The frontend renormalises piece widths against `input_tokens`
    # (the provider's count) for honest segment proportions.
    #
    # Spec 0145 — this passthrough is load-bearing for the canonical-ID
    # contract. Only `str(k)`/`int(v)` coercion happens here; key
    # normalisation must NEVER be added at this layer, because both
    # canonical-ID runs (post-0145) and legacy-key historical runs flow
    # through the same path and rely on the read-shim in
    # `artifact-display.js` for translation. Any future normalisation
    # belongs at the consumer side (the JS shim), not here.
    pieces_raw = event.get("prompt_pieces") or {}
    prompt_pieces: dict[str, int] = {
        str(k): int(v) for k, v in pieces_raw.items() if v is not None
    }
    # Spec 0031: defence in depth — if state.context_window is still 0
    # (run_started never seen or model unknown), try the tier lookup
    # again using the event's model_id.
    turn_model_id = event.get("model_id") or state.model_id
    turn_context_window = state.context_window or _context_window_from_tier(turn_model_id)
    # Spec 0031: web-search tool calls + their separate per-request cost.
    # Cost is computed via the pricing module's per-search rate; stays
    # OUT of the headline `cost` field (token-cost only, by design).
    searches = int(event.get("searches", 0) or 0)
    search_cost = compute_search_cost(turn_model_id or "", searches)
    # Spec 0033 / 0036: preserve the `input_path` + `search_audit_path`
    # stamped earlier by `_on_turn_inputs` / `_on_turn_searches` (either
    # of which may have created a stub `TurnTokenUsage` before TurnEnded
    # arrived).
    prev = run.phase_token_usage.get(key)
    input_path = prev.input_path if prev is not None else None
    search_audit_path = prev.search_audit_path if prev is not None else None

    # Spec 0039 → Spec 0047 — same-label dedup (pre-0039 transcripts
    # with literal duplicate labels) is handled upstream by
    # ``_dedup_turn_ended_by_label``. Sibling labels (original turn +
    # its ``-repair`` / ``-hashdrift-repair`` sibling) now derive
    # DIFFERENT per-turn keys via the ``_repair`` suffix above, so each
    # LLM call gets its own Consumption-tab card. The agent-level
    # totals (state.tokens.*, state.cost) still accumulate every event
    # unconditionally — they match the billing aggregate.
    state.tokens.in_ += in_tokens
    state.tokens.out += out_tokens
    state.cost += cost
    state.search_cost += search_cost

    # Spec 0039 D9: token_cost = full cost - search cost. The breakdown
    # is what the Consumption tab's "of which web search" reads; the
    # invariant token_cost + search_cost == cost holds for every turn.
    token_cost = max(0.0, cost - search_cost)

    # Spec 0148 D10 — closeout signal derived from the prompt-pieces
    # dict (the closeout-request text rides as ``closeout.request`` in
    # the same dict the aggregator just passed through). Event-only
    # path; no orchestrator changes needed.
    was_closeout = int(prompt_pieces.get("closeout.request", 0)) > 0

    # Spec 0148 D11 — output-token breakdown. Reasoning is sourced
    # from the event's ``reasoning_tokens`` (OpenAI extracts it from
    # ``output_tokens_details.reasoning_tokens``; Anthropic captures
    # ``thinking_tokens`` when extended-thinking is enabled — both
    # plumb through ``TokenUsage.reasoning_tokens`` → TurnEnded).
    # ``tool_calls`` is always 0 in this codebase (no general-purpose
    # assistant tool calls; web_search invocations bill via
    # ``searches``/``search_cost``); preserved in the breakdown shape
    # for future tool-using phases. ``response`` is the remainder,
    # clamped at 0 if the provider reports inconsistent counts.
    reasoning_tokens = int(event.get("reasoning_tokens", 0) or 0)
    tool_call_tokens = 0
    response_tokens = out_tokens - reasoning_tokens - tool_call_tokens
    if response_tokens < 0:
        import logging
        logging.getLogger(__name__).warning(
            "[spec-0148] outputBreakdown underflow at %s: out=%d, reasoning=%d, tool_calls=%d",
            key, out_tokens, reasoning_tokens, tool_call_tokens,
        )
        response_tokens = 0
    output_breakdown = {
        "reasoning": reasoning_tokens,
        "response": response_tokens,
        "tool_calls": tool_call_tokens,
    }

    # Spec 0148 D12 — cache-read savings vs. paying fresh input rate.
    # Helper returns 0.0 for unknown models and for cache_read <= 0,
    # so non-cache-engaged turns and pre-pricing models stay at zero
    # without special-casing here.
    cache_savings_usd = compute_cache_savings_usd(turn_model_id or "", cache_read)

    run.phase_token_usage[key] = TurnTokenUsage(
        in_=in_tokens,
        out=out_tokens,
        cache_read=cache_read,
        cache_write=cache_write,
        cost=cost,
        token_cost=token_cost,
        model_id=turn_model_id,
        context_window=turn_context_window,
        prompt_pieces=prompt_pieces,
        searches=searches,
        search_cost=search_cost,
        input_path=input_path,
        search_audit_path=search_audit_path,
        was_closeout=was_closeout,
        output_breakdown=output_breakdown,
        cache_savings_usd=cache_savings_usd,
    )


# Spec 0085 — turn-key → builder dispatch for runs whose per-turn
# bundle was never persisted (pre-dates spec 0033's input-audit
# rollout, or the JSON was lost). Every builder produces a system
# prompt rebuilt from the current source; the brief comes from
# ``brief.md`` so it's always real. Other pieces (d1/d2/plan/hist/
# draft/histp) cannot be reconstructed for historical runs and stay
# empty — the UI hides empty pieces (spec 0045 D3).
def build_input_bundle_fallback(
    session_dir: Path, snake_key: str
) -> dict | None:
    """Spec 0085 — synthesise an input bundle for a turn whose JSON is missing.

    ``snake_key`` is the normalised key the server uses on disk
    (e.g. ``phase1_claude``, ``phase2_round3_claude``, ``phase4_round2_gpt``).

    Returns ``None`` if the key is unparseable. Otherwise returns a
    bundle whose ``pieces.system`` is the agent's current default
    system prompt for that phase, with a
    ``system_source: 'agent-default'`` marker on the payload.

    The brief comes from ``brief.md`` if present; if not, the bundle
    still surfaces the system prompt with an empty ``brief`` slot.
    """
    brief_path = session_dir / "brief.md"
    brief_text = ""
    if brief_path.exists():
        try:
            brief_text = brief_path.read_text(encoding="utf-8")
        except OSError:
            brief_text = ""

    parsed = _parse_snake_key(snake_key)
    if parsed is None:
        return None
    phase, round_idx, ui_agent_label, is_repair = parsed
    return synthesize_bundle_payload(
        phase=phase,
        round_idx=round_idx,
        ui_agent_label=ui_agent_label,
        is_repair=is_repair,
        brief_text=brief_text,
    )


def synthesize_bundle_payload(
    *,
    phase: int,
    round_idx: int,
    ui_agent_label: str,
    is_repair: bool,
    brief_text: str,
) -> dict | None:
    """Spec 0085 — pure synthesis: turn-key parts + brief text → bundle dict.

    Shared by the filesystem and Supabase backends. No I/O — callers
    are responsible for resolving the brief text first. Returns the
    JSON-ready payload (with ``system_source: 'agent-default'``) or
    ``None`` if ``phase`` is out of range.
    """
    from dual_research.protocol import prompts as _prompts

    agent_name = "Claude" if ui_agent_label == "claude" else "OpenAI GPT"
    other_name = "OpenAI GPT" if ui_agent_label == "claude" else "Claude"

    pieces: dict[str, str] | None = None
    if is_repair:
        # Repair turns don't carry per-phase context — we can't
        # reconstruct ``hist`` (the malformed previous turn) without the
        # original bundle. Surface the repair system prompt with empty
        # data slots so the UI at least shows the agent's instructions.
        pieces = _prompts.repair_input_bundle(
            agent_name=agent_name,
            phase=phase,
            errors=None,
            malformed_content="",
        )
    elif phase == 0:
        pieces = _prompts.preflight_input_bundle(
            brief=brief_text, agent_name=agent_name
        )
    elif phase == 1:
        pieces = _prompts.research_input_bundle(
            brief=brief_text, agent_name=agent_name
        )
    elif phase == 2 and round_idx == 1:
        pieces = _prompts.negotiation_round1_input_bundle(
            brief=brief_text,
            claude_draft="",
            openai_draft="",
            agent_name=agent_name,
            other_name=other_name,
        )
    elif phase == 2:
        pieces = _prompts.negotiation_turn_input_bundle(
            brief=brief_text,
            claude_draft="",
            openai_draft="",
            prior_turns=[],
            agent_name=agent_name,
            other_name=other_name,
            round=round_idx,
        )
    elif phase == 3:
        pieces = _prompts.drafting_input_bundle(
            brief=brief_text,
            claude_draft="",
            openai_draft="",
            plan=None,
            prior_turns=[],
            agent_name=agent_name,
            other_name=other_name,
        )
    elif phase == 4:
        pieces = _prompts.review_input_bundle(
            brief=brief_text,
            draft="",
            prior_turns=[],
            agent_name=agent_name,
            other_name=other_name,
            drafter_name=other_name,
            round=round_idx,
        )
    else:
        return None

    label = f"phase{phase}"
    if round_idx > 0:
        label = f"{label}-r{round_idx}"
    label = f"{label}-{ui_agent_label}"
    if is_repair:
        label = f"{label}-repair"

    return {
        "agent": ui_agent_label,
        "phase": f"phase{phase}",
        "label": label,
        "pieces": pieces,
        "emitted_at": "",
        # Spec 0085 — single source of truth marker the frontend reads to
        # decide whether to surface the "agent default, not per-run" caveat.
        "system_source": "agent-default",
    }


def _parse_snake_key(snake_key: str) -> tuple[int, int, str, bool] | None:
    """Spec 0085 — parse a snake-case input-bundle key into structured parts.

    Accepts:
        ``phase0_claude``, ``phase1_gpt``,
        ``phase2_round3_claude``, ``phase4_round1_gpt``,
        ``phase2_round3_claude_repair``.

    Returns ``(phase, round_idx, agent, is_repair)`` or ``None`` if the
    shape doesn't match. ``round_idx`` is ``0`` for phases that don't
    have rounds. ``agent`` is the UI label (``claude`` | ``gpt``).
    """
    import re

    pattern = re.compile(
        r"^phase(\d+)(?:_round(\d+))?_(claude|gpt)(_repair)?$"
    )
    m = pattern.match(snake_key)
    if m is None:
        return None
    phase = int(m.group(1))
    round_idx = int(m.group(2)) if m.group(2) else 0
    agent = m.group(3)
    is_repair = m.group(4) is not None
    return phase, round_idx, agent, is_repair


def _on_turn_inputs(run: Run, event: dict, session_dir: Path) -> None:
    """Spec 0033 — persist a per-turn input bundle to ``inputs/<key>.json``.

    Emitted by the orchestrator alongside ``TurnStarted``; carries the
    Tk-keyed text dict produced by ``protocol/prompts.py::*_input_bundle()``.
    The JSON file is the UI server's source-of-truth (read on demand via
    ``/api/runs/<id>/inputs/<key>``). The aggregator stamps a relative
    path on ``TurnTokenUsage.input_path`` so the UI can detect which
    turns have bundles available.
    """
    backend_ag = event.get("agent")
    if backend_ag not in ("claude", "openai"):
        return
    ag = ui_agent(backend_ag)
    phase_str = event.get("phase", "phase0")
    phase_int = phase_to_int(phase_str)
    label = event.get("label") or ""
    idx = _round_index_from_label(label)
    # Spec 0142 — Phase 0 round-keying mirrors ``_call.py::_derive_turn_key``;
    # without this, per-round Phase-0 bundles all write to
    # ``phase0_<agent>.json`` and the last round overwrites the rest.
    if phase_int in (0, 2, 4) and idx > 0:
        key = f"phase{phase_int}_round{idx}_{ag}"
    else:
        key = f"phase{phase_int}_{ag}"
    # Repair turns have labels like ``phase2-r3-claude-repair`` — capture
    # them under a distinct key so the round-N entry isn't overwritten by
    # the repaired retry. The Consumption tab already ignores keys that
    # don't match ``^phase\d+(Round\d+)?(Claude|Gpt)$``; the Input tab
    # falls back to "(repair)" suffix display via the regex below.
    if "-repair" in label or "-hashdrift" in label:
        key = f"{key}_repair"

    pieces_raw = event.get("pieces") or {}
    pieces: dict[str, str] = {str(k): str(v) for k, v in pieces_raw.items()}

    inputs_dir = session_dir / "inputs"
    path = inputs_dir / f"{key}.json"
    # Spec 0150 — the serve mode replays events to compute snapshots; the
    # writer here used to overwrite existing files on every replay. For
    # historical runs whose events still carry the legacy 8-key vocab,
    # that overwrote backfilled canonical files with legacy data. Guard
    # against overwrite so backfilled state survives serve replays. The
    # orchestrator's first write still lands (the file doesn't exist yet
    # on the first emission of a turn).
    if path.exists():
        rel = f"inputs/{key}.json"
        existing = run.phase_token_usage.get(key)
        if existing is not None:
            existing.input_path = rel
        else:
            run.phase_token_usage[key] = TurnTokenUsage(input_path=rel)
        return
    try:
        inputs_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "agent": ag,
            "phase": phase_str,
            "label": label,
            "pieces": pieces,
            "emitted_at": event.get("ts", "") or "",
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        # Disk-write failures are non-fatal — the UI just won't have the
        # bundle to render. Same failure mode as a pre-0033 run.
        return

    rel = f"inputs/{key}.json"
    existing = run.phase_token_usage.get(key)
    if existing is not None:
        existing.input_path = rel
    else:
        run.phase_token_usage[key] = TurnTokenUsage(input_path=rel)


def _on_turn_searches(run: Run, event: dict, session_dir: Path) -> None:
    """Spec 0036 — persist a per-turn web-search audit bundle to
    ``searches/<key>.json``.

    Mirrors ``_on_turn_inputs``. The aggregator runs
    ``validate_search_audit`` on the reconstructed audit dataclass
    before writing so ``flags`` and ``matched_query_id`` are populated
    on disk and on the wire. ``TurnTokenUsage.search_audit_path`` is
    stamped so the UI can detect which turns have audit data available.
    """
    from dataclasses import asdict
    from dual_research.audit import audit_from_dict, audit_to_dict, validate_search_audit

    audit_raw = event.get("audit")
    if not isinstance(audit_raw, dict) or not audit_raw:
        return

    backend_ag = event.get("agent")
    if backend_ag not in ("claude", "openai"):
        return
    ag = ui_agent(backend_ag)
    phase_str = event.get("phase", "phase0")
    phase_int = phase_to_int(phase_str)
    label = event.get("label") or ""
    idx = _round_index_from_label(label)
    # Spec 0142 — Phase 0 round-keying. See ``_on_turn_inputs`` above and
    # ``_call.py::_derive_turn_key`` for the matching change.
    if phase_int in (0, 2, 4) and idx > 0:
        key = f"phase{phase_int}_round{idx}_{ag}"
    else:
        key = f"phase{phase_int}_{ag}"
    if "-repair" in label or "-hashdrift" in label:
        key = f"{key}_repair"
    # Honour the event's turn_key if it was provided and looks safe.
    event_key = event.get("turn_key")
    if isinstance(event_key, str) and re.match(r"^[a-zA-Z0-9_]+$", event_key):
        key = event_key

    audit = audit_from_dict(audit_raw)
    validate_search_audit(audit)

    searches_dir = session_dir / "searches"
    try:
        searches_dir.mkdir(parents=True, exist_ok=True)
        path = searches_dir / f"{key}.json"
        path.write_text(json.dumps(audit_to_dict(audit), indent=2), encoding="utf-8")
    except OSError:
        return

    rel = f"searches/{key}.json"
    existing = run.phase_token_usage.get(key)
    if existing is not None:
        existing.search_audit_path = rel
    else:
        run.phase_token_usage[key] = TurnTokenUsage(search_audit_path=rel)


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
    # Spec 0136 — record the final-emitted signal so ``_finalise_status``
    # can promote ``run.status`` to "completed" via the truth-table's
    # final-emitted branch. Pre-spec this handler was a no-op; the
    # detail page relied on the subsequent ``run_completed{exit_code: 0}``
    # event to flip status, and the All-Runs page read
    # ``state.final_emitted_to`` directly. Stashing here keeps the two
    # paths in sync without depending on the orchestrator's exit-code
    # mapping.
    # confidence: 'HIGH' | 'MODERATE' | 'LOW' — not currently displayed
    # but could feed a future "confidence" pill.
    run._terminal_signals.final_emitted = True


def _on_run_completed(run: Run, event: dict) -> None:
    # Spec 0136 — stash the exit code on _terminal_signals; _finalise_status
    # runs the unified truth table after the dispatch returns. Pre-spec
    # the handler imperatively mapped exit_code 0 → "completed" without
    # cross-checking ``state.phase`` or ``final_emitted_to``, which
    # produced false "completed" pills for runs that exited at the hard
    # cap with every item already terminal (Phase 2 silent-exit).
    try:
        exit_code = int(event.get("exit_code", 0))
    except (TypeError, ValueError):
        exit_code = 0
    run._terminal_signals.run_completed_exit_code = exit_code
    # All agents go idle on terminal.
    for ag in run.agents.values():
        ag.status = "idle"


def _on_run_failed(run: Run, event: dict) -> None:
    # Spec 0136 — stash the signal + error payload on _terminal_signals;
    # _finalise_status applies the truth table.
    run._terminal_signals.run_failed = True
    run._terminal_signals.run_failed_error = TopLevelError(
        when=event.get("ts", ""),
        where=event.get("phase_reached", "orchestrator"),
        code=event.get("error_type", "ORCHESTRATOR_PANIC"),
        detail=event.get("message", ""),
    )
    for ag in run.agents.values():
        ag.status = "idle"


def _finalise_status(run: Run) -> None:
    """Spec 0136 — apply the unified ``derive_run_status`` truth table.

    Reads the terminal signals stashed on ``run._terminal_signals`` by
    the event handlers + the snapshot fields (``run.phase``,
    ``run.current_draft_path`` if any) and writes a single canonical
    ``run.status``. Called after every ``apply_event`` tick so live SSE
    deliveries re-derive status the same way the snapshot path does.

    Idempotent — safe to call repeatedly. Side-effects: writes
    ``run.status`` and (when ``run_failed``) ``run.error``.
    """
    sigs = run._terminal_signals
    # ``state.phase == "done"`` is the orchestrator's terminal-state
    # marker; on the Run dataclass that's ``run.phase == 5`` because the
    # UI uses int phase numbers (Phase 5 == post-Phase-4 / final-emitted).
    state_phase = "done" if run.phase == 5 else f"phase{run.phase}"
    # Either the ``final_emitted`` transcript event arrived (sigs.final_emitted)
    # or ``_augment_from_state_json`` set ``run.phase = 5`` from
    # ``state.final_emitted_to`` — both signal the run reached done.
    final_emitted = sigs.final_emitted or run.phase == 5
    run.status = derive_run_status(
        state_phase=state_phase,
        final_emitted=final_emitted,
        hard_cap_hit=sigs.hard_cap_hit,
        run_failed=sigs.run_failed,
        run_completed_exit_code=sigs.run_completed_exit_code,
        last_event_at=sigs.last_event_at,
    )
    if sigs.run_failed and sigs.run_failed_error is not None:
        run.error = sigs.run_failed_error


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


def _earliest_known_ts(session_dir: Path) -> str | None:
    """Spec 0195 — best-effort 'when did this run start' timestamp.

    Priority (mirrors ``_last_activity_ts`` below but for the earliest,
    not latest, timestamp):

    1. First event ts in ``transcript.jsonl`` (the canonical signal —
       same as ``_earliest_event_ts`` returns directly).
    2. Parsed ``YYYYMMDD-HHMMSS`` prefix from the session dir name (the
       absolute floor — set at session-dir creation time, before any
       event is emitted).

    A run with neither returns ``None``, and the caller decides how to
    render that (``run-list.jsx`` renders ``None`` as ``"—"`` after the
    spec 0195 client-side guard).

    Why no mtime fallback (unlike ``_last_activity_ts``): file mtimes
    drift upward over time as state.json / metrics.json get written, so
    they make a poor proxy for *start* time. The dir-name prefix is
    fixed at creation and so is the right floor for "earliest known".
    """
    ts = _earliest_event_ts(session_dir / "transcript.jsonl")
    if ts:
        return ts
    m = _SESSION_DIR_TS_RE.match(session_dir.name)
    if m:
        date_part, time_part = m.groups()
        try:
            return (
                datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S")
                .replace(tzinfo=timezone.utc)
                .isoformat()
            )
        except ValueError:
            return None
    return None


def _latest_event_ts(transcript_path: Path) -> str | None:
    """Spec 0181 — ISO ts of the LAST event in the transcript.

    Reads the tail of the file (~64 KB) so even multi-MB transcripts
    are cheap. Feeds the staleness rule in ``derive_run_status`` via
    ``summarize_run``.
    """
    if not transcript_path.exists():
        return None
    try:
        with transcript_path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size == 0:
                return None
            tail = b""
            chunk = 64 * 1024
            while size > 0 and tail.count(b"\n") < 2:
                read_n = min(chunk, size)
                f.seek(size - read_n)
                tail = f.read(read_n) + tail
                size -= read_n
            lines = [ln for ln in tail.splitlines() if ln.strip()]
            if not lines:
                return None
            evt = json.loads(lines[-1])
            return evt.get("ts")
    except (OSError, ValueError, json.JSONDecodeError):
        return None


_SESSION_DIR_TS_RE = re.compile(r"^(\d{8})-(\d{6})-")


def _last_activity_ts(session_dir: Path) -> str | None:
    """Spec 0181 — best-effort 'last activity' timestamp for a session dir.

    Priority:
    1. Last event ts in ``transcript.jsonl`` (the canonical signal).
    2. Newest mtime among ``state.json`` + ``metrics.json`` + the dir
       itself (catches runs that wrote state but never emitted events).
    3. The parsed ``YYYYMMDD-HHMMSS`` prefix from the dir name
       (creation time; the absolute floor for any run).

    The first non-None value wins. A run with none of these would have
    ``last_event_at=None`` returned to the truth table, which falls
    through to ``running`` (backwards-compatible default).
    """
    ts = _latest_event_ts(session_dir / "transcript.jsonl")
    if ts:
        return ts
    # Fall back to the newest mtime — captures runs that wrote
    # state.json or metrics.json without emitting transcript events.
    candidates = [session_dir, session_dir / "state.json", session_dir / "metrics.json"]
    mtimes = []
    for p in candidates:
        try:
            mtimes.append(p.stat().st_mtime)
        except (OSError, FileNotFoundError):
            continue
    if mtimes:
        return datetime.fromtimestamp(max(mtimes), tz=timezone.utc).isoformat()
    # Last resort — parse the session dir name (YYYYMMDD-HHMMSS-slug).
    m = _SESSION_DIR_TS_RE.match(session_dir.name)
    if m:
        date_part, time_part = m.groups()
        try:
            return (
                datetime.strptime(date_part + time_part, "%Y%m%d%H%M%S")
                .replace(tzinfo=timezone.utc)
                .isoformat()
            )
        except ValueError:
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


def _dedup_turn_ended_by_label(events: list[dict]) -> list[dict]:
    """Spec 0039 — keep the last ``turn_ended`` per ``label`` only.

    Sibling labels (canonical + ``-repair`` variants that the
    aggregator's per-turn key maps to the same bucket) are NOT
    deduped — they are distinct API calls billed separately. Only
    exact-label collisions (parse-error retries) collapse. Order is
    preserved by first-seen so timing-sensitive logic downstream still
    sees a clean monotonic event stream.
    """
    last_index: dict[str, int] = {}
    for i, ev in enumerate(events):
        if ev.get("event") != "turn_ended":
            continue
        label = ev.get("label")
        if not label:
            continue
        last_index[label] = i
    keep = set(last_index.values())
    out: list[dict] = []
    for i, ev in enumerate(events):
        if ev.get("event") == "turn_ended":
            label = ev.get("label")
            if label and i != last_index.get(label):
                continue
        out.append(ev)
    return out


def _sum_transcript_cost(transcript_path: Path) -> float:
    """Sum ``cost_usd`` across the canonical turn_ended events.

    Spec 0039:
    - Parse-error recoveries replay the same ``label`` multiple times.
      Keep the last occurrence per label (failed earlier attempts are
      discarded; their cost is part of the deduped total only when the
      canonical attempt's ``cost_usd`` accounts for them — usually it
      doesn't, but that's a provider-side reality, not something the
      aggregator can fix).
    - Pre-0039 events store token-only cost in ``cost_usd``. When the
      event lacks ``search_cost`` AND has ``searches > 0``, fold the
      search fee back in so the headline matches the recompute tool.
    """
    if not transcript_path.exists():
        return 0.0
    by_label: dict[str, float] = {}
    try:
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event") != "turn_ended":
                continue
            label = event.get("label")
            if not label:
                continue
            cost = float(event.get("cost_usd", 0.0))
            if "search_cost" not in event:
                n_searches = int(event.get("searches", 0) or 0)
                if n_searches > 0:
                    cost += compute_search_cost(
                        event.get("model_id") or "", n_searches
                    )
            by_label[label] = cost
    except OSError:
        return 0.0
    return sum(by_label.values())


def _scan_terminal_signals(transcript_path: Path) -> tuple[bool, bool, int | None]:
    """Tail-scan the transcript for terminal-event markers.

    Returns ``(hard_cap_hit, run_failed, run_completed_exit_code)``.
    ``run_completed_exit_code`` is ``None`` when the event hasn't fired
    yet (live in-flight runs); ``int`` when the orchestrator has emitted
    ``RunCompleted``. Spec 0136 added the third return value so
    ``summarize_run`` can pass it to ``derive_run_status`` and unify the
    list-page status derivation with the detail-page replay path.
    """
    hard_cap = False
    run_failed = False
    run_completed_exit_code: int | None = None
    if not transcript_path.exists():
        return False, False, None
    try:
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = event.get("event")
            if kind == "hard_cap_hit":
                hard_cap = True
            elif kind == "run_failed":
                run_failed = True
            elif kind == "run_completed":
                try:
                    run_completed_exit_code = int(event.get("exit_code", 0))
                except (TypeError, ValueError):
                    run_completed_exit_code = 0
    except OSError:
        return False, False, None
    return hard_cap, run_failed, run_completed_exit_code


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
    """Extract the round number from a turn label.

    Two label shapes in the wild:
    - ``phase2-r3-claude`` / ``phase2-r3-claude-repair`` — the actual
      orchestrator emits this form (see ``orchestrator/phase2.py``).
    - ``phase2-claude-round-3`` — older test fixtures + the original
      shape this helper was designed against.

    Returns 0 if neither shape matches (single-shot phases — Phase 0, 1, 3 —
    correctly fall into the round-less keying branch).
    """
    m = re.search(r"-r(\d+)(?:[-_]|$)", label)
    if m:
        return int(m.group(1))
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
        # Phase 0 — spec 0135. New-protocol runs write multi-round
        # ``round-NN-{agent}.md`` files; prefer the latest round for the
        # in-flight live-card body. Fall back to legacy
        # ``preflight-{agent}.md`` when no round files exist (pre-0114
        # transcripts).
        rnd = _latest_round_for(session_dir, 0)
        if rnd is not None and rnd > 0:
            _set_body_if_present(run, "claude", session_dir / "phase0" / f"round-{rnd:02d}-claude.md", kind="thinking", index=rnd)
            _set_body_if_present(run, "gpt", session_dir / "phase0" / f"round-{rnd:02d}-openai.md", kind="thinking", index=rnd)
        else:
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
# Spec 0042 — Phase 1 draft files have one per agent, no round.
_PHASE1_DRAFT_RE = re.compile(r"^draft-(claude|openai)\.md$")


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
        phase0_<agent>             (legacy single-shot preflight critique)
        phase0_round{R}_<agent>    (spec 0135 — new-protocol multi-round)
        phase1_<agent>             (research draft)
        phase2_round{R}_<agent>    (negotiate turns)
        phase3                     (converged draft — no agent split)
        phase4_round{R}_<agent>    (review turns)
    """
    out: dict[str, str] = {}

    # Phase 0 (legacy) — pre-0114 single-shot preflight critiques. Stays
    # populated for legacy transcripts that only carry
    # ``phase0/preflight-{agent}.md`` files; new-protocol runs add
    # ``phase0_round{R}_<agent>`` entries below.
    for agent in ("claude", "openai"):
        path = session_dir / "phase0" / f"preflight-{agent}.md"
        _maybe_set_summary(out, f"phase0_{_ui_agent(agent)}", path)

    # Phase 1 — research drafts.
    for agent in ("claude", "openai"):
        path = session_dir / "phase1" / f"draft-{agent}.md"
        _maybe_set_summary(out, f"phase1_{_ui_agent(agent)}", path)

    # Phase 0, 2, and 4 — turn-based; enumerate every round file on disk.
    # Spec 0135 — Phase 0 joined the round-keyed loop when the new-protocol
    # multi-round negotiation landed.
    for phase in (0, 2, 4):
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


def _read_phase_review_items(session_dir: Path) -> dict[str, list[dict]]:
    """Walk every Phase 2 + Phase 4 turn file and extract review items.

    Keyed by `phase{N}_round{R}_<agent>` — same convention as
    `phase_summaries`. Phase 4 was added in spec 0028 (cross-review
    side-by-side modal); the section taxonomy in `extract_review_items`
    handles both phases.

    Spec 0034: each item is anchor-resolved against the PRIOR content
    (Phase 1 draft / previous-round turn / current converged draft) at
    parse time via ``resolve_review_items``. The result is a list of
    items each carrying ``block_id`` — populated when the anchor
    resolves cleanly, None when the agent paraphrased or the parser
    missed. The frontend uses ``block_id`` first via
    ``document.getElementById`` and falls back to the legacy
    text-scan only when None.
    """
    from dual_research.protocol.blocks import assign_block_ids
    from dual_research.protocol.parse import (
        ReviewItem,
        _normalize_for_match,
        parse_turn_v2,
        resolve_review_items,
    )

    out: dict[str, list[dict]] = {}

    def _v2_review_items(text: str, prior_blocks) -> list | None:
        """Try the spec-0114 schema first. Returns a list of ReviewItem
        when at least one RaiseBlock parsed (i.e. this is clearly a v2
        turn file), or ``None`` to signal that the legacy extractor
        should run.

        Anchor resolution (``block_id``) mirrors the legacy path: if
        the RaiseBlock's anchor type is ``quote``/``after`` and the
        anchor text matches a prior block, the block id is attached.
        """
        parsed = parse_turn_v2(text)
        raise_blocks = [b for b in parsed.blocks if hasattr(b, "kind") and hasattr(b, "anchor_type")]
        if not raise_blocks:
            return None
        # Map blocks to IDs positionally — the orchestrator stamps
        # ``raised_this_turn`` in the same order the RAISE blocks
        # appear in the body, and the same convention is preserved
        # on disk via the ``RAISED_THIS_TURN: [...]`` footer.
        ids = list(parsed.raised_this_turn)
        # Pre-normalise prior blocks once.
        norm_blocks = [(b, _normalize_for_match(b.text)) for b in (prior_blocks or [])]
        items: list[ReviewItem] = []
        for idx, blk in enumerate(raise_blocks):
            stamped_id = ids[idx] if idx < len(ids) else None
            quote = blk.anchor_text if blk.anchor_type == "quote" else None
            after = blk.anchor_text if blk.anchor_type == "after" else None
            block_id: str | None = None
            for b, btxt in norm_blocks:
                if quote and _normalize_for_match(quote) in btxt:
                    block_id = b.id
                    break
                if after and _normalize_for_match(after) == btxt:
                    block_id = b.id
                    break
            items.append(ReviewItem(
                kind=blk.kind.value if hasattr(blk.kind, "value") else str(blk.kind),
                body=blk.body,
                quote=quote,
                after=after,
                item_id=stamped_id,
                block_id=block_id,
            ))
        return items
    # Cache the current-draft path lookup so we don't probe the
    # phase4 directory once per turn.
    cached_current_draft: str | None = None

    def _resolve_prior_blocks(phase_n: int, round_n: int, agent_be: str):
        nonlocal cached_current_draft
        # Mirror ``ui/static/run-detail.jsx::priorContentPathFor``.
        if phase_n == 0:
            # Spec 0135 — Phase 0 critiques the brief at round 1; round
            # N ≥ 2 responds to the other agent's prior Phase 0 turn.
            other_be = "openai" if agent_be == "claude" else "claude"
            if round_n <= 1:
                prior_path = session_dir / "brief.md"
            else:
                rr = f"{round_n - 1:02d}"
                prior_path = session_dir / "phase0" / f"round-{rr}-{other_be}.md"
        elif phase_n == 1:
            # Spec 0042 — Phase 1 draft claims/questions anchor against
            # the brief (the agent's only input at that point).
            prior_path = session_dir / "brief.md"
        elif phase_n == 4:
            # Phase 4 anchors are against the current converged draft.
            if cached_current_draft is None:
                cached_current_draft = _find_current_draft_path(session_dir) or ""
            if not cached_current_draft:
                return []
            prior_path = session_dir / cached_current_draft
        else:
            other_be = "openai" if agent_be == "claude" else "claude"
            if round_n <= 1:
                prior_path = session_dir / "phase1" / f"draft-{other_be}.md"
            else:
                rr = f"{round_n - 1:02d}"
                prior_path = session_dir / "phase2" / f"round-{rr}-{other_be}.md"
        if not prior_path.is_file():
            return []
        try:
            prior_text = prior_path.read_text(encoding="utf-8")
        except OSError:
            return []
        _, records = assign_block_ids(prior_text)
        return records

    # Spec 0042 D3 — Phase 1 walked alongside Phase 2 + Phase 4 so the
    # side-by-side modal can render structured items for plan-draft cards.
    # Phase 1 has one draft per agent and no rounds; the bucket key drops
    # the round component (``phase1_<agent>``).
    phase1_dir = session_dir / "phase1"
    if phase1_dir.is_dir():
        for entry in sorted(phase1_dir.iterdir()):
            if not entry.is_file() or not entry.name.endswith(".md"):
                continue
            m = _PHASE1_DRAFT_RE.match(entry.name)
            if not m:
                continue
            agent = m.group(1)
            try:
                text = entry.read_text(encoding="utf-8")
            except OSError:
                continue
            prior_blocks = _resolve_prior_blocks(1, 1, agent)
            v2_items = _v2_review_items(text, prior_blocks)
            if v2_items is not None:
                items = v2_items
            else:
                items = resolve_review_items(text, prior_blocks)
            # Spec 0042 D7 — always create the bucket so absence-as-empty
            # ambiguity is resolved. An empty list means "we looked; nothing
            # there" instead of "we never looked."
            key = f"phase1_{_ui_agent(agent)}"
            out[key] = [asdict(i) for i in items]

    # Spec 0135 — Phase 0 walks alongside Phase 2 + Phase 4. Round files
    # produced by ``dr_run.run_dr_phase0`` carry the same RAISE-block
    # schema; the side-by-side modal opens with the brief on the left
    # at round 1 and the other agent's prior Phase 0 turn at round ≥ 2.
    for phase_n in (0, 2, 4):
        phase_dir = session_dir / f"phase{phase_n}"
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
            try:
                text = entry.read_text(encoding="utf-8")
            except OSError:
                continue
            prior_blocks = _resolve_prior_blocks(phase_n, round_n, agent)
            v2_items = _v2_review_items(text, prior_blocks)
            if v2_items is not None:
                items = v2_items
            else:
                items = resolve_review_items(text, prior_blocks)
            # Spec 0042 D7 — always create the bucket, even when items
            # is empty, so the frontend can distinguish "parsed and got
            # nothing" from "never parsed" (the latter is now impossible
            # for any agent's turn file that exists on disk).
            key = f"phase{phase_n}_round{round_n}_{_ui_agent(agent)}"
            out[key] = [asdict(i) for i in items]
    return out


_DRAFT_VERSION_RE = re.compile(r"^draft-v(\d+)\.md$")


def _find_current_draft_path(session_dir: Path) -> str | None:
    """Return the latest converged-document path, relative to session-dir.

    Prefers the highest-numbered `phase4/draft-v*.md` (drafter revisions
    that land in Phase 4); falls back to `phase3/draft-v1.md`. Returns
    None when neither file exists yet (Phase 3 hasn't completed).
    """
    phase4 = session_dir / "phase4"
    if phase4.is_dir():
        best: tuple[int, str] | None = None
        for entry in phase4.iterdir():
            if not entry.is_file():
                continue
            m = _DRAFT_VERSION_RE.match(entry.name)
            if not m:
                continue
            n = int(m.group(1))
            if best is None or n > best[0]:
                best = (n, entry.name)
        if best is not None:
            return f"phase4/{best[1]}"
    phase3 = session_dir / "phase3" / "draft-v1.md"
    if phase3.is_file():
        return "phase3/draft-v1.md"
    return None


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


# ─── Spec 0034 — disagreement turn-key threading + question anchor resolution


def _populate_disagreement_turn_keys(disagreements: list) -> None:
    """Stamp ``raised_turn_key`` / ``closed_turn_key`` on each disagreement.

    Read off the disagreement's ``progression`` steps: the first step's
    ``(round, agent)`` is the raised-turn; for status-resolved
    disagreements, the LAST step's ``(round, agent)`` is the closed-turn.
    Format matches spec 0033's ``item.turnKey`` so the explorer's
    click-to-highlight feature jumps straight to a timeline card.
    """
    for d in disagreements:
        progression = getattr(d, "progression", None) or []
        if progression:
            first = progression[0]
            agent_ui = "gpt" if first.agent == "openai" else first.agent
            d.raised_turn_key = f"phase{d.phase}_round{first.round}_{agent_ui}"
            if str(d.status).startswith("resolved"):
                last = progression[-1]
                agent_last = "gpt" if last.agent == "openai" else last.agent
                d.closed_turn_key = f"phase{d.phase}_round{last.round}_{agent_last}"
        elif d.opened_round:
            # Fallback when progression is empty — derive from opened_round
            # + raised_by. (Disagreement parsing always emits a progression
            # in practice, but be defensive.)
            raised = "gpt" if d.raised_by == "openai" else d.raised_by
            if raised in ("claude", "gpt"):
                d.raised_turn_key = f"phase{d.phase}_round{d.opened_round}_{raised}"


def _resolve_question_anchors(session_dir: Path, questions: list) -> None:
    """Pre-resolve each Question's ``quote``/``after`` anchor against the
    block-IDs of the prior content the question was about.

    Mirrors ``_read_phase_review_items``: Phase 2 uses the other agent's
    prior round-file (or Phase 1 draft for round 1); Phase 4 uses the
    current converged draft.
    """
    from dual_research.protocol.blocks import assign_block_ids

    if not questions:
        return

    cache: dict[tuple[int, int, str], list] = {}
    current_draft_rel = _find_current_draft_path(session_dir) or ""

    def _prior_blocks(phase: int, round_n: int, raiser_ui: str) -> list:
        key = (phase, round_n, raiser_ui)
        if key in cache:
            return cache[key]
        if phase == 4:
            prior_path = session_dir / current_draft_rel if current_draft_rel else None
        else:
            other_be = "claude" if raiser_ui == "gpt" else "openai"
            if round_n <= 1:
                prior_path = session_dir / "phase1" / f"draft-{other_be}.md"
            else:
                rr = f"{round_n - 1:02d}"
                prior_path = session_dir / "phase2" / f"round-{rr}-{other_be}.md"
        if not prior_path or not prior_path.is_file():
            cache[key] = []
            return []
        try:
            text = prior_path.read_text(encoding="utf-8")
        except OSError:
            cache[key] = []
            return []
        _, records = assign_block_ids(text)
        cache[key] = records
        return records

    for q in questions:
        if not q.quote and not q.after:
            continue
        blocks = _prior_blocks(q.phase, q.raised_round, q.raised_by)
        if not blocks:
            continue
        if q.quote:
            needle = re.sub(r"\s+", " ", q.quote).strip().lower()
            for b in blocks:
                hay = re.sub(r"\s+", " ", b.text).strip().lower()
                if needle and needle in hay:
                    q.block_id = b.id
                    break
        if q.block_id is None and q.after:
            needle = re.sub(r"\s+", " ", q.after).strip().lower()
            for b in blocks:
                hay = re.sub(r"\s+", " ", b.text).strip().lower()
                if hay == needle:
                    q.block_id = b.id
                    break


# ─── Spec 0043 — ledger drift signal ──────────────────────────────────


def _compute_ledger_drifts(run: Run) -> list[dict]:
    """Emit one drift event per (turn, kind) where the agent's
    self-reported counter disagrees with the ledger's count of items
    in the same state.

    The check runs against each turn's terminal counter:
    - ``stats.openQuestions`` vs the ledger's count of open questions
      RAISED in or BEFORE this turn that are still open after it.
    - ``stats.blocking`` (BLOCKING_DISAGREEMENTS) vs the ledger's count
      of open disagreements at the same point.
    - ``stats.openIssues`` (Phase 4 only) vs the ledger's count of open
      issues at the same point.

    For v1 the comparison is end-of-phase only: if the final round's
    agent counter says 0 but the ledger has open entries, that's a
    drift event for the (phase, kind). Per-turn granularity would
    require replaying the ledger up to each turn — deferred to a
    follow-up if the end-of-phase signal proves insufficient.
    """
    drifts: list[dict] = []
    # Phase 2 + Phase 4 end-of-phase check.
    for phase, kind, counter_attr in (
        (2, "question", "open_questions"),
        (2, "disagreement", "blocking"),
        (4, "issue", "open_issues"),
    ):
        ledger_entries = run.phase_ledgers.get(phase, [])
        ledger_open = sum(
            1 for e in ledger_entries
            if e.get("kind") == kind and e.get("current_status") == "open"
        )
        # Find the latest round's stats per agent.
        stats_dict = (
            run.phase_stats.phase2 if phase == 2 else run.phase_stats.phase4
        )
        if not stats_dict:
            continue
        last_round = max(stats_dict.keys())
        per_agent = stats_dict.get(last_round, {})
        # Aggregate the agents' counters — the convergence check treats
        # them as "both must report 0", so we compare the sum (which
        # is 0 iff both are 0 individually).
        agent_total = 0
        for ts in per_agent.values():
            val = getattr(ts, counter_attr, None)
            if val is not None:
                agent_total += val
        if agent_total == ledger_open:
            continue
        # Drift recorded.
        turn_key = f"phase{phase}_round{last_round}_summary"
        drifts.append({
            "turn_key": turn_key,
            "kind": kind,
            "agent_count": agent_total,
            "ledger_count": ledger_open,
            "severity": "warn" if ledger_open > agent_total else "info",
        })
    return drifts


# ─── Spec 0115 — per-category Item aggregation ────────────────────────


def _attach_item_aggregation(run, transcript_path, session_dir=None):
    """Populate the new per-category Item fields on PhaseStats by walking
    the new ``item_raised`` / ``item_transitioned`` event stream.

    Pre-spec-0114 runs produce no such events; the new fields stay empty
    and the legacy UI path uses the scalar fields on ``TurnStats``.

    Spec 0122 — when the transcript carries no item events but the
    session directory has v2 round files on disk, fall back to
    ``replay_items_from_disk`` so historical runs (created before the
    event-bus → transcript bridge landed) still surface their items.
    Returns the ``AggregatedItems`` bundle so the caller can project
    it into the legacy typed lists + ``phase_ledgers``.
    """
    from dual_research.ui.items import (
        aggregate_items_from_transcript,
        build_session_audit_lookup,
    )
    from dual_research.ui.models import TurnStats

    # Spec 0144 — when we have a session dir, build an audit_lookup so
    # evidence records get densified with consulted_sources from the
    # persisted TurnSearchAudit bundles. Cold replay (no session_dir)
    # gets empty consulted_sources, matching the pre-spec behaviour.
    audit_lookup = (
        build_session_audit_lookup(session_dir) if session_dir is not None else None
    )
    bundle = aggregate_items_from_transcript(transcript_path, audit_lookup=audit_lookup)
    if not bundle.items and session_dir is not None:
        from dual_research.ledger.replay import replay_items_from_disk
        bundle = replay_items_from_disk(session_dir, audit_lookup=audit_lookup)
    run.phase_stats.items = list(bundle.items)
    if 0 in bundle.phase_category_stats:
        run.phase_stats.phase_summary_0 = bundle.phase_category_stats[0]
    if 2 in bundle.phase_category_stats:
        run.phase_stats.phase_summary_2 = bundle.phase_category_stats[2]
    if 4 in bundle.phase_category_stats:
        run.phase_stats.phase_summary_4 = bundle.phase_category_stats[4]

    for phase, by_round in bundle.turn_category_stats.items():
        for round_no, by_agent in by_round.items():
            for agent, cat_stats in by_agent.items():
                ui_agent = "gpt" if agent == "openai" else agent
                if phase == 2:
                    slot = run.phase_stats.phase2.setdefault(round_no, {})
                elif phase == 4:
                    slot = run.phase_stats.phase4.setdefault(round_no, {})
                elif phase == 0:
                    # Spec 0135 — Phase 0 is now round-keyed (matching
                    # Phase 2 / Phase 4). Pre-0114 legacy transcripts
                    # produce no Phase 0 item events at all and never
                    # reach this branch, so the round-keyed shape is
                    # safe to assume here.
                    slot = run.phase_stats.phase0.setdefault(round_no, {})
                else:
                    continue
                existing = slot.get(ui_agent) or TurnStats()
                existing.categories = cat_stats
                slot[ui_agent] = existing

    # Spec 0122 — carry-forward standing for rounds where neither agent
    # raised or transitioned anything (e.g. both agents emit
    # ``STATUS: AGREED`` with empty operation arrays before convergence
    # is actually reached). Without this, the timeline card for that
    # round renders no chips at all instead of "0 +0/-0 on standing N".
    _fill_carry_forward_categories(run)
    return bundle


def _fill_carry_forward_categories(run) -> None:
    """For every round file present on disk where ``stats.categories``
    is None, populate it with a carry-forward ``TurnCategoryStats`` whose
    ``standing`` matches the same agent's most recent populated round.
    ``raised`` and ``closed`` stay at zero — nothing happened that round.

    This is a presentation fix only: convergence math reads from
    ``phase_ledgers`` (the item pipeline), which already accounts for
    every item regardless of whether the round had any operations.
    """
    from dual_research.ui.models import CategoryCounters, TurnCategoryStats
    for phase_dict in (
        run.phase_stats.phase0,
        run.phase_stats.phase2,
        run.phase_stats.phase4,
    ):
        if not phase_dict:
            continue
        # Spec 0135 — phase 0 is dual-shape during the transition. Skip
        # the carry-forward pass for the legacy per-agent shape (values
        # are TurnStats, not dict[str, TurnStats]); only the new
        # round-keyed shape participates in carry-forward standing.
        sample_key = next(iter(phase_dict))
        if not isinstance(sample_key, int):
            continue
        # Per-agent running standing across rounds, in ascending order.
        running: dict[str, dict[str, int]] = {}
        for round_no in sorted(phase_dict.keys()):
            for ui_agent, ts in phase_dict[round_no].items():
                agent_run = running.setdefault(ui_agent, {
                    "questions": 0, "disagreements": 0,
                    "issues": 0, "comments": 0,
                })
                if ts.categories is None:
                    # Carry-forward: zeros for raised/closed; standing
                    # inherits the prior round's running total.
                    new_cats = TurnCategoryStats()
                    for kind in ("questions", "disagreements", "issues", "comments"):
                        getattr(new_cats, kind).standing = agent_run[kind]
                    ts.categories = new_cats
                else:
                    # Update running totals from this round's absolute
                    # standing (``_finalise_running_totals`` already
                    # converted deltas to absolutes).
                    for kind in ("questions", "disagreements", "issues", "comments"):
                        agent_run[kind] = getattr(ts.categories, kind).standing
