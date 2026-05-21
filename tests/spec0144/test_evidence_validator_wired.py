"""Spec 0144 §8.2 — the production evidence validator is wired in.

The default DeepResearchPhase ships with a no-op validator
(``lambda recs, p, a, ate: []``). The whole point of spec 0144 is
that ``dr_run.py`` and ``ledger/replay.py`` must override that slot
with the real ``_evidence_validator_for_run`` closure. If either
construction site reverts to the default, the validator becomes dead
code again — exactly the §3.2(d) failure mode this spec closed.
"""

from __future__ import annotations

import inspect

from dual_research.orchestrator.deep_research import DeepResearchPhase
from dual_research.orchestrator.dr_run import (
    _build_dr_phase,
    _evidence_validator_for_run,
)


def test_dr_build_phase_wires_real_validator():
    """_build_dr_phase must NOT fall back to the noop default."""
    phase = _build_dr_phase(2)
    assert phase.evidence_validator is _evidence_validator_for_run, (
        "spec 0144 regression — _build_dr_phase reverted to the "
        "default no-op validator"
    )


def test_default_validator_is_a_distinct_no_op():
    """The lambda default must remain a 4-arg slot per §6.1.b — the
    signature widening was the breaking change that lets apply_turn
    supply audit_tool_events. If someone collapses it back to 3 args,
    fail loudly here.
    """
    phase = DeepResearchPhase(phase=2, agent_turn=lambda req: "")
    sig = inspect.signature(phase.evidence_validator)
    assert len(sig.parameters) == 4, (
        f"evidence_validator default must be 4-arg, got {len(sig.parameters)}"
    )


def test_replay_construction_uses_real_validator():
    """ledger/replay._replay_phase constructs DeepResearchPhase with
    evidence_validator=_evidence_validator_for_run. We can't easily
    intercept the construction; instead, read the module source and
    assert the override is wired explicitly. A grep test like this
    is brittle but cheap, and the failure mode (validator missing
    from the replay construction) is exactly what we're guarding.
    """
    from dual_research.ledger import replay
    src = inspect.getsource(replay._replay_phase)
    assert "evidence_validator=_evidence_validator_for_run" in src, (
        "spec 0144 regression — ledger/replay._replay_phase no longer "
        "wires the production evidence validator"
    )


def test_drive_interaction_phase_uses_real_validator():
    """Same grep-level guard for dr_run._drive_interaction_phase."""
    from dual_research.orchestrator import dr_run
    src = inspect.getsource(dr_run._drive_interaction_phase)
    assert "evidence_validator=_evidence_validator_for_run" in src, (
        "spec 0144 regression — dr_run._drive_interaction_phase no "
        "longer wires the production evidence validator"
    )
