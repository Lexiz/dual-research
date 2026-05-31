"""Phase 2 outcome contract.

Spec 0257.1 deleted the dead legacy ``run_phase2`` runner that used to
live here. It had been unreachable from the live entry point since the
spec-0118 v2 rewrite — the active Phase 2 driver is
``dr_run.run_dr_phase2`` (via ``_drive_interaction_phase``). Only the
``Phase2Outcome`` dataclass is preserved: it remains the finalize-layer
contract still imported by ``dr_run.py``, ``run.py``, and
``finalize.py``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Phase2Outcome:
    converged: bool
    rounds: int
    drafter: str | None
    agreed_plan: str | None
    fsd_count: int
    via_tiebreak: bool
    hard_capped: bool
    parse_failure: bool = False
    parse_failure_agent: str | None = None
    last_claude_text: str | None = None
    last_openai_text: str | None = None
