"""0.46.1 regression — ``reconcile-costs`` must not exit with code 2 when
``runs/`` is missing.

The original 0.46.0 code path bailed early on `if not runs_dir.exists()`,
which broke the GitHub Actions cron: CI runners check out a clean repo
where ``runs/`` is gitignored and therefore absent. The reconcile flow
should run anyway and report honestly that local totals are empty (the
underlying ``gather_local_totals`` already returns an empty dict in
this case).
"""

from __future__ import annotations

import json
from pathlib import Path

from dual_research.cli import _run_reconcile


def test_missing_runs_dir_does_not_exit_2(tmp_path: Path, capsys, monkeypatch):
    """Invoke the CLI with --runs-dir pointing at a non-existent path; the
    command must exit 0 (within tolerance — there's nothing to compare)
    rather than 2 (the pre-fix behaviour)."""
    # No provider keys → status will be ``unverified``; that's fine, the
    # test cares about the exit code path, not the verification logic.
    monkeypatch.delenv("OPENAI_ADMIN_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_ADMIN_KEY", raising=False)

    fake_runs_dir = tmp_path / "definitely-not-here"
    assert not fake_runs_dir.exists()

    code = _run_reconcile([
        "--day", "2026-05-16",
        "--runs-dir", str(fake_runs_dir),
        "--no-write-snapshots",
        "--format", "json",
    ])
    assert code == 0, "reconcile-costs should not exit 2 when runs/ is missing"

    captured = capsys.readouterr()
    # Stderr carries the explanatory warning.
    assert "warning" in captured.err.lower()
    assert "runs dir not found" in captured.err.lower()

    # Stdout carries a valid JSON report.
    reports = json.loads(captured.out)
    assert isinstance(reports, list) and len(reports) == 1
    r = reports[0]
    assert r["date"] == "2026-05-16"
    # No keys configured + no local runs ⇒ unverified.
    assert r["verificationStatus" if "verificationStatus" in r else "verification_status"] in (
        "unverified", "awaiting_provider_data",
    )
    assert r["totalLocalUsd" if "totalLocalUsd" in r else "total_local_usd"] == 0.0
