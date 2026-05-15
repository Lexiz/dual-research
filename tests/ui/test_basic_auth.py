"""Tests for the HTTP Basic auth middleware (spec 0020 stopgap)."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_app


@pytest.fixture
def client_no_auth(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    app = _make_app(runs)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_with_auth(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    app = _make_app(runs, basic_auth_password="hunter2")
    with TestClient(app) as c:
        yield c


def _creds(password: str) -> dict[str, str]:
    encoded = base64.b64encode(f"dual-research:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {encoded}"}


def test_no_password_means_no_gate(client_no_auth) -> None:
    r = client_no_auth.get("/api/health")
    assert r.status_code == 200


def test_password_gated_rejects_unauthenticated(client_with_auth) -> None:
    r = client_with_auth.get("/api/runs")
    assert r.status_code == 401
    assert "Basic" in r.headers.get("www-authenticate", "")


def test_password_gated_allows_correct_creds(client_with_auth) -> None:
    r = client_with_auth.get("/api/runs", headers=_creds("hunter2"))
    assert r.status_code == 200


def test_password_gated_rejects_wrong_password(client_with_auth) -> None:
    r = client_with_auth.get("/api/runs", headers=_creds("nope"))
    assert r.status_code == 401


def test_password_gated_rejects_wrong_username(client_with_auth) -> None:
    encoded = base64.b64encode(b"someone-else:hunter2").decode("ascii")
    r = client_with_auth.get("/api/runs", headers={"Authorization": f"Basic {encoded}"})
    assert r.status_code == 401


def test_health_bypasses_auth(client_with_auth) -> None:
    r = client_with_auth.get("/api/health")
    assert r.status_code == 200
    assert "version" in r.json()


def test_malformed_authorization_header(client_with_auth) -> None:
    r = client_with_auth.get("/api/runs", headers={"Authorization": "Bearer xyz"})
    assert r.status_code == 401
    r2 = client_with_auth.get("/api/runs", headers={"Authorization": "Basic not-base64!"})
    assert r2.status_code == 401
