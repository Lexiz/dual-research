"""Spec 0082 — HIDDEN_RUN_IDS filter tests.

Verifies that runs whose ids appear in ``HIDDEN_RUN_IDS`` are silently
omitted from the list, search, and per-run endpoints. Rows stay in the
fake database — the filter is server-side only.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from dual_research.ui import server as ui_server
from dual_research.ui.server import _make_supabase_app

from .supabase_fake import FakeSupabaseClient


_HIDDEN_ID = "20260518-000000-hidden-fixture"
_VISIBLE_ID = "20260518-000000-visible-fixture"


@pytest.fixture
def app_with_hidden(monkeypatch: pytest.MonkeyPatch):
    """Seed two runs; mark one as hidden via ``HIDDEN_RUN_IDS``."""
    monkeypatch.setattr(ui_server, "HIDDEN_RUN_IDS", frozenset({_HIDDEN_ID}))

    fake = FakeSupabaseClient()
    for rid, slug in [(_HIDDEN_ID, "hidden"), (_VISIBLE_ID, "visible")]:
        fake.runs.append(
            {
                "id": rid,
                "slug": slug,
                "created_at": "2026-05-18T00:00:00+00:00",
                "phase_reached": "done",
                "exit_code": 0,
                "duration_ms": 1000,
                "total_cost_usd": 0.01,
                "state": {"phase": "done"},
                "metrics": {"total_cost_usd": 0.01},
            }
        )
        fake.session_files.append(
            {"run_id": rid, "path": "brief.md", "content": f"# {slug} topic"}
        )
        fake.session_files.append(
            {"run_id": rid, "path": "state.json", "content": json.dumps({"phase": "done"})}
        )
    fake.auth.users_by_token["t"] = "alex.lisitzky@gmail.com"
    fake.approved_emails.append({"email": "alex.lisitzky@gmail.com", "is_admin": True})

    app = _make_supabase_app(
        fake, supabase_url="https://x.supabase.co", supabase_anon_key="anon"
    )
    with TestClient(app, headers={"Authorization": "Bearer t"}) as c:
        yield c


def test_list_runs_excludes_hidden_ids(app_with_hidden) -> None:
    r = app_with_hidden.get("/api/runs")
    assert r.status_code == 200
    body = r.json()
    ids = [row.get("id") for row in body]
    assert _VISIBLE_ID in ids
    assert _HIDDEN_ID not in ids


def test_run_detail_returns_404_for_hidden_id(app_with_hidden) -> None:
    r = app_with_hidden.get(f"/api/runs/{_HIDDEN_ID}")
    assert r.status_code == 404


def test_run_detail_returns_200_for_visible_id(app_with_hidden) -> None:
    r = app_with_hidden.get(f"/api/runs/{_VISIBLE_ID}")
    assert r.status_code == 200


def test_search_excludes_hidden_ids(app_with_hidden) -> None:
    # Both runs match the substring "topic" via their brief.md. The hidden
    # one must be filtered out before results are returned.
    r = app_with_hidden.get("/api/search?q=topic")
    assert r.status_code == 200
    ids = [row.get("runId") for row in r.json()]
    assert _VISIBLE_ID in ids
    assert _HIDDEN_ID not in ids
