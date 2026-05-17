"""Spec 0048 — recompute_run stamps the rewritten metrics.json with
``PRICING_VERSION`` and surfaces the before/after transition on the report."""

from __future__ import annotations

import json
from pathlib import Path

from dual_research.agents.pricing import PRICING_VERSION
from dual_research.audit.recompute import recompute_run


def _seed_session(tmp_path: Path, *, pricing_version: str | None) -> Path:
    """Build a minimal session dir with one turn + a metrics.json that
    either carries ``pricing_version`` or omits it (pre-0048 shape)."""
    session = tmp_path / "20260516-035048-test"
    session.mkdir()
    # One turn — values picked to roundtrip cleanly through compute_full_cost.
    transcript = session / "transcript.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "ts": "2026-05-16T03:51:00+00:00",
                "event": "turn_ended",
                "agent": "claude",
                "phase": "phase0",
                "label": "phase0-claude",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "cost_usd": 0.0105,
                "duration_ms": 1000,
                "model_id": "claude-sonnet-4-6",
                "prompt_pieces": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    metrics_payload: dict = {
        "started_at": "2026-05-16T03:50:48+00:00",
        "ended_at": "2026-05-16T03:51:01+00:00",
        "calls": [],
        "totals_by_agent": {},
        "total_cost_usd": 0.0105,
        "total_search_cost_usd": 0.0,
    }
    if pricing_version is not None:
        metrics_payload["pricing_version"] = pricing_version
    (session / "metrics.json").write_text(
        json.dumps(metrics_payload), encoding="utf-8"
    )
    return session


def test_recompute_writes_current_pricing_version(tmp_path: Path):
    """The rewritten metrics.json carries the live PRICING_VERSION."""
    session = _seed_session(tmp_path, pricing_version=None)
    recompute_run(session, write=True)

    after = json.loads((session / "metrics.json").read_text())
    assert after["pricing_version"] == PRICING_VERSION


def test_recompute_report_surfaces_transition(tmp_path: Path):
    """RecomputeReport.before/after reflect the change accurately."""
    session = _seed_session(tmp_path, pricing_version=None)
    report = recompute_run(session, write=True)
    assert report.pricing_version_before == ""
    assert report.pricing_version_after == PRICING_VERSION

    # Re-running is idempotent on the version side too.
    report2 = recompute_run(session, write=True)
    assert report2.pricing_version_before == PRICING_VERSION
    assert report2.pricing_version_after == PRICING_VERSION


def test_recompute_overwrites_explicit_old_version(tmp_path: Path):
    """A metrics.json with an explicit older version is overwritten with
    the live constant — recompute reprices under today's table by
    definition, so the file should reflect that."""
    session = _seed_session(tmp_path, pricing_version="2025-12-01")
    report = recompute_run(session, write=True)
    assert report.pricing_version_before == "2025-12-01"
    assert report.pricing_version_after == PRICING_VERSION

    after = json.loads((session / "metrics.json").read_text())
    assert after["pricing_version"] == PRICING_VERSION
