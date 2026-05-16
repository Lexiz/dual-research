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
from dual_research.protocol import (
    ParsedTurn,
    ProtocolParseError,
    parse_turn,
    repair_prompt,
)
from dual_research.protocol.prompts import repair_input_bundle


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
) -> tuple[str, ParsedTurn]:
    """Parse + validate. On malformed: invoke repair once if budget permits.

    Returns (final_text, parsed). If the after-repair turn is still malformed,
    that is returned (validation will raise on the *next* round's call into
    this function, after consecutive_failures reaches 2).

    Raises ProtocolParseError on the second consecutive failure for the agent.
    """
    parsed = parse_turn(text)
    first_errors: list[str] | None = None
    try:
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
        max_output_tokens=6144,
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
