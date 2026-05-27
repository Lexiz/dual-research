"""Spec 0229 — addressee-obligation invariant.

Locks in that an agent emitting ``STATUS: AGREED`` while items raised by
the OTHER agent remain ``open`` and un-ADDRESSed by this agent:

- emits exactly one ``ProtocolViolation(agreed_with_open_addressed_items)``
  per blocking item;
- causes the orchestrator to demote that agent's *effective* convergence
  status to ``IN_PROGRESS`` even though the self-reported `STATUS: AGREED`
  on the turn file is preserved (gate-only demotion — transcript truth);
- causes verifier I2.4 to classify the AGREED turn as HANDLED (passes)
  when the matching ProtocolViolation is present; UNHANDLED (fails) when
  no matching ProtocolViolation exists AND the same-round
  ``phase_converged`` event exists (the AGREED actually counted).

Also covers the closeout-request prompt extension: when the orchestrator
detects items the other agent raised and the current agent has not yet
ADDRESSed, the closeout-request body grows an addressee-obligation
block naming each item with the literal "before declaring AGREED"
instruction.

And the severity flip of I2.4 from `reporting` to `gating` across the
three anchor-run fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.contract.categories import Category
from dual_research.contract.lifecycle import State
from dual_research.contract.verifier import _check_i2_4, verify_run
from dual_research.events import ProtocolViolation
from dual_research.orchestrator.deep_research import (
    DeepResearchPhase,
    LedgerEntryV2,
    _effective_status_for,
)
from dual_research.protocol.parse import parse_turn_v2
from dual_research.protocol.prompts import closeout_request_section


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "anchor-runs"


# ─── Helpers ───────────────────────────────────────────────────────────


def _seed_phase_with_item(
    *,
    raiser: str,
    current_state: State,
    item_id: str = "D-plan-g-01",
    kind: Category = Category.DISAGREEMENT,
    phase_no: int = 2,
) -> tuple[DeepResearchPhase, LedgerEntryV2]:
    phase = DeepResearchPhase(phase=phase_no, agent_turn=lambda req: "")
    entry = LedgerEntryV2(
        id=item_id,
        kind=kind,
        phase=phase_no,
        raiser=raiser,
        body="we should pick uvicorn over gunicorn",
        anchor_type="none",
        anchor_text="",
        evidence_required=False,
        current_state=current_state,
        raised_round=1,
    )
    phase.state.ledger.append(entry)
    return phase, entry


# ─── §2.2 runtime emission ─────────────────────────────────────────────


def test_agreed_with_open_addressed_item_emits_one_protocol_violation():
    """One open item raised by claude and addressed-at-openai. Openai
    emits AGREED without ADDRESSing it — exactly one
    ``agreed_with_open_addressed_items`` PV fires, citing the blocking
    item id in both ``item_id`` and ``reason``."""
    phase, entry = _seed_phase_with_item(
        raiser="claude", current_state=State.OPEN, item_id="D-plan-c-02",
    )
    parsed = parse_turn_v2(
        "## My position\n"
        "I have nothing to add.\n\n"
        "STATUS: AGREED\n"
    )
    _, _, violations, _ = phase.apply_turn(
        text="STATUS: AGREED\n",
        parsed=parsed,
        agent="openai",
        round=3,
        is_closeout_round=False,
    )
    pvs = [v for v in violations if isinstance(v, ProtocolViolation)
           and v.violation_code == "agreed_with_open_addressed_items"]
    assert len(pvs) == 1, f"expected exactly one PV; got {violations!r}"
    pv = pvs[0]
    assert pv.agent == "openai"
    assert pv.phase == 2
    assert pv.round == 3
    assert pv.item_id == "D-plan-c-02"
    assert pv.from_state == "open"
    assert pv.op_kind == "agreed"
    assert pv.expected_state == "addressed"
    assert "D-plan-c-02" in pv.reason
    assert "claude" in pv.reason  # names the raiser
    # The ledger item is unchanged — emission is observability only.
    assert entry.current_state == State.OPEN


def test_address_then_agreed_in_one_turn_is_silent():
    """ADDRESS-then-AGREED in a single turn — the post-turn ledger has
    the item flipped to ``addressed`` BEFORE the addressee-obligation
    check fires, so zero ``agreed_with_open_addressed_items`` PVs fire
    (R1 mitigation per spec §7)."""
    phase, entry = _seed_phase_with_item(
        raiser="claude", current_state=State.OPEN, item_id="D-plan-c-02",
    )
    parsed = parse_turn_v2(
        "## Addressing items raised against me\n\n"
        "### ADDRESS D-plan-c-02\n"
        "response: uvicorn it is.\n\n"
        "STATUS: AGREED\n"
    )
    _, transitions, violations, _ = phase.apply_turn(
        text="ADDRESS then AGREED",
        parsed=parsed,
        agent="openai",
        round=3,
        is_closeout_round=False,
    )
    addr_pvs = [v for v in violations if isinstance(v, ProtocolViolation)
                and v.violation_code == "agreed_with_open_addressed_items"]
    assert addr_pvs == [], f"expected zero addressee-obligation PVs; got {violations!r}"
    # The ADDRESS actually transitioned the item before the AGREED check.
    assert entry.current_state == State.ADDRESSED
    assert len(transitions) == 1
    assert transitions[0].to_state == "addressed"


def test_two_open_items_addressed_at_same_agent_yields_two_violations():
    """Per-item emission granularity — two open items addressed at the
    same agent produce two PVs, each naming its own ``item_id``."""
    phase, _ = _seed_phase_with_item(
        raiser="claude", current_state=State.OPEN, item_id="D-plan-c-02",
    )
    phase.state.ledger.append(LedgerEntryV2(
        id="Q-plan-c-01",
        kind=Category.QUESTION,
        phase=2,
        raiser="claude",
        body="does uvicorn support websockets?",
        anchor_type="none",
        anchor_text="",
        evidence_required=False,
        current_state=State.OPEN,
        raised_round=1,
    ))
    parsed = parse_turn_v2("## stuff\n\nSTATUS: AGREED\n")
    _, _, violations, _ = phase.apply_turn(
        text="STATUS: AGREED\n",
        parsed=parsed,
        agent="openai",
        round=3,
        is_closeout_round=False,
    )
    addr_pvs = [v for v in violations if isinstance(v, ProtocolViolation)
                and v.violation_code == "agreed_with_open_addressed_items"]
    ids = sorted(v.item_id for v in addr_pvs)
    assert ids == ["D-plan-c-02", "Q-plan-c-01"]


def test_non_agreed_status_does_not_emit_addressee_violation():
    """The check guards on ``parsed.status == 'AGREED'`` — IN_PROGRESS
    turns with the same ledger shape stay silent."""
    phase, _ = _seed_phase_with_item(
        raiser="claude", current_state=State.OPEN, item_id="D-plan-c-02",
    )
    parsed = parse_turn_v2("## my position\n\nSTATUS: IN_PROGRESS\n")
    _, _, violations, _ = phase.apply_turn(
        text="IN_PROGRESS turn",
        parsed=parsed,
        agent="openai",
        round=3,
        is_closeout_round=False,
    )
    assert all(
        not (isinstance(v, ProtocolViolation)
             and v.violation_code == "agreed_with_open_addressed_items")
        for v in violations
    )


def test_agreed_with_own_open_items_does_not_fire_addressee_obligation():
    """Items the AGREED-ing agent themselves raised are not addressee-
    obligation candidates — the obligation applies only to items raised
    by the OTHER agent."""
    phase, _ = _seed_phase_with_item(
        raiser="openai", current_state=State.OPEN, item_id="D-plan-o-01",
    )
    parsed = parse_turn_v2("## stuff\n\nSTATUS: AGREED\n")
    _, _, violations, _ = phase.apply_turn(
        text="STATUS: AGREED\n",
        parsed=parsed,
        agent="openai",
        round=3,
        is_closeout_round=False,
    )
    addr_pvs = [v for v in violations if isinstance(v, ProtocolViolation)
                and v.violation_code == "agreed_with_open_addressed_items"]
    assert addr_pvs == []


def test_agreed_with_addressed_state_owing_item_is_silent():
    """Items already in ``addressed`` state (the other agent's items
    that this agent already responded to) do not trigger the obligation
    — the predicate is ``open`` only."""
    phase, _ = _seed_phase_with_item(
        raiser="claude", current_state=State.ADDRESSED, item_id="D-plan-c-02",
    )
    parsed = parse_turn_v2("## stuff\n\nSTATUS: AGREED\n")
    _, _, violations, _ = phase.apply_turn(
        text="STATUS: AGREED\n",
        parsed=parsed,
        agent="openai",
        round=3,
        is_closeout_round=False,
    )
    addr_pvs = [v for v in violations if isinstance(v, ProtocolViolation)
                and v.violation_code == "agreed_with_open_addressed_items"]
    assert addr_pvs == []


# ─── §2.2 effective-status helper + RoundResult demotion ────────────────


def test_effective_status_helper_demotes_agreed_when_violation_present():
    pv = ProtocolViolation(
        phase=2, round=3, agent="openai",
        violation_code="agreed_with_open_addressed_items",
        item_id="D-plan-c-02", from_state="open",
        op_kind="agreed", expected_state="addressed",
        reason="owing",
    )
    assert _effective_status_for(
        agent="openai", self_reported="AGREED", violations=[pv],
    ) == "IN_PROGRESS"
    # claude was not the offender — passthrough.
    assert _effective_status_for(
        agent="claude", self_reported="AGREED", violations=[pv],
    ) == "AGREED"


def test_effective_status_helper_passes_through_when_no_violation():
    assert _effective_status_for(
        agent="openai", self_reported="AGREED", violations=[],
    ) == "AGREED"
    assert _effective_status_for(
        agent="openai", self_reported="IN_PROGRESS", violations=[],
    ) == "IN_PROGRESS"
    assert _effective_status_for(
        agent="openai", self_reported=None, violations=[],
    ) is None


def test_effective_status_passthrough_for_non_addressee_violation_code():
    """Other ProtocolViolation codes (e.g. resolve_from_non_addressed)
    do not demote AGREED — the demotion is specific to the addressee-
    obligation code."""
    pv = ProtocolViolation(
        phase=2, round=3, agent="openai",
        violation_code="resolve_from_non_addressed",
        item_id="D-plan-c-02", from_state="open",
        op_kind="resolve", expected_state="addressed",
        reason="wrong state",
    )
    assert _effective_status_for(
        agent="openai", self_reported="AGREED", violations=[pv],
    ) == "AGREED"


def test_process_round_end_stores_effective_status_on_round_result():
    """``process_round_end`` returns a ``RoundResult`` whose
    ``effective_openai_status`` is demoted to ``IN_PROGRESS`` when an
    ``agreed_with_open_addressed_items`` violation fired for openai
    this round. Self-reported ``openai_status`` stays ``AGREED`` for
    the diagnostic trail; the convergence gate sees the demoted
    value and refuses to converge."""
    phase, _ = _seed_phase_with_item(
        raiser="claude", current_state=State.OPEN, item_id="D-plan-c-02",
    )
    parsed_claude = parse_turn_v2("## position\n\nSTATUS: IN_PROGRESS\n")
    parsed_openai = parse_turn_v2("## position\n\nSTATUS: AGREED\n")
    # Apply openai's AGREED turn — emits the addressee-obligation PV.
    _, _, openai_violations, _ = phase.apply_turn(
        text="STATUS: AGREED\n", parsed=parsed_openai, agent="openai",
        round=3, is_closeout_round=False,
    )
    rr = phase.process_round_end(
        parsed_claude=parsed_claude,
        parsed_openai=parsed_openai,
        round=3,
        is_closeout_round=False,
        raised_events=[],
        transition_events=[],
        violation_events=list(openai_violations),
    )
    assert rr.claude_status == "IN_PROGRESS"
    assert rr.openai_status == "AGREED"           # self-reported preserved
    assert rr.effective_claude_status == "IN_PROGRESS"  # passthrough
    assert rr.effective_openai_status == "IN_PROGRESS"  # demoted at gate
    assert not rr.converged
    addr_pvs = [v for v in rr.violation_events if isinstance(v, ProtocolViolation)
                and v.violation_code == "agreed_with_open_addressed_items"]
    assert len(addr_pvs) == 1


def test_process_round_end_passes_through_when_no_demotion():
    """Clean round where both agents emit AGREED and no
    ``agreed_with_open_addressed_items`` violation fired — effective
    matches self-reported for both agents."""
    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")
    parsed_claude = parse_turn_v2("## position\n\nSTATUS: AGREED\n")
    parsed_openai = parse_turn_v2("## position\n\nSTATUS: AGREED\n")
    rr = phase.process_round_end(
        parsed_claude=parsed_claude,
        parsed_openai=parsed_openai,
        round=3,
        is_closeout_round=False,
        raised_events=[],
        transition_events=[],
        violation_events=[],
    )
    assert rr.effective_claude_status == "AGREED"
    assert rr.effective_openai_status == "AGREED"


# ─── §2.1 closeout-request prompt rendering ────────────────────────────


def test_closeout_request_section_renders_addressee_obligation_block():
    """When ``addressed_at_me_items`` is non-empty, the rendered section
    contains a new block listing each addressed-at-me id and the
    literal 'before declaring AGREED' instruction."""
    owned = [
        {"id": "Q-plan-o-01", "kind": "question",
         "body": "what's our token budget?", "current_state": "open"},
    ]
    addressed_at_me = [
        {"id": "D-plan-c-02", "kind": "disagreement",
         "body": "pick uvicorn over gunicorn", "current_state": "open"},
        {"id": "Q-plan-c-01", "kind": "question",
         "body": "does uvicorn support websockets?", "current_state": "open"},
    ]
    rendered = closeout_request_section(
        items=owned,
        agent_name="openai",
        remaining_budget=2,
        addressed_at_me_items=addressed_at_me,
    )
    # Owned items are still listed.
    assert "Q-plan-o-01" in rendered
    # New addressee-obligation block names each addressed-at-me item.
    assert "D-plan-c-02" in rendered
    assert "Q-plan-c-01" in rendered
    # The instruction literal is present.
    assert "before declaring AGREED" in rendered
    # The block header mentions addressee-obligation.
    assert "Addressee-obligation" in rendered


def test_closeout_request_section_back_compat_empty_addressed_at_me():
    """Calls that omit ``addressed_at_me_items`` (or pass an empty
    list / None) render no addressee-obligation block — pre-spec
    callsites continue to work unchanged."""
    owned = [
        {"id": "Q-plan-o-01", "kind": "question",
         "body": "what's our budget?", "current_state": "open"},
    ]
    rendered_default = closeout_request_section(
        items=owned, agent_name="openai", remaining_budget=2,
    )
    rendered_explicit_none = closeout_request_section(
        items=owned, agent_name="openai", remaining_budget=2,
        addressed_at_me_items=None,
    )
    rendered_empty = closeout_request_section(
        items=owned, agent_name="openai", remaining_budget=2,
        addressed_at_me_items=[],
    )
    for rendered in (rendered_default, rendered_explicit_none, rendered_empty):
        assert "Addressee-obligation" not in rendered
        assert "before declaring AGREED" not in rendered
        # Owned block is still rendered.
        assert "Q-plan-o-01" in rendered


# ─── §2.4 verifier I2.4 handled-vs-unhandled refactor ──────────────────


def _build_turn_file(*, phase: int, round: int, agent: str, status: str,
                     rel_path: str = "phase2/round-03-openai.md"):
    """Minimal _TurnFile-shaped object (only fields _check_i2_4 reads)."""
    class _TF:
        pass
    tf = _TF()
    tf.phase = phase
    tf.round = round
    tf.agent = agent
    tf.status = status
    tf.rel_path = rel_path
    tf.ops = []
    tf.counters = None
    return tf


def test_i2_4_premature_agreed_with_demotion_passes():
    """Spec §6 test plan — AGREED-while-owing turn WITH a matching
    ``agreed_with_open_addressed_items`` ProtocolViolation for the same
    (phase, round, agent). The detector classifies it HANDLED → pass."""
    events = [
        {"event": "item_raised", "phase": 2, "round": 1,
         "raiser": "claude", "id": "D-plan-c-02"},
        {"event": "protocol_violation", "phase": 2, "round": 3,
         "agent": "openai",
         "violation_code": "agreed_with_open_addressed_items",
         "item_id": "D-plan-c-02"},
    ]
    turn_files = [_build_turn_file(
        phase=2, round=3, agent="openai", status="AGREED",
    )]
    result = _check_i2_4(events, turn_files)
    assert result.severity == "gating"
    assert result.verdict == "pass", (
        f"expected pass (HANDLED via matching PV); got "
        f"{result.verdict}: {result.evidence}"
    )


def test_i2_4_agreed_that_converged_with_owing_fails():
    """Spec §6 test plan — AGREED-while-owing turn with NO matching
    ProtocolViolation AND a same-round ``phase_converged`` event. The
    detector classifies it UNHANDLED → fail (gating). The failure
    evidence cites the addressed-at-me item id."""
    events = [
        {"event": "item_raised", "phase": 2, "round": 1,
         "raiser": "claude", "id": "D-plan-c-02"},
        {"event": "phase_converged", "phase": 2, "final_round": 3},
    ]
    turn_files = [_build_turn_file(
        phase=2, round=3, agent="openai", status="AGREED",
    )]
    result = _check_i2_4(events, turn_files)
    assert result.severity == "gating"
    assert result.verdict == "fail", (
        f"expected fail (UNHANDLED — no PV, converged); got "
        f"{result.verdict}: {result.evidence}"
    )
    text = " ".join(e.detail for e in result.evidence)
    assert "D-plan-c-02" in text


def test_i2_4_agreed_with_owing_and_no_pv_fails_even_without_convergence():
    """Per spec §2.4 / §6 — the UNHANDLED test is "no matching PV".
    The dead-primary anchor run never converges in phase 2 yet its
    AGREED-while-owing turns are still UNHANDLED ("every offending
    AGREED is UNHANDLED" per §6 acceptance). The presence of a same-
    round `phase_converged` event is descriptive of the bad case, not
    a required precondition for failure."""
    events = [
        {"event": "item_raised", "phase": 2, "round": 1,
         "raiser": "claude", "id": "D-plan-c-02"},
        # No phase_converged, no addressee-obligation PV — UNHANDLED.
    ]
    turn_files = [_build_turn_file(
        phase=2, round=3, agent="openai", status="AGREED",
    )]
    result = _check_i2_4(events, turn_files)
    assert result.severity == "gating"
    assert result.verdict == "fail"
    text = " ".join(e.detail for e in result.evidence)
    assert "D-plan-c-02" in text


def test_i2_4_no_agreeds_is_not_applicable():
    """Runs with zero AGREED turns return not_applicable (still
    gating)."""
    result = _check_i2_4(events=[], turn_files=[])
    assert result.severity == "gating"
    assert result.verdict == "not_applicable"


# ─── §2.4 severity flip lock-in across anchor-run fixtures ─────────────


def test_i2_4_on_dead_primary_fails_naming_four_addressee_items():
    """Spec §6 acceptance — the dead-primary anchor run flips to
    ``gating/fail`` with the four addressed-at-openai items
    (``D-plan-c-02 / D-plan-c-04 / D-plan-c-05 / Q-plan-c-01``) named
    in the evidence list. The frozen run is pre-0229 so no matching
    ``agreed_with_open_addressed_items`` ProtocolViolation events
    exist — every offending AGREED is UNHANDLED."""
    rd = FIXTURES / "20260526-102321-backend-language-choice"
    report = verify_run(rd)
    i2_4 = next(r for r in report.results if r.id == "I2.4")
    assert i2_4.severity == "gating"
    assert i2_4.verdict == "fail", (
        f"expected fail (UNHANDLED) on dead primary; got "
        f"{i2_4.verdict}: {i2_4.evidence}"
    )
    text = " ".join(e.detail for e in i2_4.evidence)
    for item_id in ("D-plan-c-02", "D-plan-c-04", "D-plan-c-05", "Q-plan-c-01"):
        assert item_id in text, (
            f"missing {item_id} in I2.4 evidence on dead primary; got: {text!r}"
        )


def test_i2_4_on_clean_anchor_passes():
    """Spec §6 acceptance — the clean-reference anchor run flips to
    ``gating/pass`` because no AGREEDs in that run ever carried open
    addressed-at-me debt (the handled-vs-unhandled detector returns a
    vacuous pass on it)."""
    rd = FIXTURES / "20260521-010637-dvs-backend-language-choice"
    report = verify_run(rd)
    i2_4 = next(r for r in report.results if r.id == "I2.4")
    assert i2_4.severity == "gating"
    assert i2_4.verdict == "pass"


@pytest.mark.parametrize(
    "fixture_id",
    [
        "20260521-010637-dvs-backend-language-choice",  # clean reference
        "20260525-135006-backend-language-choice",       # dead secondary
        "20260526-102321-backend-language-choice",       # dead primary
    ],
)
def test_i2_4_severity_is_gating_on_each_anchor_fixture(fixture_id: str):
    """Live verifier reports I2.4 with severity='gating' on every
    anchor-run fixture (post-spec-0229 promotion)."""
    rd = FIXTURES / fixture_id
    report = verify_run(rd)
    i2_4 = next(r for r in report.results if r.id == "I2.4")
    assert i2_4.severity == "gating", (
        f"expected gating severity post-0229 on {fixture_id}; got {i2_4.severity!r}"
    )


@pytest.mark.parametrize(
    "fixture_id",
    [
        "20260521-010637-dvs-backend-language-choice",
        "20260525-135006-backend-language-choice",
        "20260526-102321-backend-language-choice",
    ],
)
def test_i2_4_severity_is_gating_in_expected_json(fixture_id: str):
    """Frozen ``expected.json`` baselines record severity='gating' for
    I2.4 — the regenerated baselines that ship in this PR."""
    path = FIXTURES / fixture_id / "expected.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in payload["results"]}
    assert by_id["I2.4"]["severity"] == "gating", (
        f"expected gating severity in {path}; got {by_id['I2.4']['severity']!r}"
    )


# ─── §2.6 version + CHANGELOG smoke check ──────────────────────────────


def test_version_is_1_48_0():
    """``__version__`` matches the version bumped in this spec."""
    import dual_research
    assert dual_research.__version__ == "1.48.0"


def test_changelog_has_1_48_0_section():
    """CHANGELOG.md grew a ``## [1.48.0] — 2026-05-27`` section."""
    body = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.48.0] — 2026-05-27" in body


# ─── §2.5 CLAUDE.md doctrinal addition ─────────────────────────────────


def test_claude_md_has_carve_out_disposition_subsection():
    """CLAUDE.md grew the ``Carve-out follow-ups must triage at carve-
    out time`` subsection per spec §2.5."""
    body = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Carve-out follow-ups must triage at carve-out time" in body
    # And it carries the substantive `disposition:` field guidance.
    assert "`disposition:`" in body
    assert "`ship`" in body and "`archive`" in body
