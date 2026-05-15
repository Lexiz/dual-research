from __future__ import annotations

import re
from pathlib import Path

from dual_research.persistence import SessionDirectory
from dual_research.protocol import PriorTurn


_TURN_RE = re.compile(r"^round-(\d{2})-(claude|openai)\.md$")


def turn_filename(*, round: int, agent: str) -> str:
    return f"round-{round:02d}-{agent}.md"


def malformed_filename(*, round: int, agent: str, n: int) -> str:
    return f"round-{round:02d}-{agent}.malformed-{n}.md"


def turn_path(session: SessionDirectory, *, phase: str, round: int, agent: str) -> Path:
    return session.phase_dir(phase) / turn_filename(round=round, agent=agent)


def list_turns(session: SessionDirectory, *, phase: str, up_to_round: int | None = None) -> list[PriorTurn]:
    """Return PriorTurn(agent, round, content) for every round in the phase dir.

    Sorted by (round, agent) so the conversation reads naturally. If up_to_round
    is set, only rounds < up_to_round are returned (typically the caller wants
    everything *before* the round it is currently building).
    """
    phase_dir = session.phase_dir(phase)
    out: list[tuple[int, str, str]] = []
    for f in phase_dir.iterdir():
        if not f.is_file():
            continue
        m = _TURN_RE.match(f.name)
        if not m:
            continue
        r = int(m.group(1))
        agent = m.group(2)
        if up_to_round is not None and r >= up_to_round:
            continue
        try:
            content = f.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        out.append((r, agent, content))
    out.sort(key=lambda x: (x[0], 0 if x[1] == "claude" else 1))
    return [PriorTurn(agent=a, round=r, content=c) for r, a, c in out]


def next_malformed_n(session: SessionDirectory, *, phase: str, round: int, agent: str) -> int:
    """Find the next available .malformed-N suffix for a turn file."""
    phase_dir = session.phase_dir(phase)
    prefix = f"round-{round:02d}-{agent}.malformed-"
    used: set[int] = set()
    for f in phase_dir.iterdir():
        if not f.is_file():
            continue
        if f.name.startswith(prefix) and f.name.endswith(".md"):
            try:
                n = int(f.name[len(prefix) : -len(".md")])
                used.add(n)
            except ValueError:
                pass
    n = 1
    while n in used:
        n += 1
    return n
