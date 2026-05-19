"""Tests for queue_v2.verify — matrix planning + verdict bookkeeping."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.queue_v2 import parse_spec, state, verify


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n")
    return tmp_path


def _write_parsed(spec: str, repo: Path, matrix: list[tuple[str, str]]) -> None:
    state.init_queue([spec], repo_root=repo)
    state.begin_spec(spec, "dummy", f"spec/{spec}-dummy", repo_root=repo)
    parsed = {
        "spec": spec,
        "slug": "dummy",
        "title": "t",
        "label": "refactoring",
        "version_bump": "PATCH",
        "target_version": "0.72.2",
        "file_path": f"specs/{spec}-dummy.md",
        "handover_read_paths": [],
        "files_touched": [],
        "notion_issues": [],
        "design_anchors": [],
        "acceptance": [],
        "visual_matrix": [{"viewport": vp, "theme": th, "detail": ""} for vp, th in matrix],
        "css_anchors": [],
        "backend_touched": False,
        "raw_sections": {},
    }
    (state.run_dir(spec, repo) / "spec-parsed.json").write_text(json.dumps(parsed))


def test_planned_shots_uses_spec_matrix(repo: Path) -> None:
    _write_parsed("0092", repo, [("2200x1300", "dark"), ("820x1180", "light")])
    shots = verify.begin("0092", repo_root=repo)
    assert len(shots) == 2
    assert shots[0].viewport == "2200x1300"
    assert shots[0].theme == "dark"


def test_planned_shots_default_matrix_when_empty(repo: Path) -> None:
    _write_parsed("0092", repo, [])
    shots = verify.begin("0092", repo_root=repo)
    assert len(shots) == 6
    pairs = {(s.viewport, s.theme) for s in shots}
    assert pairs == set(verify.DEFAULT_MATRIX)


def test_verdict_records_and_finalize_fails_on_any_fail(repo: Path) -> None:
    _write_parsed("0092", repo, [("2200x1300", "dark"), ("2200x1300", "light")])
    verify.begin("0092", repo_root=repo)
    verify.record_shot("0092", 1, captured=True, repo_root=repo)
    verify.record_verdict("0092", 1, "pass", repo_root=repo)
    verify.record_shot("0092", 2, captured=True, repo_root=repo)
    verify.record_verdict("0092", 2, "fail", note="layout drift", repo_root=repo)

    ok = verify.finalize("0092", repo_root=repo)
    assert ok is False

    s = state.load(repo)
    assert s.active["steps"]["5_verify"]["status"] == "failed"
    assert s.active["detail"]["5_verify"]["rows_failed"] == 1
    assert s.active["detail"]["5_verify"]["rows_passed"] == 1


def test_finalize_passes_when_all_rows_pass(repo: Path) -> None:
    _write_parsed("0092", repo, [("2200x1300", "dark")])
    verify.begin("0092", repo_root=repo)
    verify.record_shot("0092", 1, captured=True, repo_root=repo)
    verify.record_verdict("0092", 1, "pass", repo_root=repo)
    ok = verify.finalize("0092", repo_root=repo)
    assert ok is True


def test_reference_notion_screenshot_resolves(tmp_path: Path) -> None:
    screenshots = tmp_path / "docs" / "design-system-v2" / "notion-issues" / "screenshots"
    screenshots.mkdir(parents=True)
    (screenshots / "07-question-card-duplicate.png").write_bytes(b"\x89PNG")
    p = verify.reference_notion_screenshot(tmp_path, "7")
    assert p is not None
    assert p.name == "07-question-card-duplicate.png"


def test_reference_notion_screenshot_missing_returns_none(tmp_path: Path) -> None:
    (tmp_path / "docs" / "design-system-v2" / "notion-issues" / "screenshots").mkdir(parents=True)
    assert verify.reference_notion_screenshot(tmp_path, "99") is None
