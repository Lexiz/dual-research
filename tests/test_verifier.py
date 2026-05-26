"""Spec 0225 — lifecycle-trace verifier tests.

Two layers:

1. **Per-invariant unit tests** — synthetic minimal transcripts + turn
   files under ``tmp_path``. For each of the 22 invariants, one positive
   case (passes) + one antipodal case (fails). I4.4 has three cases per
   spec §6 (transition-match passes, ProtocolViolation-match passes,
   neither fails).

2. **Snapshot tests against the frozen corpus** at
   ``tests/fixtures/anchor-runs/<run-id>/``. Each fixture's
   ``expected.json`` is the frozen LKG verdict-baseline; the test asserts
   ``baseline_diffs == []`` and adds targeted assertions on evidence
   contents per spec §6 (e.g. I4.4 logs the named dropped-RESOLVE items
   on ``20260526-102321``).

Regenerating ``expected.json`` after a legitimate verdict change: run
``regenerate_baseline`` in this module, inspect the diff, commit
alongside the change that caused it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.contract.verifier import (
    Evidence,
    InvariantResult,
    VerifierReport,
    baseline_regressions,
    verify_run,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "anchor-runs"


# ─── Test helpers ──────────────────────────────────────────────────────


def _write_transcript(run_dir: Path, events: list[dict]) -> None:
    lines = "\n".join(json.dumps(e) for e in events) + "\n"
    (run_dir / "transcript.jsonl").write_text(lines, encoding="utf-8")


def _write_metrics(run_dir: Path, ended_at: str | None = "2026-01-01T00:01:00Z") -> None:
    (run_dir / "metrics.json").write_text(
        json.dumps({"started_at": "2026-01-01T00:00:00Z", "ended_at": ended_at}, indent=2),
        encoding="utf-8",
    )


def _write_turn(
    run_dir: Path,
    phase: int,
    round_no: int,
    agent: str,
    *,
    raise_ids: list[str] | None = None,
    address_ids: list[str] | None = None,
    resolve_ids: list[str] | None = None,
    withdraw_ids: list[str] | None = None,
    acknowledge_ids: list[str] | None = None,
    status: str = "IN_PROGRESS",
    counters: dict[str, int] | None = None,
    array_raised: list[str] | None = None,
) -> Path:
    """Write a synthetic phase{N}/round-XX-<agent>.md turn file.

    Returns the file path. Each ID supplied generates a canonical ``### OP <ID>``
    block. ``array_raised`` overrides the RAISED_THIS_TURN array list (defaults
    to ``raise_ids``); use it to inject prose into status footer (antipodal
    I3.3 case).
    """
    phase_dir = run_dir / f"phase{phase}"
    phase_dir.mkdir(parents=True, exist_ok=True)
    raise_ids = raise_ids or []
    address_ids = address_ids or []
    resolve_ids = resolve_ids or []
    withdraw_ids = withdraw_ids or []
    acknowledge_ids = acknowledge_ids or []
    counters = counters or {}
    if array_raised is None:
        array_raised = raise_ids

    lines: list[str] = []
    lines.append("## Header\n\nbody.\n")
    if raise_ids:
        lines.append("## New items I'm raising\n")
        for iid in raise_ids:
            lines.append(f"### RAISE\nkind: question\nbody: |\n  Synthetic.\n")
    if address_ids:
        lines.append("## Addressing items raised against me\n")
        for iid in address_ids:
            lines.append(f"### ADDRESS {iid}\nreason: synthetic addressing.\n")
    if resolve_ids:
        lines.append("## Ratifying my own items\n")
        for iid in resolve_ids:
            lines.append(f"### RESOLVE {iid}\nreason: synthetic resolution.\n")
    if withdraw_ids:
        for iid in withdraw_ids:
            lines.append(f"### WITHDRAW {iid}\nreason: synthetic withdrawal.\n")
    if acknowledge_ids:
        for iid in acknowledge_ids:
            lines.append(f"### ACKNOWLEDGE {iid}\nreason: synthetic acknowledgement.\n")

    lines.append("## Status\n")
    lines.append(f"STATUS: {status}")
    lines.append(f"RAISED_THIS_TURN: [{', '.join(array_raised)}]")
    lines.append(f"ADDRESSED_THIS_TURN: [{', '.join(address_ids)}]")
    lines.append(f"RESOLVED_THIS_TURN: [{', '.join(resolve_ids)}]")
    lines.append(f"ACKNOWLEDGED_THIS_TURN: [{', '.join(acknowledge_ids)}]")
    lines.append(f"WITHDRAWN_THIS_TURN: [{', '.join(withdraw_ids)}]")
    for k, v in counters.items():
        lines.append(f"{k}: {v}")

    p = phase_dir / f"round-{round_no:02d}-{agent}.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _verdicts(report: VerifierReport) -> dict[str, str]:
    return {r.id: r.verdict for r in report.results}


def _result(report: VerifierReport, inv_id: str) -> InvariantResult:
    return next(r for r in report.results if r.id == inv_id)


# ─── Synthetic minimum-viable run helpers ───────────────────────────────


def _minimal_clean_events() -> list[dict]:
    """A minimal balanced phase 0/1/2/3/4 lifecycle with one item that
    flows open → addressed → resolved, plus a happy-path run_completed."""
    return [
        {"event": "run_started", "session_dir": "/tmp/x", "slug": "s", "model_tier": "test",
         "claude_model": "c", "openai_model": "o", "soft_cap": 6, "hard_cap": 12},
        {"event": "phase_entered", "phase": "phase0"},
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"event": "item_transitioned", "id": "Q-input-c-01", "from_state": "open",
         "to_state": "addressed", "actor": "openai", "phase": 0, "round": 2,
         "reason": "ok"},
        {"event": "item_transitioned", "id": "Q-input-c-01", "from_state": "addressed",
         "to_state": "resolved", "actor": "claude", "phase": 0, "round": 3,
         "reason": "ok"},
        {"event": "phase_converged", "phase": 0, "final_round": 3,
         "via_closeout": False, "via_ghost_cap": False, "via_hard_cap": False,
         "via_artifact_promotion": False},
        {"event": "phase_exited", "phase": "phase0", "duration_ms": 1000},
        {"event": "phase_entered", "phase": "phase1"},
        {"event": "phase_exited", "phase": "phase1", "duration_ms": 1000},
        {"event": "phase_entered", "phase": "phase2"},
        {"event": "phase_exited", "phase": "phase2", "duration_ms": 1000},
        {"event": "phase_entered", "phase": "phase3"},
        {"event": "phase_exited", "phase": "phase3", "duration_ms": 1000},
        {"event": "phase_entered", "phase": "phase4"},
        {"event": "phase_exited", "phase": "phase4", "duration_ms": 1000},
        {"ts": "2026-01-01T00:01:00Z", "event": "run_completed",
         "phase_reached": "phase4", "exit_code": 0, "total_cost_usd": 0.1, "duration_ms": 1000},
    ]


def _build_clean_run(run_dir: Path) -> None:
    """Stage a baseline-clean synthetic run with one resolved item."""
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_transcript(run_dir, _minimal_clean_events())
    _write_metrics(run_dir)
    # Turn files matching the transitions above.
    _write_turn(run_dir, phase=0, round_no=1, agent="claude", raise_ids=["Q-input-c-01"])
    _write_turn(run_dir, phase=0, round_no=2, agent="openai", address_ids=["Q-input-c-01"])
    _write_turn(
        run_dir, phase=0, round_no=3, agent="claude", resolve_ids=["Q-input-c-01"],
        status="AGREED",
    )
    _write_turn(run_dir, phase=0, round_no=3, agent="openai", status="AGREED")


# ─── Area 1 — Phases ───────────────────────────────────────────────────


def test_i1_1_balanced_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I1.1"] == "pass"


def test_i1_1_unbalanced_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    _write_transcript(rd, [
        {"event": "run_started", "session_dir": "x", "slug": "s", "model_tier": "t",
         "claude_model": "c", "openai_model": "o", "soft_cap": 6, "hard_cap": 12},
        {"event": "phase_entered", "phase": "phase0"},
        # missing phase_exited; run dies
    ])
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I1.1"] == "fail"


def test_i1_2_phases_1_and_3_silent_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I1.2"] == "pass"


def test_i1_2_phase1_item_event_fail(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    # Inject an illegal item_raised in phase 1.
    events = _minimal_clean_events()
    events.insert(8, {"event": "item_raised", "id": "Q-input-c-02", "item_kind": "question",
                      "phase": 1, "round": 1, "raiser": "claude", "body": "b",
                      "anchor_type": "none", "anchor_text": "", "evidence_required": False})
    _write_transcript(rd, events)
    res = _result(verify_run(rd), "I1.2")
    assert res.verdict == "fail"
    assert any("phase 1" in e.detail for e in res.evidence)


def test_i1_3_terminal_at_exit_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I1.3"] == "pass"


def test_i1_3_open_at_exit_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = _minimal_clean_events()
    # Drop the resolved transition so Q-input-c-01 stays addressed at phase_exited.
    events = [e for e in events if not (
        e.get("event") == "item_transitioned" and e.get("to_state") == "resolved"
    )]
    _write_transcript(rd, events)
    _write_metrics(rd)
    res = _result(verify_run(rd), "I1.3")
    assert res.verdict == "fail"


def test_i1_4_linear_order_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I1.4"] == "pass"


def test_i1_4_loop_back_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    _write_transcript(rd, [
        {"event": "phase_entered", "phase": "phase0"},
        {"event": "phase_exited", "phase": "phase0", "duration_ms": 1},
        {"event": "phase_entered", "phase": "phase2"},
        {"event": "phase_exited", "phase": "phase2", "duration_ms": 1},
        {"event": "phase_entered", "phase": "phase1"},   # loop-back
    ])
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I1.4"] == "fail"


def test_i1_5_phase4_finish_clean_pass(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = _minimal_clean_events() + [
        {"event": "turn_ended", "agent": "claude", "phase": "phase4",
         "label": "phase4-r1-claude", "input_tokens": 10, "output_tokens": 5,
         "cache_read_tokens": 0, "cache_write_tokens": 0, "cost_usd": 0.0,
         "duration_ms": 100, "finish_reason": "stop", "model_id": "m"},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd)
    assert _verdicts(verify_run(rd))["I1.5"] == "pass"


def test_i1_5_phase4_max_tokens_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = _minimal_clean_events() + [
        {"event": "turn_ended", "agent": "claude", "phase": "phase4",
         "label": "phase4-r1-claude", "input_tokens": 10, "output_tokens": 5,
         "cache_read_tokens": 0, "cache_write_tokens": 0, "cost_usd": 0.0,
         "duration_ms": 100, "finish_reason": "max_tokens", "model_id": "m"},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd)
    res = _result(verify_run(rd), "I1.5")
    assert res.verdict == "fail"


# ─── Area 2 — Negotiations ─────────────────────────────────────────────


def test_i2_1_organic_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I2.1"] == "pass"


def test_i2_1_organic_with_open_item_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = _minimal_clean_events()
    # Remove the addressing-and-resolution to leave item open at phase_converged.
    events = [e for e in events if not (
        e.get("event") == "item_transitioned"
    )]
    _write_transcript(rd, events)
    _write_metrics(rd)
    _write_turn(rd, phase=0, round_no=3, agent="claude", status="AGREED")
    _write_turn(rd, phase=0, round_no=3, agent="openai", status="AGREED")
    assert _verdicts(verify_run(rd))["I2.1"] == "fail"


def test_i2_2_round1_no_agreed_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I2.2"] == "pass"


def test_i2_2_round1_agreed_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    _write_transcript(rd, _minimal_clean_events())
    _write_metrics(rd)
    _write_turn(rd, phase=0, round_no=1, agent="claude", raise_ids=["Q-input-c-01"], status="AGREED")
    assert _verdicts(verify_run(rd))["I2.2"] == "fail"


def test_i2_3_single_via_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I2.3"] == "pass"


def test_i2_3_multi_via_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [{
        "event": "phase_converged", "phase": 0, "final_round": 4,
        "via_closeout": True, "via_ghost_cap": True,
        "via_hard_cap": False, "via_artifact_promotion": False,
    }]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I2.3"] == "fail"


def test_i2_4_no_open_other_agent_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I2.4"] == "pass"


def test_i2_4_open_other_agent_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    # openai raises an item, claude AGREED without addressing it.
    events = [
        {"event": "item_raised", "id": "Q-input-g-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "openai", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    _write_turn(rd, phase=0, round_no=2, agent="claude", status="AGREED")
    res = _result(verify_run(rd), "I2.4")
    assert res.verdict == "fail"


def test_i2_5_ledger_matches_self_report_pass(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    _write_turn(
        rd, phase=0, round_no=1, agent="claude", raise_ids=["Q-input-c-01"],
        counters={"OPEN_QUESTIONS": 1, "OPEN_DISAGREEMENTS": 0,
                  "OPEN_ISSUES": 0, "OPEN_COMMENTS": 0},
    )
    assert _verdicts(verify_run(rd))["I2.5"] == "pass"


def test_i2_5_self_report_diverges_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    # Self-report says zero open questions; ledger says 1 → divergence.
    _write_turn(
        rd, phase=0, round_no=1, agent="claude", raise_ids=["Q-input-c-01"],
        counters={"OPEN_QUESTIONS": 0, "OPEN_DISAGREEMENTS": 0,
                  "OPEN_ISSUES": 0, "OPEN_COMMENTS": 0},
    )
    res = _result(verify_run(rd), "I2.5")
    assert res.verdict == "fail"


# ─── Area 3 — Categorisation ───────────────────────────────────────────


def test_i3_1_canonical_ids_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I3.1"] == "pass"


def test_i3_1_bad_id_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-1-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I3.1"] == "fail"


def test_i3_2_ids_immutable_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I3.2"] == "pass"


def test_i3_2_id_across_phases_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 2, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I3.2"] == "fail"


def test_i3_3_canonical_arrays_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I3.3"] == "pass"


def test_i3_3_prose_in_array_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    _write_transcript(rd, [])
    _write_metrics(rd, ended_at=None)
    _write_turn(
        rd, phase=0, round_no=1, agent="openai",
        raise_ids=["Q-input-g-01"],
        array_raised=['"some prose"'],
    )
    assert _verdicts(verify_run(rd))["I3.3"] == "fail"


def test_i3_4_no_claim_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I3.4"] == "pass"


def test_i3_4_claim_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "claim",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I3.4"] == "fail"


def test_i3_5_raisable_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I3.5"] == "pass"


def test_i3_5_issue_in_phase0_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "I-input-c-01", "item_kind": "issue",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I3.5"] == "fail"


# ─── Area 4 — Resolution lifecycle ─────────────────────────────────────


def test_i4_1_permitted_edges_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I4.1"] == "pass"


def test_i4_1_forbidden_edge_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"event": "item_transitioned", "id": "Q-input-c-01", "from_state": "resolved",
         "to_state": "addressed", "actor": "claude", "phase": 0, "round": 2,
         "reason": "x"},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I4.1"] == "fail"


def test_i4_2_no_post_terminal_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I4.2"] == "pass"


def test_i4_2_post_terminal_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"event": "item_transitioned", "id": "Q-input-c-01", "from_state": "open",
         "to_state": "withdrawn", "actor": "claude", "phase": 0, "round": 2, "reason": "x"},
        {"event": "item_transitioned", "id": "Q-input-c-01", "from_state": "withdrawn",
         "to_state": "addressed", "actor": "claude", "phase": 0, "round": 3, "reason": "x"},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I4.2"] == "fail"


def test_i4_3_reason_present_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I4.3"] == "pass"


def test_i4_3_empty_reason_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"event": "item_transitioned", "id": "Q-input-c-01", "from_state": "open",
         "to_state": "addressed", "actor": "openai", "phase": 0, "round": 2, "reason": "   "},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I4.3"] == "fail"


def test_i4_4_op_with_transition_match_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I4.4"] == "pass"


def test_i4_4_op_with_protocol_violation_match_pass(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        # Claude tried to ADDRESS its own item in r2 — dropped by the orchestrator's
        # ProtocolViolation guard (spec 0216). The verifier accepts this as a valid
        # explanation for the op being in the turn file but absent from transitions.
        {"event": "protocol_violation", "phase": 0, "round": 2, "agent": "claude",
         "violation_code": "raiser_self_address", "item_id": "Q-input-c-01",
         "from_state": "open", "dropped_block": "..."},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    _write_turn(rd, phase=0, round_no=1, agent="claude", raise_ids=["Q-input-c-01"])
    _write_turn(rd, phase=0, round_no=2, agent="claude", address_ids=["Q-input-c-01"])
    assert _verdicts(verify_run(rd))["I4.4"] == "pass"


def test_i4_4_silent_drop_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    # An ADDRESS block on the turn file but NEITHER item_transitioned NOR
    # protocol_violation in the transcript — the canonical silent drop.
    events = [
        {"event": "item_raised", "id": "Q-input-g-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "openai", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    _write_turn(rd, phase=0, round_no=2, agent="claude", address_ids=["Q-input-g-01"])
    res = _result(verify_run(rd), "I4.4")
    assert res.verdict == "fail"
    assert any("phase0/round-02-claude.md" in e.location for e in res.evidence)
    assert any("Q-input-g-01" in e.detail for e in res.evidence)


def test_i4_5_no_open_to_resolved_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I4.5"] == "pass"


def test_i4_5_open_to_resolved_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"event": "item_transitioned", "id": "Q-input-c-01", "from_state": "open",
         "to_state": "resolved", "actor": "claude", "phase": 0, "round": 2, "reason": "x"},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I4.5"] == "fail"


def test_i4_6_mutual_ack_pass(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-review-g-01", "item_kind": "question",
         "phase": 4, "round": 1, "raiser": "openai", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"event": "item_transitioned", "id": "Q-review-g-01", "from_state": "open",
         "to_state": "addressed", "actor": "claude", "phase": 4, "round": 2, "reason": "x"},
        {"event": "item_transitioned", "id": "Q-review-g-01", "from_state": "addressed",
         "to_state": "acknowledged", "actor": "claude", "phase": 4, "round": 3, "reason": "x"},
        {"event": "item_transitioned", "id": "Q-review-g-01", "from_state": "acknowledged",
         "to_state": "acknowledged", "actor": "openai", "phase": 4, "round": 4, "reason": "x"},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I4.6"] == "pass"


def test_i4_6_single_agent_ack_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-review-g-01", "item_kind": "question",
         "phase": 4, "round": 1, "raiser": "openai", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"event": "item_transitioned", "id": "Q-review-g-01", "from_state": "open",
         "to_state": "acknowledged", "actor": "claude", "phase": 4, "round": 2, "reason": "x"},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I4.6"] == "fail"


def test_i4_7_via_hard_cap_pass(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"event": "item_transitioned", "id": "Q-input-c-01", "from_state": "open",
         "to_state": "capped", "actor": "orchestrator", "phase": 0, "round": 4,
         "reason": "hard cap", "via": "hard_cap"},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I4.7"] == "pass"


def test_i4_7_capped_without_via_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    events = [
        {"event": "item_raised", "id": "Q-input-c-01", "item_kind": "question",
         "phase": 0, "round": 1, "raiser": "claude", "body": "b",
         "anchor_type": "none", "anchor_text": "", "evidence_required": False},
        {"event": "item_transitioned", "id": "Q-input-c-01", "from_state": "open",
         "to_state": "capped", "actor": "claude", "phase": 0, "round": 4,
         "reason": "x", "via": None},
    ]
    _write_transcript(rd, events)
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I4.7"] == "fail"


# ─── Area 5 — Liveness ─────────────────────────────────────────────────


def test_i5_1_one_terminal_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I5.1"] == "pass"


def test_i5_1_no_terminal_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    _write_transcript(rd, [
        {"event": "run_started", "session_dir": "x", "slug": "s", "model_tier": "t",
         "claude_model": "c", "openai_model": "o", "soft_cap": 6, "hard_cap": 12},
    ])
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I5.1"] == "fail"


def test_i5_2_ended_at_set_pass(tmp_path):
    rd = tmp_path / "run"
    _build_clean_run(rd)
    assert _verdicts(verify_run(rd))["I5.2"] == "pass"


def test_i5_2_ended_at_null_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    _write_transcript(rd, [
        {"event": "run_started", "session_dir": "x", "slug": "s", "model_tier": "t",
         "claude_model": "c", "openai_model": "o", "soft_cap": 6, "hard_cap": 12},
    ])
    _write_metrics(rd, ended_at=None)
    assert _verdicts(verify_run(rd))["I5.2"] == "fail"


def test_i5_3_terminal_last_pass(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    _write_transcript(rd, [
        {"ts": "2026-01-01T00:00:00Z", "event": "run_started", "session_dir": "x",
         "slug": "s", "model_tier": "t", "claude_model": "c", "openai_model": "o",
         "soft_cap": 6, "hard_cap": 12},
        {"ts": "2026-01-01T00:00:30Z", "event": "phase_entered", "phase": "phase0"},
        {"ts": "2026-01-01T00:01:00Z", "event": "run_completed",
         "phase_reached": "phase0", "exit_code": 0, "total_cost_usd": 0.0,
         "duration_ms": 60000},
    ])
    _write_metrics(rd)
    assert _verdicts(verify_run(rd))["I5.3"] == "pass"


def test_i5_3_non_terminal_after_terminal_fail(tmp_path):
    rd = tmp_path / "run"
    rd.mkdir()
    _write_transcript(rd, [
        {"ts": "2026-01-01T00:00:00Z", "event": "run_started", "session_dir": "x",
         "slug": "s", "model_tier": "t", "claude_model": "c", "openai_model": "o",
         "soft_cap": 6, "hard_cap": 12},
        {"ts": "2026-01-01T00:01:00Z", "event": "run_completed",
         "phase_reached": "phase0", "exit_code": 0, "total_cost_usd": 0.0,
         "duration_ms": 60000},
        {"ts": "2026-01-01T00:02:00Z", "event": "phase_entered", "phase": "phase1"},
    ])
    _write_metrics(rd)
    assert _verdicts(verify_run(rd))["I5.3"] == "fail"


# ─── Snapshot tests against the frozen corpus ──────────────────────────


def _baseline_for(run_dir: Path) -> dict:
    return json.loads((run_dir / "expected.json").read_text(encoding="utf-8"))


def _verdict_diff(report: VerifierReport, baseline: dict) -> list[tuple[str, str, str]]:
    base = {item["id"]: item["verdict"] for item in baseline.get("results", [])}
    diffs: list[tuple[str, str, str]] = []
    for r in report.results:
        b = base.get(r.id)
        if b is not None and b != r.verdict:
            diffs.append((r.id, b, r.verdict))
    return diffs


def test_snapshot_clean_run_matches_baseline():
    """20260521-010637 — clean E2E run, the live regression detector. The
    verifier's verdicts must exactly match the frozen expected.json."""
    rd = FIXTURES / "20260521-010637-dvs-backend-language-choice"
    report = verify_run(rd)
    baseline = _baseline_for(rd)
    assert _verdict_diff(report, baseline) == []


