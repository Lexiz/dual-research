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
from dual_research.events import (
    CloseoutUrged,
    CloseoutViolation,
    ItemRaised,
    ItemTransitioned,
    PhaseConverged,
)
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


def test_evidence_fabricated_event_id_blocks_address_transition():
    """An ADDRESS with evidence_required=True but fabricated
    evidence_event_id is rejected. The item stays in `open` state and
    closeout fires next round."""
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

    # Stub evidence validator that always rejects fabricated event ids.
    from dual_research.contract.evidence import EvidenceFlag

    def reject_fabricated(records, parsed, agent):
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

    # The item must NOT have transitioned to addressed (because evidence
    # was rejected). No ItemTransitioned event with to_state=addressed.
    addressed = [
        e for e in events
        if isinstance(e, ItemTransitioned) and e.to_state == "addressed"
    ]
    assert len(addressed) == 0

    # Closeout was urged at round 2 (both AGREED, item still non-terminal)
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
