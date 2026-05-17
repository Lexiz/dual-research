from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.events import EventBus
from dual_research.orchestrator.phase2 import run_phase2
from dual_research.persistence import (
    Metrics,
    SessionContext,
    SessionDirectory,
    SessionState,
)
from tests.protocol.fixtures import (
    CANONICAL_AGREED_PLAN,
    plan_turn_agreed,
)


# Spec 0043 — these tests exercise the orchestrator's convergence
# detection with synthetic fixtures whose disagreement-section format
# predates the spec-0042 / spec-0043 parser conventions. The ledger
# cross-check would block convergence on D-N tokens parsed from the
# fixture text that don't match the canonical resolved format. Force
# legacy mode so these tests assert pre-spec convergence semantics;
# real-run integration is covered by dedicated ledger tests.
@pytest.fixture(autouse=True)
def _force_legacy_ledger(monkeypatch):
    monkeypatch.setenv("DR_LEDGER_MODE", "legacy")


# ---------- stub agent that can return per-call canned responses ----------


class ScriptedAgent:
    """Returns canned text in order, one per .run() call.

    If the script is exhausted, raises to fail the test loudly.
    """

    def __init__(self, *, label: str, model_id: str, script: list[str]):
        self.label = label
        self.model_id = model_id
        self.provider = "anthropic" if label == "claude" else "openai"
        self._script = list(script)
        self._idx = 0

    async def run(self, prompt, *, max_output_tokens=8192, stream_to=None, stream_prefix="", audit_context=None):
        if self._idx >= len(self._script):
            raise RuntimeError(
                f"ScriptedAgent({self.label}) script exhausted at call {self._idx + 1}; "
                f"prompt prefix: {prompt[:80]!r}"
            )
        text = self._script[self._idx]
        self._idx += 1
        return AgentResult(
            text=text,
            usage=TokenUsage(input_tokens=10, output_tokens=20),
            cost_usd=0.0001,
            duration_ms=10,
            model_id=self.model_id,
            provider=self.provider,
            label=self.label,
            extras={"stop_reason": "end_turn"},
        )


# ---------- round-1 canned content (lenient) ----------

ROUND1_CONTENT = """## Diff vs other's Phase 1
1. D-1: example difference

## Gaps I researched this round
1. (none)

## Updated position
Same as Phase 1.

## Open questions for other
(none)

## Initial plan proposal
- Section 1
- Section 2

## Drafter recommendation
- DRAFTER: claude
- DOMAIN_FIT_SELF: 4
- DOMAIN_FIT_OTHER: 4

## Status
STATUS: NEGOTIATING
OPEN_QUESTIONS: 0

## Sources
[1] https://example.com
"""


def _make_ctx(tmp_path: Path) -> tuple[SessionContext, EventBus]:
    sess = SessionDirectory(root=tmp_path / "run").ensure()
    # Seed required phase1 drafts
    p1 = sess.phase_dir("phase1")
    (p1 / "draft-claude.md").write_text("claude draft")
    (p1 / "draft-openai.md").write_text("openai draft")
    state = SessionState(phase="phase2")
    ctx = SessionContext(
        session=sess,
        state=state,
        transcript=sess.open_transcript(),
        metrics=Metrics(),
    )
    return ctx, EventBus()


# ---------- converges in round 2 ----------


@pytest.mark.asyncio
async def test_phase2_converges_in_round2(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path)
    events: list[str] = []
    bus.subscribe(lambda e: events.append(e.kind))

    agreed_turn = plan_turn_agreed("claude")
    claude_agent = ScriptedAgent(
        label="claude",
        model_id="claude-sonnet-4-6",
        script=[ROUND1_CONTENT, agreed_turn],
    )
    openai_agent = ScriptedAgent(
        label="openai",
        model_id="gpt-5.5",
        script=[ROUND1_CONTENT.replace("DRAFTER: claude", "DRAFTER: openai"), agreed_turn],
    )

    outcome = await run_phase2(
        ctx=ctx,
        claude_agent=claude_agent,
        openai_agent=openai_agent,
        event_bus=bus,
        brief_content="test brief",
        soft_cap=4,
        hard_cap=6,
    )

    assert outcome.converged is True
    assert outcome.rounds == 2
    assert outcome.drafter == "claude"
    assert outcome.hard_capped is False
    assert outcome.parse_failure is False
    assert ctx.state.phase == "phase3"
    assert ctx.state.drafter == "claude"
    assert ctx.state.agreed_plan is not None
    assert "phase2_round_complete" in events
    assert "phase2_complete" in events


# ---------- drafter-tiebreak path ----------


