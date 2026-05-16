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
class TurnInputs(Event):
    """Spec 0033 — full per-piece prompt text for an upcoming turn.

    Emitted alongside ``TurnStarted`` (NOT ``TurnEnded``) so the UI can
    audit what's about to be sent even while the call is in flight. Keys
    match the spec-0030 Tk-vocab (``brief``, ``d1``, ``d2``, ``plan``,
    ``hist``, ``draft``, ``histp``) plus a fixed ``system`` key for the
    static instruction template.

    Empty pieces are present-with-empty-string, not omitted, so the UI
    can render a "(not used in this turn)" stub uniformly.

    Payload size is non-trivial (whole prompt text per turn); the
    aggregator persists each bundle to ``session_dir/inputs/<key>.json``
    and the UI fetches on demand via a REST endpoint. Bundles are NOT
    pushed over SSE.
    """

    agent: str  # "claude" | "openai" (backend vocab)
    phase: str  # "phase0" | "phase1" | "phase2_round1" | ...
    label: str  # same label shape as TurnStarted / TurnEnded
    pieces: dict[str, str] = field(default_factory=dict)
    kind: str = "turn_inputs"


@dataclass(frozen=True, kw_only=True)
class TurnSearches(Event):
    """Spec 0036 — per-turn web-search audit payload.

    Emitted by the orchestrator after the agent returns but before
    ``TurnEnded``, so the aggregator can persist the audit bundle and
    stamp ``search_audit_path`` on the turn's ``TurnTokenUsage`` row
    before the ``TurnEnded`` handler runs.

    ``audit`` is the JSON-serialisable dict produced by
    ``dual_research.audit.audit_to_dict`` over a normalised
    ``TurnSearchAudit``. Carrying it as an opaque dict on the event
    keeps the events module free of an audit-schema import.

    Not emitted when web search is disabled or when the provider
    response carried no search activity. Aggregator + UI tolerate
    absence (the search-audit-path stays ``None``).
    """

    agent: str
    phase: str
    label: str
    turn_key: str
    audit: dict = field(default_factory=dict)
    kind: str = "turn_searches"


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
    # Spec 0031: web-search tool calls in this turn. Anthropic +
    # OpenAI both report tool-call counts; this is the count of
    # web_search invocations. Pre-0031 transcripts omit it (defaults
    # to 0).
    searches: int = 0
    # Spec 0039: cost_usd is now the FULL invoice (tokens + web-search
    # fees). ``search_cost`` is preserved alongside as a breakdown so
    # the UI can show "of which web search" without losing the total.
    # The 5m/1h cache-write split lets the recompute tool re-price
    # exactly; older transcripts lack the split and credit the
    # aggregate ``cache_write_tokens`` entirely to 5m at recompute time.
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0
    search_cost: float = 0.0
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
class DrafterCanonicalPromoted(Event):
    """Spec 0032 — Phase 2 escaped a hash-drift loop by promoting the
    drafter's plan as canonical without strict hash-match.

    Fires when both agents emit STATUS: AGREED with matching drafter /
    OQ / BD / FSD on two successive rounds but the AGREED_PLAN hashes
    keep drifting (the model paraphrases instead of copying verbatim).
    First detection triggers a `force_verbatim_copy` repair turn; if
    that also fails to match, the orchestrator promotes the named
    drafter's plan as canonical and exits Phase 2 converged.

    `canonical_hash` and `other_hash` are the short prefixes used in
    the run log — same shape as the protocol's internal hash check.
    """

    round: int
    drafter: str
    other_agent: str
    canonical_hash: str
    other_hash: str
    kind: str = "drafter_canonical_promoted"


@dataclass(frozen=True, kw_only=True)
class Phase2Complete(Event):
    rounds: int
    converged: bool
    drafter: str | None
    fsd_count: int
    via_tiebreak: bool
    # Spec 0032: set when Phase 2 converged via canonical promotion
    # rather than clean hash-match agreement.
    via_canonical_promotion: bool = False
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
