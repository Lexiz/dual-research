from __future__ import annotations

import asyncio
import logging
import sys
import time
from dataclasses import dataclass

from dual_research.agents.base import AgentCall
from dual_research.events import (
    EventBus,
    Phase0Complete,
    PhaseEntered,
    PhaseExited,
)
from dual_research.orchestrator._call import run_one_call
from dual_research.persistence import SessionContext
from dual_research.persistence.state import write_atomic
from dual_research.protocol import Status, parse_preflight_turn, preflight_prompt
from dual_research.protocol.prompt_pieces import pieces_for_preflight

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Phase0Outcome:
    claude_status: str | None
    openai_status: str | None
    claude_brief_issues: int | None
    openai_brief_issues: int | None
    brief_needs_input: bool


async def run_phase0(
    *,
    ctx: SessionContext,
    claude_agent: AgentCall,
    openai_agent: AgentCall,
    event_bus: EventBus,
    brief_content: str,
) -> Phase0Outcome:
    phase_dir = ctx.session.phase_dir("phase0")
    await event_bus.publish(PhaseEntered(phase="phase0"))
    ctx.transcript.write("phase_entered", phase="phase0")
    started = time.perf_counter()

    claude_prompt = preflight_prompt(brief_content=brief_content, agent_name="claude")
    openai_prompt = preflight_prompt(brief_content=brief_content, agent_name="openai")
    # Spec 0030: per-piece token sizes for the Consumption tab.
    p0_pieces = pieces_for_preflight(brief=brief_content)

    print("\n[phase 0] preflight — both agents in parallel\n", flush=True)

    claude_result, openai_result = await asyncio.gather(
        run_one_call(
            agent=claude_agent,
            prompt=claude_prompt,
            label="phase0-claude",
            phase="phase0",
            metrics=ctx.metrics,
            transcript=ctx.transcript,
            event_bus=event_bus,
            stream_to=None,
            max_output_tokens=4096,
            prompt_pieces=p0_pieces,
        ),
        run_one_call(
            agent=openai_agent,
            prompt=openai_prompt,
            label="phase0-openai",
            phase="phase0",
            metrics=ctx.metrics,
            transcript=ctx.transcript,
            event_bus=event_bus,
            stream_to=None,
            max_output_tokens=4096,
            prompt_pieces=p0_pieces,
        ),
    )

    write_atomic(phase_dir / "preflight-claude.md", claude_result.text)
    write_atomic(phase_dir / "preflight-openai.md", openai_result.text)

    c_parsed = parse_preflight_turn(claude_result.text)
    o_parsed = parse_preflight_turn(openai_result.text)
    needs_input = (
        c_parsed.status == Status.BRIEF_NEEDS_INPUT.value
        or o_parsed.status == Status.BRIEF_NEEDS_INPUT.value
    )

    outcome = Phase0Outcome(
        claude_status=c_parsed.status,
        openai_status=o_parsed.status,
        claude_brief_issues=c_parsed.brief_issues,
        openai_brief_issues=o_parsed.brief_issues,
        brief_needs_input=needs_input,
    )

    await event_bus.publish(
        Phase0Complete(
            claude_status=outcome.claude_status,
            openai_status=outcome.openai_status,
            claude_brief_issues=outcome.claude_brief_issues,
            openai_brief_issues=outcome.openai_brief_issues,
            brief_needs_input=outcome.brief_needs_input,
        )
    )
    ctx.transcript.write(
        "phase0_complete",
        claude_status=outcome.claude_status,
        openai_status=outcome.openai_status,
        claude_brief_issues=outcome.claude_brief_issues,
        openai_brief_issues=outcome.openai_brief_issues,
        brief_needs_input=outcome.brief_needs_input,
    )

    if needs_input:
        flaggers = []
        if c_parsed.status == Status.BRIEF_NEEDS_INPUT.value:
            flaggers.append("claude")
        if o_parsed.status == Status.BRIEF_NEEDS_INPUT.value:
            flaggers.append("openai")
        print(
            f"\n[phase 0] NOTE: {', '.join(flaggers)} flagged BRIEF_NEEDS_INPUT — "
            f"continuing anyway (autonomous mode). See preflight files in "
            f"{phase_dir} for details.",
            flush=True,
        )
    else:
        print(
            f"\n[phase 0] both agents: BRIEF_OK "
            f"(claude issues={c_parsed.brief_issues}, openai issues={o_parsed.brief_issues}).",
            flush=True,
        )

    duration_ms = int((time.perf_counter() - started) * 1000)
    await event_bus.publish(PhaseExited(phase="phase0", duration_ms=duration_ms))
    ctx.transcript.write("phase_exited", phase="phase0", duration_ms=duration_ms)
    return outcome
