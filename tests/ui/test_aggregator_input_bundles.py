"""Spec 0033 — input-bundle persistence + Phase 0 synthesis in aggregator.

Two flows under test:

1. ``_on_turn_inputs`` writes the bundle JSON to ``inputs/<key>.json``
   and stamps the relative path on ``TurnTokenUsage.input_path``. The
   subsequent ``TurnEnded`` preserves ``input_path`` while filling in
   the token/cost fields.
2. ``build_phase0_input_bundle`` synthesises the shared Phase 0 input
   bundle from ``brief.md`` on demand (the per-agent critique modals
   share this single bundle).
"""

from __future__ import annotations

import json
from pathlib import Path

from dual_research.ui.aggregator import (
    apply_event,
    build_phase0_input_bundle,
)
from dual_research.ui.models import Run


def _empty_run() -> Run:
    return Run(id="r-1", display_id="abcd")


def _turn_inputs(*, agent: str, phase: str, label: str, pieces: dict[str, str]) -> dict:
    return {
        "event": "turn_inputs",
        "agent": agent,
        "phase": phase,
        "label": label,
        "pieces": pieces,
    }


def _turn_ended(
    *,
    agent: str,
    phase: str,
    label: str,
    in_tokens: int = 100,
    out_tokens: int = 200,
    cost: float = 0.01,
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
        "model_id": "claude-sonnet-4-6",
        "prompt_pieces": {},
    }


class TestPersistInputBundle:
    def test_writes_phase0_bundle_to_disk(self, tmp_path: Path) -> None:
        run = _empty_run()
        apply_event(
            run,
            _turn_inputs(
                agent="claude",
                phase="phase0",
                label="phase0-claude",
                pieces={"system": "SYS_TEXT", "brief": "BRIEF_TEXT"},
            ),
            tmp_path,
        )
        path = tmp_path / "inputs" / "phase0_claude.json"
        assert path.is_file()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["agent"] == "claude"
        assert data["phase"] == "phase0"
        assert data["pieces"]["brief"] == "BRIEF_TEXT"
        assert data["pieces"]["system"] == "SYS_TEXT"

    def test_stamps_input_path_on_turn_token_usage(self, tmp_path: Path) -> None:
        run = _empty_run()
        apply_event(
            run,
            _turn_inputs(
                agent="openai",
                phase="phase1",
                label="phase1-openai",
                pieces={"system": "S", "brief": "B"},
            ),
            tmp_path,
        )
        usage = run.phase_token_usage["phase1_gpt"]
        assert usage.input_path == "inputs/phase1_gpt.json"

    def test_input_path_survives_subsequent_turn_ended(self, tmp_path: Path) -> None:
        run = _empty_run()
        # Inputs arrive first (real orchestrator ordering — phase string
        # is "phase2", round comes from the label).
        apply_event(
            run,
            _turn_inputs(
                agent="claude",
                phase="phase2",
                label="phase2-r3-claude",
                pieces={"system": "S", "brief": "B"},
            ),
            tmp_path,
        )
        # Then TurnEnded fills in token/cost detail.
        apply_event(
            run,
            _turn_ended(agent="claude", phase="phase2", label="phase2-r3-claude"),
            tmp_path,
        )
        usage = run.phase_token_usage["phase2_round3_claude"]
        assert usage.input_path == "inputs/phase2_round3_claude.json"
        # ... and the token fields landed on the same record.
        assert usage.in_ == 100
        assert usage.out == 200

    def test_repair_turn_lands_under_distinct_key(self, tmp_path: Path) -> None:
        """Repair turns must not overwrite the original round's bundle."""
        run = _empty_run()
        apply_event(
            run,
            _turn_inputs(
                agent="claude",
                phase="phase2",
                label="phase2-r3-claude",
                pieces={"system": "S"},
            ),
            tmp_path,
        )
        apply_event(
            run,
            _turn_inputs(
                agent="claude",
                phase="phase2",
                label="phase2-r3-claude-repair",
                pieces={"system": "S_REPAIR"},
            ),
            tmp_path,
        )
        assert (tmp_path / "inputs" / "phase2_round3_claude.json").is_file()
        assert (tmp_path / "inputs" / "phase2_round3_claude_repair.json").is_file()


class TestPhase0Synthesis:
    def test_returns_none_when_brief_missing(self, tmp_path: Path) -> None:
        assert build_phase0_input_bundle(tmp_path) is None

    def test_synthesises_bundle_from_brief(self, tmp_path: Path) -> None:
        (tmp_path / "brief.md").write_text("UNIQUE_BRIEF_42", encoding="utf-8")
        bundle = build_phase0_input_bundle(tmp_path)
        assert bundle is not None
        assert bundle["phase"] == "phase0"
        assert bundle["agent"] == "shared"
        # The brief text shows up in the `brief` piece (not the `system`
        # template, which carries placeholders only).
        assert bundle["pieces"]["brief"] == "UNIQUE_BRIEF_42"
        assert "UNIQUE_BRIEF_42" not in bundle["pieces"]["system"]
        # System has the epistemic-duty preamble.
        assert "epistemic" in bundle["pieces"]["system"]
