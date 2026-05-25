"""Spec 0214 — phase-4 convergence gate locked to orchestrator-owned versioning.

Replaces the SHA-256 gate that deadlocked when agents could not replicate
``canonical_hash``. The new gate requires both agents to emit
``AGREED_DRAFT_ACCEPTANCE`` with the same ``draft_version`` AND that the
version equal ``ctx.state.draft_round``. Provenance moves to
``Phase4Complete.draft_file_sha256`` (orchestrator-computed).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from dual_research.contract.artifacts import hash_draft_content
from dual_research.events import Phase4Complete
from dual_research.orchestrator.dr_run import (
    _compute_draft_sha_if_present,
    phase4_version_gate,
)


def _parsed(artifact_body: str | None):
    """Minimal ParsedTurnV2-shaped stand-in for the gate.

    The gate only reads ``.phase_artifact`` via ``_render_for_extract``.
    """
    return SimpleNamespace(phase_artifact=artifact_body)


def _acceptance_block(version: int, *, endorsement: str = "This draft satisfies the brief.") -> str:
    return (
        "### AGREED_DRAFT_ACCEPTANCE\n"
        "\n"
        f"draft_version: v{version}\n"
        "endorsement: |\n"
        f"  {endorsement}\n"
    )


# ─── Gate logic ──────────────────────────────────────────────────────


def test_version_gate_accepts_when_both_emit_same_version_matching_ctx_draft_round():
    a = _parsed(_acceptance_block(3))
    b = _parsed(_acceptance_block(3))
    assert phase4_version_gate(a, b, ctx_draft_round=3) is True


def test_version_gate_rejects_when_drafter_revised_same_round():
    # Drafter bumped to v4 and emitted AGREED in the same turn; orchestrator
    # has not yet advanced ctx.state.draft_round (still v3). A naive
    # version-only gate would accept (both blocks read v4); the ctx-anchor
    # third clause is what rejects.
    a = _parsed(_acceptance_block(4))
    b = _parsed(_acceptance_block(4))
    assert phase4_version_gate(a, b, ctx_draft_round=3) is False


def test_version_gate_rejects_when_versions_disagree():
    a = _parsed(_acceptance_block(3))
    b = _parsed(_acceptance_block(2))
    assert phase4_version_gate(a, b, ctx_draft_round=3) is False


def test_version_gate_rejects_when_acceptance_block_missing():
    a = _parsed(_acceptance_block(3))
    b = _parsed(None)
    assert phase4_version_gate(a, b, ctx_draft_round=3) is False


def test_version_gate_tolerates_legacy_draft_hash_line_in_acceptance_block():
    # Defensive: if a turn happens to carry a stray ``draft_hash:`` line
    # (pre-fix agents, or fixtures captured before the rollout), the new
    # parser ignores it and the gate still passes on version equality
    # alone. Locks in that the prompt change is purely subtractive and
    # the orchestrator does not regress on the parse path.
    body_with_legacy_hash = (
        "### AGREED_DRAFT_ACCEPTANCE\n"
        "\n"
        "draft_version: v3\n"
        "draft_hash: deadbeef\n"
        "endorsement: |\n"
        "  ok.\n"
    )
    a = _parsed(body_with_legacy_hash)
    b = _parsed(body_with_legacy_hash)
    assert phase4_version_gate(a, b, ctx_draft_round=3) is True


# ─── Phase4Complete provenance (orchestrator-computed SHA) ───────────


def _build_ctx(tmp_path: Path, *, draft_round: int):
    """Build a ctx-shaped stub for ``_compute_draft_sha_if_present``.

    Real ``SessionContext`` is expensive to construct; the helper only
    touches ``ctx.state.draft_round`` and ``ctx.session.phase_dir(...)``,
    which is enough surface area to stub directly.
    """
    phase3_dir = tmp_path / "phase3"
    phase4_dir = tmp_path / "phase4"
    phase3_dir.mkdir()
    phase4_dir.mkdir()
    dirs = {"phase3": phase3_dir, "phase4": phase4_dir}
    session = SimpleNamespace(phase_dir=lambda name: dirs[name])
    state = SimpleNamespace(draft_round=draft_round)
    return SimpleNamespace(state=state, session=session)


def test_compute_draft_sha_if_present_returns_canonical_hash_when_file_exists(tmp_path):
    ctx = _build_ctx(tmp_path, draft_round=3)
    text = "## Draft\n\nbody.\n"
    (tmp_path / "phase4" / "draft-v3.md").write_text(text, encoding="utf-8")
    assert _compute_draft_sha_if_present(ctx) == hash_draft_content(text)


def test_compute_draft_sha_if_present_returns_none_when_file_missing(tmp_path):
    ctx = _build_ctx(tmp_path, draft_round=3)
    # No draft-v3.md written — the publish site must tolerate "no draft
    # on disk" (hard-cap or artifact-promotion paths with no draft yet).
    assert _compute_draft_sha_if_present(ctx) is None


def test_phase4_complete_event_carries_orchestrator_computed_sha():
    # Dataclass-level lock: the new optional field exists, defaults to
    # ``None`` (additive change preserves existing consumers), and
    # accepts a concrete hash value.
    e_default = Phase4Complete(
        rounds=3, approved=True, final_draft_round=3, revisions=0,
    )
    assert e_default.draft_file_sha256 is None

    sha = hash_draft_content("draft body.")
    e_with_sha = Phase4Complete(
        rounds=3, approved=True, final_draft_round=3, revisions=0,
        draft_file_sha256=sha,
    )
    assert e_with_sha.draft_file_sha256 == sha


# ─── Replay-fixture smoke against the historical failing run ─────────


_REPLAY_FIXTURE_DIR = (
    Path(__file__).parent.parent / "fixtures" / "phase4_hash_gate_replay"
)


def test_replay_round03_synthetic_post_fix_pair_converges_under_new_gate():
    """Spec 0214 replay smoke.

    The historical ``20260521-010637-dvs-backend-language-choice`` run
    showed agents content-converged at round 3 but procedurally blocked:
    the reviewer (openai) refused to emit AGREED until the orchestrator
    exposed a SHA-256 hash. Under the new gate, with the prompt no
    longer asking for a hash, openai would have emitted an AGREED block
    pointing at v3. This test locks in that — given the post-fix
    AGREED_DRAFT_ACCEPTANCE shape — both agents pointing at v3 against
    ``ctx.state.draft_round=3`` converges immediately, instead of
    burning through to the hard cap at round 8.

    The fixture pair is synthetic (the historical openai turn was a
    procedural refusal, not an AGREED block); a tracked copy of the
    historical Claude round-3 turn lives alongside for forensic
    reference but is not parsed by this test.
    """
    claude_post_fix = _REPLAY_FIXTURE_DIR / "round-03-claude-post-fix.md"
    openai_post_fix = _REPLAY_FIXTURE_DIR / "round-03-openai-post-fix.md"
    assert claude_post_fix.exists(), claude_post_fix
    assert openai_post_fix.exists(), openai_post_fix

    # The fixtures carry a ``## Phase artifact`` section with the
    # post-fix AGREED_DRAFT_ACCEPTANCE shape. Extract the artifact body
    # directly so the test is independent of parse_turn_v2 evolution.
    def _extract_artifact(path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        marker = "## Phase artifact\n"
        idx = text.index(marker) + len(marker)
        return text[idx:].split("\n## ")[0]

    a = _parsed(_extract_artifact(claude_post_fix))
    b = _parsed(_extract_artifact(openai_post_fix))
    assert phase4_version_gate(a, b, ctx_draft_round=3) is True
