from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from dual_research.agents.base import AgentCall
from dual_research.events import EventBus, RepairInvoked
from dual_research.orchestrator._call import run_one_call
from dual_research.orchestrator._turns import next_malformed_n
from dual_research.persistence import Metrics, SessionDirectory, Transcript
from dual_research.persistence.state import write_atomic
from dual_research.contract.markers import SECTION_REVISED_DRAFT_RE
from dual_research.protocol import (
    ParsedTurn,
    ParsedTurnV2,
    ProtocolParseError,
    apply_revised_draft_deltas,
    extract_revised_draft_deltas,
    parse_turn,
    parse_turn_v2,
    repair_prompt,
)
from dual_research.protocol.prompts import repair_input_bundle


# Spec 0218 §3.3 — `finish_reason in {"max_tokens", "length"}` is a synthetic
# parse failure. A truncated turn whose tail bytes happen to look like a valid
# STATUS block is still untrustworthy; the canonical guarantee is that no
# truncated turn ever lands as canonical without going through repair.
_TRUNCATED_FINISH_REASONS = frozenset({"max_tokens", "length"})
_TRUNCATED_ERROR = "truncated_by_max_tokens"


def _is_truncated_finish(finish_reason: str | None) -> bool:
    return finish_reason is not None and finish_reason.lower() in _TRUNCATED_FINISH_REASONS


# Spec 0036: repair turns sometimes need to replay the canonical plan +
# the response that drifted, which can exceed the previous 6144-token
# cap. Match the regular turn budget so large repaired turns don't
# truncate.
REPAIR_MAX_OUTPUT_TOKENS = 16384


@dataclass
class RepairTracker:
    """Per-phase repair-budget + consecutive-failure tracking.

    Budget: each agent gets 1 free repair attempt per phase. Once spent, further
    malformed turns are not re-repaired in the same phase; the parsed result is
    returned as-is and the orchestrator handles the consequence.

    Consecutive failures: tracked across rounds within the phase. If an agent
    produces a malformed turn twice in a row (even after an attempted repair),
    the run aborts with exit 52.
    """

    initial_budget: int = 1
    budget: dict[str, int] = field(default_factory=dict)
    consecutive_failures: dict[str, int] = field(default_factory=dict)

    def _ensure(self, agent: str) -> None:
        if agent not in self.budget:
            self.budget[agent] = self.initial_budget
        if agent not in self.consecutive_failures:
            self.consecutive_failures[agent] = 0

    def reset_consecutive(self, agent: str) -> None:
        self._ensure(agent)
        self.consecutive_failures[agent] = 0

    def record_failure(self, agent: str) -> int:
        self._ensure(agent)
        self.consecutive_failures[agent] += 1
        return self.consecutive_failures[agent]

    def has_budget(self, agent: str) -> bool:
        self._ensure(agent)
        return self.budget[agent] > 0

    def spend(self, agent: str) -> int:
        self._ensure(agent)
        self.budget[agent] = max(0, self.budget[agent] - 1)
        return self.budget[agent]


# Validators: phase 2 / phase 4 implementations live in their modules; the
# repair flow takes a callable so it stays neutral about which protocol phase.
Validator = Callable[[ParsedTurn, str], None]


