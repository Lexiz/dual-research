"""Per-turn token-usage capture in the aggregator — spec 0029.

After each ``TurnEnded`` event the aggregator preserves the per-turn
token + cost detail on ``Run.phase_token_usage``, keyed the same way as
``phase_summaries`` and ``phase_review_items``:

  - phase 0, 1, 3 (single-shot): ``phase{N}_<agent>``
  - phase 2, 4 (round-loop):    ``phase{N}_round{R}_<agent>``

The pre-0029 accumulation onto ``AgentState.tokens`` and ``cost`` is
preserved — the run-total chips in the timeline toolbar keep working.
"""

from __future__ import annotations

from pathlib import Path

from dual_research.ui.aggregator import apply_event
from dual_research.ui.models import Run, TurnTokenUsage


def _empty_run() -> Run:
    return Run(id="r-1", display_id="abcd")


def _turn_ended(
    *,
    agent: str,
    phase: str,
    label: str,
    in_tokens: int = 100,
    out_tokens: int = 200,
    cache_read: int = 0,
    cache_write: int = 0,
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
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
        "cost_usd": cost,
        "duration_ms": 1000,
        "finish_reason": "end_turn",
        "model_id": model_id,
    }


class TestPhaseTokenUsageKeys:
    def test_phase0_keyed_per_agent(self, tmp_path: Path) -> None:
        run = _empty_run()
        apply_event(
            run,
            _turn_ended(agent="claude", phase="phase0", label="phase0-claude"),
            tmp_path,
        )
        apply_event(
            run,
            _turn_ended(
                agent="openai",
                phase="phase0",
                label="phase0-openai",
                model_id="gpt-5.5",
            ),
            tmp_path,
        )
        assert set(run.phase_token_usage.keys()) == {"phase0_claude", "phase0_gpt"}

    def test_phase1_keyed_per_agent(self, tmp_path: Path) -> None:
        run = _empty_run()
        apply_event(
            run,
            _turn_ended(agent="claude", phase="phase1", label="phase1-claude"),
            tmp_path,
        )
        assert "phase1_claude" in run.phase_token_usage
        assert "phase1_gpt" not in run.phase_token_usage

    def test_phase2_keyed_per_round_per_agent(self, tmp_path: Path) -> None:
        run = _empty_run()
        # Round 1 — both agents.
        apply_event(
            run,
            _turn_ended(
                agent="claude", phase="phase2", label="phase2-claude-round-1"
            ),
            tmp_path,
        )
        apply_event(
            run,
            _turn_ended(
                agent="openai",
                phase="phase2",
                label="phase2-openai-round-1",
                model_id="gpt-5.5",
            ),
            tmp_path,
        )
        # Round 3 — both agents (skipping 2 to prove keys are independent).
        apply_event(
            run,
            _turn_ended(
                agent="claude",
                phase="phase2",
                label="phase2-claude-round-3",
                in_tokens=5_000,
            ),
            tmp_path,
        )
        apply_event(
            run,
            _turn_ended(
                agent="openai",
                phase="phase2",
                label="phase2-openai-round-3",
                model_id="gpt-5.5",
                in_tokens=4_800,
            ),
            tmp_path,
        )
        assert set(run.phase_token_usage.keys()) == {
            "phase2_round1_claude",
            "phase2_round1_gpt",
            "phase2_round3_claude",
            "phase2_round3_gpt",
        }
        # Round 3 input is larger than round 1 input — exactly the
        # buildup the Consumption tab visualises.
        assert (
            run.phase_token_usage["phase2_round3_claude"].in_
            > run.phase_token_usage["phase2_round1_claude"].in_
        )

    def test_phase3_keyed_per_agent_drafter_only(self, tmp_path: Path) -> None:
        run = _empty_run()
        apply_event(
            run,
            _turn_ended(agent="claude", phase="phase3", label="phase3-claude"),
            tmp_path,
        )
        # Only one entry — the drafter. Non-drafter never gets a turn_ended.
        assert run.phase_token_usage == {
            "phase3_claude": run.phase_token_usage["phase3_claude"]
        }

    def test_phase4_keyed_per_round_per_agent(self, tmp_path: Path) -> None:
        run = _empty_run()
        apply_event(
            run,
            _turn_ended(
                agent="openai",
                phase="phase4",
                label="phase4-openai-round-2",
                model_id="gpt-5.5",
            ),
            tmp_path,
        )
        assert "phase4_round2_gpt" in run.phase_token_usage


class TestPhaseTokenUsagePayload:
    def test_records_all_token_fields(self, tmp_path: Path) -> None:
        run = _empty_run()
        apply_event(
            run,
            _turn_ended(
                agent="claude",
                phase="phase2",
                label="phase2-claude-round-1",
                in_tokens=1234,
                out_tokens=567,
                cache_read=300,
                cache_write=80,
                cost=0.42,
                model_id="claude-sonnet-4-6",
            ),
            tmp_path,
        )
        usage = run.phase_token_usage["phase2_round1_claude"]
        assert isinstance(usage, TurnTokenUsage)
        assert usage.in_ == 1234
        assert usage.out == 567
        assert usage.cache_read == 300
        assert usage.cache_write == 80
        assert usage.cost == 0.42
        assert usage.model_id == "claude-sonnet-4-6"

    def test_model_id_falls_back_to_agent_state(self, tmp_path: Path) -> None:
        """If the event lacks model_id, fall back to whatever was set on
        the agent at run_started time. Pre-0029 transcripts may omit it."""
        run = _empty_run()
        apply_event(
            run,
            {
                "event": "run_started",
                "soft_cap": 4,
                "hard_cap": 8,
                "claude_model": "claude-sonnet-4-6",
                "openai_model": "gpt-5.5",
            },
            tmp_path,
        )
        event = _turn_ended(
            agent="claude", phase="phase1", label="phase1-claude"
        )
        event.pop("model_id")
        apply_event(run, event, tmp_path)
        usage = run.phase_token_usage["phase1_claude"]
        assert usage.model_id == "claude-sonnet-4-6"


class TestAccumulationPreserved:
    """Existing per-agent totals must keep working (timeline toolbar chips)."""

    def test_run_totals_still_accumulate(self, tmp_path: Path) -> None:
        run = _empty_run()
        apply_event(
            run,
            _turn_ended(
                agent="claude",
                phase="phase2",
                label="phase2-claude-round-1",
                in_tokens=100,
                out_tokens=200,
                cost=0.01,
            ),
            tmp_path,
        )
        apply_event(
            run,
            _turn_ended(
                agent="claude",
                phase="phase2",
                label="phase2-claude-round-2",
                in_tokens=300,
                out_tokens=400,
                cost=0.03,
            ),
            tmp_path,
        )
        assert run.agents["claude"].tokens.in_ == 400
        assert run.agents["claude"].tokens.out == 600
        assert abs(run.agents["claude"].cost - 0.04) < 1e-9
        # And the per-turn dict has both entries with their own values.
        assert run.phase_token_usage["phase2_round1_claude"].in_ == 100
        assert run.phase_token_usage["phase2_round2_claude"].in_ == 300
