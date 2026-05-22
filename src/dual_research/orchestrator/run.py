from __future__ import annotations

import asyncio
import logging
import sys
import time
import traceback
from dataclasses import dataclass

from dual_research.agents import ClaudeAgent, GptAgent, make_agents
from dual_research.config import Credentials, ModelTier, SupabaseCredentials
from dual_research.events import (
    CloseoutUrged,
    CloseoutViolation,
    CostUpdate,
    EmptyTurnDetected,
    EventBus,
    ItemRaised,
    ItemTransitioned,
    PhaseConverged,
    ProtocolViolation,
    RunCompleted,
    RunFailed,
    RunStarted,
    TurnEnded,
)
from dual_research.orchestrator.finalize import emit_final
# Spec 0114 — the production path uses the new Deep Research runners.
# The legacy ``run_phase{0..4}`` coroutines remain importable for their
# dedicated tests but ``run.py`` no longer calls them.
from dual_research.orchestrator.dr_run import (
    run_dr_phase0 as run_phase0,
    run_dr_phase1 as run_phase1,
    run_dr_phase2 as run_phase2,
    run_dr_phase3 as run_phase3,
    run_dr_phase4 as run_phase4,
)
from dual_research.orchestrator.phase0 import Phase0Outcome
from dual_research.orchestrator.phase1 import Phase1Outcome
from dual_research.orchestrator.phase2 import Phase2Outcome
from dual_research.orchestrator.phase3 import Phase3Outcome
from dual_research.orchestrator.phase4 import Phase4Outcome
from dual_research.persistence import (
    Metrics,
    SessionContext,
    SessionDirectory,
)
from dual_research.persistence.state import SessionState, write_atomic
from dual_research.protocol.prompt_pieces import Attachment

logger = logging.getLogger(__name__)


# Text-mime-type prefixes whose attachment content is read off disk and
# threaded through the protocol layer as `Attachment.content`. Binary
# attachments (images, PDFs) get empty content + a zero-token row on
# the consumption card — their actual prompt-encoded cost lands in the
# provider-reported input_tokens, which the renormaliser proportionally
# distributes across the populated piece rows.
_TEXT_ATTACHMENT_EXTS = frozenset({
    ".md", ".markdown", ".txt", ".text", ".log", ".json", ".yaml", ".yml",
    ".toml", ".rst", ".csv", ".tsv", ".html", ".htm", ".xml", ".sql",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".css", ".sh", ".bash",
})


def _slug(value: str) -> str:
    """Conservative slugifier — alphanumerics + dashes only."""
    return "".join(c if c.isalnum() else "-" for c in (value or "")).strip("-")


def _attachment_id(ing) -> str:
    """Spec 0145 §5.1 — stable canonical ID for `user_prompt.attachment.<id>`.

    Prefers the first 8 chars of the content sha256 (set for local-file
    attachments). Falls back to a slugified basename for URL attachments
    that don't carry a hash. The ID must match the registry's `<id>`
    placeholder regex (``[^.]+(?:\\..+)?``) — both branches satisfy it.
    """
    from pathlib import Path as _Path

    if getattr(ing, "sha256", None):
        return ing.sha256[:8]
    base = (
        getattr(ing, "rel_path", None)
        or getattr(ing, "source", None)
        or ""
    )
    if base:
        slug = _slug(_Path(base).stem)
        if slug:
            return slug
    return "attachment"


def _read_attachment_text(session_root, ing) -> str:
    """Read a text attachment's content from disk, or return ''.

    `rel_path` is the in-session path written by the materialiser
    (e.g. ``attachments/a3f4b9c2-foo.md``). Only files whose extension
    is in ``_TEXT_ATTACHMENT_EXTS`` are read — binary attachments get
    empty content and contribute a zero-width row to the consumption
    card.
    """
    from pathlib import Path as _Path

    rel = getattr(ing, "rel_path", None)
    if not rel:
        return ""
    path = _Path(session_root) / rel
    if not path.exists() or not path.is_file():
        return ""
    if path.suffix.lower() not in _TEXT_ATTACHMENT_EXTS:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _resolve_run_attachments(session_root) -> list[Attachment]:
    """Spec 0145 §5.1 — convert `attachments.json` → `prompt_pieces.Attachment` list.

    Loaded once at session setup and threaded through every
    `pieces_for_*()` / `*_input_bundle()` call for the run. Returns an
    empty list if `attachments.json` is missing or empty.
    """
    import json as _json

    from dual_research.ingest import AttachmentBundle

    path = session_root / "attachments.json"
    if not path.exists():
        return []
    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError):
        return []
    bundle = AttachmentBundle.from_dict(data)
    out: list[Attachment] = []
    from pathlib import Path as _Path

    for ing in bundle.attachments:
        title = (
            ing.title
            or _Path(ing.rel_path or ing.source or "").name
            or "attachment"
        )
        out.append(
            Attachment(
                id=_attachment_id(ing),
                title=title,
                content=_read_attachment_text(session_root, ing),
            )
        )
    return out

