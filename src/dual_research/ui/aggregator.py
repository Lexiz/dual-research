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
from dual_research.agents.pricing import compute_search_cost
from dual_research.config import TIERS
from dual_research.ui.models import (
    AgentState,
    Disagreement,
    Run,
    RunListRow,
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
    for event in transcript:
        apply_event(run, event, session_dir)

    _augment_from_state_json(run, session_dir / "state.json")
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
    elif kind == "turn_inputs":
        _on_turn_inputs(run, event, session_dir)
    elif kind == "turn_searches":
        _on_turn_searches(run, event, session_dir)
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
    # cleanly. Single-shot phases (0, 1, 3) use phase{N}_<agent>;
    # round-loop phases (2, 4) use phase{N}_round{R}_<agent>. The model id
    # is recorded so the frontend can pick the right context-window
    # denominator, even if the agent's `model_id` later changes mid-run.
    phase_int = phase_to_int(phase_str)
    if phase_int in (2, 4) and idx > 0:
        key = f"phase{phase_int}_round{idx}_{ag}"
    else:
        key = f"phase{phase_int}_{ag}"
    # Spec 0030: per-piece sizes and the real context-window cap travel with
    # each turn. The frontend renormalises piece widths against `input_tokens`
    # (the provider's count) for honest segment proportions.
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

    # Spec 0039 — same-label dedup (parse-error retries) is handled
    # upstream by ``_dedup_turn_ended_by_label`` so by the time we get
    # here the event stream is canonical. The agent-level totals
    # accumulate every event unconditionally; the per-turn dict
    # overwrites when sibling labels share a key (e.g. ``phase4-r1-claude``
    # and ``phase4-r1-claude-repair`` both → ``phase4_round1_claude``)
    # — the LAST sibling wins on the Consumption tab card but BOTH
    # contribute to the agent rollup, which matches the real billing.
    state.tokens.in_ += in_tokens
    state.tokens.out += out_tokens
    state.cost += cost
    state.search_cost += search_cost

    # Spec 0039 D9: token_cost = full cost - search cost. The breakdown
    # is what the Consumption tab's "of which web search" reads; the
    # invariant token_cost + search_cost == cost holds for every turn.
    token_cost = max(0.0, cost - search_cost)
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
    )


def build_phase0_input_bundle(session_dir: Path) -> dict | None:
    """Spec 0033 — synthesise the shared Phase 0 input bundle on demand.

    Called by the UI server for the special ``input`` turn-key (the
    "input modal" on the run's Phase 0 card). Reads ``brief.md`` and
    composes a preflight-shaped bundle with a placeholder ``agent_name``.

    Returns the JSON-ready payload or ``None`` if ``brief.md`` is
    missing.
    """
    from dual_research.protocol.prompts import preflight_input_bundle

    brief_path = session_dir / "brief.md"
    if not brief_path.exists():
        return None
    try:
        brief_text = brief_path.read_text(encoding="utf-8")
    except OSError:
        return None
    pieces = preflight_input_bundle(brief=brief_text, agent_name="<agent>")
    return {
        "agent": "shared",
        "phase": "phase0",
        "label": "phase0-input",
        "pieces": pieces,
        "emitted_at": "",
    }


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
    if phase_int in (2, 4) and idx > 0:
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
    try:
        inputs_dir.mkdir(parents=True, exist_ok=True)
        path = inputs_dir / f"{key}.json"
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
    if phase_int in (2, 4) and idx > 0:
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
    from dual_research.protocol.parse import resolve_review_items

    out: dict[str, list[dict]] = {}
    # Cache the current-draft path lookup so we don't probe the
    # phase4 directory once per turn.
    cached_current_draft: str | None = None

    def _resolve_prior_blocks(phase_n: int, round_n: int, agent_be: str):
        nonlocal cached_current_draft
        # Mirror ``ui/static/run-detail.jsx::priorContentPathFor``.
        if phase_n == 4:
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

    for phase_n in (2, 4):
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
            items = resolve_review_items(text, prior_blocks)
            if not items:
                continue
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
