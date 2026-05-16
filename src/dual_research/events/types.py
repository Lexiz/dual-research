from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, kw_only=True)
class Event:
    """Base for all orchestrator events. Subclasses add specific fields."""
    kind: str

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


@dataclass(frozen=True, kw_only=True)
class RunStarted(Event):
    session_dir: str
    slug: str
    model_tier: str
    claude_model: str
    openai_model: str
    soft_cap: int
    hard_cap: int
    # Spec 0030: real context-window caps from the tier's ModelSpec.
    # Default 0 keeps pre-0030 transcripts replay-safe.
    claude_context_window: int = 0
    openai_context_window: int = 0
    kind: str = "run_started"


@dataclass(frozen=True, kw_only=True)
class RunCompleted(Event):
    phase_reached: str
    exit_code: int
    total_cost_usd: float
    duration_ms: int
    kind: str = "run_completed"


@dataclass(frozen=True, kw_only=True)
class RunFailed(Event):
    phase_reached: str
    error_type: str
    message: str
    kind: str = "run_failed"


@dataclass(frozen=True, kw_only=True)
class PhaseEntered(Event):
    phase: str
    kind: str = "phase_entered"


@dataclass(frozen=True, kw_only=True)
class PhaseExited(Event):
    phase: str
    duration_ms: int
    kind: str = "phase_exited"


@dataclass(frozen=True, kw_only=True)
class TurnStarted(Event):
    agent: str
    phase: str
    label: str
    kind: str = "turn_started"


@dataclass(frozen=True, kw_only=True)
class TurnEnded(Event):
    agent: str
    phase: str
    label: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float
    duration_ms: int
    finish_reason: str | None
    model_id: str
    # Spec 0030: best-effort per-piece token sizes (Tk-vocab keys —
    # ``brief`` / ``d1`` / ``d2`` / ``hist`` / ``plan`` / ``draft`` /
    # ``histp``). Computed at call time via char÷3.5 heuristic; renormalised
    # against ``input_tokens`` for honest segment widths on the
    # Consumption tab. Empty dict for pre-0030 transcripts.
    prompt_pieces: dict[str, int] = field(default_factory=dict)
    kind: str = "turn_ended"


@dataclass(frozen=True, kw_only=True)
class Phase0Complete(Event):
    claude_status: str | None
    openai_status: str | None
    claude_brief_issues: int | None
    openai_brief_issues: int | None
    brief_needs_input: bool
    kind: str = "phase0_complete"


@dataclass(frozen=True, kw_only=True)
class Phase1Complete(Event):
    claude_chars: int
    openai_chars: int
    kind: str = "phase1_complete"


@dataclass(frozen=True, kw_only=True)
class CostUpdate(Event):
    total_usd: float
    by_agent: dict[str, float] = field(default_factory=dict)
    kind: str = "cost_update"


@dataclass(frozen=True, kw_only=True)
class Phase2RoundComplete(Event):
    round: int
    agreed: bool
    claude_status: str | None
    openai_status: str | None
    claude_drafter: str | None
    openai_drafter: str | None
    claude_open_questions: int | None
    openai_open_questions: int | None
    claude_blocking: int | None
    openai_blocking: int | None
    claude_fsd: int | None
    openai_fsd: int | None
    kind: str = "phase2_round_complete"


@dataclass(frozen=True, kw_only=True)
class RepairInvoked(Event):
    agent: str
    phase: int
    round: int
    errors: list[str]
    budget_remaining: int
    kind: str = "repair_invoked"


@dataclass(frozen=True, kw_only=True)
class SoftCapHit(Event):
    phase: str
    round: int
    cap: int
    kind: str = "soft_cap_hit"


@dataclass(frozen=True, kw_only=True)
class HardCapHit(Event):
    phase: str
    round: int
    cap: int
    kind: str = "hard_cap_hit"


@dataclass(frozen=True, kw_only=True)
class DrafterTiebreakResolved(Event):
    round: int
    selected_drafter: str
    reason: str
    claude_proposed: str | None
    openai_proposed: str | None
    kind: str = "drafter_tiebreak_resolved"


@dataclass(frozen=True, kw_only=True)
class Phase2Complete(Event):
    rounds: int
    converged: bool
    drafter: str | None
    fsd_count: int
    via_tiebreak: bool
    kind: str = "phase2_complete"


@dataclass(frozen=True, kw_only=True)
class Phase3Complete(Event):
    drafter: str
    draft_chars: int
    kind: str = "phase3_complete"


@dataclass(frozen=True, kw_only=True)
class Phase4RoundComplete(Event):
    round: int
    approved: bool
    claude_status: str | None
    openai_status: str | None
    claude_open_issues: int | None
    openai_open_issues: int | None
    draft_round: int
    kind: str = "phase4_round_complete"


@dataclass(frozen=True, kw_only=True)
class Phase4DraftRevised(Event):
    round: int
    new_draft_round: int
    new_draft_chars: int
    kind: str = "phase4_draft_revised"


@dataclass(frozen=True, kw_only=True)
class Phase4Complete(Event):
    rounds: int
    approved: bool
    final_draft_round: int
    revisions: int
    kind: str = "phase4_complete"


@dataclass(frozen=True, kw_only=True)
class FinalEmitted(Event):
    session_final_path: str
    out_path: str | None
    char_count: int
    confidence: str
    kind: str = "final_emitted"