async def parse_with_repair(
    *,
    agent: AgentCall,
    text: str,
    phase: int,
    round: int,
    validator: Validator,
    tracker: RepairTracker,
    session: SessionDirectory,
    session_phase: str,
    transcript: Transcript,
    event_bus: EventBus,
    metrics: Metrics,
    out_path: Path,
    finish_reason: str | None = None,
) -> tuple[str, ParsedTurn]:
    """Parse + validate. On malformed: invoke repair once if budget permits.

    Returns (final_text, parsed). If the after-repair turn is still malformed,
    that is returned (validation will raise on the *next* round's call into
    this function, after consecutive_failures reaches 2).

    Raises ProtocolParseError on the second consecutive failure for the agent.

    Spec 0218 §3.3 — when ``finish_reason`` is ``"max_tokens"`` or
    ``"length"``, the turn is treated as malformed regardless of body
    shape and routed through the same repair flow.
    """
    parsed = parse_turn(text)
    first_errors: list[str] | None = None
    truncated = _is_truncated_finish(finish_reason)
    try:
        if truncated:
            raise ProtocolParseError(agent.label, [_TRUNCATED_ERROR])
        validator(parsed, agent.label)
        tracker.reset_consecutive(agent.label)
        return text, parsed
    except ProtocolParseError as e:
        first_errors = list(e.errors)

    failures = tracker.record_failure(agent.label)
    if failures >= 2:
        raise ProtocolParseError(agent.label, first_errors or ["unknown"])

    if not tracker.has_budget(agent.label):
        transcript.write(
            "repair_skipped_budget_exhausted",
            agent=agent.label,
            phase=phase,
            round=round,
            errors=first_errors,
        )
        return text, parsed

    # Save malformed text to audit trail, then invoke repair turn.
    n = next_malformed_n(session, phase=session_phase, round=round, agent=agent.label)
    malformed_path = out_path.parent / f"{out_path.stem}.malformed-{n}.md"
    write_atomic(malformed_path, text)

    tracker.spend(agent.label)
    await event_bus.publish(
        RepairInvoked(
            agent=agent.label,
            phase=phase,
            round=round,
            errors=first_errors or [],
            budget_remaining=tracker.budget[agent.label],
        )
    )
    transcript.write(
        "repair_invoked",
        agent=agent.label,
        phase=phase,
        round=round,
        errors=first_errors,
        malformed_path=str(malformed_path),
        budget_remaining=tracker.budget[agent.label],
    )

    prompt = repair_prompt(
        agent_name=agent.label,
        phase=phase,
        errors=first_errors or [],
        malformed_content=text,
    )
    # Spec 0033: per-piece TEXT bundle for the Input tab.
    repair_bundle = repair_input_bundle(
        agent_name=agent.label,
        phase=phase,
        errors=first_errors or [],
        malformed_content=text,
    )
    repaired_result = await run_one_call(
        agent=agent,
        prompt=prompt,
        label=f"phase{phase}-r{round}-{agent.label}-repair",
        phase=f"phase{phase}",
        metrics=metrics,
        transcript=transcript,
        event_bus=event_bus,
        stream_to=None,
        max_output_tokens=REPAIR_MAX_OUTPUT_TOKENS,
        prompt_bundle=repair_bundle,
    )
    write_atomic(out_path, repaired_result.text)
    new_parsed = parse_turn(repaired_result.text)
    try:
        validator(new_parsed, agent.label)
        tracker.reset_consecutive(agent.label)
        return repaired_result.text, new_parsed
    except ProtocolParseError:
        # Repair did not produce a valid turn either. Leave it; next round's
        # validation will trip consecutive_failures = 2 and abort.
        return repaired_result.text, new_parsed


# Spec 0218 §3.3 — v2 sibling. dr_run.py uses parse_turn_v2; the legacy v1
# parse_with_repair is still wired into phase4.py (dead code at the moment
# but kept for the dedicated tests). The two functions share RepairTracker
# semantics and the same one-shot-per-phase budget.

ValidatorV2 = Callable[..., None]


def _assert_v2_well_formed_turn(
    parsed: ParsedTurnV2,
    raw_text: str,
    agent: str,
    *,
    is_drafter: bool = False,
    prior_draft: str | None = None,
) -> None:
    """Default v2 validator for the dr_run.py path (spec 0218 §3.3, spec 0219 §3.2/§3.4/§3.5).

    Asserts:
      - `## Status` block is present (`parsed.status is not None`).
      - If the turn carries a non-empty `## Revised draft` section **and
        the agent is the phase-4 drafter** (spec 0219 §3.2), the body
        parses as section-delta operations (spec 0218 §3.2). Legacy
        full-prose `## Revised draft` bodies — i.e. no `### REPLACE_*` /
        `### APPEND_*` / `### DELETE_*` / `### REPLACE_DRAFT_FULL` /
        `### EDIT_SECTION` sub-heading — raise
        ``ProtocolParseError("revised_draft_body_missing_delta_op")``
        via the extractor.
      - When ``prior_draft`` is provided alongside an ``is_drafter`` turn,
        dry-run ``apply_revised_draft_deltas`` to surface heading-mismatch
        / anchor-mismatch / missing-``reason:`` errors through the same
        repair plumbing (spec 0219 §3.4, §3.5). The reviewer's
        ``## Revised draft`` placeholder body never trips this gate
        because ``is_drafter`` is False on reviewer turns (spec 0219 §3.1).
    """
    errs: list[str] = []
    if parsed.status is None:
        errs.append("missing STATUS:")
    if is_drafter:
        # Check raw_text directly for the `## Revised draft` heading
        # because parse_turn_v2 strips empty-body sections to None;
        # spec 0219 §3.5 wants "heading present, body empty" to fail
        # the same as "heading present, body is non-delta prose".
        revised_heading_present = SECTION_REVISED_DRAFT_RE.search(raw_text) is not None
        if revised_heading_present:
            if parsed.revised_draft is None or not parsed.revised_draft.strip():
                # Heading present but body empty / whitespace-only — a
                # stillborn revision section. Per the doctrine the
                # drafter must OMIT the section entirely when there
                # are no edits, never emit it empty.
                errs.append("revised_draft_body_missing_delta_op")
            else:
                payload = None
                try:
                    payload = extract_revised_draft_deltas(raw_text)
                except ProtocolParseError as e:
                    errs.extend(e.errors)
                if payload is not None and prior_draft is not None:
                    try:
                        apply_revised_draft_deltas(prior_draft=prior_draft, payload=payload)
                    except ProtocolParseError as e:
                        errs.extend(e.errors)
    if errs:
        raise ProtocolParseError(agent, errs)


