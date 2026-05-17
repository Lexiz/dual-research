"""Spec 0043 — build_phase_ledger transition tests."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from dual_research.ledger import build_phase_ledger


def _seed_p1_claim_section(session_dir: Path, agent: str, body: str) -> None:
    p = session_dir / "phase1" / f"draft-{agent}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def _seed_p2(session_dir: Path, round_n: int, agent: str, body: str) -> None:
    p = session_dir / "phase2" / f"round-{round_n:02d}-{agent}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def _seed_p4(session_dir: Path, round_n: int, agent: str, body: str) -> None:
    p = session_dir / "phase4" / f"round-{round_n:02d}-{agent}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_phase1_claim_escalates_when_d_id_appears_in_p2_substantive(tmp_path: Path) -> None:
    """A claim raised in Phase 1 with a D-N suffix is escalated when
    the same D-N appears in any later Phase 2 round's
    ``## Substantive disagreements I'm holding`` section."""
    _seed_p1_claim_section(tmp_path, "claude", dedent("""
        ## 4. Claims I Expect the Other Agent Might Dispute

        1. **D-1** RLS isolation mechanism adequacy — concrete claim body.

        2. **D-2** Mutation testing requirement — concrete claim body.
    """).strip())
    _seed_p2(tmp_path, 1, "claude", "STATUS: NEGOTIATING\n")
    _seed_p2(tmp_path, 1, "openai", "STATUS: NEGOTIATING\n")
    _seed_p2(tmp_path, 2, "claude", dedent("""
        ## Substantive disagreements I'm holding

        - **D-1**: held position — status: open
          > quote: source
    """).strip())
    _seed_p2(tmp_path, 2, "openai", "STATUS: NEGOTIATING\n")

    ledger = build_phase_ledger(tmp_path, phase=2)
    by_id = {e.id: e for e in ledger.entries if e.kind == "claim"}
    # D-1 claim must be escalated; D-2 (no later mention) must stay open.
    cl1 = next((e for e in ledger.entries if e.kind == "claim" and "D-1" in e.body_snippet), None)
    cl2 = next((e for e in ledger.entries if e.kind == "claim" and "D-2" in e.body_snippet), None)
    assert cl1 is not None and cl1.current_status == "escalated"
    assert cl2 is not None and cl2.current_status == "open"


def test_claim_escalates_via_resolved_section_too(tmp_path: Path) -> None:
    """Spec 0043 D4 — a claim's D-N appearing in ``## Resolved or
    non-blocking differences`` also counts as a closure signal."""
    _seed_p1_claim_section(tmp_path, "claude", dedent("""
        ## 4. Claims I Expect the Other Agent Might Dispute

        1. **D-3** OWASP cryptographic posture — claim body.
    """).strip())
    _seed_p2(tmp_path, 1, "claude", "STATUS: NEGOTIATING\n")
    _seed_p2(tmp_path, 1, "openai", "STATUS: NEGOTIATING\n")
    _seed_p2(tmp_path, 2, "claude", dedent("""
        ## Resolved or non-blocking differences

        - D-3 (cryptographic posture): resolved — both agreed on AES-GCM.
    """).strip())
    _seed_p2(tmp_path, 2, "openai", "STATUS: NEGOTIATING\n")

    ledger = build_phase_ledger(tmp_path, phase=2)
    cl = next((e for e in ledger.entries if e.kind == "claim"), None)
    assert cl is not None
    assert cl.current_status == "escalated"
    # The transition's reason should reference the resolved-section path.
    closing = [t for t in cl.status_history if t.status == "escalated"]
    assert closing and "resolved-or-non-blocking" in closing[0].reason


def test_ghosted_rounds_accumulate_on_unaddressed_open_items(tmp_path: Path) -> None:
    """A claim that stays open across multiple rounds without an
    addressing signal accumulates ghosted_rounds equal to the number
    of rounds it persisted unaddressed."""
    _seed_p1_claim_section(tmp_path, "claude", dedent("""
        ## 4. Claims I Expect the Other Agent Might Dispute

        1. **D-9** consent cache invalidation — claim body.
    """).strip())
    _seed_p2(tmp_path, 1, "claude", "STATUS: NEGOTIATING\n")
    _seed_p2(tmp_path, 1, "openai", "STATUS: NEGOTIATING\n")
    _seed_p2(tmp_path, 2, "claude", "STATUS: NEGOTIATING\n")
    _seed_p2(tmp_path, 2, "openai", "STATUS: NEGOTIATING\n")
    _seed_p2(tmp_path, 3, "claude", "STATUS: NEGOTIATING\n")
    _seed_p2(tmp_path, 3, "openai", "STATUS: NEGOTIATING\n")

    ledger = build_phase_ledger(tmp_path, phase=2)
    cl = next(e for e in ledger.entries if e.kind == "claim")
    assert cl.current_status == "open"
    # Last round observed = 3; raised_round = 0; ghosted_rounds counts
    # rounds 1, 2, 3 — three rounds open with no addressing signal.
    assert cl.ghosted_rounds == 3


def test_phase4_issue_fixed_when_latest_marker_says_resolved(tmp_path: Path) -> None:
    """A Phase 4 issue raised in R1 by openai marked ``resolved`` in
    R2 flips to ``fixed`` in the ledger. (Mirrors the existing
    ``reconstruct_issues`` body-marker semantics from spec 0041 — the
    closure signal is the explicit ``resolved`` token in the latest
    round's ledger entry, NOT absence-from-section.)"""
    _seed_p4(tmp_path, 1, "openai", dedent("""
        STATUS: REVIEWING

        ## Issue ledger (delta + currently open)

        1. **OAI-1 — open — Issue body.** Detail.
    """).strip())
    _seed_p4(tmp_path, 2, "openai", dedent("""
        STATUS: APPROVED

        ## Issue ledger (delta + currently open)

        1. **OAI-1 — resolved — Issue body addressed.** Detail.
    """).strip())

    ledger = build_phase_ledger(tmp_path, phase=4)
    issues = [e for e in ledger.entries if e.kind == "issue"]
    assert len(issues) == 1
    assert issues[0].current_status == "fixed"


def test_phase4_comment_terminal_noted(tmp_path: Path) -> None:
    """Comments are terminal ``noted`` — no closure transitions ever."""
    _seed_p4(tmp_path, 1, "openai", dedent("""
        STATUS: REVIEWING

        ## Comments on the current draft

        1. Minor: phrasing in §2.4 could be tightened.
    """).strip())
    ledger = build_phase_ledger(tmp_path, phase=4)
    comments = [e for e in ledger.entries if e.kind == "comment"]
    assert len(comments) == 1
    assert comments[0].current_status == "noted"


def test_phase1_only_no_phase2_returns_seed_claims_with_no_ghosting(tmp_path: Path) -> None:
    """When a Phase 2 hasn't started yet, seed claims appear with
    status open and ghosted_rounds=0 (no rounds have passed)."""
    _seed_p1_claim_section(tmp_path, "claude", dedent("""
        ## 4. Claims I Expect the Other Agent Might Dispute

        1. First claim body.
    """).strip())
    ledger = build_phase_ledger(tmp_path, phase=2)
    cl = next((e for e in ledger.entries if e.kind == "claim"), None)
    assert cl is not None
    assert cl.current_status == "open"
    assert cl.ghosted_rounds == 0


def test_unknown_phase_returns_empty_state() -> None:
    """Phase != 2 and != 4 returns an empty LedgerState without error."""
    from pathlib import Path as _P
    s = build_phase_ledger(_P("/nonexistent"), phase=99)
    assert s.entries == []
