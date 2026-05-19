"""Spec 0114 — STATUS enum + per-phase counter field names.

The new protocol has only two STATUS values across every interaction
phase: ``IN_PROGRESS`` and ``AGREED``. The legacy values
(``NEGOTIATING`` / ``REVIEWING`` / ``APPROVED`` / ``BRIEF_OK`` /
``BRIEF_NEEDS_INPUT``) are removed from the prompt vocabulary.

Per-phase counter names diverge only on whether ``OPEN_ISSUES`` /
``OPEN_COMMENTS`` appear (review-draft only). The orchestrator derives
all per-kind, per-raiser breakdowns from the action-array IDs; the
agent does not break these down themselves.
"""

from __future__ import annotations

from enum import StrEnum

from dual_research.contract.categories import Category


class TurnStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    AGREED = "AGREED"


# Counters that always appear in the status footer of an interaction
# turn, regardless of phase.
_ALWAYS_COUNTERS: tuple[str, ...] = (
    "OPEN_QUESTIONS",
    "OPEN_DISAGREEMENTS",
    "ADDRESSED_QUESTIONS",
    "ADDRESSED_DISAGREEMENTS",
)

# Counters that appear only in review-draft (phase 4).
_REVIEW_ONLY_COUNTERS: tuple[str, ...] = (
    "OPEN_ISSUES",
    "OPEN_COMMENTS",
    "ADDRESSED_ISSUES",
    "ADDRESSED_COMMENTS",
)

# Per-phase action arrays (always present in every interaction-phase
# turn).
ACTION_ARRAYS: tuple[str, ...] = (
    "RAISED_THIS_TURN",
    "ADDRESSED_THIS_TURN",
    "RESOLVED_THIS_TURN",
    "ACKNOWLEDGED_THIS_TURN",
    "WITHDRAWN_THIS_TURN",
)


def counter_fields_for_phase(phase: int) -> tuple[str, ...]:
    """Return the counter-field names that should appear for ``phase``."""
    base = list(_ALWAYS_COUNTERS)
    if phase == 4:
        base.extend(_REVIEW_ONLY_COUNTERS)
    return tuple(base)


def counter_field_for(*, kind: Category, state: str) -> str | None:
    """Return the counter-field name for ``(kind, state)`` or ``None``.

    ``state`` is one of ``"open"`` / ``"addressed"`` (the only two states
    surfaced as counters). Returns ``None`` for kinds that have no
    counter in the spec (none currently).
    """
    if state not in {"open", "addressed"}:
        return None
    prefix = state.upper()
    suffix = {
        Category.QUESTION: "QUESTIONS",
        Category.DISAGREEMENT: "DISAGREEMENTS",
        Category.ISSUE: "ISSUES",
        Category.COMMENT: "COMMENTS",
    }[kind]
    return f"{prefix}_{suffix}"
