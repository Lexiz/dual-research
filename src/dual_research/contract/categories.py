"""Spec 0114 — canonical category vocabulary.

Four item kinds (``question``, ``disagreement``, ``issue``, ``comment``)
shared across every interaction phase that allows raising. Phases differ
only in which categories they admit, not in the vocabulary itself.

The legacy ``claim`` kind is gone — the new prompts never ask for it.
"""

from __future__ import annotations

from enum import StrEnum


class Category(StrEnum):
    QUESTION = "question"
    DISAGREEMENT = "disagreement"
    ISSUE = "issue"
    COMMENT = "comment"


# Single-letter token used as the first segment in a stable item ID.
ID_TOKEN: dict[Category, str] = {
    Category.QUESTION: "Q",
    Category.DISAGREEMENT: "D",
    Category.ISSUE: "I",
    Category.COMMENT: "C",
}

# Inverse: ID-token letter → Category.
TOKEN_TO_CATEGORY: dict[str, Category] = {v: k for k, v in ID_TOKEN.items()}


# Phase-token segment in stable IDs. Phase 1 and 3 don't raise items and
# have no token. Keys are integer phase numbers (0/2/4).
PHASE_TOKEN: dict[int, str] = {
    0: "input",
    2: "plan",
    4: "review",
}

# Inverse: phase-token → integer phase number.
TOKEN_TO_PHASE: dict[str, int] = {v: k for k, v in PHASE_TOKEN.items()}


# Per-phase allow-set: which categories can be raised in which phase.
RAISABLE_IN: dict[int, frozenset[Category]] = {
    0: frozenset({Category.QUESTION, Category.DISAGREEMENT}),
    2: frozenset({Category.QUESTION, Category.DISAGREEMENT}),
    4: frozenset({
        Category.QUESTION,
        Category.DISAGREEMENT,
        Category.ISSUE,
        Category.COMMENT,
    }),
}


# Category-level guidance for the per-item evidence_required flag. The
# agent decides per-item; this table is only used in prompt construction
# as a hint.
TYPICAL_EVIDENCE_REQUIRED: dict[Category, bool] = {
    Category.QUESTION: True,
    Category.DISAGREEMENT: True,
    Category.ISSUE: False,
    Category.COMMENT: False,
}


def is_raisable(category: Category, phase: int) -> bool:
    """``True`` iff ``category`` is allowed to be raised in ``phase``."""
    return category in RAISABLE_IN.get(phase, frozenset())
