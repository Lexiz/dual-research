"""Spec 0089 + 0090 replay tests — pin behaviour against real
production-derived turn pairs from the 2c4f deadlock.

These fixtures are checked-in copies of two of the round-04 turn
files from `20260518-065852-backend-language-choice-briefing-for-
dual-research` (run id `2c4f`), where Phase 2 hard-capped at 12
rounds despite mutual AGREED from r3 onward.

**Important spec-0090 update to the test interpretation:** pre-spec
0090, `parse_turn`'s ``extract_fenced_section`` truncated AGREED_PLAN
bodies at the first ``##`` heading inside the ```` ```markdown ```` fence,
leaving both agents' ``agreed_plan`` field as just ```` ```markdown ````
(the fence opener). That made their plan hashes trivially equal,
which made the stuck-AGREED *signature* (`lenient=True, strict=False
with ledger > 0`) appear at r4 — but the underlying agreement was
illusory. Post-spec-0090, the parser now sees both agents' full
plan bodies, which differ in content (~4 diff hunks of paraphrased
content). So the stuck-AGREED signature no longer fires on 2c4f r4
— the agents really weren't aligned and the spec-0032 hash-drift
path is the correct escape.

The remaining regression we DO want to pin from 2c4f r4:
  - § A canonical-FSD detection helper: must NOT misfire when the
    agents emit a canonical sub-section correctly.
  - `is_plan_agreed` correctly REJECTS 2c4f r4 once parse-fence bug
    is fixed (this used to incorrectly pass without a ledger block).
"""

from __future__ import annotations

from pathlib import Path

from dual_research.protocol.convergence import (
    all_substantive_gates_pass_except_canonical_fsd,
    all_substantive_gates_pass_except_plan_hash,
    is_plan_agreed,
    is_plan_agreed_lenient,
)


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "spec0089"


def _read(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


class TestReplay2c4fRound04:
    """The 2c4f case at round 4 — first round both agents emitted full
    AGREED turns. Post-spec-0090 we see the agents weren't actually
    aligned; the apparent alignment was a parse-bug artifact."""

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

    def test_strict_blocks_with_ledger_open_items(self) -> None:
        """The real 2c4f ledger reported 17 open items at this round.
        Strict convergence rejects (both due to ledger AND, post-spec-
        0090, the genuine plan-hash mismatch)."""
        assert not is_plan_agreed(
            self.claude, self.openai, ledger_open_count=17,
        )

    def test_strict_blocks_even_without_ledger(self) -> None:
        """Post-spec-0090 reality check: the agents' AGREED_PLAN bodies
        are NOT byte-equivalent — paraphrased content across ~4 sections
        — so strict convergence correctly rejects even with no ledger
        block. Pre-spec-0090 this incorrectly returned True because
        parse_turn truncated both plans to the same fence opener.

        This is a genuine plan disagreement that the spec-0032 hash-
        drift path is designed to handle (force-verbatim-copy repair,
        then canonical promotion)."""
        assert not is_plan_agreed(
            self.claude, self.openai, ledger_open_count=0,
        )
        assert not is_plan_agreed(
            self.claude, self.openai, ledger_open_count=None,
        )

    def test_lenient_rejects_genuine_disagreement(self) -> None:
        """Lenient also rejects because the hash mismatch is real, not
        a ledger artifact. Confirms spec-0089 § B's stuck-AGREED escape
        valve correctly does NOT fire on 2c4f — that path is for cases
        where agents genuinely agree but the ledger over-blocks, not
        cases like this one where agents merely *think* they agree."""
        assert not is_plan_agreed_lenient(self.claude, self.openai)

    def test_hash_drift_path_correctly_detects(self) -> None:
        """The right escape for 2c4f r4 is the spec-0032 hash-drift
        path: drafters match (both 'claude'), every other surface
        signal aligns, only the plan hash differs. The orchestrator
        would fire force-verbatim-copy repair on round 4 instead of
        looping."""
        drift = all_substantive_gates_pass_except_plan_hash(
            self.claude, self.openai
        )
        assert drift.detected
        assert drift.drafter == "claude"
        assert drift.other_agent == "gpt"
        assert drift.canonical_hash != drift.other_hash
