from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from dual_research.agents.base import AgentCall
from dual_research.events import (
    EventBus,
    HardCapHit,
    Phase4Complete,
    Phase4DraftRevised,
    Phase4RoundComplete,
    PhaseEntered,
    PhaseExited,
    SoftCapHit,
)
from dual_research.orchestrator._call import run_one_call
from dual_research.orchestrator._turns import list_turns, turn_path
from dual_research.orchestrator.phase3 import current_draft_path
from dual_research.orchestrator.repair import RepairTracker, parse_with_repair
from dual_research.persistence import SessionContext
from dual_research.persistence.state import write_atomic
from dual_research.protocol import (
    ProtocolParseError,
    assert_well_formed_review_turn,
    extract_revised_draft_inclusive,
    is_review_approved,
    parse_turn,
    review_turn_prompt,
)
from dual_research.protocol.prompt_pieces import pieces_for_review
from dual_research.protocol.prompts import review_input_bundle


@dataclass(frozen=True)
class Phase4Outcome:
    approved: bool
    rounds: int
    final_draft_round: int
    revisions: int
    hard_capped: bool
    parse_failure: bool = False
    parse_failure_agent: str | None = None
    last_claude_text: str | None = None
    last_openai_text: str | None = None


async def run_phase4(
    *,
    ctx: SessionContext,
    claude_agent: AgentCall,
    openai_agent: AgentCall,
    event_bus: EventBus,
    brief_content: str,
    soft_cap: int,
    hard_cap: int,
) -> Phase4Outcome:
    phase_dir = ctx.session.phase_dir("phase4")
    await event_bus.publish(PhaseEntered(phase="phase4"))
    ctx.transcript.write("phase_entered", phase="phase4")
    started = time.perf_counter()

    drafter = ctx.state.drafter
    other = "openai" if drafter == "claude" else "claude"
    tracker = RepairTracker()
    revisions = 0
    rounds_done = 0
    approved = False
    parse_failure = False
    parse_failure_agent: str | None = None
    last_claude_text: str | None = None
    last_openai_text: str | None = None

    for r in range(1, hard_cap + 1):
        rounds_done = r

        # Spec 0036 — resume-aware skip. If both turn files for this
        # round already exist on disk (e.g. the run is being resumed
        # after Phase 4 round R completed), replay state without
        # re-issuing API calls or re-emitting events. The transcript
        # already carries the original TurnStarted/TurnEnded pair.
        claude_path = turn_path(ctx.session, phase="phase4", round=r, agent="claude")
        openai_path = turn_path(ctx.session, phase="phase4", round=r, agent="openai")
        if claude_path.is_file() and openai_path.is_file():
            print(
                f"\n[phase 4] round {r}/{hard_cap} — skipping (turn files exist on disk)",
                flush=True,
            )
            try:
                claude_text_existing = claude_path.read_text(encoding="utf-8")
                openai_text_existing = openai_path.read_text(encoding="utf-8")
            except OSError:
                # Fall through to the normal path if the read failed.
                pass
            else:
                last_claude_text = claude_text_existing
                last_openai_text = openai_text_existing

                # Detect revised draft from the drafter's existing turn.
                drafter_text = claude_text_existing if drafter == "claude" else openai_text_existing
                revised = extract_revised_draft_inclusive(drafter_text)
                if revised:
                    # If the revision file already exists on disk, just
                    # bump the state pointer. Otherwise write it now.
                    new_round = ctx.state.draft_round + 1
                    new_path = phase_dir / f"draft-v{new_round}.md"
                    if not new_path.is_file():
                        write_atomic(new_path, revised)
                    ctx.state.draft_round = new_round
                    ctx.session.save_state(ctx.state)
                    revisions += 1

                # Spec 0043 D7 — same ledger gate on resume-replay.
                from dual_research.ledger import (
                    build_phase_ledger as _build_pl_resume,
                    ledger_mode as _ledger_mode_resume,
                )
                ledger_open_resume = None
                if _ledger_mode_resume() != "legacy":
                    _l_resume = _build_pl_resume(ctx.session.root, phase=4)
                    ledger_open_resume = _l_resume.open_count(kind="issue")
                try:
                    approved = is_review_approved(
                        claude_text_existing, openai_text_existing,
                        round=r,
                        ledger_open_count=ledger_open_resume,
                    )
                except ProtocolParseError:
                    approved = False

                if approved:
                    print(
                        f"[phase 4] round {r}: replayed as APPROVED (resume).",
                        flush=True,
                    )
                    break
                continue

        current_draft = current_draft_path(ctx.session, ctx.state.draft_round).read_text(encoding="utf-8")
        prior = list_turns(ctx.session, phase="phase4", up_to_round=r)
        print(f"\n[phase 4] round {r}/{hard_cap}  (current draft = v{ctx.state.draft_round})\n", flush=True)

        # Spec 0043 D6 — standing items input for R≥2 review turns.
        from dual_research.ledger import (
            build_phase_ledger as _build_pl,
            build_standing_items_section as _build_si,
            ledger_mode as _ledger_mode,
        )
        if r > 1 and _ledger_mode() != "legacy":
            _ledger = _build_pl(ctx.session.root, phase=4)
            claude_standing = _build_si(_ledger, perspective="claude")
            openai_standing = _build_si(_ledger, perspective="gpt")
        else:
            claude_standing = ""
            openai_standing = ""

        claude_prompt = review_turn_prompt(
            brief_content=brief_content,
            draft_content=current_draft,
            prior_turns=prior,
            agent_name="claude",
            other_name="openai",
            drafter_name=drafter,
            round=r,
            soft_cap=soft_cap,
            hard_cap=hard_cap,
            standing_items=claude_standing,
        )
        openai_prompt = review_turn_prompt(
            brief_content=brief_content,
            draft_content=current_draft,
            prior_turns=prior,
            agent_name="openai",
            other_name="claude",
            drafter_name=drafter,
            round=r,
            soft_cap=soft_cap,
            hard_cap=hard_cap,
            standing_items=openai_standing,
        )
        # Spec 0030: per-piece sizes for the Consumption tab. Both agents
        # share the same input shape this round (same brief + same draft
        # + same prior P4 turns).
        round_pieces = pieces_for_review(
            brief=brief_content,
            draft=current_draft,
            prior_turns=prior,
        )
        # Spec 0033: per-piece TEXT bundles (per-agent system templates).
        claude_bundle = review_input_bundle(
            brief=brief_content,
            draft=current_draft,
            prior_turns=prior,
            agent_name="claude",
            other_name="openai",
            drafter_name=drafter,
            round=r,
            soft_cap=soft_cap,
            hard_cap=hard_cap,
        )
        openai_bundle = review_input_bundle(
            brief=brief_content,
            draft=current_draft,
            prior_turns=prior,
            agent_name="openai",
            other_name="claude",
            drafter_name=drafter,
            round=r,
            soft_cap=soft_cap,
            hard_cap=hard_cap,
        )

        # `claude_path` / `openai_path` already bound above for the resume check.

        claude_result, openai_result = await asyncio.gather(
            run_one_call(
                agent=claude_agent,
                prompt=claude_prompt,
                label=f"phase4-r{r}-claude",
                phase="phase4",
                metrics=ctx.metrics,
                transcript=ctx.transcript,
                event_bus=event_bus,
                stream_to=None,
                max_output_tokens=16384,
                prompt_pieces=round_pieces,
                prompt_bundle=claude_bundle,
            ),
            run_one_call(
                agent=openai_agent,
                prompt=openai_prompt,
                label=f"phase4-r{r}-openai",
                phase="phase4",
                metrics=ctx.metrics,
                transcript=ctx.transcript,
                event_bus=event_bus,
                stream_to=None,
                max_output_tokens=16384,
                prompt_pieces=round_pieces,
                prompt_bundle=openai_bundle,
            ),
        )
        write_atomic(claude_path, claude_result.text)
        write_atomic(openai_path, openai_result.text)

        validator = lambda p, a: assert_well_formed_review_turn(p, a, round=r)
        try:
            claude_text, claude_parsed = await parse_with_repair(
                agent=claude_agent,
                text=claude_result.text,
                phase=4,
                round=r,
                validator=validator,
                tracker=tracker,
                session=ctx.session,
                session_phase="phase4",
                transcript=ctx.transcript,
                event_bus=event_bus,
                metrics=ctx.metrics,
                out_path=claude_path,
            )
            openai_text, openai_parsed = await parse_with_repair(
                agent=openai_agent,
                text=openai_result.text,
                phase=4,
                round=r,
                validator=validator,
                tracker=tracker,
                session=ctx.session,
                session_phase="phase4",
                transcript=ctx.transcript,
                event_bus=event_bus,
                metrics=ctx.metrics,
                out_path=openai_path,
            )
        except ProtocolParseError as pe:
            ctx.transcript.write(
                "protocol_parse_failure",
                agent=pe.agent,
                phase=4,
                round=r,
                errors=pe.errors,
            )
            parse_failure = True
            parse_failure_agent = pe.agent
            last_claude_text = claude_result.text
            last_openai_text = openai_result.text
            print(
                f"\n[phase 4] PROTOCOL PARSE FAILURE — agent={pe.agent} errors={pe.errors}. Exit 52.",
                flush=True,
            )
            break

        last_claude_text = claude_text
        last_openai_text = openai_text

        # Detect revised draft from the DRAFTER's turn
        drafter_text = claude_text if drafter == "claude" else openai_text
        revised = extract_revised_draft_inclusive(drafter_text)
        if revised:
            new_round = ctx.state.draft_round + 1
            new_path = phase_dir / f"draft-v{new_round}.md"
            write_atomic(new_path, revised)
            ctx.state.draft_round = new_round
            ctx.session.save_state(ctx.state)
            revisions += 1
            await event_bus.publish(
                Phase4DraftRevised(
                    round=r, new_draft_round=new_round, new_draft_chars=len(revised)
                )
            )
            ctx.transcript.write(
                "phase4_draft_revised",
                round=r,
                new_draft_round=new_round,
                new_draft_chars=len(revised),
                path=str(new_path),
            )
            print(f"[phase 4] {drafter} revised: draft v{new_round} ({len(revised):,} chars)", flush=True)

        # Spec 0043 D7 — ledger cross-check on Phase 4 termination.
        from dual_research.ledger import (
            build_phase_ledger as _build_pl_p4,
            ledger_mode as _ledger_mode_p4,
        )
        ledger_open_p4 = None
        if _ledger_mode_p4() != "legacy":
            _l4 = _build_pl_p4(ctx.session.root, phase=4)
            # Phase 4 termination gates on issues (open issues block
            # approval); comments are non-blocking; disagreements
            # are surface-only at this point.
            ledger_open_p4 = _l4.open_count(kind="issue")
        try:
            approved = is_review_approved(
                claude_text, openai_text,
                round=r,
                ledger_open_count=ledger_open_p4,
            )
        except ProtocolParseError:
            approved = False

        await event_bus.publish(
            Phase4RoundComplete(
                round=r,
                approved=approved,
                claude_status=claude_parsed.status,
                openai_status=openai_parsed.status,
                claude_open_issues=claude_parsed.open_issues,
                openai_open_issues=openai_parsed.open_issues,
                draft_round=ctx.state.draft_round,
            )
        )
        ctx.transcript.write(
            "phase4_round_complete",
            round=r,
            approved=approved,
            claude_status=claude_parsed.status,
            openai_status=openai_parsed.status,
            claude_open_issues=claude_parsed.open_issues,
            openai_open_issues=openai_parsed.open_issues,
            draft_round=ctx.state.draft_round,
        )
        print(
            f"[phase 4] round {r}: claude {claude_parsed.status}/oi={claude_parsed.open_issues or 0}  "
            f"openai {openai_parsed.status}/oi={openai_parsed.open_issues or 0}  "
            f"approved={approved}  draft=v{ctx.state.draft_round}",
            flush=True,
        )

        if approved:
            print("\n[phase 4] APPROVED. ", flush=True)
            break

        if r == soft_cap:
            await event_bus.publish(SoftCapHit(phase="phase4", round=r, cap=soft_cap))
            ctx.transcript.write("soft_cap_hit", phase="phase4", round=r, cap=soft_cap)
            print(
                f"\n[phase 4] soft cap ({soft_cap}) hit; continuing to hard cap ({hard_cap}) (autonomous).",
                flush=True,
            )

        if r == hard_cap:
            await event_bus.publish(HardCapHit(phase="phase4", round=r, cap=hard_cap))
            ctx.transcript.write("hard_cap_hit", phase="phase4", round=r, cap=hard_cap)
            print(f"\n[phase 4] HARD CAP ({hard_cap}) hit without approval. Exit 51.", flush=True)

    if approved:
        ctx.state.phase = "done"
        ctx.session.save_state(ctx.state)

    await event_bus.publish(
        Phase4Complete(
            rounds=rounds_done,
            approved=approved,
            final_draft_round=ctx.state.draft_round,
            revisions=revisions,
        )
    )
    ctx.transcript.write(
        "phase4_complete",
        rounds=rounds_done,
        approved=approved,
        final_draft_round=ctx.state.draft_round,
        revisions=revisions,
        parse_failure=parse_failure,
    )

    duration_ms = int((time.perf_counter() - started) * 1000)
    await event_bus.publish(PhaseExited(phase="phase4", duration_ms=duration_ms))
    ctx.transcript.write("phase_exited", phase="phase4", duration_ms=duration_ms)

    return Phase4Outcome(
        approved=approved,
        rounds=rounds_done,
        final_draft_round=ctx.state.draft_round,
        revisions=revisions,
        hard_capped=(not approved and not parse_failure and rounds_done == hard_cap),
        parse_failure=parse_failure,
        parse_failure_agent=parse_failure_agent,
        last_claude_text=last_claude_text,
        last_openai_text=last_openai_text,
    )
