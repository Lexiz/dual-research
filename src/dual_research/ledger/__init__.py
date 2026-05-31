"""Spec 0043 — authoritative cross-round ledger.

The ledger maintains a programmatic record of every claim / question /
disagreement / issue / comment raised across a phase's rounds, derived
from the existing parsed sections in each turn file. **No new agent
output is required** — agents keep writing the same `## Open questions
for X`, `## Substantive disagreements I'm holding`, `## Issue ledger`,
`## Answers to:`, `## Resolved or non-blocking differences` sections
they write today. The ledger reads them.

Why: prior to this spec the system trusted agent self-counters
(``OPEN_QUESTIONS: 0`` etc.) as the sole convergence signal. The
ledger gives the system an independent count to cross-check against,
closing a class of silent-ghosting failure modes. It also gives the
LLM structured prior-state as input via the ``## Standing items from
prior rounds`` section the orchestrator injects into round-N (N≥2)
prompts.

Public surface:
- ``LedgerEntry``, ``LedgerState``, ``LedgerDrift`` — dataclasses
- ``build_phase_ledger(session_dir, phase)`` — derives the ledger

Kill-switch: set ``DR_LEDGER_MODE=legacy`` in the environment to fall
back to self-counter-only convergence. The ledger is still BUILT (UI
uses it) but doesn't affect orchestrator behaviour. Default is
``enforce``.

Spec 0257.1 removed the dead legacy LLM-facing prompt surface
(``build_standing_items_section`` / ``build_blocked_convergence_warning``,
formerly ``ledger/prompt.py``). The live role-aware standing-items
surface is ``deep_research.format_role_aware_standing_items``, rendered
off the contract ``LedgerEntryV2`` state machine.
"""

from __future__ import annotations

import os

from dual_research.ledger.build import build_phase_ledger
from dual_research.ledger.models import (
    CLAIM_STATUSES,
    COMMENT_STATUSES,
    DISAGREEMENT_STATUSES,
    ISSUE_STATUSES,
    QUESTION_STATUSES,
    LedgerDrift,
    LedgerEntry,
    LedgerState,
    LedgerStatusTransition,
)
__all__ = (
    "LedgerEntry",
    "LedgerState",
    "LedgerStatusTransition",
    "LedgerDrift",
    "QUESTION_STATUSES",
    "DISAGREEMENT_STATUSES",
    "CLAIM_STATUSES",
    "ISSUE_STATUSES",
    "COMMENT_STATUSES",
    "build_phase_ledger",
    "ledger_mode",
)


def ledger_mode() -> str:
    """Return ``"enforce"`` or ``"legacy"`` from the env. Default
    enforce. Anything other than ``"legacy"`` (case-insensitive) is
    treated as enforce.
    """
    val = (os.environ.get("DR_LEDGER_MODE") or "enforce").strip().lower()
    return "legacy" if val == "legacy" else "enforce"
