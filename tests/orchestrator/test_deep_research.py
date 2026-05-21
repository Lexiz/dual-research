"""Spec 0114 — Deep Research phase orchestrator integration tests.

Each scenario the spec's test plan calls out:
- Closeout mechanism fires when both AGREED but non-terminal items remain;
  budget decrements; ghost-cap fires at exhaustion.
- Hard-cap behavior — agents never reach AGREED; hard cap fires; all
  non-terminal items auto-cap with ``via: hard_cap``.
- Evidence anti-hallucination — fabricated event_id rejects the ADDRESS;
  the item stays non-terminal; closeout urge fires next round.
- Backward-compat shim — legacy event payloads derived from ledger snapshot.

All tests drive ``DeepResearchPhase`` with a canned ``agent_turn``
callable that returns synthetic turn text per round/agent. No I/O, no
async, no LLM calls.
"""

from __future__ import annotations

from typing import Callable

from dual_research.contract.caps import PhaseCaps
from dual_research.contract.categories import Category
from dual_research.contract.lifecycle import State
from dual_research.contract.operations import (
    AcknowledgeBlock,
    AddressBlock,
    RaiseBlock,
    ResolveBlock,
)
from dual_research.events import (
    ArtifactCanonicallyPromoted,
    CloseoutUrged,
    CloseoutViolation,
    EmptyTurnDetected,
    ItemRaised,
    ItemTransitioned,
    PhaseConverged,
    ProtocolViolation,
)
from dual_research.orchestrator.deep_research import LedgerEntryV2
from dual_research.protocol.parse_v2 import ParsedTurnV2
# Spec 0115 — legacy_shim removed; the shim-test below is also gone.
from dual_research.orchestrator.deep_research import (
    AgentTurnRequest,
    DeepResearchPhase,
)


# ─── Test fixtures — canned turn text builders ────────────────────────