EXIT_OK = 0
EXIT_RUNTIME = 2
EXIT_HARD_CAP = 51
EXIT_PROTOCOL_PARSE_FAILURE = 52


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    phase_reached: str
    total_cost_usd: float
    duration_ms: int
    phase0: Phase0Outcome | None = None
    phase1: Phase1Outcome | None = None
    phase2: Phase2Outcome | None = None
    phase3: Phase3Outcome | None = None
    phase4: Phase4Outcome | None = None
    final_path: str | None = None
    # Spec 0039: search-fee component of ``total_cost_usd``. The CLI
    # summary surfaces "(tokens $X · web search $Y)" when this is > 0.
    total_search_cost_usd: float = 0.0


def _install_cost_ticker(event_bus: EventBus, metrics: Metrics) -> None:
    async def on_turn_ended(event):
        if not isinstance(event, TurnEnded):
            return
        total = metrics.total_cost_usd()
        by_agent = {a: t["cost_usd"] for a, t in metrics.totals_by_agent().items()}
        await event_bus.publish(CostUpdate(total_usd=total, by_agent=by_agent))
        cache_note = ""
        if event.cache_read_tokens or event.cache_write_tokens:
            cache_note = (
                f"  cache:r={event.cache_read_tokens:,}/w={event.cache_write_tokens:,}"
            )
        print(
            f"\n[{event.agent}] {event.phase}  in={event.input_tokens:,}  "
            f"out={event.output_tokens:,}{cache_note}  ${event.cost_usd:.4f}  "
            f"{event.duration_ms / 1000:.1f}s   |   "
            f"running total: ${total:.4f}",
            flush=True,
        )

    event_bus.subscribe(on_turn_ended)


def _install_transcript_publisher(event_bus: EventBus, ctx: SessionContext) -> None:
    """Metrics save-on-every-event subscriber. Item-lifecycle event
    mirroring is handled separately by ``_install_transcript_bridge`` so
    the two concerns are independently testable."""
    async def on_event(_event):
        ctx.metrics.save(ctx.session.metrics_path)

    event_bus.subscribe(on_event)


# Spec 0122 — event types the bridge mirrors into transcript.jsonl.
# Limited to types the orchestrator does NOT already double-write via a
# direct ``transcript.write(...)`` call; adding any of those here would
# duplicate lines.
_TRANSCRIPT_MIRRORED_EVENTS = (
    ItemRaised,
    ItemTransitioned,
    CloseoutUrged,
    CloseoutViolation,
    PhaseConverged,
    # Spec 0141 — protocol-invariant violations + empty-turn signals
    # land on the bus from `apply_turn`; mirror them to the transcript
    # for the audit trail (no UI surface in this spec).
    ProtocolViolation,
    EmptyTurnDetected,
)


def _install_transcript_bridge(event_bus: EventBus, ctx: SessionContext) -> None:
    """Spec 0122 — mirror Deep-Research lifecycle events to the transcript.

    Without this bridge, ``ItemRaised`` / ``ItemTransitioned`` /
    ``CloseoutUrged`` / ``CloseoutViolation`` / ``PhaseConverged`` events
    are published to the bus but never persisted, so the UI aggregator
    (``aggregate_items_from_transcript``) finds nothing and every per-
    category badge/filter renders empty.
    """
    async def on_event(event):
        if not isinstance(event, _TRANSCRIPT_MIRRORED_EVENTS):
            return
        payload = event.to_dict()
        name = payload.pop("kind", None)
        if not name:
            return
        ctx.transcript.write(name, **payload)

    event_bus.subscribe(on_event)


