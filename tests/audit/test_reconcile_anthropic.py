"""Spec 0048 — Anthropic cost-report fetcher tested against a canonical
docs-shape fixture (built blind; revalidate when real admin key arrives)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from dual_research.audit.reconcile import (
    ReconcileError,
    fetch_anthropic_daily_costs,
)


FIXTURE = Path(__file__).parent / "fixtures" / "anthropic_cost_report_sample.json"


def _mock_client(body: dict, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)
    return httpx.Client(transport=httpx.MockTransport(handler))


class TestFetchAnthropicDailyCosts:
    def test_parses_canonical_fixture(self):
        fixture = json.loads(FIXTURE.read_text())
        client = _mock_client(fixture)
        out = fetch_anthropic_daily_costs(
            client,
            start_date=dt.date(2026, 5, 15),
            end_date=dt.date(2026, 5, 17),
            api_key="sk-ant-admin-test",
            workspace_id="wrkspc_test",
        )

        assert set(out.keys()) == {"2026-05-15", "2026-05-16"}

        # 2026-05-15: claude-sonnet-4-6 = 1.2345 + 3.5000; claude-haiku-4-5 = 0.15.
        day = out["2026-05-15"]
        assert day["claude-sonnet-4-6"] == pytest.approx(1.2345 + 3.5000, abs=1e-3)
        assert day["claude-haiku-4-5"] == pytest.approx(0.15, abs=1e-3)

        # 2026-05-16: claude-sonnet-4-6 only.
        assert out["2026-05-16"]["claude-sonnet-4-6"] == pytest.approx(5.5, abs=1e-3)

    def test_401_raises_reconcile_error(self):
        client = _mock_client({"error": {"message": "invalid x-api-key"}}, status=401)
        with pytest.raises(ReconcileError) as exc:
            fetch_anthropic_daily_costs(
                client,
                start_date=dt.date(2026, 5, 15),
                end_date=dt.date(2026, 5, 16),
                api_key="bad-key",
            )
        assert "401" in str(exc.value)
        assert "anthropic" in str(exc.value).lower()

    def test_falls_back_to_description_for_model_id(self):
        """When the API doesn't include a `model` field, we pluck the model
        id out of the `description` string."""
        body = {
            "data": [
                {
                    "starting_at": "2026-05-15T00:00:00Z",
                    "results": [
                        {
                            "amount": {"value": "1.00"},
                            "description": "claude-sonnet-4-6 some other text",
                        }
                    ],
                }
            ],
            "has_more": False,
        }
        client = _mock_client(body)
        out = fetch_anthropic_daily_costs(
            client,
            start_date=dt.date(2026, 5, 15),
            end_date=dt.date(2026, 5, 16),
            api_key="sk-ant-admin-test",
        )
        assert out["2026-05-15"]["claude-sonnet-4-6"] == pytest.approx(1.0)

    def test_unknown_model_falls_back_to_anthropic_other(self):
        body = {
            "data": [
                {
                    "starting_at": "2026-05-15T00:00:00Z",
                    "results": [
                        {
                            "amount": {"value": "0.25"},
                            "description": "totally unknown product line",
                        }
                    ],
                }
            ],
            "has_more": False,
        }
        client = _mock_client(body)
        out = fetch_anthropic_daily_costs(
            client,
            start_date=dt.date(2026, 5, 15),
            end_date=dt.date(2026, 5, 16),
            api_key="sk-ant-admin-test",
        )
        assert out["2026-05-15"]["anthropic-other"] == pytest.approx(0.25)