_STATUS_FOOTER = """\
## Status
STATUS: {status}
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""


def _wrap_turn(*, status: str, body_sections: dict[str, str], artifact: str = "") -> str:
    parts = ["## Stance\nposition.\n"]
    for section_name in (
        "Addressing items raised against me",
        "Ratifying my own items",
        "New items I'm raising",
    ):
        body = body_sections.get(section_name, "(none)")
        parts.append(f"## {section_name}\n{body}\n")
    if artifact:
        parts.append(f"## Phase artifact\n\n{artifact}\n")
    parts.append(_STATUS_FOOTER.format(status=status))
    return "\n".join(parts)


def _raise_block(*, kind: str, body: str) -> str:
    return (
        f"### RAISE\n"
        f"kind: {kind}\n"
        f"body: |\n  {body}\n"
        f"anchor_type: none\n"
        f"anchor_text:\n"
        f"evidence_required: false\n"
    )


def _resolve_block(*, item_id: str, reason: str) -> str:
    return f"### RESOLVE {item_id}\nreason: |\n  {reason}\n"


def _address_block(*, item_id: str, response: str) -> str:
    return (
        f"### ADDRESS {item_id}\n"
        f"response: |\n  {response}\n"
        f"proposes_status: addressed\n"
    )


def _withdraw_block(*, item_id: str, reason: str) -> str:
    return f"### WITHDRAW {item_id}\nreason: |\n  {reason}\n"


def _ack_block_ratifying(*, item_id: str, reason: str) -> str:
    return f"### ACKNOWLEDGE {item_id}\nreason: |\n  {reason}\n"


def _ack_block_addressing(*, item_id: str, reason: str) -> str:
    return f"### ACKNOWLEDGE {item_id}\nreason: |\n  {reason}\n"


# ─── Scripted-agent helper ────────────────────────────────────────────


def make_scripted_agent(
    scripts: dict[tuple[int, str], str],
) -> Callable[[AgentTurnRequest], str]:
    """Return an ``agent_turn`` callable that looks up turn text by
    (round, agent). KeyError if the round/agent pair is missing —
    tests should always cover every round both agents see."""

    def _agent(req: AgentTurnRequest) -> str:
        return scripts[(req.round, req.agent)]

    return _agent


# ─── Scenario: closeout fires + ghost-cap ─────────────────────────────


def test_closeout_fires_and_ghost_caps_at_budget_exhaustion():
    """Both agents AGREE at round 2 with a non-terminal item → closeout
    fires for round 3. Both AGREE again at round 3 still with the item
    non-terminal → budget burns; round 4 same → ghost-cap fires."""
    # Use a small budget (1) to keep the test compact.
    caps = PhaseCaps(soft=2, hard=8, closeout_budget=1)

    scripts: dict[tuple[int, str], str] = {}
    # Round 1: claude raises a disagreement; openai does nothing.
    scripts[(1, "claude")] = _wrap_turn(
        status="IN_PROGRESS",
        body_sections={
            "New items I'm raising": _raise_block(
                kind="disagreement", body="i hold X.",
            ),
        },
    )
    scripts[(1, "openai")] = _wrap_turn(status="IN_PROGRESS", body_sections={})

    # Round 2: openai addresses; claude is silent. Both AGREE.
    # Item is now `addressed` (claude raised → openai addressed).
    scripts[(2, "claude")] = _wrap_turn(
        status="AGREED",
        body_sections={},
        artifact="### AGREED_PLAN\nshared",
    )
    scripts[(2, "openai")] = _wrap_turn(
        status="AGREED",
        body_sections={
            "Addressing items raised against me": _address_block(
                item_id="D-plan-c-01", response="here is my view.",
            ),
        },
        artifact="### AGREED_PLAN\nshared",
    )

    # Round 3 (closeout round): neither side ratifies. Both AGREE again.
    scripts[(3, "claude")] = _wrap_turn(
        status="AGREED",
        body_sections={},
        artifact="### AGREED_PLAN\nshared",
    )
    scripts[(3, "openai")] = _wrap_turn(
        status="AGREED",
        body_sections={},
        artifact="### AGREED_PLAN\nshared",
    )

    # Round 4 (closeout round, budget=0 for claude): claude still
    # doesn't ratify → ghost-cap fires.
    scripts[(4, "claude")] = _wrap_turn(
        status="AGREED",
        body_sections={},
        artifact="### AGREED_PLAN\nshared",
    )
    scripts[(4, "openai")] = _wrap_turn(
        status="AGREED",
        body_sections={},
        artifact="### AGREED_PLAN\nshared",
    )

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        caps_override=caps,
    )
    result, events = phase.run()

    # Closeout urged event fired at round 2
    closeout_events = [e for e in events if isinstance(e, CloseoutUrged)]
    assert len(closeout_events) >= 1
    assert closeout_events[0].round == 2

    # Phase converged via ghost-cap
    assert result.converged is True
    assert result.via_ghost_cap is True
    assert result.via_closeout is False
    assert result.via_hard_cap is False

    # The disagreement item is now capped
    capped_transitions = [
        e for e in events
        if isinstance(e, ItemTransitioned) and e.to_state == "capped"
    ]
    assert len(capped_transitions) == 1
    assert capped_transitions[0].via == "ghost_cap"
    assert capped_transitions[0].actor == "orchestrator"


# ─── Scenario: organic convergence with closeout cleanup ──────────────


def test_organic_convergence_after_closeout_cleanup():
    """Both AGREE at round 2 with addressed item → closeout round 3 →
    claude resolves → convergence fires (via_closeout=True)."""
    caps = PhaseCaps(soft=2, hard=8, closeout_budget=2)

    scripts: dict[tuple[int, str], str] = {}
    scripts[(1, "claude")] = _wrap_turn(
        status="IN_PROGRESS",
        body_sections={
            "New items I'm raising": _raise_block(
                kind="question", body="how about X?",
            ),
        },
    )
    scripts[(1, "openai")] = _wrap_turn(status="IN_PROGRESS", body_sections={})

    scripts[(2, "claude")] = _wrap_turn(
        status="AGREED",
        body_sections={},
        artifact="### AGREED_PLAN\nshared",
    )
    scripts[(2, "openai")] = _wrap_turn(
        status="AGREED",
        body_sections={
            "Addressing items raised against me": _address_block(
                item_id="Q-plan-c-01", response="here is my answer.",
            ),
        },
        artifact="### AGREED_PLAN\nshared",
    )

    # Closeout round 3: claude resolves the item; both AGREE.
    scripts[(3, "claude")] = _wrap_turn(
        status="AGREED",
        body_sections={
            "Ratifying my own items": _resolve_block(
                item_id="Q-plan-c-01", reason="the answer convinced me.",
            ),
        },
        artifact="### AGREED_PLAN\nshared",
    )
    scripts[(3, "openai")] = _wrap_turn(
        status="AGREED",
        body_sections={},
        artifact="### AGREED_PLAN\nshared",
    )

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        caps_override=caps,
    )
    result, events = phase.run()

    assert result.converged is True
    assert result.via_closeout is True
    assert result.via_ghost_cap is False
    assert result.via_hard_cap is False

    # Item is resolved, not capped
    converged_event = [e for e in events if isinstance(e, PhaseConverged)][0]
    assert converged_event.via_closeout is True


# ─── Scenario: hard cap fires when agents never converge ──────────────


def test_hard_cap_with_no_remaining_items_still_marks_via_hard_cap():
    """Spec 0136 — agents never reach AGREED but never raise any items
    either. Hard cap fires at round 4; ``hard_cap_remaining_items``
    returns ``[]`` because there are no items to cap. Pre-spec the
    gating ``if hard_caps:`` predicate let this case return
    ``converged=False, via_hard_cap=False`` and the orchestrator
    exit code stayed at 0 (silent-exit deadlock). Post-spec the
    predicate is gone: ``via_hard_cap=True`` regardless of
    remaining-item count."""
    caps = PhaseCaps(soft=2, hard=4, closeout_budget=2)

    scripts: dict[tuple[int, str], str] = {}
    for r in range(1, 5):
        for agent in ("claude", "openai"):
            scripts[(r, agent)] = _wrap_turn(status="IN_PROGRESS", body_sections={})

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        caps_override=caps,
    )
    result, events = phase.run()

    assert result.converged is True
    assert result.via_hard_cap is True
    # No items raised → no items capped.
    capped = [e for e in events if isinstance(e, ItemTransitioned) and e.to_state == "capped"]
    assert capped == []
    # PhaseConverged event still emits with via_hard_cap=True.
    converged_events = [e for e in events if isinstance(e, PhaseConverged)]
    assert len(converged_events) == 1
    assert converged_events[0].via_hard_cap is True


def test_hard_cap_auto_caps_remaining_items():
    """Agents never reach AGREED. Hard cap fires at round 4 (caps.hard
    overridden to 4). All non-terminal items auto-cap via hard_cap."""
    caps = PhaseCaps(soft=2, hard=4, closeout_budget=2)

    scripts: dict[tuple[int, str], str] = {}
    scripts[(1, "claude")] = _wrap_turn(
        status="IN_PROGRESS",
        body_sections={
            "New items I'm raising": _raise_block(
                kind="disagreement", body="i hold A.",
            ),
        },
    )
    scripts[(1, "openai")] = _wrap_turn(
        status="IN_PROGRESS",
        body_sections={
            "New items I'm raising": _raise_block(
                kind="disagreement", body="i hold B.",
            ),
        },
    )
    # Rounds 2-4: stay IN_PROGRESS doing nothing. Hard cap fires at end of 4.
    for r in (2, 3, 4):
        for agent in ("claude", "openai"):
            scripts[(r, agent)] = _wrap_turn(status="IN_PROGRESS", body_sections={})

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        caps_override=caps,
    )
    result, events = phase.run()

    assert result.converged is True
    assert result.via_hard_cap is True
    assert result.via_ghost_cap is False
    assert result.via_closeout is False

    capped = [e for e in events if isinstance(e, ItemTransitioned) and e.to_state == "capped"]
    assert len(capped) == 2
    assert all(e.via == "hard_cap" for e in capped)


# ─── Scenario: evidence anti-hallucination rejects ADDRESS ────────────


def test_evidence_fabricated_event_id_annotates_unverified():
    """Spec 0144 §6.1.c — an ADDRESS with evidence_required=True but
    fabricated evidence_event_id no longer blocks the transition. The
    item moves to ``addressed`` but the offending evidence record is
    annotated with ``unverified=True`` so the UI can render a ⚠ chip
    on the source row. Pre-spec behaviour (silent drop) is the
    structural defect this fix closes."""
    caps = PhaseCaps(soft=2, hard=8, closeout_budget=2)

    scripts: dict[tuple[int, str], str] = {}
    # Round 1: claude raises evidence-required disagreement.
    scripts[(1, "claude")] = _wrap_turn(
        status="IN_PROGRESS",
        body_sections={
            "New items I'm raising": (
                "### RAISE\n"
                "kind: disagreement\n"
                "body: |\n  the version is X.\n"
                "anchor_type: none\n"
                "anchor_text:\n"
                "evidence_required: true\n"
            ),
        },
    )
    scripts[(1, "openai")] = _wrap_turn(status="IN_PROGRESS", body_sections={})

    # Round 2: openai addresses with a fabricated evidence record.
    # Both AGREE at round 2.
    address_with_bad_evidence = (
        "### ADDRESS D-plan-c-01\n"
        "response: |\n  my evidence says Y.\n"
        "evidence:\n"
        "  - url: https://example.com/page\n"
        "    title: page\n"
        "    search_query: q\n"
        "    fetched_at: 2026-05-19T12:00:00Z\n"
        "    evidence_event_id: srvtoolu_fake\n"
        "    content_excerpt: |\n"
        "      " + ("x" * 250) + "\n"
        "proposes_status: addressed\n"
    )
    scripts[(2, "claude")] = _wrap_turn(
        status="AGREED",
        body_sections={},
        artifact="### AGREED_PLAN\nshared",
    )
    scripts[(2, "openai")] = _wrap_turn(
        status="AGREED",
        body_sections={"Addressing items raised against me": address_with_bad_evidence},
        artifact="### AGREED_PLAN\nshared",
    )

    # Round 3 (closeout) and beyond — nothing happens. Test only verifies
    # round-2 behavior; we just need enough rounds to exit without exception.
    for r in (3, 4, 5, 6, 7, 8):
        for agent in ("claude", "openai"):
            scripts[(r, agent)] = _wrap_turn(status="IN_PROGRESS", body_sections={})

    # Stub evidence validator that always flags fabricated event ids.
    # Spec 0144 widened the slot to a 4-arg signature so the audit
    # tool_events list can ride along with the call.
    from dual_research.contract.evidence import EvidenceFlag

    def reject_fabricated(records, parsed, agent, audit_tool_events):
        flags = []
        for rec in records:
            if rec.evidence_event_id == "srvtoolu_fake":
                flags.append(EvidenceFlag(
                    code="evidence_event_id_fabricated",
                    message="fabricated",
                    record=rec,
                ))
        return flags

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        caps_override=caps,
        evidence_validator=reject_fabricated,
    )
    result, events = phase.run()

    # Spec 0144 — the transition DOES land (no silent drop). The
    # offending evidence record is annotated with unverified=True and
    # carries the validator's flag code in unverified_reason.
    addressed = [
        e for e in events
        if isinstance(e, ItemTransitioned) and e.to_state == "addressed"
    ]
    assert len(addressed) == 1, f"expected one addressed transition; got {len(addressed)}"
    ev_recs = addressed[0].evidence_records
    assert len(ev_recs) == 1
    assert ev_recs[0]["unverified"] is True
    assert ev_recs[0]["unverified_reason"] == "evidence_event_id_fabricated"

    # The item is now ``addressed`` (not terminal); the raiser can
    # still RESOLVE/ACKNOWLEDGE in a later round. Closeout fires only
    # if the standing item set is non-empty at end-of-round AGREED;
    # since the address landed, the item moved to addressed but is
    # still non-terminal, so closeout still urges. The annotator
    # semantics preserve the closeout-urge dynamic exactly as the
    # spec §6.1.c verbatim goal states.
    closeout_events = [e for e in events if isinstance(e, CloseoutUrged)]
    assert len(closeout_events) >= 1
    assert closeout_events[0].round == 2


# ─── Scenario: closeout-round RAISE blocks dropped ────────────────────


def test_raise_in_closeout_round_dropped_with_violation():
    caps = PhaseCaps(soft=2, hard=8, closeout_budget=2)

    scripts: dict[tuple[int, str], str] = {}
    # Round 1: claude raises a disagreement.
    scripts[(1, "claude")] = _wrap_turn(
        status="IN_PROGRESS",
        body_sections={
            "New items I'm raising": _raise_block(
                kind="disagreement", body="i hold X.",
            ),
        },
    )
    scripts[(1, "openai")] = _wrap_turn(status="IN_PROGRESS", body_sections={})

    # Round 2: openai addresses. Both AGREE → closeout urged.
    scripts[(2, "claude")] = _wrap_turn(
        status="AGREED", body_sections={}, artifact="### AGREED_PLAN\nshared",
    )
    scripts[(2, "openai")] = _wrap_turn(
        status="AGREED",
        body_sections={
            "Addressing items raised against me": _address_block(
                item_id="D-plan-c-01", response="my response.",
            ),
        },
        artifact="### AGREED_PLAN\nshared",
    )

    # Round 3 (closeout): claude RESOLVES the existing item AND
    # attempts to raise a new one (should be dropped + violation).
    scripts[(3, "claude")] = _wrap_turn(
        status="AGREED",
        body_sections={
            "Ratifying my own items": _resolve_block(
                item_id="D-plan-c-01", reason="convinced.",
            ),
            "New items I'm raising": _raise_block(
                kind="question", body="late question.",
            ),
        },
        artifact="### AGREED_PLAN\nshared",
    )
    scripts[(3, "openai")] = _wrap_turn(
        status="AGREED", body_sections={}, artifact="### AGREED_PLAN\nshared",
    )

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        caps_override=caps,
    )
    result, events = phase.run()

    violations = [e for e in events if isinstance(e, CloseoutViolation)]
    assert len(violations) == 1
    assert violations[0].violation_code == "closeout_violation_raise"
    assert violations[0].agent == "claude"
    assert violations[0].round == 3
    assert result.converged is True
    # No question was added to the ledger (RAISE was dropped)
    raised = [e for e in events if isinstance(e, ItemRaised)]
    assert len(raised) == 1
    assert raised[0].item_kind == "disagreement"


# Spec 0115 — the "legacy shim derives counters" scenario was deleted
# along with events/legacy_shim.py. The new-protocol UI reads
# per-category counters directly from the ItemRaised /
# ItemTransitioned event stream via ui.items.aggregate_items;
# verified in tests/ui/test_items.py.


# ─── Spec 0137 — substantive-convergence escape valve ─────────────────


def _hash_mismatch_match(a, b) -> bool:
    """artifact_hash_match stub that always rejects — simulates the
    production failure mode where agents emit semantically-equivalent
    but byte-different artifact bodies."""
    return False


def _hash_match(a, b) -> bool:
    """artifact_hash_match stub that always accepts — simulates organic
    byte-equal convergence."""
    return True


def test_artifact_promotion_fires_when_both_agreed_ledger_terminal_hash_drifts():
    """Spec 0137 — substantive-convergence escape valve.

    Round 1: claude raises a question; openai is silent.
    Round 2: openai addresses (item → addressed); both IN_PROGRESS.
    Round 3: claude resolves (item → resolved, terminal); both AGREED
    with DIFFERENT artifact text (the hash-drift signature).
    The artifact_hash_match stub rejects. The escape valve fires:
    result.via_artifact_promotion=True, the phase converges at
    round 3, and an ArtifactCanonicallyPromoted event is emitted."""
    caps = PhaseCaps(soft=2, hard=8, closeout_budget=2)

    scripts: dict[tuple[int, str], str] = {}
    scripts[(1, "claude")] = _wrap_turn(
        status="IN_PROGRESS",
        body_sections={
            "New items I'm raising": _raise_block(
                kind="question", body="how about X?",
            ),
        },
    )
    scripts[(1, "openai")] = _wrap_turn(status="IN_PROGRESS", body_sections={})

    # Round 2: openai addresses the question. Item → ADDRESSED. Both
    # still negotiating.
    scripts[(2, "claude")] = _wrap_turn(status="IN_PROGRESS", body_sections={})
    scripts[(2, "openai")] = _wrap_turn(
        status="IN_PROGRESS",
        body_sections={
            "Addressing items raised against me": _address_block(
                item_id="Q-plan-c-01", response="here is my answer.",
            ),
        },
    )

    # Round 3: claude resolves; both emit AGREED with byte-different
    # artifacts. Ledger fully terminal.
    scripts[(3, "claude")] = _wrap_turn(
        status="AGREED",
        body_sections={
            "Ratifying my own items": _resolve_block(
                item_id="Q-plan-c-01", reason="the answer convinced me.",
            ),
        },
        artifact="### AGREED_PLAN\nclaude wrote this version",
    )
    scripts[(3, "openai")] = _wrap_turn(
        status="AGREED",
        body_sections={},
        artifact="### AGREED_PLAN\nopenai wrote this DIFFERENT version",
    )

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        artifact_hash_match=_hash_mismatch_match,
        caps_override=caps,
    )
    result, events = phase.run()

    assert result.converged is True
    assert result.via_artifact_promotion is True
    assert result.via_closeout is False
    assert result.via_ghost_cap is False
    assert result.via_hard_cap is False
    assert result.final_round == 3

    promoted = [e for e in events if isinstance(e, ArtifactCanonicallyPromoted)]
    assert len(promoted) == 1
    assert promoted[0].phase == "phase2"
    assert promoted[0].round == 3

    converged_events = [e for e in events if isinstance(e, PhaseConverged)]
    assert len(converged_events) == 1
    assert converged_events[0].via_artifact_promotion is True


def test_artifact_promotion_does_not_fire_when_ledger_has_open_items():
    """Spec 0137 — the escape valve must NOT fire when items are
    non-terminal, even if both agents emit AGREED with hash drift.
    The closeout mechanism must take precedence (this is the existing
    closeout-urge path)."""
    caps = PhaseCaps(soft=2, hard=8, closeout_budget=2)

    scripts: dict[tuple[int, str], str] = {}
    scripts[(1, "claude")] = _wrap_turn(
        status="IN_PROGRESS",
        body_sections={
            "New items I'm raising": _raise_block(
                kind="question", body="how about X?",
            ),
        },
    )
    scripts[(1, "openai")] = _wrap_turn(status="IN_PROGRESS", body_sections={})

    # Round 2: openai addresses, both AGREE. Item is now `addressed`
    # (non-terminal) — closeout should urge, not artifact-promote.
    scripts[(2, "claude")] = _wrap_turn(
        status="AGREED",
        body_sections={},
        artifact="### AGREED_PLAN\nclaude version",
    )
    scripts[(2, "openai")] = _wrap_turn(
        status="AGREED",
        body_sections={
            "Addressing items raised against me": _address_block(
                item_id="Q-plan-c-01", response="here is my answer.",
            ),
        },
        artifact="### AGREED_PLAN\nopenai DIFFERENT version",
    )

    # Round 3 (closeout round): both still don't ratify. Same artifact
    # drift. Closeout budget decrements, but artifact promotion still
    # must not fire while the item is non-terminal.
    scripts[(3, "claude")] = _wrap_turn(
        status="AGREED", body_sections={},
        artifact="### AGREED_PLAN\nclaude version",
    )
    scripts[(3, "openai")] = _wrap_turn(
        status="AGREED", body_sections={},
        artifact="### AGREED_PLAN\nopenai DIFFERENT version",
    )

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        artifact_hash_match=_hash_mismatch_match,
        caps_override=PhaseCaps(soft=2, hard=4, closeout_budget=1),
    )
    result, events = phase.run()

    # Should NOT have fired artifact promotion — closeout urged
    # instead, and at budget exhaustion the item ghost-caps.
    promoted = [e for e in events if isinstance(e, ArtifactCanonicallyPromoted)]
    assert promoted == [], (
        "artifact promotion fired despite non-terminal item; "
        "this would short-circuit the closeout mechanism."
    )
    assert result.via_artifact_promotion is False
    # The closeout path runs — exact via_* depends on budget timing,
    # but result.converged must still be True.
    assert result.converged is True


def test_artifact_promotion_does_not_fire_when_only_one_agreed_below_soft_cap():
    """Spec 0140 — the widened one-agent-AGREED branch is gated on
    ``round_no >= caps.soft``. Below the soft cap, one-sided AGREED +
    terminal ledger continues the loop. This protects the early-round
    case where the other agent has not yet had a chance to surface its
    objections into the ledger."""
    # soft=5 keeps every round (1..4) strictly below the soft-cap gate;
    # hard=4 bounds the test so it exits via hard cap, not the widening.
    caps = PhaseCaps(soft=5, hard=4, closeout_budget=2)

    scripts: dict[tuple[int, str], str] = {}
    for r in (1, 2, 3, 4):
        # Claude AGREED with terminal (empty) ledger; openai still
        # IN_PROGRESS. Widened branch must NOT fire because
        # round_no (max 4) < caps.soft (5).
        scripts[(r, "claude")] = _wrap_turn(
            status="AGREED", body_sections={},
            artifact="### AGREED_PLAN\nclaude version",
        )
        scripts[(r, "openai")] = _wrap_turn(
            status="IN_PROGRESS", body_sections={},
        )

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        artifact_hash_match=_hash_mismatch_match,
        caps_override=caps,
    )
    result, events = phase.run()

    promoted = [e for e in events if isinstance(e, ArtifactCanonicallyPromoted)]
    assert promoted == []
    assert result.via_artifact_promotion is False
    # Should hard-cap instead.
    assert result.via_hard_cap is True


def test_artifact_promotion_fires_when_one_agreed_terminal_past_soft_cap():
    """Spec 0140 — at or past the soft cap, one-agent-AGREED + terminal
    ledger fires the widened escape valve. This catches the anchor-run
    deadlock shape: one reviewer stuck on protocol semantics (e.g.
    blocked on a 76-byte stub draft) while the ledger is otherwise
    quiet."""
    # soft=2, hard=8 — round 2 is the first round that satisfies the
    # ``round_no >= caps.soft`` gate. The test asserts the widening
    # fires exactly there rather than burning to hard cap.
    caps = PhaseCaps(soft=2, hard=8, closeout_budget=2)

    scripts: dict[tuple[int, str], str] = {}
    # Round 1: both IN_PROGRESS, ledger empty. Loop continues.
    scripts[(1, "claude")] = _wrap_turn(status="IN_PROGRESS", body_sections={})
    scripts[(1, "openai")] = _wrap_turn(status="IN_PROGRESS", body_sections={})
    # Round 2: claude AGREED, openai IN_PROGRESS, ledger still empty
    # (terminal). round_no (2) >= caps.soft (2) — widening fires.
    scripts[(2, "claude")] = _wrap_turn(
        status="AGREED", body_sections={},
        artifact="### AGREED_PLAN\nclaude version",
    )
    scripts[(2, "openai")] = _wrap_turn(
        status="IN_PROGRESS", body_sections={},
    )

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        artifact_hash_match=_hash_mismatch_match,
        caps_override=caps,
    )
    result, events = phase.run()

    assert result.converged is True
    assert result.via_artifact_promotion is True
    assert result.via_hard_cap is False
    assert result.via_closeout is False
    assert result.via_ghost_cap is False
    assert result.final_round == 2

    promoted = [e for e in events if isinstance(e, ArtifactCanonicallyPromoted)]
    assert len(promoted) == 1
    assert promoted[0].phase == "phase2"
    assert promoted[0].round == 2

    converged_events = [e for e in events if isinstance(e, PhaseConverged)]
    assert len(converged_events) == 1
    assert converged_events[0].via_artifact_promotion is True


def test_organic_convergence_keeps_all_via_flags_false():
    """Spec 0137 sanity — when the artifact hashes DO match (organic
    convergence), every ``via_*`` flag stays False, including the new
    ``via_artifact_promotion``."""
    caps = PhaseCaps(soft=2, hard=8, closeout_budget=2)

    scripts: dict[tuple[int, str], str] = {}
    scripts[(1, "claude")] = _wrap_turn(status="IN_PROGRESS", body_sections={})
    scripts[(1, "openai")] = _wrap_turn(status="IN_PROGRESS", body_sections={})
    # Round 2: empty ledger, both AGREED, artifact_hash_match returns True
    scripts[(2, "claude")] = _wrap_turn(
        status="AGREED", body_sections={},
        artifact="### AGREED_PLAN\nshared",
    )
    scripts[(2, "openai")] = _wrap_turn(
        status="AGREED", body_sections={},
        artifact="### AGREED_PLAN\nshared",
    )

    phase = DeepResearchPhase(
        phase=2,
        agent_turn=make_scripted_agent(scripts),
        artifact_hash_match=_hash_match,
        caps_override=caps,
    )
    result, events = phase.run()

    assert result.converged is True
    assert result.via_artifact_promotion is False
    assert result.via_closeout is False
    assert result.via_ghost_cap is False
    assert result.via_hard_cap is False
    # No promotion event in stream.
    promoted = [e for e in events if isinstance(e, ArtifactCanonicallyPromoted)]
    assert promoted == []


# ─── Spec 0141 — terminal-state-absorbing invariant (B02) ─────────────


def _seed_phase_with_disagreement(*, raiser: str, current_state: State) -> tuple[DeepResearchPhase, LedgerEntryV2]:
    """Build a Phase 2 DR phase with one disagreement already in ``current_state``."""
    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")
    entry = LedgerEntryV2(
        id="D-plan-g-01",
        kind=Category.DISAGREEMENT,
        phase=2,
        raiser=raiser,
        body="we hold X.",
        anchor_type="none",
        anchor_text="",
        evidence_required=False,
        current_state=current_state,
        raised_round=1,
    )
    phase.state.ledger.append(entry)
    return phase, entry


import pytest


@pytest.mark.parametrize(
    "terminal_state",
    [State.RESOLVED, State.ACKNOWLEDGED, State.WITHDRAWN, State.CAPPED],
)
def test_address_on_terminal_item_dropped_with_protocol_violation(terminal_state):
    """Spec 0141 B02 — ADDRESS targeting a terminal item is silently
    dropped at the orchestrator with a ProtocolViolation event.

    Anchor-run smoking gun: r2.2 openai RESOLVED D-plan-g-01, then r2.3
    claude ADDRESSED the resolved item. Without this guard the ADDRESS
    leaked it back to ``addressed`` and r2.3 openai RESOLVED it a second
    time — producing closed > raised in the run-summary aggregator.
    """
    phase, entry = _seed_phase_with_disagreement(
        raiser="openai", current_state=terminal_state,
    )
    parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[AddressBlock(
            item_id="D-plan-g-01",
            response="we now think it's fine.",
            raw_text="### ADDRESS D-plan-g-01\nresponse: we now think it's fine.\n",
        )],
    )

    raised, transitions, violations, empty_turns = phase.apply_turn(
        text="",
        parsed=parsed,
        agent="claude",
        round=3,
        is_closeout_round=False,
    )

    assert raised == []
    assert transitions == []
    assert len(violations) == 1
    pv = violations[0]
    assert isinstance(pv, ProtocolViolation)
    assert pv.violation_code == "terminal_state_re_address"
    assert pv.item_id == "D-plan-g-01"
    assert pv.from_state == terminal_state.value
    assert pv.agent == "claude"
    assert pv.phase == 2
    assert pv.round == 3
    # Ledger entry stays in the terminal state — guard prevented the flip.
    assert entry.current_state == terminal_state


def test_address_on_open_item_still_transitions_to_addressed():
    """Spec 0141 regression-pin — the happy path is unchanged: an
    ADDRESS targeting a non-terminal (open) item still flips it to
    ``addressed`` and emits an ItemTransitioned (no violation)."""
    phase, entry = _seed_phase_with_disagreement(
        raiser="openai", current_state=State.OPEN,
    )
    parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[AddressBlock(
            item_id="D-plan-g-01",
            response="here is my response.",
            raw_text="### ADDRESS D-plan-g-01\nresponse: here is my response.\n",
        )],
    )

    raised, transitions, violations, _ = phase.apply_turn(
        text="",
        parsed=parsed,
        agent="claude",
        round=2,
        is_closeout_round=False,
    )

    assert raised == []
    assert len(transitions) == 1
    assert transitions[0].from_state == "open"
    assert transitions[0].to_state == "addressed"
    assert violations == []
    assert entry.current_state == State.ADDRESSED


def test_addressed_to_addressed_no_op_still_silent_no_violation():
    """Spec 0141 regression-pin — the pre-existing line-366 no-op
    short-circuit for already-addressed items stays. The terminal-state
    guard must not change behaviour on the non-terminal ADDRESSED state.
    """
    phase, entry = _seed_phase_with_disagreement(
        raiser="openai", current_state=State.ADDRESSED,
    )
    parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[AddressBlock(
            item_id="D-plan-g-01",
            response="more thoughts.",
            raw_text="### ADDRESS D-plan-g-01\nresponse: more thoughts.\n",
        )],
    )

    raised, transitions, violations, _ = phase.apply_turn(
        text="",
        parsed=parsed,
        agent="claude",
        round=3,
        is_closeout_round=False,
    )

    assert raised == []
    assert transitions == []   # no-op short-circuit kept
    assert violations == []     # not a violation — just a redundant address
    assert entry.current_state == State.ADDRESSED


def test_anchor_run_double_close_scenario_now_blocked_at_orchestrator():
    """Spec 0141 — end-to-end shape of the anchor-run double-close.
    Replays the four lifecycle events on D-plan-g-01 (raise → address →
    resolve → re-address → resolve) and asserts the second close never
    fires because the re-address is dropped with a ProtocolViolation."""
    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")

    # r1 openai: RAISE.
    r1_parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[RaiseBlock(
            kind=Category.DISAGREEMENT,
            body="we hold X.",
            anchor_type="none",
            anchor_text="",
            evidence_required=False,
            raw_text="### RAISE\nkind: disagreement\nbody: we hold X.\n",
        )],
    )
    raised, _, _, _ = phase.apply_turn(
        text="", parsed=r1_parsed, agent="openai",
        round=1, is_closeout_round=False,
    )
    assert len(raised) == 1
    item_id = raised[0].id  # parser-stamped, e.g. "D-plan-g-01"

    # r2 claude: ADDRESS (legal: open → addressed).
    r2_parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[AddressBlock(
            item_id=item_id,
            response="addressing.",
            raw_text=f"### ADDRESS {item_id}\nresponse: addressing.\n",
        )],
    )
    _, t1, v1, _ = phase.apply_turn(
        text="", parsed=r2_parsed, agent="claude",
        round=2, is_closeout_round=False,
    )
    assert len(t1) == 1 and t1[0].to_state == "addressed"
    assert v1 == []

    # r2 openai: RESOLVE (legal: addressed → resolved — first close).
    r2o_parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[ResolveBlock(
            item_id=item_id,
            reason="we accept the address.",
            raw_text=f"### RESOLVE {item_id}\nreason: we accept.\n",
        )],
    )
    _, t2, v2, _ = phase.apply_turn(
        text="", parsed=r2o_parsed, agent="openai",
        round=2, is_closeout_round=False,
    )
    assert len(t2) == 1 and t2[0].to_state == "resolved"
    assert v2 == []

    # r3 claude: ADDRESS — illegal (resolved → addressed). Pre-fix this
    # leaked the item back to addressed; post-fix it's dropped with a
    # ProtocolViolation.
    r3_parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[AddressBlock(
            item_id=item_id,
            response="actually, more thoughts.",
            raw_text=f"### ADDRESS {item_id}\nresponse: more thoughts.\n",
        )],
    )
    _, t3, v3, _ = phase.apply_turn(
        text="", parsed=r3_parsed, agent="claude",
        round=3, is_closeout_round=False,
    )
    assert t3 == []
    assert len(v3) == 1
    assert isinstance(v3[0], ProtocolViolation)
    assert v3[0].violation_code == "terminal_state_re_address"

    # r3 openai: RESOLVE — pre-fix this would have been the second
    # close. Post-fix the item is still RESOLVED (ResolveBlock's
    # `current_state != ADDRESSED` guard rejects it), so no second
    # ItemTransitioned. Aggregate stays at 1 raise, 1 close.
    r3o_parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[ResolveBlock(
            item_id=item_id,
            reason="closing again.",
            raw_text=f"### RESOLVE {item_id}\nreason: closing.\n",
        )],
    )
    _, t4, v4, _ = phase.apply_turn(
        text="", parsed=r3o_parsed, agent="openai",
        round=3, is_closeout_round=False,
    )
    assert t4 == []           # second close blocked
    assert v4 == []           # ResolveBlock just silently no-ops

    # Final state — exactly one terminal transition on this item.
    entry = phase.state.find(item_id)
    assert entry is not None
    terminal_transitions = [
        tr for tr in entry.transitions if tr["to"] == "resolved"
    ]
    assert len(terminal_transitions) == 1


# ─── Spec 0141 — empty-turn detector (B06) ─────────────────────────────


@pytest.mark.parametrize("phase_id", [0, 2, 4])
def test_empty_turn_detected_fires_in_negotiate_phases(phase_id):
    """Spec 0141 B06 — zero ledger-affecting blocks in phase 0 / 2 / 4
    emits exactly one EmptyTurnDetected with the threaded finish_reason
    / output_tokens. Anchor-run shape: phase4-r6-claude turn_ended
    finish_reason='max_tokens', output_tokens=8750.
    """
    phase = DeepResearchPhase(phase=phase_id, agent_turn=lambda req: "")
    parsed = ParsedTurnV2(status="IN_PROGRESS", blocks=[])

    _, _, _, empty_turns = phase.apply_turn(
        text="",
        parsed=parsed,
        agent="claude",
        round=6,
        is_closeout_round=False,
        finish_reason="max_tokens",
        output_tokens=8750,
    )

    assert len(empty_turns) == 1
    e = empty_turns[0]
    assert isinstance(e, EmptyTurnDetected)
    assert e.phase == phase_id
    assert e.round == 6
    assert e.agent == "claude"
    assert e.parser_block_count == 0
    assert e.finish_reason == "max_tokens"
    assert e.output_tokens == 8750


@pytest.mark.parametrize("phase_id", [1, 3])
def test_empty_turn_detected_does_not_fire_in_silent_phases(phase_id):
    """Spec 0141 B06 — Phase 1 (parallel drafts) and Phase 3 (single-
    agent drafting) are item-silent by design. An empty turn there is
    not a signal worth surfacing.

    ``DeepResearchPhase`` only supports phases 0/2/4 at construction;
    phases 1/3 don't run through ``apply_turn`` in production. We
    exercise the phase-gating predicate by constructing a phase-2 DR
    phase and mutating ``.phase`` so the in-method `self.phase in
    (0, 2, 4)` check sees the silent-phase value.
    """
    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")
    phase.phase = phase_id  # type: ignore[assignment]
    parsed = ParsedTurnV2(status="IN_PROGRESS", blocks=[])

    _, _, _, empty_turns = phase.apply_turn(
        text="",
        parsed=parsed,
        agent="claude",
        round=1,
        is_closeout_round=False,
        finish_reason="stop",
        output_tokens=4000,
    )

    assert empty_turns == []


def test_empty_turn_detected_does_not_fire_when_any_block_present():
    """Spec 0141 B06 — a single RAISE / ADDRESS / etc. block keeps the
    turn out of the empty-turn bucket. False positives on legit movement
    would defeat the purpose."""
    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")
    parsed = ParsedTurnV2(
        status="IN_PROGRESS",
        blocks=[RaiseBlock(
            kind=Category.QUESTION,
            body="what about Y?",
            anchor_type="none",
            anchor_text="",
            evidence_required=False,
            raw_text="### RAISE\nkind: question\nbody: what about Y?\n",
        )],
    )

    _, _, _, empty_turns = phase.apply_turn(
        text="", parsed=parsed, agent="claude",
        round=1, is_closeout_round=False,
        finish_reason="stop", output_tokens=200,
    )

    assert empty_turns == []


def test_empty_turn_detected_with_unknown_finish_reason_carries_none():
    """Spec 0141 B06 — finish_reason defaults to None when the upstream
    payload doesn't carry one (e.g. the replay path, which has no
    turn_ended event to read from)."""
    phase = DeepResearchPhase(phase=4, agent_turn=lambda req: "")
    parsed = ParsedTurnV2(status="IN_PROGRESS", blocks=[])

    _, _, _, empty_turns = phase.apply_turn(
        text="", parsed=parsed, agent="openai",
        round=8, is_closeout_round=False,
    )

    assert len(empty_turns) == 1
    assert empty_turns[0].finish_reason is None
    assert empty_turns[0].output_tokens == 0
