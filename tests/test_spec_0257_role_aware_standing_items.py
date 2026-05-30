"""Spec 0257 — role-aware standing-items surface (addressee must ADDRESS,
raiser must not self-address or resolve-from-open).

Two test tiers, mirroring spec 0257 §6:

§6.1 — prompt-content + unit checks (necessary, NOT sufficient). These
assert the LIVE role-aware surface says the right words. **Retarget
note:** the queued spec cited ``ledger/prompt.py:build_standing_items_section``
and the non-``_v2`` prompt builders — both DEAD since the spec-0118 v2
rewrite (unreachable from ``run_dr_phase2`` / ``run_dr_phase4``). The
live surface is ``deep_research.format_role_aware_standing_items`` (wired
via ``dr_run._format_standing_items``) plus the ``*_v2`` prompt builders.
These checks assert on the live surface; asserting on the dead one would
be the 0231→0238 "green CI, wrong layer" trap the spec warns against.

§6.2 — behavioural replay harness (the CI floor). Replays run
``20260530-175809``'s vendored phase-2 / phase-4 turns through the REAL
``DeepResearchPhase.apply_turn`` path — the same path ``run_dr_phase2``
and ``ledger/replay`` drive — and renders standing items through the
live ``dr_run._format_standing_items`` entry point. This exercises the
changed surface against the captured artifact (spec-0238 discipline).

Why §6.2 does not assert "zero violations" on the vendored turns: the
vendored turns are frozen pre-fix LLM outputs produced UNDER the
role-blind prompt, so replaying them necessarily re-emits the captured
violations. The deterministic assertion is therefore (a) the live
entry point now renders the role-correct grouping the agents would see,
and (b) the captured artifact reproduces the exact failure the fix
targets. Zeroing the emitted violations requires a live LLM re-run —
that is §6.3 PR acceptance evidence, not a CI gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.contract.categories import Category
from dual_research.contract.lifecycle import State
from dual_research.orchestrator.deep_research import (
    DeepResearchPhase,
    LedgerEntryV2,
    format_role_aware_standing_items,
)
from dual_research.orchestrator.dr_run import (
    _evidence_validator_for_run,
    _format_standing_items,
)
from dual_research.protocol import prompts as P
from dual_research.protocol.parse import parse_turn_v2

FIXTURES = Path(__file__).parent / "fixtures" / "spec_0257"


# ─── helpers ──────────────────────────────────────────────────────────


def _mk(entry_id, raiser, state, *, kind=Category.DISAGREEMENT, transitions=None):
    return LedgerEntryV2(
        id=entry_id,
        kind=kind,
        phase=2,
        raiser=raiser,
        body=f"body of {entry_id}",
        anchor_type="none",
        anchor_text="",
        evidence_required=False,
        current_state=state,
        transitions=transitions or [],
    )


def _replay_phase_to(phase_int: int, *, through_round: int) -> tuple[DeepResearchPhase, dict]:
    """Apply vendored turns for ``phase_int`` rounds 1..through_round via the
    REAL ``apply_turn`` path. Returns the phase (with a populated ledger)
    and a ``{round: {agent: [violation_codes]}}`` map.
    """
    fx = FIXTURES / f"phase{phase_int}"
    phase = DeepResearchPhase(
        phase=phase_int,
        agent_turn=lambda req: "",
        evidence_validator=_evidence_validator_for_run,
    )
    violations: dict = {}
    for rnd in range(1, through_round + 1):
        violations[rnd] = {}
        for agent in ("claude", "openai"):
            path = fx / f"round-{rnd:02d}-{agent}.md"
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            parsed = parse_turn_v2(text)
            _r, _t, v, _e = phase.apply_turn(
                text=text,
                parsed=parsed,
                agent=agent,
                round=rnd,
                is_closeout_round=False,
                audit_tool_events=[],
            )
            violations[rnd][agent] = [pv.violation_code for pv in v]
    return phase, violations


# ─── §6.1 — prompt-content + unit checks (live surface) ───────────────


def test_role_aware_renders_three_actionable_groups_with_role_correct_text():
    """One open-against-me, one open-by-me, one addressed-by-me → three
    distinct role groups, each carrying only that role's legal ops."""
    ledger = [
        _mk("D-g-1", "openai", State.OPEN),  # raised against claude → addressee
        _mk("D-c-1", "claude", State.OPEN),  # raised by claude, still open
        _mk(
            "D-c-2",
            "claude",
            State.ADDRESSED,
            transitions=[{"to": "addressed", "actor": "openai"}],
        ),
    ]
    out = format_role_aware_standing_items(ledger, "claude")

    # Group 1 — addressee.
    assert "you are the ADDRESSEE" in out
    assert "MUST emit `### ADDRESS" in out
    assert "may NOT RESOLVE" in out
    # Group 2 — raiser, open.
    assert "still open (NOT yet addressed)" in out
    assert "Do NOT emit `### ADDRESS" in out
    assert "WITHDRAW" in out
    # Group 3 — raiser, addressed (ratifiable).
    assert "ready for you to ratify" in out
    assert "RESOLVE" in out
    assert "ratify" in out
    # addressed_by surfaced for the raiser's ratifiable item.
    assert "addressed_by: openai" in out


