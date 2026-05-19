"""Spec 0114 — turn-level validator.

The validator is structure-only: it consumes a turn's raw text and
returns a ``ValidationResult`` of errors and warnings. The validator
does NOT know the ledger; it does not check whether the IDs in
operation blocks reference existing items. Ledger-aware checks (item
exists, current state allows the requested transition, mutual ack
handshake) live in the orchestrator after this validator passes.

The validator runs after the parser has assembled typed operation
blocks and pulled out the action arrays. ``validate_turn`` is a thin
top-level shim that the orchestrator can call without first parsing,
but the heavier ``validate_parsed`` accepts a pre-parsed structure for
the orchestrator's "validate after parse" flow.

Severity:
- ``error``    → the parser / orchestrator rejects the turn.
- ``warning``  → logged but the turn is accepted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dual_research.contract.categories import Category, is_raisable
from dual_research.contract.markers import (
    SECTION_ADDRESSING_RE,
    SECTION_NEW_ITEMS_RE,
    SECTION_PHASE_ARTIFACT_RE,
    SECTION_RATIFYING_RE,
    SECTION_STANCE_RE,
    SECTION_STATUS_RE,
    STATUS_RE,
)
from dual_research.contract.operations import (
    AcknowledgeBlock,
    AddressBlock,
    OperationBlock,
    RaiseBlock,
    ResolveBlock,
    WithdrawBlock,
)
from dual_research.contract.status import TurnStatus


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str
    severity: str = "error"  # "error" | "warning"


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)

    def with_error(self, error: ValidationError) -> "ValidationResult":
        return ValidationResult(
            valid=False if error.severity == "error" else self.valid,
            errors=[*self.errors, error],
        )


def _section_present(text: str, pattern) -> bool:
    return bool(pattern.search(text))


# ─── Structural-section gates ─────────────────────────────────────────


def _structural_errors(
    text: str,
    *,
    phase: int,
    round: int,
    is_closeout_round: bool,
) -> list[ValidationError]:
    errors: list[ValidationError] = []

    if not _section_present(text, SECTION_STANCE_RE):
        errors.append(ValidationError(
            code="missing_section_stance",
            message="turn is missing required `## Stance` section",
        ))
    # The Addressing and Ratifying sections are required in shape even
    # on round 1 (they may be empty; the spec's round-1 prompts put a
    # placeholder line under them). The parser tolerates empty bodies.
    if not _section_present(text, SECTION_ADDRESSING_RE):
        errors.append(ValidationError(
            code="missing_section_addressing",
            message=(
                "turn is missing required "
                "`## Addressing items raised against me` section"
            ),
        ))
    if not _section_present(text, SECTION_RATIFYING_RE):
        errors.append(ValidationError(
            code="missing_section_ratifying",
            message="turn is missing required `## Ratifying my own items` section",
        ))
    if not _section_present(text, SECTION_NEW_ITEMS_RE) and not is_closeout_round:
        errors.append(ValidationError(
            code="missing_section_new_items",
            message="turn is missing required `## New items I'm raising` section",
        ))
    if not _section_present(text, SECTION_STATUS_RE):
        errors.append(ValidationError(
            code="missing_section_status",
            message="turn is missing required `## Status` section",
        ))
    return errors


def _status_value(text: str) -> str | None:
    m = STATUS_RE.search(text)
    return m.group(1) if m else None


# ─── Operation-block validity ─────────────────────────────────────────


def _operation_errors(
    blocks: list[OperationBlock],
    *,
    phase: int,
    round: int,
    is_closeout_round: bool,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for block in blocks:
        if isinstance(block, RaiseBlock):
            if is_closeout_round:
                errors.append(ValidationError(
                    code="closeout_violation_raise",
                    message=(
                        "RAISE block emitted in a closeout round; "
                        "RAISE blocks are not permitted in closeout rounds"
                    ),
                    severity="warning",
                ))
                continue
            if not is_raisable(Category(block.kind), phase):
                errors.append(ValidationError(
                    code="raise_disallowed_category_for_phase",
                    message=(
                        f"category {block.kind!r} is not raisable in phase {phase}"
                    ),
                ))
            if not (block.body or "").strip():
                errors.append(ValidationError(
                    code="raise_missing_body",
                    message="RAISE block has empty body",
                ))
            if block.anchor_type not in {"quote", "after", "none"}:
                errors.append(ValidationError(
                    code="raise_invalid_anchor_type",
                    message=(
                        f"anchor_type must be one of quote|after|none; "
                        f"got {block.anchor_type!r}"
                    ),
                ))
        elif isinstance(block, AddressBlock):
            if not block.item_id:
                errors.append(ValidationError(
                    code="address_missing_item_id",
                    message="ADDRESS block is missing its item ID",
                ))
            if not (block.response or "").strip():
                errors.append(ValidationError(
                    code="address_missing_response",
                    message=f"ADDRESS {block.item_id} has empty response body",
                ))
            if block.proposes_status not in {"addressed", "acknowledged_proposed"}:
                errors.append(ValidationError(
                    code="address_invalid_proposes_status",
                    message=(
                        f"ADDRESS {block.item_id} proposes_status must be "
                        f"addressed|acknowledged_proposed; "
                        f"got {block.proposes_status!r}"
                    ),
                ))
        elif isinstance(block, ResolveBlock):
            if not block.item_id:
                errors.append(ValidationError(
                    code="resolve_missing_item_id",
                    message="RESOLVE block is missing its item ID",
                ))
            if not (block.reason or "").strip():
                errors.append(ValidationError(
                    code="resolve_missing_reason",
                    message=f"RESOLVE {block.item_id} requires non-empty reason",
                ))
        elif isinstance(block, AcknowledgeBlock):
            if not block.item_id:
                errors.append(ValidationError(
                    code="acknowledge_missing_item_id",
                    message="ACKNOWLEDGE block is missing its item ID",
                ))
            if not (block.reason or "").strip():
                errors.append(ValidationError(
                    code="acknowledge_missing_reason",
                    message=f"ACKNOWLEDGE {block.item_id} requires non-empty reason",
                ))
        elif isinstance(block, WithdrawBlock):
            if not block.item_id:
                errors.append(ValidationError(
                    code="withdraw_missing_item_id",
                    message="WITHDRAW block is missing its item ID",
                ))
            if not (block.reason or "").strip():
                errors.append(ValidationError(
                    code="withdraw_missing_reason",
                    message=f"WITHDRAW {block.item_id} requires non-empty reason",
                ))
    return errors


# ─── Top-level entry points ───────────────────────────────────────────


def validate_parsed(
    *,
    text: str,
    blocks: list[OperationBlock],
    phase: int,
    round: int,
    agent: str,
    is_closeout_round: bool = False,
) -> ValidationResult:
    """Validate a turn given its raw text + the parser's typed blocks.

    Caller is the parser, after it has assembled the operation blocks.
    The validator does NOT consult the ledger; it only checks structural
    shape, intra-turn invariants, and per-block field presence.
    """
    errors: list[ValidationError] = []
    errors.extend(_structural_errors(
        text,
        phase=phase,
        round=round,
        is_closeout_round=is_closeout_round,
    ))
    status_value = _status_value(text)
    if status_value is None:
        errors.append(ValidationError(
            code="missing_status_value",
            message="`## Status` section has no STATUS line",
        ))
    elif status_value not in {TurnStatus.IN_PROGRESS, TurnStatus.AGREED}:
        errors.append(ValidationError(
            code="invalid_status_value",
            message=(
                f"STATUS must be IN_PROGRESS or AGREED; got {status_value!r}"
            ),
        ))
    elif status_value == TurnStatus.AGREED and round == 1:
        # Round 1 cannot converge — no AGREED.
        errors.append(ValidationError(
            code="agreed_in_round_one",
            message=(
                "STATUS: AGREED is not allowed in round 1 of an interaction phase"
            ),
        ))
    elif status_value == TurnStatus.AGREED:
        # Must include a Phase artifact section when AGREED.
        if not _section_present(text, SECTION_PHASE_ARTIFACT_RE):
            errors.append(ValidationError(
                code="agreed_without_phase_artifact",
                message=(
                    "STATUS: AGREED requires a `## Phase artifact` section"
                ),
            ))

    errors.extend(_operation_errors(
        blocks,
        phase=phase,
        round=round,
        is_closeout_round=is_closeout_round,
    ))

    has_fatal = any(e.severity == "error" for e in errors)
    return ValidationResult(valid=not has_fatal, errors=errors)


def validate_turn(
    text: str,
    *,
    phase: int,
    round: int,
    agent: str,
    is_closeout_round: bool = False,
) -> ValidationResult:
    """Top-level structural validation without operation blocks.

    Performs only the structural-section gates and the STATUS-line
    invariants. Use ``validate_parsed`` once the parser has typed
    operation blocks.
    """
    errors: list[ValidationError] = []
    errors.extend(_structural_errors(
        text,
        phase=phase,
        round=round,
        is_closeout_round=is_closeout_round,
    ))
    status_value = _status_value(text)
    if status_value is None:
        errors.append(ValidationError(
            code="missing_status_value",
            message="`## Status` section has no STATUS line",
        ))
    elif status_value not in {TurnStatus.IN_PROGRESS, TurnStatus.AGREED}:
        errors.append(ValidationError(
            code="invalid_status_value",
            message=(
                f"STATUS must be IN_PROGRESS or AGREED; got {status_value!r}"
            ),
        ))
    elif status_value == TurnStatus.AGREED and round == 1:
        errors.append(ValidationError(
            code="agreed_in_round_one",
            message=(
                "STATUS: AGREED is not allowed in round 1 of an interaction phase"
            ),
        ))
    elif status_value == TurnStatus.AGREED:
        if not _section_present(text, SECTION_PHASE_ARTIFACT_RE):
            errors.append(ValidationError(
                code="agreed_without_phase_artifact",
                message=(
                    "STATUS: AGREED requires a `## Phase artifact` section"
                ),
            ))
    has_fatal = any(e.severity == "error" for e in errors)
    return ValidationResult(valid=not has_fatal, errors=errors)
