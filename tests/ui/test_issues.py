"""Spec 0041 — first-class Issue reconstruction tests."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from dual_research.ui.issues import reconstruct_issues


def _seed(phase_dir: Path, round_n: int, agent: str, body: str) -> Path:
    rr = f"{round_n:02d}"
    path = phase_dir / f"round-{rr}-{agent}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_phase4_issue_open_then_resolved_marker_wins(tmp_path: Path) -> None:
    """An issue opened in round 1 and re-stated as ``resolved`` in
    round 2 reads as ``resolved`` — the latest-round marker is the
    canonical status. (Pre-spec 0041 the reconstructor used a
    cross-round positional-match heuristic that read everything as
    open; the spec replaces that with a body-marker read.)"""
    _seed(tmp_path / "phase4", 1, "openai", dedent("""
        STATUS: REVIEWING

        ## Issue ledger (delta + currently open)

        1. **OAI-1 — open — Claim-level [V]/[U] source tagging is missing.** Body...
    """).strip())
    _seed(tmp_path / "phase4", 2, "openai", dedent("""
        STATUS: APPROVED

        ## Issue ledger (delta + currently open)

        1. **OAI-1 — resolved — Claim-level [V]/[U] tagging is now sufficient.** Body...
    """).strip())

    issues = reconstruct_issues(tmp_path, phase=4)
    assert len(issues) == 1
    assert issues[0].status == "resolved"
    assert issues[0].round_first_seen == 1
    assert issues[0].round_last_seen == 2
    assert issues[0].raised_by == "gpt"


def test_phase4_claude_style_bold_heading_ledger(tmp_path: Path) -> None:
    """Claude's Issue ledger uses ``**C-1** — open — body`` heading
    style (bold-prefixed, no numbered list). The parser must recognise
    it; pre-spec 0041 it only matched numbered entries and missed
    these entirely."""
    _seed(tmp_path / "phase4", 1, "claude", dedent("""
        STATUS: REVIEWING

        ## Issue ledger (delta + currently open)

        **C-1** — `open` — Mutation testing gate lacks a concrete enforcement mechanism

        The draft names threshold targets but does not specify which tool enforces it.

        **C-2** — `open` — Critical core / generated shell split is structurally undefined

        The draft asserts this must be enforced structurally but does not specify the mechanism.
    """).strip())
    _seed(tmp_path / "phase4", 2, "claude", dedent("""
        STATUS: REVIEWING

        ## Issue ledger (delta + currently open)

        **C-1** — `resolved` — Mutation testing gate tool family named.

        **C-2** — `resolved` — Critical core / generated shell split enforcement mechanism specified.
    """).strip())

    issues = reconstruct_issues(tmp_path, phase=4)
    assert len(issues) == 2
    assert all(i.status == "resolved" for i in issues)
    assert sorted(i.id for i in issues) == ["I-c-r1-01", "I-c-r1-02"]


def test_non_blocking_marker_treated_as_resolved(tmp_path: Path) -> None:
    """``**D-5** — \\`open\\` (non-blocking, Phase 2 FSD) — ...`` carries
    BOTH the ``open`` and ``non-blocking`` tokens. The protocol's
    ``OPEN_ISSUES: N`` end-of-turn counter doesn't count non-blocking
    carry-overs; the reconstructor matches that semantics."""
    _seed(tmp_path / "phase4", 1, "claude", dedent("""
        STATUS: APPROVED

        ## Issue ledger (delta + currently open)

        **D-5** — `open` (non-blocking, Phase 2 FSD) — MCP-only public programmatic surface.
    """).strip())
    issues = reconstruct_issues(tmp_path, phase=4)
    assert len(issues) == 1
    assert issues[0].status == "resolved"


def test_no_issue_ledger_returns_empty(tmp_path: Path) -> None:
    _seed(tmp_path / "phase4", 1, "claude", dedent("""
        STATUS: REVIEWING

        ## Open questions for openai

        1. A question, not an issue.
    """).strip())
    assert reconstruct_issues(tmp_path, phase=4) == []


def test_phase4_id_token_dedup_across_rewordings(tmp_path: Path) -> None:
    """The leading ``ID-N`` token is stable across rounds even when
    the body wording changes substantially (resolved → resolved
    different phrasing). The dedup signature catches it."""
    _seed(tmp_path / "phase4", 1, "openai", dedent("""
        STATUS: REVIEWING

        ## Issue ledger (delta + currently open)

        1. **OAI-2 — open — The RLS referential-integrity invariant is factually wrong.** Body.
    """).strip())
    _seed(tmp_path / "phase4", 2, "openai", dedent("""
        STATUS: APPROVED

        ## Issue ledger (delta + currently open)

        1. **OAI-2 / D-OAI-1 — resolved — RLS referential-integrity mechanism is now correctly framed.** Body.
    """).strip())

    issues = reconstruct_issues(tmp_path, phase=4)
    assert len(issues) == 1
    assert issues[0].status == "resolved"
    assert issues[0].round_first_seen == 1
    assert issues[0].round_last_seen == 2
