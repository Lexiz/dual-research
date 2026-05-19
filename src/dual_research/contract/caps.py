"""Spec 0114 — soft / hard caps per phase + closeout budget defaults.

The hard cap is the actual ceiling; reaching it auto-caps any remaining
non-terminal items via ``hard_cap`` and converges the phase. The soft
cap is signal-only (``SoftCapHit`` event) used for UI / logging.

Closeout budget defaults are per-phase, per-agent. Each failed closeout
round (the agent did not bring all their non-terminal items to a
terminal state) decrements the budget by 1. At budget=0 the next failed
closeout round triggers a ghost-cap auto-flip on the agent's remaining
non-terminal items.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseCaps:
    soft: int
    hard: int
    closeout_budget: int


# Phase token (matches ``contract.categories.PHASE_TOKEN`` values) to
# ``PhaseCaps`` mapping. Phase 1 and 3 are production phases and have
# no cap.
PHASE_CAPS: dict[int, PhaseCaps] = {
    0: PhaseCaps(soft=2, hard=4, closeout_budget=2),
    2: PhaseCaps(soft=4, hard=8, closeout_budget=2),
    4: PhaseCaps(soft=4, hard=8, closeout_budget=2),
}


def caps_for(phase: int) -> PhaseCaps:
    """Return the ``PhaseCaps`` for ``phase``. Raises on invalid phase."""
    try:
        return PHASE_CAPS[phase]
    except KeyError as exc:
        raise ValueError(f"phase {phase} has no caps") from exc
