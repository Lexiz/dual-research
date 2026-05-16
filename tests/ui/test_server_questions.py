"""Spec 0034 — wire format for questions + new disagreement/review-item fields.

Asserts that the snapshot endpoint carries ``questions`` (camelCased)
and that the per-disagreement / per-review-item entries surface the
new ``raisedTurnKey`` / ``closedTurnKey`` / ``blockId`` fields.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_app


def _seed_session(runs_dir: Path, name: str) -> Path:
    session = runs_dir / name
    session.mkdir(parents=True)
    (session / "brief.md").write_text("# T\n\nb\n", encoding="utf-8")
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
        json.dumps({"total_cost_usd": 0.0}), encoding="utf-8"
    )
    (session / "transcript.jsonl").write_text("", encoding="utf-8")
    p1 = session / "phase1"
    p1.mkdir()
    (p1 / "draft-claude.md").write_text("# C\n\nSomething.\n", encoding="utf-8")
    (p1 / "draft-openai.md").write_text(
        "# O\n\nSQLite is fine for low-concurrency reads.\n", encoding="utf-8"
    )
    p2 = session / "phase2"
    p2.mkdir()
    (p2 / "round-01-claude.md").write_text(
        """## Summary
S.

## Open questions for openai
1. Have you measured concurrency?
> quote: SQLite is fine for low-concurrency reads
""",
        encoding="utf-8",
    )
    (p2 / "round-01-openai.md").write_text(
        "## Summary\nG.\n\n## Open questions for claude\n(none)\n",
        encoding="utf-8",
    )
    return session


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    app = _make_app(runs_dir)
    return TestClient(app)


class TestQuestionsOnWire:
    def test_questions_camel_key_present(self, client: TestClient, tmp_path: Path) -> None:
        _seed_session(tmp_path / "runs", "run-q1")
        r = client.get("/api/runs/run-q1")
        assert r.status_code == 200
        data = r.json()
        assert "questions" in data
        assert isinstance(data["questions"], list)
        assert len(data["questions"]) == 1
        q = data["questions"][0]
        # Inner fields camelCased.
        assert q["id"] == "Q-c-r1-01"
        assert q["raisedRound"] == 1
        assert q["raisedBy"] == "claude"
        assert q["raisedTurnKey"] == "phase2_round1_claude"
        assert q["status"] == "open"
        # Anchor block_id resolved against GPT's P1 draft.
        assert q["blockId"] is not None


class TestReviewItemBlockIdOnWire:
    def test_review_item_carries_blockId(self, client: TestClient, tmp_path: Path) -> None:
        _seed_session(tmp_path / "runs", "run-r1")
        r = client.get("/api/runs/run-r1")
        assert r.status_code == 200
        data = r.json()
        items = data["phaseReviewItems"]["phase2Round1Claude"]
        assert items[0]["blockId"] is not None
