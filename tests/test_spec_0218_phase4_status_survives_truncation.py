"""Spec 0218 — phase-4 STATUS survives truncation.

Six regression tests for the four coordinated fixes in spec 0218:
  - §3.1 — STATUS-first ordering across all 5 prompt sites
  - §3.2 — section-delta `## Revised draft` contract
  - §3.3 — `finish_reason in {max_tokens, length}` is a synthetic parse failure
  - §3.4 — bumped `_TURN_MAX_OUTPUT_TOKENS` + Anthropic beta header

All six tests MUST fail on `main` before this spec lands and pass after.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TextIO

import pytest

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.events import EventBus, RepairInvoked
from dual_research.orchestrator.repair import (
    RepairTracker,
    parse_v2_with_repair,
)
from dual_research.persistence import Metrics, SessionDirectory
from dual_research.persistence.state import write_atomic
from dual_research.protocol import (
    AppendSectionOp,
    DeleteSectionOp,
    ProtocolParseError,
    ReplaceSectionOp,
    RevisedDraftDeltas,
    RevisedDraftFull,
    apply_revised_draft_deltas,
    extract_revised_draft_deltas,
)
from dual_research.protocol.prompts import (
    input_negotiation_prompt_v2,
    plan_negotiation_round_n_prompt_v2,
    preflight_prompt_v2,
    review_round1_prompt_v2,
    review_round_n_prompt_v2,
)


# ─── 5.1 — STATUS-first ordering across all prompt sites ───────────────


_BODY_HEADINGS_REVIEW_RN = (
    "## Revised draft",
    "## Addressing items raised against me",
    "## Ratifying my own items",
    "## New items I'm raising",
    "## Phase artifact",
)
_BODY_HEADINGS_REVIEW_R1 = (
    "## Addressing items raised against me",
    "## Ratifying my own items",
    "## New items I'm raising",
)
_BODY_HEADINGS_NEGOTIATION = (
    "## Addressing items raised against me",
    "## Ratifying my own items",
    "## New items I'm raising",
    "## Phase artifact",
)
_BODY_HEADINGS_NEGOTIATION_R1 = (
    "## Addressing items raised against me",
    "## Ratifying my own items",
    "## New items I'm raising",
)


def _status_index(text: str) -> int:
    m = re.search(r"^## Status\b", text, re.MULTILINE)
    assert m is not None, "## Status heading must be present in rendered prompt"
    return m.start()


def _heading_index(text: str, heading: str) -> int:
    m = re.search(r"^" + re.escape(heading) + r"\b", text, re.MULTILINE)
    return m.start() if m else -1


def test_5_1_status_first_ordering_phase4_round_n():
    out = review_round_n_prompt_v2(
        brief_content="brief",
        draft_content="## 1. Summary\nbody\n",
        drafter_name="claude",
        prior_turns=[],
        standing_items="",
        agent_name="claude",
        other_name="openai",
        round=2,
        soft_cap=4,
        hard_cap=6,
        draft_version=1,
    )
    s = _status_index(out)
    for h in _BODY_HEADINGS_REVIEW_RN:
        pos = _heading_index(out, h)
        assert pos != -1, f"{h!r} must appear in phase-4 round-N prompt"
        assert s < pos, (
            f"## Status (at {s}) must appear before {h!r} (at {pos}) "
            "— spec 0218 §3.1 STATUS-first ordering"
        )


def test_5_1_status_first_ordering_phase4_round1():
    out = review_round1_prompt_v2(
        brief_content="brief",
        draft_content="## 1. Summary\nbody\n",
        drafter_name="claude",
        agent_name="claude",
        other_name="openai",
    )
    s = _status_index(out)
    for h in _BODY_HEADINGS_REVIEW_R1:
        pos = _heading_index(out, h)
        assert pos != -1
        assert s < pos, (
            f"phase-4 round-1: ## Status (at {s}) must appear before {h!r} (at {pos})"
        )


def test_5_1_status_first_ordering_phase2_round_n():
    out = plan_negotiation_round_n_prompt_v2(
        brief_content="brief",
        agreed_interpretation="AI",
        own_plan="OP",
        other_plan="OTP",
        prior_turns=[],
        standing_items="",
        agent_name="claude",
        other_name="openai",
        round=2,
        soft_cap=4,
        hard_cap=6,
    )
    s = _status_index(out)
    for h in _BODY_HEADINGS_NEGOTIATION:
        pos = _heading_index(out, h)
        assert pos != -1
        assert s < pos, (
            f"phase-2 round-N: ## Status (at {s}) must appear before {h!r} (at {pos})"
        )


def test_5_1_status_first_ordering_phase0_round1():
    out = preflight_prompt_v2(
        brief_content="brief",
        agent_name="claude",
        other_name="openai",
    )
    s = _status_index(out)
    for h in _BODY_HEADINGS_NEGOTIATION_R1:
        pos = _heading_index(out, h)
        assert pos != -1
        assert s < pos, (
            f"phase-0 round-1: ## Status (at {s}) must appear before {h!r} (at {pos})"
        )


def test_5_1_status_first_ordering_phase0_round_n():
    out = input_negotiation_prompt_v2(
        brief_content="brief",
        prior_turns=[],
        standing_items="",
        agent_name="claude",
        other_name="openai",
        round=2,
        soft_cap=4,
        hard_cap=6,
    )
    s = _status_index(out)
    for h in _BODY_HEADINGS_NEGOTIATION:
        pos = _heading_index(out, h)
        assert pos != -1
        assert s < pos, (
            f"phase-0 round-N: ## Status (at {s}) must appear before {h!r} (at {pos})"
        )


# ─── 5.2 — Section-delta application ───────────────────────────────────


def test_5_2_section_delta_application_produces_correct_draft_v_n_plus_1():
    prior_draft = (
        "## 1. Summary\n\nOriginal summary body.\n\n"
        "## 2. Findings\n\nOriginal findings body.\n\n"
        "## 3. Sources\n\nOriginal sources body.\n"
    )
    turn_text = (
        "## Stance\nfoo\n\n"
        "## Status\nSTATUS: IN_PROGRESS\nRAISED_THIS_TURN: []\n\n"
        "## Revised draft\n\n"
        "### REPLACE_SECTION 2. Findings\n\n"
        "Replaced findings line 1\nReplaced findings line 2\n\n"
        "### APPEND_SECTION 4. Confidence ledger\n\n"
        "Ledger row A\n\n"
        "### DELETE_SECTION 3. Sources\n"
    )
    payload = extract_revised_draft_deltas(turn_text)
    assert isinstance(payload, RevisedDraftDeltas)
    assert len(payload.ops) == 3
    new_draft, violations = apply_revised_draft_deltas(
        prior_draft=prior_draft, payload=payload,
    )
    # Summary unchanged.
    assert "## 1. Summary" in new_draft
    assert "Original summary body" in new_draft
    # Findings body replaced.
    assert "Replaced findings line 1" in new_draft
    assert "Original findings body" not in new_draft
    # Sources removed.
    assert "## 3. Sources" not in new_draft
    assert "Original sources body" not in new_draft
    # Confidence ledger appended.
    assert "## 4. Confidence ledger" in new_draft
    assert "Ledger row A" in new_draft
    # No violations on a clean turn.
    assert violations == []


# ─── 5.3 — prose-body Revised draft is rejected ────────────────────────


def test_5_3_prose_body_revised_draft_raises_protocol_parse_error():
    """Legacy full-prose `## Revised draft` body (no `### REPLACE_*` /
    `### APPEND_*` / `### DELETE_*` / `### REPLACE_DRAFT_FULL` sub-heading)
    is rejected. Routes through repair via parse_v2_with_repair."""
    turn_text = (
        "## Stance\nfoo\n\n"
        "## Status\nSTATUS: IN_PROGRESS\n\n"
        "## Revised draft\n\n"
        "# Decision: Backend Language\n\n"
        "This is the entire revised draft as inline prose, no delta sub-headings.\n"
        "Lots more paragraphs would follow in a real run.\n"
    )
    with pytest.raises(ProtocolParseError) as ei:
        extract_revised_draft_deltas(turn_text)
    assert any("revised_draft_body_missing_delta_op" in e for e in ei.value.errors)


# ─── 5.4 — finish_reason raises ProtocolParseError via parse_v2_with_repair ──


class _ScriptedAgent:
    """Returns scripted (text, extras) tuples on successive calls.

    For finish-reason / repair tests where we want to control the agent's
    response across the original call + the repair retry.
    """

    def __init__(self, label: str, responses: list[tuple[str, dict]]):
        self.label = label
        self.provider = "test"
        self._responses = list(responses)
        self.call_count = 0

    @property
    def model_id(self) -> str:
        return f"{self.label}-model"

    async def run(
        self,
        prompt: str,
        *,
        max_output_tokens: int = 8192,
        stream_to: TextIO | None = None,
        stream_prefix: str = "",
        audit_context: dict | None = None,
    ) -> AgentResult:
        text, extras = self._responses[self.call_count]
        self.call_count += 1
        return AgentResult(
            text=text,
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            cost_usd=0.01,
            duration_ms=10,
            model_id=self.model_id,
            provider=self.provider,
            label=self.label,
            extras=extras,
        )


_VALID_TURN_TEXT = (
    "## Stance\nfoo\n\n"
    "## Status\n"
    "STATUS: IN_PROGRESS\n"
    "RAISED_THIS_TURN: []\n"
    "ADDRESSED_THIS_TURN: []\n"
    "RESOLVED_THIS_TURN: []\n"
    "ACKNOWLEDGED_THIS_TURN: []\n"
    "WITHDRAWN_THIS_TURN: []\n"
    "OPEN_QUESTIONS: 0\n"
    "OPEN_DISAGREEMENTS: 0\n"
)


def _session_ctx(tmp_path: Path):
    session = SessionDirectory(root=tmp_path).ensure()
    session.brief_path.write_text("# Brief\n", encoding="utf-8")
    transcript = session.open_transcript()
    return session, transcript


@pytest.mark.asyncio
async def test_5_4_max_tokens_raises_protocol_parse_error(tmp_path: Path):
    """A syntactically-valid turn (intact STATUS) with
    `extras["stop_reason"]="max_tokens"` is treated as malformed and routed
    through repair. On exhausted budget for the first call, the malformed
    response still gets logged but isn't sent back as canonical."""
    session, transcript = _session_ctx(tmp_path)
    # The truncated original is passed as ``text=`` directly; the scripted
    # agent only needs the repair-call response.
    agent = _ScriptedAgent(
        "claude",
        [
            (_VALID_TURN_TEXT, {"stop_reason": "end_turn", "searches": 0}),
        ],
    )
    bus = EventBus()
    repair_events: list = []
    bus.subscribe(lambda e: repair_events.append(e) if isinstance(e, RepairInvoked) else None)

    tracker = RepairTracker()
    out_path = tmp_path / "round-01-claude.md"
    final_text, parsed = await parse_v2_with_repair(
        agent=agent,
        text=_VALID_TURN_TEXT,
        phase=4,
        round=1,
        tracker=tracker,
        session=session,
        session_phase="phase4",
        transcript=transcript,
        event_bus=bus,
        metrics=Metrics(),
        out_path=out_path,
        finish_reason="max_tokens",
    )
    # Repair should have been invoked exactly once.
    assert len(repair_events) == 1
    assert "truncated_by_max_tokens" in repair_events[0].errors
    # The repaired text returned should be the second response (clean).
    assert final_text == _VALID_TURN_TEXT
    # Tracker should have spent the budget.
    assert tracker.budget["claude"] == 0


