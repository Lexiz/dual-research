"""Spec 0048 — Metrics.pricing_version round-trip + load tolerance."""

from __future__ import annotations

import json
from pathlib import Path

from dual_research.agents.pricing import PRICING_VERSION
from dual_research.persistence.metrics import CallRecord, Metrics


def test_to_json_includes_pricing_version_constant():
    """A fresh Metrics serializes with the live PRICING_VERSION."""
    m = Metrics()
    payload = json.loads(m.to_json())
    assert payload["pricing_version"] == PRICING_VERSION


def test_load_preserves_pricing_version(tmp_path: Path):
    """Round-trip: save → load preserves whatever pricing_version was on disk."""
    m = Metrics(pricing_version="2025-12-01")
    m.calls.append(
        CallRecord(
            label="phase0-claude",
            agent="claude",
            model_id="claude-sonnet-4-6",
            input_tokens=10,
            output_tokens=20,
            cache_read_tokens=0,
            cache_write_tokens=0,
            cost_usd=0.001,
            duration_ms=100,
        )
    )
    path = tmp_path / "metrics.json"
    m.save(path)

    # The saved file should carry the explicit value, not the live constant.
    on_disk = json.loads(path.read_text())
    assert on_disk["pricing_version"] == "2025-12-01"

    # Round-trip through Metrics.load.
    loaded = Metrics.load(path)
    assert loaded.pricing_version == "2025-12-01"


def test_load_tolerates_missing_pricing_version(tmp_path: Path):
    """Pre-0048 metrics.json files (no pricing_version field) load with ''."""
    path = tmp_path / "metrics.json"
    payload = {
        "started_at": "2026-05-01T00:00:00+00:00",
        "ended_at": "2026-05-01T01:00:00+00:00",
        "calls": [],
        "totals_by_agent": {},
        "total_cost_usd": 0.0,
        "total_search_cost_usd": 0.0,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = Metrics.load(path)
    assert loaded.pricing_version == ""


def test_to_json_falls_back_to_constant_when_field_empty():
    """An in-memory Metrics with empty pricing_version writes the live constant.

    This is the resume-and-save path: load an old file (pricing_version="");
    save it back; the new file should carry the live PRICING_VERSION so the
    on-disk record always reflects the current table.
    """
    m = Metrics(pricing_version="")
    payload = json.loads(m.to_json())
    assert payload["pricing_version"] == PRICING_VERSION
