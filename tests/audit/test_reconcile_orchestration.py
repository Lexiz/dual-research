"""Spec 0048 — reconcile_day / reconcile_range end-to-end with mocked HTTP."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from dual_research.audit.reconcile import (
    ProviderConfig,
    format_json,
    format_text,
    reconcile_day,
    reconcile_range,
)


def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _write_run(runs_dir: Path, run_id: str, started_at: str, calls: list[dict]) -> None:
    d = runs_dir / run_id
    d.mkdir(parents=True)
    payload = {
        "started_at": started_at,
        "ended_at": None,
        "pricing_version": "2026-05-17",
        "calls": calls,
        "totals_by_agent": {},
        "total_cost_usd": sum(c.get("cost_usd", 0.0) for c in calls),
        "total_search_cost_usd": 0.0,
    }
    (d / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")


def test_reconcile_day_with_only_openai_key(tmp_path: Path):
    """OpenAI key present, Anthropic missing → partial status, OpenAI verified."""
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir,
        "20260516-test",
        "2026-05-16T03:50:48+00:00",
        [
            {"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 5.00, "search_cost": 0.0},
        ],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert "openai.com" in str(request.url)
        return httpx.Response(200, json={
            "data": [{
                "start_time_iso": "2026-05-16T00:00:00",
                "results": [
                    {"amount": {"value": "5.00"}, "line_item": "gpt-5.5, input"},
                ],
            }],
            "has_more": False,
        })

    client = _mock_client(handler)
    config = ProviderConfig(openai_key="sk-admin-test")

    report = reconcile_day(
        dt.date(2026, 5, 16),
        client=client, runs_dir=runs_dir, config=config, tolerance_pct=1.0,
    )

    assert report.verification_status == "partial"
    assert report.providers_checked == ["openai"]
    assert "anthropic" in report.providers_skipped
    assert report.providers_skipped["anthropic"] == "ANTHROPIC_ADMIN_KEY not set"
    assert report.total_local_usd == 5.0
    assert report.total_provider_usd == 5.0


def test_reconcile_day_with_no_keys(tmp_path: Path):
    """No keys at all → unverified; local-only total still reported."""
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir,
        "r-1",
        "2026-05-16T03:50:48+00:00",
        [{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 7.50}],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP calls should be made when keys are missing")

    client = _mock_client(handler)
    config = ProviderConfig()  # no keys

    report = reconcile_day(
        dt.date(2026, 5, 16),
        client=client, runs_dir=runs_dir, config=config, tolerance_pct=1.0,
    )

    assert report.verification_status == "unverified"
    assert report.providers_checked == []
    assert report.total_local_usd == 7.50
    assert report.total_provider_usd == 0.0


def test_reconcile_day_with_provider_error_marks_skipped(tmp_path: Path):
    """Provider returns 401 → that provider becomes skipped, the day's
    report still ships."""
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir,
        "r-1",
        "2026-05-16T03:50:48+00:00",
        [{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 5.00}],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid x-api-key"}})

    client = _mock_client(handler)
    config = ProviderConfig(openai_key="sk-admin-bad")

    report = reconcile_day(
        dt.date(2026, 5, 16),
        client=client, runs_dir=runs_dir, config=config, tolerance_pct=1.0,
    )

    assert "openai" in report.providers_skipped
    assert "401" in report.providers_skipped["openai"]


def test_reconcile_range_walks_each_day(tmp_path: Path):
    """A 3-day range produces 3 reports, one per UTC date."""
    runs_dir = tmp_path / "runs"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [], "has_more": False})

    client = _mock_client(handler)
    reports = reconcile_range(
        dt.date(2026, 5, 14), dt.date(2026, 5, 16),
        client=client, runs_dir=runs_dir, config=ProviderConfig(openai_key="k"),
        tolerance_pct=1.0,
    )
    assert [r.date for r in reports] == ["2026-05-14", "2026-05-15", "2026-05-16"]


class TestFormatters:
    def _report(self, status: str, deltas: list[dict]) -> "ReconcileReport":
        from dual_research.audit.reconcile import ProviderDelta, ReconcileReport
        return ReconcileReport(
            date="2026-05-16",
            checked_at="2026-05-17T12:00:00Z",
            tolerance_pct=1.0,
            providers_checked=["openai"],
            providers_skipped={},
            runs_on_date=["r-1"],
            pricing_versions_seen=["2026-05-17"],
            per_model_deltas=[ProviderDelta(**d) for d in deltas],
            total_local_usd=sum(d["local_usd"] for d in deltas),
            total_provider_usd=sum(d["provider_usd"] for d in deltas),
            total_delta_usd=sum(d["delta_usd"] for d in deltas),
            verification_status=status,
        )

    def test_text_includes_status_and_totals(self):
        r = self._report("verified", [
            {"provider": "openai", "model_id": "gpt-5.5",
             "local_usd": 5.0, "provider_usd": 5.0, "delta_usd": 0.0,
             "delta_pct": 0.0, "flagged": False},
        ])
        out = format_text([r])
        assert "2026-05-16" in out
        assert "verified" in out
        assert "gpt-5.5" in out
        assert "TOTAL" in out

    def test_text_flags_drift_rows_with_bang(self):
        r = self._report("drift", [
            {"provider": "openai", "model_id": "gpt-5.5",
             "local_usd": 1.0, "provider_usd": 10.0, "delta_usd": -9.0,
             "delta_pct": 90.0, "flagged": True},
        ])
        out = format_text([r])
        # Flagged row carries a leading "!"
        lines = [ln for ln in out.splitlines() if "gpt-5.5" in ln]
        assert lines
        assert any(ln.lstrip().startswith("!") for ln in lines)

    def test_json_round_trippable(self):
        r = self._report("verified", [
            {"provider": "openai", "model_id": "gpt-5.5",
             "local_usd": 5.0, "provider_usd": 5.0, "delta_usd": 0.0,
             "delta_pct": 0.0, "flagged": False},
        ])
        out = format_json([r])
        decoded = json.loads(out)
        assert decoded[0]["date"] == "2026-05-16"
        assert decoded[0]["verification_status"] == "verified"
