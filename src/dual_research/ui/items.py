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
from typing import Callable

from dual_research.ui.models import (
    CategoryCounters,
    ConsultedSource,
    EvidenceRecord,
    Item,
    ItemTransition,
    PhaseCategoryStats,
    TurnCategoryStats,
)


# Audit lookup signature: given a logical turn_key, return the persisted
# ``TurnSearchAudit`` dict (or None if no audit exists for that turn).
AuditLookup = Callable[[str], dict | None]


def _derive_turn_key_for_transition(*, phase: int, round: int, actor: str) -> str:
    """Mirror of ``orchestrator/_call._derive_turn_key`` for items.

    The ItemTransitioned event doesn't carry ``turn_key`` directly, but
    the (phase, round, actor) triple is enough to reconstruct it under
    the round-keyed convention spec 0142 established for phases 0 / 2 / 4.
    Phases 1 / 3 collapse to ``phase{N}_{agent}`` (no per-round audits).
    """
    if not actor or actor in {"mutual", "orchestrator"}:
        return ""
    ui_ag = "gpt" if actor == "openai" else actor
    if phase in (0, 2, 4):
        return f"phase{phase}_round{round}_{ui_ag}"
    return f"phase{phase}_{ui_ag}"


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


_SEARCH_N_PATTERN = "search_"


def _resolve_consulted_sources(
    *,
    evidence_event_id: str,
    audit: dict | None,
) -> list[ConsultedSource]:
    """Spec 0144 §6.1.d / §9.5 — resolve an evidence_event_id against the
    persisted ``TurnSearchAudit`` and project a slim consulted_sources list.

    The model emits logical handles (``search_1``, ``search_2``, …)
    rather than the provider's opaque physical event_id
    (``srvtoolu_…`` for Anthropic, ``ws_…`` for OpenAI). Both
    providers persist their ``tool_events`` list in turn-order, so
    ``search_N`` resolves to ``tool_events[N-1]``. We also fall back to
    matching by physical ``event_id`` when the model happens to emit
    the real handle.

    Returns an empty list when the audit is missing, the event_id is
    empty, no match is found, or the matched ToolEvent has no
    consulted sources. ``encrypted_content`` is intentionally NOT
    projected (multi-KB per source; UI never renders it).
    """
    if not evidence_event_id or not audit:
        return []
    tool_events = audit.get("tool_events") or []
    if not isinstance(tool_events, list) or not tool_events:
        return []

    matched: dict | None = None
    if evidence_event_id.startswith(_SEARCH_N_PATTERN):
        idx_str = evidence_event_id[len(_SEARCH_N_PATTERN):]
        try:
            idx = int(idx_str) - 1
        except (TypeError, ValueError):
            idx = -1
        if 0 <= idx < len(tool_events) and isinstance(tool_events[idx], dict):
            matched = tool_events[idx]
    if matched is None:
        for ev in tool_events:
            if isinstance(ev, dict) and ev.get("event_id") == evidence_event_id:
                matched = ev
                break
    if matched is None:
        return []

    queries = [
        str(q) for q in (matched.get("queries") or []) if isinstance(q, (str, int))
    ]
    out: list[ConsultedSource] = []
    for src in matched.get("consulted_sources") or []:
        if not isinstance(src, dict):
            continue
        url = str(src.get("url") or "")
        if not url:
            continue
        out.append(ConsultedSource(
            url=url,
            title=str(src.get("title") or ""),
            page_age=str(src.get("page_age") or ""),
            queries=list(queries),
        ))
    return out


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
    turn_key: str = "",
    attached_at: str = "",
    audit_lookup: AuditLookup | None = None,
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

    audit = audit_lookup(turn_key) if (audit_lookup and turn_key) else None

    for rec in evidence_records or []:
        if not isinstance(rec, dict):
            continue
        record = EvidenceRecord(
            item_id=item_id,
            url=str(rec.get("url", "")),
            title=str(rec.get("title", "")),
            search_query=str(rec.get("search_query", "")),
            fetched_at=str(rec.get("fetched_at", "")),
            evidence_event_id=str(rec.get("evidence_event_id", "")),
            content_excerpt=str(rec.get("content_excerpt", "")),
            unverified=bool(rec.get("unverified", False)),
            unverified_reason=str(rec.get("unverified_reason", "")),
            raised_in_round=int(item.raised_round or 0),
            answered_in_round=int(round),
            requested_by=None,
            provided_by=str(actor or ""),
            attached_at=str(attached_at or ""),
            consulted_sources=_resolve_consulted_sources(
                evidence_event_id=str(rec.get("evidence_event_id", "")),
                audit=audit,
            ),
        )
        item.evidence.append(record)

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


