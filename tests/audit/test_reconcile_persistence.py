"""Spec 0048 — reconcile/<date>.json round-trip."""

from __future__ import annotations

from pathlib import Path

from dual_research.audit.reconcile import (
    ProviderDelta,
    ReconcileReport,
    read_reconcile_json,
    reconcile_dir,
    write_reconcile_json,
)


def _sample_report() -> ReconcileReport:
    return ReconcileReport(
        date="2026-05-16",
        checked_at="2026-05-17T12:00:00Z",
        tolerance_pct=1.0,
        providers_checked=["openai"],
        providers_skipped={"anthropic": "ANTHROPIC_ADMIN_KEY not set"},
        runs_on_date=["20260516-035048-partner-vetting"],
        pricing_versions_seen=["2026-05-17"],
        per_model_deltas=[
            ProviderDelta(
                provider="openai",
                model_id="gpt-5.5-2026-04-23",
                local_usd=2.48,
                provider_usd=13.73,
                delta_usd=-11.25,
                delta_pct=81.93,
                flagged=True,
            ),
        ],
        total_local_usd=9.86,
        total_provider_usd=13.73,
        total_delta_usd=-3.87,
        verification_status="partial",
    )


def test_write_creates_reconcile_dir(tmp_path: Path):
    report = _sample_report()
    written = write_reconcile_json(report, project_root=tmp_path)
    assert written.exists()
    assert written.parent == reconcile_dir(tmp_path)
    assert written.name == "2026-05-16.json"


def test_round_trip_preserves_all_fields(tmp_path: Path):
    report = _sample_report()
    write_reconcile_json(report, project_root=tmp_path)
    loaded = read_reconcile_json(tmp_path, "2026-05-16")
    assert loaded is not None
    assert loaded.date == report.date
    assert loaded.checked_at == report.checked_at
    assert loaded.tolerance_pct == report.tolerance_pct
    assert loaded.providers_checked == report.providers_checked
    assert loaded.providers_skipped == report.providers_skipped
    assert loaded.runs_on_date == report.runs_on_date
    assert loaded.pricing_versions_seen == report.pricing_versions_seen
    assert loaded.total_local_usd == report.total_local_usd
    assert loaded.total_provider_usd == report.total_provider_usd
    assert loaded.total_delta_usd == report.total_delta_usd
    assert loaded.verification_status == report.verification_status
    assert len(loaded.per_model_deltas) == 1
    d = loaded.per_model_deltas[0]
    assert d.provider == "openai"
    assert d.model_id == "gpt-5.5-2026-04-23"
    assert d.flagged is True


def test_read_missing_date_returns_none(tmp_path: Path):
    assert read_reconcile_json(tmp_path, "2099-01-01") is None


def test_overwrite_on_re_run(tmp_path: Path):
    """Re-running reconciliation for the same date overwrites the file."""
    report1 = _sample_report()
    write_reconcile_json(report1, project_root=tmp_path)
    report2 = _sample_report()
    report2.total_delta_usd = -5.0
    report2.verification_status = "drift"
    write_reconcile_json(report2, project_root=tmp_path)
    loaded = read_reconcile_json(tmp_path, "2026-05-16")
    assert loaded.total_delta_usd == -5.0
    assert loaded.verification_status == "drift"
