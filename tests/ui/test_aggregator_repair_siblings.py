"""Per-turn key derivation for protocol-repair siblings — spec 0047.

A repair sibling (``-repair`` / ``-hashdrift-repair``) is a real extra
LLM call billed separately by the provider. The aggregator must:

1. Derive a distinct per-turn key (``..._repair``) for the sibling so
   the Consumption tab can render it as its own card alongside the
   original.
2. Still accumulate both events into the agent-level rollup
   (``state.tokens.*`` / ``state.cost``) so totals match the billing
   aggregate.

Mirrors the convention already established by ``_on_turn_inputs`` and
``_on_turn_searches`` (which write per-turn input + search-audit stubs
under the same ``..._repair`` key).
"""

from __future__ import annotations

from pathlib import Path

from dual_research.ui.aggregator import apply_event
from dual_research.ui.models import Run


def _empty_run() -> Run:
    return Run(id="r-1", display_id="abcd")


def _run_started() -> dict:
    return {
        "event": "run_started",
        "claude_model_id": "claude-sonnet-4-6",
        "openai_model_id": "gpt-5.5-2026-04-23",
    }


def _turn_ended(
    *,
    agent: str,
    phase: str,
    label: str,
    in_tokens: int = 100,
    out_tokens: int = 200,
    cost: float = 0.01,
    model_id: str = "claude-sonnet-4-6",
) -> dict:
    return {
        "event": "turn_ended",
        "agent": agent,
        "phase": phase,
        "label": label,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "cost_usd": cost,
        "duration_ms": 1000,
        "finish_reason": "end_turn",
        "model_id": model_id,
        "prompt_pieces": {},
    }


class TestRepairSiblingKeys:
    def test_phase4_repair_sibling_gets_distinct_key(self, tmp_path: Path) -> None:
        """The original ``phase4-r1-claude`` and its ``phase4-r1-claude-repair``
        sibling produce two distinct ``phase_token_usage`` entries."""
        run = _empty_run()
        apply_event(run, _run_started(), tmp_path)
        apply_event(
            run,
            _turn_ended(
                agent="claude", phase="phase4", label="phase4-r1-claude",
                in_tokens=15_000, out_tokens=4_000, cost=0.10,
            ),
            tmp_path,
        )
        apply_event(
            run,
            _turn_ended(
                agent="claude", phase="phase4", label="phase4-r1-claude-repair",
                in_tokens=20_000, out_tokens=6_000, cost=0.15,
            ),
            tmp_path,
        )
        assert "phase4_round1_claude" in run.phase_token_usage
        assert "phase4_round1_claude_repair" in run.phase_token_usage

        original = run.phase_token_usage["phase4_round1_claude"]
        repair = run.phase_token_usage["phase4_round1_claude_repair"]
        assert original.in_ == 15_000
        assert original.out == 4_000
        assert original.cost == 0.10
        assert repair.in_ == 20_000
        assert repair.out == 6_000
        assert repair.cost == 0.15

    def test_phase2_hashdrift_repair_uses_same_suffix(self, tmp_path: Path) -> None:
        """``-hashdrift-repair`` siblings (Phase 2 recovery flow) share the same
        ``_repair`` suffix convention as protocol-parse repairs."""
        run = _empty_run()
        apply_event(run, _run_started(), tmp_path)
        apply_event(
            run,
            _turn_ended(
                agent="openai", phase="phase2", label="phase2-r4-gpt",
                model_id="gpt-5.5-2026-04-23",
            ),
            tmp_path,
        )
        apply_event(
            run,
            _turn_ended(
                agent="openai", phase="phase2", label="phase2-r4-gpt-hashdrift-repair",
                model_id="gpt-5.5-2026-04-23",
            ),
            tmp_path,
        )
        assert "phase2_round4_gpt" in run.phase_token_usage
        assert "phase2_round4_gpt_repair" in run.phase_token_usage

    def test_agent_rollup_sums_original_plus_repair(self, tmp_path: Path) -> None:
        """The per-agent ``tokens`` + ``cost`` rollup must include BOTH the
        original and the repair sibling (matches the billing aggregate)."""
        run = _empty_run()
        apply_event(run, _run_started(), tmp_path)
        apply_event(
            run,
            _turn_ended(
                agent="claude", phase="phase4", label="phase4-r1-claude",
                in_tokens=15_000, out_tokens=4_000, cost=0.10,
            ),
            tmp_path,
        )
        apply_event(
            run,
            _turn_ended(
                agent="claude", phase="phase4", label="phase4-r1-claude-repair",
                in_tokens=20_000, out_tokens=6_000, cost=0.15,
            ),
            tmp_path,
        )
        claude = run.agents["claude"]
        assert claude.tokens.in_ == 35_000
        assert claude.tokens.out == 10_000
        assert abs(claude.cost - 0.25) < 1e-9

    def test_regular_turn_keeps_unsuffixed_key(self, tmp_path: Path) -> None:
        """Sanity: a plain (non-repair) turn still keys to
        ``phase{N}_round{R}_{agent}`` with no suffix."""
        run = _empty_run()
        apply_event(run, _run_started(), tmp_path)
        apply_event(
            run,
            _turn_ended(agent="claude", phase="phase4", label="phase4-r2-claude"),
            tmp_path,
        )
        assert "phase4_round2_claude" in run.phase_token_usage
        assert "phase4_round2_claude_repair" not in run.phase_token_usage
