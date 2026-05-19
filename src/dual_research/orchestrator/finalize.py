from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from dual_research.events import EventBus, FinalEmitted
from dual_research.orchestrator.phase2 import Phase2Outcome
from dual_research.orchestrator.phase3 import current_draft_path
from dual_research.orchestrator.phase4 import Phase4Outcome
from dual_research.persistence import Metrics, SessionContext
from dual_research.persistence.state import write_atomic


def confidence_tag(
    *,
    phase2_outcome: Phase2Outcome | None,
    phase4_outcome: Phase4Outcome,
    soft_cap: int,
    hard_cap: int,
    repair_count: int,
) -> str:
    """HIGH / MODERATE / LOW based on round counts, caps, repairs.

    Spec 0036: ``phase2_outcome`` can be ``None`` when resuming a run that
    completed Phase 2 in a previous invocation (state.json was past Phase 2
    on resume so Phase 2 didn't re-run). In that case we don't have the
    Phase 2 round / FSD counts and degrade to MODERATE rather than crashing.
    """
    if not phase4_outcome.approved:
        return "LOW"
    if phase2_outcome is None:
        return "MODERATE"
    p2_clean = phase2_outcome.rounds <= soft_cap and not phase2_outcome.via_tiebreak
    p4_clean = phase4_outcome.rounds <= soft_cap
    if p2_clean and p4_clean and repair_count == 0 and phase2_outcome.fsd_count == 0:
        return "HIGH"
    return "MODERATE"


def _count_repairs(transcript_path: Path) -> int:
    if not transcript_path.exists():
        return 0
    n = 0
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        if '"event": "repair_invoked"' in line:
            n += 1
    return n


def render_metadata_header(
    *,
    ctx: SessionContext,
    phase2_outcome: Phase2Outcome | None,
    phase4_outcome: Phase4Outcome,
    soft_cap: int,
    hard_cap: int,
    claude_model: str,
    openai_model: str,
) -> str:
    """Compose the metadata header for ``final.md``.

    Spec 0036: ``phase2_outcome`` is ``None`` when resuming a run that
    completed Phase 2 in a previous invocation. The header renders a
    "(replayed from prior run — Phase 2 details unavailable)" note in
    place of the negotiation rounds + FSD lines.
    """
    m = ctx.metrics
    by_agent = m.totals_by_agent()
    total = m.total_cost_usd()
    calls = sum(b.get("calls", 0) for b in by_agent.values())
    input_tokens = sum(b.get("input_tokens", 0) for b in by_agent.values())
    output_tokens = sum(b.get("output_tokens", 0) for b in by_agent.values())
    total_ms = sum(b.get("duration_ms", 0) for b in by_agent.values())
    total_min = total_ms // 60_000
    total_sec = (total_ms % 60_000) // 1000

    repair_count = _count_repairs(ctx.session.transcript_path)
    conf = confidence_tag(
        phase2_outcome=phase2_outcome,
        phase4_outcome=phase4_outcome,
        soft_cap=soft_cap,
        hard_cap=hard_cap,
        repair_count=repair_count,
    )
    outcome = (
        "**APPROVED** — both agents signed off"
        if phase4_outcome.approved
        else "**DEADLOCKED** — hard cap hit, document includes unresolved review comments"
    )

    if phase2_outcome is None:
        p2_rounds_line = "(replayed from prior run — Phase 2 details unavailable)"
        p2_drafter_line = "(replayed from prior run — drafter recorded in state.json)"
        p2_fsd_line = "(replayed from prior run)"
    else:
        p2_note = "moderate contention" if phase2_outcome.rounds > 2 else "clean convergence"
        if phase2_outcome.rounds > soft_cap:
            p2_note += "; soft cap crossed"
        if phase2_outcome.via_tiebreak:
            p2_note += "; drafter resolved by orchestrator tiebreak"
        p2_rounds_line = f"**{phase2_outcome.rounds} rounds** ({p2_note})"
        p2_drafter_line = f"**{phase2_outcome.drafter or '(unset)'}**"
        p2_fsd_line = str(phase2_outcome.fsd_count)

    p4_note = f"{phase4_outcome.revisions} draft revision(s)"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "> ## How this document was produced",
        ">",
        f"> Two agents (`{claude_model}` and `{openai_model}`) co-authored this via the dual-research protocol on **{now}**.",
        ">",
        "> | metric | value |",
        "> |---|---|",
        f"> | Outcome | {outcome} |",
        f"> | Plan negotiation | {p2_rounds_line} |",
        f"> | Drafter | {p2_drafter_line} |",
        f"> | Review | **{phase4_outcome.rounds} rounds**, {p4_note} (final = draft v{phase4_outcome.final_draft_round}) |",
        f"> | FSDs surfaced | {p2_fsd_line} |",
        f"> | Repair turns | {repair_count} |",
        f"> | Total time | {total_min}m {total_sec}s ({calls} model calls) |",
        f"> | Tokens | {input_tokens:,} input · {output_tokens:,} output |",
        f"> | Cost | ${total:.4f} (best-effort, not an invoice) |",
        ">",
        f"> Read with **{conf} confidence**.",
        "",
        "",
    ]
    return "\n".join(lines)


