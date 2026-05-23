"""Tests for scripts.spec_lifecycle.archive_handoffs (spec 0202 §2.3, §6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.spec_lifecycle.archive_handoffs import (
    DEFAULT_CAP,
    _active_checkpoint_paths,
    archive_old_handoffs,
    cleanup_superseded_checkpoints,
    main as cli_main,
)


def _write_handoff(path: Path, frontmatter_lines: list[str], body: str = "body\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = "\n".join(frontmatter_lines)
    path.write_text(f"---\n{fm}\n---\n\n{body}")


# --- archive_old_handoffs --------------------------------------------------

def test_archive_keeps_most_recent_cap_files(tmp_path: Path) -> None:
    d = tmp_path / "handoffs"
    d.mkdir()
    for n in range(25):
        date = f"2026-04-{(n % 28) + 1:02d}"
        # Order: tag a serial so sort by filename is deterministic
        (d / f"{date}-spec-{n:04d}-foo.md").write_text("body\n")

    moved = archive_old_handoffs(d, cap=20)
    live = sorted(p.name for p in d.iterdir() if p.is_file())
    assert len(live) == 20
    assert len(moved) == 5
    # Every moved file lives under archive/YYYY-MM/.
    for _src, dst in moved:
        assert dst.parent.parent.name == "archive"
        assert dst.parent.name.startswith("2026-")


def test_archive_no_op_when_under_cap(tmp_path: Path) -> None:
    d = tmp_path / "handoffs"
    d.mkdir()
    for n in range(5):
        (d / f"2026-05-{n + 1:02d}-spec-{n:04d}-foo.md").write_text("body\n")
    moved = archive_old_handoffs(d, cap=20)
    assert moved == []
    assert len({p.name for p in d.iterdir()}) == 5


def test_archive_dry_run_does_not_move(tmp_path: Path) -> None:
    d = tmp_path / "handoffs"
    d.mkdir()
    for n in range(25):
        (d / f"2026-04-{(n % 28) + 1:02d}-spec-{n:04d}-foo.md").write_text("body\n")
    moved = archive_old_handoffs(d, cap=20, dry_run=True)
    assert len(moved) == 5
    # Files are still in place.
    assert len([p for p in d.iterdir() if p.is_file()]) == 25
    assert not (d / "archive").exists()


def test_archive_skips_files_without_date_prefix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    d = tmp_path / "handoffs"
    d.mkdir()
    (d / "latest-arc.md").write_text("body\n")
    (d / "integration-state.md").write_text("body\n")
    for n in range(25):
        (d / f"2026-04-{(n % 28) + 1:02d}-spec-{n:04d}-foo.md").write_text("body\n")

    moved = archive_old_handoffs(d, cap=20)
    err = capsys.readouterr().err
    assert "latest-arc.md" in err
    assert "integration-state.md" in err
    # The non-date files stay put; only dated files were considered.
    live_names = {p.name for p in d.iterdir() if p.is_file()}
    assert "latest-arc.md" in live_names
    assert "integration-state.md" in live_names
    assert len(moved) == 5


def test_archive_groups_by_year_month_from_filename(tmp_path: Path) -> None:
    d = tmp_path / "handoffs"
    d.mkdir()
    # 22 files split across two months — 2 of which should archive.
    for day in range(1, 15):
        (d / f"2026-03-{day:02d}-spec-{day:04d}-foo.md").write_text("body\n")
    for day in range(1, 9):
        (d / f"2026-04-{day:02d}-spec-{day + 100:04d}-foo.md").write_text("body\n")
    archive_old_handoffs(d, cap=20)
    assert (d / "archive" / "2026-03").exists()
    # Confirm at least one file landed in March's bucket.
    assert any((d / "archive" / "2026-03").iterdir())


def test_archive_respects_protect_set(tmp_path: Path) -> None:
    """Protected files stay even when they'd otherwise be cap'd out."""
    d = tmp_path / "handoffs"
    d.mkdir()
    protected = d / "2026-01-01-spec-0150-foo.md"
    protected.write_text("body\n")
    for n in range(25):
        (d / f"2026-04-{(n % 28) + 1:02d}-spec-{n + 200:04d}-foo.md").write_text("body\n")

    moved = archive_old_handoffs(d, cap=20, protect={protected})
    moved_srcs = {src.name for src, _dst in moved}
    assert protected.name not in moved_srcs
    assert protected.exists()


# --- cleanup_superseded_checkpoints ----------------------------------------

def test_cleanup_matches_both_predicates(tmp_path: Path) -> None:
    d = tmp_path / "handoffs"
    d.mkdir()
    matching = d / "2026-05-20-spec-0202-checkpoint.md"
    mismatched_spec = d / "2026-05-21-spec-0201-checkpoint.md"
    post_deploy_same_spec = d / "2026-05-22-spec-0202-deploy.md"
    _write_handoff(matching, ['spec: "0202"', "kind: in-spec-checkpoint"])
    _write_handoff(mismatched_spec, ['spec: "0201"', "kind: in-spec-checkpoint"])
    # post-deploy has no kind field today; spec 0186 §classify_handoff_kind
    # treats absent-kind as post-deploy.
    _write_handoff(post_deploy_same_spec, ['spec: "0202"'])

    deleted = cleanup_superseded_checkpoints(d, "0202")
    assert deleted == [matching]
    assert not matching.exists()
    assert mismatched_spec.exists()
    assert post_deploy_same_spec.exists()


def test_cleanup_no_op_when_no_checkpoint(tmp_path: Path) -> None:
    d = tmp_path / "handoffs"
    d.mkdir()
    (d / "2026-05-22-spec-0202-deploy.md").write_text("---\nspec: '0202'\n---\nbody\n")
    deleted = cleanup_superseded_checkpoints(d, "0202")
    assert deleted == []


def test_cleanup_no_op_when_handoffs_dir_missing(tmp_path: Path) -> None:
    assert cleanup_superseded_checkpoints(tmp_path / "nope", "0202") == []


def test_cleanup_handles_multiple_checkpoints(tmp_path: Path) -> None:
    """An L-spec with several mid-spec checkpoints — clean all of them."""
    d = tmp_path / "handoffs"
    d.mkdir()
    files = [
        d / "2026-05-20-spec-0202-checkpoint-a.md",
        d / "2026-05-21-spec-0202-checkpoint-b.md",
        d / "2026-05-22-spec-0202-checkpoint-c.md",
    ]
    for f in files:
        _write_handoff(f, ['spec: "0202"', "kind: in-spec-checkpoint"])
    deleted = cleanup_superseded_checkpoints(d, "0202")
    assert sorted(p.name for p in deleted) == sorted(f.name for f in files)


# --- _active_checkpoint_paths (resume-target protection) ------------------

def test_active_checkpoint_paths_returns_in_flight_only(tmp_path: Path) -> None:
    d = tmp_path / "handoffs"
    d.mkdir()
    in_flight_cp = d / "2026-05-20-spec-0202-cp.md"
    stale_cp = d / "2026-05-19-spec-0150-cp.md"
    post_deploy = d / "2026-05-22-spec-0202-deploy.md"
    _write_handoff(in_flight_cp, ['spec: "0202"', "kind: in-spec-checkpoint"])
    _write_handoff(stale_cp, ['spec: "0150"', "kind: in-spec-checkpoint"])
    _write_handoff(post_deploy, ['spec: "0202"'])

    protected = _active_checkpoint_paths(d, active_spec_ids={"0202"})
    assert protected == {in_flight_cp}


# --- CLI ----------------------------------------------------------------

def test_cli_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    d = tmp_path / "handoffs"
    d.mkdir()
    for n in range(25):
        (d / f"2026-04-{(n % 28) + 1:02d}-spec-{n:04d}-foo.md").write_text("body\n")

    rc = cli_main(["--handoffs-dir", str(d), "--cap", "20", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "would move" in out
    # Filesystem untouched.
    assert not (d / "archive").exists()


def test_cli_with_cleanup_spec(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    d = tmp_path / "handoffs"
    d.mkdir()
    cp = d / "2026-05-20-spec-0202-cp.md"
    _write_handoff(cp, ['spec: "0202"', "kind: in-spec-checkpoint"])

    rc = cli_main(["--handoffs-dir", str(d), "--cleanup-spec", "0202"])
    assert rc == 0
    assert not cp.exists()
    assert "cleaned checkpoint" in capsys.readouterr().out


def test_default_cap_is_twenty() -> None:
    """The constant is referenced from /dev-next step 24a as `--cap 20`."""
    assert DEFAULT_CAP == 20
