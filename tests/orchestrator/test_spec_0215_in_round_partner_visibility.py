"""Regression test for spec 0215.

The phase-2 round-5 OpenAI prompt in the local
`runs/20260521-010637-dvs-backend-language-choice/` failing run was missing
Claude's round-5 turn. The fix opts the three `_build` call sites in
`dr_run.py` into a new `for_agent` mode of `list_turns` that drops only the
agent's own same-round file. This test locks in that the actual failing
fixture, when read through the post-fix `list_turns` call, now surfaces
Claude's round-5 RESOLVE turn to OpenAI.

Fixtures are a literal copy of three turns from the failing run
(round-04-claude, round-04-openai, round-05-claude) committed under
``tests/fixtures/in_round_partner_visibility/phase2/``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from dual_research.orchestrator._turns import list_turns
from dual_research.persistence import SessionDirectory
from dual_research.protocol.prompts import _inline_prior_turns


FIXTURE_DIR = (
    Path(__file__).parent.parent
    / "fixtures"
    / "in_round_partner_visibility"
    / "phase2"
)


def _seed_session_from_fixture(tmp_path: Path) -> SessionDirectory:
    sess = SessionDirectory(root=tmp_path).ensure()
    dest = sess.phase_dir("phase2")
    for f in FIXTURE_DIR.iterdir():
        if f.is_file() and f.name.endswith(".md"):
            shutil.copy(f, dest / f.name)
    return sess


def test_phase2_round_5_openai_prompt_includes_claudes_same_round_turn(
    tmp_path: Path,
) -> None:
    sess = _seed_session_from_fixture(tmp_path)

    prior = list_turns(
        sess, phase="phase2", up_to_round=5, for_agent="openai",
    )

    same_round_claude = [t for t in prior if t.round == 5 and t.agent == "claude"]
    assert len(same_round_claude) == 1, (
        f"expected Claude's round-5 turn to be visible to OpenAI under the "
        f"post-fix `for_agent='openai'` path, got rounds={[(t.round, t.agent) for t in prior]}"
    )

    same_round_openai = [t for t in prior if t.round == 5 and t.agent == "openai"]
    assert same_round_openai == [], (
        "OpenAI's own round-5 turn must never appear in OpenAI's own prompt"
    )

    rendered = _inline_prior_turns(
        prior, header="Prior Phase 2 conversation turns (in order)"
    )
    assert "#### Prior turn — claude, round 5" in rendered
    assert "D-plan-c-05" in rendered, (
        "Claude's round-5 RESOLVE content (referencing D-plan-c-05) should "
        "be inlined in the rendered prior_turns block — that is the exact "
        "state OpenAI was blind to pre-fix."
    )


def test_phase2_round_5_pre_fix_legacy_path_still_drops_both_same_round_turns(
    tmp_path: Path,
) -> None:
    """Antipodal-absence: the legacy `for_agent=None` path must continue to
    drop both same-round files. Locks the strict opt-in nature of the fix."""

    sess = _seed_session_from_fixture(tmp_path)

    prior = list_turns(sess, phase="phase2", up_to_round=5)

    assert all(t.round < 5 for t in prior), (
        f"legacy path must exclude both round-5 entries, got "
        f"rounds={[(t.round, t.agent) for t in prior]}"
    )
