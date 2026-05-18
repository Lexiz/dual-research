"""Spec 0089 replay tests — pin the escape behaviour against real
production-derived turn pairs from the 2c4f deadlock.

These fixtures are checked-in copies of two of the round-04 turn
files from `20260518-065852-backend-language-choice-briefing-for-
dual-research` (run id `2c4f`), where Phase 2 hard-capped at 12
rounds despite mutual AGREED from r3 onward.

The escape paths in spec 0089 should:
  - § A canonical-FSD synthesis: not fire on 2c4f (the agents DID emit
    the canonical sub-section correctly — the failure was elsewhere).
    But the test file is the most faithful regression we have for
    "well-formed AGREED + FSD>0 turn" so it must still pass through
    the helpers without raising.
  - § B stuck-AGREED escape valve: fires on 2c4f when run for two
    consecutive rounds because `is_plan_agreed_lenient` returns True
    but `is_plan_agreed(..., ledger_open_count=17)` returns False.

The 27de r04/r05 files are also pulled but exercise the spec-0032
hash-drift path, which spec 0089 leaves unchanged.
"""

from __future__ import annotations

from pathlib import Path

from dual_research.protocol.convergence import (
    all_substantive_gates_pass_except_canonical_fsd,
    is_plan_agreed,
    is_plan_agreed_lenient,
)


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "spec0089"


def _read(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


class TestReplay2c4fRound04:
    """The 2c4f deadlock case at round 4 — first round where both agents
    cleanly emitted AGREED + matching plan + matching FSD canonical."""

    def setup_method(self) -> None:
        self.claude = _read("2c4f-r04-claude.md")
        self.openai = _read("2c4f-r04-openai.md")

    def test_canonical_fsd_escape_does_not_misfire(self) -> None:
        """Agents emitted the canonical sub-section correctly, so the
        § A escape MUST NOT fire (otherwise we'd be 'synthesising' over
        a perfectly good canonical block)."""
        gap = all_substantive_gates_pass_except_canonical_fsd(
            self.claude, self.openai
        )
        assert not gap.detected

    def test_lenient_passes(self) -> None:
        """Both agents are aligned on protocol surface signals → lenient
        check passes."""
        assert is_plan_agreed_lenient(self.claude, self.openai)

    def test_strict_blocks_with_ledger_open_items(self) -> None:
        """The real 2c4f ledger reported 17 open items at this round
        (12 questions + 5 claims). The ledger cross-check blocks strict
        convergence — this is the exact bug spec 0089 § B exists to
        address."""
        assert not is_plan_agreed(
            self.claude, self.openai, ledger_open_count=17,
        )

    def test_strict_passes_without_ledger_block(self) -> None:
        """Sanity: without the ledger cross-check the strict path is
        also happy. (This is the only signal that distinguishes 'really
        stuck' from 'orchestrator over-cautious'.)"""
        assert is_plan_agreed(
            self.claude, self.openai, ledger_open_count=0,
        )
        assert is_plan_agreed(
            self.claude, self.openai, ledger_open_count=None,
        )

    def test_stuck_agreed_signature(self) -> None:
        """Composite: lenient True + strict False = the stuck-AGREED
        signature the § B escape valve counts. Two consecutive rounds
        of this composite (`STUCK_AGREED_K = 2`) trigger promotion."""
        strict = is_plan_agreed(
            self.claude, self.openai, ledger_open_count=17,
        )
        lenient = is_plan_agreed_lenient(self.claude, self.openai)
        assert lenient and not strict
