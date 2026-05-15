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
from dual_research.orchestrator.phase0 import Phase0Outcome, run_phase0
from dual_research.orchestrator.phase1 import Phase1Outcome, run_phase1
from dual_research.persistence import (
    Metrics,
    SessionContext,
    SessionDirectory,
)
from dual_research.persistence.state import SessionState

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_RUNTIME = 2


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    phase_reached: str
    total_cost_usd: float
    duration_ms: int
    phase0: Phase0Outcome | None = None
    phase1: Phase1Outcome | None = None


def _install_cost_ticker(event_bus: EventBus, metrics: Metrics) -> None:
    async def on_turn_ended(event):
        if not isinstance(event, TurnEnded):
            return
        total = metrics.total_cost_usd()
        by_agent = {a: t["cost_usd"] for a, t in metrics.totals_by_agent().items()}
        await event_bus.publish(CostUpdate(total_usd=total, by_agent=by_agent))
        # Stdout ticker (per-call)
        print(
            f"\n[{event.agent}] {event.phase}  in={event.input_tokens:,}  "
            f"out={event.output_tokens:,}  ${event.cost_usd:.4f}  "
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
    phase_reached = state.phase

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

        # Phases 2-4 not yet implemented (specs 0003+). Stop here cleanly.
        if state.phase == "phase2":
            print(
                "\n[done] Phases 0 + 1 complete. Phases 2–4 are not yet wired up "
                "(see specs/0003+); future runs will negotiate, draft, and review.",
                flush=True,
            )

        total_cost = metrics.total_cost_usd()
        duration_ms = int((time.perf_counter() - run_started) * 1000)
        metrics.mark_done()
        metrics.save(session.metrics_path)

        await bus.publish(
            RunCompleted(
                phase_reached=phase_reached,
                exit_code=EXIT_OK,
                total_cost_usd=total_cost,
                duration_ms=duration_ms,
            )
        )
        transcript.write(
            "run_completed",
            phase_reached=phase_reached,
            exit_code=EXIT_OK,
            total_cost_usd=total_cost,
            duration_ms=duration_ms,
        )

        return RunResult(
            exit_code=EXIT_OK,
            phase_reached=phase_reached,
            total_cost_usd=total_cost,
            duration_ms=duration_ms,
            phase0=phase0_outcome,
            phase1=phase1_outcome,
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
        )
