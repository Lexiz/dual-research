"""Spec 0145 §5.3 — aggregator preserves prompt_pieces keys verbatim.

The aggregator's `_on_turn_ended` handler does only `str(k) → int(v)`
coercion on the incoming `prompt_pieces` dict. Both canonical-ID runs
(post-0145) and legacy-key historical runs flow through this path; the
JS-side `artifact-display.js::canonicaliseLegacyKey` is the only place
that ever translates between the two vocabs.

This test guards the load-bearing contract against future drift —
adding any normalisation step at the aggregator would silently break
the legacy read-shim.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.ui.aggregator import apply_event
from dual_research.ui.models import Run


def _empty_run() -> Run:
    return Run(id="r-1", display_id="abcd")


def _turn_ended(prompt_pieces: dict) -> dict:
    return {
        "event": "turn_ended",
        "agent": "claude",
        "phase": "phase2",
        "label": "phase2-r1-claude",
        "input_tokens": 1000,
        "output_tokens": 200,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "cost_usd": 0.01,
        "duration_ms": 100,
        "finish_reason": "end_turn",
        "model_id": "claude-sonnet-4-6",
        "prompt_pieces": prompt_pieces,
    }


class TestPromptPiecesPassthrough:
    def test_canonical_keys_pass_through_unchanged(self, tmp_path: Path) -> None:
        run = _empty_run()
        canonical = {
            "system.task.plan_negotiation": 1903,
            "user_prompt.message": 5251,
            "user_prompt.attachment.abc": 100,
            "user_prompt.attachment.def": 200,
            "phase1.claude": 10971,
        }
        apply_event(run, _turn_ended(canonical), tmp_path)
        usage = run.phase_token_usage["phase2_round1_claude"]
        # No key translation happens at this layer.
        assert usage.prompt_pieces == canonical

    def test_legacy_short_keys_pass_through_unchanged(self, tmp_path: Path) -> None:
        run = _empty_run()
        legacy = {
            "system": 1500,
            "brief": 4000,
            "d1": 800,
            "d2": 750,
        }
        apply_event(run, _turn_ended(legacy), tmp_path)
        usage = run.phase_token_usage["phase2_round1_claude"]
        # The aggregator does NOT translate legacy → canonical; the JS
        # `canonicaliseLegacyKey` shim is the only translation point.
        assert usage.prompt_pieces == legacy

    def test_mixed_vocab_preserved_as_is(self, tmp_path: Path) -> None:
        """A pathological-but-possible payload (mid-spec rollout) — both
        legacy and canonical keys in the same dict. The aggregator must
        not collapse or rename either."""
        run = _empty_run()
        mixed = {
            "system": 1000,                      # legacy
            "system.task.plan_negotiation": 50,  # canonical
            "user_prompt.message": 3000,
            "brief": 4000,                       # legacy
        }
        apply_event(run, _turn_ended(mixed), tmp_path)
        assert run.phase_token_usage["phase2_round1_claude"].prompt_pieces == mixed

    def test_string_token_value_is_coerced_to_int(self, tmp_path: Path) -> None:
        """Defensive coercion only — values may arrive as strings from
        JSON roundtrips; names themselves don't change."""
        run = _empty_run()
        apply_event(run, _turn_ended({"user_prompt.message": "5251"}), tmp_path)
        usage = run.phase_token_usage["phase2_round1_claude"]
        assert usage.prompt_pieces == {"user_prompt.message": 5251}

    def test_anchor_run_shape_passes_through(self, tmp_path: Path) -> None:
        """Spec §1.1 — pin the exact key set the anchor run's seq=83
        turn_ended event carries (verified live in the spec brief).
        Adding any normalisation would silently break this fixture."""
        run = _empty_run()
        anchor_shape = {
            "user_prompt": 5251,
            "phase1.claude": 10971,
            "phase1.openai": 5525,
            "prior_turns.phase2": 5482,
            "ledger.standing_items": 903,
            "system.task.plan_negotiation": 1903,
            "phase0.agreement.interpretation": 2321,
        }
        apply_event(run, _turn_ended(anchor_shape), tmp_path)
        usage = run.phase_token_usage["phase2_round1_claude"]
        # The legacy aggregate `user_prompt` key survives — the JS shim
        # is what makes the read path render it correctly under canonical.
        assert usage.prompt_pieces == anchor_shape
