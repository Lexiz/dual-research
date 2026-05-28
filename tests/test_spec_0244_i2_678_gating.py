"""Spec 0244 — verifier I2.6 / I2.7 / I2.8 promotion from ``reporting`` to
``gating``.

Locks in that:

- The InvariantResult for I2.6, I2.7, I2.8 carries
  ``severity="gating"`` across all six anchor-run fixtures (live
  verifier output + frozen ``expected.json`` baselines agree).
- The new ``20260528-094743-backend-language-choice`` reference fixture
  is present and complete, with all three invariants at gating pass.
- The gating contract actually gates: a synthetic fixture with a bare
  ``turn_started`` (I2.8 violation) exits the verifier CLI non-zero in
  standalone mode and names ``I2.8`` in the gating-fail list.

Companion tests in ``tests/test_verifier.py`` (verdict axis) and
``tests/_fixture_regen.py`` (regen idempotency) continue to assert
their respective axes.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from dual_research.contract.verifier import verify_run


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "anchor-runs"

ALL_FIXTURES = [
    "20260521-010637-dvs-backend-language-choice",
    "20260525-135006-backend-language-choice",
    "20260526-102321-backend-language-choice",
    "20260527-054652-backend-language-choice",
    "20260527-142625-backend-language-choice",
    "20260528-094743-backend-language-choice",
]


def _result_for(report, invariant_id: str):
    for r in report.results:
        if r.id == invariant_id:
            return r
    raise AssertionError(f"no invariant result for {invariant_id!r}")


# ─── Live verifier severity flip on every fixture ───────────────────────


@pytest.mark.parametrize("fixture_id", ALL_FIXTURES)
@pytest.mark.parametrize("invariant_id", ["I2.6", "I2.7", "I2.8"])
def test_i2_678_severity_is_gating_live(fixture_id: str, invariant_id: str):
    rd = FIXTURES / fixture_id
    report = verify_run(rd)
    r = _result_for(report, invariant_id)
    assert r.severity == "gating", (
        f"expected gating severity post-0244 for {invariant_id} on "
        f"{fixture_id}; got {r.severity!r}"
    )


# ─── Frozen baselines agree with the live verifier ──────────────────────


@pytest.mark.parametrize("fixture_id", ALL_FIXTURES)
@pytest.mark.parametrize("invariant_id", ["I2.6", "I2.7", "I2.8"])
def test_i2_678_severity_is_gating_in_expected_json(
    fixture_id: str, invariant_id: str
):
    path = FIXTURES / fixture_id / "expected.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in payload["results"]}
    assert by_id[invariant_id]["severity"] == "gating", (
        f"expected gating severity in {path} for {invariant_id}; "
        f"got {by_id[invariant_id]['severity']!r}"
    )


# ─── Per-fixture spec-§6 checklist items ────────────────────────────────


def test_094743_fixture_present_and_clean():
    """Spec 0244 §6 — the new reference fixture is present with all
    required files and shows I2.6/I2.7/I2.8 = gating pass."""
    d = FIXTURES / "20260528-094743-backend-language-choice"
    assert d.is_dir(), f"missing fixture dir {d}"
    for name in (
        "transcript.jsonl",
        "final.md",
        "metrics.json",
        "state.json",
        "expected.json",
        "fixture-notes.md",
    ):
        assert (d / name).is_file(), f"missing {name} in {d}"

    payload = json.loads((d / "expected.json").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in payload["results"]}
    for iid in ("I2.6", "I2.7", "I2.8"):
        assert by_id[iid]["severity"] == "gating"
        assert by_id[iid]["verdict"] == "pass", (
            f"expected {iid} gating pass on 094743 fixture; "
            f"got {by_id[iid]['verdict']!r}"
        )


@pytest.mark.parametrize(
    "fixture_id",
    [
        "20260521-010637-dvs-backend-language-choice",  # clean baseline
        "20260527-054652-backend-language-choice",       # post-0240 regen
        "20260527-142625-backend-language-choice",       # post-0240 regen
    ],
)
def test_named_fixtures_gating_pass_or_na(fixture_id: str):
    """Spec 0244 §2.2 table — for each of the spec's named fixtures,
    I2.6/I2.7/I2.8 should be gating-pass (or not_applicable when the
    fixture has no events for that invariant)."""
    payload = json.loads(
        (FIXTURES / fixture_id / "expected.json").read_text(encoding="utf-8")
    )
    by_id = {r["id"]: r for r in payload["results"]}
    for iid in ("I2.6", "I2.7", "I2.8"):
        assert by_id[iid]["severity"] == "gating"
        assert by_id[iid]["verdict"] in ("pass", "not_applicable"), (
            f"{fixture_id} {iid} verdict = {by_id[iid]['verdict']!r} "
            f"would now block CI"
        )


# ─── Gating actually gates: synthetic I2.8 violation ────────────────────


def test_gating_blocks_synthetic_i2_8_violation(tmp_path):
    """Spec 0244 §6 — construct a synthetic fixture with a bare
    ``turn_started`` and no terminal event; run the verifier; assert
    I2.8 is gating-fail AND the CLI exits non-zero in standalone mode
    (no ``expected.json``). This is the executable proof that the
    gating promotion actually gates.
    """
    rd = tmp_path / "synth-i2-8-violation"
    rd.mkdir()
    transcript = [
        {
            "event": "turn_started",
            "phase": "phase2",
            "round": 1,
            "agent": "claude",
            "ts": "2026-05-28T12:00:00Z",
        },
    ]
    (rd / "transcript.jsonl").write_text(
        "\n".join(json.dumps(e) for e in transcript) + "\n",
        encoding="utf-8",
    )

    report = verify_run(rd)
    i2_8 = _result_for(report, "I2.8")
    assert i2_8.severity == "gating"
    assert i2_8.verdict == "fail", (
        f"expected I2.8 gating fail on synthetic bare-turn_started "
        f"fixture; got {i2_8.verdict!r}"
    )
    assert report.has_gating_failure, (
        "synthetic I2.8 fail should set report.has_gating_failure"
    )

    from dual_research.verifier_cli import main as verifier_main

    buf = io.StringIO()
    real_stdout = sys.stdout
    sys.stdout = buf
    try:
        rc = verifier_main([str(rd)])
    finally:
        sys.stdout = real_stdout
    output = buf.getvalue()

    assert rc == 1, (
        f"expected standalone-mode CLI to exit 1 on synthetic I2.8 "
        f"fail; got rc={rc}, output:\n{output}"
    )
    assert "I2.8" in output, f"I2.8 not named in CLI output:\n{output}"
    assert "[gating]" in output, f"[gating] not in CLI output:\n{output}"
