"""Step 5 · Verify — screenshot capture + before/target comparison.

The Verify step is a hybrid: the screenshot capture itself happens
through the preview_* MCP tools (which are wired into the calling
Claude session, not callable from this Python module). Per row in the
spec's § 6 Visual verification matrix the caller:

  1. preview_resize to the viewport
  2. emulates the theme (body.dark / body.light or colorScheme)
  3. navigates to the URL fragment
  4. performs any setup interaction (hover / click / scroll)
  5. preview_screenshot → save to ``queue/runs/<NNNN>/screenshots/``

This module owns the bookkeeping:

- ``planned_shots(parsed)`` produces the row list with a default 6-row
  matrix when the spec's § 6 doesn't override.
- ``shot_path(...)`` is the canonical screenshot filename so caller
  and verifier agree.
- ``record_shot(...)`` updates the in-progress verify-report.md.
- ``record_compare(...)`` records the side-by-side verdict per row
  (against a Notion screenshot and/or a Design System anchor).
- ``finalize(...)`` writes the final report, transitions the step.

Failure mode: any row's verdict is "fail" → step fails, queue halts,
operator goes back to Step 4 Implement to fix, then re-runs Step 5.
The shot files and partial report are preserved across re-runs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Literal

from dual_research.queue_v2 import parse_spec, state

DEFAULT_MATRIX: list[tuple[str, str]] = [
    ("2200x1300", "dark"),
    ("2200x1300", "light"),
    ("1400x900", "dark"),
    ("1400x900", "light"),
    ("820x1180", "dark"),
    ("820x1180", "light"),
]


Verdict = Literal["pass", "fail", "skipped"]


@dataclass
class ShotPlan:
    index: int
    viewport: str
    theme: str
    detail: str = ""
    path: str = ""
    captured: bool = False
    verdict: Verdict = "skipped"
    notes: list[str] = field(default_factory=list)


def planned_shots(parsed_spec_path: Path | None = None, parsed: parse_spec.ParsedSpec | None = None) -> list[ShotPlan]:
    """Yield the canonical shot list. Falls back to DEFAULT_MATRIX when
    the spec's § 6 didn't list anything parseable."""
    if parsed is None:
        assert parsed_spec_path is not None
        raw = json.loads(parsed_spec_path.read_text())
        rows = [(s["viewport"], s["theme"], s.get("detail", "")) for s in raw.get("visual_matrix", [])]
    else:
        rows = [(s.viewport, s.theme, s.detail) for s in parsed.visual_matrix]
    if not rows:
        rows = [(vp, th, "") for vp, th in DEFAULT_MATRIX]
    return [
        ShotPlan(index=i, viewport=vp, theme=th, detail=detail)
        for i, (vp, th, detail) in enumerate(rows, 1)
    ]


def shot_path(spec_number: str, plan: ShotPlan, repo_root: Path | None = None) -> Path:
    repo = repo_root or _repo_root()
    return (
        state.run_dir(spec_number, repo)
        / "screenshots"
        / f"{plan.index:02d}-{plan.viewport}-{plan.theme}.png"
    )


def reference_notion_screenshot(repo_root: Path, issue_num: str) -> Path | None:
    """Best-effort match of a Notion issue number to its screenshot.

    The screenshots are named ``01-badge-heights.png`` … ``17-topbar-
    layout.png`` plus optional dash-suffixed extras. Return the first
    file whose stem starts with the zero-padded issue number; None if
    no such file exists.
    """
    root = repo_root / "docs" / "design-system-v2" / "notion-issues" / "screenshots"
    if not root.is_dir():
        return None
    prefix = issue_num.zfill(2)
    matches = sorted(root.glob(f"{prefix}-*.png"))
    return matches[0] if matches else None


def begin(spec_number: str, repo_root: Path | None = None) -> list[ShotPlan]:
    repo = repo_root or _repo_root()
    state.begin_step("5_verify", repo_root=repo)
    parsed_path = state.run_dir(spec_number, repo) / "spec-parsed.json"
    shots = planned_shots(parsed_spec_path=parsed_path)
    # Pre-populate the path so the caller knows where to save.
    for s in shots:
        s.path = str(shot_path(spec_number, s, repo))
    _persist_plan(spec_number, shots, repo)
    _render_partial_report(spec_number, shots, repo)
    return shots


def record_shot(
    spec_number: str,
    index: int,
    captured: bool,
    notes: Iterable[str] = (),
    repo_root: Path | None = None,
) -> None:
    repo = repo_root or _repo_root()
    shots = _load_plan(spec_number, repo)
    for s in shots:
        if s.index == index:
            s.captured = captured
            for n in notes:
                s.notes.append(n)
            break
    _persist_plan(spec_number, shots, repo)
    _render_partial_report(spec_number, shots, repo)


def record_verdict(
    spec_number: str,
    index: int,
    verdict: Verdict,
    note: str | None = None,
    repo_root: Path | None = None,
) -> None:
    repo = repo_root or _repo_root()
    shots = _load_plan(spec_number, repo)
    for s in shots:
        if s.index == index:
            s.verdict = verdict
            if note:
                s.notes.append(note)
            break
    _persist_plan(spec_number, shots, repo)
    _render_partial_report(spec_number, shots, repo)


def finalize(spec_number: str, repo_root: Path | None = None) -> bool:
    """Write the final report; end the step with done/failed."""
    repo = repo_root or _repo_root()
    shots = _load_plan(spec_number, repo)
    failed = [s for s in shots if s.verdict == "fail"]
    captured = [s for s in shots if s.captured]
    detail = {
        "rows_total": len(shots),
        "rows_passed": sum(1 for s in shots if s.verdict == "pass"),
        "rows_failed": len(failed),
        "rows_captured": len(captured),
        "report_file": str(state.run_dir(spec_number, repo) / "verify-report.md"),
    }
    if failed:
        state.end_step("5_verify", "failed", detail, repo_root=repo)
        _render_partial_report(spec_number, shots, repo, final=True)
        return False
    state.end_step("5_verify", "done", detail, repo_root=repo)
    _render_partial_report(spec_number, shots, repo, final=True)
    return True


# -- internals -------------------------------------------------------------


def _persist_plan(spec_number: str, shots: list[ShotPlan], repo: Path) -> None:
    fp = state.run_dir(spec_number, repo) / "verify-plan.json"
    fp.write_text(json.dumps([asdict(s) for s in shots], indent=2) + "\n")


def _load_plan(spec_number: str, repo: Path) -> list[ShotPlan]:
    fp = state.run_dir(spec_number, repo) / "verify-plan.json"
    raw = json.loads(fp.read_text())
    return [ShotPlan(**r) for r in raw]


def _render_partial_report(
    spec_number: str,
    shots: list[ShotPlan],
    repo: Path,
    final: bool = False,
) -> None:
    fp = state.run_dir(spec_number, repo) / "verify-report.md"
    lines = [f"# Spec {spec_number} — verify report"]
    if final:
        lines.append("\n_Final report._\n")
    else:
        lines.append("\n_In-progress; rows update as shots are captured + judged._\n")
    lines.append("| # | Viewport | Theme | Captured | Verdict | Notes |")
    lines.append("|---|---|---|---|---|---|")
    for s in shots:
        notes = "; ".join(s.notes) if s.notes else ""
        captured = "✓" if s.captured else "—"
        lines.append(
            f"| {s.index:02d} | `{s.viewport}` | `{s.theme}` | {captured} | "
            f"`{s.verdict}` | {notes} |"
        )
    lines.append("\n## Screenshots")
    for s in shots:
        rel = Path(s.path).relative_to(repo) if s.path else None
        if rel and (repo / rel).exists():
            lines.append(f"\n### Row {s.index:02d} — {s.viewport} {s.theme}")
            lines.append(f"\n![row {s.index:02d}]({rel.as_posix()})\n")
    fp.write_text("\n".join(lines) + "\n")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root")


__all__ = [
    "DEFAULT_MATRIX",
    "ShotPlan",
    "Verdict",
    "begin",
    "finalize",
    "planned_shots",
    "record_shot",
    "record_verdict",
    "reference_notion_screenshot",
    "shot_path",
]
