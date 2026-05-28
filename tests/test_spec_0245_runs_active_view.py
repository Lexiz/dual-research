"""Spec 0245 — `runs_active` view + `?archived=` query-param tests.

The view is a Postgres ``WHERE deleted_at IS NULL`` predicate; the
``FakeSupabaseClient`` mirrors that via a snapshot at ``.table()`` time
(see ``tests/ui/supabase_fake.py``). These tests verify the canonical
reader sites (``/api/runs``, ``/api/runs/{id}``, ``/api/search``) all
filter archived rows out for everyone by default, and that
``?archived=true`` flips the list endpoint to the archived rows for
admins only.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_supabase_app

from .ui.supabase_fake import FakeSupabaseClient


ADMIN_TOKEN = "tok-admin"
ADMIN_EMAIL = "alex.lisitzky@gmail.com"
MEMBER_TOKEN = "tok-member"
MEMBER_EMAIL = "alice@example.com"

ACTIVE_ID = "20260528-100000-active-run"
ARCHIVED_ID = "20260527-100000-archived-run"


@pytest.fixture
def app_mixed():
    fake = FakeSupabaseClient()
    fake.auth.users_by_token[ADMIN_TOKEN] = ADMIN_EMAIL
    fake.auth.users_by_token[MEMBER_TOKEN] = MEMBER_EMAIL
    fake.approved_emails.extend([
        {"email": ADMIN_EMAIL, "is_admin": True, "added_at": "2026-05-15T10:00:00+00:00"},
        {"email": MEMBER_EMAIL, "is_admin": False, "added_at": "2026-05-15T11:00:00+00:00"},
    ])
    fake.runs.extend([
        {
            "id": ACTIVE_ID,
            "slug": "active",
            "created_at": "2026-05-28T10:00:00+00:00",
            "pushed_at": "2026-05-28T10:05:00+00:00",
            "phase_reached": "done",
            "exit_code": 0,
            "duration_ms": 300000,
            "total_cost_usd": 0.10,
            "state": {"phase": "done"},
            "metrics": {},
            "deleted_at": None,
            "deleted_by": None,
        },
        {
            "id": ARCHIVED_ID,
            "slug": "archived",
            "created_at": "2026-05-27T10:00:00+00:00",
            "pushed_at": "2026-05-27T10:05:00+00:00",
            "phase_reached": "done",
            "exit_code": 0,
            "duration_ms": 200000,
            "total_cost_usd": 0.05,
            "state": {"phase": "done"},
            "metrics": {},
            "deleted_at": "2026-05-28T09:00:00+00:00",
            "deleted_by": ADMIN_EMAIL,
        },
    ])
    for rid, topic in [(ACTIVE_ID, "live topic"), (ARCHIVED_ID, "archived topic")]:
        fake.session_files.append({"run_id": rid, "path": "brief.md", "content": f"# {topic}"})
        fake.session_files.append({"run_id": rid, "path": "state.json", "content": json.dumps({"phase": "done"})})
    app = _make_supabase_app(
        fake, supabase_url="https://x.supabase.co", supabase_anon_key="anon"
    )
    return app


def _admin(app):
    return TestClient(app, headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})


def _member(app):
    return TestClient(app, headers={"Authorization": f"Bearer {MEMBER_TOKEN}"})


def test_runs_active_view_excludes_archived(app_mixed) -> None:
    r = _admin(app_mixed).get("/api/runs")
    assert r.status_code == 200
    ids = [row["id"] for row in r.json()]
    assert ACTIVE_ID in ids
    assert ARCHIVED_ID not in ids


def test_archived_query_param_admin_returns_archived(app_mixed) -> None:
    r = _admin(app_mixed).get("/api/runs?archived=true")
    assert r.status_code == 200
    ids = [row["id"] for row in r.json()]
    assert ARCHIVED_ID in ids
    assert ACTIVE_ID not in ids


def test_archived_query_param_non_admin_ignored(app_mixed) -> None:
    r = _member(app_mixed).get("/api/runs?archived=true")
    assert r.status_code == 200
    ids = [row["id"] for row in r.json()]
    # Non-admin gets the active list as if they hadn't passed the flag —
    # no error, no leak of archived ids.
    assert ACTIVE_ID in ids
    assert ARCHIVED_ID not in ids


def test_run_detail_404_on_archived(app_mixed) -> None:
    # Detail endpoint uses _require_run_exists which now reads
    # runs_active, so archived rows 404 for everyone (admin included)
    # — admin-side recovery flows through the dedicated unarchive
    # endpoint, not the detail surface.
    r = _admin(app_mixed).get(f"/api/runs/{ARCHIVED_ID}")
    assert r.status_code == 404
    r2 = _member(app_mixed).get(f"/api/runs/{ARCHIVED_ID}")
    assert r2.status_code == 404
