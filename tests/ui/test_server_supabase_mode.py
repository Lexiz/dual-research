"""Tests for the supabase-backed UI server (spec 0020)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_supabase_app

from .supabase_fake import FakeSupabaseClient


def _seed(client: FakeSupabaseClient) -> None:
    client.runs.extend(
        [
            {
                "id": "20260515-163105-live-integration-test",
                "slug": "live-integration-test",
                "created_at": "2026-05-15T16:31:05+00:00",
                "phase_reached": "done",
                "exit_code": 0,
                "duration_ms": 772_800,
                "total_cost_usd": 0.4228,
                "state": {"phase": "done", "final_emitted_to": "/tmp/final.md"},
                "metrics": {"total_cost_usd": 0.4228},
            },
            {
                "id": "20260515-103340-sample-brief",
                "slug": "sample-brief",
                "created_at": "2026-05-15T10:33:40+00:00",
                "phase_reached": "phase2",
                "exit_code": None,
                "duration_ms": None,
                "total_cost_usd": 0.05,
                "state": {"phase": "phase2"},
                "metrics": None,
            },
        ]
    )
    client.session_files.extend(
        [
            {
                "run_id": "20260515-163105-live-integration-test",
                "path": "brief.md",
                "content": "# Compare SQLite and PostgreSQL\n\nWhich for 1-10M rows?",
            },
            {
                "run_id": "20260515-163105-live-integration-test",
                "path": "state.json",
                "content": json.dumps({"phase": "done", "final_emitted_to": "/tmp/final.md"}),
            },
            {
                "run_id": "20260515-163105-live-integration-test",
                "path": "final.md",
                "content": "# Final\n\nConverged content.\n",
            },
            {
                "run_id": "20260515-103340-sample-brief",
                "path": "brief.md",
                "content": "# Sample brief\n\nNothing fancy",
            },
            {
                "run_id": "20260515-103340-sample-brief",
                "path": "state.json",
                "content": json.dumps({"phase": "phase2"}),
            },
        ]
    )
    client.events.extend(
        [
            {
                "run_id": "20260515-163105-live-integration-test",
                "seq": 0,
                "ts": "2026-05-15T16:31:05+00:00",
                "kind": "run_started",
                "payload": {
                    "slug": "live-integration-test",
                    "model_tier": "test",
                    "claude_model": "claude-haiku-4-5",
                    "openai_model": "gpt-5-mini",
                    "soft_cap": 3,
                    "hard_cap": 5,
                },
            },
            {
                "run_id": "20260515-163105-live-integration-test",
                "seq": 1,
                "ts": "2026-05-15T16:44:48+00:00",
                "kind": "run_completed",
                "payload": {
                    "phase_reached": "done",
                    "exit_code": 0,
                    "total_cost_usd": 0.4228,
                    "duration_ms": 772800,
                },
            },
        ]
    )


@pytest.fixture
def client_and_fake():
    fake = FakeSupabaseClient()
    _seed(fake)
    app = _make_supabase_app(fake)
    with TestClient(app) as c:
        yield c, fake


def test_health_reports_supabase_backend(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["backend"] == "supabase"


def test_list_runs_returns_rows_sorted_newest_first(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/runs")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert rows[0]["id"] == "20260515-163105-live-integration-test"
    assert rows[1]["id"] == "20260515-103340-sample-brief"
    assert rows[0]["topic"] == "Compare SQLite and PostgreSQL"
    assert rows[0]["status"] == "completed"
    assert rows[0]["phase"] == 5  # phase_to_int("done") == 5
    assert rows[0]["cost"] == 0.4228


def test_list_runs_topic_falls_back_to_first_line_when_no_h1(client_and_fake) -> None:
    c, fake = client_and_fake
    for f in fake.session_files:
        if f["run_id"] == "20260515-163105-live-integration-test" and f["path"] == "brief.md":
            f["content"] = "Compare SQLite vs Postgres. One-page memo."
    r = c.get("/api/runs")
    rows = r.json()
    target = next(r for r in rows if r["id"] == "20260515-163105-live-integration-test")
    assert target["topic"] == "Compare SQLite vs Postgres. One-page memo."


def test_list_runs_empty_topic_when_no_brief(client_and_fake) -> None:
    c, fake = client_and_fake
    fake.session_files = [f for f in fake.session_files if f["path"] != "brief.md"]
    r = c.get("/api/runs")
    rows = r.json()
    assert all(row["topic"] == "" for row in rows)


def test_get_run_returns_full_snapshot(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/runs/20260515-163105-live-integration-test")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "20260515-163105-live-integration-test"
    assert body["topic"] == "Compare SQLite and PostgreSQL"


def test_get_run_missing_returns_404(client_and_fake) -> None:
    c, _ = client_and_fake
    assert c.get("/api/runs/no-such-run").status_code == 404


def test_get_run_path_traversal_returns_404(client_and_fake) -> None:
    c, _ = client_and_fake
    assert c.get("/api/runs/..%2Fsecret").status_code == 404


def test_get_file_returns_text_body(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/runs/20260515-163105-live-integration-test/files/final.md")
    assert r.status_code == 200
    assert "Converged content" in r.text


def test_get_file_missing_returns_404(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/runs/20260515-163105-live-integration-test/files/no.md")
    assert r.status_code == 404


def test_get_file_path_traversal_returns_404(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/runs/20260515-163105-live-integration-test/files/../brief.md")
    # Starlette normalizes the path before routing, so traversal collapses
    # to a non-matching path → 404 either way.
    assert r.status_code in (400, 404)
