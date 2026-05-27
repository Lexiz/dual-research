"""Spec 0231 — parser heading tolerance and graceful repair fallback.

Three layers ship together, each independently testable:

- §2.1: parser strips a leading ``## `` token in section-heading
  arguments (`### EDIT_SECTION ## 1. Summary`) — see the parse-level
  unit tests in ``tests/protocol/test_parse.py``.
- §2.2: parser accepts glued ``## <heading><prose>`` — same file.
- §2.3: drafter-side no-op fallback + mandatory ProtocolViolation when
  the revised-draft body fails to parse even after repair — this file.

The §2.3 fallback replaces the silent ``except ProtocolParseError: pass``
in ``parse_v2_with_repair`` (drafter-only) plus the uncaught raise that
was crashing the run at ``dr_run.py:1426`` in the anchor-run
``20260527-054652-backend-language-choice`` failure.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from dual_research.events import (
    EventBus,
    Phase4DraftRevised,
    ProtocolViolation,
)
from dual_research.orchestrator.dr_run import _apply_drafter_revised_draft
from dual_research.orchestrator.repair import RepairTracker
from dual_research.persistence import SessionContext
from dual_research.persistence.metrics import Metrics
from dual_research.persistence.session import SessionDirectory
from dual_research.persistence.state import SessionState, write_atomic


_PRIOR_DRAFT = (
    "## 1. Summary\n"
    "Original summary body.\n\n"
    "## 2. Findings\n"
    "Original findings body.\n"
)


_UNPARSEABLE_REVISED_TURN = (
    "## Stance\nstance.\n\n"
    "## Status\nSTATUS: REVIEWING\n\n"
    "## Revised draft\n\n"
    "# Decision: Backend Language\n\n"
    "This is the entire revised draft as inline prose, no delta sub-headings.\n"
    "Lots more paragraphs would follow in a real run.\n"
)


def _session_ctx(tmp_path: Path) -> SessionContext:
    """Build a minimal SessionContext with phase3/draft-v1.md seeded."""
    session = SessionDirectory(root=tmp_path).ensure()
    state = SessionState(drafter="claude", draft_round=1)
    session.save_state(state)
    write_atomic(session.phase_dir("phase3") / "draft-v1.md", _PRIOR_DRAFT)
    return SessionContext(
        session=session,
        state=state,
        transcript=session.open_transcript(),
        metrics=Metrics(),
    )


def test_fallback_fires_writes_byte_equal_noop_draft_and_emits_protocol_violation(
    tmp_path: Path,
) -> None:
    """Spec 0231 §2.3b/§2.3c — synthetic phase-4 round where the drafter
    emits unparseable output and ``parse_v2_with_repair`` couldn't recover.

    Asserts:
      (i)   the call returns ``True`` (revision applied) and does NOT raise;
      (ii)  ``phase4/draft-v2.md`` is byte-equal to ``phase3/draft-v1.md``
            (the no-op preserves the prior draft body verbatim, NOT the
            unparseable original);
      (iii) exactly one ``ProtocolViolation`` with
            ``violation_code="phase4_drafter_repair_failed"`` is published,
            naming the drafter and the underlying parse error in
            ``reason``;
      (iv)  ``state.draft_round`` advances to 2 and a
            ``Phase4DraftRevised`` event is published (the round loop's
            handoff to the next round is unchanged).
    """
    ctx = _session_ctx(tmp_path)
    bus = EventBus()
    seen: list = []
    bus.subscribe(lambda e: seen.append(e))

    async def _run() -> bool:
        return await _apply_drafter_revised_draft(
            ctx=ctx,
            event_bus=bus,
            round=2,
            revised_text=_UNPARSEABLE_REVISED_TURN,
            drafter="claude",
        )

    applied = asyncio.run(_run())

    # (i) returned True, no exception.
    assert applied is True

    # (ii) byte-equal no-op draft.
    new_draft_path = tmp_path / "phase4" / "draft-v2.md"
    assert new_draft_path.exists()
    assert new_draft_path.read_text(encoding="utf-8") == _PRIOR_DRAFT

    # (iii) exactly one ProtocolViolation with the spec-0231 code.
    pvs = [e for e in seen if isinstance(e, ProtocolViolation)]
    assert len(pvs) == 1
    pv = pvs[0]
    assert pv.violation_code == "phase4_drafter_repair_failed"
    assert pv.agent == "claude"
    assert pv.phase == 4
    assert pv.round == 2
    assert pv.op_kind == "revised_draft"
    assert "revised_draft_body_missing_delta_op" in pv.reason
    assert "no-op fallback applied" in pv.reason
    # item_id / from_state are empty for whole-turn conditions per the
    # extended docstring at events/types.py.
    assert pv.item_id == ""
    assert pv.from_state == ""

    # (iv) state advanced AND Phase4DraftRevised emitted.
    assert ctx.state.draft_round == 2
    revised_events = [e for e in seen if isinstance(e, Phase4DraftRevised)]
    assert len(revised_events) == 1
    assert revised_events[0].new_draft_round == 2


def test_clean_revised_draft_does_not_fire_fallback(tmp_path: Path) -> None:
    """Spec 0231 §2.3 — back-compat. A well-formed delta-op turn applies
    normally, no ``phase4_drafter_repair_failed`` event is emitted, and
    the new draft reflects the edits (not byte-equal to the prior)."""
    ctx = _session_ctx(tmp_path)
    bus = EventBus()
    seen: list = []
    bus.subscribe(lambda e: seen.append(e))

    clean_turn = (
        "## Stance\nstance.\n\n"
        "## Status\nSTATUS: REVIEWING\n\n"
        "## Revised draft\n\n"
        "### EDIT_SECTION 1. Summary\n\n"
        "ANCHOR: Original summary body.\n"
        "REPLACE_WITH: Replaced summary body.\n"
    )

    async def _run() -> bool:
        return await _apply_drafter_revised_draft(
            ctx=ctx,
            event_bus=bus,
            round=2,
            revised_text=clean_turn,
            drafter="claude",
        )

    applied = asyncio.run(_run())
    assert applied is True

    new_draft = (tmp_path / "phase4" / "draft-v2.md").read_text(encoding="utf-8")
    assert "Replaced summary body." in new_draft
    assert "Original summary body." not in new_draft

    pvs = [e for e in seen if isinstance(e, ProtocolViolation)]
    assert pvs == [], f"unexpected ProtocolViolation events: {pvs!r}"


def test_omitted_revised_draft_section_is_noop_no_fallback(tmp_path: Path) -> None:
    """Spec 0218 §3.2 — back-compat. A turn that omits the ``## Revised
    draft`` section entirely (reviewer-style turn) returns False and
    writes no new draft; the §2.3 fallback does NOT fire."""
    ctx = _session_ctx(tmp_path)
    bus = EventBus()
    seen: list = []
    bus.subscribe(lambda e: seen.append(e))

    reviewer_turn = (
        "## Stance\nstance.\n\n"
        "## Status\nSTATUS: REVIEWING\n"
    )

    async def _run() -> bool:
        return await _apply_drafter_revised_draft(
            ctx=ctx,
            event_bus=bus,
            round=2,
            revised_text=reviewer_turn,
            drafter="claude",
        )

    applied = asyncio.run(_run())
    assert applied is False

    # No new draft file written.
    assert not (tmp_path / "phase4" / "draft-v2.md").exists()
    # No PV, no Phase4DraftRevised.
    pvs = [e for e in seen if isinstance(e, ProtocolViolation)]
    revised_events = [e for e in seen if isinstance(e, Phase4DraftRevised)]
    assert pvs == []
    assert revised_events == []
    # State unchanged.
    assert ctx.state.draft_round == 1


def test_parse_v2_with_repair_does_not_raise_when_drafter_persists_malformed(
    tmp_path: Path,
) -> None:
    """Spec 0231 §2.3 — ``parse_v2_with_repair`` no longer raises on the
    drafter's 2nd consecutive parse failure; it now returns the malformed
    text so the downstream ``_apply_drafter_revised_draft`` fallback can
    no-op the revision. ``is_drafter=False`` still raises (reviewer keeps
    the exit-52 path).
    """
    from dual_research.agents.base import AgentResult, TokenUsage
    from dual_research.orchestrator.repair import parse_v2_with_repair

    class _ScriptedAgent:
        def __init__(self, label: str, response_text: str):
            self.label = label
            self.provider = "test"
            self._response_text = response_text

        @property
        def model_id(self) -> str:
            return f"{self.label}-model"

        async def run(
            self,
            prompt: str,
            *,
            max_output_tokens: int = 8192,
            stream_to=None,
            stream_prefix: str = "",
            audit_context=None,
        ) -> AgentResult:
            return AgentResult(
                text=self._response_text,
                usage=TokenUsage(input_tokens=100, output_tokens=50),
                cost_usd=0.01,
                duration_ms=10,
                model_id=self.model_id,
                provider=self.provider,
                label=self.label,
                extras={"stop_reason": "end_turn"},
            )

    session = SessionDirectory(root=tmp_path).ensure()
    session.brief_path.write_text("# Brief\n", encoding="utf-8")
    transcript = session.open_transcript()

    # First-failure path: tracker.consecutive_failures == 0 → record → 1
    # → repair fires → repaired text ALSO fails → except pass → returns
    # the malformed text. No raise from parse_v2_with_repair itself in
    # round N. Second round (failures → 2) is where the drafter exemption
    # kicks in; that path is exercised below.
    agent = _ScriptedAgent("claude", _UNPARSEABLE_REVISED_TURN)
    bus = EventBus()
    tracker = RepairTracker()
    # Pre-seed the tracker with a prior failure so the next record_failure
    # call trips ``failures >= 2``.
    tracker.record_failure("claude")
    out_path = tmp_path / "round-02-claude.md"

    async def _drive_drafter() -> tuple[str, object]:
        return await parse_v2_with_repair(
            agent=agent,
            text=_UNPARSEABLE_REVISED_TURN,
            phase=4,
            round=2,
            tracker=tracker,
            session=session,
            session_phase="phase4",
            transcript=transcript,
            event_bus=bus,
            metrics=Metrics(),
            out_path=out_path,
            is_drafter=True,
            prior_draft=_PRIOR_DRAFT,
        )

    # Drafter path: failures>=2 must NOT raise (spec 0231 §2.3).
    text, parsed = asyncio.run(_drive_drafter())
    assert text == _UNPARSEABLE_REVISED_TURN

    # Reviewer path: failures>=2 still raises (back-compat). The reviewer
    # validator's only universal gate is ``missing STATUS:`` — the
    # drafter-revised-draft check is skipped when ``is_drafter=False``
    # per spec 0219 §3.2. Use a turn with no ``## Status`` heading to
    # trip the reviewer-side failure.
    no_status_turn = (
        "## Stance\n"
        "no status block here.\n"
    )
    agent2 = _ScriptedAgent("claude", no_status_turn)
    tracker2 = RepairTracker()
    tracker2.record_failure("claude")

    async def _drive_reviewer() -> tuple[str, object]:
        return await parse_v2_with_repair(
            agent=agent2,
            text=no_status_turn,
            phase=4,
            round=2,
            tracker=tracker2,
            session=session,
            session_phase="phase4",
            transcript=transcript,
            event_bus=bus,
            metrics=Metrics(),
            out_path=tmp_path / "round-02-openai.md",
            is_drafter=False,
            prior_draft=None,
        )

    from dual_research.protocol.errors import ProtocolParseError as _PPE
    with pytest.raises(_PPE):
        asyncio.run(_drive_reviewer())
