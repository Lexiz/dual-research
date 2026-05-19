"""Step 2 · Reason — compare the spec against the previous handover.

The Read → Reason → Rewrite triad is the cross-spec safety net. This
step loads every file the spec's § 8 Handover read points at, then
detects drift between what the previous spec actually shipped and what
this spec assumes. Drift surfaces as a list of "alignment notes"
written to ``queue/runs/<NNNN>/reason-notes.md``.

The alignment detector is intentionally simple and explicit. It runs
three checks:

1. **Missing previous handover**: any path in § 8 that doesn't exist
   on disk halts the queue. This means the previous spec didn't
   finish cleanly — the operator goes back and finishes it.

2. **File-touched overlap**: every path in § 2 Files touched is
   grepped against the most recent handovers under ``handoffs/``.
   If a previous spec in this same arc already modified the path,
   that's surfaced — the spec may need to reflect what's now in the
   file rather than the pre-arc state.

3. **CSS class anchor collision**: every CSS selector in § 11 is
   grepped against the same handovers. If a previous spec introduced
   the same selector under a different anatomy, surface it.

Notes are descriptive, not prescriptive. Step 3 Rewrite decides what
to do.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from dual_research.queue_v2 import parse_spec, state


def detect_alignment_notes(
    parsed: parse_spec.ParsedSpec,
    repo_root: Path,
    handover_window: int = 5,
) -> list[str]:
    """Return the alignment-note bodies. Empty list = no drift."""
    notes: list[str] = []
    notes.extend(_check_handover_read_exists(parsed, repo_root))
    notes.extend(_check_files_touched_overlap(parsed, repo_root, handover_window))
    notes.extend(_check_css_anchor_collision(parsed, repo_root, handover_window))
    return notes


def run(spec_number: str, repo_root: Path | None = None) -> list[str]:
    repo = repo_root or _repo_root()
    state.begin_step("2_reason", repo_root=repo)
    try:
        parsed_path = state.run_dir(spec_number, repo) / "spec-parsed.json"
        parsed = _hydrate(parsed_path)
        notes = detect_alignment_notes(parsed, repo)
    except Exception as e:
        state.end_step("2_reason", "failed", {"error": str(e)}, repo_root=repo)
        raise

    notes_path = state.run_dir(spec_number, repo) / "reason-notes.md"
    body = _render_notes(notes, parsed)
    notes_path.write_text(body)

    detail = {
        "alignment_note_count": len(notes),
        "notes_file": str(notes_path),
    }
    state.end_step("2_reason", "done", detail, repo_root=repo)
    return notes


def _check_handover_read_exists(
    parsed: parse_spec.ParsedSpec, repo: Path
) -> list[str]:
    out: list[str] = []
    for rel in parsed.handover_read_paths:
        if (repo / rel).exists():
            continue
        out.append(
            f"§ 8 Handover read names `{rel}` but the file does not exist on `main` "
            "— the previous spec did not finish cleanly. Halt and resolve before "
            "proceeding."
        )
    return out


def _check_files_touched_overlap(
    parsed: parse_spec.ParsedSpec, repo: Path, window: int
) -> list[str]:
    out: list[str] = []
    if not parsed.files_touched:
        return out
    handover_text = _recent_handover_text(repo, window)
    for path in parsed.files_touched:
        if not _path_mentioned_in(path, handover_text):
            continue
        out.append(
            f"`{path}` was modified by a previous spec in this arc (mentioned in a "
            "recent handover). Confirm the spec's pre-conditions still match the "
            "current state of the file before implementing."
        )
    return out


def _check_css_anchor_collision(
    parsed: parse_spec.ParsedSpec, repo: Path, window: int
) -> list[str]:
    out: list[str] = []
    selectors = [c.split()[0] for c in parsed.css_anchors if c and c[0] in ".#:"]
    if not selectors:
        return out
    handover_text = _recent_handover_text(repo, window)
    for sel in selectors:
        if not _selector_mentioned_in(sel, handover_text):
            continue
        out.append(
            f"CSS anchor `{sel}` appears in a recent handover. Verify the spec's "
            "intended anatomy does not collide with what a previous spec already "
            "introduced."
        )
    return out


def _recent_handover_text(repo: Path, window: int) -> str:
    handoffs_dir = repo / "handoffs"
    if not handoffs_dir.is_dir():
        return ""
    files = sorted(
        handoffs_dir.glob("2026-*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:window]
    return "\n".join(f.read_text() for f in files)


def _path_mentioned_in(path: str, blob: str) -> bool:
    # Path appears verbatim inside backticks or naked on a line.
    return path in blob


def _selector_mentioned_in(selector: str, blob: str) -> bool:
    # Selector appears inside backticks somewhere.
    return f"`{selector}" in blob or f" {selector} " in blob


def _render_notes(notes: list[str], parsed: parse_spec.ParsedSpec) -> str:
    head = (
        f"# Spec {parsed.spec} — alignment notes\n\n"
        f"Generated by Step 2 Reason. Read by Step 3 Rewrite.\n\n"
    )
    if not notes:
        return head + "_No alignment notes — Step 3 Rewrite is skipped._\n"
    lines = [head, f"{len(notes)} note(s):\n"]
    for i, n in enumerate(notes, 1):
        lines.append(f"{i}. {n}\n")
    return "\n".join(lines)


def _hydrate(parsed_path: Path) -> parse_spec.ParsedSpec:
    raw = json.loads(parsed_path.read_text())
    return parse_spec.ParsedSpec(
        spec=raw["spec"],
        slug=raw["slug"],
        title=raw["title"],
        label=raw["label"],
        version_bump=raw["version_bump"],
        target_version=raw["target_version"],
        file_path=raw["file_path"],
        handover_read_paths=list(raw.get("handover_read_paths", [])),
        files_touched=list(raw.get("files_touched", [])),
        notion_issues=list(raw.get("notion_issues", [])),
        design_anchors=list(raw.get("design_anchors", [])),
        acceptance=list(raw.get("acceptance", [])),
        visual_matrix=[
            parse_spec.VisualShot(**s) for s in raw.get("visual_matrix", [])
        ],
        css_anchors=list(raw.get("css_anchors", [])),
        backend_touched=bool(raw.get("backend_touched", False)),
        raw_sections=dict(raw.get("raw_sections", {})),
    )


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root")


__all__ = ["detect_alignment_notes", "run"]
