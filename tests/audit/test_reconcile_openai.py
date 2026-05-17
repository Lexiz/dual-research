"""Spec 0048 — OpenAI cost-report fetcher tested against a real captured
response shape (2026-05-17 probe of /v1/organization/costs)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from dual_research.audit.reconcile import (
    ReconcileError,
    _parse_openai_line_item,
    fetch_openai_daily_costs,
)


FIXTURE = Path(__file__).parent / "fixtures" / "openai_cost_report_2026_05_15_to_17.json"


def _mock_client(response_body: dict, status: int = 200) -> httpx.Client:
    """Return an httpx.Client that returns ``response_body`` for any request."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=response_body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _multi_page_client(pages: list[dict]) -> httpx.Client:
    """Return an httpx.Client that walks through ``pages`` in order."""
    state = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        i = state["i"]
        state["i"] = min(i + 1, len(pages) - 1)
        return httpx.Response(200, json=pages[i])

    return httpx.Client(transport=httpx.MockTransport(handler))


class TestLineItemParser:
    @pytest.mark.parametrize(
        "line_item,expected",
        [
            ("gpt-5.5-2026-04-23, input", ("gpt-5.5-2026-04-23", "input")),
            ("gpt-5.5-2026-04-23, output", ("gpt-5.5-2026-04-23", "output")),
            ("gpt-5.5-2026-04-23, cached input", ("gpt-5.5-2026-04-23", "cached input")),
            ("gpt-4.1-2025-04-14, input", ("gpt-4.1-2025-04-14", "input")),
            ("gpt-5-mini-2025-08-07, output", ("gpt-5-mini-2025-08-07", "output")),
        ],
    )
    def test_parses_model_pieces(self, line_item: str, expected: tuple[str, str]):
        assert _parse_openai_line_item(line_item) == expected

    def test_returns_none_for_web_search(self):
        assert _parse_openai_line_item("web search tool calls") == (None, None)

    def test_returns_none_for_unknown_shape(self):
        assert _parse_openai_line_item("totally unstructured line item") == (None, None)


class TestFetchOpenAIDailyCosts:
    def test_parses_real_2026_05_16_partner_vetting_day(self):
        """The 2026-05-16 day in the fixture has gpt-4.1, gpt-5.5, web
        search results. Our parser must roll them up per (date, model).
        """
        fixture = json.loads(FIXTURE.read_text())
        client = _mock_client(fixture)
        out = fetch_openai_daily_costs(
            client,
            start_date=dt.date(2026, 5, 15),
            end_date=dt.date(2026, 5, 17),
            api_key="sk-admin-test",
            project_id="proj_0W823hZF68Md05LXB3iCXRx7",
        )

        # Both days present.
        assert set(out.keys()) == {"2026-05-15", "2026-05-16"}

        # 2026-05-16 totals: gpt-5.5 input+output+cached = 8.4368+4.7678+0.5266
        # = 13.7312; gpt-4.1 = 0.1373+0.0137 = 0.1510; web search = 0.49.
        day = out["2026-05-16"]
        assert "gpt-5.5-2026-04-23" in day
        assert "gpt-4.1-2025-04-14" in day
        assert "openai-web-search" in day

        gpt55 = day["gpt-5.5-2026-04-23"]
        assert gpt55 == pytest.approx(8.4368 + 4.7678 + 0.5266, abs=1e-3)

        gpt41 = day["gpt-4.1-2025-04-14"]
        assert gpt41 == pytest.approx(0.1373 + 0.0137, abs=1e-3)

        assert day["openai-web-search"] == pytest.approx(0.49, abs=1e-3)

    def test_2026_05_15_totals(self):
        fixture = json.loads(FIXTURE.read_text())
        client = _mock_client(fixture)
        out = fetch_openai_daily_costs(
            client,
            start_date=dt.date(2026, 5, 15),
            end_date=dt.date(2026, 5, 17),
            api_key="sk-admin-test",
        )

        day = out["2026-05-15"]
        # gpt-5.5: 0.0258 + 2.1940 + 1.5167
        assert day["gpt-5.5-2026-04-23"] == pytest.approx(0.0258 + 2.1940 + 1.5167, abs=1e-3)
        # gpt-5-mini: 0.0041 + 0.2560 + 0.4880
        assert day["gpt-5-mini-2025-08-07"] == pytest.approx(0.0041 + 0.2560 + 0.4880, abs=1e-3)
        # web search
        assert day["openai-web-search"] == pytest.approx(1.01, abs=1e-3)

    def test_handles_pagination(self):
        """A paginated response: page 1 has has_more=True, page 2 closes."""
        page1 = {
            "object": "page",
            "has_more": True,
            "next_page": "cursor_xyz",
            "data": [
                {
                    "start_time_iso": "2026-05-15T00:00:00",
                    "results": [
                        {"amount": {"value": "1.00"}, "line_item": "gpt-5.5-2026-04-23, input"},
                    ],
                }
            ],
        }
        page2 = {
            "object": "page",
            "has_more": False,
            "next_page": None,
            "data": [
                {
                    "start_time_iso": "2026-05-16T00:00:00",
                    "results": [
                        {"amount": {"value": "2.00"}, "line_item": "gpt-5.5-2026-04-23, output"},
                    ],
                }
            ],
        }
        client = _multi_page_client([page1, page2])
        out = fetch_openai_daily_costs(
            client,
            start_date=dt.date(2026, 5, 15),
            end_date=dt.date(2026, 5, 17),
            api_key="sk-admin-test",
        )
        assert out["2026-05-15"]["gpt-5.5-2026-04-23"] == pytest.approx(1.0)
        assert out["2026-05-16"]["gpt-5.5-2026-04-23"] == pytest.approx(2.0)

    def test_401_raises_reconcile_error(self):
        client = _mock_client({"error": {"message": "invalid x-api-key"}}, status=401)
        with pytest.raises(ReconcileError) as exc:
            fetch_openai_daily_costs(
                client,
                start_date=dt.date(2026, 5, 15),
                end_date=dt.date(2026, 5, 17),
                api_key="bad-key",
            )
        assert "401" in str(exc.value)
        assert "openai" in str(exc.value).lower()

    def test_network_error_raises_reconcile_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(ReconcileError) as exc:
            fetch_openai_daily_costs(
                client,
                start_date=dt.date(2026, 5, 15),
                end_date=dt.date(2026, 5, 17),
                api_key="sk-admin-test",
            )
        assert "network" in str(exc.value).lower()

    def test_unparseable_line_item_goes_to_openai_other(self):
        body = {
            "data": [
                {
                    "start_time_iso": "2026-05-15T00:00:00",
                    "results": [
                        {"amount": {"value": "0.50"}, "line_item": "unknown weird thing"},
                    ],
                }
            ],
            "has_more": False,
        }
        client = _mock_client(body)
        out = fetch_openai_daily_costs(
            client,
            start_date=dt.date(2026, 5, 15),
            end_date=dt.date(2026, 5, 16),
            api_key="sk-admin-test",
        )
        assert out["2026-05-15"]["openai-other"] == pytest.approx(0.5)

    def test_empty_response_returns_empty_dict(self):
        body = {"data": [], "has_more": False}
        client = _mock_client(body)
        out = fetch_openai_daily_costs(
            client,
            start_date=dt.date(2026, 5, 15),
            end_date=dt.date(2026, 5, 16),
            api_key="sk-admin-test",
        )
        assert out == {}