@pytest.mark.asyncio
async def test_phase2_drafter_tiebreak(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path)
    received_tiebreak: list[dict] = []

    def sub(ev):
        if ev.kind == "drafter_tiebreak_resolved":
            received_tiebreak.append({"reason": ev.reason, "drafter": ev.selected_drafter})

    bus.subscribe(sub)

    # Both agents emit AGREED with matching plan but different DRAFTER.
    # Domain fit: claude self=5 + openai's other=5 → 10. openai self=2 + claude's other=2 → 4.
    # So domain-fit wins for claude.
    claude_agreed = plan_turn_agreed("claude", fit_self=5, fit_other=2)
    openai_agreed = plan_turn_agreed("openai", fit_self=2, fit_other=5)

    claude_agent = ScriptedAgent(
        label="claude",
        model_id="claude-sonnet-4-6",
        script=[ROUND1_CONTENT, claude_agreed],
    )
    openai_agent = ScriptedAgent(
        label="openai",
        model_id="gpt-5.5",
        script=[ROUND1_CONTENT.replace("DRAFTER: claude", "DRAFTER: openai"), openai_agreed],
    )

    outcome = await run_phase2(
        ctx=ctx,
        claude_agent=claude_agent,
        openai_agent=openai_agent,
        event_bus=bus,
        brief_content="test brief",
        soft_cap=4,
        hard_cap=6,
    )

    assert outcome.converged is True
    assert outcome.via_tiebreak is True
    assert outcome.drafter == "claude"
    assert len(received_tiebreak) == 1
    assert received_tiebreak[0]["reason"] == "domain-fit"
    assert received_tiebreak[0]["drafter"] == "claude"


# ---------- repair recovers a malformed turn ----------


@pytest.mark.asyncio
async def test_phase2_repair_recovers_malformed(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path)
    repair_events: list[str] = []
    bus.subscribe(lambda e: repair_events.append(e.kind) if e.kind == "repair_invoked" else None)

    # Round 2 malformed for claude (no BLOCKING_DISAGREEMENTS); repair then valid.
    malformed_round2 = """## Plan as I currently propose it
- foo

## Status
STATUS: NEGOTIATING
OPEN_QUESTIONS: 1
DRAFTER: claude
DOMAIN_FIT_SELF: 3
DOMAIN_FIT_OTHER: 3
"""
    valid_round2 = """## Plan as I currently propose it
- foo

## Substantive disagreements I'm holding
1. D-1: stuff

## Status
STATUS: NEGOTIATING
OPEN_QUESTIONS: 1
BLOCKING_DISAGREEMENTS: 1
FINAL_SURFACED_DISAGREEMENTS: 0
DRAFTER: claude
DOMAIN_FIT_SELF: 3
DOMAIN_FIT_OTHER: 3
"""
    valid_round2_openai = valid_round2.replace("DRAFTER: claude", "DRAFTER: openai")

    agreed = plan_turn_agreed("claude")
    claude_agent = ScriptedAgent(
        label="claude",
        model_id="claude-sonnet-4-6",
        script=[ROUND1_CONTENT, malformed_round2, valid_round2, agreed],
    )
    openai_agent = ScriptedAgent(
        label="openai",
        model_id="gpt-5.5",
        script=[ROUND1_CONTENT, valid_round2_openai, agreed],
    )

    outcome = await run_phase2(
        ctx=ctx,
        claude_agent=claude_agent,
        openai_agent=openai_agent,
        event_bus=bus,
        brief_content="brief",
        soft_cap=4,
        hard_cap=4,
    )

    assert repair_events == ["repair_invoked"]
    assert outcome.parse_failure is False
    assert outcome.converged is True
    assert outcome.rounds == 3
    # Audit trail of the malformed turn
    assert (ctx.session.phase_dir("phase2") / "round-02-claude.malformed-1.md").exists()


# ---------- hard cap ----------


@pytest.mark.asyncio
async def test_phase2_hard_cap_when_never_converges(tmp_path: Path) -> None:
    ctx, bus = _make_ctx(tmp_path)
    hardcap_events: list[str] = []
    bus.subscribe(lambda e: hardcap_events.append(e.kind) if e.kind == "hard_cap_hit" else None)

    # Both agents emit valid NEGOTIATING turns forever.
    negotiating = """## Plan as I currently propose it
- foo

## Substantive disagreements I'm holding
1. D-1: stuff

## Status
STATUS: NEGOTIATING
OPEN_QUESTIONS: 1
BLOCKING_DISAGREEMENTS: 1
FINAL_SURFACED_DISAGREEMENTS: 0
DRAFTER: claude
DOMAIN_FIT_SELF: 3
DOMAIN_FIT_OTHER: 3
"""
    claude_agent = ScriptedAgent(
        label="claude",
        model_id="claude-sonnet-4-6",
        script=[ROUND1_CONTENT] + [negotiating] * 5,
    )
    openai_agent = ScriptedAgent(
        label="openai",
        model_id="gpt-5.5",
        script=[ROUND1_CONTENT] + [negotiating.replace("claude", "openai").replace("openai_FIT", "openai_FIT")] * 5,
    )

    outcome = await run_phase2(
        ctx=ctx,
        claude_agent=claude_agent,
        openai_agent=openai_agent,
        event_bus=bus,
        brief_content="brief",
        soft_cap=2,
        hard_cap=3,
    )

    assert outcome.hard_capped is True
    assert outcome.converged is False
    assert outcome.rounds == 3
    assert hardcap_events == ["hard_cap_hit"]
