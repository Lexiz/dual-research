from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, dataclass

from dual_research.agents.base import AgentCall
from dual_research.events import (
    CanonicalFsdSynthesized,
    DrafterCanonicalPromoted,
    DrafterTiebreakResolved,
    EventBus,
    HardCapHit,
    Phase2Complete,
    Phase2RoundComplete,
    PhaseEntered,
    PhaseExited,
    SoftCapHit,
    StuckAgreedPromoted,
)
from dual_research.orchestrator._call import run_one_call
from dual_research.orchestrator._turns import list_turns, turn_path
from dual_research.orchestrator.repair import RepairTracker, parse_with_repair
from dual_research.persistence import SessionContext
from dual_research.persistence.state import write_atomic
from dual_research.protocol import (
    ProtocolParseError,
    all_substantive_gates_pass_except_drafter,
    all_substantive_gates_pass_except_plan_hash,
    assert_well_formed_plan_turn,
    assert_well_formed_round1_turn,
    extract_canonical_fsd_items,
    force_verbatim_copy_prompt,
    is_plan_agreed,
    negotiation_round1_prompt,
    negotiation_turn_prompt,
    parse_turn,
    pick_drafter,
)
# Spec 0089 — new convergence escapes.
from dual_research.protocol.convergence import (
    all_substantive_gates_pass_except_canonical_fsd,
    compose_full_agreed_plan,
    is_plan_agreed_lenient,
    splice_canonical_into_agreed_plan,
)


