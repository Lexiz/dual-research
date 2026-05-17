"""``load_run_snapshot`` resilience on ``drafter=null + completed`` runs — spec 0047.

Five historical local runs in the working tree reached ``status: completed``
with ``drafter: null`` (orchestrator versions that flipped state.json to
``phase: done`` before Phase 3 ran). The aggregator + frontend must handle
this combination without crashing — the front-end's ``ArtifactHeader``
``meta`` access was the visible regression (spec 0047 F1), but the
load path itself should survive cleanly so the snapshot is at least
servable for inspection.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from dual_research.ui.aggregator import load_run_snapshot


def _write_session(tmp_path: Path) -> Path:
    session = tmp_path / "20260515-111151-asyncio-vs-goroutines"
    session.mkdir()
    (session / "brief.md").write_text("# Async\n\nasyncio vs goroutines\n", encoding="utf-8")
    (session / "state.json").write_text(
        json.dumps(
            {
                "phase": "done",
                "drafter": None,
                "agreed_plan": None,
                "final_surfaced_disagreements": [],
                "draft_round": 0,
                "final_emitted_to": None,
            }
        ),
        encoding="utf-8",
    )
    (session / "metrics.json").write_text(
        json.dumps({"total_cost_usd": 0.05}), encoding="utf-8"
    )
    transcript = session / "transcript.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": "run_started",
                "session_dir": str(session),
                "slug": "asyncio-vs-goroutines",
                "model_tier": "test",
                "claude_model": "claude-haiku-4-5",
                "openai_model": "gpt-5-mini",
                "soft_cap": 3,
                "hard_cap": 5,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return session


def test_load_run_snapshot_succeeds_when_drafter_is_null_and_completed(tmp_path: Path):
    """The snapshot must materialise without raising; downstream JSON
    round-trip must succeed so the server can ship it to the frontend."""
    session = _write_session(tmp_path)
    run = load_run_snapshot(session)

    # drafter is allowed to be None on these historical runs.
    assert run.drafter is None
    # Round-trip the full Run through asdict (the same path the server
    # uses to emit JSON) — must not raise.
    payload = asdict(run)
    serialised = json.dumps(payload, default=str)
    # Sanity: drafter survives as null on the wire.
    assert '"drafter": null' in serialised
