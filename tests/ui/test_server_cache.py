"""Spec 0079 — LRU cache + Cache-Control header + gzip middleware tests.

Covers the read-path-perf changes that wrap the immutable per-turn endpoints:

- `_read_input_bundle_supabase` and `_read_search_audit_supabase` memoise
  positive results in process-local LRUs, so repeated lookups for the same
  `(run_id, key)` skip the Supabase round-trip.
- The corresponding HTTP endpoints emit
  `Cache-Control: public, max-age=86400, immutable`.
- `GZipMiddleware` compresses bundle responses that exceed the 1 KB floor.
"""

from __future__ import annotations

import gzip
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dual_research.ui import cache as ui_cache
from dual_research.ui.server import (
    _IMMUTABLE_CACHE_CONTROL,
    _INPUT_BUNDLE_CACHE,
    _SEARCH_AUDIT_CACHE,
    _clear_caches_for_test,
    _make_supabase_app,
    _read_input_bundle_supabase,
    _read_search_audit_supabase,
)

from .supabase_fake import FakeBuilder, FakeSupabaseClient


# ─── execute-counting wrapper ────────────────────────────────────────────────


class _CountingClient:
    """Wraps ``FakeSupabaseClient`` and increments ``execute_count`` on every
    terminal ``.execute()`` so tests can assert "second call hit the cache,
    not the client"."""

    def __init__(self, inner: FakeSupabaseClient) -> None:
        self._inner = inner
        self.execute_count = 0

    def table(self, name: str) -> "_CountingBuilder":
        return _CountingBuilder(self._inner.table(name), self)

    # auth + other namespaces fall through unmodified
    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _CountingBuilder:
    def __init__(self, inner: FakeBuilder, parent: _CountingClient) -> None:
        self._inner = inner
        self._parent = parent

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._inner, name)
        if name == "execute":
            def _execute(*a: Any, **kw: Any) -> Any:
                self._parent.execute_count += 1
                return attr(*a, **kw)

            return _execute

        # Chain methods return a FakeBuilder; rewrap so the next call still
        # counts.
        def _chain(*a: Any, **kw: Any) -> "_CountingBuilder":
            new_inner = attr(*a, **kw)
            return _CountingBuilder(new_inner, self._parent)

        return _chain


# ─── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Every test starts with empty LRUs."""
    _clear_caches_for_test()


def _seed_bundle(fake: FakeSupabaseClient, run_id: str, key: str) -> dict:
    bundle = {
        "agent": "claude",
        "phase": "phase2",
        "label": f"phase2-{key}",
        "pieces": {"system": "you are a research agent", "brief": "test brief"},
        "emitted_at": "2026-05-18T00:00:00+00:00",
    }
    fake.session_files.append(
        {"run_id": run_id, "path": f"inputs/{key}.json", "content": json.dumps(bundle)}
    )
    return bundle


def _seed_search_audit(fake: FakeSupabaseClient, run_id: str, key: str) -> dict:
    audit = {
        "agent": "claude",
        "queries": [{"query": "test", "results": 5}],
    }
    fake.session_files.append(
        {"run_id": run_id, "path": f"searches/{key}.json", "content": json.dumps(audit)}
    )
    return audit


def _seed_run(fake: FakeSupabaseClient, run_id: str) -> None:
    fake.runs.append(
        {
            "id": run_id,
            "slug": "test",
            "created_at": "2026-05-18T00:00:00+00:00",
            "phase_reached": "phase2",
            "exit_code": None,
            "duration_ms": None,
            "total_cost_usd": 0.0,
            "state": {"phase": "phase2"},
            "metrics": None,
        }
    )


@pytest.fixture
def app_client():
    fake = FakeSupabaseClient()
    run_id = "20260518-000000-test"
    _seed_run(fake, run_id)
    _seed_bundle(fake, run_id, "phase2_round1_claude")
    _seed_search_audit(fake, run_id, "phase2_round1_claude")
    # also seed brief.md so /inputs/input synthesises cleanly
    fake.session_files.append(
        {"run_id": run_id, "path": "brief.md", "content": "# test brief"}
    )
    # auth (spec 0021) — seed an approved token
    fake.auth.users_by_token["test-token"] = "alex.lisitzky@gmail.com"
    fake.approved_emails.append({"email": "alex.lisitzky@gmail.com", "is_admin": True})

    app = _make_supabase_app(
        fake,
        supabase_url="https://x.supabase.co",
        supabase_anon_key="sb_publishable_test",
    )
    with TestClient(app, headers={"Authorization": "Bearer test-token"}) as c:
        yield c, run_id


# ─── helper-level cache tests ────────────────────────────────────────────────


def test_input_bundle_helper_caches_positive_results() -> None:
    fake = FakeSupabaseClient()
    run_id = "run-input"
    _seed_bundle(fake, run_id, "phase2_round1_claude")
    spy = _CountingClient(fake)

    first = _read_input_bundle_supabase(spy, run_id, "phase2_round1_claude")
    second = _read_input_bundle_supabase(spy, run_id, "phase2_round1_claude")

    assert first is not None
    assert first == second
    # First call hits Supabase once. Second call returns from the LRU with no
    # additional .execute() — that's the perf win we ship.
    assert spy.execute_count == 1


