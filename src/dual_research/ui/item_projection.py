"""Spec 0122 — project the unified ``Item`` model into the legacy typed
lists + ``phase_ledgers`` shapes the UI still consumes.

Background: spec 0115 introduced a single ``Item`` model that captures
every tracked artefact (question / disagreement / issue / comment) with
its full lifecycle transition history. The new UI surfaces
(``run.phase_stats.items``) read from that model directly. But several
existing components still read the legacy typed lists ``run.questions``,
``run.disagreements``, ``run.issues``, ``run.comments`` and the per-
phase ledger ``run.phase_ledgers[phase]``. Before this module, those
fields were populated by the legacy section-schema reconstructors,
which return ``[]`` for any post-spec-0114 run because the on-disk
section headings no longer match.

This module fills the gap: given an ``AggregatedItems`` bundle (from
the transcript replay or the disk-replay fallback), it projects each
``Item`` into the legacy dataclass that the frontend expects.

No information loss in the projection — every legacy field is either
mapped from an ``Item`` field or set to a stable default.
"""

from __future__ import annotations

from dataclasses import asdict

from dual_research.ledger.models import (
    LedgerEntry,
    LedgerStatusTransition,
)
from dual_research.ui.items import AggregatedItems
from dual_research.ui.models import (
    Comment,
    Disagreement,
    Issue,
    Item,
    ProgressionStep,
    Question,
)


# Backend vocabulary uses ``openai``; the UI vocabulary uses ``gpt``.
# Helper kept local so the projection stays self-contained.
def _ui_agent(backend_agent: str) -> str:
    return "gpt" if backend_agent == "openai" else backend_agent


def _turn_key(phase: int, round: int, ui_agent: str) -> str:
    """Format the canonical turn key the UI uses for cross-axis highlighting."""
    if phase == 0:
        # Phase 0 (preflight) has rounds too in the new protocol.
        return f"phase0_round{round}_{ui_agent}"
    return f"phase{phase}_round{round}_{ui_agent}"


def _terminal_round(item: Item) -> int | None:
    """Round when the item entered its current terminal state, or None
    if the item is still in an open / addressed (non-terminal) state."""
    if item.current_state in ("open", "addressed"):
        return None
    if not item.transitions:
        return None
    return item.transitions[-1].round


def _terminal_turn_key(item: Item) -> str | None:
    """Closed-turn key in UI vocabulary, or None when not yet closed."""
    rnd = _terminal_round(item)
    if rnd is None:
        return None
    actor = item.transitions[-1].actor if item.transitions else item.raiser
    # ``actor`` is one of "claude" / "openai" / "orchestrator" / "mutual".
    # Use the raiser as the turn-key agent for orchestrator/mutual
    # transitions (cap / handshake) — the raiser's card is the most
    # useful place to surface the cross-axis highlight.
    if actor in ("claude", "openai"):
        return _turn_key(item.phase, rnd, _ui_agent(actor))
    return _turn_key(item.phase, rnd, _ui_agent(item.raiser))


# ─── Projection: Item → legacy typed objects ──────────────────────────


def _item_to_question(item: Item) -> Question:
    answered_round = _terminal_round(item)
    answered_turn_key = _terminal_turn_key(item)
    answered = item.current_state != "open"
    last_transition = item.transitions[-1] if item.transitions else None
    answered_by = None
    if answered and last_transition is not None:
        actor = last_transition.actor
        if actor in ("claude", "openai"):
            answered_by = _ui_agent(actor)
    return Question(
        id=item.id,
        phase=item.phase,
        raised_round=item.raised_round,
        raised_by=_ui_agent(item.raiser),
        status="answered" if answered else "open",
        body=item.body,
        quote=item.anchor_text if item.anchor_type == "quote" else None,
        after=item.anchor_text if item.anchor_type == "after" else None,
        block_id=None,
        raised_turn_key=_turn_key(item.phase, item.raised_round, _ui_agent(item.raiser)),
        answered_round=answered_round if answered else None,
        answered_by=answered_by,
        answered_turn_key=answered_turn_key if answered else None,
        answer_body=last_transition.reason if (answered and last_transition) else "",
        match=None,
    )


