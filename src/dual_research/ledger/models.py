"""Spec 0043 — ledger dataclasses + status enums."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# Per-kind status vocabularies. Kept as plain tuples so callers can
# validate without importing Literal from typing in hot paths.
QUESTION_STATUSES = ("open", "answered", "withdrawn")
DISAGREEMENT_STATUSES = ("open", "resolved", "final_surfaced")
CLAIM_STATUSES = ("open", "escalated", "withdrawn")
ISSUE_STATUSES = ("open", "fixed", "non_blocking")
COMMENT_STATUSES = ("noted",)


LedgerKind = Literal["question", "disagreement", "claim", "issue", "comment"]


@dataclass
class LedgerStatusTransition:
    """One state-change event for a LedgerEntry.

    Captured each time the ledger flips an entry's status as it walks
    forward through the turn files. ``reason`` is a short
    human-readable explanation (e.g. "answered in phase2_round3_gpt's
    ## Answers to: section"). ``turn_key`` identifies the turn that
    triggered the transition for cross-axis click-to-highlight in the
    UI.
    """

    round: int
    status: str
    reason: str
    turn_key: str


@dataclass
class LedgerEntry:
    """One tracked item across rounds within a single phase.

    Cross-round identity is via ``id``:
    - ``question`` items: parser-assigned ``Q-{initial}-r{round}-{idx}``.
      Cross-round answer linkage flows through ``status_history``.
    - ``disagreement`` items: agent-maintained ``D-N`` (stable across
      rounds).
    - ``claim`` items: parser-assigned ``Cl-{initial}-{p1|r{N}}-{idx}``.
      Linkage to a later-round disagreement happens via the ``D-N``
      suffix matched against substantive-disagreement section content
      — when matched, the claim's status flips to ``escalated`` and
      the new disagreement enters as its own entry.
    - ``issue`` items: agent-maintained (``OAI-N`` / ``C-N``); the
      ledger preserves the raiser's ID convention.
    - ``comment`` items: parser-assigned per turn; status is always
      terminal ``noted``.
    """

    id: str
    kind: str  # one of QUESTION_STATUSES.keys etc — validated at construction by builder
    raised_round: int               # 0 for Phase 1 plan-draft items
    raised_by: str                  # "claude" | "gpt"
    raised_turn_key: str            # phase1_<agent> / phase{N}_round{R}_<agent>
    current_status: str
    status_history: list[LedgerStatusTransition] = field(default_factory=list)
    body_snippet: str = ""          # first ~120 chars of body, trailing "…" when truncated
    last_addressed_round: int | None = None
    ghosted_rounds: int = 0         # accumulated rounds open with no addressing signal

    def is_open(self) -> bool:
        """``True`` iff the current status is one of the kind's open
        states. Used by convergence + UI.
        """
        return self.current_status == "open"


@dataclass
class LedgerState:
    """Per-phase ledger snapshot.

    ``entries`` is the ordered list of tracked items in the phase, in
    insertion order (first raised first). ``phase`` is 2 or 4 (Phase 1
    is one-shot and produces claims that flow into the Phase 2 ledger
    as ``raised_round=0`` entries — there's no separate Phase 1
    ledger).
    """

    phase: int
    entries: list[LedgerEntry] = field(default_factory=list)

    # ─── Open-set queries used by convergence ──────────────────────

    def open_count(self, *, kind: str | None = None) -> int:
        """Count entries with ``current_status == "open"``.

        ``kind`` filter is optional; when ``None`` returns the total
        open across all kinds.
        """
        if kind is None:
            return sum(1 for e in self.entries if e.is_open())
        return sum(1 for e in self.entries if e.is_open() and e.kind == kind)

    def open_entries(self, *, kind: str | None = None) -> list[LedgerEntry]:
        if kind is None:
            return [e for e in self.entries if e.is_open()]
        return [e for e in self.entries if e.is_open() and e.kind == kind]

    def find_by_id(self, entry_id: str) -> LedgerEntry | None:
        for e in self.entries:
            if e.id == entry_id:
                return e
        return None


@dataclass
class LedgerDrift:
    """One mismatch between an agent's self-reported counter and the
    ledger's count for the same (turn, kind) — spec 0043 D8.

    Emitted at aggregator-load time; surfaced in the UI as a small
    ``⚠ drift`` badge on the turn card. The drift signal does NOT
    block convergence on its own — that's D7's ledger cross-check
    (which uses ``LedgerState.open_count`` directly).
    """

    turn_key: str
    kind: str                       # "question" | "disagreement" | "issue"
    agent_count: int                # the self-reported value
    ledger_count: int               # what the ledger counted for that turn
    severity: Literal["info", "warn"] = "warn"