async def emit_final(
    *,
    ctx: SessionContext,
    event_bus: EventBus,
    out_path: Path | None,
    phase2_outcome: Phase2Outcome | None,
    phase4_outcome: Phase4Outcome,
    soft_cap: int,
    hard_cap: int,
    claude_model: str,
    openai_model: str,
) -> Path:
    """Compose and write final.md (session + optional out_path).

    For deadlocked runs, includes the last two Phase 4 review turns as an
    appendix so a human can adjudicate.
    """
    draft_path = current_draft_path(ctx.session, ctx.state.draft_round)
    draft_body = draft_path.read_text(encoding="utf-8")
    header = render_metadata_header(
        ctx=ctx,
        phase2_outcome=phase2_outcome,
        phase4_outcome=phase4_outcome,
        soft_cap=soft_cap,
        hard_cap=hard_cap,
        claude_model=claude_model,
        openai_model=openai_model,
    )

    appendix = ""
    if not phase4_outcome.approved:
        appendix = (
            f"\n\n---\n\n"
            f"# Reviewer disagreements (unresolved after {phase4_outcome.rounds} rounds)\n\n"
            f"## claude — last review turn\n\n"
            f"{phase4_outcome.last_claude_text or '(no content)'}\n\n"
            f"---\n\n"
            f"## openai — last review turn\n\n"
            f"{phase4_outcome.last_openai_text or '(no content)'}\n"
        )

    # Spec 0115 — Deep Research unresolved-items appendix. Built from
    # the carry-forward fields on SessionState (populated by the dr
    # phase runners at phase boundaries). Appended to final.md as
    # plain markdown so it renders in any viewer; the UI parses it
    # back into structured card stacks for richer display.
    dr_appendix = _render_unresolved_items_appendix(ctx)
    if dr_appendix:
        appendix = (appendix or "") + dr_appendix

    final_body = header + draft_body + appendix
    session_final = ctx.session.root / "final.md"
    write_atomic(session_final, final_body)

    final_out: Path | None = None
    if out_path is not None:
        out_path = Path(out_path).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(session_final, out_path)
        final_out = out_path

    ctx.state.final_emitted_to = str(final_out) if final_out else str(session_final)
    ctx.session.save_state(ctx.state)

    conf = confidence_tag(
        phase2_outcome=phase2_outcome,
        phase4_outcome=phase4_outcome,
        soft_cap=soft_cap,
        hard_cap=hard_cap,
        repair_count=_count_repairs(ctx.session.transcript_path),
    )
    await event_bus.publish(
        FinalEmitted(
            session_final_path=str(session_final),
            out_path=str(final_out) if final_out else None,
            char_count=len(final_body),
            confidence=conf,
        )
    )
    ctx.transcript.write(
        "final_emitted",
        session_final_path=str(session_final),
        out_path=str(final_out) if final_out else None,
        char_count=len(final_body),
        confidence=conf,
    )
    return session_final


# ─── Spec 0115 — unresolved-items appendix renderer ───────────────────


_PHASE_SECTION_TITLE = {
    0: "Briefing limitations (phase 0)",
    2: ("Surfaced disagreements (negotiate-plan phase)",
        "Unanswered research questions (negotiate-plan phase)"),
    4: ("Known issues in this draft (review-draft phase)",
        "Pending comments (review-draft phase)"),
}


