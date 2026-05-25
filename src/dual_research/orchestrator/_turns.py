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


def list_turns(
    session: SessionDirectory,
    *,
    phase: str,
    up_to_round: int | None = None,
    for_agent: str | None = None,
) -> list[PriorTurn]:
    """Return PriorTurn(agent, round, content) for every round in the phase dir.

    Sorted by (round, agent) so the conversation reads naturally. If up_to_round
    is set, strictly-future rounds (r > up_to_round) are always dropped. The
    same-round behaviour depends on for_agent:

    - for_agent is None (default): drop both same-round files. Preserves the
      pre-spec-0215 strict ``r >= up_to_round`` semantics — every caller that
      doesn't opt in sees no behavioural change.
    - for_agent is set: drop only the same-round file whose agent matches
      for_agent (the agent's own turn). The partner's same-round file — when
      it already exists on disk because agents execute sequentially within
      the round — is included so the receiving agent can ADDRESS items the
      partner emitted milliseconds earlier (spec 0215).
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
        if up_to_round is not None:
            if r > up_to_round:
                continue
            if r == up_to_round:
                if for_agent is None or agent == for_agent:
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