def _disagreement_status(item: Item) -> str:
    """Map a v2 item state to the legacy DisagreementStatus enum.

    Legacy enum: ``open`` / ``resolved-claude`` / ``resolved-gpt`` /
    ``resolved-both``. We map the v2 terminal states by who triggered
    the transition (raiser for WITHDRAW, addressee for ADDRESS,
    ``mutual`` for the ACK handshake, ``orchestrator`` for caps).
    """
    if item.current_state == "open" or item.current_state == "addressed":
        return "open"
    if not item.transitions:
        return "open"
    last = item.transitions[-1]
    if last.actor == "mutual":
        return "resolved-both"
    if last.actor in ("claude", "openai"):
        return f"resolved-{_ui_agent(last.actor)}"
    # Orchestrator-driven (cap) — attribute to the raiser by convention.
    return f"resolved-{_ui_agent(item.raiser)}"


def _build_progression(item: Item) -> list[ProgressionStep]:
    """Map ``ItemTransition`` history into the UI ProgressionStep list.

    The legacy steps use action vocabulary
    ``raised | pushed back | restated | conceded | aligned``. We use a
    minimal mapping that conveys the same shape:

    - The item's raise produces the first ``raised`` step.
    - ``open → addressed`` → ``pushed back`` (addressee responded).
    - ``addressed → resolved`` / ``open → withdrawn`` → ``conceded``.
    - ``open → acknowledged`` (mutual) → ``aligned``.
    - ``addressed → open`` (counter-argument) → ``restated``.
    - ``* → capped`` → ``conceded`` (orchestrator-forced).
    """
    steps: list[ProgressionStep] = [
        ProgressionStep(
            round=item.raised_round,
            agent=_ui_agent(item.raiser),
            action="raised",
            note=(item.body or "").strip()[:200],
        )
    ]
    for tr in item.transitions:
        action: str
        if tr.to_state == "addressed":
            action = "pushed back"
        elif tr.from_state == "addressed" and tr.to_state == "open":
            action = "restated"
        elif tr.to_state == "acknowledged":
            action = "aligned"
        elif tr.to_state in ("resolved", "withdrawn", "capped"):
            action = "conceded"
        else:
            action = "raised"
        if tr.actor == "mutual":
            agent = "both"
        elif tr.actor in ("claude", "openai"):
            agent = _ui_agent(tr.actor)
        else:
            agent = _ui_agent(item.raiser)
        steps.append(ProgressionStep(
            round=tr.round,
            agent=agent,
            action=action,
            note=(tr.reason or "").strip()[:200],
        ))
    return steps


def _item_to_disagreement(item: Item) -> Disagreement:
    raised_round = item.raised_round
    closed_round = _terminal_round(item)
    status = _disagreement_status(item)
    progression = _build_progression(item)
    raised_turn_key = _turn_key(item.phase, raised_round, _ui_agent(item.raiser))
    closed_turn_key = _terminal_turn_key(item) if status != "open" else None

    # Positions: the raiser's body is their own position. If the item
    # has an ADDRESS transition, the addressee's reason text is the
    # other side's position.
    raiser_ui = _ui_agent(item.raiser)
    claude_pos = ""
    gpt_pos = ""
    if raiser_ui == "claude":
        claude_pos = item.body
    else:
        gpt_pos = item.body
    for tr in item.transitions:
        if tr.to_state == "addressed":
            other = "gpt" if raiser_ui == "claude" else "claude"
            if other == "claude" and not claude_pos:
                claude_pos = tr.reason
            elif other == "gpt" and not gpt_pos:
                gpt_pos = tr.reason
            break

    resolution = None
    if status != "open" and item.transitions:
        resolution = (item.transitions[-1].reason or "").strip() or None

    short_label = (item.body or "").strip().split("\n", 1)[0][:80]

    return Disagreement(
        id=item.id,
        phase=item.phase,
        round=closed_round or raised_round,
        opened_round=raised_round,
        closed_round=closed_round,
        status=status,  # type: ignore[arg-type]
        deadlocked=(item.current_state == "capped"),
        raised_by=raiser_ui,
        short_label=short_label,
        point=item.body,
        claude_position=claude_pos,
        gpt_position=gpt_pos,
        resolution=resolution,
        progression=progression,
        raised_turn_key=raised_turn_key,
        closed_turn_key=closed_turn_key,
    )


def _item_to_issue(item: Item) -> Issue:
    """Map an Item(kind="issue") into the legacy Issue type."""
    closed_round = _terminal_round(item)
    return Issue(
        id=item.id,
        phase=item.phase,
        raised_by=_ui_agent(item.raiser),
        round_first_seen=item.raised_round,
        round_last_seen=closed_round or item.raised_round,
        status="open" if item.current_state == "open" else "resolved",  # type: ignore[arg-type]
        body=item.body,
        quote=item.anchor_text if item.anchor_type == "quote" else None,
        after=item.anchor_text if item.anchor_type == "after" else None,
        block_id=None,
        raised_turn_key=_turn_key(item.phase, item.raised_round, _ui_agent(item.raiser)),
    )


