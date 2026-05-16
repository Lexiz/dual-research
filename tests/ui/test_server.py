"""Tests for the FastAPI UI server."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_app, _snake_to_camel, _to_camel


# ─── Fixture helpers ──────────────────────────────────────────────────────────


def _seed_session(runs_dir: Path, session_name: str, *, topic: str = "Test topic") -> Path:
    """Create a minimal session directory with brief.md / state.json / metrics.json
    / transcript.jsonl so the aggregator + server can read it."""
    session = runs_dir / session_name
    session.mkdir(parents=True)
    (session / "brief.md").write_text(f"# {topic}\n\nbody\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps(
            {
                "phase": "phase2",
                "drafter": None,
                "agreed_plan": None,
                "final_surfaced_disagreements": [],
                "draft_round": 1,
                "final_emitted_to": None,
            }
        ),
        encoding="utf-8",
    )
    (session / "metrics.json").write_text(
        json.dumps({"total_cost_usd": 0.5}), encoding="utf-8"
    )
    line = json.dumps(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": "run_started",
            "session_dir": str(session),
            "slug": session_name,
            "model_tier": "test",
            "claude_model": "claude-haiku-4-5",
            "openai_model": "gpt-5-mini",
            "soft_cap": 3,
            "hard_cap": 5,
        }
    )
    (session / "transcript.jsonl").write_text(line + "\n", encoding="utf-8")
    return session


@pytest.fixture
def client_with_runs(tmp_path):
    """Build a TestClient over an empty tmp runs/ dir."""
    runs = tmp_path / "runs"
    runs.mkdir()
    app = _make_app(runs)
    with TestClient(app) as c:
        yield c, runs


# ─── camelCase translation ────────────────────────────────────────────────────


class TestCamelCase:
    @pytest.mark.parametrize(
        "snake,camel",
        [
            ("phase_timings", "phaseTimings"),
            ("started_at_ago", "startedAtAgo"),
            ("in_", "in"),
            ("current_turn", "currentTurn"),
            ("foo", "foo"),
            ("foo_bar_baz", "fooBarBaz"),
        ],
    )
    def test_snake_to_camel(self, snake, camel):
        assert _snake_to_camel(snake) == camel

    def test_to_camel_recurses(self):
        obj = {
            "phase_timings": {0: 18, 1: 482},
            "agents": {"claude": {"tokens": {"in_": 100, "out": 200}}},
        }
        out = _to_camel(obj)
        assert out == {
            "phaseTimings": {"0": 18, "1": 482},
            "agents": {"claude": {"tokens": {"in": 100, "out": 200}}},
        }

    def test_to_camel_passes_primitives(self):
        assert _to_camel("x") == "x"
        assert _to_camel(42) == 42
        assert _to_camel(None) is None
        assert _to_camel([1, 2, 3]) == [1, 2, 3]

    def test_phase_token_usage_inner_keys_and_fields(self):
        """Spec 0029 — per-turn usage dict survives the wire pass with
        camelized inner keys and `in_` → `in`, `cache_read` → `cacheRead`,
        `model_id` → `modelId`."""
        from dual_research.ui.models import Run, TurnTokenUsage, to_jsonable

        run = Run(id="r", display_id="abcd")
        run.phase_token_usage["phase2_round1_claude"] = TurnTokenUsage(
            in_=1234, out=567, cache_read=300, cache_write=80,
            cost=0.42, model_id="claude-sonnet-4-6",
        )
        run.phase_token_usage["phase0_gpt"] = TurnTokenUsage(
            in_=10, out=20, model_id="gpt-5.5",
        )
        wire = _to_camel(to_jsonable(run))
        usage = wire["phaseTokenUsage"]
        # Inner keys are camelized — the frontend must mirror this.
        assert set(usage.keys()) == {"phase2Round1Claude", "phase0Gpt"}
        # Field names: `in_` → `in`, `cache_read` → `cacheRead`,
        # `cache_write` → `cacheWrite`, `model_id` → `modelId`.
        entry = usage["phase2Round1Claude"]
        assert entry == {
            "in": 1234, "out": 567,
            "cacheRead": 300, "cacheWrite": 80,
            "cost": 0.42, "modelId": "claude-sonnet-4-6",
        }


# ─── /api/health ──────────────────────────────────────────────────────────────


class TestHealth:
    def test_returns_ok_with_version(self, client_with_runs):
        c, runs = client_with_runs
        r = c.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert "version" in body and body["version"]
        assert body["runsDir"] == str(runs.resolve())


# ─── /api/runs ────────────────────────────────────────────────────────────────


class TestListRuns:
    def test_empty_dir(self, client_with_runs):
        c, _ = client_with_runs
        r = c.get("/api/runs")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_rows_in_reverse_order(self, client_with_runs):
        c, runs = client_with_runs
        _seed_session(runs, "20260515-100000-alpha", topic="Alpha")
        _seed_session(runs, "20260515-110000-beta", topic="Beta")
        r = c.get("/api/runs")
        rows = r.json()
        assert len(rows) == 2
        # Reverse lex order: newest (beta) first.
        assert rows[0]["id"] == "20260515-110000-beta"
        assert rows[1]["id"] == "20260515-100000-alpha"
        # Camel-case at the wire.
        assert "displayId" in rows[0]
        assert "startedAtAgo" in rows[0]

    def test_ignores_stray_folders(self, client_with_runs):
        c, runs = client_with_runs
        # A non-session folder (no state.json or brief.md) should be ignored.
        (runs / "not-a-session").mkdir()
        _seed_session(runs, "20260515-100000-real", topic="Real")
        rows = c.get("/api/runs").json()
        assert {r["id"] for r in rows} == {"20260515-100000-real"}


# ─── /api/runs/{id} ───────────────────────────────────────────────────────────


class TestRunSnapshot:
    def test_404_when_missing(self, client_with_runs):
        c, _ = client_with_runs
        assert c.get("/api/runs/does-not-exist").status_code == 404

    def test_returns_full_snapshot(self, client_with_runs):
        c, runs = client_with_runs
        _seed_session(runs, "20260515-100000-x", topic="Topic X")
        r = c.get("/api/runs/20260515-100000-x")
        assert r.status_code == 200
        body = r.json()
        # Required camelCase fields are present.
        for k in (
            "id",
            "displayId",
            "topic",
            "status",
            "phase",
            "startedAtAgo",
            "round",
            "agents",
            "disagreements",
            "errors",
            "phaseTimings",
            "phaseReviewItems",   # spec 0027
            "currentDraftPath",   # spec 0028
            "phaseTokenUsage",    # spec 0029
        ):
            assert k in body, f"missing key {k}"
        assert body["topic"] == "Topic X"
        assert body["agents"]["claude"]["tokens"].keys() == {"in", "out"}
        # Spec 0029 — per-turn token usage is keyed by `phase{N}_<agent>` or
        # `phase{N}_round{R}_<agent>` on the Python side. The wire camelizer
        # rewrites those inner keys to `phase{N}{Agent}` / `phase{N}Round{R}{Agent}`
        # (e.g. `phase2Round1Claude`). Empty for a freshly-seeded fixture
        # because no `turn_ended` events have been applied — the dict
        # exists, just has no entries.
        assert isinstance(body["phaseTokenUsage"], dict)

    def test_path_traversal_rejected(self, client_with_runs):
        c, _ = client_with_runs
        # `..` in the id is blocked outright.
        r = c.get("/api/runs/..")
        # FastAPI may treat `..` as the parent route — either 404 or 405 is OK
        # as long as we don't expose anything.
        assert r.status_code in (404, 405)


# ─── /api/runs/{id}/files/{path:path} ────────────────────────────────────────


class TestFileEndpoint:
    def test_returns_markdown(self, client_with_runs):
        c, runs = client_with_runs
        session = _seed_session(runs, "20260515-100000-x")
        r = c.get(f"/api/runs/{session.name}/files/brief.md")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/plain")
        assert "Test topic" in r.text

    def test_404_when_file_absent(self, client_with_runs):
        c, runs = client_with_runs
        session = _seed_session(runs, "20260515-100000-x")
        r = c.get(f"/api/runs/{session.name}/files/no-such.md")
        assert r.status_code == 404

    def test_rejects_path_traversal(self, client_with_runs):
        c, runs = client_with_runs
        session = _seed_session(runs, "20260515-100000-x")
        # Try to climb out via ..
        r = c.get(f"/api/runs/{session.name}/files/../../../etc/passwd")
        assert r.status_code == 404

    def test_rejects_disallowed_extension(self, client_with_runs):
        c, runs = client_with_runs
        session = _seed_session(runs, "20260515-100000-x")
        (session / "secret.pdf").write_text("PDF DATA", encoding="utf-8")
        r = c.get(f"/api/runs/{session.name}/files/secret.pdf")
        assert r.status_code == 404


# ─── /api/runs/{id}/stream (SSE) ─────────────────────────────────────────────


class TestStream:
    """The SSE endpoint composes two pieces:

    - ``_snapshot_frame(session)`` — builds one ``snapshot`` frame
    - ``sse_starlette.EventSourceResponse`` — handles the SSE wire format

    We unit-test the snapshot helper here (it's where our logic lives) and
    leave the wire-format concerns to sse-starlette's own tests. A
    full-stack streaming test against ``TestClient`` blocks indefinitely
    because the stream is unbounded by design — that surface is exercised
    manually via ``dual-research serve`` instead.
    """

    def test_snapshot_frame_shape(self, tmp_path):
        from dual_research.ui.server import _snapshot_frame

        runs = tmp_path / "runs"
        runs.mkdir()
        session = _seed_session(runs, "20260515-100000-x", topic="Frame topic")
        frame = _snapshot_frame(session)
        assert frame["event"] == "snapshot"
        data = json.loads(frame["data"])
        assert data["topic"] == "Frame topic"
        assert data["id"] == session.name
        assert "displayId" in data
        assert "agents" in data and "claude" in data["agents"]

    # NB: a full-stack streaming reachability test against ``TestClient``
    # blocks indefinitely because the stream is unbounded by design (the
    # server emits one frame per ``transcript.jsonl`` change forever). The
    # endpoint is exercised manually via ``dual-research serve`` and
    # automatically by the UI client in spec 0011.


# ─── /api/runs/{id}/attachments + attachment-blobs (spec 0025) ───────────────


class TestAttachments:
    def _seed_with_attachments(self, runs_dir: Path) -> Path:
        session = _seed_session(runs_dir, "20260515-100000-x", topic="With attachments")
        att_dir = session / "attachments"
        att_dir.mkdir()
        (att_dir / "abc-foo.png").write_bytes(b"\x89PNG-binary")
        (session / "attachments.json").write_text(
            json.dumps(
                {
                    "attachments": [
                        {
                            "kind": "image",
                            "source": "cli:foo.png",
                            "title": "foo.png",
                            "url": None,
                            "rel_path": "attachments/abc-foo.png",
                            "mime": "image/png",
                            "size_bytes": len(b"\x89PNG-binary"),
                        },
                        {
                            "kind": "link",
                            "source": "url:https://example.com",
                            "title": "Example",
                            "url": "https://example.com",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        return session

    def test_lists_attachments(self, client_with_runs):
        c, runs = client_with_runs
        session = self._seed_with_attachments(runs)
        r = c.get(f"/api/runs/{session.name}/attachments")
        assert r.status_code == 200
        data = r.json()
        assert "attachments" in data
        kinds = [a["kind"] for a in data["attachments"]]
        assert "image" in kinds
        assert "link" in kinds

    def test_empty_when_no_attachments_file(self, client_with_runs):
        c, runs = client_with_runs
        session = _seed_session(runs, "20260515-100000-no-att")
        r = c.get(f"/api/runs/{session.name}/attachments")
        assert r.status_code == 200
        assert r.json() == {"attachments": []}

    def test_serves_blob_with_mime(self, client_with_runs):
        c, runs = client_with_runs
        session = self._seed_with_attachments(runs)
        r = c.get(f"/api/runs/{session.name}/attachment-blobs/attachments/abc-foo.png")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/")
        assert r.content == b"\x89PNG-binary"

    def test_blob_404_on_missing(self, client_with_runs):
        c, runs = client_with_runs
        session = _seed_session(runs, "20260515-100000-x")
        r = c.get(f"/api/runs/{session.name}/attachment-blobs/attachments/none.png")
        assert r.status_code == 404

    def test_blob_rejects_path_outside_attachments(self, client_with_runs):
        c, runs = client_with_runs
        session = self._seed_with_attachments(runs)
        # Even an existing file inside the session-dir is off-limits if it's
        # not under attachments/.
        r = c.get(f"/api/runs/{session.name}/attachment-blobs/brief.md")
        assert r.status_code == 404

    def test_blob_rejects_traversal(self, client_with_runs):
        c, runs = client_with_runs
        session = self._seed_with_attachments(runs)
        r = c.get(
            f"/api/runs/{session.name}/attachment-blobs/attachments/../brief.md"
        )
        assert r.status_code == 404


# ─── Static UI mount ──────────────────────────────────────────────────────────


class TestStaticMount:
    def test_root_404_when_no_index(self, client_with_runs):
        c, _ = client_with_runs
        # Static dir is empty in tests — root request 404s (or returns a small
        # autoindex listing depending on Starlette). Either way we shouldn't 500.
        r = c.get("/")
        assert r.status_code in (200, 404)
