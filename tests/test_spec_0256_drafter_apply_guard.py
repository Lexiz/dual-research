"""Spec 0256 — drafter-delta apply guard, drafter resync, strict anchor
contract.

Four load-bearing changes ship together:

- §2.1 APPLY-GUARD — an apply-time anchor failure triggers the same no-op
  fallback as a parse failure, instead of propagating to the run-level
  tombstone (run_failed → EXIT_RUNTIME with no final.md). This is the
  run-saving guard.
- §2.2 DRAFTER RESYNC — when a revision no-ops, the next-round drafter
  prompt carries an explicit "your previous revision did NOT apply" banner.
- §2.3 ANCHOR ROBUSTNESS — strict deterministic normalization at match time
  (whitespace-run collapse, smart→straight quotes, trailing-punct tolerance)
  + a tighter anchor-contract prompt. NOT fuzzy: a similar-but-different
  anchor must NOT match.
- §2.4 SECONDARY — the drafter-path phase-4 prompt no longer presents an
  ADDRESS affordance for the drafter's own items (raiser_self_address ×7 in
  the evidence run).

The load-bearing regression (per CLAUDE.md spec-0238 live-failure-fix
discipline) exercises the **real entry point** ``_apply_drafter_revised_draft``
against the **captured artifacts** from the live run
``20260529-164844-backend-language-choice`` — the run that died at
EXIT_RUNTIME with no final.md. Vendored fixtures live under
``tests/fixtures/spec_0256/phase4/``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from dual_research.events import (
    EventBus,
    Phase4DraftRevised,
    ProtocolViolation,
)
from dual_research.orchestrator.dr_run import _apply_drafter_revised_draft
from dual_research.persistence import SessionContext
from dual_research.persistence.metrics import Metrics
from dual_research.persistence.session import SessionDirectory
from dual_research.persistence.state import SessionState, write_atomic
from dual_research.protocol.parse import (
    _edit_section_apply_one,
    apply_revised_draft_deltas,
)
from dual_research.protocol.prompts import review_round_n_prompt_v2

_FIXTURES = Path(__file__).parent / "fixtures" / "spec_0256" / "phase4"


def _seed_ctx(tmp_path: Path, *, draft_round: int, draft_text: str) -> SessionContext:
    """Build a SessionContext with the current draft seeded at the canonical
    location (phase3/draft-v1.md for round 1, phase4/draft-vN.md otherwise)."""
    from dual_research.orchestrator.phase3 import current_draft_path

    session = SessionDirectory(root=tmp_path).ensure()
    state = SessionState(drafter="claude", draft_round=draft_round)
    session.save_state(state)
    write_atomic(current_draft_path(session, draft_round), draft_text)
    return SessionContext(
        session=session,
        state=state,
        transcript=session.open_transcript(),
        metrics=Metrics(),
    )


# ─── §6 item 1 + 2 — real-entry-point regression + no wrong-section corruption ──


def test_captured_run_no_longer_crashes_and_no_wrong_section_corruption(
    tmp_path: Path,
) -> None:
    """Load-bearing: replay the captured no-op-at-r2 → anchor-mismatch-at-r3
    sequence through the real ``_apply_drafter_revised_draft`` entry point.

    Captured behaviour of the vendored turns (verified at authoring time):
      - ``round-02-claude.md`` fails to PARSE (``revised_draft_body_missing_
        delta_op``) → parse-step fallback (spec 0231).
      - ``round-03-claude.md`` PARSES but its EDIT_SECTION anchors (multi-line
        body + table-row literals against a draft that diverged) fail to
        match at APPLY time → apply-step fallback (spec 0256 §2.1, the new
        guard). Before this spec, that raise propagated to the run-level
        tombstone → run_failed → EXIT_RUNTIME with no final.md.

    Asserts: (1) neither call raises and the run survives; (2) a final
    on-disk draft is always produced; (3) every round emits exactly one
    ``phase4_drafter_repair_failed``; (4) no wrong-section corruption — the
    four "Tier 2 Scoring" sections (the fuzzy-match trap) are byte-unchanged.
    """
    draft_v2 = (_FIXTURES / "draft-v2.md").read_text(encoding="utf-8")
    r2_turn = (_FIXTURES / "round-02-claude.md").read_text(encoding="utf-8")
    r3_turn = (_FIXTURES / "round-03-claude.md").read_text(encoding="utf-8")

    ctx = _seed_ctx(tmp_path, draft_round=2, draft_text=draft_v2)
    bus = EventBus()
    seen: list = []
    bus.subscribe(lambda e: seen.append(e))

    async def _apply(round: int, revised_text: str):
        return await _apply_drafter_revised_draft(
            ctx=ctx,
            event_bus=bus,
            round=round,
            revised_text=revised_text,
            drafter="claude",
        )

    # r2: parse-step no-op (spec 0231).
    res2 = asyncio.run(_apply(2, r2_turn))
    # r3: apply-step no-op (spec 0256 §2.1) — the captured crash point.
    res3 = asyncio.run(_apply(3, r3_turn))

    # (1) neither raised; both wrote a (no-op) revision.
    assert res2.written is True and res2.noop is True
    assert res3.written is True and res3.noop is True

    # (2) a final on-disk draft is always produced, byte-equal to the prior
    #     (the no-op contract): the run can finalize, not die.
    final_draft_path = tmp_path / "phase4" / f"draft-v{ctx.state.draft_round}.md"
    assert final_draft_path.exists()
    final_draft = final_draft_path.read_text(encoding="utf-8")
    assert final_draft == draft_v2

    # (3) one phase4_drafter_repair_failed per round (parse-step + apply-step).
    repair_failed = [
        e for e in seen
        if isinstance(e, ProtocolViolation)
        and e.violation_code == "phase4_drafter_repair_failed"
    ]
    assert len(repair_failed) == 2, [e.reason[:80] for e in repair_failed]
    # The r3 fallback is specifically the apply-time anchor failure.
    assert any(
        "edit_section_anchor_not_found" in e.reason for e in repair_failed
    ), "expected the r3 apply-step fallback to cite edit_section_anchor_not_found"

    # (4) No wrong-section corruption: the four "Tier 2 Scoring" sections that
    #     a fuzzy match could have cross-bound are byte-unchanged. (Byte-equal
    #     final draft already implies this; assert the trap content explicitly
    #     so a future regression that *does* corrupt a section is caught here.)
    for marker in (
        "### Section 3 — Tier 2 Scoring",
        "### Section 4 — Tier 2 Scoring",
        "### Section 5 — Tier 2 Scoring",
        "### Section 6 — Tier 2 Scoring",
    ):
        assert final_draft.count(marker) == draft_v2.count(marker)


# ─── §6 item 3 — apply-guard unit coverage (distinct from parse-step path) ──────


def test_apply_guard_catches_apply_time_anchor_failure(tmp_path: Path) -> None:
    """Spec 0256 §2.1 — a turn that PARSES cleanly but whose EDIT_SECTION
    anchor does not match at apply time is caught and converted to the same
    no-op fallback as a parse failure: byte-equal draft + one
    ``phase4_drafter_repair_failed``. This is the apply-step path, distinct
    from the spec-0231 parse-step path.
    """
    prior = (
        "## 1. Summary\n"
        "The real summary body, verbatim.\n\n"
        "## 2. Findings\n"
        "Real findings body.\n"
    )
    ctx = _seed_ctx(tmp_path, draft_round=1, draft_text=prior)
    bus = EventBus()
    seen: list = []
    bus.subscribe(lambda e: seen.append(e))

    # Parses fine (well-formed EDIT_SECTION delta op against a real heading),
    # but the ANCHOR is genuinely absent from the section body → apply raises.
    turn = (
        "## Stance\nstance.\n\n"
        "## Status\nSTATUS: REVIEWING\n\n"
        "## Revised draft\n\n"
        "### EDIT_SECTION 1. Summary\n\n"
        "ANCHOR: A line that is not present in the summary at all.\n"
        "REPLACE_WITH: Replacement that must never land.\n"
    )

    async def _run():
        return await _apply_drafter_revised_draft(
            ctx=ctx, event_bus=bus, round=2, revised_text=turn, drafter="claude",
        )

    res = asyncio.run(_run())
    assert res.written is True
    assert res.noop is True  # apply-guard fired

    new_draft = (tmp_path / "phase4" / "draft-v2.md").read_text(encoding="utf-8")
    assert new_draft == prior  # byte-equal no-op
    assert "Replacement that must never land." not in new_draft

    pvs = [
        e for e in seen
        if isinstance(e, ProtocolViolation)
        and e.violation_code == "phase4_drafter_repair_failed"
    ]
    assert len(pvs) == 1
    assert "edit_section_anchor_not_found" in pvs[0].reason
    # The round loop still hands off to the next round.
    assert ctx.state.draft_round == 2
    assert any(isinstance(e, Phase4DraftRevised) for e in seen)


# ─── §6 item 4 — resync signal banner gating ───────────────────────────────────

_BANNER_MARK = "YOUR PREVIOUS REVISION DID NOT APPLY"


def _round_n_prompt(*, agent_name: str, prior_revision_noop: bool) -> str:
    return review_round_n_prompt_v2(
        brief_content="brief",
        draft_content="## 1. Summary\nbody\n",
        drafter_name="claude",
        prior_turns=[],
        standing_items="",
        agent_name=agent_name,
        other_name="openai" if agent_name == "claude" else "claude",
        round=3,
        soft_cap=6,
        hard_cap=10,
        draft_version=2,
        draft_headings=["1. Summary"],
        prior_revision_noop=prior_revision_noop,
        prior_revision_noop_errors=["edit_section_anchor_not_found: ..."],
    )


def test_resync_banner_present_only_when_drafter_revision_noopd() -> None:
    """Spec 0256 §2.2 — the resync banner appears in the DRAFTER's next-round
    prompt when (and only when) the prior round no-op'd, and never for the
    REVIEWER."""
    # Drafter, prior round no-op'd → banner present.
    assert _BANNER_MARK in _round_n_prompt(agent_name="claude", prior_revision_noop=True)
    # Drafter, clean prior apply → banner absent.
    assert _BANNER_MARK not in _round_n_prompt(agent_name="claude", prior_revision_noop=False)
    # Reviewer never gets the banner, even if the flag is (defensively) set.
    assert _BANNER_MARK not in _round_n_prompt(agent_name="openai", prior_revision_noop=True)


# ─── §6 item 5 — strict normalization, both directions (no fuzzy) ───────────────


def test_strict_normalization_matches_tolerated_differences() -> None:
    """Spec 0256 §2.3(a) — anchors differing from the body only by inner-
    whitespace runs, smart-vs-straight quotes, or a trailing punctuation char
    match and replace correctly."""
    # inner whitespace-run collapse
    body, status = _edit_section_apply_one("\nFoo   bar   baz here.\n", "Foo bar baz", "X")
    assert status == "ok" and body == "\nX here.\n"
    # smart → straight quotes
    body, status = _edit_section_apply_one("\nThe drafter’s plan is set.\n", "The drafter's plan", "Y")
    assert status == "ok" and body == "\nY is set.\n"
    # trailing-punct tolerance on the anchor (anchor has ':', body does not)
    body, status = _edit_section_apply_one("\n### Section 3 — Tier 2 Scoring\nrest\n", "### Section 3 — Tier 2 Scoring:", "Z")
    assert status == "ok" and body == "\nZ\nrest\n"


def test_strict_normalization_rejects_absent_and_similar_anchors() -> None:
    """Spec 0256 §2.3(a) — NOT fuzzy. A genuinely-absent anchor (the r3
    divergence case) and a similar-but-different anchor both fail to match;
    there is no similarity fallthrough."""
    # genuinely absent (the evidence divergence): "Summary" subsection that
    # does not exist — the real heading is "Tier 2 Scoring: AI fitness".
    _, status = _edit_section_apply_one(
        "\n### Section 3 — Tier 2 Scoring: AI fitness\nbody\n",
        "### Section 3 — Tier 2 Scoring Summary",
        "Q",
    )
    assert status == "not_found"
    # similar-but-different — one token differs; must NOT fuzzy-match.
    _, status = _edit_section_apply_one("\nalpha beta gamma\n", "alpha beta delta", "Q")
    assert status == "not_found"


def test_strict_normalization_ambiguous_still_raises() -> None:
    """Spec 0256 §2.3(a) — `>1` normalized matches still raise ambiguity
    (no silent first-match replace)."""
    _, status = _edit_section_apply_one("\nrepeated line\nrepeated line\n", "repeated line", "Q")
    assert status == "ambiguous"


def test_apply_deltas_strict_normalization_via_public_entry() -> None:
    """The normalization is reached through the public
    ``apply_revised_draft_deltas`` EDIT_SECTION branch, not just the helper:
    a smart-quote-only difference matches; an absent anchor raises
    ``edit_section_anchor_not_found``."""
    from dual_research.protocol.errors import ProtocolParseError
    from dual_research.protocol.parse import EditSectionOp, RevisedDraftDeltas

    prior = "## 1. Summary\nThe team’s decision is final.\n"
    payload = RevisedDraftDeltas(
        ops=[EditSectionOp(heading="1. Summary", edits=[("The team's decision", "The verdict")])]
    )
    new_draft, _ = apply_revised_draft_deltas(prior_draft=prior, payload=payload)
    assert "The verdict is final." in new_draft

    bad = RevisedDraftDeltas(
        ops=[EditSectionOp(heading="1. Summary", edits=[("nonexistent anchor", "X")])]
    )
    try:
        apply_revised_draft_deltas(prior_draft=prior, payload=bad)
        raise AssertionError("expected ProtocolParseError")
    except ProtocolParseError as e:
        assert any("edit_section_anchor_not_found" in err for err in e.errors)


# ─── §6 item 6 — raiser_self_address: prompt fix + drop-semantics pin ───────────


def test_drafter_prompt_forbids_self_address_affordance() -> None:
    """Spec 0256 §2.4 — the round-N prompt makes the "ADDRESS only the other
    agent's items; use RESOLVE/WITHDRAW/ACKNOWLEDGE for your own" rule
    unambiguous on the DRAFTER path (the drafter self-addressed ×7 in the
    evidence run)."""
    prompt = _round_n_prompt(agent_name="claude", prior_revision_noop=False)
    # The "Addressing items raised against me" section explicitly scopes
    # ADDRESS to the other agent and forbids self-address. (Collapse
    # whitespace so the assertion is robust to prompt line-wrapping.)
    collapsed = " ".join(prompt.split())
    assert "ADDRESS targets ONLY openai's items — NEVER your own" in collapsed
    assert "self-address protocol violation" in collapsed
    # The "Ratifying my own items" section routes own-item actions to
    # RESOLVE/ACKNOWLEDGE/WITHDRAW, explicitly NOT ADDRESS.
    assert "RESOLVE / ACKNOWLEDGE / WITHDRAW / counter-argument — NOT ADDRESS" in collapsed


def test_self_address_drop_semantics_unchanged() -> None:
    """Spec 0256 §2.4 — pin: the apply-layer drop semantics for a
    self-addressed item (deep_research.py) are unchanged — a
    ``raiser_self_address`` ProtocolViolation is still emitted (full
    behavioural coverage lives in
    tests/orchestrator/test_spec_0216_raiser_self_address.py)."""
    from dual_research.orchestrator import deep_research

    src = Path(deep_research.__file__).read_text(encoding="utf-8")
    assert 'violation_code="raiser_self_address"' in src
    assert "an agent cannot ADDRESS their own item" in src
