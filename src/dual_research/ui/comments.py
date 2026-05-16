"""Spec 0041 — reconstruct ``Comment`` objects from Phase 4 turn files.

Phase 4 turn files maintain a ``## Comments on the current draft``
section with non-blocking commentary on the draft. Comments don't
close in any protocol-defined way — once written, they stay as
``noted``. This module captures them so the UI's Critique pane can
surface them as their own typed group instead of bucketing them
under Questions.
"""

from __future__ import annotations

import re
from pathlib import Path

from dual_research.protocol.parse import extract_review_items
from dual_research.ui.labels import ui_agent
from dual_research.ui.models import Comment


_ROUND_FILE_RE = re.compile(r"^round-(\d{2})-(claude|openai)\.md$")


def _turn_key(phase: int, round_n: int, agent_ui: str) -> str:
    return f"phase{phase}_round{round_n}_{agent_ui}"


def _initial(agent_ui: str) -> str:
    return "c" if agent_ui == "claude" else "g"


def _extract_comments_from_turn(
    turn_text: str,
) -> list[tuple[str, str | None, str | None]]:
    items = extract_review_items(turn_text)
    return [
        (it.body, it.quote, it.after)
        for it in items
        if it.kind == "comment"
    ]


def reconstruct_comments(session_dir: Path, *, phase: int) -> list[Comment]:
    """Build the ordered list of Comment objects for ``phase`` (2 or 4).

    One Comment per (round, agent, list-index) tuple. No
    cross-round closure heuristic — comments are append-only.
    """
    phase_dir = session_dir / f"phase{phase}"
    if not phase_dir.is_dir():
        return []

    rounds: dict[int, dict[str, str]] = {}
    for entry in sorted(phase_dir.iterdir()):
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        if ".malformed" in entry.name:
            continue
        m = _ROUND_FILE_RE.match(entry.name)
        if not m:
            continue
        round_n = int(m.group(1))
        backend_agent = m.group(2)
        try:
            text = entry.read_text(encoding="utf-8")
        except OSError:
            continue
        rounds.setdefault(round_n, {})[backend_agent] = text

    out: list[Comment] = []
    for round_n in sorted(rounds):
        per_agent = rounds[round_n]
        for backend_agent in ("claude", "openai"):
            text = per_agent.get(backend_agent)
            if not text:
                continue
            ui = ui_agent(backend_agent)
            items = _extract_comments_from_turn(text)
            for idx, (body, quote, after) in enumerate(items, start=1):
                out.append(
                    Comment(
                        id=f"C-{_initial(ui)}-r{round_n}-{idx:02d}",
                        phase=phase,
                        raised_by=ui,
                        raised_round=round_n,
                        body=body,
                        quote=quote,
                        after=after,
                        block_id=None,
                        raised_turn_key=_turn_key(phase, round_n, ui),
                    )
                )
    return out
