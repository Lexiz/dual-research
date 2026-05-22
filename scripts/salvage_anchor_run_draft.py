#!/usr/bin/env python3
"""Spec 0149 §5.9 (D07) — salvage the anchor run's draft body.

The anchor run ``20260521-010637-dvs-backend-language-choice`` reached
Phase 4 round 7 with a substantive draft body (lines 47-312 of
``round-07-claude.md``) but never produced a clean ``final.md`` because
Phase 4 didn't converge. This one-shot lifts those lines into a
``final.md`` so the run has a readable terminal artifact.

Run once from the repo root::

    uv run python scripts/salvage_anchor_run_draft.py

Idempotent — overwrites ``final.md`` on each invocation. Not part of the
production pipeline; safe to delete after the anchor run is retired.
"""
from __future__ import annotations

from pathlib import Path

ANCHOR_DIR = Path("runs/20260521-010637-dvs-backend-language-choice")
SOURCE = ANCHOR_DIR / "phase4" / "round-07-claude.md"
DEST = ANCHOR_DIR / "final.md"
# Source lines are 1-indexed in the spec; Python slicing is 0-indexed.
# Lines 47-312 inclusive → indices [46:312].
START_LINE_1IDX = 47
END_LINE_1IDX = 312


def main() -> int:
    if not SOURCE.is_file():
        print(f"error: source not found at {SOURCE}")
        return 1
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    if len(lines) < END_LINE_1IDX:
        print(
            f"error: source only has {len(lines)} lines; "
            f"expected at least {END_LINE_1IDX}"
        )
        return 1
    body = "\n".join(lines[START_LINE_1IDX - 1:END_LINE_1IDX]) + "\n"
    DEST.write_text(body, encoding="utf-8")
    print(
        f"wrote {DEST} ({body.count(chr(10))} lines from "
        f"{SOURCE.name} lines {START_LINE_1IDX}-{END_LINE_1IDX})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