async def parse_v2_with_repair(
    *,
    agent: AgentCall,
    text: str,
    phase: int,
    round: int,
    tracker: RepairTracker,
    session: SessionDirectory,
    session_phase: str,
    transcript: Transcript,
    event_bus: EventBus,
    metrics: Metrics,
    out_path: Path,
    finish_reason: str | None = None,
    validator: ValidatorV2 | None = None,
    is_drafter: bool = False,
    prior_draft: str | None = None,
) -> tuple[str, ParsedTurnV2]:
    """Parse + validate a v2-protocol turn. On malformed, invoke repair once.

    Spec 0218 §3.3 — same one-shot-per-phase repair semantics as the v1
    `parse_with_repair`. Returns ``(final_text, parsed_v2)``. The canonical
    write is the responsibility of the caller, who writes ``final_text`` to
    the canonical turn path AFTER this function returns.

    Spec 0219 §3.2 — ``is_drafter`` flows through to the validator so the
    reviewer's placeholder ``## Revised draft`` body never trips the
    drafter-only section-delta gate. Spec 0219 §3.4/§3.5 — ``prior_draft``
    flows through so the validator can dry-run-apply the deltas against
    the on-disk draft and surface heading-mismatch / anchor-mismatch /
    missing-``reason:`` failures through the same one-shot repair flow.

    When ``finish_reason in {"max_tokens", "length"}`` the turn is treated
    as malformed regardless of body shape — a truncated turn whose tail
    bytes happen to look like a valid STATUS block is still untrustworthy.
    """
    val = validator or _assert_v2_well_formed_turn
    truncated = _is_truncated_finish(finish_reason)
    parsed = parse_turn_v2(text)
    first_errors: list[str] | None = None
    try:
        if truncated:
            raise ProtocolParseError(agent.label, [_TRUNCATED_ERROR])
        val(parsed, text, agent.label, is_drafter=is_drafter, prior_draft=prior_draft)
        tracker.reset_consecutive(agent.label)
        return text, parsed
    except ProtocolParseError as e:
        first_errors = list(e.errors)

    failures = tracker.record_failure(agent.label)
    if failures >= 2:
        if not is_drafter:
            raise ProtocolParseError(agent.label, first_errors or ["unknown"])
        # Spec 0231 §2.3 — drafter has a downstream no-op fallback in
        # ``_on_revised_draft`` and emits a
        # ``ProtocolViolation(phase4_drafter_repair_failed)`` per failing
        # round. Suppress the exit-52 raise so the round loop continues
        # until ``hard_cap``; the PV makes each occurrence observable on
        # the dashboard. The malformed text is returned unchanged so the
        # caller's ``_on_revised_draft`` catches the same parse error and
        # writes a byte-equal no-op draft.
        transcript.write(
            "repair_drafter_fallback_engaged",
            agent=agent.label,
            phase=phase,
            round=round,
            errors=first_errors,
            consecutive_failures=failures,
        )
        return text, parsed

    if not tracker.has_budget(agent.label):
        transcript.write(
            "repair_skipped_budget_exhausted",
            agent=agent.label,
            phase=phase,
            round=round,
            errors=first_errors,
        )
        return text, parsed

    # Save malformed text to audit trail, then invoke repair turn.
    n = next_malformed_n(session, phase=session_phase, round=round, agent=agent.label)
    malformed_path = out_path.parent / f"{out_path.stem}.malformed-{n}.md"
    write_atomic(malformed_path, text)

    tracker.spend(agent.label)
    await event_bus.publish(
        RepairInvoked(
            agent=agent.label,
            phase=phase,
            round=round,
            errors=first_errors or [],
            budget_remaining=tracker.budget[agent.label],
        )
    )
    transcript.write(
        "repair_invoked",
        agent=agent.label,
        phase=phase,
        round=round,
        errors=first_errors,
        malformed_path=str(malformed_path),
        budget_remaining=tracker.budget[agent.label],
    )

    prompt = repair_prompt(
        agent_name=agent.label,
        phase=phase,
        errors=first_errors or [],
        malformed_content=text,
    )
    repair_bundle = repair_input_bundle(
        agent_name=agent.label,
        phase=phase,
        errors=first_errors or [],
        malformed_content=text,
    )
    repaired_result = await run_one_call(
        agent=agent,
        prompt=prompt,
        label=f"phase{phase}-r{round}-{agent.label}-repair",
        phase=f"phase{phase}",
        metrics=metrics,
        transcript=transcript,
        event_bus=event_bus,
        stream_to=None,
        max_output_tokens=REPAIR_MAX_OUTPUT_TOKENS,
        prompt_bundle=repair_bundle,
    )
    repaired_text = repaired_result.text
    new_parsed = parse_turn_v2(repaired_text)
    try:
        val(new_parsed, repaired_text, agent.label, is_drafter=is_drafter, prior_draft=prior_draft)
        tracker.reset_consecutive(agent.label)
    except ProtocolParseError:
        # Repair did not converge. Leave it; the next round's validation
        # will trip consecutive_failures = 2 and abort with exit 52.
        pass
    return repaired_text, new_parsed
