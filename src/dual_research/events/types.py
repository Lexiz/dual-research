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
    # Spec 0143 §3.1 Step 2 — informational breakdown of how many output
    # tokens were reasoning (subset of ``output_tokens``, NOT a separate
    # bill). Zero on Anthropic and on non-reasoning OpenAI models.
    reasoning_tokens: int = 0
    kind: str = "turn_ended"


@dataclass(frozen=True, kw_only=True)
class Phase0Complete(Event):
    """Phase 0 marker event.

    Spec 0115 — the legacy counter fields (``claude_brief_issues``,
    ``openai_brief_issues``) default to ``None`` and are no longer
    populated on new-protocol runs. They remain on the dataclass so
    legacy transcripts continue to deserialise cleanly during the
    transition. The new-protocol UI reads counters from the
    ``ItemRaised`` event stream instead.
    """

    claude_status: str | None = None
    openai_status: str | None = None
    claude_brief_issues: int | None = None
    openai_brief_issues: int | None = None
    brief_needs_input: bool = False
    kind: str = "phase0_complete"


@dataclass(frozen=True, kw_only=True)
class Phase0RoundComplete(Event):
    """Phase 0 round marker event (spec 0135).

    Mirrors the ``Phase2RoundComplete`` / ``Phase4RoundComplete`` shape:
    counter fields default to ``None`` and are not populated on
    new-protocol runs — the UI reads per-category data from
    ``ItemRaised`` / ``ItemTransitioned`` just like phases 2 and 4 do
    since spec 0115. Emitted from ``dr_run._publish_legacy_round_complete``
    once per Phase 0 negotiation round (matching the per-round granularity
    Phase 2 and Phase 4 already publish).
    """

    round: int
    agreed: bool
    claude_status: str | None = None
    openai_status: str | None = None
    kind: str = "phase0_round_complete"


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
    """Phase 2 round marker event.

    Spec 0115 — the legacy counter fields default to ``None`` and are
    no longer populated on new-protocol runs. The new-protocol UI
    reads counters from the ``ItemRaised`` / ``ItemTransitioned``
    event stream. Fields retained for legacy transcript compat.
    """

    round: int
    agreed: bool
    claude_status: str | None = None
    openai_status: str | None = None
    claude_drafter: str | None = None
    openai_drafter: str | None = None
    claude_open_questions: int | None = None
    openai_open_questions: int | None = None
    claude_blocking: int | None = None
    openai_blocking: int | None = None
    claude_fsd: int | None = None
    openai_fsd: int | None = None
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
class CanonicalFsdSynthesized(Event):
    """Spec 0089 § A — Phase 2 escaped a stuck-AGREED loop where every
    convergence gate passed except the canonical FSD sub-section was
    missing from the AGREED_PLAN block.

    The orchestrator synthesised the canonical sub-section from the
    drafter's standalone Final-surfaced disagreements section (which
    is a strict superset of the canonical fields), spliced it into
    the drafter's AGREED_PLAN, and exited Phase 2 converged. No
    repair turn fired; the synthesis is a pure transformation of
    existing on-disk content.
    """

    round: int
    drafter: str
    fsd_ids: list[str]
    kind: str = "canonical_fsd_synthesized"


@dataclass(frozen=True, kw_only=True)
class StuckAgreedPromoted(Event):
    """Spec 0089 § B — Phase 2 or Phase 4 escaped a stuck-AGREED loop
    where the agents were fully aligned on the protocol surface
    (status, drafter, hash, FSDs) for K consecutive rounds but the
    system-derived ledger cross-check kept blocking convergence.

    The orchestrator accepts the agents' judgment after the K-round
    streak and exits converged via the stuck-AGREED escape valve.
    `phase` is 2 or 4. `streak` is the number of consecutive
    lenient-True / strict-False rounds (≥ K). `ledger_open_count`
    is the ledger's count at the round when the escape fired.
    """

    phase: int
    round: int
    streak: int
    ledger_open_count: int
    kind: str = "stuck_agreed_promoted"


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
    # Spec 0089 § A: set when Phase 2 converged via canonical-FSD
    # sub-section synthesis.
    via_canonical_fsd_synthesis: bool = False
    # Spec 0089 § B: set when Phase 2 converged via the stuck-AGREED
    # escape valve (ledger kept blocking, agents stayed aligned).
    via_stuck_agreed: bool = False
    kind: str = "phase2_complete"