def aggregate_items(
    events: list[dict],
    *,
    audit_lookup: AuditLookup | None = None,
) -> AggregatedItems:
    """Build the aggregated bundle from a list of event dicts.

    ``events`` is the raw JSON-decoded event stream from
    ``transcript.jsonl``. Only ``item_raised`` / ``item_transitioned``
    events drive aggregation; all others are ignored.

    Returns a bundle where ``CategoryCounters.standing`` is the
    DELTA at this round (raised − closed); ``_finalise_running_totals``
    is then called to convert standing-deltas into absolute running
    standing totals per (phase, raiser) sequence so the timeline JSX
    can read absolute values directly.

    Spec 0144 — when ``audit_lookup`` is supplied, every transition's
    evidence record is densified with the slim ``consulted_sources``
    projection drawn from the per-turn ``TurnSearchAudit`` (resolved
    by ``search_N`` enumeration). ``audit_lookup`` is keyed by the
    logical turn_key (``phase{N}_round{R}_{agent}`` or
    ``phase{N}_{agent}``); callers building from a session dir
    typically wrap ``_read_search_audit(session_dir, turn_key)``.
    """
    bundle = AggregatedItems()
    for event in events:
        # Transcript writes ``event``; orchestrator dicts use ``kind`` /
        # ``event_type``. Accept all three so the same aggregator works
        # against the live transcript path AND the replay event list.
        kind = (
            event.get("kind")
            or event.get("event_type")
            or event.get("event")
        )
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
            phase_i = int(event.get("phase", 0))
            round_i = int(event.get("round", 0))
            actor_s = str(event.get("actor", ""))
            turn_key = str(event.get("turn_key") or "") or _derive_turn_key_for_transition(
                phase=phase_i, round=round_i, actor=actor_s,
            )
            _apply_transition(
                bundle,
                item_id=str(event.get("id", "")),
                from_state=str(event.get("from_state", "")),
                to_state=str(event.get("to_state", "")),
                actor=actor_s,
                phase=phase_i,
                round=round_i,
                reason=str(event.get("reason", "")),
                via=event.get("via"),
                evidence_records=event.get("evidence_records") or [],
                turn_key=turn_key,
                attached_at=str(event.get("ts", "")),
                audit_lookup=audit_lookup,
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


def aggregate_items_from_transcript(
    transcript_path: Path,
    *,
    audit_lookup: AuditLookup | None = None,
) -> AggregatedItems:
    """Convenience wrapper: read ``transcript.jsonl`` and aggregate.

    Spec 0144 — pass ``audit_lookup`` through to ``aggregate_items`` so
    callers with a session directory in scope can densify evidence
    records with ``consulted_sources`` resolved against
    ``session_dir/searches/<turn-key>.json``.
    """
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
    return aggregate_items(events, audit_lookup=audit_lookup)


def build_session_audit_lookup(session_dir: Path) -> AuditLookup:
    """Spec 0144 §6.1.d — build a turn_key → TurnSearchAudit dict lookup.

    Reads ``session_dir/searches/<turn-key>.json`` lazily (per turn_key)
    and caches the result. Returns ``None`` when the file is missing or
    unreadable so the caller can fall back to the un-densified path.
    """
    searches_dir = session_dir / "searches"
    cache: dict[str, dict | None] = {}

    def _lookup(turn_key: str) -> dict | None:
        if not turn_key:
            return None
        if turn_key in cache:
            return cache[turn_key]
        path = searches_dir / f"{turn_key}.json"
        if not path.is_file():
            cache[turn_key] = None
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cache[turn_key] = data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            cache[turn_key] = None
        return cache[turn_key]

    return _lookup
