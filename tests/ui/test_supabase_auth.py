"""Tests for the SupabaseAuthMiddleware + /api/config (spec 0021)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_supabase_app

from .supabase_fake import FakeSupabaseClient


@pytest.fixture
def client_and_fake():
    fake = FakeSupabaseClient(
        runs=[{"id": "R1", "slug": "r1", "created_at": "2026-05-15T00:00:00+00:00",
               "phase_reached": "done", "exit_code": 0, "duration_ms": 1000,
               "total_cost_usd": 0.01, "state": {}, "metrics": None}],
    )
    app = _make_supabase_app(
        fake,
        supabase_url="https://x.supabase.co",
        supabase_anon_key="sb_publishable_test",
    )
    with TestClient(app) as c:
        yield c, fake


# ─── Public endpoints (no auth required) ──────────────────────────────────────


def test_health_is_public(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/health")
    assert r.status_code == 200


def test_config_is_public(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert body["supabaseUrl"] == "https://x.supabase.co"
    assert body["supabaseAnonKey"] == "sb_publishable_test"


def test_static_is_public(client_and_fake) -> None:
    c, _ = client_and_fake
    # /index.html is served by StaticFiles; should pass through without auth.
    r = c.get("/")
    # 200 or 404 depending on whether the file exists at test time — but never 401.
    assert r.status_code != 401


# ─── Gated endpoints ──────────────────────────────────────────────────────────


def test_api_runs_without_token_is_401(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/runs")
    assert r.status_code == 401
    assert r.json()["error"] == "missing_token"


def test_api_runs_with_malformed_authorization_is_401(client_and_fake) -> None:
    c, _ = client_and_fake
    r = c.get("/api/runs", headers={"Authorization": "Basic xyz"})
    assert r.status_code == 401


def test_api_runs_with_invalid_token_is_401(client_and_fake) -> None:
    c, fake = client_and_fake
    # No user registered for this token — get_user returns user=None.
    r = c.get("/api/runs", headers={"Authorization": "Bearer bogus"})
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_token"


def test_api_runs_with_not_approved_email_is_403(client_and_fake) -> None:
    c, fake = client_and_fake
    fake.auth.users_by_token["t1"] = "stranger@example.com"
    # approved_emails stays empty by default
    r = c.get("/api/runs", headers={"Authorization": "Bearer t1"})
    assert r.status_code == 403
    body = r.json()
    assert body["error"] == "email_not_approved"
    assert body["email"] == "stranger@example.com"


def test_api_runs_with_approved_email_is_200(client_and_fake) -> None:
    c, fake = client_and_fake
    fake.auth.users_by_token["t2"] = "alex.lisitzky@gmail.com"
    fake.approved_emails.append({"email": "alex.lisitzky@gmail.com", "is_admin": True})
    r = c.get("/api/runs", headers={"Authorization": "Bearer t2"})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_email_comparison_is_case_insensitive(client_and_fake) -> None:
    """Tokens sometimes come back with mixed-case emails; allowlist is lowercase."""
    c, fake = client_and_fake
    fake.auth.users_by_token["t3"] = "Alex.Lisitzky@Gmail.com"
    fake.approved_emails.append({"email": "alex.lisitzky@gmail.com", "is_admin": True})
    r = c.get("/api/runs", headers={"Authorization": "Bearer t3"})
    assert r.status_code == 200


def test_validation_is_cached_across_requests(client_and_fake) -> None:
    c, fake = client_and_fake
    fake.auth.users_by_token["t4"] = "alex.lisitzky@gmail.com"
    fake.approved_emails.append({"email": "alex.lisitzky@gmail.com", "is_admin": True})
    c.get("/api/runs", headers={"Authorization": "Bearer t4"})
    c.get("/api/runs", headers={"Authorization": "Bearer t4"})
    c.get("/api/runs", headers={"Authorization": "Bearer t4"})
    assert fake.auth.calls.count("t4") == 1  # only the first request hit get_user
