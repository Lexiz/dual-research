from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from dual_research.agents.base import AgentCall
from dual_research.events import (
    EventBus,
    Phase3Complete,
    PhaseEntered,
    PhaseExited,
)
from dual_research.orchestrator._call import run_one_call
from dual_research.orchestrator._turns import list_turns
from dual_research.persistence import SessionContext
from dual_research.persistence.state import write_atomic
from dual_research.protocol import FsdItem, drafting_prompt
from dual_research.protocol.prompts import drafting_input_bundle


@dataclass(frozen=True)
class Phase3Outcome:
    drafter: str
    draft_chars: int
    draft_path: str


async def run_phase3(
    *,
    ctx: SessionContext,
    claude_agent: AgentCall,
    openai_agent: AgentCall,
    event_bus: EventBus,
    brief_content: str,
) -> Phase3Outcome:
    drafter = ctx.state.drafter
    if drafter not in ("claude", "openai"):
        raise RuntimeError(f"Phase 3 reached without a valid drafter (state.drafter={drafter!r})")

    phase_dir = ctx.session.phase_dir("phase3")
    await event_bus.publish(PhaseEntered(phase="phase3"))
    ctx.transcript.write("phase_entered", phase="phase3")
    started = time.perf_counter()

    p1 = ctx.session.phase_dir("phase1")
    own_draft = (p1 / f"draft-{drafter}.md").read_text(encoding="utf-8")
    other = "openai" if drafter == "claude" else "claude"
    other_draft = (p1 / f"draft-{other}.md").read_text(encoding="utf-8")
    prior_turns = list_turns(ctx.session, phase="phase2")

    fsd_items = [FsdItem(**d) for d in (ctx.state.final_surfaced_disagreements or [])]

    agent = claude_agent if drafter == "claude" else openai_agent

    prompt = drafting_prompt(
        brief_content=brief_content,
        own_draft=own_draft,
        other_draft=other_draft,
        prior_turns=prior_turns,
        agent_name=drafter,
        other_name=other,
        agreed_plan_block=ctx.state.agreed_plan,
        final_surfaced_disagreements=fsd_items,
    )
    # Spec 0118: legacy run_phase3 path no longer emits Consumption-tab
    # piece breakdowns; dr_run.run_dr_phase3 is the active code path and
    # builds canonical-key pieces directly.
    p3_pieces = None
    claude_draft = own_draft if drafter == "claude" else other_draft
    openai_draft = own_draft if drafter == "openai" else other_draft
    # Spec 0033: per-piece TEXT bundle for the Input tab.
    p3_bundle = drafting_input_bundle(
        brief=brief_content,
        claude_draft=claude_draft,
        openai_draft=openai_draft,
        plan=ctx.state.agreed_plan,
        prior_turns=prior_turns,
        agent_name=drafter,
        other_name=other,
    )

    print(f"\n[phase 3] drafting by {drafter} (single-shot)\n", flush=True)
    result = await run_one_call(
        agent=agent,
        prompt=prompt,
        label=f"phase3-{drafter}",
        phase="phase3",
        metrics=ctx.metrics,
        transcript=ctx.transcript,
        event_bus=event_bus,
        stream_to=None,
        max_output_tokens=16384,
        prompt_pieces=p3_pieces,
        prompt_bundle=p3_bundle,
    )

    draft_path = phase_dir / "draft-v1.md"
    write_atomic(draft_path, result.text)

    outcome = Phase3Outcome(
        drafter=drafter, draft_chars=len(result.text), draft_path=str(draft_path)
    )
    await event_bus.publish(Phase3Complete(drafter=drafter, draft_chars=outcome.draft_chars))
    ctx.transcript.write(
        "phase3_complete",
        drafter=drafter,
        draft_chars=outcome.draft_chars,
        draft_path=str(draft_path),
    )

    ctx.state.phase = "phase4"
    ctx.session.save_state(ctx.state)

    duration_ms = int((time.perf_counter() - started) * 1000)
    await event_bus.publish(PhaseExited(phase="phase3", duration_ms=duration_ms))
    ctx.transcript.write("phase_exited", phase="phase3", duration_ms=duration_ms)

    print(f"\n[phase 3] draft v1 written ({outcome.draft_chars:,} chars).", flush=True)
    return outcome


def current_draft_path(session, draft_round: int) -> Path:
    """Resolve which file holds the current draft.

    Phase 3 writes draft-v1.md to phase3/. Phase 4 writes revisions to phase4/.
    """
    if draft_round == 1:
        return session.phase_dir("phase3") / "draft-v1.md"
    return session.phase_dir("phase4") / f"draft-v{draft_round}.md"
