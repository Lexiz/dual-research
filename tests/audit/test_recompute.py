"""Spec 0039 — backfill tool tests.

Recompute is the one-shot fix for the partner-vetting class of bug:
prior runs that have an undercount in ``metrics.json`` because of the
resume overwrite, the 5m/1h mis-pricing, or the missing search-fee
fold-in. The tests pin the dedup-by-label behaviour, the idempotence,
the back-up-original behaviour, the per-call diff shape, and the
graceful path through old-shape transcripts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.audit.recompute import (
    BACKUP_SUFFIX,
    recompute_all,
    recompute_run,
)


def _seed(
    session_dir: Path,
    *,
    turn_events: list[dict],
    old_total: float = 0.0,
) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    transcript = session_dir / "transcript.jsonl"
    lines = []
    for ev in turn_events:
        lines.append(json.dumps({"event": "turn_ended", **ev}))
    transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")
    metrics = session_dir / "metrics.json"
    metrics.write_text(
        json.dumps({
            "started_at": "2026-05-16T03:50:00+00:00",
            "ended_at": "2026-05-16T04:00:00+00:00",
            "calls": [],
            "total_cost_usd": old_total,
        }),
        encoding="utf-8",
    )


def test_recompute_dedupes_duplicate_labels(tmp_path: Path) -> None:
    """A parse-error recovery emits the same label twice; the recompute
    tool keeps only the last occurrence (canonical attempt). The naive
    sum would double-count and overstate the total."""
    session = tmp_path / "run-1"
    _seed(
        session,
        turn_events=[
            {
                "agent": "claude", "phase": "phase4", "label": "phase4-r1-claude",
                "input_tokens": 1000, "output_tokens": 200,
                "cache_read_tokens": 0, "cache_write_tokens": 0,
                "model_id": "claude-sonnet-4-6", "duration_ms": 1500,
                "cost_usd": 0.99,   # failed attempt
                "searches": 0,
            },
            {
                "agent": "claude", "phase": "phase4", "label": "phase4-r1-claude",
                "input_tokens": 500, "output_tokens": 100,
                "cache_read_tokens": 0, "cache_write_tokens": 0,
                "model_id": "claude-sonnet-4-6", "duration_ms": 800,
                "cost_usd": 0.01,   # the wrong stale value — recompute repairs it
                "searches": 0,
            },
        ],
        old_total=999.0,
    )
    report = recompute_run(session, write=False)
    # Only one canonical turn is summed.
    assert len(report.diffs) == 1
    # 500 × $3 + 100 × $15 per Mtok = $0.0015 + $0.0015 = $0.003
    assert report.new_total == pytest.approx(0.003)


def test_recompute_partner_vetting_style_full_pricing(tmp_path: Path) -> None:
    """End-to-end exercise on a partner-vetting-shaped synthetic transcript:
    the recompute should price 1h cache writes at 2× input AND fold search
    fees in. The old metrics.json reports the (broken) 5m-only token cost
    with no search fees."""
    session = tmp_path / "run-2"
    _seed(
        session,
        turn_events=[
            {
                "agent": "claude", "phase": "phase2", "label": "phase2-r1-claude",
                "input_tokens": 0, "output_tokens": 0,
                "cache_read_tokens": 0, "cache_write_tokens": 1_000_000,
                "cache_write_5m_tokens": 0, "cache_write_1h_tokens": 1_000_000,
                "model_id": "claude-sonnet-4-6", "duration_ms": 1500,
                "cost_usd": 3.75,  # priced at 5m (the bug); should be 6.00
                "searches": 5,     # search fees were not folded in
            },
            {
                "agent": "openai", "phase": "phase2", "label": "phase2-r1-openai",
                "input_tokens": 0, "output_tokens": 0,
                "cache_read_tokens": 0, "cache_write_tokens": 0,
                "model_id": "gpt-5.5", "duration_ms": 1500,
                "cost_usd": 0.00,
                "searches": 4,     # 4 × $0.025 = $0.10
            },
        ],
        old_total=3.75,
    )
    report = recompute_run(session, write=True)
    # Claude: 1M tokens × $6/Mtok (1h tier) + 5 × $0.010 = $6.00 + $0.05 = $6.05
    # OpenAI: 0 token cost + 4 × $0.025 = $0.10
    # Total: $6.15
    assert report.new_total == pytest.approx(6.15)
    assert report.old_total == pytest.approx(3.75)
    assert report.delta == pytest.approx(2.40)
    assert report.backed_up is True
    assert report.metrics_written is True

    # Backup preserves the original.
    backup = session / f"metrics.json.{BACKUP_SUFFIX}"
    assert backup.exists()
    backed_up = json.loads(backup.read_text(encoding="utf-8"))
    assert backed_up["total_cost_usd"] == pytest.approx(3.75)

    # Rewritten metrics.json reflects the new total.
    fresh = json.loads((session / "metrics.json").read_text(encoding="utf-8"))
    assert fresh["total_cost_usd"] == pytest.approx(6.15)


def test_recompute_is_idempotent(tmp_path: Path) -> None:
    """Running the tool twice produces the same metrics.json and does
    NOT clobber the original backup."""
    session = tmp_path / "run-3"
    _seed(
        session,
        turn_events=[
            {
                "agent": "claude", "phase": "phase1", "label": "phase1-claude",
                "input_tokens": 1_000_000, "output_tokens": 0,
                "cache_read_tokens": 0, "cache_write_tokens": 0,
                "model_id": "claude-sonnet-4-6", "duration_ms": 1000,
                "cost_usd": 0.01, "searches": 0,
            },
        ],
        old_total=0.01,
    )
    first = recompute_run(session, write=True)
    # 1M input × $3 = $3.00
    assert first.new_total == pytest.approx(3.00)
    assert first.backed_up is True
    backup_mtime = (session / f"metrics.json.{BACKUP_SUFFIX}").stat().st_mtime
    fresh_first = (session / "metrics.json").read_text(encoding="utf-8")

    second = recompute_run(session, write=True)
    # Second run: still produces 3.00; the new "old" is what the first
    # write produced — so delta is 0.
    assert second.new_total == pytest.approx(3.00)
    assert second.old_total == pytest.approx(3.00)
    assert second.delta == pytest.approx(0.0)
    # Backup wasn't overwritten — original is preserved.
    assert (session / f"metrics.json.{BACKUP_SUFFIX}").stat().st_mtime == backup_mtime
    assert second.backed_up is False
    # metrics.json content is stable across re-runs.
    assert (session / "metrics.json").read_text(encoding="utf-8") == fresh_first


def test_recompute_all_walks_directory(tmp_path: Path) -> None:
    """``--all`` recomputes every run that has a transcript; non-run
    directories and runs without transcripts are skipped silently."""
    runs = tmp_path / "runs"
    runs.mkdir()
    # Run A: has transcript.
    _seed(
        runs / "run-A",
        turn_events=[{
            "agent": "claude", "phase": "phase1", "label": "phase1-claude",
            "input_tokens": 1_000_000, "output_tokens": 0,
            "cache_read_tokens": 0, "cache_write_tokens": 0,
            "model_id": "claude-sonnet-4-6", "duration_ms": 0,
            "cost_usd": 0.01, "searches": 0,
        }],
        old_total=0.01,
    )
    # Run B: also has transcript.
    _seed(
        runs / "run-B",
        turn_events=[{
            "agent": "openai", "phase": "phase1", "label": "phase1-openai",
            "input_tokens": 1_000_000, "output_tokens": 0,
            "cache_read_tokens": 0, "cache_write_tokens": 0,
            "model_id": "gpt-5.5", "duration_ms": 0,
            "cost_usd": 0.0, "searches": 0,
        }],
        old_total=0.0,
    )
    # Run C: stray dir with no transcript — should be skipped.
    (runs / "run-C").mkdir()

    reports = recompute_all(runs, write=False)
    run_ids = sorted(r.run_id for r in reports)
    assert run_ids == ["run-A", "run-B"]


def test_recompute_dry_run_does_not_write(tmp_path: Path) -> None:
    """``--dry-run`` reports the diff but leaves metrics.json untouched
    and no backup is created."""
    session = tmp_path / "run-dry"
    _seed(
        session,
        turn_events=[{
            "agent": "claude", "phase": "phase0", "label": "phase0-claude",
            "input_tokens": 1_000_000, "output_tokens": 0,
            "cache_read_tokens": 0, "cache_write_tokens": 0,
            "model_id": "claude-sonnet-4-6", "duration_ms": 0,
            "cost_usd": 0.01, "searches": 0,
        }],
        old_total=0.01,
    )
    pre_mtime = (session / "metrics.json").stat().st_mtime
    report = recompute_run(session, write=False)
    assert report.metrics_written is False
    assert report.backed_up is False
    # File unchanged.
    assert (session / "metrics.json").stat().st_mtime == pre_mtime
    assert not (session / f"metrics.json.{BACKUP_SUFFIX}").exists()
    # And the diff is still reported.
    assert report.new_total == pytest.approx(3.00)
    assert report.old_total == pytest.approx(0.01)
