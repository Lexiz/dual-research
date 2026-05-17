"""Spec 0048 — gather_local_totals walks runs/<id>/metrics.json files and
groups per-call cost by (UTC date, provider, model_id)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from dual_research.audit.reconcile import gather_local_totals


def _write_run(
    runs_dir: Path,
    *,
    run_id: str,
    started_at: str,
    calls: list[dict],
    pricing_version: str = "2026-05-17",
) -> None:
    """Write a synthetic runs/<id>/metrics.json."""
    d = runs_dir / run_id
    d.mkdir(parents=True)
    payload = {
        "started_at": started_at,
        "ended_at": None,
        "pricing_version": pricing_version,
        "calls": calls,
        "totals_by_agent": {},
        "total_cost_usd": sum(c.get("cost_usd", 0.0) for c in calls),
        "total_search_cost_usd": sum(c.get("search_cost", 0.0) for c in calls),
    }
    (d / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")


def test_groups_by_utc_date_provider_model(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir,
        run_id="20260516-035048-partner-vetting",
        started_at="2026-05-16T03:50:48+00:00",
        calls=[
            {"agent": "claude", "model_id": "claude-sonnet-4-6", "cost_usd": 7.50, "search_cost": 0.0},
            {"agent": "openai", "model_id": "gpt-5.5-2026-04-23", "cost_usd": 2.00, "search_cost": 0.30},
        ],
    )
    out = gather_local_totals(
        runs_dir,
        start_date=dt.date(2026, 5, 16),
        end_date=dt.date(2026, 5, 17),
    )
    assert "2026-05-16" in out
    day = out["2026-05-16"]
    # Claude — single model bucket.
    assert ("anthropic", "claude-sonnet-4-6") in day
    assert day[("anthropic", "claude-sonnet-4-6")]["usd"] == 7.50
    # OpenAI — model bucket = cost - search_cost (token-only).
    assert day[("openai", "gpt-5.5-2026-04-23")]["usd"] == 1.70
    # Search cost broken out separately.
    assert day[("openai", "openai-web-search")]["usd"] == 0.30


def test_aggregates_multiple_runs_on_same_date(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir,
        run_id="run-a",
        started_at="2026-05-16T01:00:00+00:00",
        calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 1.00}],
    )
    _write_run(
        runs_dir,
        run_id="run-b",
        started_at="2026-05-16T05:00:00+00:00",
        calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 2.00}],
    )
    out = gather_local_totals(
        runs_dir,
        start_date=dt.date(2026, 5, 16),
        end_date=dt.date(2026, 5, 17),
    )
    bucket = out["2026-05-16"][("openai", "gpt-5.5")]
    assert bucket["usd"] == 3.0
    assert sorted(bucket["run_ids"]) == ["run-a", "run-b"]


def test_excludes_runs_outside_date_range(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir,
        run_id="run-old",
        started_at="2026-05-10T00:00:00+00:00",
        calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 99.0}],
    )
    _write_run(
        runs_dir,
        run_id="run-in-range",
        started_at="2026-05-16T05:00:00+00:00",
        calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 1.0}],
    )
    out = gather_local_totals(
        runs_dir,
        start_date=dt.date(2026, 5, 15),
        end_date=dt.date(2026, 5, 17),
    )
    assert "2026-05-10" not in out
    assert "2026-05-16" in out


def test_collects_distinct_pricing_versions(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir,
        run_id="r1",
        started_at="2026-05-16T01:00:00+00:00",
        calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 1.0}],
        pricing_version="2026-04-01",
    )
    _write_run(
        runs_dir,
        run_id="r2",
        started_at="2026-05-16T05:00:00+00:00",
        calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 1.0}],
        pricing_version="2026-05-17",
    )
    out = gather_local_totals(
        runs_dir,
        start_date=dt.date(2026, 5, 16),
        end_date=dt.date(2026, 5, 17),
    )
    versions = out["2026-05-16"][("openai", "gpt-5.5")]["pricing_versions"]
    assert sorted(versions) == ["2026-04-01", "2026-05-17"]


def test_handles_gpt_alias_for_openai_agent(tmp_path: Path):
    """Older transcripts used `agent: "gpt"` (UI name); newer use `openai`."""
    runs_dir = tmp_path / "runs"
    _write_run(
        runs_dir,
        run_id="r1",
        started_at="2026-05-16T05:00:00+00:00",
        calls=[{"agent": "gpt", "model_id": "gpt-5.5", "cost_usd": 1.0}],
    )
    out = gather_local_totals(
        runs_dir,
        start_date=dt.date(2026, 5, 16),
        end_date=dt.date(2026, 5, 17),
    )
    assert ("openai", "gpt-5.5") in out["2026-05-16"]


def test_returns_empty_for_missing_runs_dir(tmp_path: Path):
    out = gather_local_totals(
        tmp_path / "nonexistent",
        start_date=dt.date(2026, 5, 16),
        end_date=dt.date(2026, 5, 17),
    )
    assert out == {}
