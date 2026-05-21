"""Spec 0033 — server endpoints for the Input tab.

Two endpoints under test:

- ``GET /api/runs/<id>/inputs/index`` — list of available turn-keys.
- ``GET /api/runs/<id>/inputs/<key>`` — single bundle by key. Accepts
  camel (``phase2Round3Claude``) and snake (``phase2_round3_claude``)
  forms; ``input`` returns the synthesised Phase 0 bundle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dual_research.ui.server import _make_app


def _seed_minimal_session(runs_dir: Path, name: str) -> Path:
    session = runs_dir / name
    session.mkdir(parents=True)
    (session / "brief.md").write_text("# Test\n\nbody\n", encoding="utf-8")
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
    return session


def _seed_input_bundle(session: Path, key: str, pieces: dict[str, str]) -> None:
    inputs_dir = session / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "agent": "claude",
        "phase": "phase2",
        "label": "phase2-r3-claude",
        "pieces": pieces,
        "emitted_at": "",
    }
    (inputs_dir / f"{key}.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    app = _make_app(runs_dir)
    return TestClient(app)


class TestGetBundle:
    def test_snake_case_key_returns_bundle(self, client: TestClient, tmp_path: Path) -> None:
        session = _seed_minimal_session(tmp_path / "runs", "run-1")
        _seed_input_bundle(session, "phase2_round3_claude", {"system": "S", "brief": "B"})
        r = client.get("/api/runs/run-1/inputs/phase2_round3_claude")
        assert r.status_code == 200
        data = r.json()
        assert data["pieces"]["system"] == "S"
        assert data["pieces"]["brief"] == "B"

    def test_camel_case_key_also_accepted(self, client: TestClient, tmp_path: Path) -> None:
        session = _seed_minimal_session(tmp_path / "runs", "run-2")
        _seed_input_bundle(session, "phase2_round3_claude", {"system": "S"})
        r = client.get("/api/runs/run-2/inputs/phase2Round3Claude")
        assert r.status_code == 200
        assert r.json()["pieces"]["system"] == "S"

    def test_missing_key_synthesises_fallback_with_agent_default(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Spec 0085 — when a per-turn bundle JSON isn't on disk, the
        server now synthesises a fallback from the agent's current
        default prompts (system prompt + brief), tagged
        ``system_source: 'agent-default'``. Historical runs that
        pre-date input auditing still render something useful."""
        _seed_minimal_session(tmp_path / "runs", "run-3")
        r = client.get("/api/runs/run-3/inputs/phase2_round9_claude")
        assert r.status_code == 200
        data = r.json()
        assert data["system_source"] == "agent-default"
        # Spec 0145 — phase-2 fallback emits the canonical system key.
        assert data["pieces"]["system.task.plan_negotiation"]
        # Brief carried through under the canonical user-prompt key.
        assert "# Test" in data["pieces"]["user_prompt.message"]

    def test_unparseable_key_returns_404(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Spec 0085 — a key that matches the path regex but doesn't
        parse to a real (phase, round, agent) triple yields 404, not
        a synthesised bundle. Guards against silent fallback for
        garbage keys."""
        _seed_minimal_session(tmp_path / "runs", "run-3b")
        # Path-regex permits the chars; the parser rejects the shape.
        r = client.get("/api/runs/run-3b/inputs/phaseXY_round1_claude")
        assert r.status_code == 404

    def test_phase0_input_synthesised_from_brief(self, client: TestClient, tmp_path: Path) -> None:
        _seed_minimal_session(tmp_path / "runs", "run-4")
        r = client.get("/api/runs/run-4/inputs/input")
        assert r.status_code == 200
        data = r.json()
        assert data["phase"] == "phase0"
        # Spec 0145 — synthesised bundle exposes canonical keys.
        assert "# Test" in data["pieces"]["user_prompt.message"]
        assert "epistemic" in data["pieces"]["system.task.input"]
        # Spec 0085 — Phase 0 synthesis also stamps system_source.
        assert data["system_source"] == "agent-default"

    def test_recorded_bundle_stamps_system_source_recorded(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Spec 0085 — bundles served from disk (i.e., recorded for
        modern runs) are stamped ``system_source: 'recorded'`` so the
        frontend can distinguish them from synthesised fallbacks and
        SKIP the 'agent default' caveat."""
        session = _seed_minimal_session(tmp_path / "runs", "run-rec")
        _seed_input_bundle(session, "phase2_round3_claude", {"system": "REAL", "brief": "B"})
        r = client.get("/api/runs/run-rec/inputs/phase2_round3_claude")
        assert r.status_code == 200
        data = r.json()
        assert data["system_source"] == "recorded"
        assert data["pieces"]["system"] == "REAL"

    def test_persisted_input_json_overrides_synth_fallback(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Spec 0142 — when ``inputs/input.json`` is present (written at
        session setup), the server returns it instead of falling through
        to the spec-0085 synthesis path. The recorded bundle is stamped
        ``system_source: 'recorded'`` so the frontend skips the
        'agent default' caveat on the Initial Brief modal."""
        session = _seed_minimal_session(tmp_path / "runs", "run-rec-input")
        inputs_dir = session / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        recorded = {
            "agent": "shared",
            "phase": "phase0",
            "label": "phase0-input",
            "pieces": {
                "system": "REAL_SYSTEM_PROMPT",
                "brief": "REAL_BRIEF_TEXT",
                "d1": "", "d2": "", "plan": "",
                "hist": "", "draft": "", "histp": "",
            },
            "emitted_at": "",
            "system_source": "recorded",
        }
        (inputs_dir / "input.json").write_text(json.dumps(recorded), encoding="utf-8")

        r = client.get("/api/runs/run-rec-input/inputs/input")
        assert r.status_code == 200
        data = r.json()
        assert data["system_source"] == "recorded"
        assert data["pieces"]["brief"] == "REAL_BRIEF_TEXT"
        assert data["pieces"]["system"] == "REAL_SYSTEM_PROMPT"

    def test_traversal_attempt_rejected(self, client: TestClient, tmp_path: Path) -> None:
        _seed_minimal_session(tmp_path / "runs", "run-5")
        r = client.get("/api/runs/run-5/inputs/..%2Fetc")
        # Either 404 (route doesn't accept slashes/non-key chars) or
        # 422 from FastAPI's path validation; both are safe.
        assert r.status_code in (404, 422)


class TestIndex:
    def test_lists_bundles_on_disk(self, client: TestClient, tmp_path: Path) -> None:
        session = _seed_minimal_session(tmp_path / "runs", "run-6")
        _seed_input_bundle(session, "phase1_claude", {"system": "S"})
        _seed_input_bundle(session, "phase1_gpt", {"system": "S"})
        r = client.get("/api/runs/run-6/inputs/index")
        assert r.status_code == 200
        keys = r.json()["keys"]
        assert "phase1_claude" in keys
        assert "phase1_gpt" in keys
        # Phase 0 input is always available when brief.md exists.
        assert "input" in keys

    def test_empty_run_still_lists_phase0_input(self, client: TestClient, tmp_path: Path) -> None:
        _seed_minimal_session(tmp_path / "runs", "run-7")
        r = client.get("/api/runs/run-7/inputs/index")
        assert r.status_code == 200
        # Pre-0033 run (no inputs dir) — but brief.md exists, so the
        # phase 0 synth is offered.
        assert r.json()["keys"] == ["input"]


class TestInputPathOnSnapshot:
    """``TurnTokenUsage.inputPath`` should round-trip through the wire as
    camelCase so the frontend can detect which turns have bundles."""

    def test_input_path_present_in_snapshot(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        from dual_research.ui.aggregator import apply_event
        from dual_research.ui.models import Run

        runs_dir = tmp_path / "runs"
        session = _seed_minimal_session(runs_dir, "run-8")
        # Use the real aggregator to emit an input bundle, then dump the
        # transcript so the snapshot pass picks it up.
        run = Run(id="run-8", display_id="run8")
        apply_event(
            run,
            {
                "event": "turn_inputs",
                "agent": "claude",
                "phase": "phase1",
                "label": "phase1-claude",
                "pieces": {"system": "S", "brief": "B"},
            },
            session,
        )
        # Now write the event to the transcript so /api/runs/<id> sees it.
        with (session / "transcript.jsonl").open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "event": "turn_inputs",
                        "agent": "claude",
                        "phase": "phase1",
                        "label": "phase1-claude",
                        "pieces": {"system": "S", "brief": "B"},
                    }
                )
                + "\n"
            )
        r = client.get("/api/runs/run-8")
        assert r.status_code == 200
        usage = r.json()["phaseTokenUsage"]["phase1Claude"]
        # camelCase'd at the wire boundary.
        assert usage["inputPath"] == "inputs/phase1_claude.json"