def test_search_audit_helper_caches_positive_results() -> None:
    fake = FakeSupabaseClient()
    run_id = "run-search"
    _seed_search_audit(fake, run_id, "phase2_round1_claude")
    spy = _CountingClient(fake)

    first = _read_search_audit_supabase(spy, run_id, "phase2_round1_claude")
    second = _read_search_audit_supabase(spy, run_id, "phase2_round1_claude")

    assert first is not None
    assert first == second
    assert spy.execute_count == 1


def test_input_bundle_helper_does_not_cache_negative_results() -> None:
    fake = FakeSupabaseClient()
    # No bundle seeded — first call returns None, must not be cached because
    # the bundle may appear later in a live run.
    spy = _CountingClient(fake)

    assert _read_input_bundle_supabase(spy, "ghost-run", "phase2_round1_claude") is None
    # After miss the row gets seeded — second call must see it.
    _seed_bundle(fake, "ghost-run", "phase2_round1_claude")
    assert _read_input_bundle_supabase(spy, "ghost-run", "phase2_round1_claude") is not None
    # Two execute() calls: one for the miss path, one for the real hit. If the
    # negative result had been cached, we'd see only one.
    assert spy.execute_count >= 2


def test_search_audit_helper_does_not_cache_negative_results() -> None:
    fake = FakeSupabaseClient()
    spy = _CountingClient(fake)

    assert _read_search_audit_supabase(spy, "ghost", "phase2_round1_claude") is None
    _seed_search_audit(fake, "ghost", "phase2_round1_claude")
    assert _read_search_audit_supabase(spy, "ghost", "phase2_round1_claude") is not None
    assert spy.execute_count >= 2


def test_bounded_lru_evicts_oldest_when_full() -> None:
    lru = ui_cache.BoundedLRU(maxsize=3)
    lru.set("a", 1)
    lru.set("b", 2)
    lru.set("c", 3)
    assert lru.get("a") == 1  # a is now most-recent
    lru.set("d", 4)  # b should evict (it's now LRU)
    assert lru.get("b") is ui_cache.MISSING
    assert lru.get("a") == 1
    assert lru.get("c") == 3
    assert lru.get("d") == 4


def test_bounded_lru_caches_none_value_distinctly_from_miss() -> None:
    lru = ui_cache.BoundedLRU(maxsize=4)
    assert lru.get("k") is ui_cache.MISSING
    lru.set("k", None)
    # None must round-trip without collapsing into MISSING.
    assert lru.get("k") is None
    assert lru.get("k") is not ui_cache.MISSING


def test_clear_caches_for_test_drops_all_entries() -> None:
    _INPUT_BUNDLE_CACHE.set(("r", "k"), {"x": 1})
    _SEARCH_AUDIT_CACHE.set(("r", "k"), {"x": 1})
    assert len(_INPUT_BUNDLE_CACHE) == 1
    assert len(_SEARCH_AUDIT_CACHE) == 1
    _clear_caches_for_test()
    assert len(_INPUT_BUNDLE_CACHE) == 0
    assert len(_SEARCH_AUDIT_CACHE) == 0


# ─── HTTP-level header + gzip tests ──────────────────────────────────────────


def test_input_bundle_endpoint_emits_immutable_cache_control(app_client) -> None:
    c, run_id = app_client
    r = c.get(f"/api/runs/{run_id}/inputs/phase2_round1_claude")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == _IMMUTABLE_CACHE_CONTROL


def test_search_audit_endpoint_emits_immutable_cache_control(app_client) -> None:
    c, run_id = app_client
    r = c.get(f"/api/runs/{run_id}/searches/phase2_round1_claude")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == _IMMUTABLE_CACHE_CONTROL


def test_runs_list_does_not_emit_immutable_cache_control(app_client) -> None:
    """Run-list mutates as new runs land; must NOT be marked immutable."""
    c, _ = app_client
    r = c.get("/api/runs")
    assert r.status_code == 200
    # No Cache-Control at all is fine; an immutable one would be a bug.
    assert "immutable" not in (r.headers.get("cache-control") or "")


def test_gzip_compresses_large_bundle_payload() -> None:
    """Build a bundle large enough to exceed the 1 KB gzip floor and confirm
    the response advertises ``Content-Encoding: gzip``."""
    fake = FakeSupabaseClient()
    run_id = "run-big"
    _seed_run(fake, run_id)
    big_pieces = {"system": "x" * 4096}  # well above the 1 KB minimum_size
    fake.session_files.append(
        {
            "run_id": run_id,
            "path": "inputs/phase2_round1_claude.json",
            "content": json.dumps(
                {
                    "agent": "claude",
                    "phase": "phase2",
                    "label": "phase2_round1_claude",
                    "pieces": big_pieces,
                    "emitted_at": "",
                }
            ),
        }
    )
    fake.auth.users_by_token["test-token"] = "alex.lisitzky@gmail.com"
    fake.approved_emails.append({"email": "alex.lisitzky@gmail.com", "is_admin": True})
    app = _make_supabase_app(
        fake,
        supabase_url="https://x.supabase.co",
        supabase_anon_key="sb_publishable_test",
    )
    with TestClient(app, headers={"Authorization": "Bearer test-token"}) as c:
        r = c.get(
            f"/api/runs/{run_id}/inputs/phase2_round1_claude",
            headers={"Accept-Encoding": "gzip"},
        )
    assert r.status_code == 200
    assert r.headers.get("content-encoding") == "gzip"
    # httpx decompresses transparently; sanity-check the body parses.
    body = r.json()
    assert body["pieces"]["system"].startswith("x")