def _is_appendix_candidate(entry: dict) -> bool:
    """Spec 0114 — items appearing in the appendix are terminal-not-resolved.

    Resolved items vanish into the document body. Acknowledged / capped
    items always surface. Withdrawn items surface only when the reason
    is non-trivial (length > 40 chars and no boilerplate prefix).
    """
    state = entry.get("current_state")
    if state in {"acknowledged", "capped"}:
        return True
    if state == "withdrawn":
        # Look at the last transition's reason.
        transitions = entry.get("transitions") or []
        last = transitions[-1] if transitions else None
        reason = (last or {}).get("reason", "") if isinstance(last, dict) else ""
        if len(reason) <= 40:
            return False
        boilerplate = ("duplicate of", "superseded by")
        if any(reason.strip().lower().startswith(b) for b in boilerplate):
            return False
        return True
    return False


def _format_entry(entry: dict) -> str:
    iid = entry.get("id", "?")
    state = entry.get("current_state", "?")
    body = (entry.get("body") or "").strip().replace("\n", " ")
    transitions = entry.get("transitions") or []
    last = transitions[-1] if transitions else {}
    raiser = entry.get("raiser", "?")
    raiser_label = "Claude" if raiser == "claude" else "GPT" if raiser == "openai" else raiser
    raised_round = entry.get("raised_round", "?")
    terminal_round = last.get("round", "?") if isinstance(last, dict) else "?"
    via = last.get("via") if isinstance(last, dict) else None
    state_label = f"{state} ({via})" if via else state
    reason = last.get("reason", "") if isinstance(last, dict) else ""

    lines = [
        f"- [{iid}] {state_label}: {body}",
        f"  - Raised by: {raiser_label} in round {raised_round}",
        f"  - Terminal in round {terminal_round}",
    ]
    if reason:
        # Single-line reason for readability in plain markdown viewers.
        reason_line = reason.strip().replace("\n", " ")[:400]
        lines.append(f"  - Reason: {reason_line}")
    return "\n".join(lines)


def _entries_by_kind(entries: list[dict], kind: str) -> list[dict]:
    return [e for e in entries if e.get("kind") == kind and _is_appendix_candidate(e)]


def _render_unresolved_items_appendix(ctx) -> str:
    """Render the ``## Appendix — Unresolved items`` section as plain markdown.

    Reads from ``ctx.state.carry_forward_phase{0,2,4}`` (populated by
    the dr phase runners). Returns empty string if no carry-forward
    items exist (legacy runs / clean convergence).
    """
    cf0 = getattr(ctx.state, "carry_forward_phase0", []) or []
    cf2 = getattr(ctx.state, "carry_forward_phase2", []) or []
    cf4 = getattr(ctx.state, "carry_forward_phase4", []) or []
    if not (cf0 or cf2 or cf4):
        return ""

    sections: list[str] = []

    # Phase 0 — briefing limitations
    p0 = [e for e in cf0 if _is_appendix_candidate(e)]
    if p0:
        sections.append("### " + _PHASE_SECTION_TITLE[0])
        for e in p0:
            sections.append(_format_entry(e))
        sections.append("")

    # Phase 2 — disagreements + questions in separate subsections.
    p2_disagreements = _entries_by_kind(cf2, "disagreement")
    p2_questions = _entries_by_kind(cf2, "question")
    if p2_disagreements:
        sections.append("### " + _PHASE_SECTION_TITLE[2][0])
        for e in p2_disagreements:
            sections.append(_format_entry(e))
        sections.append("")
    if p2_questions:
        sections.append("### " + _PHASE_SECTION_TITLE[2][1])
        for e in p2_questions:
            sections.append(_format_entry(e))
        sections.append("")

    # Phase 4 — issues + comments in separate subsections.
    p4_issues = _entries_by_kind(cf4, "issue")
    p4_comments = _entries_by_kind(cf4, "comment")
    if p4_issues:
        sections.append("### " + _PHASE_SECTION_TITLE[4][0])
        for e in p4_issues:
            sections.append(_format_entry(e))
        sections.append("")
    if p4_comments:
        sections.append("### " + _PHASE_SECTION_TITLE[4][1])
        for e in p4_comments:
            sections.append(_format_entry(e))
        sections.append("")

    if not sections:
        return ""

    return "\n\n---\n\n## Appendix — Unresolved items\n\n" + "\n".join(sections)