@dataclass(frozen=True, kw_only=True)
class Phase3Complete(Event):
    drafter: str
    draft_chars: int
    kind: str = "phase3_complete"


@dataclass(frozen=True, kw_only=True)
class Phase4RoundComplete(Event):
    """Phase 4 round marker event.

    Spec 0115 — legacy counter fields default to ``None``; the
    new-protocol UI reads from ``ItemRaised`` / ``ItemTransitioned``.
    """

    round: int
    approved: bool
    claude_status: str | None = None
    openai_status: str | None = None
    claude_open_issues: int | None = None
    openai_open_issues: int | None = None
    draft_round: int = 1
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
    # Spec 0089 § B: set when Phase 4 converged via the stuck-AGREED
    # (stuck-APPROVED) escape valve.
    via_stuck_agreed: bool = False
    # Spec 0214: orchestrator-computed canonical_hash (smart-quote-folded,
    # whitespace-collapsed SHA-256) of the on-disk draft at the converged
    # round. ``None`` when no draft file is on disk for the final round.
    draft_file_sha256: str | None = None
    kind: str = "phase4_complete"


@dataclass(frozen=True, kw_only=True)
class FinalEmitted(Event):
    session_final_path: str
    out_path: str | None
    char_count: int
    confidence: str
    kind: str = "final_emitted"


# ─── Spec 0114 — Deep Research lifecycle events ───────────────────────
#
# These events form the canonical persistence of the lifecycle. The
# ledger can be reconstructed from the event stream alone — no need to
# re-parse markdown for state derivation.


@dataclass(frozen=True, kw_only=True)
class ItemRaised(Event):
    """A new item entered the ledger.

    ``id`` is the orchestrator-assigned stable ID (e.g. ``Q-plan-c-04``).
    ``phase`` is the integer phase number (0, 2, or 4) — string-coercion
    happens at the serialization boundary.
    """

    id: str
    item_kind: str          # "question" | "disagreement" | "issue" | "comment"
    phase: int
    round: int
    raiser: str             # "claude" | "openai"
    body: str
    anchor_type: str        # "quote" | "after" | "none"
    anchor_text: str
    evidence_required: bool
    kind: str = "item_raised"


@dataclass(frozen=True, kw_only=True)
class ItemTransitioned(Event):
    """An item moved from one state to another.

    ``actor`` is one of ``"claude"`` / ``"openai"`` / ``"orchestrator"``.
    ``evidence_records`` is populated only on ``open → addressed``
    transitions; each entry is a dict shape mirroring
    ``contract.EvidenceRecord``. ``via`` is set only when
    ``actor == "orchestrator"`` for ``capped`` transitions (``"hard_cap"``
    or ``"ghost_cap"``).
    """

    id: str
    from_state: str         # "open" | "addressed" | "resolved" | …
    to_state: str
    actor: str              # "claude" | "openai" | "orchestrator"
    phase: int
    round: int
    reason: str
    evidence_records: list[dict] = field(default_factory=list)
    via: str | None = None
    kind: str = "item_transitioned"


@dataclass(frozen=True, kw_only=True)
class CloseoutUrged(Event):
    """The orchestrator detected both agents emitted AGREED with
    non-terminal items in the ledger. The next round becomes a closeout
    round; each agent's prompt receives a closeout_request section.
    """

    phase: int
    round: int
    affected_items: list[str] = field(default_factory=list)
    affected_raiser_budgets: dict[str, int] = field(default_factory=dict)
    kind: str = "closeout_urged"


