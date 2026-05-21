"""Spec 0114 — Deep Research phase orchestrator.

A self-contained, pure-Python phase runner for the new Deep Research
protocol. It coexists with the legacy ``phase0.py`` / ``phase2.py`` /
``phase4.py`` orchestrators during the migration. Callers wire this
runner into ``run.py`` once they're ready to cut a run over to the new
protocol; until then the legacy runners stay live.

The runner is structured as a synchronous-step "round loop" over an
``AgentTurnFn`` callable. The caller supplies that callable; in
production it wraps the agent SDK call, in tests it returns canned turn
text. This keeps the runner unit-testable without async / I/O scaffolding.

Public surface:

- ``LedgerEntryV2``       — orchestrator-side per-item state
- ``DeepResearchPhase``   — runs a single interaction phase
- ``PhaseRunResult``      — bundle returned after the loop terminates
- ``AgentTurnFn``         — callable type for "build prompt → get turn text"
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Callable

from dual_research.contract.artifacts import canonical_hash
from dual_research.contract.caps import caps_for
from dual_research.contract.categories import Category
from dual_research.contract.ids import format_id, raiser_letter
from dual_research.contract.lifecycle import State, is_terminal
from dual_research.contract.operations import (
    AcknowledgeBlock,
    AddressBlock,
    RaiseBlock,
    ResolveBlock,
    WithdrawBlock,
)
from dual_research.contract.validator import validate_parsed
from dual_research.events import (
    CloseoutUrged,
    CloseoutViolation,
    ItemRaised,
    ItemTransitioned,
    PhaseConverged,
)
# Spec 0115 — legacy_shim removed; the snapshot helper below is no
# longer used by production code but is retained for ad-hoc callers
# (tests, debugging tools).
from dual_research.orchestrator.closeout import (
    CloseoutTracker,
    _ItemView,
    check_convergence,
    ghost_cap_reason,
    hard_cap_reason,
    items_blocking_convergence,
    select_ghost_cap_items,
    should_urge_closeout,
)
from dual_research.protocol.parse import parse_turn_v2
from dual_research.protocol.parse_v2 import ParsedTurnV2


# ─── Per-item ledger entry (orchestrator view) ────────────────────────


@dataclass
class LedgerEntryV2:
    """One tracked item across rounds of a single phase.

    The orchestrator builds this incrementally as turns arrive. The
    canonical persistence is the event stream (ItemRaised /
    ItemTransitioned); ``LedgerEntryV2`` is the in-memory projection.
    """

    id: str
    kind: Category
    phase: int
    raiser: str             # "claude" | "openai"
    body: str
    anchor_type: str
    anchor_text: str
    evidence_required: bool
    current_state: State = State.OPEN
    raised_round: int = 0
    transitions: list[dict] = field(default_factory=list)
    ack_proposed_by: str | None = None  # for the mutual-ack handshake

    def to_item_view(self) -> _ItemView:
        return _ItemView(
            id=self.id,
            raiser=self.raiser,
            current_state=self.current_state.value,
        )


# ─── Per-phase state ──────────────────────────────────────────────────


@dataclass
class PhaseState:
    phase: int
    ledger: list[LedgerEntryV2] = field(default_factory=list)
    seq: dict[tuple[Category, str], int] = field(default_factory=dict)
    closeout: CloseoutTracker | None = None

    def next_seq(self, kind: Category, raiser: str) -> int:
        key = (kind, raiser)
        nxt = self.seq.get(key, 0) + 1
        self.seq[key] = nxt
        return nxt

    def find(self, item_id: str) -> LedgerEntryV2 | None:
        for e in self.ledger:
            if e.id == item_id:
                return e
        return None

    def item_views(self) -> list[_ItemView]:
        return [e.to_item_view() for e in self.ledger]


# ─── Round / phase results ────────────────────────────────────────────


@dataclass(frozen=True)
class RoundResult:
    """Result of processing one round (both agents' turns)."""

    round: int
    claude_status: str | None
    openai_status: str | None
    raised_events: tuple[ItemRaised, ...]
    transition_events: tuple[ItemTransitioned, ...]
    violation_events: tuple[CloseoutViolation, ...]
    closeout_event: CloseoutUrged | None
    converged: bool
    is_closeout_round: bool


@dataclass(frozen=True)
class PhaseRunResult:
    """Final outcome of running a phase end-to-end."""

    phase: int
    converged: bool
    rounds: int
    final_round: int
    via_closeout: bool
    via_ghost_cap: bool
    via_hard_cap: bool
    ledger: tuple[LedgerEntryV2, ...]
    converged_event: PhaseConverged | None
    # Spec 0137 — substantive-convergence escape valve. True when the
    # orchestrator declared convergence at a round where both agents
    # emitted AGREED with a terminal ledger but the strict three-gate
    # check_convergence rejected on the artifact-hash gate. The
    # canonical artifact body comes from the designated agent's turn
    # file regardless (claude for phase 0; the drafter for phase 2;
    # the drafter for phase 4), so the non-canonical agent's drift
    # does not block downstream consumption.
    via_artifact_promotion: bool = False


# ─── Agent-turn callable ─────────────────────────────────────────────


# In production this wraps the AgentCall + run_one_call pipeline; in
# tests it returns canned turn text.
AgentTurnFn = Callable[..., str]


@dataclass
class AgentTurnRequest:
    """Inputs to the agent-turn callable for a single round.

    ``is_closeout_round`` is True when the prior round triggered
    closeout. ``standing_items`` is a textual summary of non-terminal
    items rendered into the prompt's "Standing items" section.
    """

    phase: int
    round: int
    agent: str           # "claude" | "openai"
    other: str
    is_closeout_round: bool
    standing_items: str
    closeout_request: str


# ─── Phase runner ─────────────────────────────────────────────────────


class DeepResearchPhase:
    """Drive an interaction phase under the new Deep Research protocol.

    The caller supplies an ``agent_turn`` callable that, given a
    ``AgentTurnRequest``, returns the raw turn text (markdown). The
    runner parses, validates, applies lifecycle transitions, decides
    whether to urge closeout for the next round, and terminates when
    convergence fires (organic / via_closeout / via_ghost_cap /
    via_hard_cap).

    The runner is deliberately I/O-free: it does not write files,
    publish events to a bus, or call agents directly. Callers wrap
    those concerns around the loop. The returned ``PhaseRunResult``
    carries every event the orchestrator should publish.
    """

    def __init__(
        self,
        *,
        phase: int,
        agent_turn: AgentTurnFn,
        artifact_hash_match: Callable[[ParsedTurnV2, ParsedTurnV2], bool] | None = None,
        evidence_validator: Callable[
            [list, ParsedTurnV2, str],  # records, parsed, agent
            list,                        # list[EvidenceFlag]
        ] | None = None,
        caps_override=None,
    ) -> None:
        self.phase = phase
        self.agent_turn = agent_turn
        # ``artifact_hash_match`` is supplied by phase-specific wiring
        # (phase 0 hashes AGREED_INTERPRETATION, phase 2 hashes
        # AGREED_PLAN + DRAFTER, phase 4 cross-checks
        # AGREED_DRAFT_ACCEPTANCE + draft file hash). Default: compare
        # the raw ``phase_artifact`` strings via canonical_hash.
        self.artifact_hash_match = (
            artifact_hash_match or _default_artifact_hash_match
        )
        # ``evidence_validator`` is the anti-hallucination check that
        # consumes the parsed ADDRESS block's evidence records and the
        # turn's tool-call audit. Default: no-op (returns []) so unit
        # tests don't need to supply tool-call audits.
        self.evidence_validator = evidence_validator or (lambda recs, p, a: [])
        self.caps = caps_override or caps_for(phase)
        self.state = PhaseState(
            phase=phase,
            closeout=CloseoutTracker(
                phase=phase,
                initial_budget=self.caps.closeout_budget,
            ),
        )

    # ── Internal helpers ─────────────────────────────────────────

    def _build_standing_items_text(self) -> str:
        non_terminal = items_blocking_convergence(self.state.item_views())
        if not non_terminal:
            return "(none)"
        rows: list[str] = []
        for iv in non_terminal:
            ent = self.state.find(iv.id)
            if ent is None:
                continue
            rows.append(
                f"- [{ent.id}] ({ent.kind.value}, state: {ent.current_state.value}, "
                f"raiser: {ent.raiser}): {(ent.body or '').strip()[:200]}"
            )
        return "\n".join(rows)

    def _build_closeout_request_text(self, agent: str) -> str:
        non_terminal = items_blocking_convergence(self.state.item_views())
        if not non_terminal:
            return ""
        from dual_research.protocol.prompts import closeout_request_section

        owned = []
        for iv in non_terminal:
            ent = self.state.find(iv.id)
            if ent is None:
                continue
            if ent.raiser == agent:
                owned.append({
                    "id": ent.id,
                    "kind": ent.kind.value,
                    "body": ent.body,
                    "current_state": ent.current_state.value,
                })
        return closeout_request_section(
            items=owned,
            agent_name=agent,
            remaining_budget=self.state.closeout.remaining(agent),
        )

    def apply_turn(
        self,
        *,
        text: str,
        parsed: ParsedTurnV2,
        agent: str,
        round: int,
        is_closeout_round: bool,
    ) -> tuple[list[ItemRaised], list[ItemTransitioned], list[CloseoutViolation]]:
        """Apply a parsed turn to the ledger. Returns the events the
        orchestrator should publish."""
        raised_events: list[ItemRaised] = []
        transition_events: list[ItemTransitioned] = []
        violations: list[CloseoutViolation] = []

        other = "openai" if agent == "claude" else "claude"
        raiser_tok = raiser_letter(agent)

        # RAISE blocks → ledger entries + ItemRaised events. Dropped in
        # closeout rounds with a violation event each.
        for blk in parsed.blocks:
            if isinstance(blk, RaiseBlock):
                if is_closeout_round:
                    violations.append(CloseoutViolation(
                        phase=self.phase,
                        round=round,
                        agent=agent,
                        violation_code="closeout_violation_raise",
                        dropped_block=blk.raw_text[:1000],
                    ))
                    continue
                seq = self.state.next_seq(blk.kind, raiser_tok)
                item_id = format_id(blk.kind, self.phase, raiser_tok, seq)
                entry = LedgerEntryV2(
                    id=item_id,
                    kind=blk.kind,
                    phase=self.phase,
                    raiser=agent,
                    body=blk.body,
                    anchor_type=blk.anchor_type,
                    anchor_text=blk.anchor_text,
                    evidence_required=blk.evidence_required,
                    current_state=State.OPEN,
                    raised_round=round,
                )
                self.state.ledger.append(entry)
                raised_events.append(ItemRaised(
                    id=item_id,
                    item_kind=blk.kind.value,
                    phase=self.phase,
                    round=round,
                    raiser=agent,
                    body=blk.body,
                    anchor_type=blk.anchor_type,
                    anchor_text=blk.anchor_text,
                    evidence_required=blk.evidence_required,
                ))
            elif isinstance(blk, AddressBlock):
                ent = self.state.find(blk.item_id)
                if ent is None:
                    # Address of an unknown item is silently dropped;
                    # the validator already flagged it as malformed.
                    continue
                if ent.raiser == agent:
                    # An agent cannot ADDRESS their own item; ignore.
                    continue
                # Anti-hallucination validation when evidence is required.
                if ent.evidence_required:
                    flags = self.evidence_validator(blk.evidence, parsed, agent)
                    if flags:
                        # Evidence rejected → item stays in its current state.
                        # The orchestrator will urge closeout for this item
                        # in the next round. We still emit a transition
                        # event with the rejection reason for the audit
                        # trail.
                        continue
                from_state = ent.current_state
                to_state = State.ADDRESSED
                if from_state == to_state:
                    # No-op address (already addressed). Allow but
                    # don't emit a duplicate transition.
                    continue
                ent.current_state = to_state
                evidence_dicts = [
                    {
                        "item_id": ev.item_id,
                        "url": ev.url,
                        "title": ev.title,
                        "search_query": ev.search_query,
                        "fetched_at": ev.fetched_at,
                        "evidence_event_id": ev.evidence_event_id,
                        "content_excerpt": ev.content_excerpt,
                    }
                    for ev in blk.evidence
                ]
                transition = {
                    "from": from_state.value,
                    "to": to_state.value,
                    "round": round,
                    "actor": agent,
                    "reason": blk.response[:500],
                    "evidence_records": evidence_dicts,
                }
                ent.transitions.append(transition)
                transition_events.append(ItemTransitioned(
                    id=ent.id,
                    from_state=from_state.value,
                    to_state=to_state.value,
                    actor=agent,
                    phase=self.phase,
                    round=round,
                    reason=blk.response,
                    evidence_records=evidence_dicts,
                ))
                # acknowledged_proposed by the addressee: half of the
                # mutual handshake.
                if blk.proposes_status == "acknowledged_proposed":
                    ent.ack_proposed_by = agent
            elif isinstance(blk, ResolveBlock):
                ent = self.state.find(blk.item_id)
                if ent is None or ent.raiser != agent:
                    continue
                if ent.current_state != State.ADDRESSED:
                    continue
                from_state = ent.current_state
                ent.current_state = State.RESOLVED
                transition = {
                    "from": from_state.value,
                    "to": State.RESOLVED.value,
                    "round": round,
                    "actor": agent,
                    "reason": blk.reason,
                }
                ent.transitions.append(transition)
                transition_events.append(ItemTransitioned(
                    id=ent.id,
                    from_state=from_state.value,
                    to_state=State.RESOLVED.value,
                    actor=agent,
                    phase=self.phase,
                    round=round,
                    reason=blk.reason,
                ))
            elif isinstance(blk, WithdrawBlock):
                ent = self.state.find(blk.item_id)
                if ent is None or ent.raiser != agent:
                    continue
                if is_terminal(ent.current_state):
                    continue
                from_state = ent.current_state
                ent.current_state = State.WITHDRAWN
                transition = {
                    "from": from_state.value,
                    "to": State.WITHDRAWN.value,
                    "round": round,
                    "actor": agent,
                    "reason": blk.reason,
                }
                ent.transitions.append(transition)
                transition_events.append(ItemTransitioned(
                    id=ent.id,
                    from_state=from_state.value,
                    to_state=State.WITHDRAWN.value,
                    actor=agent,
                    phase=self.phase,
                    round=round,
                    reason=blk.reason,
                ))
            elif isinstance(blk, AcknowledgeBlock):
                ent = self.state.find(blk.item_id)
                if ent is None:
                    continue
                if is_terminal(ent.current_state):
                    continue
                # Mutual handshake: if the OTHER agent has already
                # proposed ack on this item, this ACKNOWLEDGE completes
                # the handshake and transitions to terminal.
                other_proposed = (
                    ent.ack_proposed_by is not None
                    and ent.ack_proposed_by != agent
                )
                if other_proposed:
                    from_state = ent.current_state
                    ent.current_state = State.ACKNOWLEDGED
                    transition = {
                        "from": from_state.value,
                        "to": State.ACKNOWLEDGED.value,
                        "round": round,
                        "actor": "mutual",
                        "reason": blk.reason,
                    }
                    ent.transitions.append(transition)
                    transition_events.append(ItemTransitioned(
                        id=ent.id,
                        from_state=from_state.value,
                        to_state=State.ACKNOWLEDGED.value,
                        actor="mutual",
                        phase=self.phase,
                        round=round,
                        reason=blk.reason,
                    ))
                else:
                    # First half of the handshake — record the proposal
                    # but do not transition.
                    ent.ack_proposed_by = agent

        return raised_events, transition_events, violations

    # ── Round driver ─────────────────────────────────────────────

    def process_round_end(
        self,
        *,
        parsed_claude: ParsedTurnV2 | None,
        parsed_openai: ParsedTurnV2 | None,
        round: int,
        is_closeout_round: bool,
        raised_events: list[ItemRaised],
        transition_events: list[ItemTransitioned],
        violation_events: list[CloseoutViolation],
    ) -> RoundResult:
        """End-of-round processing: convergence check + closeout urge decision.

        Used by the async production orchestrator after both agents'
        turns have been applied via ``apply_turn``. Returns a
        ``RoundResult`` bundle the caller publishes.
        """
        artifact_match = False
        if (
            parsed_claude is not None
            and parsed_openai is not None
            and parsed_claude.status == "AGREED"
            and parsed_openai.status == "AGREED"
        ):
            artifact_match = self.artifact_hash_match(parsed_claude, parsed_openai)

        conv = check_convergence(
            claude_status=parsed_claude.status if parsed_claude else None,
            openai_status=parsed_openai.status if parsed_openai else None,
            items=self.state.item_views(),
            artifact_hash_match=artifact_match,
        )

        closeout_evt: CloseoutUrged | None = None
        if not conv.converged and should_urge_closeout(
            claude_status=parsed_claude.status if parsed_claude else None,
            openai_status=parsed_openai.status if parsed_openai else None,
            items=self.state.item_views(),
        ):
            blocking = items_blocking_convergence(self.state.item_views())
            closeout_evt = CloseoutUrged(
                phase=self.phase,
                round=round,
                affected_items=[iv.id for iv in blocking],
                affected_raiser_budgets={
                    "claude": self.state.closeout.remaining("claude"),
                    "openai": self.state.closeout.remaining("openai"),
                },
            )

        return RoundResult(
            round=round,
            claude_status=parsed_claude.status if parsed_claude else None,
            openai_status=parsed_openai.status if parsed_openai else None,
            raised_events=tuple(raised_events),
            transition_events=tuple(transition_events),
            violation_events=tuple(violation_events),
            closeout_event=closeout_evt,
            converged=conv.converged,
            is_closeout_round=is_closeout_round,
        )

    def spend_failed_closeout_budget(self) -> bool:
        """Spend one closeout-round slot for each agent that still has
        blocking items they raised. Returns ``True`` if any agent's
        budget hit 0 with blocking items remaining (signals ghost-cap)."""
        for agent in ("claude", "openai"):
            owned = select_ghost_cap_items(
                agent=agent,
                items=self.state.item_views(),
            )
            if owned:
                self.state.closeout.decrement_on_fail(agent)
        return any(
            self.state.closeout.remaining(agent) <= 0
            and select_ghost_cap_items(
                agent=agent, items=self.state.item_views(),
            )
            for agent in ("claude", "openai")
        )

    def ghost_cap_remaining_items(self, *, round: int) -> list[ItemTransitioned]:
        """Public alias for ``_ghost_cap_all_blocking`` — called by the
        async production orchestrator when budget is exhausted."""
        return self._ghost_cap_all_blocking(round=round)

    def hard_cap_remaining_items(self, *, round: int) -> list[ItemTransitioned]:
        """Public alias for ``_hard_cap_all_blocking``."""
        return self._hard_cap_all_blocking(round=round)

    def build_phase_converged_event(
        self,
        *,
        final_round: int,
        via_closeout: bool,
        via_ghost_cap: bool,
        via_hard_cap: bool,
        via_artifact_promotion: bool = False,
    ) -> PhaseConverged:
        return PhaseConverged(
            phase=self.phase,
            final_round=final_round,
            via_closeout=via_closeout,
            via_ghost_cap=via_ghost_cap,
            via_hard_cap=via_hard_cap,
            via_artifact_promotion=via_artifact_promotion,
        )

    def run_round(self, *, round: int, is_closeout_round: bool) -> RoundResult:
        """Drive a single round: both agents' turns + lifecycle updates."""
        raised: list[ItemRaised] = []
        transitions: list[ItemTransitioned] = []
        violations: list[CloseoutViolation] = []

        parsed_claude: ParsedTurnV2 | None = None
        parsed_openai: ParsedTurnV2 | None = None

        for agent in ("claude", "openai"):
            other = "openai" if agent == "claude" else "claude"
            request = AgentTurnRequest(
                phase=self.phase,
                round=round,
                agent=agent,
                other=other,
                is_closeout_round=is_closeout_round,
                standing_items=self._build_standing_items_text(),
                closeout_request=self._build_closeout_request_text(agent),
            )
            text = self.agent_turn(request)
            parsed = parse_turn_v2(text)
            # Validate; structurally invalid turns are still applied
            # for what they parse, but the orchestrator should log the
            # validation result. The caller has access to it via the
            # parsed object.
            validate_parsed(
                text=text,
                blocks=parsed.blocks,
                phase=self.phase,
                round=round,
                agent=agent,
                is_closeout_round=is_closeout_round,
            )
            if agent == "claude":
                parsed_claude = parsed
            else:
                parsed_openai = parsed
            r, t, v = self.apply_turn(
                text=text,
                parsed=parsed,
                agent=agent,
                round=round,
                is_closeout_round=is_closeout_round,
            )
            raised.extend(r)
            transitions.extend(t)
            violations.extend(v)

        # Convergence cross-check
        artifact_match = False
        if (
            parsed_claude is not None
            and parsed_openai is not None
            and parsed_claude.status == "AGREED"
            and parsed_openai.status == "AGREED"
        ):
            artifact_match = self.artifact_hash_match(parsed_claude, parsed_openai)

        conv = check_convergence(
            claude_status=parsed_claude.status if parsed_claude else None,
            openai_status=parsed_openai.status if parsed_openai else None,
            items=self.state.item_views(),
            artifact_hash_match=artifact_match,
        )

        closeout_evt: CloseoutUrged | None = None
        if not conv.converged and should_urge_closeout(
            claude_status=parsed_claude.status if parsed_claude else None,
            openai_status=parsed_openai.status if parsed_openai else None,
            items=self.state.item_views(),
        ):
            blocking = items_blocking_convergence(self.state.item_views())
            closeout_evt = CloseoutUrged(
                phase=self.phase,
                round=round,
                affected_items=[iv.id for iv in blocking],
                affected_raiser_budgets={
                    "claude": self.state.closeout.remaining("claude"),
                    "openai": self.state.closeout.remaining("openai"),
                },
            )

        return RoundResult(
            round=round,
            claude_status=parsed_claude.status if parsed_claude else None,
            openai_status=parsed_openai.status if parsed_openai else None,
            raised_events=tuple(raised),
            transition_events=tuple(transitions),
            violation_events=tuple(violations),
            closeout_event=closeout_evt,
            converged=conv.converged,
            is_closeout_round=is_closeout_round,
        )

    # ── Cap / ghost-cap helpers ──────────────────────────────────

    def _ghost_cap_all_blocking(self, *, round: int) -> list[ItemTransitioned]:
        """Auto-cap remaining non-terminal items with ``via: ghost_cap``."""
        events: list[ItemTransitioned] = []
        for ent in self.state.ledger:
            if is_terminal(ent.current_state):
                continue
            reason = ghost_cap_reason(
                ent.raiser,
                round=round,
                budget_used=self.state.closeout.closeout_rounds_used[ent.raiser],
            )
            from_state = ent.current_state
            ent.current_state = State.CAPPED
            ent.transitions.append({
                "from": from_state.value,
                "to": State.CAPPED.value,
                "round": round,
                "actor": "orchestrator",
                "reason": reason,
                "via": "ghost_cap",
            })
            events.append(ItemTransitioned(
                id=ent.id,
                from_state=from_state.value,
                to_state=State.CAPPED.value,
                actor="orchestrator",
                phase=self.phase,
                round=round,
                reason=reason,
                via="ghost_cap",
            ))
        return events

    def _hard_cap_all_blocking(self, *, round: int) -> list[ItemTransitioned]:
        """Auto-cap remaining non-terminal items with ``via: hard_cap``."""
        events: list[ItemTransitioned] = []
        reason = hard_cap_reason(self.phase, round=round)
        for ent in self.state.ledger:
            if is_terminal(ent.current_state):
                continue
            from_state = ent.current_state
            ent.current_state = State.CAPPED
            ent.transitions.append({
                "from": from_state.value,
                "to": State.CAPPED.value,
                "round": round,
                "actor": "orchestrator",
                "reason": reason,
                "via": "hard_cap",
            })
            events.append(ItemTransitioned(
                id=ent.id,
                from_state=from_state.value,
                to_state=State.CAPPED.value,
                actor="orchestrator",
                phase=self.phase,
                round=round,
                reason=reason,
                via="hard_cap",
            ))
        return events

    # ── Phase driver ─────────────────────────────────────────────

    def run(self) -> tuple[PhaseRunResult, list]:
        """Run the phase end-to-end. Returns (result, all_events)."""
        from dual_research.events import ArtifactCanonicallyPromoted

        all_events: list = []
        is_closeout_round = False
        final_round = 0
        via_closeout = False
        via_ghost_cap = False
        via_hard_cap = False
        via_artifact_promotion = False
        converged = False
        round_no = 0

        # Hard cap: at most caps.hard rounds total (including any
        # closeout rounds).
        while round_no < self.caps.hard:
            round_no += 1
            final_round = round_no
            rr = self.run_round(
                round=round_no,
                is_closeout_round=is_closeout_round,
            )
            all_events.extend(rr.raised_events)
            all_events.extend(rr.transition_events)
            all_events.extend(rr.violation_events)
            if rr.closeout_event is not None:
                all_events.append(rr.closeout_event)

            if rr.converged:
                converged = True
                via_closeout = is_closeout_round
                break

            # Spec 0137 (widened by 0140) — substantive-convergence
            # escape valve. Mirrors the production-path branch in
            # ``dr_run._drive_interaction_phase``. Original 0137 form:
            # both AGREED + terminal ledger with hash drift. 0140
            # widening: one agent AGREED + terminal ledger past the
            # soft cap is also a deadlock shape — the other agent is
            # blocked on something the protocol cannot surface
            # (typically a stub draft from a prior-round extractor
            # truncation).
            both_agreed = (
                rr.claude_status == "AGREED" and rr.openai_status == "AGREED"
            )
            one_agreed = (
                (rr.claude_status == "AGREED") ^ (rr.openai_status == "AGREED")
            )
            terminal_ledger = not items_blocking_convergence(self.state.item_views())

            if terminal_ledger and (
                both_agreed
                or (one_agreed and round_no >= self.caps.soft)
            ):
                converged = True
                via_artifact_promotion = True
                all_events.append(ArtifactCanonicallyPromoted(
                    phase=f"phase{self.phase}",
                    round=round_no,
                ))
                break

            if rr.closeout_event is not None:
                # The round attempted convergence but left items
                # non-terminal. Spend budget if we WERE in a closeout
                # round; otherwise, set up the next round as a
                # closeout round.
                if is_closeout_round:
                    for agent in ("claude", "openai"):
                        # Only burn budget for agents who still have
                        # non-terminal items they raised.
                        owned_blocking = select_ghost_cap_items(
                            agent=agent,
                            items=self.state.item_views(),
                        )
                        if owned_blocking:
                            self.state.closeout.decrement_on_fail(agent)
                    # If any side is now out of budget AND still has
                    # blocking items, ghost-cap the rest.
                    out_of_budget = any(
                        self.state.closeout.remaining(agent) <= 0
                        and select_ghost_cap_items(
                            agent=agent,
                            items=self.state.item_views(),
                        )
                        for agent in ("claude", "openai")
                    )
                    if out_of_budget:
                        ghost = self._ghost_cap_all_blocking(round=round_no)
                        all_events.extend(ghost)
                        via_ghost_cap = True
                        converged = True
                        break
                # Next round is a closeout round (continues if budget
                # remains).
                is_closeout_round = True
                continue

            # Convergence did NOT fire, no closeout urged. Just keep
            # going as a normal round.
            is_closeout_round = False

        if not converged and round_no >= self.caps.hard:
            # Hit hard cap without convergence — auto-cap any remaining
            # non-terminal items and flag the run as via-hard-cap so the
            # UI status pipeline can mark it deadlocked. Spec 0136
            # dropped the ``if hard_caps:`` gate: pre-spec the
            # "every-item-terminal-but-no-AGREED" pattern returned
            # ``converged=False, via_hard_cap=False`` and the orchestrator
            # exit code stayed at 0, which the UI then rendered as a
            # silent "completed". The async ``_drive_interaction_phase``
            # in ``dr_run.py`` carries the same fix.
            hard_caps = self._hard_cap_all_blocking(round=round_no)
            all_events.extend(hard_caps)  # may be empty; that's fine
            via_hard_cap = True
            converged = True

        converged_event: PhaseConverged | None = None
        if converged:
            converged_event = PhaseConverged(
                phase=self.phase,
                final_round=final_round,
                via_closeout=via_closeout,
                via_ghost_cap=via_ghost_cap,
                via_hard_cap=via_hard_cap,
                via_artifact_promotion=via_artifact_promotion,
            )
            all_events.append(converged_event)

        result = PhaseRunResult(
            phase=self.phase,
            converged=converged,
            rounds=round_no,
            final_round=final_round,
            via_closeout=via_closeout,
            via_ghost_cap=via_ghost_cap,
            via_hard_cap=via_hard_cap,
            ledger=tuple(self.state.ledger),
            converged_event=converged_event,
            via_artifact_promotion=via_artifact_promotion,
        )
        return result, all_events


def _default_artifact_hash_match(
    a: ParsedTurnV2,
    b: ParsedTurnV2,
) -> bool:
    """Default convergence cross-check on phase_artifact text.

    Phase-specific wiring overrides this to add extra invariants
    (phase 2's DRAFTER agreement, phase 4's draft file hash match).
    """
    return (
        a.phase_artifact is not None
        and b.phase_artifact is not None
        and canonical_hash(a.phase_artifact) == canonical_hash(b.phase_artifact)
    )


__all__ = [
    "AgentTurnFn",
    "AgentTurnRequest",
    "DeepResearchPhase",
    "LedgerEntryV2",
    "PhaseRunResult",
    "PhaseState",
    "RoundResult",
]
