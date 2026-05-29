"""Spec 0255 — closeout-urge gate decoupled from effective status.

Regression for the captured live failure
``runs/20260529-091956-backend-language-choice`` (exit 51, $7.19, no
``final.md``): two agents reached full self-reported agreement (both
``STATUS: AGREED``) yet phase 2 ground to its hard cap and dead-ended,
because a spec-0229 addressee-obligation demotion of openai's AGREED was
fed into BOTH end-of-round gates — convergence AND closeout-urge. With
the closeout-urge gate disarmed, ``CloseoutUrged`` never fired (0 in the
transcript), the closeout → ghost-cap escape valve never armed, and the
loop ran to ``caps.hard``.

Per the spec-0238 live-failure doctrine this test drives the REAL
``run_dr_phase2`` entry point (not a helper in isolation) with scripted
stub agents reproducing the captured shape: claude raises 5 items in
round 1; openai ``ADDRESS``es none; both emit empty ``STATUS: AGREED``
for the remaining rounds so openai is demoted every round. Post-fix the
phase converges ``via_ghost_cap`` (exit 0) instead of dead-ending at the
hard cap. The falsifiability assertion (``hard_capped is False``,
``CloseoutUrged`` count ≥ 1) is exactly what flips red on the pre-fix
code, where the run converges with ``hard_capped=True`` at ``rounds=8``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.agents.base import AgentResult, TokenUsage
from dual_research.events import (
    CloseoutUrged,
    EventBus,
    ItemTransitioned,
    PhaseConverged,
)
from dual_research.orchestrator.dr_run import run_dr_phase2
from dual_research.persistence import (
    Metrics,
    SessionContext,
    SessionDirectory,
    SessionState,
)


# ─── Turn-text builders (parser-valid, mirror tests/orchestrator) ──────

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


def _raise_block(*, kind: str, body: str) -> str:
    return (
        f"### RAISE\n"
        f"kind: {kind}\n"
        f"body: |\n  {body}\n"
        f"anchor_type: none\n"
        f"anchor_text:\n"
        f"evidence_required: false\n"
    )


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


_PHASE1_DRAFT = (
    "## 1. Summary\nFindings overview.\n\n"
    "## 2. My thesis\nMy current judgment.\n\n"
    "## 3. Detailed findings\nThe substance with [V] tags inline.\n\n"
    "## 4. Sources\n[1] https://example.com\n"
)

_AGREED_PLAN = "### AGREED_PLAN\nshared plan body — drafter: claude\n"


class ScriptedAgent:
    """Round-scripted async stub agent. Returns the canned turn text for
    its (round, label) pair; ``run_dr_phase2`` calls each agent exactly
    once per round, so an internal call counter tracks the round."""

    def __init__(self, *, label: str, model_id: str, scripts: dict[int, str]):
        self.label = label
        self.model_id = model_id
        self.provider = "anthropic" if label == "claude" else "openai"
        self._scripts = scripts
        self._round = 0

    async def run(
        self,
        prompt,
        *,
        max_output_tokens=8192,
        stream_to=None,
        stream_prefix="",
        audit_context=None,
    ):
        self._round += 1
        text = self._scripts[self._round]
        return AgentResult(
            text=text,
            usage=TokenUsage(input_tokens=10, output_tokens=20),
            cost_usd=0.0001,
            duration_ms=42,
            model_id=self.model_id,
            provider=self.provider,
            label=self.label,
            extras={"stop_reason": "end_turn"},
        )


def _make_ctx(tmp_path: Path) -> tuple[SessionContext, EventBus]:
    sess = SessionDirectory(root=tmp_path / "run").ensure()
    state = SessionState()
    state.agreed_interpretation = "(agreed interpretation body)"
    # Seed the phase-1 drafts run_dr_phase2 reads at entry.
    p1 = sess.phase_dir("phase1")
    (p1 / "draft-claude.md").write_text(_PHASE1_DRAFT, encoding="utf-8")
    (p1 / "draft-openai.md").write_text(_PHASE1_DRAFT, encoding="utf-8")
    transcript = sess.open_transcript()
    metrics = Metrics()
    ctx = SessionContext(
        session=sess, state=state, transcript=transcript, metrics=metrics,
    )
    return ctx, EventBus()


def _captured_shape_scripts() -> tuple[dict[int, str], dict[int, str]]:
    """Reproduce the captured deadlock shape over rounds 1–8 (the hard
    cap). claude raises 5 items in round 1 at IN_PROGRESS; openai never
    ADDRESSes them; both emit empty AGREED for every later round, so
    openai is demoted every round. Scripts cover all 8 rounds because
    the PRE-fix code grinds to the hard cap — the post-fix code exits at
    round 4 via ghost-cap and never reads the later entries."""
    claude: dict[int, str] = {}
    openai: dict[int, str] = {}

    # Round 1 — claude raises 5 disagreements (D-plan-c-01..05); openai idle.
    claude[1] = _wrap_turn(
        status="IN_PROGRESS",
        body_sections={
            "New items I'm raising": "\n".join(
                _raise_block(kind="disagreement", body=f"i hold position {n}.")
                for n in range(1, 6)
            ),
        },
    )
    openai[1] = _wrap_turn(status="IN_PROGRESS", body_sections={})

    # Rounds 2–8 — both emit empty AGREED with a byte-identical artifact;
    # openai never ADDRESSes claude's 5 items, so it is demoted each round.
    for r in range(2, 9):
        claude[r] = _wrap_turn(status="AGREED", body_sections={}, artifact=_AGREED_PLAN)
        openai[r] = _wrap_turn(status="AGREED", body_sections={}, artifact=_AGREED_PLAN)

    return claude, openai


@pytest.mark.asyncio
async def test_phase2_addressee_demotion_converges_via_ghost_cap(tmp_path: Path) -> None:
    """Post-fix: the captured deadlock shape converges via ghost-cap
    (exit 0) instead of dead-ending at the hard cap (exit 51).

    Pre-fix this fails: ``should_urge_closeout`` reads the demoted
    effective status (openai IN_PROGRESS) so it returns False, no
    ``CloseoutUrged`` ever fires, and the loop converges with
    ``via_hard_cap=True`` at ``rounds=8``.
    """
    ctx, bus = _make_ctx(tmp_path)
    events: list = []
    bus.subscribe(events.append)

    claude_scripts, openai_scripts = _captured_shape_scripts()

    outcome = await run_dr_phase2(
        ctx=ctx,
        claude_agent=ScriptedAgent(
            label="claude", model_id="claude-sonnet-4-6", scripts=claude_scripts,
        ),
        openai_agent=ScriptedAgent(
            label="openai", model_id="gpt-5.5", scripts=openai_scripts,
        ),
        event_bus=bus,
        brief_content="the brief",
        soft_cap=4,
        hard_cap=8,
    )

    # ── The phase converged, and NOT via the hard cap (the captured deadlock). ──
    assert outcome.converged is True
    assert outcome.hard_capped is False, (
        "phase dead-ended at the hard cap — the pre-fix deadlock; "
        f"converged at rounds={outcome.rounds}"
    )
    assert outcome.rounds < 8, (
        f"expected an early ghost-cap exit, ran to rounds={outcome.rounds}"
    )

    # ── The broken signal now fires: ≥1 CloseoutUrged (0 in the captured run). ──
    closeout_events = [e for e in events if isinstance(e, CloseoutUrged)]
    assert len(closeout_events) >= 1, "expected CloseoutUrged to fire post-fix"

    # ── The single PhaseConverged event is via_ghost_cap, not via_hard_cap. ──
    converged_events = [e for e in events if isinstance(e, PhaseConverged)]
    assert len(converged_events) == 1, f"expected exactly one PhaseConverged; got {converged_events!r}"
    pc = converged_events[0]
    assert pc.via_ghost_cap is True
    assert pc.via_hard_cap is False

    # ── claude's 5 items end capped via ghost_cap. ──
    capped = [
        e for e in events
        if isinstance(e, ItemTransitioned) and e.to_state == "capped"
    ]
    assert len(capped) == 5, f"expected 5 ghost-capped items; got {capped!r}"
    assert all(e.via == "ghost_cap" for e in capped)
    assert all(e.actor == "orchestrator" for e in capped)