@dataclass(frozen=True, kw_only=True)
class CloseoutViolation(Event):
    """A closeout-round turn contained a forbidden operation (e.g. a
    RAISE block). The orchestrator silently drops the offending block
    and records this event for diagnostics.
    """

    phase: int
    round: int
    agent: str
    violation_code: str     # "closeout_violation_raise" | …
    dropped_block: str = ""
    kind: str = "closeout_violation"


@dataclass(frozen=True, kw_only=True)
class ProtocolViolation(Event):
    """Spec 0141 — the orchestrator dropped a block that would have
    violated the item-state invariant.

    Today this fires for exactly one case: an ADDRESS block targeting an
    item already in a terminal state (resolved / acknowledged /
    withdrawn / capped). Future invariants reuse the same event with a
    different ``violation_code``.

    Anchor-run smoking gun (20260521-010637-dvs-backend-language-choice,
    item ``D-plan-g-01``): r2.1 claude addressed; r2.2 openai RESOLVED;
    r2.3 claude ADDRESSED the resolved item — without the guard this
    leaked the item back to ``addressed`` and r2.3 openai RESOLVED it a
    second time, producing the ``closed > raised`` invariant violation
    in the run-summary aggregator (B02).
    """

    phase: int
    round: int
    agent: str
    violation_code: str     # "terminal_state_re_address" | …
    item_id: str
    from_state: str
    dropped_block: str = ""
    kind: str = "protocol_violation"


@dataclass(frozen=True, kw_only=True)
class EmptyTurnDetected(Event):
    """Spec 0141 — a negotiate / review turn produced zero
    ledger-affecting blocks (no RAISE / ADDRESS / RESOLVE / WITHDRAW /
    ACKNOWLEDGE) at parse time.

    Fires only in phases that expect item movement (0, 2, 4). Phases 1
    (parallel drafts) and 3 (single-agent drafting) are by design item-
    silent and do not generate this event.

    Informational only — does not abort the turn or advance any retry
    counter. Consumers (the UI surface, post-run analytics) decide what
    to do with it. ``finish_reason == "max_tokens"`` is the dispositive
    "model was producing output but ran out of room" signal.
    """

    phase: int
    round: int
    agent: str
    parser_block_count: int = 0     # always 0 by definition; carried for future
    finish_reason: str | None = None
    output_tokens: int = 0
    kind: str = "empty_turn_detected"


@dataclass(frozen=True, kw_only=True)
class PhaseConverged(Event):
    """A phase reached terminal convergence.

    One of ``via_closeout`` / ``via_ghost_cap`` / ``via_hard_cap`` /
    ``via_artifact_promotion`` may be ``True``; an organic convergence
    has all four ``False``.
    """

    phase: int
    final_round: int
    via_closeout: bool = False
    via_ghost_cap: bool = False
    via_hard_cap: bool = False
    via_artifact_promotion: bool = False
    kind: str = "phase_converged"


@dataclass(frozen=True, kw_only=True)
class ArtifactCanonicallyPromoted(Event):
    """Spec 0137 — orchestrator escaped a hash-drift loop by accepting
    the agents' self-declared AGREED.

    Fires when both agents emit ``STATUS: AGREED`` in the same round
    AND the ledger has zero non-terminal items, but the per-phase
    artifact hash gate ([orchestrator/closeout.py] ``check_convergence``)
    still rejects (the two agents wrote semantically-equivalent but
    byte-different artifact bodies). The orchestrator treats this as
    substantive convergence — agents' AGREED is load-bearing; byte
    equality of the artifact block was a hopeful structural assertion
    downstream code does not actually require — promotes the canonical
    artifact from the designated agent's turn file (claude for phase 0;
    the drafter for phase 2; the drafter for phase 4), and exits the
    phase converged.

    Distinct from the legacy ``DrafterCanonicalPromoted`` event (spec
    0032), which fired in the legacy ``phase2.py`` after a force-verbatim
    repair turn also failed. This spec's escape valve fires without a
    repair turn — the downstream consumer reads from one specific
    agent's emission regardless, so the second agent's drift is not
    actually load-bearing.
    """

    phase: str
    round: int
    kind: str = "artifact_canonically_promoted"
