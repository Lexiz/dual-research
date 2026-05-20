"""Spec 0126 — backend tests for /api/specs/{spec_id}.

Covers prefix-by-number match, exact filename match, 404 on unknown id,
400 on path-traversal attempts, frontmatter stripping, and the Content-Type
header. Tested in both fs and supabase modes — the endpoint is mounted on
both factories.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import (
    _strip_yaml_frontmatter,
    _make_app,
    _make_supabase_app,
)

from .supabase_fake import FakeSupabaseClient


# ─── Unit: frontmatter stripping ─────────────────────────────────────────────


def test_strip_frontmatter_drops_yaml_block():
    text = "---\nspec: 0121\ntitle: Foo\n---\n\n# Body\n\nMore."
    out = _strip_yaml_frontmatter(text)
    assert out.startswith("# Body")
    assert "spec: 0121" not in out


def test_strip_frontmatter_noop_when_absent():
    text = "# Body only\n\nNo frontmatter here.\n"
    assert _strip_yaml_frontmatter(text) == text


def test_strip_frontmatter_keeps_inner_dashes():
    # `---` appearing later in the body should NOT be treated as a delimiter.
    text = "---\nspec: 0001\n---\n\n# Title\n\nSection\n---\n\nBody after rule\n"
    out = _strip_yaml_frontmatter(text)
    assert out.startswith("# Title")
    assert "Body after rule" in out


# ─── fs-mode endpoint ────────────────────────────────────────────────────────


@pytest.fixture
def fs_client(tmp_path):
    app = _make_app(tmp_path)
    with TestClient(app) as c:
        yield c


def test_fs_specs_exact_filename(fs_client):
    r = fs_client.get("/api/specs/0121-how-it-works-and-changelog-rework")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/markdown")
    body = r.text
    # Frontmatter stripped → first non-blank line should be the H1.
    first_nonblank = next(ln for ln in body.splitlines() if ln.strip())
    assert first_nonblank.startswith("# Spec 0121")


def test_fs_specs_prefix_by_number(fs_client):
    r = fs_client.get("/api/specs/0121")
    assert r.status_code == 200, r.text
    assert "Spec 0121" in r.text


def test_fs_specs_404_for_unknown(fs_client):
    r = fs_client.get("/api/specs/9999")
    assert r.status_code == 404


def test_fs_specs_rejects_path_traversal(fs_client):
    # FastAPI normalizes `..` segments at the router level (404) before our
    # regex sees them; if it somehow reaches our handler, the regex returns
    # 400. Either way the request is rejected — it must NOT return a 200
    # with someone's /etc/passwd. Accept both rejection codes.
    r = fs_client.get("/api/specs/..%2Fetc")
    assert r.status_code in (400, 404)


def test_fs_specs_rejects_dotdot(fs_client):
    r = fs_client.get("/api/specs/..")
    assert r.status_code in (400, 404)


def test_fs_specs_rejects_extension(fs_client):
    # Period isn't in [0-9a-zA-Z\-_]; regex rejects (400).
    r = fs_client.get("/api/specs/0121.md")
    assert r.status_code == 400


def test_fs_specs_content_type_is_markdown(fs_client):
    r = fs_client.get("/api/specs/0126")
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/markdown; charset=utf-8"


# ─── supabase-mode endpoint ──────────────────────────────────────────────────


def _seed(fake: FakeSupabaseClient) -> None:
    fake.auth.users_by_token["test-token"] = "alex.lisitzky@gmail.com"
    fake.approved_emails.append({"email": "alex.lisitzky@gmail.com", "is_admin": True})


@pytest.fixture
def sb_client():
    fake = FakeSupabaseClient()
    _seed(fake)
    app = _make_supabase_app(
        fake,
        supabase_url="https://x.supabase.co",
        supabase_anon_key="sb_publishable_test",
    )
    with TestClient(app, headers={"Authorization": "Bearer test-token"}) as c:
        yield c


def test_sb_specs_authed(sb_client):
    r = sb_client.get("/api/specs/0121")
    assert r.status_code == 200, r.text
    assert "Spec 0121" in r.text


def test_sb_specs_unauthed_401():
    fake = FakeSupabaseClient()
    app = _make_supabase_app(
        fake,
        supabase_url="https://x.supabase.co",
        supabase_anon_key="sb_publishable_test",
    )
    with TestClient(app) as c:
        r = c.get("/api/specs/0121")
    # No Authorization header → unauthenticated.
    assert r.status_code in (401, 403)


def test_sb_specs_invalid_id_rejected(sb_client):
    r = sb_client.get("/api/specs/..")
    assert r.status_code in (400, 404)


def test_sb_specs_invalid_id_extension_400(sb_client):
    # Extension dots reach the handler — must 400 from the regex.
    r = sb_client.get("/api/specs/0121.md")
    assert r.status_code == 400
