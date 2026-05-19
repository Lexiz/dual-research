"""Spec 0115 — unified Item + per-category aggregation from the event stream.

Single pass over a session's transcript that builds:

- ``Item`` instances for every ``ItemRaised`` event, with their full
  transition history attached from ``ItemTransitioned`` events.
- Per-(phase, round, agent) ``TurnCategoryStats`` (standing / raised /
  closed / capped per category) for the timeline chips.
- Per-phase aggregated ``PhaseCategoryStats`` for the phase-header row.

The output is the canonical data shape the new UI surface (timeline
chips + Critique pane + final-doc appendix) reads from. Legacy fields
on ``TurnStats`` (open_questions / blocking / fsd / open_issues) are
NOT computed here — they come from the legacy-shim path during the
transition window, and they're deleted in step 6 (shim removal).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from dual_research.ui.models import (
    CategoryCounters,
    EvidenceRecord,
    Item,
    ItemTransition,
    PhaseCategoryStats,
    TurnCategoryStats,
)


# ─── Constants ────────────────────────────────────────────────────────


_TERMINAL_STATES = frozenset({"resolved", "acknowledged", "withdrawn", "capped"})


_KIND_TO_FIELD = {
    "question": "questions",
    "disagreement": "disagreements",
    "issue": "issues",
    "comment": "comments",
}


@dataclass
class AggregatedItems:
    """Bundle returned by ``aggregate_items_from_transcript``.

    - ``items``                : every Item in raise-time order.
    - ``turn_category_stats``  : nested dict
        ``{phase: {round: {agent: TurnCategoryStats}}}``.
    - ``phase_category_stats`` : per-phase aggregated stats
        ``{phase: PhaseCategoryStats}``.
    """

    items: list[Item] = field(default_factory=list)
    turn_category_stats: dict[int, dict[int, dict[str, TurnCategoryStats]]] = field(
        default_factory=dict
    )
    phase_category_stats: dict[int, PhaseCategoryStats] = field(default_factory=dict)


def _empty_turn_stats() -> TurnCategoryStats:
    return TurnCategoryStats()


def _get_turn_stats(
    bundle: AggregatedItems, *, phase: int, round: int, agent: str,
) -> TurnCategoryStats:
    by_round = bundle.turn_category_stats.setdefault(phase, {})
    by_agent = by_round.setdefault(round, {})
    if agent not in by_agent:
        by_agent[agent] = _empty_turn_stats()
    return by_agent[agent]


def _get_phase_stats(bundle: AggregatedItems, phase: int) -> PhaseCategoryStats:
    if phase not in bundle.phase_category_stats:
        bundle.phase_category_stats[phase] = PhaseCategoryStats()
    return bundle.phase_category_stats[phase]


def _counter_for(stats, kind: str) -> CategoryCounters:
    """Return the per-category ``CategoryCounters`` on a stats dataclass.

    ``stats`` is either ``TurnCategoryStats`` or ``PhaseCategoryStats``.
    """
    field_name = _KIND_TO_FIELD[kind]
    return getattr(stats, field_name)


def _apply_raise(
    bundle: AggregatedItems,
    *,
    item_id: str,
    item_kind: str,
    phase: int,
    round: int,
    raiser: str,
    body: str,
    anchor_type: str,
    anchor_text: str,
    evidence_required: bool,
) -> Item:
    item = Item(
        id=item_id,
        kind=item_kind,
        phase=phase,
        raiser=raiser,
        body=body,
        anchor_type=anchor_type,
        anchor_text=anchor_text,
        evidence_required=evidence_required,
        raised_round=round,
        current_state="open",
    )
    bundle.items.append(item)

    if item_kind not in _KIND_TO_FIELD:
        return item

    turn_stats = _get_turn_stats(bundle, phase=phase, round=round, agent=raiser)
    _counter_for(turn_stats, item_kind).raised += 1
    _counter_for(turn_stats, item_kind).standing += 1

    phase_stats = _get_phase_stats(bundle, phase)
    _counter_for(phase_stats, item_kind).raised += 1
    _counter_for(phase_stats, item_kind).standing += 1

    return item


def _find_item(bundle: AggregatedItems, item_id: str) -> Item | None:
    for it in bundle.items:
        if it.id == item_id:
            return it
    return None


def _apply_transition(
    bundle: AggregatedItems,
    *,
    item_id: str,
    from_state: str,
    to_state: str,
    actor: str,
    phase: int,
    round: int,
    reason: str,
    via: str | None,
    evidence_records: list[dict],
) -> None:
    item = _find_item(bundle, item_id)
    if item is None:
        return  # transition of an unknown item — ignore

    item.transitions.append(ItemTransition(
        from_state=from_state,
        to_state=to_state,
        actor=actor,
        round=round,
        reason=reason,
        via=via,
    ))
    item.current_state = to_state

    for rec in evidence_records or []:
        if not isinstance(rec, dict):
            continue
        item.evidence.append(EvidenceRecord(
            item_id=item_id,
            url=str(rec.get("url", "")),
            title=str(rec.get("title", "")),
            search_query=str(rec.get("search_query", "")),
            fetched_at=str(rec.get("fetched_at", "")),
            evidence_event_id=str(rec.get("evidence_event_id", "")),
            content_excerpt=str(rec.get("content_excerpt", "")),
        ))

    kind = item.kind
    raiser = item.raiser
    if kind not in _KIND_TO_FIELD:
        return

    # Standing tracks (open + addressed). A transition into a terminal
    # state decrements standing; a transition out of terminal would
    # increment (orchestrator transitions are always toward terminal,
    # so the latter doesn't happen in practice — but we guard against
    # the counter-argument case `addressed → open` which keeps the
    # item non-terminal and therefore doesn't decrement standing).
    was_non_terminal = from_state not in _TERMINAL_STATES
    is_non_terminal = to_state not in _TERMINAL_STATES

    turn_stats = _get_turn_stats(bundle, phase=phase, round=round, agent=raiser)
    phase_stats = _get_phase_stats(bundle, phase)

    if was_non_terminal and not is_non_terminal:
        # Closed this round.
        _counter_for(turn_stats, kind).closed += 1
        _counter_for(turn_stats, kind).standing -= 1
        _counter_for(phase_stats, kind).closed += 1
        _counter_for(phase_stats, kind).standing -= 1
        if via in {"hard_cap", "ghost_cap"}:
            _counter_for(turn_stats, kind).capped += 1
            _counter_for(phase_stats, kind).capped += 1


def aggregate_items(events: list[dict]) -> AggregatedItems:
    """Build the aggregated bundle from a list of event dicts.

    ``events`` is the raw JSON-decoded event stream from
    ``transcript.jsonl``. Only ``item_raised`` / ``item_transitioned``
    events drive aggregation; all others are ignored.

    Returns a bundle where ``CategoryCounters.standing`` is the
    DELTA at this round (raised − closed); ``_finalise_running_totals``
    is then called to convert standing-deltas into absolute running
    standing totals per (phase, raiser) sequence so the timeline JSX
    can read absolute values directly.
    """
    bundle = AggregatedItems()
    for event in events:
        kind = event.get("kind") or event.get("event_type")
        if kind == "item_raised":
            _apply_raise(
                bundle,
                item_id=str(event.get("id", "")),
                item_kind=str(event.get("item_kind", "")),
                phase=int(event.get("phase", 0)),
                round=int(event.get("round", 0)),
                raiser=str(event.get("raiser", "")),
                body=str(event.get("body", "")),
                anchor_type=str(event.get("anchor_type", "none")),
                anchor_text=str(event.get("anchor_text", "")),
                evidence_required=bool(event.get("evidence_required", False)),
            )
        elif kind == "item_transitioned":
            _apply_transition(
                bundle,
                item_id=str(event.get("id", "")),
                from_state=str(event.get("from_state", "")),
                to_state=str(event.get("to_state", "")),
                actor=str(event.get("actor", "")),
                phase=int(event.get("phase", 0)),
                round=int(event.get("round", 0)),
                reason=str(event.get("reason", "")),
                via=event.get("via"),
                evidence_records=event.get("evidence_records") or [],
            )
    _finalise_running_totals(bundle)
    return bundle


def _finalise_running_totals(bundle: AggregatedItems) -> None:
    """Convert per-turn ``standing`` deltas into absolute running totals.

    Walks each (phase, raiser) sequence in round order and accumulates
    the standing delta. Carries forward across rounds where the agent
    didn't act so every emitted TurnCategoryStats row carries the
    correct end-of-round standing total for both agents.
    """
    for phase, by_round in bundle.turn_category_stats.items():
        rounds = sorted(by_round.keys())
        agents = {a for r in rounds for a in by_round[r].keys()}
        for agent in agents:
            running = {"questions": 0, "disagreements": 0, "issues": 0, "comments": 0}
            for r in rounds:
                slot = by_round.setdefault(r, {})
                stats = slot.get(agent)
                if stats is None:
                    # Carry-forward: agent didn't act this round; emit
                    # a row with raised/closed=0 and the running
                    # standing total carried in.
                    from dual_research.ui.models import (
                        CategoryCounters,
                        TurnCategoryStats,
                    )
                    stats = TurnCategoryStats()
                    slot[agent] = stats
                for field in ("questions", "disagreements", "issues", "comments"):
                    cc = getattr(stats, field)
                    running[field] += cc.standing
                    cc.standing = running[field]
    # Same idea for phase-level totals — standing currently holds
    # raised − closed, which IS the phase-end carry-forward count.
    # No carry-across-phases (each phase is independent).
    pass


def aggregate_items_from_transcript(transcript_path: Path) -> AggregatedItems:
    """Convenience wrapper: read ``transcript.jsonl`` and aggregate."""
    if not transcript_path.exists():
        return AggregatedItems()
    events: list[dict] = []
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return aggregate_items(events)
