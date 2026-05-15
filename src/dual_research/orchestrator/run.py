from __future__ import annotations

import logging
import sys
import time
import traceback
from dataclasses import dataclass

from dual_research.agents import ClaudeAgent, GptAgent, make_agents
from dual_research.config import Credentials, ModelTier
from dual_research.events import (
    CostUpdate,
    EventBus,
    RunCompleted,
    RunFailed,
    RunStarted,
    TurnEnded,
)
from dual_research.orchestrator.finalize import emit_final
from dual_research.orchestrator.phase0 import Phase0Outcome, run_phase0
from dual_research.orchestrator.phase1 import Phase1Outcome, run_phase1
from dual_research.orchestrator.phase2 import Phase2Outcome, run_phase2
from dual_research.orchestrator.phase3 import Phase3Outcome, run_phase3
from dual_research.orchestrator.phase4 import Phase4Outcome, run_phase4
from dual_research.persistence import (
    Metrics,
    SessionContext,
    SessionDirectory,
)
from dual_research.persistence.state import SessionState, write_atomic

logger = logging.getLogger(__name__)

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
    """Future event subscribers (UI) get a hook here. For now we just keep
    metrics.json fresh after every event burst."""
    async def on_event(_event):
        ctx.metrics.save(ctx.session.metrics_path)

    event_bus.subscribe(on_event)


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
) -> RunResult:
    """Drive a session from its current state through as many phases as
    are wired up. Phase 0 and Phase 1 are implemented; Phases 2–4 are
    stubbed (the run exits cleanly after Phase 1 with a message)."""
    session = SessionDirectory(root=session_root).ensure()
    state = session.load_state()
    transcript = session.open_transcript()
    metrics = Metrics()
    ctx = SessionContext(session=session, state=state, transcript=transcript, metrics=metrics)

    bus = event_bus or EventBus()
    _install_cost_ticker(bus, metrics)
    _install_transcript_publisher(bus, ctx)

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
    )

    brief_content = session.brief_path.read_text(encoding="utf-8")
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
