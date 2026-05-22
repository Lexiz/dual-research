"""Spec 0114 — Deep Research contract module.

Single source of truth for category vocabulary, lifecycle states,
stable ID format, section / counter regexes, operation block schemas,
evidence anti-hallucination rules, phase artifact templates / hashing,
per-phase caps + closeout budgets, status vocabulary, and the turn
validator.

Prompts, parser, validator, orchestrator, persistence, and downstream
UI all import from this module. No duplicated string literals — the
module is the canonical home for every constant that the rest of the
system reads from.
"""

from __future__ import annotations

from dual_research.contract.artifacts import (
    AGREED_DRAFT_ACCEPTANCE_TEMPLATE,
    AGREED_INTERPRETATION_TEMPLATE,
    AGREED_PLAN_TEMPLATE,
    ARTIFACT_HEADING,
    canonical_hash,
    hash_draft_content,
)
from dual_research.contract.caps import PHASE_CAPS, PhaseCaps, caps_for
from dual_research.contract.categories import (
    ID_TOKEN,
    PHASE_TOKEN,
    RAISABLE_IN,
    TOKEN_TO_CATEGORY,
    TOKEN_TO_PHASE,
    TYPICAL_EVIDENCE_REQUIRED,
    Category,
    is_raisable,
)
from dual_research.contract.evidence import (
    MAX_CONTENT_EXCERPT_CHARS,
    MIN_CONTENT_EXCERPT_CHARS,
    EvidenceFlag,
    EvidenceRecord,
    validate_all_evidence,
    validate_evidence,
)
from dual_research.contract.ids import (
    AGENT_TO_RAISER,
    ID_PATTERN,
    RAISER_TO_AGENT,
    agent_name,
    format_id,
    is_well_formed,
    parse_id,
    raiser_letter,
)
from dual_research.contract.lifecycle import (
    CAPPED_VIA,
    TERMINAL_STATES,
    TRANSITIONS,
    State,
    is_terminal,
    is_valid_transition,
)
from dual_research.contract.operations import (
    AcknowledgeBlock,
    AddressBlock,
    OperationBlock,
    ParseError,
    RaiseBlock,
    RequestEvidenceBlock,
    ResolveBlock,
    WithdrawBlock,
)
from dual_research.contract.status import (
    ACTION_ARRAYS,
    TurnStatus,
    counter_field_for,
    counter_fields_for_phase,
)
from dual_research.contract.validator import (
    ValidationError,
    ValidationResult,
    validate_parsed,
    validate_turn,
)

__all__ = [
    # categories
    "Category",
    "ID_TOKEN",
    "PHASE_TOKEN",
    "RAISABLE_IN",
    "TOKEN_TO_CATEGORY",
    "TOKEN_TO_PHASE",
    "TYPICAL_EVIDENCE_REQUIRED",
    "is_raisable",
    # lifecycle
    "CAPPED_VIA",
    "State",
    "TERMINAL_STATES",
    "TRANSITIONS",
    "is_terminal",
    "is_valid_transition",
    # ids
    "AGENT_TO_RAISER",
    "ID_PATTERN",
    "RAISER_TO_AGENT",
    "agent_name",
    "format_id",
    "is_well_formed",
    "parse_id",
    "raiser_letter",
    # operations
    "AcknowledgeBlock",
    "AddressBlock",
    "OperationBlock",
    "ParseError",
    "RaiseBlock",
    "RequestEvidenceBlock",
    "ResolveBlock",
    "WithdrawBlock",
    # evidence
    "EvidenceFlag",
    "EvidenceRecord",
    "MAX_CONTENT_EXCERPT_CHARS",
    "MIN_CONTENT_EXCERPT_CHARS",
    "validate_all_evidence",
    "validate_evidence",
    # artifacts
    "AGREED_DRAFT_ACCEPTANCE_TEMPLATE",
    "AGREED_INTERPRETATION_TEMPLATE",
    "AGREED_PLAN_TEMPLATE",
    "ARTIFACT_HEADING",
    "canonical_hash",
    "hash_draft_content",
    # caps
    "PHASE_CAPS",
    "PhaseCaps",
    "caps_for",
    # status
    "ACTION_ARRAYS",
    "TurnStatus",
    "counter_field_for",
    "counter_fields_for_phase",
    # validator
    "ValidationError",
    "ValidationResult",
    "validate_parsed",
    "validate_turn",
]