@pytest.mark.asyncio
async def test_5_4_length_finish_reason_also_triggers_repair(tmp_path: Path):
    """OpenAI's `finish_reason="length"` is the symmetric truncation
    signal and must be treated identically to `max_tokens`."""
    session, transcript = _session_ctx(tmp_path)
    agent = _ScriptedAgent(
        "openai",
        [
            (_VALID_TURN_TEXT, {"finish_reason": "stop", "searches": 0}),
        ],
    )
    bus = EventBus()
    repair_events: list = []
    bus.subscribe(lambda e: repair_events.append(e) if isinstance(e, RepairInvoked) else None)

    tracker = RepairTracker()
    out_path = tmp_path / "round-01-openai.md"
    final_text, parsed = await parse_v2_with_repair(
        agent=agent,
        text=_VALID_TURN_TEXT,
        phase=4,
        round=1,
        tracker=tracker,
        session=session,
        session_phase="phase4",
        transcript=transcript,
        event_bus=bus,
        metrics=Metrics(),
        out_path=out_path,
        finish_reason="length",
    )
    assert len(repair_events) == 1
    assert "truncated_by_max_tokens" in repair_events[0].errors


# ─── 5.5 — truncated turn never lands as canonical ─────────────────────


@pytest.mark.asyncio
async def test_5_5_truncated_turn_does_not_land_as_canonical(tmp_path: Path):
    """Mock the drafter: first call returns text ending mid-section with
    `stop_reason="max_tokens"`; the repair call returns clean text with
    `stop_reason="end_turn"`.

    Asserts:
      (i) the canonical write contains the REPAIRED text, not the
          truncated text;
      (ii) a `<turn>.malformed-1.md` sibling holds the discarded
           truncated bytes;
      (iii) RepairTracker.budget["claude"] == 0 after the repair;
      (iv) exactly one RepairInvoked event was published.
    """
    session, transcript = _session_ctx(tmp_path)
    truncated_text = (
        "## Stance\nfoo\n\n"
        "## Addressing items raised against me\n"
        "Some prose that ends mid-cell | **Java** | **"
    )
    repaired_text = _VALID_TURN_TEXT
    # ``truncated_text`` is passed as ``text=`` to parse_v2_with_repair — only
    # the repair-call response needs to be scripted here.
    agent = _ScriptedAgent(
        "claude",
        [
            (repaired_text, {"stop_reason": "end_turn", "searches": 0}),
        ],
    )
    bus = EventBus()
    repair_events: list = []
    bus.subscribe(lambda e: repair_events.append(e) if isinstance(e, RepairInvoked) else None)

    tracker = RepairTracker()
    out_path = tmp_path / "round-02-claude.md"
    final_text, parsed = await parse_v2_with_repair(
        agent=agent,
        text=truncated_text,
        phase=4,
        round=2,
        tracker=tracker,
        session=session,
        session_phase="phase4",
        transcript=transcript,
        event_bus=bus,
        metrics=Metrics(),
        out_path=out_path,
        finish_reason="max_tokens",
    )
    # The caller (dr_run.py) writes final_text to out_path AFTER this returns.
    write_atomic(out_path, final_text)

    # (i) canonical text == repaired, not truncated.
    canonical = out_path.read_text(encoding="utf-8")
    assert canonical == repaired_text
    assert canonical != truncated_text

    # (ii) malformed sidecar exists with the truncated bytes.
    malformed_files = sorted(out_path.parent.glob(f"{out_path.stem}.malformed-*.md"))
    assert len(malformed_files) == 1
    assert malformed_files[0].read_text(encoding="utf-8") == truncated_text

    # (iii) tracker budget exhausted.
    assert tracker.budget["claude"] == 0

    # (iv) exactly one RepairInvoked event published.
    assert len(repair_events) == 1