def _persist_initial_brief_bundle(
    session_root,
    brief_text: str,
    attachments: "list[Attachment] | tuple[Attachment, ...]" = (),
) -> None:
    """Spec 0142 — write ``inputs/input.json`` once at session setup.

    Stamps ``system_source="recorded"`` so the hosted UI's Initial
    Brief modal does not render the spec-0085 "agent default — not
    recorded" caveat. The file is then picked up by
    :func:`dual_research.persistence.remote._iter_file_rows` and pushed
    to Supabase like every other input bundle. Idempotent: a re-entry
    on a resumed run leaves the existing file alone.

    Spec 0145 — ``attachments`` threads the run's resolved attachment
    list into the persisted bundle so the Initial-Brief modal can
    render per-attachment rows on canonical-ID hydration.
    """
    import json as _json

    from dual_research.protocol.prompts import preflight_input_bundle

    inputs_dir = session_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    path = inputs_dir / "input.json"
    if path.exists():
        return
    payload = {
        "agent": "shared",
        "phase": "phase0",
        "label": "phase0-input",
        "pieces": preflight_input_bundle(
            brief=brief_text,
            attachments=attachments,
            agent_name="<both>",
        ),
        "emitted_at": "",
        "system_source": "recorded",
    }
    write_atomic(path, _json.dumps(payload, indent=2))