# Spec 0089 § B — number of consecutive lenient-True / strict-False rounds
# before the stuck-AGREED escape valve fires. K=2 gives the strengthened
# § C standing-items prompt one round of nudging before the orchestrator
# accepts agent judgment over the ledger cross-check.
STUCK_AGREED_K = 2
from dual_research.protocol.prompt_pieces import (
    pieces_for_negotiation_round1,
    pieces_for_negotiation_turn,
)
from dual_research.protocol.prompts import (
    force_verbatim_copy_input_bundle,
    negotiation_round1_input_bundle,
    negotiation_turn_input_bundle,
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
    via_canonical_promotion = False
    # Spec 0089 § A — set when the canonical-FSD synthesis escape fired.
    via_canonical_fsd_synthesis = False
    # Spec 0089 § B — set when the stuck-AGREED escape valve fired.
    via_stuck_agreed = False
    rounds_done = 0
    last_claude_text: str | None = None
    last_openai_text: str | None = None
    parse_failure = False
    parse_failure_agent: str | None = None
    # Spec 0032 — track how many times we've fired a force-verbatim-copy
    # repair turn for each agent. First detection of hash drift fires a
    # repair turn (counter goes to 1); if drift recurs and the counter is
    # already ≥ 1, we escape via canonical promotion. Per-agent because
    # only one side ever needs repairing (the non-drafter).
    hash_drift_repair_attempts: dict[str, int] = {"claude": 0, "gpt": 0}
    # Spec 0089 § B — consecutive rounds where agents are fully aligned
    # on the protocol surface (lenient check passes) but the strict
    # ledger-cross-check rejects. After STUCK_AGREED_K such rounds in
    # a row, accept the lenient convergence.
    stuck_agreed_streak: int = 0
    # Spec 0089 § C — track whether the prior round was blocked by the
    # ledger cross-check, so the next round's prompt carries the
    # high-salience warning section explaining what's happening.
    prior_round_blocked_ledger_open: int = 0
    prior_round_blocked: bool = False

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
            # Spec 0033: per-piece TEXT — per-agent system templates.
            claude_bundle = negotiation_round1_input_bundle(
                brief=brief_content,
                claude_draft=claude_draft,
                openai_draft=openai_draft,
                agent_name="claude",
                other_name="openai",
            )
            openai_bundle = negotiation_round1_input_bundle(
                brief=brief_content,
                claude_draft=claude_draft,
                openai_draft=openai_draft,
                agent_name="openai",
                other_name="claude",
            )
        else:
            prior = list_turns(ctx.session, phase="phase2", up_to_round=r)
            # Spec 0043 D6 — build the per-agent standing-items section
            # from the cross-round ledger, derived from the existing
            # parsed sections. Empty string when DR_LEDGER_MODE=legacy,
            # OR when no items are open. Each agent sees a perspective-
            # specific view (items raised by the other surface first).
            from dual_research.ledger import (
                build_blocked_convergence_warning,
                build_phase_ledger,
                build_standing_items_section,
                ledger_mode,
            )
            if ledger_mode() == "legacy":
                claude_standing = ""
                openai_standing = ""
            else:
                _ledger = build_phase_ledger(ctx.session.root, phase=2)
                claude_standing = build_standing_items_section(_ledger, perspective="claude")
                openai_standing = build_standing_items_section(_ledger, perspective="gpt")
            # Spec 0089 § C — when the prior round emitted AGREED but the
            # ledger blocked, surface a high-salience warning section so
            # the agents understand what's actually gating them.
            blocked_warning = build_blocked_convergence_warning(
                prior_round_was_blocked=prior_round_blocked,
                ledger_open_count=prior_round_blocked_ledger_open,
                prior_round_number=r - 1,
            )
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
                standing_items=claude_standing,
                blocked_warning=blocked_warning,
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
                standing_items=openai_standing,
                blocked_warning=blocked_warning,
            )
            validator = assert_well_formed_plan_turn
            # Spec 0030: rounds 2+ also carry the growing P2 history.
            round_pieces = pieces_for_negotiation_turn(
                brief=brief_content,
                claude_draft=claude_draft,
                openai_draft=openai_draft,
                prior_turns=prior,
            )
            # Spec 0033: per-piece TEXT bundles (per-agent system templates).
            claude_bundle = negotiation_turn_input_bundle(
                brief=brief_content,
                claude_draft=claude_draft,
                openai_draft=openai_draft,
                prior_turns=prior,
                agent_name="claude",
                other_name="openai",
                round=r,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
            )
            openai_bundle = negotiation_turn_input_bundle(
                brief=brief_content,
                claude_draft=claude_draft,
                openai_draft=openai_draft,
                prior_turns=prior,
                agent_name="openai",
                other_name="claude",
                round=r,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
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
                prompt_bundle=claude_bundle,
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
                prompt_bundle=openai_bundle,
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
        # Spec 0089 § B — lenient check (no ledger gate). True when agents
        # are fully aligned on the protocol surface; orchestrator tracks
        # streak of lenient-True / strict-False rounds and escapes via
        # stuck-AGREED promotion after STUCK_AGREED_K consecutive rounds.
        lenient_agreed = False
        ledger_open = None
        if r > 1:
            # Spec 0043 D7 — ledger cross-check: build the ledger from
            # the just-written turn files and pass the open count to
            # is_plan_agreed. When DR_LEDGER_MODE=legacy, skip the
            # check entirely (pass None).
            from dual_research.ledger import build_phase_ledger as _build_pl
            from dual_research.ledger import ledger_mode as _ledger_mode
            if _ledger_mode() != "legacy":
                _ledger = _build_pl(ctx.session.root, phase=2)
                # Phase 2 convergence considers questions + held disagreements
                # + claims (claims that haven't escalated yet remain "open"
                # contested points the agents haven't moved on).
                ledger_open = (
                    _ledger.open_count(kind="question")
                    + _ledger.open_count(kind="disagreement")
                    + _ledger.open_count(kind="claim")
                )
            try:
                agreed = is_plan_agreed(
                    claude_text, openai_text,
                    ledger_open_count=ledger_open,
                )
            except ProtocolParseError:
                agreed = False
            if not agreed:
                tb = all_substantive_gates_pass_except_drafter(claude_text, openai_text)
                tiebreak_passes = tb.passes
                # Spec 0089 § B — track lenient agreement.
                try:
                    lenient_agreed = is_plan_agreed_lenient(claude_text, openai_text)
                except ProtocolParseError:
                    lenient_agreed = False

        # Spec 0089 § B — update the stuck-AGREED streak counter.
        if lenient_agreed and not agreed:
            stuck_agreed_streak += 1
        else:
            stuck_agreed_streak = 0
        # Spec 0089 § C — propagate the blocked-warning state into the
        # NEXT round's prompt. "Blocked" means agents emitted aligned
        # AGREED but the ledger cross-check rejected.
        prior_round_blocked = lenient_agreed and not agreed
        prior_round_blocked_ledger_open = ledger_open or 0

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
            # Spec 0089 — splice the top-level canonical FSD sub-section
            # back into the plan so Phase 3 + extract_canonical_fsd_items
            # see a self-contained plan+canonical block.
            ctx.state.agreed_plan = compose_full_agreed_plan(
                claude_text, claude_parsed.agreed_plan
            )
            fsd_items = extract_canonical_fsd_items(ctx.state.agreed_plan)
            ctx.state.final_surfaced_disagreements = [asdict(i) for i in fsd_items]
            converged = True
            print(f"\n[phase 2] AGREED. Drafter = {ctx.state.drafter}.", flush=True)
            break

        # ─── Spec 0089 § A — canonical-FSD synthesis escape ─────────────
        # Fires when every substantive gate passes AND plan hashes match
        # AND standalone FSD IDs match across agents, but the canonical
        # ## Final-surfaced disagreements (canonical) sub-section is
        # missing from the AGREED_PLAN. The orchestrator synthesises the
        # sub-section deterministically from the drafter's standalone
        # section (a strict superset of the canonical fields), splices
        # it into the drafter's plan, and exits converged. No repair
        # turn fired; this is pure on-disk transformation.
        if r > 1:
            fsd_gap = all_substantive_gates_pass_except_canonical_fsd(
                claude_text, openai_text
            )
            if fsd_gap.detected:
                new_plan = splice_canonical_into_agreed_plan(
                    fsd_gap.canonical_plan or "",
                    fsd_gap.synthesized_section or "",
                )
                ctx.state.drafter = fsd_gap.drafter
                ctx.state.agreed_plan = new_plan
                fsd_items = extract_canonical_fsd_items(new_plan)
                ctx.state.final_surfaced_disagreements = [asdict(i) for i in fsd_items]
                converged = True
                via_canonical_fsd_synthesis = True
                await event_bus.publish(
                    CanonicalFsdSynthesized(
                        round=r,
                        drafter=fsd_gap.drafter or "",
                        fsd_ids=list(fsd_gap.fsd_ids),
                    )
                )
                ctx.transcript.write(
                    "canonical_fsd_synthesized",
                    round=r,
                    drafter=fsd_gap.drafter,
                    fsd_ids=list(fsd_gap.fsd_ids),
                )
                print(
                    f"\n[phase 2] AGREED (canonical-FSD synthesis). "
                    f"Drafter = {fsd_gap.drafter}. "
                    f"Synthesised canonical sub-section for FSDs: "
                    f"{', '.join(fsd_gap.fsd_ids)}.",
                    flush=True,
                )
                break

        # ─── Spec 0089 § B — stuck-AGREED escape valve ─────────────────
        # Fires when agents have emitted substantively-equivalent AGREED
        # for STUCK_AGREED_K consecutive rounds while only the ledger
        # cross-check (or some other secondary gate) was blocking. After
        # two such rounds the agents have demonstrated alignment beyond
        # any reasonable doubt; the orchestrator accepts their judgment.
        if (
            lenient_agreed
            and not agreed
            and stuck_agreed_streak >= STUCK_AGREED_K
        ):
            ctx.state.drafter = claude_parsed.drafter
            # Spec 0089 — same compose dance as the normal success branch.
            ctx.state.agreed_plan = compose_full_agreed_plan(
                claude_text, claude_parsed.agreed_plan
            )
            fsd_items = extract_canonical_fsd_items(ctx.state.agreed_plan)
            ctx.state.final_surfaced_disagreements = [asdict(i) for i in fsd_items]
            converged = True
            via_stuck_agreed = True
            await event_bus.publish(
                StuckAgreedPromoted(
                    phase=2,
                    round=r,
                    streak=stuck_agreed_streak,
                    ledger_open_count=ledger_open or 0,
                )
            )
            ctx.transcript.write(
                "stuck_agreed_promoted",
                phase=2,
                round=r,
                streak=stuck_agreed_streak,
                ledger_open_count=ledger_open or 0,
            )
            print(
                f"\n[phase 2] AGREED (stuck-AGREED escape valve). "
                f"Drafter = {ctx.state.drafter}. Agents stayed aligned "
                f"for {stuck_agreed_streak} consecutive rounds while "
                f"the ledger reported {ledger_open or 0} open items; "
                f"accepting agent judgment.",
                flush=True,
            )
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

        # ─── Spec 0032 — Phase 2 hash-drift escape ─────────────────────
        # When both agents emit STATUS: AGREED with matching drafter / OQ
        # / BD / FSD but their AGREED_PLAN hashes differ, the model is
        # paraphrasing instead of copying verbatim. The protocol prompt
        # acknowledges this case explicitly. First detection: fire a
        # force-verbatim repair turn for the non-drafter and re-check.
        # If it still drifts, canonical-promote the drafter's plan and
        # exit Phase 2 — agents agreed on substance, we shouldn't
        # deadlock on wording.
        if r > 1:
            drift = all_substantive_gates_pass_except_plan_hash(claude_text, openai_text)
            if drift.detected:
                other = drift.other_agent  # "claude" | "gpt"

                def _promote_canonical() -> None:
                    """Promote drift.drafter's plan as canonical and converge."""
                    nonlocal converged, via_canonical_promotion
                    ctx.state.drafter = drift.drafter
                    ctx.state.agreed_plan = drift.canonical_plan
                    fsd_items = extract_canonical_fsd_items(drift.canonical_plan)
                    ctx.state.final_surfaced_disagreements = [
                        asdict(i) for i in fsd_items
                    ]
                    converged = True
                    via_canonical_promotion = True

                if hash_drift_repair_attempts.get(other, 0) >= 1:
                    # D3 — second detection: auto-promote.
                    _promote_canonical()
                    await event_bus.publish(
                        DrafterCanonicalPromoted(
                            round=r,
                            drafter=drift.drafter,
                            other_agent=other,
                            canonical_hash=(drift.canonical_hash or "")[:12],
                            other_hash=(drift.other_hash or "")[:12],
                        )
                    )
                    ctx.transcript.write(
                        "drafter_canonical_promoted",
                        round=r,
                        drafter=drift.drafter,
                        other_agent=other,
                        canonical_hash=(drift.canonical_hash or "")[:12],
                        other_hash=(drift.other_hash or "")[:12],
                    )
                    print(
                        f"\n[phase 2] AGREED (canonical promotion). "
                        f"Drafter = {drift.drafter}. "
                        f"{other}'s plan kept drifting across two rounds; "
                        f"using drafter's plan as canonical.",
                        flush=True,
                    )
                    break

                # D2 — first detection: fire a force-verbatim-copy repair
                # turn for the non-drafter and re-check convergence
                # within this round.
                hash_drift_repair_attempts[other] = (
                    hash_drift_repair_attempts.get(other, 0) + 1
                )
                # Map the UI-vocab "gpt" agent back to its backend objects.
                if other == "gpt":
                    repair_agent_call = openai_agent
                    repair_other_path = openai_path
                    repair_agent_name = "openai"
                    repair_other_name = "claude"
                else:
                    repair_agent_call = claude_agent
                    repair_other_path = claude_path
                    repair_agent_name = "claude"
                    repair_other_name = "openai"

                print(
                    f"\n[phase 2] hash drift detected on round {r}: "
                    f"both AGREED but plan hashes differ "
                    f"(canonical={(drift.canonical_hash or '')[:8]} "
                    f"other={(drift.other_hash or '')[:8]}). "
                    f"Firing force-verbatim repair for {other}.",
                    flush=True,
                )
                ctx.transcript.write(
                    "phase2_hash_drift_detected",
                    round=r,
                    drafter=drift.drafter,
                    other_agent=other,
                    canonical_hash=(drift.canonical_hash or "")[:12],
                    other_hash=(drift.other_hash or "")[:12],
                )

                repair_text = force_verbatim_copy_prompt(
                    agent_name=repair_agent_name,
                    other_name=repair_other_name,
                    drafter_name=drift.drafter,
                    canonical_plan=drift.canonical_plan or "",
                    round=r,
                )
                # Spec 0033: per-piece TEXT bundle for the repair turn.
                repair_bundle = force_verbatim_copy_input_bundle(
                    agent_name=repair_agent_name,
                    other_name=repair_other_name,
                    drafter_name=drift.drafter,
                    canonical_plan=drift.canonical_plan or "",
                    round=r,
                )
                try:
                    # Spec 0036: match REPAIR_MAX_OUTPUT_TOKENS — the
                    # hash-drift repair replays the canonical plan + the
                    # response, which often exceeds 8192.
                    from dual_research.orchestrator.repair import REPAIR_MAX_OUTPUT_TOKENS
                    repair_result = await run_one_call(
                        agent=repair_agent_call,
                        prompt=repair_text,
                        label=f"phase2-r{r}-{other}-hashdrift-repair",
                        phase="phase2",
                        metrics=ctx.metrics,
                        transcript=ctx.transcript,
                        event_bus=event_bus,
                        stream_to=None,
                        max_output_tokens=REPAIR_MAX_OUTPUT_TOKENS,
                        prompt_bundle=repair_bundle,
                    )
                    write_atomic(repair_other_path, repair_result.text)
                    # Re-evaluate convergence with the repaired turn.
                    if other == "gpt":
                        openai_text = repair_result.text
                    else:
                        claude_text = repair_result.text
                    try:
                        # Spec 0043 — reuse the same conservative
                        # ledger check post-repair.
                        from dual_research.ledger import (
                            build_phase_ledger as _build_pl2,
                            ledger_mode as _ledger_mode2,
                        )
                        ledger_open_post = None
                        if _ledger_mode2() != "legacy":
                            _l = _build_pl2(ctx.session.root, phase=2)
                            ledger_open_post = (
                                _l.open_count(kind="question")
                                + _l.open_count(kind="disagreement")
                                + _l.open_count(kind="claim")
                            )
                        agreed_after_repair = is_plan_agreed(
                            claude_text, openai_text,
                            ledger_open_count=ledger_open_post,
                        )
                    except ProtocolParseError:
                        agreed_after_repair = False
                except Exception as e:  # network error, agent error, etc.
                    print(
                        f"[phase 2] force-verbatim repair call failed: {e}. "
                        f"Falling through to next round.",
                        flush=True,
                    )
                    agreed_after_repair = False

                if agreed_after_repair:
                    # Repair worked — canonicalise as usual.
                    ctx.state.drafter = drift.drafter
                    ctx.state.agreed_plan = drift.canonical_plan
                    fsd_items = extract_canonical_fsd_items(drift.canonical_plan)
                    ctx.state.final_surfaced_disagreements = [
                        asdict(i) for i in fsd_items
                    ]
                    converged = True
                    print(
                        f"\n[phase 2] AGREED (after force-verbatim repair). "
                        f"Drafter = {drift.drafter}.",
                        flush=True,
                    )
                    break

                # Repair didn't fix it — escape via canonical promotion.
                still_drift = all_substantive_gates_pass_except_plan_hash(
                    claude_text, openai_text
                )
                if still_drift.detected:
                    _promote_canonical()
                    await event_bus.publish(
                        DrafterCanonicalPromoted(
                            round=r,
                            drafter=drift.drafter,
                            other_agent=other,
                            canonical_hash=(drift.canonical_hash or "")[:12],
                            other_hash=(still_drift.other_hash or "")[:12],
                        )
                    )
                    ctx.transcript.write(
                        "drafter_canonical_promoted",
                        round=r,
                        drafter=drift.drafter,
                        other_agent=other,
                        canonical_hash=(drift.canonical_hash or "")[:12],
                        other_hash=(still_drift.other_hash or "")[:12],
                    )
                    print(
                        f"\n[phase 2] AGREED (canonical promotion). "
                        f"Repair turn still drifted; using drafter's plan.",
                        flush=True,
                    )
                    break
                # else: repair output is unparseable or substantively
                # different — fall through to the next round and let the
                # normal negotiation continue.

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
            via_canonical_promotion=via_canonical_promotion,
            via_canonical_fsd_synthesis=via_canonical_fsd_synthesis,
            via_stuck_agreed=via_stuck_agreed,
        )
    )
    ctx.transcript.write(
        "phase2_complete",
        rounds=rounds_done,
        converged=converged,
        drafter=ctx.state.drafter,
        fsd_count=len(ctx.state.final_surfaced_disagreements),
        via_tiebreak=via_tiebreak,
        via_canonical_promotion=via_canonical_promotion,
        via_canonical_fsd_synthesis=via_canonical_fsd_synthesis,
        via_stuck_agreed=via_stuck_agreed,
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
