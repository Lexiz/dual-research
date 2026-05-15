"""Per-turn protocol-stat parsing for the UI timeline cards.

The orchestrator already produces structured marker fields on every turn
(``STATUS``, ``OPEN_QUESTIONS``, ``BLOCKING_DISAGREEMENTS``, ``OPEN_ISSUES``,
``FINAL_SURFACED_DISAGREEMENTS``, ``BRIEF_ISSUES``). The aggregator reuses
``protocol.parse.parse_turn`` / ``parse_preflight_turn`` to expose those
on each timeline item so the UI can render small inline chips like
``OQ 3 · BD 1`` without sending the reader into the body.

Pure read-side; no backend changes.
"""

from __future__ import annotations

from pathlib import Path

from dual_research.protocol.parse import parse_preflight_turn, parse_turn
from dual_research.ui.labels import ui_agent
from dual_research.ui.models import PhaseStats, TurnStats

_BACKEND_AGENTS = ("claude", "openai")


def _read(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _phase0_stats(session_dir: Path, backend_ag: str) -> TurnStats | None:
    text = _read(session_dir / "phase0" / f"preflight-{backend_ag}.md")
    if text is None:
        return None
    parsed = parse_preflight_turn(text)
    return TurnStats(status=parsed.status, brief_issues=parsed.brief_issues)


def _phase1_stats(session_dir: Path, backend_ag: str) -> TurnStats | None:
    text = _read(session_dir / "phase1" / f"draft-{backend_ag}.md")
    if text is None:
        return None
    p = parse_turn(text)
    return TurnStats(
        status=p.status,
        open_questions=p.open_questions,
        blocking=p.blocking_disagreements,
        fsd=p.final_surfaced_disagreements,
    )


def _round_stats(session_dir: Path, phase: int, round_n: int, backend_ag: str) -> TurnStats | None:
    text = _read(session_dir / f"phase{phase}" / f"round-{round_n:02d}-{backend_ag}.md")
    if text is None:
        return None
    p = parse_turn(text)
    return TurnStats(
        status=p.status,
        open_questions=p.open_questions,
        open_issues=p.open_issues,
        blocking=p.blocking_disagreements,
        fsd=p.final_surfaced_disagreements,
    )


def _discover_rounds(phase_dir: Path) -> list[int]:
    """Return the sorted list of canonical round numbers present in ``phase_dir``."""
    if not phase_dir.exists():
        return []
    seen: set[int] = set()
    for entry in phase_dir.iterdir():
        if not entry.is_file():
            continue
        name = entry.name
        # canonical round file: round-NN-{claude,openai}.md (no .malformed)
        if not name.startswith("round-") or not name.endswith(".md"):
            continue
        if ".malformed" in name:
            continue
        try:
            seen.add(int(name.split("-")[1]))
        except (ValueError, IndexError):
            continue
    return sorted(seen)


def build_phase_stats(session_dir: Path) -> PhaseStats:
    """Read all relevant round/draft/preflight files and return the
    UI-shaped ``PhaseStats`` payload.

    Returns an empty ``PhaseStats`` (all dicts empty) if the session-dir
    has no files yet — graceful degradation for fresh runs.
    """
    phase0: dict[str, TurnStats] = {}
    phase1: dict[str, TurnStats] = {}
    phase2: dict[int, dict[str, TurnStats]] = {}
    phase4: dict[int, dict[str, TurnStats]] = {}

    for be in _BACKEND_AGENTS:
        s0 = _phase0_stats(session_dir, be)
        if s0 is not None:
            phase0[ui_agent(be)] = s0
        s1 = _phase1_stats(session_dir, be)
        if s1 is not None:
            phase1[ui_agent(be)] = s1

    for phase, bucket in ((2, phase2), (4, phase4)):
        for r in _discover_rounds(session_dir / f"phase{phase}"):
            per_agent: dict[str, TurnStats] = {}
            for be in _BACKEND_AGENTS:
                st = _round_stats(session_dir, phase, r, be)
                if st is not None:
                    per_agent[ui_agent(be)] = st
            if per_agent:
                bucket[r] = per_agent

    return PhaseStats(phase0=phase0, phase1=phase1, phase2=phase2, phase4=phase4)