def test_snapshot_dead_run_primary_matches_baseline_and_cites_dropped_resolves():
    """20260526-102321 — primary dead run. Asserts the baseline match plus
    the spec's named-item assertions: gating I5.1+I5.2 FAIL, reporting I4.4
    cites the four dropped RESOLVE ops, reporting I2.5 logs the self-report
    divergence on rounds 3–4, gating I4.5 reports pass."""
    rd = FIXTURES / "20260526-102321-backend-language-choice"
    report = verify_run(rd)
    baseline = _baseline_for(rd)
    assert _verdict_diff(report, baseline) == []

    verdicts = _verdicts(report)
    assert verdicts["I5.1"] == "fail"
    assert verdicts["I5.2"] == "fail"
    assert verdicts["I4.5"] == "pass"

    # I4.4 cites the four dropped RESOLVE ops on the named items
    # (each shows up in r2 and r4 — eight evidence pieces total, with
    # all four IDs represented).
    i4_4 = _result(report, "I4.4")
    assert i4_4.verdict == "fail"
    named = {"D-plan-c-02", "D-plan-c-04", "D-plan-c-05", "Q-plan-c-01"}
    cited = {iid for e in i4_4.evidence for iid in named if iid in e.detail}
    assert cited == named

    # I2.5 logs self-report divergences on rounds 3 + 4.
    i2_5 = _result(report, "I2.5")
    assert i2_5.verdict == "fail"
    rounds_cited = set()
    for e in i2_5.evidence:
        if " r3 " in e.detail:
            rounds_cited.add(3)
        if " r4 " in e.detail:
            rounds_cited.add(4)
    assert {3, 4}.issubset(rounds_cited)


