"""Spec 0115 — final.md appendix renderer tests."""

from __future__ import annotations

from types import SimpleNamespace

from dual_research.orchestrator.finalize import (
    _is_appendix_candidate,
    _render_unresolved_items_appendix,
)


def _entry(*, id: str, kind: str, raiser: str, state: str, body: str,
           reason: str = "", via: str | None = None,
           raised_round: int = 1, terminal_round: int = 3) -> dict:
    return {
        "id": id,
        "kind": kind,
        "raiser": raiser,
        "current_state": state,
        "body": body,
        "raised_round": raised_round,
        "transitions": [
            {"from_state": "open", "to_state": "addressed",
             "actor": "openai" if raiser == "claude" else "claude",
             "round": 2, "reason": "ok", "via": None},
            {"from_state": "addressed", "to_state": state,
             "actor": "orchestrator" if via else raiser,
             "round": terminal_round, "reason": reason, "via": via},
        ],
    }


def _mk_state(*, cf0=None, cf2=None, cf4=None):
    return SimpleNamespace(
        carry_forward_phase0=cf0 or [],
        carry_forward_phase2=cf2 or [],
        carry_forward_phase4=cf4 or [],
    )


def test_appendix_empty_when_no_carry_forward():
    ctx = SimpleNamespace(state=_mk_state())
    assert _render_unresolved_items_appendix(ctx) == ""


def test_appendix_renders_phase_sections():
    ctx = SimpleNamespace(state=_mk_state(
        cf0=[
            _entry(id="Q-input-c-01", kind="question", raiser="claude",
                   state="acknowledged", body="brief is ambiguous about scope",
                   reason="no canonical answer in this run"),
        ],
        cf2=[
            _entry(id="D-plan-g-04", kind="disagreement", raiser="openai",
                   state="acknowledged", body="language choice X vs Y",
                   reason="evidence inconclusive"),
            _entry(id="Q-plan-c-07", kind="question", raiser="claude",
                   state="capped", body="benchmark numbers?",
                   reason="ghost cap fired", via="ghost_cap"),
        ],
        cf4=[
            _entry(id="I-review-c-03", kind="issue", raiser="claude",
                   state="acknowledged", body="missing citation",
                   reason="will be addressed in a follow-up"),
        ],
    ))
    out = _render_unresolved_items_appendix(ctx)
    assert "## Appendix — Unresolved items" in out
    assert "Briefing limitations (phase 0)" in out
    assert "Surfaced disagreements (negotiate-plan phase)" in out
    assert "Unanswered research questions (negotiate-plan phase)" in out
    assert "Known issues in this draft (review-draft phase)" in out
    assert "[Q-input-c-01]" in out
    assert "[D-plan-g-04]" in out
    assert "[Q-plan-c-07] capped (ghost_cap)" in out
    assert "[I-review-c-03]" in out


def test_acknowledged_items_always_surface():
    e = _entry(id="X", kind="question", raiser="claude",
               state="acknowledged", body="x", reason="r")
    assert _is_appendix_candidate(e) is True


def test_capped_items_always_surface():
    e = _entry(id="X", kind="question", raiser="claude",
               state="capped", body="x", reason="r", via="hard_cap")
    assert _is_appendix_candidate(e) is True


def test_withdrawn_with_trivial_reason_is_hidden():
    e = _entry(id="X", kind="question", raiser="claude",
               state="withdrawn", body="x", reason="duplicate of Y")
    assert _is_appendix_candidate(e) is False


def test_withdrawn_with_long_reason_surfaces():
    long_reason = "we discussed this at length and reached a substantive understanding"
    e = _entry(id="X", kind="question", raiser="claude",
               state="withdrawn", body="x", reason=long_reason)
    assert _is_appendix_candidate(e) is True


def test_resolved_items_do_not_surface():
    e = _entry(id="X", kind="question", raiser="claude",
               state="resolved", body="x", reason="convinced")
    assert _is_appendix_candidate(e) is False
