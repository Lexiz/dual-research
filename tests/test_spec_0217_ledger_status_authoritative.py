"""Spec 0217 — STATUS.RESOLVED_THIS_TURN / WITHDRAWN_THIS_TURN as the
authoritative ledger-op closure channel for phase-2/4 reconstructors.

Six narrow unit tests (5.1–5.6) cover the protocol cells of STATUS-only
vs. legacy-section-tail vs. STATUS-wins-on-conflict for both disagreements
and questions. Test 5.7 is the headline regression replay: rounds 1–3 of
session ``20260525-135006-backend-language-choice`` checked into
``tests/fixtures/spec_0217/`` so the test is hermetic.

All six unit tests fail on ``main`` pre-0217 (the STATUS-pass paths simply
do not exist); all pass post-0217.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from dual_research.ui.disagreements import reconstruct as reconstruct_disagreements
from dual_research.ui.questions import reconstruct_questions

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "spec_0217"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _write_turn(
    session_dir: Path,
    *,
    round_n: int,
    agent: str,
    body: str,
) -> None:
    """Write a phase-2 round file."""
    phase_dir = session_dir / "phase2"
    phase_dir.mkdir(parents=True, exist_ok=True)
    (phase_dir / f"round-{round_n:02d}-{agent}.md").write_text(body, encoding="utf-8")


def _by_id(items, prefix: str = "d-") -> dict:
    return {i.id: i for i in items if i.id.startswith(prefix)}


# ─── Test 5.1 — STATUS-only closure (disagreement) ────────────────────────────


def test_5_1_status_only_closure_disagreement(tmp_path):
    """Round 1 raises D-1 via STATUS; round 2 closes it via STATUS only —
    no `## Resolved or non-blocking differences` body, no section-tail
    closure. The new STATUS-pass path must flip D-1 to resolved at round 2."""
    _write_turn(
        tmp_path,
        round_n=1,
        agent="claude",
        body=dedent(
            """\
            ## Stance
            Raising D-1.

            ## Status

            STATUS: IN_PROGRESS
            RAISED_THIS_TURN: [D-1]
            ADDRESSED_THIS_TURN: []
            RESOLVED_THIS_TURN: []
            ACKNOWLEDGED_THIS_TURN: []
            WITHDRAWN_THIS_TURN: []
            OPEN_DISAGREEMENTS: 1
            """
        ),
    )
    _write_turn(
        tmp_path,
        round_n=2,
        agent="claude",
        body=dedent(
            """\
            ## Stance
            Closing D-1.

            ## Status

            STATUS: AGREED
            RAISED_THIS_TURN: []
            ADDRESSED_THIS_TURN: []
            RESOLVED_THIS_TURN: [D-1]
            ACKNOWLEDGED_THIS_TURN: []
            WITHDRAWN_THIS_TURN: []
            OPEN_DISAGREEMENTS: 0
            """
        ),
    )
    ds = reconstruct_disagreements(tmp_path, phase=2)
    by_id = _by_id(ds)
    assert "d-01" in by_id, f"D-1 should be reconstructed; got {[d.id for d in ds]}"
    assert by_id["d-01"].status != "open", \
        f"D-1 must close via STATUS pass; got status={by_id['d-01'].status}"
    assert by_id["d-01"].closed_round == 2, \
        f"closed_round expected 2; got {by_id['d-01'].closed_round}"


# ─── Test 5.2 — Legacy section-tail fallback (disagreement) ───────────────────


def test_5_2_legacy_section_tail_fallback_disagreement(tmp_path):
    """No STATUS RESOLVED_THIS_TURN, but a `## Resolved or non-blocking
    differences` body lists D-1 as resolved. Legacy path must still fire."""
    _write_turn(
        tmp_path,
        round_n=1,
        agent="claude",
        body=dedent(
            """\
            ## Substantive disagreements I'm holding

            - D-1: Compiler performance — status: open
              - (a) D-1: "compile speed materially affects iteration"
              - (b) My position: Go's fast compile is decisive.
              - (c) GPT's position: differences are minor.
              - (d) Why I am not yet conceding: benchmarks pending.
              - (e) Materiality: agent test-fix loop.

            ## Status

            STATUS: IN_PROGRESS
            RAISED_THIS_TURN: [D-1]
            RESOLVED_THIS_TURN: []
            WITHDRAWN_THIS_TURN: []
            """
        ),
    )
    _write_turn(
        tmp_path,
        round_n=2,
        agent="claude",
        body=dedent(
            """\
            ## Resolved or non-blocking differences

            - **D-1 (compiler performance):** `resolved` — benchmarks confirmed Go's edge.

            ## Status

            STATUS: AGREED
            RAISED_THIS_TURN: []
            RESOLVED_THIS_TURN: []
            WITHDRAWN_THIS_TURN: []
            """
        ),
    )
    ds = reconstruct_disagreements(tmp_path, phase=2)
    by_id = _by_id(ds)
    assert "d-01" in by_id
    assert by_id["d-01"].status != "open", \
        f"Legacy section-tail must still close D-1; got {by_id['d-01'].status}"


# ─── Test 5.3 — STATUS-wins on conflict (disagreement) ────────────────────────


def test_5_3_status_wins_on_conflict_disagreement(tmp_path):
    """Round 2 STATUS says RESOLVED [D-1] but body still lists D-1 as open
    under `## Substantive disagreements I'm holding`. STATUS must win."""
    _write_turn(
        tmp_path,
        round_n=1,
        agent="claude",
        body=dedent(
            """\
            ## Substantive disagreements I'm holding

            - D-1: Adoption gap — status: open
              - (a) D-1: "Disputed enterprise adoption rate"
              - (b) My position: pending verification.
              - (c) GPT's position: data inconclusive.
              - (d) Why I am not yet conceding: sources differ.
              - (e) Materiality: ordering signal.

            ## Status

            STATUS: IN_PROGRESS
            RAISED_THIS_TURN: [D-1]
            RESOLVED_THIS_TURN: []
            WITHDRAWN_THIS_TURN: []
            """
        ),
    )
    _write_turn(
        tmp_path,
        round_n=2,
        agent="claude",
        body=dedent(
            """\
            ## Substantive disagreements I'm holding

            - D-1: Adoption gap — status: open
              - (a) D-1: "Disputed enterprise adoption rate"
              - (b) My position: pending verification.

            ## Status

            STATUS: AGREED
            RAISED_THIS_TURN: []
            RESOLVED_THIS_TURN: [D-1]
            WITHDRAWN_THIS_TURN: []
            """
        ),
    )
    ds = reconstruct_disagreements(tmp_path, phase=2)
    by_id = _by_id(ds)
    assert "d-01" in by_id
    assert by_id["d-01"].status != "open", \
        f"STATUS must win over open body section; got {by_id['d-01'].status}"
    assert by_id["d-01"].closed_round == 2


# ─── Test 5.4 — STATUS-only closure (question) ────────────────────────────────


def test_5_4_status_only_closure_question(tmp_path):
    """Round 1 raises Q-1 via STATUS; round 2 closes it via STATUS only
    (no answer block in `## Answers to <other>'s open questions`)."""
    _write_turn(
        tmp_path,
        round_n=1,
        agent="claude",
        body=dedent(
            """\
            ## Stance
            Asking Q-1.

            ## Status

            STATUS: IN_PROGRESS
            RAISED_THIS_TURN: [Q-1]
            RESOLVED_THIS_TURN: []
            WITHDRAWN_THIS_TURN: []
            """
        ),
    )
    _write_turn(
        tmp_path,
        round_n=2,
        agent="claude",
        body=dedent(
            """\
            ## Stance
            Closing Q-1.

            ## Status

            STATUS: AGREED
            RAISED_THIS_TURN: []
            RESOLVED_THIS_TURN: [Q-1]
            WITHDRAWN_THIS_TURN: []
            """
        ),
    )
    qs = reconstruct_questions(tmp_path, phase=2)
    by_id = _by_id(qs, prefix="q-")
    assert "q-01" in by_id, f"Q-1 should be reconstructed; got {[q.id for q in qs]}"
    assert by_id["q-01"].status == "answered"
    assert by_id["q-01"].answered_round == 2


# ─── Test 5.5 — Legacy positional-match fallback (question) ───────────────────


def test_5_5_legacy_positional_fallback_question(tmp_path):
    """No STATUS-listed Q-N but a matching positional answer block exists.
    Legacy positional path must still fire — STATUS pass is additive only."""
    _write_turn(
        tmp_path,
        round_n=1,
        agent="claude",
        body=dedent(
            """\
            ## Open questions for openai

            1. Have you verified the OTel logs signal stability?
               > quote: "logs Beta"

            ## Status

            STATUS: IN_PROGRESS
            RAISED_THIS_TURN: []
            RESOLVED_THIS_TURN: []
            WITHDRAWN_THIS_TURN: []
            """
        ),
    )
    _write_turn(
        tmp_path,
        round_n=2,
        agent="openai",
        body=dedent(
            """\
            ## Answers to claude's open questions

            1. Yes, we verified OTel logs are Beta per the upstream tracker;
               our 2.4 score reflects this.

            ## Status

            STATUS: IN_PROGRESS
            RAISED_THIS_TURN: []
            RESOLVED_THIS_TURN: []
            WITHDRAWN_THIS_TURN: []
            """
        ),
    )
    qs = reconstruct_questions(tmp_path, phase=2)
    by_id = _by_id(qs, prefix="q-")
    # Existing path produces Q-c-r1-01.
    assert "Q-c-r1-01" in [q.id for q in qs], f"got {[q.id for q in qs]}"
    target = [q for q in qs if q.id == "Q-c-r1-01"][0]
    assert target.status == "answered", \
        f"Legacy positional match must fire; got status={target.status}"


# ─── Test 5.6 — STATUS-wins (question) ─────────────────────────────────────────


def test_5_6_status_wins_question(tmp_path):
    """STATUS RESOLVED_THIS_TURN lists Q-c-r1-01 but no answer block exists
    in the answers section. STATUS must close the question."""
    _write_turn(
        tmp_path,
        round_n=1,
        agent="claude",
        body=dedent(
            """\
            ## Open questions for openai

            1. Verified OTel signals?
               > quote: "OTel signals"

            ## Status

            STATUS: IN_PROGRESS
            RAISED_THIS_TURN: []
            RESOLVED_THIS_TURN: []
            WITHDRAWN_THIS_TURN: []
            """
        ),
    )
    _write_turn(
        tmp_path,
        round_n=2,
        agent="openai",
        body=dedent(
            """\
            ## Stance
            Closing the question via STATUS only — no answer block.

            ## Status

            STATUS: AGREED
            RAISED_THIS_TURN: []
            RESOLVED_THIS_TURN: [Q-c-r1-01]
            WITHDRAWN_THIS_TURN: []
            """
        ),
    )
    qs = reconstruct_questions(tmp_path, phase=2)
    target = [q for q in qs if q.id == "Q-c-r1-01"][0]
    assert target.status == "answered", \
        f"STATUS must close question without answer block; got {target.status}"
    assert target.answered_round == 2


# ─── Test 5.7 — backend-language-choice round 3 replay ────────────────────────


def test_5_7_backend_language_choice_replay():
    """Replay the smoking-gun session through the reconstructor. The 5
    D-items (D-plan-c-01..05) and 2 Q-items (Q-plan-c-01..02) raised by
    claude across rounds 1–2 must all be recognized as closed by round 3
    — not still open, not leaking past round 3."""
    ds = reconstruct_disagreements(FIXTURE_ROOT, phase=2)
    qs = reconstruct_questions(FIXTURE_ROOT, phase=2)

    d_by_id = {d.id: d for d in ds}
    q_by_id = {q.id: q for q in qs}

    expected_d_ids = {f"d-plan-c-0{i}" for i in range(1, 6)}
    expected_q_ids = {"q-plan-c-01", "q-plan-c-02"}

    missing_d = expected_d_ids - set(d_by_id)
    missing_q = expected_q_ids - set(q_by_id)
    assert not missing_d, (
        f"All 5 claude-raised disagreements must surface; missing={missing_d} "
        f"reconstructed={list(d_by_id)}"
    )
    assert not missing_q, (
        f"Both claude-raised questions must surface; missing={missing_q} "
        f"reconstructed={list(q_by_id)}"
    )

    # All five D-items closed (not open) by the end of round 3.
    for d_id in expected_d_ids:
        d = d_by_id[d_id]
        assert d.status != "open", (
            f"{d_id} must be closed by round 3; got status={d.status}"
        )
        assert d.closed_round is not None and d.closed_round <= 3, (
            f"{d_id} must close at round ≤ 3; got closed_round={d.closed_round}"
        )

    # Both Q-items closed (answered) by the end of round 3.
    for q_id in expected_q_ids:
        q = q_by_id[q_id]
        assert q.status == "answered", (
            f"{q_id} must be answered by round 3; got status={q.status}"
        )
        assert q.answered_round is not None and q.answered_round <= 3, (
            f"{q_id} must close at round ≤ 3; got answered_round={q.answered_round}"
        )

    # Spec 0217 headline regression check: items must NOT close at round 5
    # (the post-bug behavior leaked closures into the 3-extra administrative
    # rounds; the canonical STATUS pass closes earlier).
    for d_id in expected_d_ids:
        assert d_by_id[d_id].closed_round != 5
    for q_id in expected_q_ids:
        assert q_by_id[q_id].answered_round != 5
