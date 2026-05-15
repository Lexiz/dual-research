from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass

from dual_research.agents.base import AgentCall
from dual_research.events import (
    EventBus,
    Phase1Complete,
    PhaseEntered,
    PhaseExited,
)
from dual_research.orchestrator._call import run_one_call
from dual_research.persistence import SessionContext
from dual_research.persistence.state import write_atomic
from dual_research.protocol import research_prompt


@dataclass(frozen=True)
class Phase1Outcome:
    claude_chars: int
    openai_chars: int
    claude_path: str
    openai_path: str


async def run_phase1(
    *,
    ctx: SessionContext,
    claude_agent: AgentCall,
    openai_agent: AgentCall,
    event_bus: EventBus,
    brief_content: str,
) -> Phase1Outcome:
    phase_dir = ctx.session.phase_dir("phase1")
    await event_bus.publish(PhaseEntered(phase="phase1"))
    ctx.transcript.write("phase_entered", phase="phase1")
    started = time.perf_counter()

    claude_prompt = research_prompt(brief_content=brief_content, agent_name="claude")
    openai_prompt = research_prompt(brief_content=brief_content, agent_name="openai")

    print(
        "\n[phase 1] independent research — both agents in parallel "
        "(streaming Claude to stdout, GPT silent in parallel)\n",
        flush=True,
    )

    claude_result, openai_result = await asyncio.gather(
        run_one_call(
            agent=claude_agent,
            prompt=claude_prompt,
            label="phase1-claude",
            phase="phase1",
            metrics=ctx.metrics,
            transcript=ctx.transcript,
            event_bus=event_bus,
            stream_to=sys.stdout,
            stream_prefix="[claude] ",
            max_output_tokens=8192,
        ),
        run_one_call(
            agent=openai_agent,
            prompt=openai_prompt,
            label="phase1-openai",
            phase="phase1",
            metrics=ctx.metrics,
            transcript=ctx.transcript,
            event_bus=event_bus,
            stream_to=None,
            max_output_tokens=8192,
        ),
    )

    claude_path = phase_dir / "draft-claude.md"
    openai_path = phase_dir / "draft-openai.md"
    write_atomic(claude_path, claude_result.text)
    write_atomic(openai_path, openai_result.text)

    outcome = Phase1Outcome(
        claude_chars=len(claude_result.text),
        openai_chars=len(openai_result.text),
        claude_path=str(claude_path),
        openai_path=str(openai_path),
    )
    await event_bus.publish(
        Phase1Complete(claude_chars=outcome.claude_chars, openai_chars=outcome.openai_chars)
    )
    ctx.transcript.write(
        "phase1_complete",
        claude_chars=outcome.claude_chars,
        openai_chars=outcome.openai_chars,
        claude_path=str(claude_path),
        openai_path=str(openai_path),
    )

    duration_ms = int((time.perf_counter() - started) * 1000)
    await event_bus.publish(PhaseExited(phase="phase1", duration_ms=duration_ms))
    ctx.transcript.write("phase_exited", phase="phase1", duration_ms=duration_ms)

    print(
        f"\n[phase 1] drafts written: "
        f"claude={outcome.claude_chars:,} chars, openai={outcome.openai_chars:,} chars.",
        flush=True,
    )
    return outcome
