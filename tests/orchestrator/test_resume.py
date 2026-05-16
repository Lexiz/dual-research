from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.cli import main as cli_main
from dual_research.persistence import SessionDirectory, SessionState


@pytest.fixture
def session_dir_at_phase4(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pre-populate a session at phase4 to test resume."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    sess_root = tmp_path / "20260515-120000-test-resume"
    sess = SessionDirectory(root=sess_root).ensure()
    sess.write_brief("Test brief content.")
    # Seed minimal artifacts so resume can read them
    state = SessionState(
        phase="phase4",
        drafter="claude",
        agreed_plan="1. **Title:** background",
        final_surfaced_disagreements=[],
        draft_round=1,
    )
    sess.save_state(state)
    (sess.phase_dir("phase1") / "draft-claude.md").write_text("claude p1 draft")
    (sess.phase_dir("phase1") / "draft-openai.md").write_text("openai p1 draft")
    (sess.phase_dir("phase3") / "draft-v1.md").write_text("the initial draft")
    return sess_root


def test_resume_rejects_missing_path(capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        cli_main(["--resume", str(tmp_path / "no-such-dir")])
    err = capsys.readouterr().err
    assert "--resume path is not a directory" in err


def test_resume_rejects_dir_without_state(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    empty = tmp_path / "empty-session"
    empty.mkdir()
    with pytest.raises(SystemExit):
        cli_main(["--resume", str(empty)])
    err = capsys.readouterr().err
    assert "no state.json" in err


def test_resume_mutually_exclusive_with_prompt(capsys: pytest.CaptureFixture) -> None:
    with pytest.raises(SystemExit):
        cli_main(["--resume", "/tmp/x", "--prompt", "hi"])
    err = capsys.readouterr().err
    # Spec 0036: --prompt/--brief/--notion are no longer in argparse's mutex
    # group with --resume; the CLI rejects the combination explicitly in
    # main() instead. The error message changed accordingly.
    assert "cannot be combined" in err


def test_resume_loads_state_from_disk(session_dir_at_phase4: Path) -> None:
    """The resume path reads the persisted state."""
    state_path = session_dir_at_phase4 / "state.json"
    persisted = json.loads(state_path.read_text())
    assert persisted["phase"] == "phase4"
    assert persisted["drafter"] == "claude"
    assert persisted["draft_round"] == 1
