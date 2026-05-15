from __future__ import annotations

from pathlib import Path

from dual_research.orchestrator._turns import (
    list_turns,
    next_malformed_n,
    turn_filename,
    turn_path,
)
from dual_research.persistence import SessionDirectory


def test_turn_filename_zero_pads() -> None:
    assert turn_filename(round=1, agent="claude") == "round-01-claude.md"
    assert turn_filename(round=12, agent="openai") == "round-12-openai.md"


def test_list_turns_orders_by_round_then_agent(tmp_path: Path) -> None:
    sess = SessionDirectory(root=tmp_path).ensure()
    p2 = sess.phase_dir("phase2")
    # Write out of order
    (p2 / "round-02-openai.md").write_text("o2")
    (p2 / "round-01-openai.md").write_text("o1")
    (p2 / "round-02-claude.md").write_text("c2")
    (p2 / "round-01-claude.md").write_text("c1")
    # Add a noise file that should be ignored
    (p2 / "preflight.md").write_text("noise")

    turns = list_turns(sess, phase="phase2")
    assert [(t.round, t.agent, t.content) for t in turns] == [
        (1, "claude", "c1"),
        (1, "openai", "o1"),
        (2, "claude", "c2"),
        (2, "openai", "o2"),
    ]


def test_list_turns_up_to_round_filters(tmp_path: Path) -> None:
    sess = SessionDirectory(root=tmp_path).ensure()
    p2 = sess.phase_dir("phase2")
    (p2 / "round-01-claude.md").write_text("c1")
    (p2 / "round-01-openai.md").write_text("o1")
    (p2 / "round-02-claude.md").write_text("c2")
    (p2 / "round-02-openai.md").write_text("o2")

    turns = list_turns(sess, phase="phase2", up_to_round=2)
    assert [(t.round, t.agent) for t in turns] == [(1, "claude"), (1, "openai")]


def test_next_malformed_n(tmp_path: Path) -> None:
    sess = SessionDirectory(root=tmp_path).ensure()
    p2 = sess.phase_dir("phase2")
    assert next_malformed_n(sess, phase="phase2", round=1, agent="claude") == 1
    (p2 / "round-01-claude.malformed-1.md").write_text("x")
    assert next_malformed_n(sess, phase="phase2", round=1, agent="claude") == 2
    (p2 / "round-01-claude.malformed-2.md").write_text("x")
    assert next_malformed_n(sess, phase="phase2", round=1, agent="claude") == 3


def test_turn_path_uses_phase_subdir(tmp_path: Path) -> None:
    sess = SessionDirectory(root=tmp_path).ensure()
    p = turn_path(sess, phase="phase2", round=5, agent="openai")
    assert p == tmp_path / "phase2" / "round-05-openai.md"
