"""Spec 0245 — admin archive / unarchive endpoint tests.

Exercises ``POST /api/runs/{id}/archive`` + ``DELETE /api/runs/{id}/archive``
through the FastAPI app built by ``_make_supabase_app`` against the
in-memory ``FakeSupabaseClient`` fixture. Mirrors the contract laid out
in spec 0245 §2.2: 204 on success, 403 for non-admin, 404 for unknown,
409 on no-op (already archived / not archived).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_supabase_app

from .ui.supabase_fake import FakeSupabaseClient


ADMIN_TOKEN = "tok-admin"
ADMIN_EMAIL = "alex.lisitzky@gmail.com"
MEMBER_TOKEN = "tok-member"
MEMBER_EMAIL = "alice@example.com"

RUN_ID = "20260528-100000-test-run"


@pytest.fixture
def app_with_run():
    fake = FakeSupabaseClient()
    fake.auth.users_by_token[ADMIN_TOKEN] = ADMIN_EMAIL
    fake.auth.users_by_token[MEMBER_TOKEN] = MEMBER_EMAIL
    fake.approved_emails.extend([
        {"email": ADMIN_EMAIL, "is_admin": True, "added_at": "2026-05-15T10:00:00+00:00"},
        {"email": MEMBER_EMAIL, "is_admin": False, "added_at": "2026-05-15T11:00:00+00:00"},
    ])
    fake.runs.append({
        "id": RUN_ID,
        "slug": "test",
        "created_at": "2026-05-28T10:00:00+00:00",
        "pushed_at": "2026-05-28T10:05:00+00:00",
        "phase_reached": "done",
        "exit_code": 0,
        "duration_ms": 300000,
        "total_cost_usd": 0.10,
        "state": {"phase": "done"},
        "metrics": {"total_cost_usd": 0.10},
        # Spec 0245 — new columns default to None on existing rows.
        "deleted_at": None,
        "deleted_by": None,
    })
    app = _make_supabase_app(
        fake, supabase_url="https://x.supabase.co", supabase_anon_key="anon"
    )
    return app, fake


def _admin(app):
    return TestClient(app, headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})


def _member(app):
    return TestClient(app, headers={"Authorization": f"Bearer {MEMBER_TOKEN}"})


def test_archive_run_admin_204(app_with_run) -> None:
    app, fake = app_with_run
    r = _admin(app).post(f"/api/runs/{RUN_ID}/archive")
    assert r.status_code == 204
    row = fake.runs[0]
    assert row["deleted_at"] is not None
    assert row["deleted_by"] == ADMIN_EMAIL


def test_archive_run_non_admin_403(app_with_run) -> None:
    app, fake = app_with_run
    r = _member(app).post(f"/api/runs/{RUN_ID}/archive")
    assert r.status_code == 403
    assert fake.runs[0]["deleted_at"] is None
    assert fake.runs[0]["deleted_by"] is None


def test_archive_run_unknown_id_404(app_with_run) -> None:
    app, _fake = app_with_run
    r = _admin(app).post("/api/runs/20260101-000000-missing/archive")
    assert r.status_code == 404


def test_archive_run_already_archived_409(app_with_run) -> None:
    app, _fake = app_with_run
    client = _admin(app)
    first = client.post(f"/api/runs/{RUN_ID}/archive")
    assert first.status_code == 204
    second = client.post(f"/api/runs/{RUN_ID}/archive")
    assert second.status_code == 409


def test_unarchive_run_admin_204(app_with_run) -> None:
    app, fake = app_with_run
    client = _admin(app)
    archive_resp = client.post(f"/api/runs/{RUN_ID}/archive")
    assert archive_resp.status_code == 204
    unarchive_resp = client.delete(f"/api/runs/{RUN_ID}/archive")
    assert unarchive_resp.status_code == 204
    row = fake.runs[0]
    assert row["deleted_at"] is None
    assert row["deleted_by"] is None


def test_unarchive_run_not_archived_409(app_with_run) -> None:
    app, _fake = app_with_run
    r = _admin(app).delete(f"/api/runs/{RUN_ID}/archive")
    assert r.status_code == 409
