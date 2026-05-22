"""Tests for scripts.spec_lifecycle.checkpoint — spec 0186.

Covers the three helpers that the supervisor model and L-spec resume mode
rely on:

- ``classify_handoff_kind`` — backwards-compat with pre-spec-0186 handoffs.
- ``read_checkpoint`` — typed parse of in-spec-checkpoint frontmatter.
- ``find_active_checkpoint`` — disambiguator for resume vs fresh start.
- ``build_headless_command`` — supervisor argv shape.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.spec_lifecycle.checkpoint import (
    CHECKPOINT_KIND,
    DEFAULT_KIND,
    CheckpointHandoff,
    build_headless_command,
    classify_handoff_kind,
    find_active_checkpoint,
    read_checkpoint,
)


def test_classify_handoff_kind_explicit_checkpoint() -> None:
    assert classify_handoff_kind({"kind": "in-spec-checkpoint"}) == CHECKPOINT_KIND


def test_classify_handoff_kind_explicit_post_deploy() -> None:
    assert classify_handoff_kind({"kind": "post-deploy"}) == DEFAULT_KIND


def test_classify_handoff_kind_missing_field_defaults_to_post_deploy() -> None:
    # Pre-spec-0186 handoffs carry no `kind:` — they must classify as
    # post-deploy so the supervisor + resume path never mistakes a
    # historical handoff for a checkpoint.
    assert classify_handoff_kind({"spec": "0042", "date": "2026-01-01"}) == DEFAULT_KIND


def test_classify_handoff_kind_empty_string_defaults_to_post_deploy() -> None:
    assert classify_handoff_kind({"kind": ""}) == DEFAULT_KIND


def test_classify_handoff_kind_passes_through_unknown_kinds() -> None:
    # Future specs may add new kinds. Don't silently coerce them to a
    # known value — surface them so callers fall through to a safe path.
    assert classify_handoff_kind({"kind": "future-kind"}) == "future-kind"


def _write_handoff(tmp_path: Path, name: str, frontmatter: str, body: str = "") -> Path:
    path = tmp_path / name
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}")
    return path


def test_read_checkpoint_returns_typed_record(tmp_path: Path) -> None:
    fm = """spec: "0186"
date: 2026-05-23
kind: in-spec-checkpoint
branch: spec/0186-queue-drain-session-isolation
branch_sha: abc1234
completed_subsections:
  - "2.1"
  - "2.2"
next_subsection: "2.3"
tests_status: green
version_bumped: true
changelog_written: false"""
    path = _write_handoff(tmp_path, "2026-05-23-spec-0186-foo.md", fm)
    cp = read_checkpoint(path)
    assert cp is not None
    assert cp.spec == "0186"
    assert cp.branch == "spec/0186-queue-drain-session-isolation"
    assert cp.branch_sha == "abc1234"
    assert cp.completed_subsections == ["2.1", "2.2"]
    assert cp.next_subsection == "2.3"
    assert cp.tests_status == "green"
    assert cp.version_bumped is True
    assert cp.changelog_written is False
    assert cp.path == path


def test_read_checkpoint_returns_none_for_post_deploy(tmp_path: Path) -> None:
    fm = """spec: "0186"
date: 2026-05-23
version: 1.33.0
pr: https://github.com/Lexiz/dual-research/pull/999"""
    path = _write_handoff(tmp_path, "2026-05-23-spec-0186-foo.md", fm, body="# Handoff body")
    assert read_checkpoint(path) is None


def test_read_checkpoint_missing_optional_fields_uses_safe_defaults(
    tmp_path: Path,
) -> None:
    # Older checkpoint authors may omit some fields — the dataclass must
    # tolerate them rather than KeyError.
    fm = """spec: "0186"
kind: in-spec-checkpoint
branch: spec/0186-foo
branch_sha: abc1234
next_subsection: "2.1\""""
    path = _write_handoff(tmp_path, "2026-05-23-spec-0186-foo.md", fm)
    cp = read_checkpoint(path)
    assert cp is not None
    assert cp.completed_subsections == []
    assert cp.tests_status == "not-yet-run"
    assert cp.version_bumped is False
    assert cp.changelog_written is False


def test_find_active_checkpoint_returns_none_when_spec_not_in_progress(
    tmp_path: Path,
) -> None:
    fm = """spec: "0186"
kind: in-spec-checkpoint
branch: spec/0186-foo
branch_sha: abc1234
next_subsection: "2.1\""""
    _write_handoff(tmp_path, "2026-05-23-spec-0186-foo.md", fm)
    # Deployed specs never enter resume mode even if a checkpoint exists
    # on disk — they shipped, the checkpoint is historical.
    assert find_active_checkpoint(tmp_path, "0186", "deployed") is None


