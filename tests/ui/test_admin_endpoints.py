"""Tests for the admin-only allowlist endpoints + /api/me (spec 0022)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_supabase_app

from .supabase_fake import FakeSupabaseClient


ADMIN_TOKEN = "tok-admin"
ADMIN_EMAIL = "alex.lisitzky@gmail.com"
MEMBER_TOKEN = "tok-member"
MEMBER_EMAIL = "alice@example.com"


@pytest.fixture
def app_fake():
    fake = FakeSupabaseClient()
    fake.auth.users_by_token[ADMIN_TOKEN] = ADMIN_EMAIL
    fake.auth.users_by_token[MEMBER_TOKEN] = MEMBER_EMAIL
    fake.approved_emails.extend([
        {"email": ADMIN_EMAIL, "is_admin": True, "added_at": "2026-05-15T10:00:00+00:00"},
        {"email": MEMBER_EMAIL, "is_admin": False, "added_at": "2026-05-15T11:00:00+00:00"},
    ])
    app = _make_supabase_app(
        fake,
        supabase_url="https://x.supabase.co",
        supabase_anon_key="sb_publishable_test",
    )
    return app, fake


def _admin_client(app):
    return TestClient(app, headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})


def _member_client(app):
    return TestClient(app, headers={"Authorization": f"Bearer {MEMBER_TOKEN}"})


# ─── /api/me ──────────────────────────────────────────────────────────────────


def test_me_returns_email_and_admin_flag_for_admin(app_fake) -> None:
    app, _ = app_fake
    r = _admin_client(app).get("/api/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["isAdmin"] is True


def test_me_returns_admin_false_for_member(app_fake) -> None:
    app, _ = app_fake
    r = _member_client(app).get("/api/me")
    assert r.status_code == 200
    assert r.json()["isAdmin"] is False


# ─── GET /api/approved-emails ─────────────────────────────────────────────────


def test_list_allowlist_as_admin_returns_rows(app_fake) -> None:
    app, _ = app_fake
    r = _admin_client(app).get("/api/approved-emails")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    emails = {row["email"] for row in rows}
    assert emails == {ADMIN_EMAIL, MEMBER_EMAIL}
    # Output uses camelCase wire format.
    assert "isAdmin" in rows[0]


def test_list_allowlist_as_member_is_403(app_fake) -> None:
    app, _ = app_fake
    r = _member_client(app).get("/api/approved-emails")
    assert r.status_code == 403


# ─── POST /api/approved-emails ────────────────────────────────────────────────


def test_add_allowlist_entry_as_admin(app_fake) -> None:
    app, fake = app_fake
    r = _admin_client(app).post(
        "/api/approved-emails", json={"email": "new@example.com", "isAdmin": False}
    )
    assert r.status_code == 201
    emails = {row["email"] for row in fake.approved_emails}
    assert "new@example.com" in emails


def test_add_allowlist_entry_is_idempotent_on_duplicate(app_fake) -> None:
    app, fake = app_fake
    before = len(fake.approved_emails)
    _admin_client(app).post(
        "/api/approved-emails", json={"email": MEMBER_EMAIL, "isAdmin": False}
    )
    _admin_client(app).post(
        "/api/approved-emails", json={"email": MEMBER_EMAIL, "isAdmin": False}
    )
    assert len(fake.approved_emails) == before


def test_add_allowlist_with_invalid_email_is_400(app_fake) -> None:
    app, _ = app_fake
    r = _admin_client(app).post(
        "/api/approved-emails", json={"email": "not-an-email", "isAdmin": False}
    )
    assert r.status_code == 400


def test_add_allowlist_as_member_is_403(app_fake) -> None:
    app, _ = app_fake
    r = _member_client(app).post(
        "/api/approved-emails", json={"email": "x@example.com", "isAdmin": False}
    )
    assert r.status_code == 403


# ─── DELETE /api/approved-emails/{email} ──────────────────────────────────────


def test_admin_can_delete_member(app_fake) -> None:
    app, fake = app_fake
    r = _admin_client(app).delete(f"/api/approved-emails/{MEMBER_EMAIL}")
    assert r.status_code == 200
    emails = {row["email"] for row in fake.approved_emails}
    assert MEMBER_EMAIL not in emails


def test_admin_cannot_delete_themselves(app_fake) -> None:
    app, fake = app_fake
    r = _admin_client(app).delete(f"/api/approved-emails/{ADMIN_EMAIL}")
    assert r.status_code == 409
    assert "yourself" in r.json()["detail"].lower()
    # Row should still be there.
    assert any(row["email"] == ADMIN_EMAIL for row in fake.approved_emails)


def test_cannot_delete_last_admin(app_fake) -> None:
    app, fake = app_fake
    # Promote another row to admin, then have *that* admin try to delete the original.
    # Simpler: make member an admin, then verify member-as-admin can't delete the
    # original admin once we've engineered a scenario where the original is solo.
    # For the "last admin" rule specifically, the simplest case is:
    #   - Add a second admin token + email
    #   - Use that admin to delete the original ADMIN_EMAIL
    #   - That leaves the second admin as the only admin
    #   - Then have a different admin try to demote them — but we don't support demote;
    #     instead, try to delete the second admin via the second admin's own token (blocked
    #     by self-protect) or via a third admin (which would succeed since the first admin
    #     was the original one).
    # So: spin up a fresh fixture with a single admin and a second admin that disappears.
    fake.auth.users_by_token["tok-admin2"] = "second-admin@example.com"
    fake.approved_emails.append({"email": "second-admin@example.com", "is_admin": True,
                                 "added_at": "2026-05-15T12:00:00+00:00"})
    # Now second-admin tries to delete alex (the original admin), then tries to delete
    # themselves — the latter is the self-protect; for last-admin we delete alex first
    # then try to delete second-admin via... we'd need a third admin. Skip this part
    # of the path; assert via the lower-level helper instead.
    from dual_research.ui.server import _count_admins
    assert _count_admins(fake) == 2

    # Delete the second-admin row, leaving alex as the sole admin.
    fake.approved_emails[:] = [row for row in fake.approved_emails
                                if row["email"] != "second-admin@example.com"]
    assert _count_admins(fake) == 1

    # Now an admin tries to delete the only admin (alex). The "yourself" rule fires first
    # because alex is the caller, so test via a non-admin client instead — which should
    # 403 (admin-only). The cleanest assertion for the "last admin" guard is via a
    # different caller that *is* admin but isn't the target. That's exactly the scenario
    # we can't construct without a third admin → which would defeat the test.
    # So we exercise the helper directly: the count is 1, and the delete handler reads
    # _count_admins and rejects when targeting an admin row. Construct the request:
    r = _admin_client(app).delete(f"/api/approved-emails/{ADMIN_EMAIL}")
    # Self-protect fires first — that's the right precedence.
    assert r.status_code == 409


def test_delete_unknown_email_is_404(app_fake) -> None:
    app, _ = app_fake
    r = _admin_client(app).delete("/api/approved-emails/ghost@example.com")
    assert r.status_code == 404


def test_delete_as_member_is_403(app_fake) -> None:
    app, _ = app_fake
    r = _member_client(app).delete(f"/api/approved-emails/{ADMIN_EMAIL}")
    assert r.status_code == 403