# ─── 5.6 — backend-language-choice R2 regression replay ────────────────


def _synthesise_r2_truncated_turn() -> str:
    """Synthetic fixture matching the shape of the captured R2 turn from
    `runs/20260525-162909-backend-language-choice/phase4/round-02-claude.md`:
    Stance + addressing-prose ending mid-table-cell ``| **Java** | **``,
    no `## Status` heading at all. The fixture is synthetic because the
    live run text is not checked into the repo; the test asserts the
    validator chain rejects this shape.
    """
    return (
        "## Stance\nDraft is materially solid; a few items to address.\n\n"
        "## Addressing items raised against me\n"
        "### ADDRESS Q-plan-c-01\n"
        "Response body discussing tradeoffs in detail.\n\n"
        "Long table starts here:\n\n"
        "| Language | Notes |\n|---|---|\n"
        "| **Go** | strong concurrency primitives |\n"
        "| **Java** | **"
    )


def test_5_6_backend_language_choice_r2_truncated_turn_replay():
    """Validator chain rejects the captured R2 truncated turn shape.

    The truncated turn has no `## Status` block — the validator raises
    `ProtocolParseError("missing STATUS:")`. With the spec 0218 §3.3
    `parse_v2_with_repair` wiring in place, this turn would NOT be
    written to the canonical path; it would be saved to a `.malformed-1.md`
    sidecar and the repair flow would invoke once.

    This test asserts the validator-level rejection (the parse stage).
    Test 5.5 asserts the canonical-write side of the contract end-to-end.
    """
    from dual_research.orchestrator.repair import _assert_v2_well_formed_turn
    from dual_research.protocol import parse_turn_v2

    fixture = _synthesise_r2_truncated_turn()
    parsed = parse_turn_v2(fixture)
    # parse_turn_v2 itself is tolerant — returns a ParsedTurnV2 with
    # status=None when no STATUS block was emitted.
    assert parsed.status is None
    # The v2 validator detects the missing STATUS and raises.
    with pytest.raises(ProtocolParseError) as ei:
        _assert_v2_well_formed_turn(parsed, fixture, "claude")
    assert any("missing STATUS:" in e for e in ei.value.errors)
