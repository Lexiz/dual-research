"""Spec 0248 — write-time per-agent critique tally for the All Runs cards.

The All Runs provider bands surface, per agent, how many Questions /
Disagreements / Issues that agent **raised** and how many reached a
**solved** (terminal / resolved) state, plus total tokens and web
searches. The raised/solved counts require replaying the Phase 2/4 round
files — the exact work ``summarize_run`` deliberately avoids so the
3-second ``/api/runs`` poll stays cheap (spec 0248 §1).

The resolution: the orchestrator calls :func:`compute_critique_by_agent`
at run-write time and persists the result under ``metrics.json``'s
``critique_by_agent`` key. The list path (``derive_agent_breakdowns``)
then only *reads* the persisted tally — never recomputes it.

Heavy imports (item pipeline, reconstructors) are done lazily inside the
function so importing this module from the orchestrator stays cheap and
cannot introduce an import cycle.
"""

from __future__ import annotations

from pathlib import Path

# Backend → wire keys. The tally is persisted under the backend agent
# names ("claude" / "openai") so it lines up with ``totals_by_agent``.
_UI_TO_BACKEND = {"claude": "claude", "gpt": "openai"}
# Spec 0252 — Comments is the 4th category (canonical order Q→D→I→C, DS §9.3).
_CATEGORIES = ("questions", "disagreements", "issues", "comments")


def _empty_agent() -> dict:
    return {
        "tokens": 0,
        "searches": 0,
        "questions": [0, 0],
        "disagreements": [0, 0],
        "issues": [0, 0],
        # Spec 0252 — Comments have no closure protocol (no ``status`` field),
        # so the "solved" half is structurally always 0; the band renders this
        # as a single idle-toned count (DS §9.3 C=idle).
        "comments": [0, 0],
    }


def _typed_lists(session_dir: Path):
    """(questions, disagreements, issues, comments) — item-pipeline first.

    Mirrors ``aggregator.build_run_detail``: the spec-0114 item pipeline is
    canonical for current (v2) runs — the legacy ``reconstruct_*`` parsers
    return ``[]`` for them. Fall back to the legacy parsers only when the
    item pipeline yields nothing (genuinely pre-0114 runs).

    Spec 0252 — returns a 4-tuple; ``comments`` comes from
    ``project_typed_lists`` for v2 runs and from ``reconstruct_comments``
    (phase 2 + phase 4) for the pre-0114 legacy fallback.
    """
    from dual_research.ui.items import (
        aggregate_items_from_transcript,
        build_session_audit_lookup,
    )

    transcript_path = session_dir / "transcript.jsonl"
    audit_lookup = build_session_audit_lookup(session_dir)
    bundle = aggregate_items_from_transcript(transcript_path, audit_lookup=audit_lookup)
    if not bundle.items:
        from dual_research.ledger.replay import replay_items_from_disk

        bundle = replay_items_from_disk(session_dir, audit_lookup=audit_lookup)

    if bundle.items:
        from dual_research.ui.item_projection import project_typed_lists

        questions, disagreements, issues, comments = project_typed_lists(bundle)
        return questions, disagreements, issues, comments

    # Legacy fallback (pre-0114 runs).
    from dual_research.ui.comments import reconstruct_comments
    from dual_research.ui.disagreements import reconstruct
    from dual_research.ui.issues import reconstruct_issues
    from dual_research.ui.questions import reconstruct_questions

    questions = reconstruct_questions(session_dir, phase=2) + reconstruct_questions(
        session_dir, phase=4
    )
    disagreements = reconstruct(session_dir, phase=2) + reconstruct(session_dir, phase=4)
    issues = reconstruct_issues(session_dir, phase=2) + reconstruct_issues(
        session_dir, phase=4
    )
    comments = reconstruct_comments(session_dir, phase=2) + reconstruct_comments(
        session_dir, phase=4
    )
    return questions, disagreements, issues, comments


def _tally_into(out: dict, category: str, items) -> None:
    """Add (raised, solved) for ``items`` into ``out`` under ``category``.

    ``raised_by`` is a UI agent label ("claude" / "gpt"); an item is
    *solved* once it leaves the ``open`` state (answered question, resolved
    disagreement, resolved issue — all share the ``status != "open"`` rule).
    """
    for it in items:
        backend = _UI_TO_BACKEND.get(getattr(it, "raised_by", ""), None)
        if backend is None:
            continue
        bucket = out.setdefault(backend, _empty_agent())
        pair = bucket[category]
        pair[0] += 1
        if getattr(it, "status", "open") != "open":
            pair[1] += 1


def compute_critique_by_agent(
    session_dir: Path, totals_by_agent: dict | None = None
) -> dict:
    """Per-agent {tokens, searches, questions, disagreements, issues} tally.

    Heavy: replays the run's items once. Call from the run-write path, not
    the list path. Never raises — any parse failure yields ``{}`` so a
    tally miss can never block the metrics save it rides alongside.
    """
    out: dict = {}
    try:
        questions, disagreements, issues, comments = _typed_lists(session_dir)
        _tally_into(out, "questions", questions)
        _tally_into(out, "disagreements", disagreements)
        _tally_into(out, "issues", issues)
        # Spec 0252 — Comment has no ``status`` attr, so ``_tally_into``
        # leaves the solved half at 0 (getattr default "open").
        _tally_into(out, "comments", comments)
    except Exception:
        # The tally is best-effort decoration on the cards; on any failure
        # we persist nothing rather than risk the metrics write.
        return {}

    # Fold in the cheap token + search totals (already aggregated upstream).
    tba = totals_by_agent or {}
    for backend in ("claude", "openai"):
        a = tba.get(backend)
        if not a:
            continue
        bucket = out.setdefault(backend, _empty_agent())
        bucket["tokens"] = int(
            (a.get("input_tokens", 0) or 0)
            + (a.get("output_tokens", 0) or 0)
            + (a.get("cache_read_tokens", 0) or 0)
            + (a.get("cache_write_tokens", 0) or 0)
        )
        bucket["searches"] = int(a.get("searches", 0) or 0)

    return out
