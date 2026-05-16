from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, dataclass

from dual_research.agents.base import AgentCall
from dual_research.events import (
    DrafterTiebreakResolved,
    EventBus,
    HardCapHit,
    Phase2Complete,
    Phase2RoundComplete,
    PhaseEntered,
    PhaseExited,
    SoftCapHit,
)
from dual_research.orchestrator._call import run_one_call
from dual_research.orchestrator._turns import list_turns, turn_path
from dual_research.orchestrator.repair import RepairTracker, parse_with_repair
from dual_research.persistence import SessionContext
from dual_research.persistence.state import write_atomic
from dual_research.protocol import (
    ProtocolParseError,
    all_substantive_gates_pass_except_drafter,
    assert_well_formed_plan_turn,
    assert_well_formed_round1_turn,
    extract_canonical_fsd_items,
    is_plan_agreed,
    negotiation_round1_prompt,
    negotiation_turn_prompt,
    parse_turn,
    pick_drafter,
)
from dual_research.protocol.prompt_pieces import (
    pieces_for_negotiation_round1,
    pieces_for_negotiation_turn,
)


@dataclass(frozen=True)
class Phase2Outcome:
    converged: bool
    rounds: int
    drafter: str | None
    agreed_plan: str | None
    fsd_count: int
    via_tiebreak: bool
    hard_capped: bool
    parse_failure: bool = False
    parse_failure_agent: str | None = None
    last_claude_text: str | None = None
    last_openai_text: str | None = None


