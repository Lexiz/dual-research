"""Spec 0114 — backward-compatibility shim for legacy event payloads.

The orchestrator emits the new ``ItemRaised`` / ``ItemTransitioned`` /
``CloseoutUrged`` / ``PhaseConverged`` events as the canonical record of
the lifecycle. The legacy UI consumes the older ``Phase0Complete`` /
``Phase2RoundComplete`` / ``Phase4RoundComplete`` payloads with their
historic counter fields. The shim bridges the two: given a snapshot of
the ledger (the typed lifecycle entries at end-of-round), it produces
the legacy payload values that the existing UI expects.

The shim is removed in spec 0115 as part of the UI cutover.

The legacy payload fields mapped here:

- ``claude_brief_issues`` / ``openai_brief_issues`` ← count of
  open + addressed items raised by that agent in phase 0.
- ``claude_open_questions`` / ``openai_open_questions`` ← count of
  open + addressed *questions* raised by that agent in phase 2.
- ``claude_blocking`` / ``openai_blocking`` ← count of *open*
  *disagreements* raised by that agent in phase 2.
- ``claude_fsd`` / ``openai_fsd`` ← count of *acknowledged*
  *disagreements* raised by that agent in phase 2 (the new model's
  analogue of "final-surfaced disagreements").
- ``claude_open_issues`` / ``openai_open_issues`` ← count of *open*
  *plus addressed* items (any category) in phase 4.
"""

from __future__ import annotations

from dataclasses import dataclass

from dual_research.contract.categories import Category
from dual_research.contract.lifecycle import State


@dataclass(frozen=True)
class LedgerSnapshotEntry:
    """One ledger entry as seen by the shim.

    The shim does not care about transition history or rationales —
    only the (kind, raiser, current_state) triple per item.
    """

    item_id: str
    kind: str            # "question" | "disagreement" | "issue" | "comment"
    raiser: str          # "claude" | "openai"
    current_state: str   # "open" | "addressed" | "resolved" | …


def _matches(
    entry: LedgerSnapshotEntry,
    *,
    raiser: str,
    kinds: set[str] | None = None,
    states: set[str] | None = None,
) -> bool:
    if entry.raiser != raiser:
        return False
    if kinds is not None and entry.kind not in kinds:
        return False
    if states is not None and entry.current_state not in states:
        return False
    return True


def phase0_complete_legacy_fields(
    ledger: list[LedgerSnapshotEntry],
    *,
    claude_status: str | None,
    openai_status: str | None,
    brief_needs_input: bool = False,
) -> dict:
    """Build the kwargs for a legacy ``Phase0Complete`` event.

    ``claude_brief_issues`` / ``openai_brief_issues`` are computed as
    the number of open + addressed items (any kind) raised by each
    agent. Pre-0114 the brief-issues counter was self-reported by the
    agent; the shim derives it from the ledger instead.
    """
    non_terminal = {State.OPEN, State.ADDRESSED}
    claude_count = sum(
        1 for e in ledger
        if _matches(e, raiser="claude", states={s.value for s in non_terminal})
    )
    openai_count = sum(
        1 for e in ledger
        if _matches(e, raiser="openai", states={s.value for s in non_terminal})
    )
    return {
        "claude_status": claude_status,
        "openai_status": openai_status,
        "claude_brief_issues": claude_count,
        "openai_brief_issues": openai_count,
        "brief_needs_input": brief_needs_input,
    }