def test_role_aware_output_omits_legacy_role_blind_phrasing():
    """Antipodal-absence: the pre-fix role-blind instruction offered the
    SAME two options ("answer or address" OR "explicitly close it out")
    for every item regardless of role. The role-aware surface must never
    co-locate those two as one shared instruction."""
    ledger = [
        _mk("D-g-1", "openai", State.OPEN),
        _mk("D-c-1", "claude", State.OPEN),
    ]
    out = format_role_aware_standing_items(ledger, "claude").lower()
    assert not ("answer or address" in out and "explicitly close it out" in out)


def test_ratifiable_group_is_exactly_addressed_and_raised_by_agent():
    """The "ready for you to ratify" group is the live equivalent of the
    spec's proposed ``ratifiable_entries`` — addressed items raised by the
    agent, never open items and never items raised by the other agent."""
    ledger = [
        _mk("D-c-open", "claude", State.OPEN),
        _mk("D-c-addr", "claude", State.ADDRESSED,
            transitions=[{"to": "addressed", "actor": "openai"}]),
        _mk("D-c-res", "claude", State.RESOLVED),       # terminal — excluded
        _mk("D-g-addr", "openai", State.ADDRESSED,      # addressed but NOT mine
            transitions=[{"to": "addressed", "actor": "claude"}]),
    ]
    out = format_role_aware_standing_items(ledger, "claude")
    ratify_block = _group_block(out, "ready for you to ratify")
    assert "D-c-addr" in ratify_block
    assert "D-c-open" not in ratify_block   # open, not ratifiable
    assert "D-c-res" not in ratify_block    # terminal, excluded entirely
    assert "D-g-addr" not in ratify_block   # raised by other agent, not mine
    assert "D-c-res" not in out             # terminal items never render


def test_empty_ledger_renders_none_sentinel():
    assert format_role_aware_standing_items([], "claude") == "(none)"
    # all-terminal also collapses to the sentinel
    ledger = [_mk("D-c-1", "claude", State.RESOLVED)]
    assert format_role_aware_standing_items(ledger, "claude") == "(none)"


def test_phase2_callout_in_v2_builders_and_absent_from_phase4():
    """``_ADDRESS_RESOLVE_ROLE_CALLOUT`` (symmetric raiser/addressee) is
    rendered in BOTH live phase-2 ``_v2`` builders and never in phase 4."""
    r1 = P.plan_negotiation_round1_prompt_v2(
        brief_content="b", agreed_interpretation="a", own_plan="o",
        other_plan="ot", agent_name="claude", other_name="openai",
    )
    rn = P.plan_negotiation_round_n_prompt_v2(
        brief_content="b", agreed_interpretation="a", own_plan="o",
        other_plan="ot", prior_turns=[], standing_items="(none)",
        agent_name="claude", other_name="openai", round=2,
        soft_cap=4, hard_cap=8,
    )
    needle = "item-ownership contract"
    for txt in (r1, rn):
        assert needle in txt
        # callout sits above the `## Status` section header.
        assert txt.index(needle) < txt.index("\n## Status\n")


def test_phase4_callout_is_distinct_drafter_reviewer_wording():
    """Correction-3 guard: phase 4 gets its OWN drafter/reviewer callout,
    NOT the phase-2 raiser/addressee paragraph verbatim. The phase-2
    needle must be absent from phase-4 prompts and vice versa."""
    v1 = P.review_round1_prompt_v2(
        brief_content="b", draft_content="d", drafter_name="claude",
        agent_name="openai", other_name="claude",
    )
    vn = P.review_round_n_prompt_v2(
        brief_content="b", draft_content="d", drafter_name="claude",
        prior_turns=[], standing_items="(none)", agent_name="openai",
        other_name="claude", round=2, soft_cap=4, hard_cap=8,
        draft_version=2, draft_headings=["Intro"],
    )
    p2_needle = "item-ownership contract"
    p4_needle = "drafter/reviewer contract"
    for txt in (v1, vn):
        assert p4_needle in txt
        assert p2_needle not in txt          # no phase-2 wording leak
        assert txt.index(p4_needle) < txt.index("\n## Status\n")
    # And the phase-2 builders must NOT carry the phase-4 wording.
    r1 = P.plan_negotiation_round1_prompt_v2(
        brief_content="b", agreed_interpretation="a", own_plan="o",
        other_plan="ot", agent_name="claude", other_name="openai",
    )
    assert p4_needle not in r1


