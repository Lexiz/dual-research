"""Spec 0228 §2.2 — verifier I4.4 promotion from ``reporting`` to
``gating``.

Locks in that:

- The InvariantResult for I4.4 carries ``severity="gating"`` (not
  ``reporting``) across pass / fail / not_applicable verdicts.
- The frozen baseline files at ``tests/fixtures/anchor-runs/*/expected.json``
  agree (all three carry ``severity: "gating"`` for I4.4 after the
  regenerate-baseline pass that landed in this spec).
- The CLI standalone-mode gate (no ``expected.json``) now treats I4.4
  failures as a non-zero exit signal — the dead-fixture, when stripped
  of its baseline, exits ``1`` with I4.4 named in the gating list.

Companion test in spec 0225's ``tests/test_verifier.py`` continues to
assert the verdict-axis behaviour; this file owns the severity-axis
assertions specific to spec 0228.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from dual_research.contract.verifier import verify_run


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "anchor-runs"


def _result_for(report, invariant_id: str):
    for r in report.results:
        if r.id == invariant_id:
            return r
    raise AssertionError(f"no invariant result for {invariant_id!r}")


# ─── Severity flip on the live verifier output ──────────────────────────


@pytest.mark.parametrize(
    "fixture_id",
    [
        "20260521-010637-dvs-backend-language-choice",  # clean reference
        "20260525-135006-backend-language-choice",       # dead secondary
        "20260526-102321-backend-language-choice",       # dead primary
    ],
)
def test_i4_4_severity_is_gating_on_each_anchor_fixture(fixture_id: str):
    """The verifier reports I4.4 with severity 'gating' on every
    anchor-run fixture (post-spec-0228 promotion)."""
    rd = FIXTURES / fixture_id
    report = verify_run(rd)
    i4_4 = _result_for(report, "I4.4")
    assert i4_4.severity == "gating", (
        f"expected gating severity post-0228 on {fixture_id}; got {i4_4.severity!r}"
    )


# ─── Frozen baselines agree with the live verifier ──────────────────────


@pytest.mark.parametrize(
    "fixture_id",
    [
        "20260521-010637-dvs-backend-language-choice",
        "20260525-135006-backend-language-choice",
        "20260526-102321-backend-language-choice",
    ],
)
def test_i4_4_severity_is_gating_in_expected_json(fixture_id: str):
    """The frozen ``expected.json`` baselines record severity='gating'
    for I4.4 — the regenerated baselines that ship in this PR."""
    path = FIXTURES / fixture_id / "expected.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in payload["results"]}
    assert by_id["I4.4"]["severity"] == "gating", (
        f"expected gating severity in {path}; got {by_id['I4.4']['severity']!r}"
    )


# ─── CLI standalone-mode gate fires on I4.4 fail ────────────────────────


def test_cli_standalone_dead_fixture_exits_nonzero_naming_i4_4(tmp_path):
    """Spec 0228 §6 — the dead fixture, run without its ``expected.json``
    baseline (standalone gate mode), exits non-zero and the gating
    failure list names I4.4 citing the four dropped RESOLVE items
    explicitly.

    With a baseline present, the CLI uses baseline-match semantics and
    returns 0 (the regenerated baseline records ``I4.4: fail`` and the
    current run matches it). This test exercises the standalone path
    where any gating-fail is a hard gate — the surface spec 0228 intends
    by "the gating failure list now includes I4.4".
    """
    from dual_research.verifier_cli import main as verifier_main

    src = FIXTURES / "20260526-102321-backend-language-choice"
    dst = tmp_path / "no-baseline"
    shutil.copytree(src, dst)
    (dst / "expected.json").unlink()  # force standalone gating mode

    captured: list[str] = []
    import sys
    from io import StringIO
    buf = StringIO()
    real_stdout = sys.stdout
    sys.stdout = buf
    try:
        rc = verifier_main([str(dst)])
    finally:
        sys.stdout = real_stdout
    captured.append(buf.getvalue())

    output = "\n".join(captured)
    assert rc == 1, f"expected non-zero rc on standalone dead fixture; got {rc}"
    # I4.4 appears as a gating-severity row marked failing.
    assert "I4.4" in output
    assert "[gating]" in output
    # Four named items cited in the I4.4 evidence list.
    for item_id in ("D-plan-c-02", "D-plan-c-04", "D-plan-c-05", "Q-plan-c-01"):
        assert item_id in output, f"missing {item_id} in CLI output"


def test_cli_with_baseline_dead_fixture_still_exits_zero():
    """The baseline-included dead fixture continues to exit 0 because
    actual matches baseline (verdict-axis only — severity flip alone
    does not produce a regression). Regression test for the spec 0225
    CLI invariant: ``test_cli_exits_zero_on_dead_run_baseline_match``."""
    from dual_research.verifier_cli import main as verifier_main

    rc = verifier_main([str(FIXTURES / "20260526-102321-backend-language-choice")])
    assert rc == 0
