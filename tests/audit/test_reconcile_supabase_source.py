"""Spec 0049 — gather_supabase_totals reads run-cost data from the
Supabase ``runs`` table and produces the same ``LocalTotals`` shape as
``gather_local_totals`` does from disk."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pytest

from dual_research.audit.reconcile import gather_supabase_totals


# ─── Fake Supabase client (matches the postgrest builder shape) ─────────


@dataclass
class _FakeResult:
    data: list[dict]


class _FakeQueryBuilder:
    """Records the chained .select / .gte / .lt calls + returns canned data
    on .execute(). The recorded calls let tests assert the right SQL
    prefilter was applied."""

    def __init__(self, rows: list[dict], recorder: dict):
        self._rows = rows
        self._recorder = recorder

    def select(self, columns: str):
        self._recorder["select"] = columns
        return self

    def gte(self, column: str, value):
        self._recorder.setdefault("gte", []).append((column, value))
        return self

    def lt(self, column: str, value):
        self._recorder.setdefault("lt", []).append((column, value))
        return self

    def execute(self):
        return _FakeResult(self._rows)


class _FakeClient:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.recorder: dict = {}

    def table(self, name: str):
        self.recorder["table"] = name
        return _FakeQueryBuilder(self._rows, self.recorder)


def _run_row(*, run_id: str, started_at: str, calls: list[dict], pricing_version: str = "2026-05-17") -> dict:
    return {
        "id": run_id,
        "metrics": {
            "started_at": started_at,
            "pricing_version": pricing_version,
            "calls": calls,
        },
    }


# ─── Tests ──────────────────────────────────────────────────────────────


class TestGatherSupabaseTotals:
    def test_returns_same_shape_as_local_gather(self):
        """Build two runs in fake Supabase rows and assert the totals
        dict structure matches what gather_local_totals would produce
        from equivalent metrics.json files."""
        rows = [
            _run_row(
                run_id="20260516-035048-partner",
                started_at="2026-05-16T03:50:48+00:00",
                calls=[
                    {"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 2.00, "search_cost": 0.30},
                    {"agent": "claude", "model_id": "claude-sonnet-4-6", "cost_usd": 7.50, "search_cost": 0.0},
                ],
            ),
            _run_row(
                run_id="20260516-023449-other",
                started_at="2026-05-16T02:34:49+00:00",
                calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 1.00}],
            ),
        ]
        client = _FakeClient(rows)

        out = gather_supabase_totals(
            client,
            start_date=dt.date(2026, 5, 16),
            end_date=dt.date(2026, 5, 17),
        )

        assert "2026-05-16" in out
        day = out["2026-05-16"]
        # Aggregated gpt-5.5 = (2.00 - 0.30) + 1.00 = 2.70
        assert day[("openai", "gpt-5.5")]["usd"] == pytest.approx(2.70)
        # Search cost goes into the synthetic web-search bucket.
        assert day[("openai", "openai-web-search")]["usd"] == pytest.approx(0.30)
        # Claude side, single call.
        assert day[("anthropic", "claude-sonnet-4-6")]["usd"] == pytest.approx(7.50)
        # Both run_ids surface on the openai/gpt-5.5 bucket.
        assert sorted(day[("openai", "gpt-5.5")]["run_ids"]) == [
            "20260516-023449-other",
            "20260516-035048-partner",
        ]

    def test_filters_at_sql_level_on_created_at(self):
        """Verify the SQL-side prefilter uses created_at with the
        correct date bounds (end is padded by 1 day per the
        implementation contract)."""
        client = _FakeClient(rows=[])
        gather_supabase_totals(
            client,
            start_date=dt.date(2026, 5, 16),
            end_date=dt.date(2026, 5, 17),
        )
        # Spec 0245 — reconcile reads `runs_active` (soft-delete view)
        # so archived runs are excluded from daily cost roll-ups.
        assert client.recorder["table"] == "runs_active"
        assert client.recorder["select"] == "id,metrics"
        assert client.recorder["gte"] == [("created_at", "2026-05-16")]
        # End padded by 1 day → 2026-05-18 (the Python check then
        # enforces the canonical end_date=2026-05-17 exclusive window).
        assert client.recorder["lt"] == [("created_at", "2026-05-18")]

    def test_excludes_rows_whose_started_at_falls_outside_window(self):
        """A run whose created_at falls in the SQL prefilter but
        metrics.started_at falls outside the canonical window must be
        excluded from the result."""
        rows = [
            _run_row(
                run_id="just-before",
                started_at="2026-05-15T23:59:00+00:00",  # outside
                calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 999.0}],
            ),
            _run_row(
                run_id="in-range",
                started_at="2026-05-16T01:00:00+00:00",
                calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 1.0}],
            ),
        ]
        client = _FakeClient(rows)
        out = gather_supabase_totals(
            client,
            start_date=dt.date(2026, 5, 16),
            end_date=dt.date(2026, 5, 17),
        )
        # The out-of-window run's $999 must NOT appear.
        assert "2026-05-15" not in out
        assert out["2026-05-16"][("openai", "gpt-5.5")]["usd"] == pytest.approx(1.0)

    def test_returns_empty_when_no_rows(self):
        client = _FakeClient(rows=[])
        out = gather_supabase_totals(
            client,
            start_date=dt.date(2026, 5, 16),
            end_date=dt.date(2026, 5, 17),
        )
        assert out == {}

    def test_tolerates_row_with_missing_metrics(self):
        """A malformed row (no metrics key, or non-dict metrics) must be
        skipped without crashing."""
        rows = [
            {"id": "broken-1", "metrics": None},
            {"id": "broken-2"},  # no metrics field at all
            _run_row(
                run_id="good",
                started_at="2026-05-16T01:00:00+00:00",
                calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 1.0}],
            ),
        ]
        client = _FakeClient(rows)
        out = gather_supabase_totals(
            client,
            start_date=dt.date(2026, 5, 16),
            end_date=dt.date(2026, 5, 17),
        )
        assert out["2026-05-16"][("openai", "gpt-5.5")]["usd"] == pytest.approx(1.0)

    def test_collects_pricing_versions(self):
        rows = [
            _run_row(
                run_id="r1",
                started_at="2026-05-16T01:00:00+00:00",
                calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 1.0}],
                pricing_version="2026-04-01",
            ),
            _run_row(
                run_id="r2",
                started_at="2026-05-16T03:00:00+00:00",
                calls=[{"agent": "openai", "model_id": "gpt-5.5", "cost_usd": 1.0}],
                pricing_version="2026-05-17",
            ),
        ]
        client = _FakeClient(rows)
        out = gather_supabase_totals(
            client,
            start_date=dt.date(2026, 5, 16),
            end_date=dt.date(2026, 5, 17),
        )
        versions = sorted(out["2026-05-16"][("openai", "gpt-5.5")]["pricing_versions"])
        assert versions == ["2026-04-01", "2026-05-17"]