def phase2_round_complete_legacy_fields(
    ledger: list[LedgerSnapshotEntry],
    *,
    round: int,
    agreed: bool,
    claude_status: str | None,
    openai_status: str | None,
    claude_drafter: str | None = None,
    openai_drafter: str | None = None,
) -> dict:
    """Build the kwargs for a legacy ``Phase2RoundComplete`` event."""
    questions = Category.QUESTION.value
    disagreements = Category.DISAGREEMENT.value

    non_terminal_states = {State.OPEN.value, State.ADDRESSED.value}

    claude_open_questions = sum(
        1 for e in ledger
        if _matches(e, raiser="claude", kinds={questions}, states=non_terminal_states)
    )
    openai_open_questions = sum(
        1 for e in ledger
        if _matches(e, raiser="openai", kinds={questions}, states=non_terminal_states)
    )

    claude_blocking = sum(
        1 for e in ledger
        if _matches(e, raiser="claude", kinds={disagreements}, states={State.OPEN.value})
    )
    openai_blocking = sum(
        1 for e in ledger
        if _matches(e, raiser="openai", kinds={disagreements}, states={State.OPEN.value})
    )

    claude_fsd = sum(
        1 for e in ledger
        if _matches(
            e, raiser="claude", kinds={disagreements},
            states={State.ACKNOWLEDGED.value},
        )
    )
    openai_fsd = sum(
        1 for e in ledger
        if _matches(
            e, raiser="openai", kinds={disagreements},
            states={State.ACKNOWLEDGED.value},
        )
    )

    return {
        "round": round,
        "agreed": agreed,
        "claude_status": claude_status,
        "openai_status": openai_status,
        "claude_drafter": claude_drafter,
        "openai_drafter": openai_drafter,
        "claude_open_questions": claude_open_questions,
        "openai_open_questions": openai_open_questions,
        "claude_blocking": claude_blocking,
        "openai_blocking": openai_blocking,
        "claude_fsd": claude_fsd,
        "openai_fsd": openai_fsd,
    }


def phase4_round_complete_legacy_fields(
    ledger: list[LedgerSnapshotEntry],
    *,
    round: int,
    approved: bool,
    claude_status: str | None,
    openai_status: str | None,
    draft_round: int,
) -> dict:
    """Build the kwargs for a legacy ``Phase4RoundComplete`` event.

    ``claude_open_issues`` / ``openai_open_issues`` mirror today's
    conflated count: every open + addressed phase-4 item (any
    category) raised by that agent. The pre-0114 UI does not
    distinguish issue / comment / question / disagreement breakdowns
    on the timeline card.
    """
    non_terminal_states = {State.OPEN.value, State.ADDRESSED.value}
    claude_open = sum(
        1 for e in ledger
        if _matches(e, raiser="claude", states=non_terminal_states)
    )
    openai_open = sum(
        1 for e in ledger
        if _matches(e, raiser="openai", states=non_terminal_states)
    )
    return {
        "round": round,
        "approved": approved,
        "claude_status": claude_status,
        "openai_status": openai_status,
        "claude_open_issues": claude_open,
        "openai_open_issues": openai_open,
        "draft_round": draft_round,
    }


def phase2_complete_legacy_fields(
    ledger: list[LedgerSnapshotEntry],
    *,
    rounds: int,
    converged: bool,
    drafter: str | None,
    via_hard_cap: bool = False,
    via_ghost_cap: bool = False,
    via_closeout: bool = False,
) -> dict:
    """Build the kwargs for a legacy ``Phase2Complete`` event."""
    disagreements = Category.DISAGREEMENT.value
    fsd_count = sum(
        1 for e in ledger
        if e.kind == disagreements and e.current_state == State.ACKNOWLEDGED.value
    )
    return {
        "rounds": rounds,
        "converged": converged,
        "drafter": drafter,
        "fsd_count": fsd_count,
        # Legacy semantics: ``via_tiebreak`` fires when the drafter was
        # picked by orchestrator tiebreak rather than agreement. In the
        # new protocol this maps to the simpler tiebreak path. The
        # shim sets it to False by default; callers can override.
        "via_tiebreak": False,
        "via_canonical_promotion": False,
        "via_canonical_fsd_synthesis": False,
        "via_stuck_agreed": False,
    }


def phase4_complete_legacy_fields(
    *,
    rounds: int,
    approved: bool,
    final_draft_round: int,
    revisions: int,
) -> dict:
    """Build the kwargs for a legacy ``Phase4Complete`` event.

    ``via_stuck_agreed`` is always False in the new protocol — the
    stuck-AGREED escape valve is removed.
    """
    return {
        "rounds": rounds,
        "approved": approved,
        "final_draft_round": final_draft_round,
        "revisions": revisions,
        "via_stuck_agreed": False,
    }
