"""Tests for the /api/search endpoint (SPEC-0060 cross-run search)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_app


# ─── Fixture helpers ──────────────────────────────────────────────────────────


def _seed_session(
    runs_dir: Path,
    session_name: str,
    *,
    topic: str = "Test topic",
    brief_body: str = "",
    final_text: str | None = None,
) -> Path:
    """Create a minimal session directory."""
    session = runs_dir / session_name
    session.mkdir(parents=True)

    brief_content = f"# {topic}\n\n{brief_body}\n" if topic else f"{brief_body}\n"
    (session / "brief.md").write_text(brief_content, encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps({
            "phase": "phase2",
            "drafter": None,
            "agreed_plan": None,
            "final_surfaced_disagreements": [],
            "draft_round": 1,
            "final_emitted_to": None,
        }),
        encoding="utf-8",
    )
    (session / "metrics.json").write_text(
        json.dumps({"total_cost_usd": 0.5}), encoding="utf-8"
    )
    line = json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "run_started",
        "session_dir": str(session),
        "slug": session_name,
        "model_tier": "test",
        "claude_model": "claude-haiku-4-5",
        "openai_model": "gpt-5-mini",
        "soft_cap": 3,
        "hard_cap": 5,
    })
    (session / "transcript.jsonl").write_text(line + "\n", encoding="utf-8")

    if final_text is not None:
        (session / "final.md").write_text(final_text, encoding="utf-8")

    return session


@pytest.fixture
def client_with_search_runs(tmp_path):
    """Build a TestClient with several seeded runs for search testing."""
    runs = tmp_path / "runs"
    runs.mkdir()
    _seed_session(runs, "run-alpha", topic="Partner vetting architecture critique",
                  brief_body="Examining RLS policies and row-level security.")
    _seed_session(runs, "run-beta", topic="Machine learning pipeline review",
                  brief_body="Evaluating transformer model performance.",
                  final_text="# Final Report\n\nThe RLS configuration was optimal.")
    _seed_session(runs, "run-gamma", topic="Database schema migration",
                  brief_body="Planning PostgreSQL migration strategy.")
    app = _make_app(runs)
    with TestClient(app) as c:
        yield c, runs


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestSearchEndpoint:
    def test_empty_query_returns_empty_list(self, client_with_search_runs):
        c, _ = client_with_search_runs
        resp = c.get("/api/search?q=")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_no_query_param_returns_empty_list(self, client_with_search_runs):
        c, _ = client_with_search_runs
        resp = c.get("/api/search")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_topic_match(self, client_with_search_runs):
        c, _ = client_with_search_runs
        resp = c.get("/api/search?q=partner")
        assert resp.status_code == 200
        results = resp.json()
        topics = [r for r in results if r["matchType"] == "topic"]
        assert len(topics) >= 1
        assert any("Partner" in r["snippet"] for r in topics)

    def test_brief_body_match(self, client_with_search_runs):
        c, _ = client_with_search_runs
        resp = c.get("/api/search?q=rls")
        assert resp.status_code == 200
        results = resp.json()
        # Should match the brief body of run-alpha.
        briefs = [r for r in results if r["matchType"] == "brief"]
        assert len(briefs) >= 1

    def test_final_doc_match(self, client_with_search_runs):
        c, _ = client_with_search_runs
        resp = c.get("/api/search?q=rls")
        assert resp.status_code == 200
        results = resp.json()
        # run-beta has "RLS" in its final.md.
        finals = [r for r in results if r["matchType"] == "final"]
        assert len(finals) >= 1

    def test_case_insensitive(self, client_with_search_runs):
        c, _ = client_with_search_runs
        resp_lower = c.get("/api/search?q=machine")
        resp_upper = c.get("/api/search?q=MACHINE")
        assert resp_lower.status_code == 200
        assert resp_upper.status_code == 200
        assert len(resp_lower.json()) == len(resp_upper.json())
        assert len(resp_lower.json()) >= 1

    def test_no_match_returns_empty(self, client_with_search_runs):
        c, _ = client_with_search_runs
        resp = c.get("/api/search?q=zzzznonexistent")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_result_shape(self, client_with_search_runs):
        c, _ = client_with_search_runs
        resp = c.get("/api/search?q=partner")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        r = results[0]
        assert "runId" in r
        assert "displayId" in r
        assert "topic" in r
        assert "matchType" in r
        assert "snippet" in r

    def test_max_results_cap(self, tmp_path):
        """Verify results are capped at 50."""
        runs = tmp_path / "runs"
        runs.mkdir()
        for i in range(60):
            _seed_session(runs, f"run-{i:03d}",
                          topic=f"Test run number {i} about banana",
                          brief_body="Also banana flavored.")
        app = _make_app(runs)
        with TestClient(app) as c:
            resp = c.get("/api/search?q=banana")
            assert resp.status_code == 200
            results = resp.json()
            assert len(results) <= 50

    def test_empty_runs_dir(self, tmp_path):
        """Search with no runs returns empty."""
        runs = tmp_path / "runs"
        runs.mkdir()
        app = _make_app(runs)
        with TestClient(app) as c:
            resp = c.get("/api/search?q=anything")
            assert resp.status_code == 200
            assert resp.json() == []
