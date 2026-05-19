"""Spec 0114 — operation block schemas.

Five operation block types, each parsed into a typed dataclass:

- ``### RAISE``        → ``RaiseBlock``
- ``### ADDRESS <id>`` → ``AddressBlock``
- ``### RESOLVE <id>`` → ``ResolveBlock``
- ``### ACKNOWLEDGE``  → ``AcknowledgeBlock``
- ``### WITHDRAW <id>``→ ``WithdrawBlock``

The parser walks the markdown's ``### `` headings and dispatches to the
per-type extractors. Field parsing is YAML-style (``key: value`` for
scalars, ``key: |`` followed by an indented block for multi-line text).

Each block has a ``raw_text`` field carrying the original substring it
was parsed from — useful for diagnostic surfaces and the closeout
``closeout_violation`` event.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dual_research.contract.categories import Category
from dual_research.contract.evidence import EvidenceRecord


@dataclass(frozen=True)
class RaiseBlock:
    """A ``### RAISE`` block. Stable ID is stamped by the parser after
    parse — it is not present in the agent's emitted text.
    """

    kind: Category
    body: str
    anchor_type: str        # "quote" | "after" | "none"
    anchor_text: str        # verbatim span, heading text, or "" for none
    evidence_required: bool
    # Optional: blockquote "> quote: …" / "> after: …" line under the
    # block — captured for the UI's anchor side-by-side viewer, separate
    # from the structured ``anchor_text`` field. Either may be empty.
    blockquote_anchor: str = ""
    raw_text: str = ""


@dataclass(frozen=True)
class AddressBlock:
    """A ``### ADDRESS <item-id>`` block.

    ``proposes_status`` is one of:
    - ``"addressed"`` (default): standard response awaiting raiser ratification.
    - ``"acknowledged_proposed"``: addressee sees no path to resolution;
      proposes mutual acknowledge. Lifecycle flips to terminal
      ``acknowledged`` only if the raiser also emits an ACKNOWLEDGE for
      the same item in their next turn.

    ``evidence`` is a list of ``EvidenceRecord`` extracted from inline
    yaml-list-style entries or from sibling ``### EVIDENCE for <id>``
    blocks pointing at this item.
    """

    item_id: str
    response: str
    evidence: list[EvidenceRecord] = field(default_factory=list)
    proposes_status: str = "addressed"
    raw_text: str = ""


@dataclass(frozen=True)
class ResolveBlock:
    """A ``### RESOLVE <item-id>`` block. ``reason`` is required and
    must be non-trivial (length > 0 after strip).
    """

    item_id: str
    reason: str
    raw_text: str = ""


@dataclass(frozen=True)
class AcknowledgeBlock:
    """A ``### ACKNOWLEDGE <item-id>`` block.

    May appear in the ``## Addressing items raised against me`` section
    (proposing mutual acknowledge as an addressee) or in the
    ``## Ratifying my own items`` section (ratifying as the raiser).
    ``section`` records which context the parser found it in.
    """

    item_id: str
    reason: str
    section: str = "ratifying"  # "ratifying" | "addressing"
    raw_text: str = ""


@dataclass(frozen=True)
class WithdrawBlock:
    """A ``### WITHDRAW <item-id>`` block. Empty rationale is rejected."""

    item_id: str
    reason: str
    raw_text: str = ""


# Convenience alias — any operation block type.
OperationBlock = (
    RaiseBlock | AddressBlock | ResolveBlock | AcknowledgeBlock | WithdrawBlock
)


@dataclass(frozen=True)
class ParseError:
    """A single parse-time issue with an operation block.

    ``code`` is a stable identifier (e.g. ``"raise_missing_kind"``,
    ``"address_no_item_id"``, ``"evidence_event_id_fabricated"``);
    ``message`` is human-readable. ``raw_text`` carries the offending
    block substring when available.
    """

    code: str
    message: str
    raw_text: str = ""
    severity: str = "error"  # "error" | "warning"
