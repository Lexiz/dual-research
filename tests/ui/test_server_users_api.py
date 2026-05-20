"""Spec 0125 — backend tests for /api/users + /api/onboarding + /api/system-settings.

Covers admin gating, the per-user reset, bulk reset, broadcast reset, the
onboarding-state GET/PUT round-trip, the mustRestart computation across
both ordering cases, and the system-settings flag.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_supabase_app

from .supabase_fake import FakeSupabaseClient


def _seed(fake: FakeSupabaseClient) -> None:
    """Three users: one admin, two members."""
    fake.approved_emails.extend(
        [
            {
                "email": "alex.lisitzky@gmail.com",
                "is_admin": True,
                "added_at": "2026-05-01T00:00:00+00:00",
                "onboarded_at": None,
                "onboarded_at_version": None,
                "tour_step": 1,
                "tour_force_reset_at": None,
                "last_seen_at": None,
            },
            {
                "email": "alice@example.com",
                "is_admin": False,
                "added_at": "2026-05-10T00:00:00+00:00",
                "onboarded_at": "2026-05-18T12:00:00+00:00",
                "onboarded_at_version": "1.5.0",
                "tour_step": 8,
                "tour_force_reset_at": None,
                "last_seen_at": "2026-05-19T08:00:00+00:00",
            },
            {
                "email": "bob@example.com",
                "is_admin": False,
                "added_at": "2026-05-15T00:00:00+00:00",
                "onboarded_at": None,
                "onboarded_at_version": None,
                "tour_step": 5,
                "tour_force_reset_at": None,
                "last_seen_at": None,
            },
        ]
    )
    fake.auth.users_by_token["admin-token"] = "alex.lisitzky@gmail.com"
    fake.auth.users_by_token["alice-token"] = "alice@example.com"
    fake.auth.users_by_token["bob-token"] = "bob@example.com"


@pytest.fixture
def app_and_fake():
    fake = FakeSupabaseClient()
    _seed(fake)
    app = _make_supabase_app(
        fake,
        supabase_url="https://x.supabase.co",
        supabase_anon_key="sb_publishable_test",
    )
    return app, fake


@pytest.fixture
def admin_client(app_and_fake):
    app, fake = app_and_fake
    with TestClient(app, headers={"Authorization": "Bearer admin-token"}) as c:
        yield c, fake


@pytest.fixture
def alice_client(app_and_fake):
    app, fake = app_and_fake
    with TestClient(app, headers={"Authorization": "Bearer alice-token"}) as c:
        yield c, fake


# ─── /api/users ─────────────────────────────────────────────────────────────


def test_list_users_admin_returns_all_with_camel_keys(admin_client):
    c, _ = admin_client
    r = c.get("/api/users")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 3
    # camelCase keys.
    sample = rows[0]
    expected_keys = {
        "email",
        "isAdmin",
        "addedAt",
        "onboardedAt",
        "onboardedAtVersion",
        "tourStep",
        "tourForceResetAt",
        "lastSeenAt",
        "mustRestart",
    }
    assert expected_keys.issubset(sample.keys()), sample.keys()


def test_list_users_non_admin_403(alice_client):
    c, _ = alice_client
    r = c.get("/api/users")
    assert r.status_code == 403


def test_list_users_unauthed_401(app_and_fake):
    app, _ = app_and_fake
    with TestClient(app) as c:
        r = c.get("/api/users")
    assert r.status_code in (401, 403)  # auth middleware shape


# ─── /api/users/<email>/reset-onboarding ─────────────────────────────────────


def test_reset_onboarding_admin_sets_force_reset(admin_client):
    c, fake = admin_client
    r = c.post("/api/users/alice@example.com/reset-onboarding")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["tourForceResetAt"]
    # Row updated.
    alice = next(x for x in fake.approved_emails if x["email"] == "alice@example.com")
    assert alice["tour_force_reset_at"] == body["tourForceResetAt"]


def test_reset_onboarding_404_for_unknown_email(admin_client):
    c, _ = admin_client
    r = c.post("/api/users/notinthelist@example.com/reset-onboarding")
    assert r.status_code == 404


def test_reset_onboarding_non_admin_403(alice_client):
    c, _ = alice_client
    r = c.post("/api/users/bob@example.com/reset-onboarding")
    assert r.status_code == 403


# ─── /api/users/bulk-reset-onboarding ────────────────────────────────────────


def test_bulk_reset_onboarding_two_users(admin_client):
    c, fake = admin_client
    r = c.post(
        "/api/users/bulk-reset-onboarding",
        json={"emails": ["alice@example.com", "bob@example.com"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["reset"] == 2
    for u in ("alice@example.com", "bob@example.com"):
        row = next(x for x in fake.approved_emails if x["email"] == u)
        assert row["tour_force_reset_at"] == body["at"]


def test_bulk_reset_onboarding_empty_array_400(admin_client):
    c, _ = admin_client
    r = c.post("/api/users/bulk-reset-onboarding", json={"emails": []})
    assert r.status_code == 400


def test_bulk_reset_onboarding_unknown_email_silently_skipped(admin_client):
    c, _ = admin_client
    r = c.post(
        "/api/users/bulk-reset-onboarding",
        json={"emails": ["alice@example.com", "doesnotexist@example.com"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["reset"] == 1  # only alice matched


# ─── /api/onboarding/broadcast-reset ─────────────────────────────────────────


def test_broadcast_reset_updates_all_rows(admin_client):
    c, fake = admin_client
    r = c.post("/api/onboarding/broadcast-reset")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["reset"] == 3
    ts = body["at"]
    for row in fake.approved_emails:
        assert row["tour_force_reset_at"] == ts


def test_broadcast_reset_non_admin_403(alice_client):
    c, _ = alice_client
    r = c.post("/api/onboarding/broadcast-reset")
    assert r.status_code == 403


# ─── /api/onboarding/state ──────────────────────────────────────────────────


def test_get_onboarding_state_returns_users_row(alice_client):
    c, _ = alice_client
    r = c.get("/api/onboarding/state")
    assert r.status_code == 200
    body = r.json()
    assert body["tourStep"] == 8
    assert body["onboardedAt"] == "2026-05-18T12:00:00+00:00"
    assert body["onboardedAtVersion"] == "1.5.0"
    assert body["mustRestart"] is False


def test_put_onboarding_state_updates_step(alice_client):
    c, fake = alice_client
    r = c.put("/api/onboarding/state", json={"tourStep": 3})
    assert r.status_code == 200
    alice = next(x for x in fake.approved_emails if x["email"] == "alice@example.com")
    assert alice["tour_step"] == 3


def test_put_onboarding_state_sets_onboarded_at(alice_client):
    c, fake = alice_client
    r = c.put(
        "/api/onboarding/state",
        json={"tourStep": 8, "onboardedAt": "2026-05-20T10:00:00+00:00"},
    )
    assert r.status_code == 200
    alice = next(x for x in fake.approved_emails if x["email"] == "alice@example.com")
    assert alice["onboarded_at"] == "2026-05-20T10:00:00+00:00"
    # onboarded_at_version is auto-set to current __version__.
    assert alice["onboarded_at_version"]


def test_put_onboarding_state_rejects_out_of_range(alice_client):
    c, _ = alice_client
    r = c.put("/api/onboarding/state", json={"tourStep": 999})
    assert r.status_code == 400


def test_put_onboarding_state_rejects_non_int(alice_client):
    c, _ = alice_client
    r = c.put("/api/onboarding/state", json={"tourStep": "five"})
    assert r.status_code == 400


# ─── mustRestart computation ─────────────────────────────────────────────────


def test_must_restart_true_when_force_reset_after_onboarded(admin_client):
    c, fake = admin_client
    # Alice was onboarded on 2026-05-18; admin force-resets her now.
    c.post("/api/users/alice@example.com/reset-onboarding")
    # Now Alice queries her state.
    fake.auth.users_by_token["alice-token"] = "alice@example.com"
    with TestClient(c.app, headers={"Authorization": "Bearer alice-token"}) as alice_c:
        r = alice_c.get("/api/onboarding/state")
    assert r.json()["mustRestart"] is True


def test_must_restart_false_when_no_force_reset(alice_client):
    c, _ = alice_client
    r = c.get("/api/onboarding/state")
    assert r.json()["mustRestart"] is False


# ─── /api/system-settings ───────────────────────────────────────────────────


def test_get_system_settings_default(alice_client):
    c, _ = alice_client
    r = c.get("/api/system-settings")
    assert r.status_code == 200
    assert r.json() == {"onboardingRequired": False}


def test_put_system_settings_admin(admin_client):
    c, fake = admin_client
    r = c.put("/api/system-settings", json={"onboardingRequired": True})
    assert r.status_code == 200
    assert r.json()["onboardingRequired"] is True
    row = fake.system_settings[0]
    assert row["onboarding_required"] is True
    assert row["updated_by"] == "alex.lisitzky@gmail.com"


def test_put_system_settings_non_admin_403(alice_client):
    c, _ = alice_client
    r = c.put("/api/system-settings", json={"onboardingRequired": True})
    assert r.status_code == 403


# ─── /api/me bumps last_seen_at ─────────────────────────────────────────────


def test_me_bumps_last_seen_at(alice_client):
    c, fake = alice_client
    before = next(x for x in fake.approved_emails if x["email"] == "alice@example.com")[
        "last_seen_at"
    ]
    r = c.get("/api/me")
    assert r.status_code == 200
    after = next(x for x in fake.approved_emails if x["email"] == "alice@example.com")[
        "last_seen_at"
    ]
    assert after != before
    assert after  # truthy ISO string
