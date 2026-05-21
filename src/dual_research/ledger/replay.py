"""Spec 0122 — replay item-lifecycle events from on-disk round files.

This module is the offline counterpart to the orchestrator's live event
emission. Production runs publish ``ItemRaised`` / ``ItemTransitioned``
/ ``CloseoutUrged`` / ``CloseoutViolation`` events to the bus, which the
spec-0122 transcript bridge mirrors to ``transcript.jsonl``. The UI
aggregator (``aggregate_items_from_transcript``) then reads those lines
to build per-turn / per-phase category stats.

Runs created before the bridge landed have no item events on disk. This
module reconstructs the same event stream by re-driving
``DeepResearchPhase.apply_turn`` + ``process_round_end`` over the on-
disk ``phase{N}/round-NN-{claude,openai}.md`` files. Because the replay
imports the orchestrator's actual lifecycle logic, it can never drift
from the live path's semantics.

The output is the same ``AggregatedItems`` shape
``aggregate_items_from_transcript`` returns, so the UI aggregator can
swap one for the other transparently.
"""

from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from dual_research.contract.caps import caps_for
from dual_research.events import (
    CloseoutUrged,
    CloseoutViolation,
    EmptyTurnDetected,
    ItemRaised,
    ItemTransitioned,
    ProtocolViolation,
)
from dual_research.orchestrator.deep_research import DeepResearchPhase
from dual_research.protocol.parse import parse_turn_v2
from dual_research.ui.items import AggregatedItems, aggregate_items


_ROUND_FILE_RE = re.compile(r"^round-(\d+)-(claude|openai)\.md$")

# Phases that admit raisable items under spec 0114 (matches
# ``categories.PHASE_TOKEN``). Phase 1 is single-shot drafts and Phase 3
# is the silent drafter; neither produces operation blocks.
_RAISABLE_PHASES = (0, 2, 4)


def _discover_rounds(phase_dir: Path) -> list[int]:
    """Return the sorted unique round numbers present in ``phase_dir``."""
    if not phase_dir.is_dir():
        return []
    seen: set[int] = set()
    for entry in phase_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        if ".malformed" in entry.name:
            continue
        m = _ROUND_FILE_RE.match(entry.name)
        if not m:
            continue
        seen.add(int(m.group(1)))
    return sorted(seen)


def _event_to_dict(event: Any) -> dict:
    """Coerce an orchestrator event to the dict shape ``aggregate_items``
    consumes.

    ``aggregate_items`` reads ``kind`` (event-name) and the per-event
    fields. ``Event.to_dict`` already returns this shape; we route via
    ``asdict`` as a fallback to keep the function tolerant of any future
    non-frozen event subclass.
    """
    if hasattr(event, "to_dict"):
        return event.to_dict()
    if is_dataclass(event):
        return asdict(event)
    raise TypeError(f"cannot serialise event of type {type(event).__name__}")


def _replay_phase(session_dir: Path, *, phase: int) -> list[dict]:
    """Replay one phase's round files into a flat list of event dicts.

    The events appear in the same order the live orchestrator would
    publish them (round-by-round, claude first, then openai, then
    closeout-urge / cap events at end-of-round). The shape matches what
    ``aggregate_items`` reads: ``kind`` plus the lifecycle fields.
    """
    phase_dir = session_dir / f"phase{phase}"
    rounds = _discover_rounds(phase_dir)
    if not rounds:
        return []

    dr_phase = DeepResearchPhase(phase=phase, agent_turn=lambda req: "")
    caps = caps_for(phase)

    events: list[dict] = []
    is_closeout_round = False
    converged = False

    for round_no in rounds:
        if converged:
            # Defensive: orchestrator stops emitting after convergence.
            break

        parsed_claude = None
        parsed_openai = None
        raised_all: list[ItemRaised] = []
        transitions_all: list[ItemTransitioned] = []
        violations_all: list[CloseoutViolation | ProtocolViolation] = []
        empty_turns_all: list[EmptyTurnDetected] = []

        for agent in ("claude", "openai"):
            path = phase_dir / f"round-{round_no:02d}-{agent}.md"
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            parsed = parse_turn_v2(text)
            if agent == "claude":
                parsed_claude = parsed
            else:
                parsed_openai = parsed
            # Spec 0141 — replay can't see the upstream turn_ended
            # payload's finish_reason / output_tokens, so apply_turn
            # falls back to None / 0. The empty-turn detector still
            # fires; the cause-attribution field is just unknown.
            r, t, v, e = dr_phase.apply_turn(
                text=text,
                parsed=parsed,
                agent=agent,
                round=round_no,
                is_closeout_round=is_closeout_round,
            )
            raised_all.extend(r)
            transitions_all.extend(t)
            violations_all.extend(v)
            empty_turns_all.extend(e)
            events.extend(_event_to_dict(ev) for ev in r)
            events.extend(_event_to_dict(ev) for ev in t)
            events.extend(_event_to_dict(ev) for ev in v)
            events.extend(_event_to_dict(ev) for ev in e)

        if parsed_claude is None and parsed_openai is None:
            continue

        rr = dr_phase.process_round_end(
            parsed_claude=parsed_claude,
            parsed_openai=parsed_openai,
            round=round_no,
            is_closeout_round=is_closeout_round,
            raised_events=raised_all,
            transition_events=transitions_all,
            violation_events=violations_all,
            empty_turn_events=empty_turns_all,
        )

        if rr.closeout_event is not None:
            events.append(_event_to_dict(rr.closeout_event))

        if rr.converged:
            converged = True
            continue

        if rr.closeout_event is not None:
            if is_closeout_round and dr_phase.spend_failed_closeout_budget():
                for ev in dr_phase.ghost_cap_remaining_items(round=round_no):
                    events.append(_event_to_dict(ev))
                converged = True
                continue
            is_closeout_round = True
        else:
            is_closeout_round = False

    # Hard-cap: if we ran out of rounds without convergence and the
    # final round equals the configured hard cap, the live driver
    # would have auto-capped remaining items.
    if not converged and rounds and rounds[-1] >= caps.hard:
        for ev in dr_phase.hard_cap_remaining_items(round=rounds[-1]):
            events.append(_event_to_dict(ev))

    return events


def replay_items_from_disk(session_dir: Path) -> AggregatedItems:
    """Reconstruct the canonical ``AggregatedItems`` for a session.

    Walks every phase that admits items (0, 2, 4), reads the round
    files in order, and re-drives ``DeepResearchPhase.apply_turn`` +
    ``process_round_end`` to regenerate the lifecycle event stream.
    The stream is then fed into ``aggregate_items`` (the same
    function the live transcript-replay path uses), so the resulting
    bundle is byte-for-byte indistinguishable from a live run's.

    Returns an empty bundle when no v2 round files exist on disk —
    callers can use this to distinguish "no items raised" from "no
    rounds happened yet".
    """
    events: list[dict] = []
    for phase in _RAISABLE_PHASES:
        events.extend(_replay_phase(session_dir, phase=phase))
    return aggregate_items(events)
