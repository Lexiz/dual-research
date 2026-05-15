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
    # Auth (spec 0021): seed an approved token so every test passes the gate
    # by default. Individual auth-specific tests live in test_supabase_auth.py.
    fake.auth.users_by_token["test-token"] = "alex.lisitzky@gmail.com"
    fake.approved_emails.append({"email": "alex.lisitzky@gmail.com", "is_admin": True})
    app = _make_supabase_app(
        fake,
        supabase_url="https://x.supabase.co",
        supabase_anon_key="sb_publishable_test",
    )
    with TestClient(app, headers={"Authorization": "Bearer test-token"}) as c:
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


# ─── attachments + attachment-blobs (spec 0025) ──────────────────────────────


def test_attachments_returns_empty_when_no_index(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/runs/20260515-163105-live-integration-test/attachments")
    assert r.status_code == 200
    assert r.json() == {"attachments": []}


def test_attachments_returns_parsed_index(client_and_fake) -> None:
    c, fake = client_and_fake
    fake.session_files.append(
        {
            "run_id": "20260515-163105-live-integration-test",
            "path": "attachments.json",
            "content": json.dumps(
                {
                    "attachments": [
                        {
                            "kind": "image",
                            "source": "cli:foo.png",
                            "rel_path": "attachments/abc-foo.png",
                            "mime": "image/png",
                            "size_bytes": 100,
                            "title": "foo.png",
                        }
                    ]
                }
            ),
        }
    )
    r = c.get("/api/runs/20260515-163105-live-integration-test/attachments")
    assert r.status_code == 200
    data = r.json()
    assert len(data["attachments"]) == 1
    assert data["attachments"][0]["kind"] == "image"


def test_attachment_blob_round_trips(client_and_fake) -> None:
    import base64

    c, fake = client_and_fake
    raw = b"\x89PNG-fake-binary"
    fake.attachment_blobs.append(
        {
            "run_id": "20260515-163105-live-integration-test",
            "rel_path": "attachments/abc-foo.png",
            "mime": "image/png",
            "size_bytes": len(raw),
            "content_b64": base64.b64encode(raw).decode("ascii"),
        }
    )
    r = c.get(
        "/api/runs/20260515-163105-live-integration-test/attachment-blobs/attachments/abc-foo.png"
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/")
    assert r.content == raw


def test_attachment_blob_404_when_missing(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get(
        "/api/runs/20260515-163105-live-integration-test/attachment-blobs/attachments/missing.png"
    )
    assert r.status_code == 404


def test_attachment_blob_404_when_not_under_attachments(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get(
        "/api/runs/20260515-163105-live-integration-test/attachment-blobs/brief.md"
    )
    assert r.status_code == 404
