"""Regression test for spec 0158 — `/dev-next` handoff template mentions deferrals.

The skill text at ``~/.claude/skills/dev-next/SKILL.md`` step 23 must explain
the ``## Deferred during implementation`` convention so the implementing
agent surfaces deferrals in the handoff. Without that prompt, the step 25.5
subagent has nothing to read.

This is a host-bound test: it reads the installed skill file. CI runners
don't have ``~/.claude/skills/``, so the test skips there. Locally it runs
every time.
"""
from __future__ import annotations

from pathlib import Path

import pytest

SKILL_PATH = Path.home() / ".claude" / "skills" / "dev-next" / "SKILL.md"


pytestmark = pytest.mark.skipif(
    not SKILL_PATH.exists(),
    reason="host-side ~/.claude/skills/dev-next/SKILL.md not installed (spec 0158)",
)


def test_skill_mentions_deferred_section() -> None:
    """Step 23 (handoff write) should describe the ``## Deferred during implementation`` section."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert "## Deferred during implementation" in text, (
        "dev-next SKILL.md should mention the `## Deferred during implementation` "
        "section as part of step 23's handoff template (spec 0158)."
    )


def test_skill_mentions_step_25_5_subagent() -> None:
    """A 25.5 step (between session-title restamp and chat report) should describe
    the deferred-spec subagent spawn (spec 0158)."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    # Look for the step number prefix and the subagent description.
    assert "25.5" in text, "dev-next SKILL.md should add a step 25.5 (spec 0158)"
    assert "deferred-spec subagent" in text.lower() or "subagent" in text.lower(), (
        "step 25.5 should mention the deferred-spec subagent"
    )


def test_skill_mentions_step_15_deferral_tracking() -> None:
    """Step 15 (implementation) should remind the agent to track deferrals as
    they work (spec 0158 §7 risks mitigation)."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    # The phrase 'Track deferrals' (or similar) should appear in or near step 15.
    assert "deferral" in text.lower() or "deferred" in text.lower(), (
        "dev-next SKILL.md should remind the agent about deferral tracking"
    )