async def run_phase2(
    *,
    ctx: SessionContext,
    claude_agent: AgentCall,
    openai_agent: AgentCall,
    event_bus: EventBus,
    brief_content: str,
    soft_cap: int,
    hard_cap: int,
) -> Phase2Outcome:
    phase_dir = ctx.session.phase_dir("phase2")
    await event_bus.publish(PhaseEntered(phase="phase2"))
    ctx.transcript.write("phase_entered", phase="phase2")
    started = time.perf_counter()

    claude_draft = (ctx.session.phase_dir("phase1") / "draft-claude.md").read_text(encoding="utf-8")
    openai_draft = (ctx.session.phase_dir("phase1") / "draft-openai.md").read_text(encoding="utf-8")

    tracker = RepairTracker()
    converged = False
    via_tiebreak = False
    rounds_done = 0
    last_claude_text: str | None = None
    last_openai_text: str | None = None
    parse_failure = False
    parse_failure_agent: str | None = None

    for r in range(1, hard_cap + 1):
        rounds_done = r
        print(f"\n[phase 2] round {r}/{hard_cap}\n", flush=True)

        # Build prompts
        if r == 1:
            claude_prompt = negotiation_round1_prompt(
                brief_content=brief_content,
                own_draft=claude_draft,
                other_draft=openai_draft,
                agent_name="claude",
                other_name="openai",
            )
            openai_prompt = negotiation_round1_prompt(
                brief_content=brief_content,
                own_draft=openai_draft,
                other_draft=claude_draft,
                agent_name="openai",
                other_name="claude",
            )
            validator = assert_well_formed_round1_turn
            # Spec 0030: per-piece token sizes — same shape for both agents
            # in round 1 (brief + d1 + d2, no history yet).
            round_pieces = pieces_for_negotiation_round1(
                brief=brief_content,
                claude_draft=claude_draft,
                openai_draft=openai_draft,
            )
        else:
            prior = list_turns(ctx.session, phase="phase2", up_to_round=r)
            claude_prompt = negotiation_turn_prompt(
                brief_content=brief_content,
                own_draft=claude_draft,
                other_draft=openai_draft,
                prior_turns=prior,
                agent_name="claude",
                other_name="openai",
                round=r,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
            )
            openai_prompt = negotiation_turn_prompt(
                brief_content=brief_content,
                own_draft=openai_draft,
                other_draft=claude_draft,
                prior_turns=prior,
                agent_name="openai",
                other_name="claude",
                round=r,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
            )
            validator = assert_well_formed_plan_turn
            # Spec 0030: rounds 2+ also carry the growing P2 history.
            round_pieces = pieces_for_negotiation_turn(
                brief=brief_content,
                claude_draft=claude_draft,
                openai_draft=openai_draft,
                prior_turns=prior,
            )

        claude_path = turn_path(ctx.session, phase="phase2", round=r, agent="claude")
        openai_path = turn_path(ctx.session, phase="phase2", round=r, agent="openai")

        claude_result, openai_result = await asyncio.gather(
            run_one_call(
                agent=claude_agent,
                prompt=claude_prompt,
                label=f"phase2-r{r}-claude",
                phase="phase2",
                metrics=ctx.metrics,
                transcript=ctx.transcript,
                event_bus=event_bus,
                stream_to=None,
                max_output_tokens=8192,
                prompt_pieces=round_pieces,
            ),
            run_one_call(
                agent=openai_agent,
                prompt=openai_prompt,
                label=f"phase2-r{r}-openai",
                phase="phase2",
                metrics=ctx.metrics,
                transcript=ctx.transcript,
                event_bus=event_bus,
                stream_to=None,
                max_output_tokens=8192,
                prompt_pieces=round_pieces,
            ),
        )
        write_atomic(claude_path, claude_result.text)
        write_atomic(openai_path, openai_result.text)

        try:
            claude_text, claude_parsed = await parse_with_repair(
                agent=claude_agent,
                text=claude_result.text,
                phase=2,
                round=r,
                validator=validator,
                tracker=tracker,
                session=ctx.session,
                session_phase="phase2",
                transcript=ctx.transcript,
                event_bus=event_bus,
                metrics=ctx.metrics,
                out_path=claude_path,
            )
            openai_text, openai_parsed = await parse_with_repair(
                agent=openai_agent,
                text=openai_result.text,
                phase=2,
                round=r,
                validator=validator,
                tracker=tracker,
                session=ctx.session,
                session_phase="phase2",
                transcript=ctx.transcript,
                event_bus=event_bus,
                metrics=ctx.metrics,
                out_path=openai_path,
            )
        except ProtocolParseError as pe:
            ctx.transcript.write(
                "protocol_parse_failure",
                agent=pe.agent,
                phase=2,
                round=r,
                errors=pe.errors,
            )
            parse_failure = True
            parse_failure_agent = pe.agent
            last_claude_text = claude_result.text
            last_openai_text = openai_result.text
            print(
                f"\n[phase 2] PROTOCOL PARSE FAILURE — agent={pe.agent} "
                f"errors={pe.errors}. Exit 52.",
                flush=True,
            )
            break

        last_claude_text = claude_text
        last_openai_text = openai_text

        # Convergence checks (round 1 cannot agree)
        agreed = False
        tiebreak_passes = False
        if r > 1:
            try:
                agreed = is_plan_agreed(claude_text, openai_text)
            except ProtocolParseError:
                agreed = False
            if not agreed:
                tb = all_substantive_gates_pass_except_drafter(claude_text, openai_text)
                tiebreak_passes = tb.passes

        await event_bus.publish(
            Phase2RoundComplete(
                round=r,
                agreed=agreed,
                claude_status=claude_parsed.status,
                openai_status=openai_parsed.status,
                claude_drafter=claude_parsed.drafter,
                openai_drafter=openai_parsed.drafter,
                claude_open_questions=claude_parsed.open_questions,
                openai_open_questions=openai_parsed.open_questions,
                claude_blocking=claude_parsed.blocking_disagreements,
                openai_blocking=openai_parsed.blocking_disagreements,
                claude_fsd=claude_parsed.final_surfaced_disagreements,
                openai_fsd=openai_parsed.final_surfaced_disagreements,
            )
        )
        ctx.transcript.write(
            "phase2_round_complete",
            round=r,
            agreed=agreed,
            claude_status=claude_parsed.status,
            openai_status=openai_parsed.status,
            claude_drafter=claude_parsed.drafter,
            openai_drafter=openai_parsed.drafter,
            claude_open_questions=claude_parsed.open_questions,
            openai_open_questions=openai_parsed.open_questions,
            claude_blocking=claude_parsed.blocking_disagreements,
            openai_blocking=openai_parsed.blocking_disagreements,
            claude_fsd=claude_parsed.final_surfaced_disagreements,
            openai_fsd=openai_parsed.final_surfaced_disagreements,
        )
        print(
            f"[phase 2] round {r}: claude {claude_parsed.status}/"
            f"oq={claude_parsed.open_questions or 0} "
            f"bd={claude_parsed.blocking_disagreements or 0}  "
            f"openai {openai_parsed.status}/"
            f"oq={openai_parsed.open_questions or 0} "
            f"bd={openai_parsed.blocking_disagreements or 0}  "
            f"agreed={agreed}",
            flush=True,
        )

        if agreed:
            ctx.state.drafter = claude_parsed.drafter
            ctx.state.agreed_plan = claude_parsed.agreed_plan
            fsd_items = extract_canonical_fsd_items(claude_parsed.agreed_plan)
            ctx.state.final_surfaced_disagreements = [asdict(i) for i in fsd_items]
            converged = True
            print(f"\n[phase 2] AGREED. Drafter = {ctx.state.drafter}.", flush=True)
            break

        if tiebreak_passes:
            tb = all_substantive_gates_pass_except_drafter(claude_text, openai_text)
            all_turns = list_turns(ctx.session, phase="phase2")
            claude_phase2 = [parse_turn(t.content) for t in all_turns if t.agent == "claude"]
            openai_phase2 = [parse_turn(t.content) for t in all_turns if t.agent == "openai"]
            choice = pick_drafter(
                claude_phase2_turns=claude_phase2,
                openai_phase2_turns=openai_phase2,
                phase1_drafts={"claude": claude_draft, "openai": openai_draft},
                agreed_plan_text=tb.agreed_plan,
                brief_content=brief_content,
            )
            ctx.state.drafter = choice.drafter
            ctx.state.agreed_plan = tb.agreed_plan
            fsd_items = extract_canonical_fsd_items(tb.agreed_plan)
            ctx.state.final_surfaced_disagreements = [asdict(i) for i in fsd_items]
            await event_bus.publish(
                DrafterTiebreakResolved(
                    round=r,
                    selected_drafter=choice.drafter,
                    reason=choice.reason,
                    claude_proposed=tb.claude_drafter,
                    openai_proposed=tb.openai_drafter,
                )
            )
            ctx.transcript.write(
                "drafter_tiebreak_resolved",
                round=r,
                selected_drafter=choice.drafter,
                reason=choice.reason,
                claude_proposed=tb.claude_drafter,
                openai_proposed=tb.openai_drafter,
            )
            converged = True
            via_tiebreak = True
            print(
                f"\n[phase 2] AGREED (orchestrator tiebreak). "
                f"Drafter = {ctx.state.drafter} via {choice.reason}.",
                flush=True,
            )
            break

        if r == soft_cap:
            await event_bus.publish(SoftCapHit(phase="phase2", round=r, cap=soft_cap))
            ctx.transcript.write("soft_cap_hit", phase="phase2", round=r, cap=soft_cap)
            print(
                f"\n[phase 2] soft cap ({soft_cap}) hit without agreement; "
                f"continuing to hard cap ({hard_cap}) (autonomous mode).",
                flush=True,
            )

        if r == hard_cap:
            await event_bus.publish(HardCapHit(phase="phase2", round=r, cap=hard_cap))
            ctx.transcript.write("hard_cap_hit", phase="phase2", round=r, cap=hard_cap)
            print(
                f"\n[phase 2] HARD CAP ({hard_cap}) hit without agreement. "
                f"Exit 51 (deadlock).",
                flush=True,
            )

    if converged:
        ctx.state.phase = "phase3"
        ctx.session.save_state(ctx.state)

    await event_bus.publish(
        Phase2Complete(
            rounds=rounds_done,
            converged=converged,
            drafter=ctx.state.drafter,
            fsd_count=len(ctx.state.final_surfaced_disagreements),
            via_tiebreak=via_tiebreak,
        )
    )
    ctx.transcript.write(
        "phase2_complete",
        rounds=rounds_done,
        converged=converged,
        drafter=ctx.state.drafter,
        fsd_count=len(ctx.state.final_surfaced_disagreements),
        via_tiebreak=via_tiebreak,
        parse_failure=parse_failure,
    )

    duration_ms = int((time.perf_counter() - started) * 1000)
    await event_bus.publish(PhaseExited(phase="phase2", duration_ms=duration_ms))
    ctx.transcript.write("phase_exited", phase="phase2", duration_ms=duration_ms)

    return Phase2Outcome(
        converged=converged,
        rounds=rounds_done,
        drafter=ctx.state.drafter,
        agreed_plan=ctx.state.agreed_plan,
        fsd_count=len(ctx.state.final_surfaced_disagreements),
        via_tiebreak=via_tiebreak,
        hard_capped=(not converged and not parse_failure and rounds_done == hard_cap),
        parse_failure=parse_failure,
        parse_failure_agent=parse_failure_agent,
        last_claude_text=last_claude_text,
        last_openai_text=last_openai_text,
    )
