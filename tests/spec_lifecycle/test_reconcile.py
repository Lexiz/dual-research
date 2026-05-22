"""Tests for scripts.spec_lifecycle.reconcile."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.spec_lifecycle.reconcile import reconcile_spec


@pytest.fixture
def repo_with_files(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("\n".join(f"line {i}" for i in range(50)) + "\n")
    (tmp_path / "src" / "bar.py").write_text("\n".join(f"line {i}" for i in range(10)) + "\n")
    return tmp_path


def test_no_drift(repo_with_files: Path) -> None:
    spec = repo_with_files / "spec.md"
    spec.write_text(
        "---\nkind: dev\nspec: \"0001\"\n---\n"
        "References `src/foo.py:10` and `src/bar.py:5`.\n"
    )
    report = reconcile_spec(spec, repo_root=repo_with_files)
    assert not report.has_drift
    assert len(report.clean) == 2


def test_mechanical_drift_line_past_eof(repo_with_files: Path) -> None:
    spec = repo_with_files / "spec.md"
    spec.write_text(
        "---\nkind: dev\nspec: \"0001\"\n---\n"
        "References `src/foo.py:200` (past EOF) and `src/bar.py:5`.\n"
    )
    report = reconcile_spec(spec, repo_root=repo_with_files)
    assert report.has_drift
    assert not report.has_blocking_drift
    assert len(report.mechanical) == 1


def test_semantic_drift_file_missing(repo_with_files: Path) -> None:
    spec = repo_with_files / "spec.md"
    spec.write_text(
        "---\nkind: dev\nspec: \"0001\"\n---\n"
        "References `src/foo.py:10` and `src/missing.py:5`.\n"
    )
    report = reconcile_spec(spec, repo_root=repo_with_files)
    assert report.has_drift
    assert report.has_blocking_drift
    assert len(report.semantic) == 1
