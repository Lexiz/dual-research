"""Spec 0114 — Deep Research async phase runners (production wiring).

The legacy ``orchestrator/phase{0..4}.py`` files are preserved for
their dedicated tests, but ``run.py`` now imports from this module.
Each ``run_dr_phase{0..4}`` coroutine is a drop-in replacement for the
legacy ``run_phase{0..4}`` coroutine and produces the same
``Phase{N}Outcome`` shape so ``finalize.py`` and ``run.py`` continue
to work without modification at the outcome-consumer level.

The interaction-phase runners (0, 2, 4) wrap a ``DeepResearchPhase``
instance, drive it round-by-round, and publish both new
(``ItemRaised`` / ``ItemTransitioned`` / ``CloseoutUrged`` /
``PhaseConverged``) and legacy (``Phase{N}RoundComplete`` /
``Phase{N}Complete``) events. The legacy events are populated by
``events.legacy_shim`` from the ledger snapshot so the existing UI
continues to render correctly.

Phase 1 and phase 3 are the production phases — they use the new
``research_plan_prompt_v2`` / ``drafting_prompt_v2`` functions with
structured carry-forward inputs read from ``SessionState``.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from dual_research.agents.base import AgentCall
from dual_research.contract.artifacts import canonical_hash, hash_draft_content
from dual_research.contract.caps import caps_for
from dual_research.contract.categories import Category
from dual_research.contract.evidence import validate_all_evidence
from dual_research.contract.lifecycle import State, is_terminal
from dual_research.events import (
    ArtifactCanonicallyPromoted,
    EventBus,
    HardCapHit,
    ItemRaised,
    ItemTransitioned,
    Phase0Complete,
    Phase0RoundComplete,
    Phase1Complete,
    Phase2Complete,
    Phase2RoundComplete,
    Phase3Complete,
    Phase4Complete,
    Phase4DraftRevised,
    Phase4RoundComplete,
    PhaseEntered,
    PhaseExited,
    SoftCapHit,
)
from dual_research.orchestrator.closeout import items_blocking_convergence
# Spec 0115 — legacy_shim removed; the new event stream is the only
# source of per-category data. Round-complete events emit as marker
# events with no counter payload.
from dual_research.orchestrator._call import _derive_turn_key, run_one_call
from dual_research.orchestrator._turns import (
    list_turns,
    next_malformed_n,
    turn_filename,
)
from dual_research.orchestrator.deep_research import (
    AgentTurnRequest,
    DeepResearchPhase,
    LedgerEntryV2,
    PhaseRunResult,
)
from dual_research.orchestrator.phase0 import Phase0Outcome
from dual_research.orchestrator.phase1 import Phase1Outcome
from dual_research.orchestrator.phase2 import Phase2Outcome
from dual_research.orchestrator.phase3 import Phase3Outcome, current_draft_path
from dual_research.orchestrator.phase4 import Phase4Outcome
from dual_research.persistence import SessionContext
from dual_research.persistence.state import write_atomic
from dual_research.protocol import (
    PriorTurn,
    extract_agreed_draft_acceptance,
    extract_agreed_interpretation_body,
    extract_agreed_plan_body,
    extract_drafter_from_agreed_plan,
    extract_revised_draft_inclusive,
    parse_turn_v2,
)
from dual_research.protocol.prompt_pieces import Attachment
from dual_research.protocol.prompts import (
    closeout_request_section,
    drafting_prompt_v2,
    input_negotiation_prompt_v2,
    plan_negotiation_round1_prompt_v2,
    plan_negotiation_round_n_prompt_v2,
    preflight_prompt_v2,
    research_plan_prompt_v2,
    review_round1_prompt_v2,
    review_round_n_prompt_v2,
)


_TURN_MAX_OUTPUT_TOKENS = 8192
_DRAFT_MAX_OUTPUT_TOKENS = 16384


# ─── Helpers ──────────────────────────────────────────────────────────


def _carry_forward_payload(ledger: Iterable[LedgerEntryV2]) -> list[dict]:
    """Build the JSON-serializable carry-forward list stored on SessionState.

    Items with terminal-not-resolved state become the carry-forward
    candidates. The shim's snapshot is the same shape the finalize step
    consumes.
    """
    out: list[dict] = []
    for e in ledger:
        if not is_terminal(e.current_state):
            continue
        if e.current_state == State.RESOLVED:
            continue
        out.append({
            "id": e.id,
            "kind": e.kind.value,
            "raiser": e.raiser,
            "current_state": e.current_state.value,
            "body": e.body,
            "raised_round": e.raised_round,
            "transitions": list(e.transitions),
        })
    return out


def _evidence_validator_for_run(recs, parsed, agent, audit_tool_events):
    """Spec 0144 §6.1.b — production evidence validator.

    Wraps ``contract.evidence.validate_all_evidence`` with the per-turn
    ``tool_events`` list supplied by the orchestrator at apply_turn
    time. The signature matches the 4-arg slot on
    ``DeepResearchPhase``. Called only when at least one ADDRESS block
    targets an evidence-required item.
    """
    if not recs:
        return []
    return validate_all_evidence(list(recs), tool_events=list(audit_tool_events or []))


def _read_turn_audit_tool_events(session_dir: Path, turn_key: str) -> list[dict]:
    """Read ``session_dir/searches/<turn_key>.json`` and return tool_events.

    Returns an empty list when the audit file is absent / unreadable /
    malformed so the validator defers (no flag fires) rather than
    rejecting a real evidence record because of an I/O glitch.
    """
    if not turn_key:
        return []
    path = session_dir / "searches" / f"{turn_key}.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    tool_events = data.get("tool_events") or []
    return [te for te in tool_events if isinstance(te, dict)]


def _build_dr_phase(
    phase: int,
    *,
    artifact_hash_match=None,
) -> DeepResearchPhase:
    return DeepResearchPhase(
        phase=phase,
        agent_turn=lambda req: "",  # never used in async path
        artifact_hash_match=artifact_hash_match,
        evidence_validator=_evidence_validator_for_run,
    )


async def _publish_round_events(
    bus: EventBus,
    *,
    raised: list[ItemRaised],
    transitions: list[ItemTransitioned],
    violations: list,
    closeout_event,
    empty_turns: list | None = None,
):
    for ev in raised:
        await bus.publish(ev)
    for ev in transitions:
        await bus.publish(ev)
    for ev in violations:
        await bus.publish(ev)
    if closeout_event is not None:
        await bus.publish(closeout_event)
    # Spec 0141 — empty-turn signals (informational, phases 0/2/4).
    for ev in empty_turns or ():
        await bus.publish(ev)


# ─── Interaction-phase driver (shared by phase 0, 2, 4) ───────────────


async def _drive_interaction_phase(
    *,
    ctx: SessionContext,
    event_bus: EventBus,
    phase_int: int,
    phase_label: str,
    soft_cap: int,
    hard_cap: int,
    build_round_prompt,            # (agent, round, is_closeout, ...) -> (prompt, bundle, pieces)
    artifact_hash_match=None,
    on_revised_draft=None,         # optional callback for phase 4 drafter revisions
    claude_agent: AgentCall,
    openai_agent: AgentCall,
) -> tuple[PhaseRunResult, DeepResearchPhase]:
    """Run an interaction phase end-to-end using DeepResearchPhase + real agents."""
    # Spec 0144 §6.1.b — wire the production evidence validator. The
    # 4-arg signature lets apply_turn pass the per-turn ``tool_events``
    # list directly, so the validator never has to reach back into the
    # session directory at validation time.
    phase = DeepResearchPhase(
        phase=phase_int,
        agent_turn=lambda req: "",  # unused in async flow
        artifact_hash_match=artifact_hash_match,
        evidence_validator=_evidence_validator_for_run,
    )

    phase_dir = ctx.session.phase_dir(phase_label)
    await event_bus.publish(PhaseEntered(phase=phase_label))
    ctx.transcript.write("phase_entered", phase=phase_label)
    started = time.perf_counter()

    caps = caps_for(phase_int)
    is_closeout_round = False
    final_round = 0
    via_closeout = False
    via_ghost_cap = False
    via_hard_cap = False
    via_artifact_promotion = False
    converged = False
    soft_hit_emitted = False
    round_no = 0

    while round_no < caps.hard:
        round_no += 1
        final_round = round_no

        # Soft-cap signal (one-shot per phase).
        if not soft_hit_emitted and round_no > caps.soft:
            await event_bus.publish(
                SoftCapHit(phase=phase_label, round=round_no, cap=caps.soft)
            )
            soft_hit_emitted = True

        # Drive both agents in the round.
        parsed_claude = None
        parsed_openai = None
        raised_all: list[ItemRaised] = []
        transitions_all: list[ItemTransitioned] = []
        violations_all = []
        empty_turns_all: list = []

        for agent_name, agent_call in (
            ("claude", claude_agent),
            ("openai", openai_agent),
        ):
            req = AgentTurnRequest(
                phase=phase_int,
                round=round_no,
                agent=agent_name,
                other="openai" if agent_name == "claude" else "claude",
                is_closeout_round=is_closeout_round,
                standing_items=_format_standing_items(phase, agent_name),
                closeout_request=_format_closeout_request(phase, agent_name),
            )
            prompt, bundle, pieces = build_round_prompt(
                agent_name=agent_name,
                round=round_no,
                is_closeout_round=is_closeout_round,
                standing_items=req.standing_items,
                closeout_request=req.closeout_request,
                ctx=ctx,
            )

            label = f"phase{phase_int}-r{round_no}-{agent_name}"
            result = await run_one_call(
                agent=agent_call,
                prompt=prompt,
                label=label,
                phase=phase_label,
                metrics=ctx.metrics,
                transcript=ctx.transcript,
                event_bus=event_bus,
                stream_to=sys.stdout if agent_name == "claude" else None,
                stream_prefix="[claude] " if agent_name == "claude" else "",
                max_output_tokens=_TURN_MAX_OUTPUT_TOKENS,
                prompt_pieces=pieces,
                prompt_bundle=bundle,
            )
            turn_path = phase_dir / turn_filename(round=round_no, agent=agent_name)
            write_atomic(turn_path, result.text)

            # Phase 4 drafter-revision detection happens before parse so
            # the revised draft is written to disk before convergence
            # check considers it.
            if on_revised_draft is not None and agent_name == ctx.state.drafter:
                # Spec 0140 — use the inclusive extractor so the
                # draft body retains its own ``## N. Section`` headings.
                # The strict extractor truncated at the first sub-heading,
                # producing 76-byte stub drafts on the anchor run.
                revised = extract_revised_draft_inclusive(result.text)
                if revised:
                    await on_revised_draft(
                        ctx=ctx,
                        event_bus=event_bus,
                        round=round_no,
                        revised_text=revised,
                    )

            parsed = parse_turn_v2(result.text)
            if agent_name == "claude":
                parsed_claude = parsed
            else:
                parsed_openai = parsed

            # Spec 0141 — thread the upstream turn_ended payload's
            # finish_reason + output_tokens into apply_turn so an empty
            # negotiate / review turn can be attributed to ``max_tokens``
            # vs a genuinely empty model output.
            _finish_reason = (result.extras or {}).get("stop_reason") \
                or (result.extras or {}).get("finish_reason")
            _output_tokens = int(getattr(result.usage, "output_tokens", 0) or 0)
            # Spec 0144 §6.1.b — the search audit for this turn was
            # persisted by ``_on_turn_searches`` immediately after
            # ``run_one_call`` published ``turn_searches``, so by the
            # time we reach apply_turn the file is on disk. Read it
            # once per turn and hand the tool_events to apply_turn so
            # the production evidence validator can resolve the
            # address-block's evidence_event_id refs. We derive the
            # turn_key with the canonical helper so phase 0's pre-spec-
            # 0142 collapsed shape and the round-keyed shape both work.
            audit_turn_key = _derive_turn_key(
                agent_label=agent_name, phase=phase_label, label=label,
            )
            audit_tool_events = _read_turn_audit_tool_events(
                Path(ctx.transcript.path).parent, audit_turn_key,
            )
            r, t, v, e = phase.apply_turn(
                text=result.text,
                parsed=parsed,
                agent=agent_name,
                round=round_no,
                is_closeout_round=is_closeout_round,
                finish_reason=str(_finish_reason) if _finish_reason is not None else None,
                output_tokens=_output_tokens,
                audit_tool_events=audit_tool_events,
            )
            raised_all.extend(r)
            transitions_all.extend(t)
            violations_all.extend(v)
            empty_turns_all.extend(e)

        rr = phase.process_round_end(
            parsed_claude=parsed_claude,
            parsed_openai=parsed_openai,
            round=round_no,
            is_closeout_round=is_closeout_round,
            raised_events=raised_all,
            transition_events=transitions_all,
            violation_events=violations_all,
            empty_turn_events=empty_turns_all,
        )

        await _publish_round_events(
            event_bus,
            raised=list(rr.raised_events),
            transitions=list(rr.transition_events),
            violations=list(rr.violation_events),
            closeout_event=rr.closeout_event,
            empty_turns=list(rr.empty_turn_events),
        )

        # Round-complete marker event (no per-category payload — those
        # flow via ItemRaised / ItemTransitioned).
        await _publish_legacy_round_complete(
            event_bus,
            phase_int=phase_int,
            round=round_no,
            agreed=rr.converged,
            claude_status=rr.claude_status,
            openai_status=rr.openai_status,
            ctx=ctx,
        )

        if rr.converged:
            converged = True
            via_closeout = is_closeout_round
            break

        # ── Spec 0137 (widened by 0140) — substantive-convergence escape ──
        # Original 0137 form: both AGREED + terminal ledger but the
        # artifact hashes drifted (agents wrote semantically-equivalent
        # but byte-different artifact bodies). Trust the agents'
        # self-declared AGREED — promote the canonical artifact from the
        # designated agent's turn and exit.
        #
        # 0140 widening: one agent AGREED + terminal ledger past the
        # soft cap is also a deadlock shape — on the anchor run the
        # drafter's revised-draft section truncated to a 76-byte stub,
        # which left the reviewer agent unable to honestly emit AGREED
        # even though the ledger was otherwise terminal. The soft-cap
        # gate (``round_no >= caps.soft``) ensures the agents had a
        # full round budget to surface items before the branch arms.
        both_agreed = (
            rr.claude_status == "AGREED" and rr.openai_status == "AGREED"
        )
        one_agreed = (
            (rr.claude_status == "AGREED") ^ (rr.openai_status == "AGREED")
        )
        terminal_ledger = not items_blocking_convergence(phase.state.item_views())

        if terminal_ledger and (
            both_agreed
            or (one_agreed and round_no >= caps.soft)
        ):
            converged = True
            via_artifact_promotion = True
            trigger = "both_agreed" if both_agreed else "one_agreed_terminal"
            await event_bus.publish(
                ArtifactCanonicallyPromoted(phase=phase_label, round=round_no)
            )
            ctx.transcript.write(
                "artifact_canonically_promoted",
                phase=phase_label,
                round=round_no,
                trigger=trigger,
            )
            if both_agreed:
                print(
                    f"\n[{phase_label}] AGREED (artifact promotion). Both agents "
                    f"emitted STATUS: AGREED with a terminal ledger at round "
                    f"{round_no}, but their artifact bodies hash-drifted. "
                    f"Accepting their self-declared agreement.",
                    flush=True,
                )
            else:
                print(
                    f"\n[{phase_label}] AGREED (artifact promotion, one-agent path). "
                    f"Round {round_no} past soft cap with one agent AGREED and a "
                    f"terminal ledger — the other agent is stuck on something the "
                    f"protocol cannot surface. Accepting the AGREED side.",
                    flush=True,
                )
            break

        if rr.closeout_event is not None:
            if is_closeout_round:
                # Burn budget; check ghost-cap.
                if phase.spend_failed_closeout_budget():
                    ghost = phase.ghost_cap_remaining_items(round=round_no)
                    for ev in ghost:
                        await event_bus.publish(ev)
                    via_ghost_cap = True
                    converged = True
                    break
            is_closeout_round = True
        else:
            is_closeout_round = False

    if not converged and round_no >= caps.hard:
        # Spec 0136 — emit HardCapHit + flip via_hard_cap whenever the
        # loop exits at caps.hard without convergence, regardless of
        # whether any items remain non-terminal. Pre-spec the gating
        # ``if hard:`` predicate let the "every item terminal but no
        # AGREED status" pattern leak through with exit_code 0, which
        # the UI then rendered as a silent "completed" on the detail
        # page (and stuck on "running" forever on the All-Runs list).
        # The two phases that hit this loop (Phase 2 and Phase 4) emit
        # the deadlock signal here so downstream code can mark the run
        # ``deadlocked`` consistently.
        await event_bus.publish(
            HardCapHit(phase=phase_label, round=round_no, cap=caps.hard)
        )
        hard = phase.hard_cap_remaining_items(round=round_no)
        for ev in hard:
            await event_bus.publish(ev)
        via_hard_cap = True
        converged = True

    converged_event = None
    if converged:
        converged_event = phase.build_phase_converged_event(
            final_round=final_round,
            via_closeout=via_closeout,
            via_ghost_cap=via_ghost_cap,
            via_hard_cap=via_hard_cap,
            via_artifact_promotion=via_artifact_promotion,
        )
        await event_bus.publish(converged_event)

    duration_ms = int((time.perf_counter() - started) * 1000)
    await event_bus.publish(PhaseExited(phase=phase_label, duration_ms=duration_ms))
    ctx.transcript.write("phase_exited", phase=phase_label, duration_ms=duration_ms)

    result = PhaseRunResult(
        phase=phase_int,
        converged=converged,
        rounds=round_no,
        final_round=final_round,
        via_closeout=via_closeout,
        via_ghost_cap=via_ghost_cap,
        via_hard_cap=via_hard_cap,
        ledger=tuple(phase.state.ledger),
        converged_event=converged_event,
        via_artifact_promotion=via_artifact_promotion,
    )
    return result, phase


def _format_standing_items(phase: DeepResearchPhase, agent: str) -> str:
    non_terminal = [
        e for e in phase.state.ledger if not is_terminal(e.current_state)
    ]
    if not non_terminal:
        return "(none)"
    rows = []
    for e in non_terminal:
        rows.append(
            f"- [{e.id}] ({e.kind.value}, state: {e.current_state.value}, "
            f"raiser: {e.raiser}): {(e.body or '').strip()[:200]}"
        )
    return "\n".join(rows)


def _format_closeout_request(phase: DeepResearchPhase, agent: str) -> str:
    non_terminal = [
        e for e in phase.state.ledger
        if not is_terminal(e.current_state) and e.raiser == agent
    ]
    if not non_terminal:
        return ""
    return closeout_request_section(
        items=[
            {
                "id": e.id,
                "kind": e.kind.value,
                "body": e.body,
                "current_state": e.current_state.value,
            }
            for e in non_terminal
        ],
        agent_name=agent,
        remaining_budget=phase.state.closeout.remaining(agent),
    )


async def _publish_legacy_round_complete(
    bus: EventBus,
    *,
    phase_int: int,
    round: int,
    agreed: bool,
    claude_status: str | None,
    openai_status: str | None,
    ctx: SessionContext,
):
    """Spec 0115 — emit minimal round-complete marker events.

    The legacy counter fields stay at their None defaults; all
    per-category data now flows via ItemRaised / ItemTransitioned.

    Spec 0135 — Phase 0 now emits its own ``Phase0RoundComplete`` per
    round so the UI can render the same per-round-per-agent timeline
    cards Phase 2 / Phase 4 already render.
    """
    if phase_int == 0:
        await bus.publish(Phase0RoundComplete(
            round=round,
            agreed=agreed,
            claude_status=claude_status,
            openai_status=openai_status,
        ))
    elif phase_int == 2:
        await bus.publish(Phase2RoundComplete(
            round=round,
            agreed=agreed,
            claude_status=claude_status,
            openai_status=openai_status,
        ))
    elif phase_int == 4:
        await bus.publish(Phase4RoundComplete(
            round=round,
            approved=agreed,
            claude_status=claude_status,
            openai_status=openai_status,
            draft_round=ctx.state.draft_round,
        ))


# ─── Phase 0 ──────────────────────────────────────────────────────────


async def run_dr_phase0(
    *,
    ctx: SessionContext,
    claude_agent: AgentCall,
    openai_agent: AgentCall,
    event_bus: EventBus,
    brief_content: str,
    attachments: "list[Attachment] | tuple[Attachment, ...]" = (),
) -> Phase0Outcome:
    """Phase 0 (input): multi-round brief critique under the new protocol.

    Returns a legacy-shaped ``Phase0Outcome`` so ``run.py`` continues to
    work. ``brief_needs_input`` is always ``False`` under the new
    protocol — clarifications surface as ``question`` items instead.
    """
    from dual_research.protocol.prompt_pieces import pieces_for_preflight
    from dual_research.protocol.prompts import preflight_input_bundle

    def _build(*, agent_name, round, is_closeout_round, standing_items, closeout_request, ctx):
        other_name = "openai" if agent_name == "claude" else "claude"
        if round == 1:
            prompt = preflight_prompt_v2(
                brief_content=brief_content,
                agent_name=agent_name,
                other_name=other_name,
            )
            # Spec 0118: system_task = the framing template with empty
            # inputs. Rebuilding with brief_content="" yields exactly the
            # surrounding instructions; estimate_tokens counts char-length.
            system_task = preflight_prompt_v2(
                brief_content="",
                agent_name=agent_name,
                other_name=other_name,
            )
            prior = None
        else:
            prior = list_turns(
                ctx.session, phase="phase0", up_to_round=round,
                for_agent=agent_name,
            )
            caps = caps_for(0)
            prompt = input_negotiation_prompt_v2(
                brief_content=brief_content,
                prior_turns=prior,
                standing_items=standing_items,
                agent_name=agent_name,
                other_name=other_name,
                round=round,
                soft_cap=caps.soft,
                hard_cap=caps.hard,
                is_closeout_round=is_closeout_round,
                closeout_request=closeout_request,
            )
            system_task = input_negotiation_prompt_v2(
                brief_content="",
                prior_turns=[],
                standing_items="",
                agent_name=agent_name,
                other_name=other_name,
                round=round,
                soft_cap=caps.soft,
                hard_cap=caps.hard,
                is_closeout_round=is_closeout_round,
                closeout_request="",
            )
        pieces = pieces_for_preflight(
            system_task=system_task,
            user_prompt_message=brief_content,
            attachments=attachments,
            prior_turns=prior,
            ledger=(standing_items or None),
            closeout_request=(closeout_request if is_closeout_round else None),
        )
        bundle = preflight_input_bundle(
            brief=brief_content,
            attachments=attachments,
            agent_name=agent_name,
        )
        return prompt, bundle, pieces

    def _phase0_artifact_hash_match(a, b) -> bool:
        from dual_research.protocol.parse import (
            extract_agreed_interpretation_body,
        )
        body_a = extract_agreed_interpretation_body(_render_for_extract(a))
        body_b = extract_agreed_interpretation_body(_render_for_extract(b))
        if body_a is None or body_b is None:
            return False
        return canonical_hash(body_a) == canonical_hash(body_b)

    print("\n[phase 0] brief critique (multi-round) — Deep Research protocol\n", flush=True)

    caps = caps_for(0)
    result, phase = await _drive_interaction_phase(
        ctx=ctx,
        event_bus=event_bus,
        phase_int=0,
        phase_label="phase0",
        soft_cap=caps.soft,
        hard_cap=caps.hard,
        build_round_prompt=_build,
        artifact_hash_match=_phase0_artifact_hash_match,
        claude_agent=claude_agent,
        openai_agent=openai_agent,
    )

    # Capture the AGREED_INTERPRETATION block (if any) into SessionState.
    agreed_interpretation = _capture_agreed_interpretation(ctx, phase, result)
    if agreed_interpretation:
        ctx.state.agreed_interpretation = agreed_interpretation
    ctx.state.carry_forward_phase0 = _carry_forward_payload(phase.state.ledger)
    ctx.session.save_state(ctx.state)

    claude_status = "AGREED" if result.converged else "IN_PROGRESS"
    openai_status = "AGREED" if result.converged else "IN_PROGRESS"
    await event_bus.publish(Phase0Complete(
        claude_status=claude_status,
        openai_status=openai_status,
        brief_needs_input=False,
    ))
    ctx.transcript.write(
        "phase0_complete",
        claude_status=claude_status,
        openai_status=openai_status,
        brief_needs_input=False,
    )

    outcome = Phase0Outcome(
        claude_status=claude_status,
        openai_status=openai_status,
        claude_brief_issues=None,
        openai_brief_issues=None,
        brief_needs_input=False,
    )
    print(
        f"\n[phase 0] complete after {result.rounds} round(s); "
        f"converged={result.converged} via_closeout={result.via_closeout} "
        f"via_ghost_cap={result.via_ghost_cap} via_hard_cap={result.via_hard_cap}.",
        flush=True,
    )
    return outcome


def _render_for_extract(parsed) -> str:
    """Re-render a ``ParsedTurnV2.phase_artifact`` as a fake turn so
    the artifact extractors can run against it."""
    if parsed is None or not parsed.phase_artifact:
        return ""
    return f"## Phase artifact\n\n{parsed.phase_artifact}\n"


def _compute_draft_sha_if_present(ctx: SessionContext) -> str | None:
    """Spec 0214 — orchestrator-side provenance for ``Phase4Complete``.

    Reads the on-disk draft for ``ctx.state.draft_round`` and returns
    its ``canonical_hash``. Returns ``None`` when no draft file exists
    for the final round (hard-cap / artifact-promotion paths with no
    draft yet on disk).
    """
    draft_path = current_draft_path(ctx.session, ctx.state.draft_round)
    if not draft_path.exists():
        return None
    return hash_draft_content(draft_path.read_text(encoding="utf-8"))


def phase4_version_gate(parsed_a, parsed_b, *, ctx_draft_round: int) -> bool:
    """Spec 0214 — phase-4 convergence gate (orchestrator-owned versioning).

    Returns ``True`` iff both agents emit an ``AGREED_DRAFT_ACCEPTANCE``
    block carrying the same ``draft_version`` AND that version equals
    ``ctx_draft_round``. The second clause anchors the gate against
    orchestrator-tracked state, so a same-round revise-then-AGREE
    (drafter bumps version to ``N+1`` and emits AGREED with
    ``draft_version: v<N+1>`` before the orchestrator advances the
    pointer) is rejected. Replaces the agent-emitted SHA-256 gate that
    deadlocked on agents' inability to replicate ``canonical_hash``.
    """
    ta = _render_for_extract(parsed_a)
    tb = _render_for_extract(parsed_b)
    acc_a = extract_agreed_draft_acceptance(ta)
    acc_b = extract_agreed_draft_acceptance(tb)
    if acc_a is None or acc_b is None:
        return False
    ver_a, _ = acc_a
    ver_b, _ = acc_b
    return ver_a == ver_b == ctx_draft_round


def _capture_agreed_interpretation(
    ctx: SessionContext,
    phase: DeepResearchPhase,
    result: PhaseRunResult,
) -> str | None:
    """Read the AGREED_INTERPRETATION block from the final phase-0 turn
    files on disk and return it. Returns ``None`` if no convergence."""
    if not result.converged:
        return None
    turn_path_claude = ctx.session.phase_dir("phase0") / turn_filename(
        round=result.final_round, agent="claude",
    )
    if not turn_path_claude.exists():
        return None
    text = turn_path_claude.read_text(encoding="utf-8")
    return extract_agreed_interpretation_body(text)


# ─── Phase 1 ──────────────────────────────────────────────────────────


async def run_dr_phase1(
    *,
    ctx: SessionContext,
    claude_agent: AgentCall,
    openai_agent: AgentCall,
    event_bus: EventBus,
    brief_content: str,
    attachments: "list[Attachment] | tuple[Attachment, ...]" = (),
) -> Phase1Outcome:
    """Phase 1 (research-plan): single-shot parallel plan + thesis using
    the new prompt with the agreed interpretation inlined."""
    from dual_research.protocol.prompt_pieces import pieces_for_research_plan
    from dual_research.protocol.prompts import research_input_bundle

    phase_dir = ctx.session.phase_dir("phase1")
    await event_bus.publish(PhaseEntered(phase="phase1"))
    ctx.transcript.write("phase_entered", phase="phase1")
    started = time.perf_counter()

    agreed = ctx.state.agreed_interpretation or "(phase 0 did not produce a hash-matched interpretation; proceed from the brief alone.)"

    claude_prompt = research_plan_prompt_v2(
        brief_content=brief_content,
        agreed_interpretation=agreed,
        agent_name="claude",
    )
    openai_prompt = research_plan_prompt_v2(
        brief_content=brief_content,
        agreed_interpretation=agreed,
        agent_name="openai",
    )
    # Spec 0118: system_task = the framing template (no brief, no
    # agreed_interpretation inlined). Built once per agent so the
    # agent-name interpolation inside the template is faithful.
    claude_system_task = research_plan_prompt_v2(
        brief_content="", agreed_interpretation="", agent_name="claude",
    )
    openai_system_task = research_plan_prompt_v2(
        brief_content="", agreed_interpretation="", agent_name="openai",
    )
    claude_pieces = pieces_for_research_plan(
        system_task=claude_system_task,
        user_prompt_message=brief_content,
        attachments=attachments,
        agreed_interpretation=agreed,
    )
    openai_pieces = pieces_for_research_plan(
        system_task=openai_system_task,
        user_prompt_message=brief_content,
        attachments=attachments,
        agreed_interpretation=agreed,
    )
    claude_bundle = research_input_bundle(
        brief=brief_content, attachments=attachments, agent_name="claude",
    )
    openai_bundle = research_input_bundle(
        brief=brief_content, attachments=attachments, agent_name="openai",
    )

    print(
        "\n[phase 1] independent research plans — both agents in parallel\n",
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
            max_output_tokens=_DRAFT_MAX_OUTPUT_TOKENS,
            prompt_pieces=claude_pieces,
            prompt_bundle=claude_bundle,
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
            max_output_tokens=_DRAFT_MAX_OUTPUT_TOKENS,
            prompt_pieces=openai_pieces,
            prompt_bundle=openai_bundle,
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
        Phase1Complete(
            claude_chars=outcome.claude_chars, openai_chars=outcome.openai_chars
        )
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
    return outcome


# ─── Phase 2 ──────────────────────────────────────────────────────────


async def run_dr_phase2(
    *,
    ctx: SessionContext,
    claude_agent: AgentCall,
    openai_agent: AgentCall,
    event_bus: EventBus,
    brief_content: str,
    soft_cap: int,
    hard_cap: int,
    attachments: "list[Attachment] | tuple[Attachment, ...]" = (),
) -> Phase2Outcome:
    """Phase 2 (negotiate-plan): multi-round plan negotiation under the
    new protocol with closeout mechanism (no escape valves)."""
    from dual_research.protocol.prompt_pieces import pieces_for_plan_negotiation
    from dual_research.protocol.prompts import (
        negotiation_round1_input_bundle,
        negotiation_turn_input_bundle,
    )

    p1 = ctx.session.phase_dir("phase1")
    own_plan_claude = (p1 / "draft-claude.md").read_text(encoding="utf-8")
    own_plan_openai = (p1 / "draft-openai.md").read_text(encoding="utf-8")
    agreed_interp = ctx.state.agreed_interpretation or "(none)"

    def _build(*, agent_name, round, is_closeout_round, standing_items, closeout_request, ctx):
        own = own_plan_claude if agent_name == "claude" else own_plan_openai
        other = own_plan_openai if agent_name == "claude" else own_plan_claude
        other_name = "openai" if agent_name == "claude" else "claude"
        if round == 1:
            prompt = plan_negotiation_round1_prompt_v2(
                brief_content=brief_content,
                agreed_interpretation=agreed_interp,
                own_plan=own,
                other_plan=other,
                agent_name=agent_name,
                other_name=other_name,
            )
            # Spec 0118: system_task = the framing template with all
            # variable inputs replaced by empty strings.
            system_task = plan_negotiation_round1_prompt_v2(
                brief_content="",
                agreed_interpretation="",
                own_plan="",
                other_plan="",
                agent_name=agent_name,
                other_name=other_name,
            )
            prior = None
            bundle = negotiation_round1_input_bundle(
                brief=brief_content,
                claude_draft=own_plan_claude,
                openai_draft=own_plan_openai,
                attachments=attachments,
                agent_name=agent_name,
            )
        else:
            prior = list_turns(
                ctx.session, phase="phase2", up_to_round=round,
                for_agent=agent_name,
            )
            prompt = plan_negotiation_round_n_prompt_v2(
                brief_content=brief_content,
                agreed_interpretation=agreed_interp,
                own_plan=own,
                other_plan=other,
                prior_turns=prior,
                standing_items=standing_items,
                agent_name=agent_name,
                other_name=other_name,
                round=round,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
                is_closeout_round=is_closeout_round,
                closeout_request=closeout_request,
            )
            system_task = plan_negotiation_round_n_prompt_v2(
                brief_content="",
                agreed_interpretation="",
                own_plan="",
                other_plan="",
                prior_turns=[],
                standing_items="",
                agent_name=agent_name,
                other_name=other_name,
                round=round,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
                is_closeout_round=is_closeout_round,
                closeout_request="",
            )
            bundle = negotiation_turn_input_bundle(
                brief=brief_content,
                claude_draft=own_plan_claude,
                openai_draft=own_plan_openai,
                prior_turns=prior,
                attachments=attachments,
                agent_name=agent_name,
                other_name=other_name,
            )
        pieces = pieces_for_plan_negotiation(
            system_task=system_task,
            user_prompt_message=brief_content,
            attachments=attachments,
            agreed_interpretation=agreed_interp,
            phase1_claude=own_plan_claude,
            phase1_openai=own_plan_openai,
            prior_turns=prior,
            ledger=(standing_items or None),
            closeout_request=(closeout_request if is_closeout_round else None),
        )
        return prompt, bundle, pieces

    print("\n[phase 2] plan negotiation — Deep Research protocol\n", flush=True)

    result, phase = await _drive_interaction_phase(
        ctx=ctx,
        event_bus=event_bus,
        phase_int=2,
        phase_label="phase2",
        soft_cap=soft_cap,
        hard_cap=hard_cap,
        build_round_prompt=_build,
        artifact_hash_match=_phase2_artifact_hash_match_factory(),
        claude_agent=claude_agent,
        openai_agent=openai_agent,
    )

    # Capture agreed plan + drafter from the final round's claude turn.
    agreed_plan_body: str | None = None
    drafter: str | None = None
    if result.converged:
        path = ctx.session.phase_dir("phase2") / turn_filename(
            round=result.final_round, agent="claude",
        )
        if path.exists():
            text = path.read_text(encoding="utf-8")
            agreed_plan_body = extract_agreed_plan_body(text)
            if agreed_plan_body:
                drafter = extract_drafter_from_agreed_plan(agreed_plan_body)

    # Hard-cap tiebreak: if convergence is via hard_cap and no drafter
    # was named, fall back to "claude" per spec § Convergence rules
    # (the "If still tied, default to claude" path).
    if drafter is None and result.converged:
        drafter = "claude"

    ctx.state.agreed_plan = agreed_plan_body
    ctx.state.drafter = drafter
    ctx.state.carry_forward_phase2 = _carry_forward_payload(phase.state.ledger)
    if drafter is not None:
        ctx.state.phase = "phase3"
    ctx.session.save_state(ctx.state)

    from dual_research.contract.lifecycle import State as _State
    fsd_count = sum(
        1 for e in phase.state.ledger
        if e.kind == Category.DISAGREEMENT and e.current_state == _State.ACKNOWLEDGED
    )
    await event_bus.publish(Phase2Complete(
        rounds=result.rounds,
        converged=result.converged,
        drafter=drafter,
        fsd_count=fsd_count,
        via_tiebreak=result.via_hard_cap and drafter == "claude",
    ))
    ctx.transcript.write(
        "phase2_complete",
        rounds=result.rounds,
        converged=result.converged,
        drafter=drafter,
        fsd_count=fsd_count,
    )

    # Build legacy Phase2Outcome shape for finalize.py consumption.
    fsd_dicts = [
        {
            "id": e.id,
            "title": e.body[:60],
            "claude_position": "",
            "openai_position": "",
            "agreed_treatment_in_final": "(see carry-forward in final appendix)",
        }
        for e in phase.state.ledger
        if e.kind == Category.DISAGREEMENT
        and e.current_state == State.ACKNOWLEDGED
    ]
    ctx.state.final_surfaced_disagreements = fsd_dicts
    ctx.session.save_state(ctx.state)

    last_claude_path = ctx.session.phase_dir("phase2") / turn_filename(
        round=result.final_round, agent="claude",
    )
    last_openai_path = ctx.session.phase_dir("phase2") / turn_filename(
        round=result.final_round, agent="openai",
    )
    last_claude = last_claude_path.read_text(encoding="utf-8") if last_claude_path.exists() else None
    last_openai = last_openai_path.read_text(encoding="utf-8") if last_openai_path.exists() else None

    outcome = Phase2Outcome(
        converged=result.converged,
        rounds=result.rounds,
        drafter=drafter,
        agreed_plan=agreed_plan_body,
        fsd_count=len(fsd_dicts),
        via_tiebreak=result.via_hard_cap and drafter == "claude",
        hard_capped=result.via_hard_cap,
        parse_failure=False,
        last_claude_text=last_claude,
        last_openai_text=last_openai,
    )
    return outcome


def _phase2_artifact_hash_match_factory():
    """Phase 2 hash-match: AGREED_PLAN body matches AND DRAFTER matches."""
    def _match(a, b) -> bool:
        ta = _render_for_extract(a)
        tb = _render_for_extract(b)
        body_a = extract_agreed_plan_body(ta)
        body_b = extract_agreed_plan_body(tb)
        if body_a is None or body_b is None:
            return False
        if canonical_hash(body_a) != canonical_hash(body_b):
            return False
        d_a = extract_drafter_from_agreed_plan(body_a)
        d_b = extract_drafter_from_agreed_plan(body_b)
        return d_a is not None and d_a == d_b
    return _match


# ─── Phase 3 ──────────────────────────────────────────────────────────


async def run_dr_phase3(
    *,
    ctx: SessionContext,
    claude_agent: AgentCall,
    openai_agent: AgentCall,
    event_bus: EventBus,
    brief_content: str,
    attachments: "list[Attachment] | tuple[Attachment, ...]" = (),
) -> Phase3Outcome:
    """Phase 3 (draft): single-shot drafter run with structured carry-forward."""
    from dual_research.protocol.prompt_pieces import pieces_for_drafting
    from dual_research.protocol.prompts import drafting_input_bundle

    drafter = ctx.state.drafter
    if drafter not in ("claude", "openai"):
        raise RuntimeError(
            f"Phase 3 reached without a valid drafter (state.drafter={drafter!r})"
        )

    phase_dir = ctx.session.phase_dir("phase3")
    await event_bus.publish(PhaseEntered(phase="phase3"))
    ctx.transcript.write("phase_entered", phase="phase3")
    started = time.perf_counter()

    p1 = ctx.session.phase_dir("phase1")
    own_plan = (p1 / f"draft-{drafter}.md").read_text(encoding="utf-8")
    other = "openai" if drafter == "claude" else "claude"
    other_plan = (p1 / f"draft-{other}.md").read_text(encoding="utf-8")
    prior_turns = list_turns(ctx.session, phase="phase2")

    agent = claude_agent if drafter == "claude" else openai_agent

    agreed_interp = ctx.state.agreed_interpretation or "(none)"
    agreed_plan = ctx.state.agreed_plan or "(none)"
    carry_forward_items = ctx.state.carry_forward_phase2 or []

    prompt = drafting_prompt_v2(
        brief_content=brief_content,
        agreed_interpretation=agreed_interp,
        own_plan=own_plan,
        other_plan=other_plan,
        agreed_plan=agreed_plan,
        carry_forward_items=carry_forward_items,
        prior_phase2_turns=prior_turns,
        agent_name=drafter,
        other_name=other,
    )
    # Spec 0118: system_task = framing template with empty inputs.
    system_task = drafting_prompt_v2(
        brief_content="",
        agreed_interpretation="",
        own_plan="",
        other_plan="",
        agreed_plan="",
        carry_forward_items=[],
        prior_phase2_turns=[],
        agent_name=drafter,
        other_name=other,
    )
    claude_draft = own_plan if drafter == "claude" else other_plan
    openai_draft = own_plan if drafter == "openai" else other_plan
    # carry_forward serialized to text approximates _fmt_cf's output
    # length (the same single-line-per-item format used in the prompt).
    def _fmt_cf_text(items):
        rows = []
        for it in items or []:
            if isinstance(it, dict):
                iid, state, body, kind = (
                    it.get("id", "?"), it.get("current_state", "?"),
                    it.get("body", ""), it.get("kind", "?"),
                )
            else:
                iid, state, body, kind = (
                    getattr(it, "id", "?"), getattr(it, "current_state", "?"),
                    getattr(it, "body", ""), getattr(it, "kind", "?"),
                )
            rows.append(f"- [{iid}] ({kind}, state: {state}): {body}")
        return "\n".join(rows) if rows else "(none)"

    pieces = pieces_for_drafting(
        system_task=system_task,
        user_prompt_message=brief_content,
        attachments=attachments,
        agreed_interpretation=agreed_interp,
        phase1_claude=own_plan if drafter == "claude" else other_plan,
        phase1_openai=own_plan if drafter == "openai" else other_plan,
        agreed_plan=agreed_plan,
        all_p2_turns=prior_turns,
        carry_forward=_fmt_cf_text(carry_forward_items) if carry_forward_items else None,
    )
    bundle = drafting_input_bundle(
        brief=brief_content,
        claude_draft=claude_draft,
        openai_draft=openai_draft,
        plan=ctx.state.agreed_plan,
        prior_turns=prior_turns,
        attachments=attachments,
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
        max_output_tokens=_DRAFT_MAX_OUTPUT_TOKENS,
        prompt_pieces=pieces,
        prompt_bundle=bundle,
    )

    draft_path = phase_dir / "draft-v1.md"
    write_atomic(draft_path, result.text)

    outcome = Phase3Outcome(
        drafter=drafter, draft_chars=len(result.text), draft_path=str(draft_path),
    )
    await event_bus.publish(
        Phase3Complete(drafter=drafter, draft_chars=outcome.draft_chars)
    )
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
    return outcome


# ─── Phase 4 ──────────────────────────────────────────────────────────


async def run_dr_phase4(
    *,
    ctx: SessionContext,
    claude_agent: AgentCall,
    openai_agent: AgentCall,
    event_bus: EventBus,
    brief_content: str,
    soft_cap: int,
    hard_cap: int,
    attachments: "list[Attachment] | tuple[Attachment, ...]" = (),
) -> Phase4Outcome:
    """Phase 4 (review-draft): multi-round review under the new protocol."""
    from dual_research.protocol.prompt_pieces import pieces_for_review
    from dual_research.protocol.prompts import review_input_bundle

    drafter = ctx.state.drafter or "claude"
    revisions_count = 0

    async def _on_revised_draft(*, ctx, event_bus, round, revised_text):
        nonlocal revisions_count
        revisions_count += 1
        new_round = ctx.state.draft_round + 1
        new_path = ctx.session.phase_dir("phase4") / f"draft-v{new_round}.md"
        write_atomic(new_path, revised_text)
        ctx.state.draft_round = new_round
        ctx.session.save_state(ctx.state)
        await event_bus.publish(Phase4DraftRevised(
            round=round,
            new_draft_round=new_round,
            new_draft_chars=len(revised_text),
        ))

    def _build(*, agent_name, round, is_closeout_round, standing_items, closeout_request, ctx):
        current_path = current_draft_path(ctx.session, ctx.state.draft_round)
        draft_content = current_path.read_text(encoding="utf-8")
        other_name = "openai" if agent_name == "claude" else "claude"
        if round == 1:
            prompt = review_round1_prompt_v2(
                brief_content=brief_content,
                draft_content=draft_content,
                drafter_name=drafter,
                agent_name=agent_name,
                other_name=other_name,
            )
            # Spec 0118: system_task = framing template with empty inputs.
            system_task = review_round1_prompt_v2(
                brief_content="",
                draft_content="",
                drafter_name=drafter,
                agent_name=agent_name,
                other_name=other_name,
            )
            prior_turns: list[PriorTurn] = []
        else:
            prior_turns = list_turns(
                ctx.session, phase="phase4", up_to_round=round,
                for_agent=agent_name,
            )
            prompt = review_round_n_prompt_v2(
                brief_content=brief_content,
                draft_content=draft_content,
                drafter_name=drafter,
                prior_turns=prior_turns,
                standing_items=standing_items,
                agent_name=agent_name,
                other_name=other_name,
                round=round,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
                draft_version=ctx.state.draft_round,
                is_closeout_round=is_closeout_round,
                closeout_request=closeout_request,
            )
            system_task = review_round_n_prompt_v2(
                brief_content="",
                draft_content="",
                drafter_name=drafter,
                prior_turns=[],
                standing_items="",
                agent_name=agent_name,
                other_name=other_name,
                round=round,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
                draft_version=ctx.state.draft_round,
                is_closeout_round=is_closeout_round,
                closeout_request="",
            )
        pieces = pieces_for_review(
            system_task=system_task,
            user_prompt_message=brief_content,
            attachments=attachments,
            current_draft=draft_content,
            prior_turns=(prior_turns or None),
            ledger=(standing_items or None),
            closeout_request=(closeout_request if is_closeout_round else None),
        )
        bundle = review_input_bundle(
            brief=brief_content,
            draft=draft_content,
            prior_turns=prior_turns,
            attachments=attachments,
            agent_name=agent_name,
            other_name=other_name,
        )
        return prompt, bundle, pieces

    def _phase4_artifact_version_match(a, b) -> bool:
        return phase4_version_gate(
            a, b, ctx_draft_round=ctx.state.draft_round,
        )

    print("\n[phase 4] review-draft — Deep Research protocol\n", flush=True)

    result, phase = await _drive_interaction_phase(
        ctx=ctx,
        event_bus=event_bus,
        phase_int=4,
        phase_label="phase4",
        soft_cap=soft_cap,
        hard_cap=hard_cap,
        build_round_prompt=_build,
        artifact_hash_match=_phase4_artifact_version_match,
        on_revised_draft=_on_revised_draft,
        claude_agent=claude_agent,
        openai_agent=openai_agent,
    )

    ctx.state.carry_forward_phase4 = _carry_forward_payload(phase.state.ledger)
    ctx.session.save_state(ctx.state)

    approved = result.converged and not result.via_hard_cap
    # Spec 0214: orchestrator records its own canonical SHA of the
    # on-disk draft for provenance; agents no longer echo a hash.
    draft_file_sha256 = _compute_draft_sha_if_present(ctx)
    await event_bus.publish(Phase4Complete(
        rounds=result.rounds,
        approved=approved,
        final_draft_round=ctx.state.draft_round,
        revisions=revisions_count,
        draft_file_sha256=draft_file_sha256,
    ))
    ctx.transcript.write(
        "phase4_complete",
        rounds=result.rounds,
        approved=approved,
        final_draft_round=ctx.state.draft_round,
        revisions=revisions_count,
        draft_file_sha256=draft_file_sha256,
    )

    last_claude_path = ctx.session.phase_dir("phase4") / turn_filename(
        round=result.final_round, agent="claude",
    )
    last_openai_path = ctx.session.phase_dir("phase4") / turn_filename(
        round=result.final_round, agent="openai",
    )
    last_claude = last_claude_path.read_text(encoding="utf-8") if last_claude_path.exists() else None
    last_openai = last_openai_path.read_text(encoding="utf-8") if last_openai_path.exists() else None

    outcome = Phase4Outcome(
        approved=result.converged and not result.via_hard_cap,
        rounds=result.rounds,
        final_draft_round=ctx.state.draft_round,
        revisions=revisions_count,
        hard_capped=result.via_hard_cap,
        parse_failure=False,
        last_claude_text=last_claude,
        last_openai_text=last_openai,
    )
    return outcome


__all__ = [
    "run_dr_phase0",
    "run_dr_phase1",
    "run_dr_phase2",
    "run_dr_phase3",
    "run_dr_phase4",
]
