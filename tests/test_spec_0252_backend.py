"""Spec 0252 — backend: Comments category in the tally + backfill CLI.

Exercises the real entry points:
  * ``critique_tally.compute_critique_by_agent`` (and the ``_typed_lists``
    4-tuple) — the write-time path that now tallies a 4th ``comments``
    category (single count; no closure protocol, so solved half == 0).
  * ``aggregator.derive_agent_breakdowns`` — the cheap read path now
    surfaces ``comments``.
  * ``audit.backfill_critique.backfill_critique_run`` — the new
    maintenance command that repairs pre-0248 runs whose ``metrics.json``
    carries an empty ``critique_by_agent``.
"""

from __future__ import annotations

import json
from pathlib import Path

from dual_research.persistence.metrics import CallRecord, Metrics


def _write_fixture_run(root: Path) -> None:
    """A minimal v2 session dir: a transcript with item_raised events
    across all four categories (including a comment) for two agents."""
    events = [
        {"event": "item_raised", "id": "Q1", "item_kind": "question",
         "phase": 2, "round": 1, "raiser": "claude", "body": "q1"},
        {"event": "item_raised", "id": "D1", "item_kind": "disagreement",
         "phase": 2, "round": 1, "raiser": "claude", "body": "d1"},
        {"event": "item_raised", "id": "I1", "item_kind": "issue",
         "phase": 4, "round": 1, "raiser": "openai", "body": "i1"},
        # Two comments by Claude, one by OpenAI — the new 4th category.
        {"event": "item_raised", "id": "C1", "item_kind": "comment",
         "phase": 4, "round": 1, "raiser": "claude", "body": "c1"},
        {"event": "item_raised", "id": "C2", "item_kind": "comment",
         "phase": 4, "round": 1, "raiser": "claude", "body": "c2"},
        {"event": "item_raised", "id": "C3", "item_kind": "comment",
         "phase": 4, "round": 1, "raiser": "openai", "body": "c3"},
    ]
    root.mkdir(parents=True, exist_ok=True)
    (root / "transcript.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )


def test_typed_lists_returns_four_tuple(tmp_path: Path) -> None:
    from dual_research.ui.critique_tally import _typed_lists

    root = tmp_path / "20260528-000000-fixture"
    _write_fixture_run(root)
    result = _typed_lists(root)
    assert len(result) == 4, "spec 0252: _typed_lists must return a 4-tuple (incl. comments)"
    questions, disagreements, issues, comments = result
    assert len(comments) == 3, "two Claude + one OpenAI comment"


def test_compute_critique_by_agent_includes_comments(tmp_path: Path) -> None:
    from dual_research.ui.critique_tally import compute_critique_by_agent

    root = tmp_path / "20260528-000000-fixture"
    _write_fixture_run(root)
    out = compute_critique_by_agent(root, totals_by_agent={})

    # Comments: single count — raised half populated, solved half always 0.
    assert out["claude"]["comments"] == [2, 0]
    assert out["openai"]["comments"] == [1, 0]
    # The other three categories are unaffected.
    assert out["claude"]["questions"] == [1, 0]
    assert out["claude"]["disagreements"] == [1, 0]
    assert out["openai"]["issues"] == [1, 0]


def test_derive_agent_breakdowns_surfaces_comments() -> None:
    from dual_research.ui.aggregator import derive_agent_breakdowns

    metrics = {
        "totals_by_agent": {
            "claude": {"cost_usd": 1.0, "search_cost": 0.0, "searches": 0,
                       "input_tokens": 100, "output_tokens": 50,
                       "cache_read_tokens": 0, "cache_write_tokens": 0},
        },
        "critique_by_agent": {
            "claude": {"tokens": 150, "searches": 0,
                       "questions": [4, 2], "disagreements": [1, 1],
                       "issues": [0, 0], "comments": [3, 0]},
        },
    }
    out = derive_agent_breakdowns(metrics)
    assert out["a"].critique["comments"] == (3, 0)


def _seed_metrics(root: Path) -> Path:
    """Write a metrics.json with calls but an EMPTY critique_by_agent —
    the shape a pre-0248 run carries on disk."""
    m = Metrics()
    m.calls.append(CallRecord(
        label="phase2_claude", agent="claude", model_id="claude-x",
        input_tokens=100, output_tokens=50,
        cache_read_tokens=0, cache_write_tokens=0,
        cost_usd=1.0, duration_ms=0,
    ))
    m.critique_by_agent = {}  # pre-0248: never computed
    path = root / "metrics.json"
    m.save(path)
    return path


def test_backfill_critique_run_repairs_metrics(tmp_path: Path) -> None:
    from dual_research.audit.backfill_critique import backfill_critique_run

    root = tmp_path / "20260528-000000-fixture"
    _write_fixture_run(root)
    metrics_path = _seed_metrics(root)

    report = backfill_critique_run(root, write=True)
    assert report.before_nonempty is False
    assert report.after_nonempty is True
    assert report.metrics_written is True

    # metrics.json is rewritten with a non-empty critique_by_agent whose
    # comments pair is [N, 0] for an agent that raised N comments.
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    cba = payload["critique_by_agent"]
    assert cba["claude"]["comments"] == [2, 0]
    assert cba["openai"]["comments"] == [1, 0]


def test_backfill_dry_run_writes_nothing(tmp_path: Path) -> None:
    from dual_research.audit.backfill_critique import backfill_critique_run

    root = tmp_path / "20260528-000000-fixture"
    _write_fixture_run(root)
    metrics_path = _seed_metrics(root)
    before = metrics_path.read_text(encoding="utf-8")

    report = backfill_critique_run(root, write=False)
    assert report.after_nonempty is True   # would-write tally is computed
    assert report.metrics_written is False
    # File is byte-for-byte unchanged.
    assert metrics_path.read_text(encoding="utf-8") == before
