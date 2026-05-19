"""Spec 0114 — closeout mechanism (replaces ``repair.py`` for the new protocol).

Closeout is the new convergence-cleanup mechanism: when both agents emit
``STATUS: AGREED`` in the same round but the ledger still carries
non-terminal items, the orchestrator urges a "closeout round" — each
agent's next prompt is restricted to closing operations (RESOLVE,
ACKNOWLEDGE, WITHDRAW, counter-argument). RAISE blocks are silently
dropped by the parser and recorded as ``CloseoutViolation`` events.

Each agent has a closeout budget per phase (default 2 from
``contract.caps``). Each failed closeout round decrements the budget by
1. When an agent's budget reaches 0 and a subsequent closeout round
still leaves their items non-terminal, those items auto-flip to
``capped`` with ``via: ghost_cap``.

The functions here are stateless utilities; the per-run state lives on
the ``CloseoutTracker`` dataclass owned by the orchestrator (parallel
to ``repair.RepairTracker``). Both trackers coexist during the
migration — the new protocol uses closeout, the legacy protocol uses
repair, neither knows about the other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from dual_research.contract.caps import caps_for
from dual_research.contract.lifecycle import State, is_terminal
from dual_research.contract.operations import RaiseBlock
from dual_research.contract.validator import (
    ValidationResult,
    validate_parsed,
)
from dual_research.events import CloseoutViolation
from dual_research.protocol.parse_v2 import ParsedTurnV2


# ─── Closeout tracker ─────────────────────────────────────────────────


@dataclass
class CloseoutTracker:
    """Per-phase, per-agent closeout budget state.

    ``budget`` defaults from ``contract.caps.caps_for(phase).closeout_budget``
    when the agent is first ``_ensure``-touched. ``decrement_on_fail``
    burns one slot when a closeout round failed to bring all of the
    agent's items to terminal state.
    """

    phase: int
    initial_budget: int = 2
    budget: dict[str, int] = field(default_factory=dict)
    closeout_rounds_used: dict[str, int] = field(default_factory=dict)

    def _ensure(self, agent: str) -> None:
        if agent not in self.budget:
            self.budget[agent] = self.initial_budget
        if agent not in self.closeout_rounds_used:
            self.closeout_rounds_used[agent] = 0

    def remaining(self, agent: str) -> int:
        self._ensure(agent)
        return self.budget[agent]

    def has_budget(self, agent: str) -> bool:
        return self.remaining(agent) > 0

    def decrement_on_fail(self, agent: str) -> int:
        """Spend one slot when a closeout round failed for ``agent``."""
        self._ensure(agent)
        self.budget[agent] = max(0, self.budget[agent] - 1)
        self.closeout_rounds_used[agent] += 1
        return self.budget[agent]

    @classmethod
    def for_phase(cls, phase: int) -> "CloseoutTracker":
        """Build a fresh tracker pre-loaded with the phase's default budget."""
        return cls(phase=phase, initial_budget=caps_for(phase).closeout_budget)


# ─── Closeout-round helpers ───────────────────────────────────────────


# A LedgerEntry-like shape the orchestrator passes into helpers below.
# Kept structural (just the fields we read) so callers can pass any
# dataclass or dict-like object with these attributes.
@dataclass(frozen=True)
class _ItemView:
    id: str
    raiser: str            # "claude" | "openai"
    current_state: str     # State enum value


def items_blocking_convergence(items: list[_ItemView]) -> list[_ItemView]:
    """Return items whose state is non-terminal (block phase convergence)."""
    return [it for it in items if not is_terminal(it.current_state)]


def should_urge_closeout(
    *,
    claude_status: str | None,
    openai_status: str | None,
    items: list[_ItemView],
) -> bool:
    """``True`` iff both agents AGREED this round AND there are still
    non-terminal items in the ledger.

    Per spec 0114: closeout fires when convergence is *attempted* (both
    AGREED) but blocked by non-terminal items.
    """
    if claude_status != "AGREED" or openai_status != "AGREED":
        return False
    return len(items_blocking_convergence(items)) > 0


def select_ghost_cap_items(
    *,
    agent: str,
    items: list[_ItemView],
) -> list[_ItemView]:
    """Return ``agent``'s non-terminal items eligible for ghost-cap.

    Called by the orchestrator when ``agent`` has exhausted its closeout
    budget and a subsequent closeout round still left their items
    non-terminal. The orchestrator transitions each returned item to
    ``capped`` with ``via: ghost_cap`` and an orchestrator-generated
    rationale.
    """
    return [
        it
        for it in items
        if it.raiser == agent and not is_terminal(it.current_state)
    ]


def ghost_cap_reason(agent: str, *, round: int, budget_used: int) -> str:
    """Canonical orchestrator-generated rationale for a ghost-cap transition."""
    return (
        f"Agent {agent} exhausted closeout budget ({budget_used} closeout "
        f"rounds) without bringing this item to a terminal state; "
        f"auto-capped at round {round}."
    )