# ─── §6.2 — behavioural replay harness (CI floor, real entry point) ───


def test_phase2_live_entry_point_renders_role_correct_grouping():
    """Build the ledger from the captured phase-2 round-1 turns via the
    REAL ``apply_turn`` path, then render through the LIVE
    ``dr_run._format_standing_items`` entry point. Assert each agent sees
    its own open items under the no-self-address raiser group and the
    OTHER agent's items under the must-ADDRESS addressee group.

    This is the regression the retarget exists for: on the dead
    ``build_standing_items_section`` surface this assertion could never
    run, because the live ``run_dr_phase2`` never calls it.
    """
    phase, _ = _replay_phase_to(2, through_round=1)
    ledger = phase.state.ledger
    claude_raised = {e.id for e in ledger if e.raiser == "claude"}
    openai_raised = {e.id for e in ledger if e.raiser == "openai"}
    assert claude_raised and openai_raised, "captured round 1 must raise items on both sides"

    claude_view = _format_standing_items(phase, "claude")
    openai_view = _format_standing_items(phase, "openai")

    # claude (raiser of the -c- items) must see them under the raiser-open
    # group with the no-self-address guidance — NOT under an ADDRESS mandate.
    c_addressee_block = _group_block(claude_view, "you are the ADDRESSEE")
    for cid in claude_raised:
        assert cid not in _ids_in(c_addressee_block), f"{cid} (claude's own) must not be in claude's ADDRESSEE group"
    c_raiser_block = _group_block(claude_view, "still open (NOT yet addressed)")
    assert claude_raised <= _ids_in(c_raiser_block)
    assert "Do NOT emit `### ADDRESS" in claude_view

    # Symmetric: claude is the addressee for every openai-raised item.
    assert openai_raised <= _ids_in(c_addressee_block)
    assert "MUST emit `### ADDRESS" in claude_view

    # And the mirror image holds for openai's view.
    o_addressee_block = _group_block(openai_view, "you are the ADDRESSEE")
    assert claude_raised <= _ids_in(o_addressee_block)
    for oid in openai_raised:
        assert oid not in _ids_in(o_addressee_block)


def test_phase2_captured_artifact_reproduces_the_three_violation_classes():
    """Spec-0238 discipline: the captured turns must reproduce, through the
    real ``apply_turn`` path, the exact ownership-violation classes spec
    0257 targets. If a future change makes the captured artifact stop
    reproducing them, this fixture has gone stale and the replay above is
    no longer guarding the real failure.
    """
    _phase, violations = _replay_phase_to(2, through_round=2)
    r2 = violations[2]
    # claude self-addressed its own open items and resolved-from-open.
    assert "raiser_self_address" in r2["claude"]
    assert "resolve_from_non_addressed" in r2["claude"]
    # openai declared AGREED while claude-raised items were still open.
    assert "agreed_with_open_addressed_items" in r2["openai"]


def test_phase4_replay_runs_and_reports_self_address_count(capsys):
    """Phase 4 is MEASUREMENT, not a pass/fail gate (spec 0257 §2.2 /
    §6.2 — phase 4 is an asymmetric drafter/reviewer axis; whether the
    corrected callout alone zeroes ``raiser_self_address`` is observed in
    the live re-run, and a non-zero residual triggers the 0257.2 carve-out
    rather than failing this test). Here we only assert the replay drives
    the real path end-to-end and surface the count for the PR record.
    """
    fx = FIXTURES / "phase4"
    rounds = sorted(
        int(p.name.split("-")[1])
        for p in fx.glob("round-*-claude.md")
    )
    phase, violations = _replay_phase_to(4, through_round=max(rounds))
    self_address_total = sum(
        codes.count("raiser_self_address")
        for per_agent in violations.values()
        for codes in per_agent.values()
    )
    print(f"[spec 0257 §6.2] phase-4 vendored raiser_self_address count = {self_address_total}")
    # Non-gating: the count is reported, not asserted to be zero. The
    # replay must have produced a populated ledger (the path ran).
    assert phase.state.ledger
    assert self_address_total >= 0


# ─── tiny block / id helpers ──────────────────────────────────────────


def _group_block(out: str, header_substr: str) -> str:
    """Return the one role group whose header line contains ``header_substr``.

    Groups are delimited by HEADER lines that begin at column 0 with
    ``### ``. Instruction text embeds inline ``` `### ADDRESS` ``` markers
    (preceded by a backtick, never at line start), so splitting on the
    line-anchored ``\\n### `` boundary keeps each group's items with its
    header and never severs the block at an inline op reference.
    """
    for part in ("\n" + out).split("\n### "):
        if header_substr in part.split("\n", 1)[0]:
            return part
    return ""


def _ids_in(block: str) -> set[str]:
    import re
    return set(re.findall(r"\[([^\]]+)\]", block))
