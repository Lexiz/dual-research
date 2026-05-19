"""Spec 0114 — six-state item lifecycle.

Every tracked item, regardless of category, lives in one of six states.
Four are terminal: ``resolved``, ``acknowledged``, ``withdrawn``, ``capped``.
Two are non-terminal: ``open``, ``addressed``.

The transition table here is the canonical source of truth for what
transitions are legal and who is allowed to trigger each. Agent-driven
transitions name the actor as ``"raiser"`` or ``"addressee"``;
``acknowledged`` is reached only via a mutual handshake (both parties
emit ACKNOWLEDGE for the same item in consecutive turns) — represented
as ``actor: "mutual"``. ``capped`` is orchestrator-only and never appears
in the agent-facing transition table.
"""

from __future__ import annotations

from enum import StrEnum


class State(StrEnum):
    OPEN = "open"
    ADDRESSED = "addressed"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    WITHDRAWN = "withdrawn"
    CAPPED = "capped"


TERMINAL_STATES: frozenset[State] = frozenset({
    State.RESOLVED,
    State.ACKNOWLEDGED,
    State.WITHDRAWN,
    State.CAPPED,
})


def is_terminal(state: State | str) -> bool:
    """``True`` iff ``state`` is a terminal lifecycle state."""
    if isinstance(state, str):
        try:
            state = State(state)
        except ValueError:
            return False
    return state in TERMINAL_STATES


# Valid transitions: from-state → {to-state: spec dict}. Spec dict carries
# ``actor`` (who is allowed to trigger this transition) and optionally
# ``requires`` (extra invariant the orchestrator must check beyond the
# actor identity).
TRANSITIONS: dict[State, dict[State, dict[str, str]]] = {
    State.OPEN: {
        State.ADDRESSED: {"actor": "addressee"},
        State.WITHDRAWN: {"actor": "raiser"},
    },
    State.ADDRESSED: {
        State.RESOLVED: {"actor": "raiser"},
        State.OPEN: {"actor": "raiser"},  # raiser counter-argues
        State.WITHDRAWN: {"actor": "raiser"},
        State.ACKNOWLEDGED: {
            "actor": "mutual",
            "requires": "ack-from-both-in-consecutive-turns",
        },
    },
    # capped is orchestrator-only; reachable from any non-terminal state
    # at hard-cap or ghost-cap time. Modeled separately via ``CAPPED_VIA``
    # rather than in this table because the actor is never an agent.
}


# Tags used on the ``via:`` field of a ``capped`` transition record. The
# orchestrator picks one based on which trigger fired.
CAPPED_VIA: dict[str, str] = {
    "hard_cap": "Hard cap reached for the phase",
    "ghost_cap": "Closeout budget exhausted; non-terminal items auto-capped",
}


def is_valid_transition(from_state: State, to_state: State, *, actor: str) -> bool:
    """Check whether ``actor`` can trigger ``from_state → to_state``.

    ``actor`` is one of ``"raiser"`` / ``"addressee"`` / ``"mutual"`` /
    ``"orchestrator"``. Orchestrator transitions to ``capped`` are always
    allowed from any non-terminal state (handled outside the table).
    """
    if actor == "orchestrator" and to_state == State.CAPPED:
        return not is_terminal(from_state)
    spec = TRANSITIONS.get(from_state, {}).get(to_state)
    if spec is None:
        return False
    expected_actor = spec["actor"]
    # mutual requires the orchestrator's post-round handshake check; the
    # agent-side transition request carries actor=="raiser" or
    # "addressee" but the resulting state flip only fires when the
    # orchestrator sees the second half of the handshake. For validation
    # purposes we accept either raiser or addressee as actor when the
    # target is mutual-required.
    if expected_actor == "mutual":
        return actor in {"raiser", "addressee"}
    return actor == expected_actor