def _item_to_comment(item: Item) -> Comment:
    """Map an Item(kind="comment") into the legacy Comment type."""
    return Comment(
        id=item.id,
        phase=item.phase,
        raised_by=_ui_agent(item.raiser),
        raised_round=item.raised_round,
        body=item.body,
        quote=item.anchor_text if item.anchor_type == "quote" else None,
        after=item.anchor_text if item.anchor_type == "after" else None,
        block_id=None,
        raised_turn_key=_turn_key(item.phase, item.raised_round, _ui_agent(item.raiser)),
    )


# ─── Projection: Item → LedgerEntry (phase_ledgers) ───────────────────


def _item_to_ledger_entry(item: Item) -> LedgerEntry:
    """Project one Item into the LedgerEntry shape consumed by the
    chip-deltas computation in the frontend.

    The frontend's ``computeChipDeltas`` reads:
    - ``kind``                 — for category bucketing
    - ``raised_turn_key`` (camelCased) — to attribute the raise to a turn
    - ``status_history``       — to walk transitions and count closes
    Other fields are surfaced in tooltips but don't drive chip math.
    """
    raiser_ui = _ui_agent(item.raiser)
    raised_turn_key = _turn_key(item.phase, item.raised_round, raiser_ui)
    history: list[LedgerStatusTransition] = [
        LedgerStatusTransition(
            round=item.raised_round,
            status="open",
            reason="item raised",
            turn_key=raised_turn_key,
        )
    ]
    for tr in item.transitions:
        if tr.actor in ("claude", "openai"):
            actor_ui = _ui_agent(tr.actor)
        elif tr.actor == "mutual":
            actor_ui = raiser_ui  # turn key needs a concrete agent — use raiser
        else:
            actor_ui = raiser_ui
        history.append(LedgerStatusTransition(
            round=tr.round,
            status=tr.to_state,
            reason=(tr.reason or "").strip()[:200],
            turn_key=_turn_key(item.phase, tr.round, actor_ui),
        ))
    last_addressed: int | None = None
    for tr in item.transitions:
        if tr.to_state == "addressed":
            last_addressed = tr.round
    return LedgerEntry(
        id=item.id,
        kind=item.kind,
        raised_round=item.raised_round,
        raised_by=raiser_ui,
        raised_turn_key=raised_turn_key,
        current_status=item.current_state,
        status_history=history,
        body_snippet=(item.body or "").strip().replace("\n", " ")[:120],
        last_addressed_round=last_addressed,
        ghosted_rounds=0,
    )


# ─── Public API ───────────────────────────────────────────────────────


def project_typed_lists(
    bundle: AggregatedItems,
) -> tuple[list[Question], list[Disagreement], list[Issue], list[Comment]]:
    """Project ``AggregatedItems.items`` into the four legacy typed lists.

    Returns ``(questions, disagreements, issues, comments)`` — ordered
    by raise time (the order ``aggregate_items`` already maintains).
    """
    questions: list[Question] = []
    disagreements: list[Disagreement] = []
    issues: list[Issue] = []
    comments: list[Comment] = []
    for item in bundle.items:
        if item.kind == "question":
            questions.append(_item_to_question(item))
        elif item.kind == "disagreement":
            disagreements.append(_item_to_disagreement(item))
        elif item.kind == "issue":
            issues.append(_item_to_issue(item))
        elif item.kind == "comment":
            comments.append(_item_to_comment(item))
    return questions, disagreements, issues, comments


def project_phase_ledgers(bundle: AggregatedItems) -> dict[int, list[dict]]:
    """Project ``AggregatedItems.items`` into the per-phase ledger shape.

    The frontend consumes ``run.phaseLedgers[phase]`` as a list of
    dicts (the typed ``LedgerEntry`` already dict-serializes cleanly).
    Spec 0135 added Phase 0 alongside phases 2 and 4 so the new-protocol
    multi-round brief negotiation contributes to the chip-deltas and
    cross-round ledger math just like the plan/review negotiations do.
    """
    out: dict[int, list[dict]] = {0: [], 2: [], 4: []}
    for item in bundle.items:
        if item.phase not in out:
            continue
        out[item.phase].append(asdict(_item_to_ledger_entry(item)))
    return out