def test_find_active_checkpoint_returns_none_when_no_handoff(tmp_path: Path) -> None:
    assert find_active_checkpoint(tmp_path, "0186", "in_progress") is None


def test_find_active_checkpoint_returns_none_when_dir_missing(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    assert find_active_checkpoint(missing, "0186", "in_progress") is None


def test_find_active_checkpoint_returns_checkpoint_when_matching(
    tmp_path: Path,
) -> None:
    fm = """spec: "0186"
kind: in-spec-checkpoint
branch: spec/0186-foo
branch_sha: abc1234
completed_subsections: ["2.1"]
next_subsection: "2.2\""""
    _write_handoff(tmp_path, "2026-05-23-spec-0186-foo.md", fm)
    cp = find_active_checkpoint(tmp_path, "0186", "in_progress")
    assert cp is not None
    assert cp.next_subsection == "2.2"


def test_find_active_checkpoint_ignores_other_specs(tmp_path: Path) -> None:
    fm = """spec: "0173"
kind: in-spec-checkpoint
branch: spec/0173-foo
branch_sha: abc1234
next_subsection: "2.1\""""
    _write_handoff(tmp_path, "2026-05-23-spec-0173-foo.md", fm)
    assert find_active_checkpoint(tmp_path, "0186", "in_progress") is None


def test_find_active_checkpoint_returns_none_when_latest_is_post_deploy(
    tmp_path: Path,
) -> None:
    # If the spec was in_progress AND the latest handoff for it is a
    # post-deploy (not a checkpoint), do not enter resume mode — that
    # would skip work. The post-deploy handoff is unusual when status is
    # in_progress, but the predicate is the safe shape.
    fm = """spec: "0186"
date: 2026-05-23
version: 1.33.0
pr: https://github.com/Lexiz/dual-research/pull/999"""
    _write_handoff(tmp_path, "2026-05-23-spec-0186-foo.md", fm)
    assert find_active_checkpoint(tmp_path, "0186", "in_progress") is None


def test_find_active_checkpoint_picks_most_recent(tmp_path: Path) -> None:
    fm1 = """spec: "0186"
kind: in-spec-checkpoint
branch: spec/0186-foo
branch_sha: aaa1111
completed_subsections: ["2.1"]
next_subsection: "2.2\""""
    fm2 = """spec: "0186"
kind: in-spec-checkpoint
branch: spec/0186-foo
branch_sha: bbb2222
completed_subsections: ["2.1", "2.2"]
next_subsection: "2.3\""""
    _write_handoff(tmp_path, "2026-05-22-spec-0186-foo.md", fm1)
    _write_handoff(tmp_path, "2026-05-23-spec-0186-foo.md", fm2)
    cp = find_active_checkpoint(tmp_path, "0186", "in_progress")
    assert cp is not None
    assert cp.next_subsection == "2.3"
    assert cp.branch_sha == "bbb2222"


def test_build_headless_command_shape(tmp_path: Path) -> None:
    cmd = build_headless_command(
        spec_number="0186",
        log_path=tmp_path / "queue-drain" / "spec-0186.log",
        project_dir="/Users/alexlisitzky/dual-research",
    )
    assert cmd == [
        "claude",
        "-p",
        "/dev-next",
        "--cwd",
        "/Users/alexlisitzky/dual-research",
    ]


def test_build_headless_command_accepts_path_objects(tmp_path: Path) -> None:
    project = Path("/some/project")
    cmd = build_headless_command(
        spec_number="0186",
        log_path=tmp_path / "log.txt",
        project_dir=project,
    )
    assert cmd[-1] == str(project)


@pytest.mark.parametrize(
    "tests_status",
    ["green", "red", "not-yet-run"],
)
def test_read_checkpoint_preserves_tests_status_values(
    tmp_path: Path, tests_status: str
) -> None:
    fm = f"""spec: "0186"
kind: in-spec-checkpoint
branch: spec/0186-foo
branch_sha: abc1234
next_subsection: "2.1"
tests_status: {tests_status}"""
    path = _write_handoff(tmp_path, f"2026-05-23-spec-0186-{tests_status}.md", fm)
    cp = read_checkpoint(path)
    assert cp is not None
    assert cp.tests_status == tests_status


def test_read_checkpoint_returns_checkpointhandoff_instance(tmp_path: Path) -> None:
    fm = """spec: "0186"
kind: in-spec-checkpoint
branch: spec/0186-foo
branch_sha: abc1234
next_subsection: "2.1\""""
    path = _write_handoff(tmp_path, "2026-05-23-spec-0186-foo.md", fm)
    cp = read_checkpoint(path)
    assert isinstance(cp, CheckpointHandoff)