def test_snapshot_dead_run_secondary_matches_baseline():
    """20260525-135006 — second silent-death control. Baseline match + the
    spec's named gating failures (I5.1 + I5.2)."""
    rd = FIXTURES / "20260525-135006-backend-language-choice"
    report = verify_run(rd)
    baseline = _baseline_for(rd)
    assert _verdict_diff(report, baseline) == []

    verdicts = _verdicts(report)
    assert verdicts["I5.1"] == "fail"
    assert verdicts["I5.2"] == "fail"


def test_cli_exits_zero_on_clean_baseline_match(tmp_path, monkeypatch):
    """CLI returns rc=0 when the report matches expected.json exactly."""
    from dual_research.verifier_cli import main as verifier_main
    rc = verifier_main([str(FIXTURES / "20260521-010637-dvs-backend-language-choice")])
    assert rc == 0


def test_cli_exits_zero_on_dead_run_baseline_match():
    """The dead-run fixtures have I5.1+I5.2 FAIL baked into expected.json;
    the CLI must still rc=0 because the verdicts match the baseline."""
    from dual_research.verifier_cli import main as verifier_main
    rc = verifier_main([str(FIXTURES / "20260526-102321-backend-language-choice")])
    assert rc == 0
    rc = verifier_main([str(FIXTURES / "20260525-135006-backend-language-choice")])
    assert rc == 0


