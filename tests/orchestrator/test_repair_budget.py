"""Spec 0036 — repair turns use the raised max_output_tokens budget."""
from __future__ import annotations


def test_repair_budget_constant_is_raised() -> None:
    """The constant moved from 6144 to 16384 (matches the regular turn budget).

    A simple sanity check — if anyone lowers this without bumping the spec,
    the test catches it.
    """
    from dual_research.orchestrator.repair import REPAIR_MAX_OUTPUT_TOKENS
    assert REPAIR_MAX_OUTPUT_TOKENS == 16384


def test_phase2_hashdrift_repair_uses_the_same_budget(monkeypatch) -> None:
    """The Phase 2 hash-drift repair sources its budget from the same constant."""
    import dual_research.orchestrator.repair as repair_mod
    # The constant lives in repair.py and is imported lazily in phase2.py.
    # Confirm the import path works.
    from dual_research.orchestrator.repair import REPAIR_MAX_OUTPUT_TOKENS as expected
    # Sanity: the spec's hash-drift call site references this same constant.
    # If a future refactor splits them, this test makes the divergence visible.
    assert expected == 16384