def hard_cap_reason(phase: int, *, round: int) -> str:
    """Canonical orchestrator-generated rationale for a hard-cap transition."""
    return (
        f"Hard cap reached for phase {phase} at round {round}; item was not "
        f"brought to a terminal state by either agent before the ceiling."
    )


# ─── parse_with_closeout ──────────────────────────────────────────────


# The parser is injected as a callable so closeout.py stays independent
# of the parser implementation. The orchestrator wires in
# ``protocol.parse.parse_turn_v2`` in step 6.
ParserFn = Callable[[str], ParsedTurnV2]


@dataclass(frozen=True)
class CloseoutParseResult:
    """Bundle returned by ``parse_with_closeout``.

    - ``parsed``       : the typed parser output (RAISE blocks already
                         filtered out when ``is_closeout_round`` was true).
    - ``validation``   : the validator's ``ValidationResult``.
    - ``violations``   : ``CloseoutViolation`` events for every dropped
                         RAISE block (empty when not a closeout round).
    - ``dropped_count``: number of RAISE blocks dropped this turn.
    """

    parsed: ParsedTurnV2
    validation: ValidationResult
    violations: list[CloseoutViolation] = field(default_factory=list)
    dropped_count: int = 0


def parse_with_closeout(
    text: str,
    *,
    phase: int,
    round: int,
    agent: str,
    parser: ParserFn,
    is_closeout_round: bool = False,
) -> CloseoutParseResult:
    """Parse + validate a new-protocol turn with closeout-round semantics.

    In a closeout round:
    - RAISE blocks are silently filtered out of the parsed result.
    - One ``CloseoutViolation`` event is produced per dropped block.
    - The validator runs in closeout-aware mode so RAISE blocks (if the
      parser already returned them and we filter here) downgrade to
      ``warning`` rather than rejecting the turn.

    In a non-closeout round this function is equivalent to "parse +
    validate".
    """
    parsed = parser(text)

    violations: list[CloseoutViolation] = []
    dropped = 0

    if is_closeout_round:
        kept_blocks = []
        for block in parsed.blocks:
            if isinstance(block, RaiseBlock):
                dropped += 1
                violations.append(CloseoutViolation(
                    phase=phase,
                    round=round,
                    agent=agent,
                    violation_code="closeout_violation_raise",
                    dropped_block=block.raw_text[:1000],
                ))
                continue
            kept_blocks.append(block)
        if dropped:
            # Rebuild the parsed turn with RAISE blocks removed.
            parsed = ParsedTurnV2(
                status=parsed.status,
                blocks=kept_blocks,
                raised_this_turn=[],
                addressed_this_turn=parsed.addressed_this_turn,
                resolved_this_turn=parsed.resolved_this_turn,
                acknowledged_this_turn=parsed.acknowledged_this_turn,
                withdrawn_this_turn=parsed.withdrawn_this_turn,
                counters=parsed.counters,
                phase_artifact=parsed.phase_artifact,
                revised_draft=parsed.revised_draft,
                stance=parsed.stance,
            )

    validation = validate_parsed(
        text=text,
        blocks=parsed.blocks,
        phase=phase,
        round=round,
        agent=agent,
        is_closeout_round=is_closeout_round,
    )

    return CloseoutParseResult(
        parsed=parsed,
        validation=validation,
        violations=violations,
        dropped_count=dropped,
    )


# ─── Convergence cross-check ──────────────────────────────────────────


@dataclass(frozen=True)
class ConvergenceCheck:
    """Result of the three-condition convergence check.

    ``converged`` is true only when all three fields below are true.
    The fields are surfaced individually so the orchestrator can log
    which gate failed.
    """

    both_agreed: bool
    all_items_terminal: bool
    artifact_hash_matched: bool

    @property
    def converged(self) -> bool:
        return self.both_agreed and self.all_items_terminal and self.artifact_hash_matched


def check_convergence(
    *,
    claude_status: str | None,
    openai_status: str | None,
    items: list[_ItemView],
    artifact_hash_match: bool,
) -> ConvergenceCheck:
    """Three-condition convergence cross-check (spec 0114 § Convergence rules).

    All three must hold in the same round for the phase to converge:
    1. Both agents emit ``STATUS: AGREED``.
    2. The ledger has zero non-terminal items.
    3. The phase artifact hash-matches across both agents (caller
       computes the hash match and passes it in).
    """
    return ConvergenceCheck(
        both_agreed=(claude_status == "AGREED" and openai_status == "AGREED"),
        all_items_terminal=len(items_blocking_convergence(items)) == 0,
        artifact_hash_matched=artifact_hash_match,
    )


# ─── Re-exports for convenience ───────────────────────────────────────

__all__ = [
    "CloseoutParseResult",
    "CloseoutTracker",
    "ConvergenceCheck",
    "ParserFn",
    "_ItemView",
    "check_convergence",
    "ghost_cap_reason",
    "hard_cap_reason",
    "items_blocking_convergence",
    "parse_with_closeout",
    "select_ghost_cap_items",
    "should_urge_closeout",
]