async def run_session(
    *,
    session_root,
    slug: str,
    creds: Credentials,
    tier: ModelTier,
    soft_cap: int,
    hard_cap: int,
    out_path=None,
    event_bus: EventBus | None = None,
    push_while_running: SupabaseCredentials | None = None,
) -> RunResult:
    """Drive a session from its current state through as many phases as
    are wired up.

    Spec 0032: when ``push_while_running`` is set, spawn a background
    task that pushes the session-dir to Supabase every 30 s. A final
    synchronous push runs in the finally block at exit so the hosted UI
    always sees the completed state even if the run errored.
    """
    session = SessionDirectory(root=session_root).ensure()
    state = session.load_state()
    transcript = session.open_transcript()
    # Spec 0039 — rehydrate any prior metrics.json so resumed runs preserve
    # the cost record across session boundaries. Without this, the
    # post-resume save() overwrites the pre-resume call list with only the
    # resume-window calls (the partner-vetting bug that drove this spec).
    metrics = Metrics.load_or_new(session.metrics_path)
    ctx = SessionContext(session=session, state=state, transcript=transcript, metrics=metrics)

    # Spec 0032 — write state.json immediately so --push-while-running can
    # succeed from tick 1. Without this, RemoteSession.push_session_dir
    # raises FileNotFoundError ("Missing state.json — not a completed
    # session dir") for the entire phase-0 window, because state.json is
    # otherwise first written only when phase 0 converges (dr_run.py).
    # The hosted UI then shows a 404 for the brief-interpretation
    # negotiation — precisely the window the user most wants to follow.
    # For a resumed run this is a no-op (state already loaded from disk).
    session.save_state(state)

    bus = event_bus or EventBus()
    _install_cost_ticker(bus, metrics)
    _install_transcript_publisher(bus, ctx)
    _install_transcript_bridge(bus, ctx)

    # Spec 0032 — live-push setup. Spawn the periodic-push task once
    # the run is about to start; cleanly stop it in the finally block
    # so the run always ends with a synchronous final push.
    push_stop_event: asyncio.Event | None = None
    push_task: asyncio.Task | None = None
    if push_while_running is not None:
        push_stop_event = asyncio.Event()
        push_task = asyncio.create_task(
            _push_watch_loop(
                session_dir=session.root,
                creds=push_while_running,
                stop=push_stop_event,
            )
        )
        print(
            f"[push-while-running] enabled — pushing to {push_while_running.url} "
            f"every 30s. Hosted UI will update as the run progresses.",
            flush=True,
        )

    claude, gpt = make_agents(tier=tier, creds=creds)

    await bus.publish(
        RunStarted(
            session_dir=str(session.root),
            slug=slug,
            model_tier=tier.name,
            claude_model=tier.claude.model_id,
            openai_model=tier.openai.model_id,
            soft_cap=soft_cap,
            hard_cap=hard_cap,
            # Spec 0030: real context-window caps from the tier's ModelSpec.
            claude_context_window=tier.claude.context_window,
            openai_context_window=tier.openai.context_window,
        )
    )
    transcript.write(
        "run_started",
        session_dir=str(session.root),
        slug=slug,
        model_tier=tier.name,
        claude_model=tier.claude.model_id,
        openai_model=tier.openai.model_id,
        soft_cap=soft_cap,
        hard_cap=hard_cap,
        claude_context_window=tier.claude.context_window,
        openai_context_window=tier.openai.context_window,
    )

    brief_content = session.brief_path.read_text(encoding="utf-8")
    # Spec 0145 — resolve `attachments.json` once and thread the list
    # through every phase runner so per-attachment token attribution
    # and per-attachment piece-text rows land uniformly.
    run_attachments = _resolve_run_attachments(session.root)
    # Spec 0142 — persist the shared Phase-0 "Initial Brief" input bundle
    # at session setup so the hosted UI's full-view modal (turnKey='input')
    # hydrates from a real recorded row instead of falling through to the
    # spec-0085 synthesis path that stamps system_source="agent-default".
    _persist_initial_brief_bundle(session.root, brief_content, run_attachments)
    run_started = time.perf_counter()
    phase0_outcome: Phase0Outcome | None = None
    phase1_outcome: Phase1Outcome | None = None
    phase2_outcome: Phase2Outcome | None = None
    phase3_outcome: Phase3Outcome | None = None
    phase4_outcome: Phase4Outcome | None = None
    final_path: str | None = None
    phase_reached = state.phase
    exit_code = EXIT_OK

    try:
        if state.phase == "phase0":
            phase0_outcome = await run_phase0(
                ctx=ctx,
                claude_agent=claude,
                openai_agent=gpt,
                event_bus=bus,
                brief_content=brief_content,
                attachments=run_attachments,
            )
            state.phase = "phase1"
            session.save_state(state)
            phase_reached = "phase1"
        else:
            print(f"[phase 0] skipped (state already at {state.phase}).", flush=True)

        if state.phase == "phase1":
            phase1_outcome = await run_phase1(
                ctx=ctx,
                claude_agent=claude,
                openai_agent=gpt,
                event_bus=bus,
                brief_content=brief_content,
                attachments=run_attachments,
            )
            state.phase = "phase2"
            session.save_state(state)
            phase_reached = "phase2"
        else:
            print(f"[phase 1] skipped (state already at {state.phase}).", flush=True)

        if state.phase == "phase2":
            phase2_outcome = await run_phase2(
                ctx=ctx,
                claude_agent=claude,
                openai_agent=gpt,
                event_bus=bus,
                brief_content=brief_content,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
                attachments=run_attachments,
            )
            if phase2_outcome.parse_failure:
                exit_code = EXIT_PROTOCOL_PARSE_FAILURE
                phase_reached = "phase2"
            elif phase2_outcome.hard_capped:
                _emit_phase2_deadlock(ctx.session.root, phase2_outcome)
                exit_code = EXIT_HARD_CAP
                phase_reached = "phase2"
            elif phase2_outcome.converged:
                phase_reached = "phase3"

        if exit_code == EXIT_OK and state.phase == "phase3":
            phase3_outcome = await run_phase3(
                ctx=ctx,
                claude_agent=claude,
                openai_agent=gpt,
                event_bus=bus,
                brief_content=brief_content,
                attachments=run_attachments,
            )
            phase_reached = "phase4"

        if exit_code == EXIT_OK and state.phase == "phase4":
            phase4_outcome = await run_phase4(
                ctx=ctx,
                claude_agent=claude,
                openai_agent=gpt,
                event_bus=bus,
                brief_content=brief_content,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
                attachments=run_attachments,
            )
            if phase4_outcome.parse_failure:
                exit_code = EXIT_PROTOCOL_PARSE_FAILURE
                phase_reached = "phase4"
            elif phase4_outcome.hard_capped:
                exit_code = EXIT_HARD_CAP
                phase_reached = "phase4"
            else:
                phase_reached = "done"

        # Emit final document if Phase 4 completed (approved or hard-capped).
        if phase4_outcome is not None and not phase4_outcome.parse_failure:
            final_emitted = await emit_final(
                ctx=ctx,
                event_bus=bus,
                out_path=out_path,
                phase2_outcome=phase2_outcome,
                phase4_outcome=phase4_outcome,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
                claude_model=tier.claude.model_id,
                openai_model=tier.openai.model_id,
            )
            final_path = str(final_emitted)

        total_cost = metrics.total_cost_usd()
        total_search_cost = metrics.total_search_cost_usd()
        duration_ms = int((time.perf_counter() - run_started) * 1000)
        metrics.mark_done()
        metrics.save(session.metrics_path)

        await bus.publish(
            RunCompleted(
                phase_reached=phase_reached,
                exit_code=exit_code,
                total_cost_usd=total_cost,
                duration_ms=duration_ms,
            )
        )
        transcript.write(
            "run_completed",
            phase_reached=phase_reached,
            exit_code=exit_code,
            total_cost_usd=total_cost,
            duration_ms=duration_ms,
        )

        return RunResult(
            exit_code=exit_code,
            phase_reached=phase_reached,
            total_cost_usd=total_cost,
            duration_ms=duration_ms,
            phase0=phase0_outcome,
            phase1=phase1_outcome,
            phase2=phase2_outcome,
            phase3=phase3_outcome,
            phase4=phase4_outcome,
            final_path=final_path,
            total_search_cost_usd=total_search_cost,
        )

    except Exception as e:
        duration_ms = int((time.perf_counter() - run_started) * 1000)
        metrics.mark_done()
        metrics.save(session.metrics_path)
        await bus.publish(
            RunFailed(
                phase_reached=phase_reached,
                error_type=type(e).__name__,
                message=str(e),
            )
        )
        transcript.write(
            "run_failed",
            phase_reached=phase_reached,
            error_type=type(e).__name__,
            message=str(e),
            traceback=traceback.format_exc(),
        )
        logger.exception("orchestrator failed during %s", phase_reached)
        return RunResult(
            exit_code=EXIT_RUNTIME,
            phase_reached=phase_reached,
            total_cost_usd=metrics.total_cost_usd(),
            duration_ms=duration_ms,
            phase0=phase0_outcome,
            phase1=phase1_outcome,
            phase2=phase2_outcome,
            phase3=phase3_outcome,
            phase4=phase4_outcome,
            final_path=final_path,
        )

    finally:
        # Spec 0032 — always stop the push-loop and do one final
        # synchronous push so the hosted UI sees the final state, even
        # on errored runs.
        if push_task is not None and push_stop_event is not None:
            push_stop_event.set()
            try:
                await asyncio.wait_for(push_task, timeout=60.0)
            except asyncio.TimeoutError:
                logger.warning(
                    "push-watch loop didn't drain in 60s; cancelling"
                )
                push_task.cancel()
            except Exception:  # the loop swallowed everything; defensive
                logger.exception("push-watch loop exited with error")