def test_cli_exits_nonzero_on_baseline_regression(tmp_path):
    """A fixture whose actual verdicts diverge from a baseline triggers
    rc=1 — the regression detector."""
    from dual_research.verifier_cli import main as verifier_main
    import shutil
    src = FIXTURES / "20260521-010637-dvs-backend-language-choice"
    dst = tmp_path / "drifted"
    shutil.copytree(src, dst)
    # Forge a baseline claiming I3.1 should fail; current run reports pass → diff.
    baseline = json.loads((dst / "expected.json").read_text(encoding="utf-8"))
    for r in baseline["results"]:
        if r["id"] == "I3.1":
            r["verdict"] = "fail"
    (dst / "expected.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    rc = verifier_main([str(dst)])
    assert rc == 1


# ─── Regeneration helper (manual; not a test) ──────────────────────────


def regenerate_baseline() -> None:
    """Rewrite every fixture's expected.json from the live verifier output.

    Call from a one-off Python shell when a verdict legitimately changed
    (e.g. a contract amendment lands and one of the invariants tightens).
    Inspect the resulting diff before committing."""
    for child in sorted(FIXTURES.iterdir()):
        if not child.is_dir():
            continue
        report = verify_run(child)
        payload = {
            "spec": "0225",
            "note": "Frozen LKG baseline of the lifecycle-trace verifier. Regenerate via "
                    "tests.test_verifier.regenerate_baseline() when a verdict legitimately changes.",
            "results": [
                {"id": r.id, "severity": r.severity, "verdict": r.verdict}
                for r in report.results
            ],
        }
        (child / "expected.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