# ─── Spec 0032 — push-while-running loop ────────────────────────────────


async def _push_watch_loop(
    *,
    session_dir,
    creds: SupabaseCredentials,
    stop: asyncio.Event,
    interval_seconds: float = 30.0,
) -> None:
    """Periodic Supabase push during a live run.

    Calls ``RemoteSession.push_session_dir`` every ``interval_seconds``
    until ``stop`` is set, then does one final synchronous push at the
    end. Push failures are logged but do not propagate — a Supabase
    blip mid-run must not abort the orchestrator.

    Imported lazily so the supabase dep can stay optional for users
    who don't enable the flag.
    """
    from dual_research.persistence.remote import RemoteSession

    try:
        remote = RemoteSession.from_credentials(creds.url, creds.service_role_key)
    except Exception as e:
        logger.warning("push-watch: failed to initialise RemoteSession: %s", e)
        return

    # Wait briefly before the first push so the session-dir has time to
    # accumulate at least one phase's worth of artifacts. Avoids
    # uploading an empty dir on the very first tick.
    try:
        await asyncio.wait_for(stop.wait(), timeout=5.0)
        # Stop was already set — fall through to the final push below.
    except asyncio.TimeoutError:
        pass

    while not stop.is_set():
        try:
            remote.push_session_dir(session_dir)
        except Exception as e:
            logger.warning("push-watch: tick push failed: %s", e)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue

    # Final synchronous push — last tick before the orchestrator exits.
    try:
        remote.push_session_dir(session_dir)
        logger.info("push-watch: final push complete")
    except Exception as e:
        logger.warning("push-watch: final push failed: %s", e)


def _emit_phase2_deadlock(session_root, phase2_outcome: Phase2Outcome) -> None:
    """Write a deadlock summary into the session root when Phase 2 hits the hard cap."""
    from pathlib import Path as _Path
    payload = (
        f"# Phase 2 deadlock\n\n"
        f"Hard cap reached after {phase2_outcome.rounds} rounds without agreement. "
        f"Both agents' last turns are preserved below for human adjudication.\n\n"
        f"---\n\n"
        f"## claude — last Phase 2 turn\n\n"
        f"{phase2_outcome.last_claude_text or '(no content)'}\n\n"
        f"---\n\n"
        f"## openai — last Phase 2 turn\n\n"
        f"{phase2_outcome.last_openai_text or '(no content)'}\n"
    )
    write_atomic(_Path(session_root) / "phase2-deadlock.md", payload)
