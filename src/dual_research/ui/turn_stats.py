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

import re
from pathlib import Path

from dual_research.protocol.parse import BRIEF_ISSUES_RE, parse_preflight_turn, parse_turn
from dual_research.ui.labels import ui_agent
from dual_research.ui.models import PhaseStats, TurnStats

_BACKEND_AGENTS = ("claude", "openai")

# Phase 1 drafts don't use the negotiation marker fields (STATUS / OPEN_QUESTIONS
# / BLOCKING_DISAGREEMENTS). Instead, the protocol asks agents to include named
# sections that we count to populate the same chip data.

# Heading patterns that introduce a counted section:
#   - H2 form (Claude):           `## Open questions`
#   - Numbered-section form (GPT): `5. **Open questions** — ...`
_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_NUMBERED_SECTION_RE = re.compile(
    r"^\d+\.\s+\*\*([^*\n]+?)\*\*", re.MULTILINE
)

_PHASE1_QUESTIONS_NEEDLES = ("open questions",)
_PHASE1_DISPUTES_NEEDLES = (
    "claims i expect",
    "dispute",
    "anticipated disagreements",
    "disagreements",
)

# Inside a section body, count top-level list items.
# Captures both "1." numbered and "- " / "* " bulleted items, but excludes
# indented sub-items (we only count lines starting at column 0).
_LIST_ITEM_RE = re.compile(r"^(?:\d+\.|[-*])\s+\S", re.MULTILINE)


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
    # Phase 1 prompts don't include the negotiation markers, so derive the
    # chip-relevant counts by reading the structured sections instead.
    questions = _count_items_in_section(text, _PHASE1_QUESTIONS_NEEDLES)
    disputes = _count_items_in_section(text, _PHASE1_DISPUTES_NEEDLES)
    return TurnStats(
        status=p.status,
        open_questions=p.open_questions if p.open_questions is not None else questions,
        blocking=p.blocking_disagreements if p.blocking_disagreements is not None else disputes,
        fsd=p.final_surfaced_disagreements,
    )


def _section_anchors(text: str) -> list[tuple[int, int, str]]:
    """Return section anchors in document order as ``(start, end, name)``.

    Two mutually exclusive formats are observed in real Phase 1 drafts:

    - **H2-headed** (Claude-style) — ``## Open questions``. We detect H2s and
      ignore numbered-section anchors entirely, because items inside an H2
      section ARE often numbered with ``\\d+. **...**`` patterns and would
      otherwise be picked up as false top-level sections.
    - **Numbered top-level sections** (GPT-style) — ``5. **Open questions** — …``
      used when the agent doesn't emit ``##`` headings at all. We only fall
      back to this when the document has zero H2 headings.

    ``end`` is the end position of the heading itself; the body runs from
    ``end`` until the next anchor's ``start`` (or end of document).
    """
    h2 = [(m.start(), m.end(), m.group(1)) for m in _H2_RE.finditer(text)]
    if h2:
        return h2
    return [(m.start(), m.end(), m.group(1)) for m in _NUMBERED_SECTION_RE.finditer(text)]


def _count_items_in_section(text: str, name_needles: tuple[str, ...]) -> int | None:
    """Find the first section whose heading contains any of ``name_needles``
    (case-insensitive) and count top-level numbered/bulleted items inside it.

    Returns ``None`` if no matching section is found.
    """
    anchors = _section_anchors(text)
    if not anchors:
        return None
    for i, (_, body_start, name) in enumerate(anchors):
        lname = name.lower()
        if not any(n in lname for n in name_needles):
            continue
        body_end = anchors[i + 1][0] if i + 1 < len(anchors) else len(text)
        body = text[body_start:body_end]
        return len(_LIST_ITEM_RE.findall(body))
    return None


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

    Spec 0135 — Phase 0 is now dual-shape during the transition:
    - New-protocol runs (``phase0/round-NN-*.md`` files on disk) →
      round-keyed ``{1: {claude, gpt}, 2: {...}, …}`` (matches
      phase 2 / phase 4 shape).
    - Legacy single-shot transcripts (only ``preflight-{agent}.md``
      on disk) → per-agent ``{claude: stats, gpt: stats}``.
    The FE distinguishes by inspecting key types.
    """
    phase0: dict = {}
    phase1: dict[str, TurnStats] = {}
    phase2: dict[int, dict[str, TurnStats]] = {}
    phase4: dict[int, dict[str, TurnStats]] = {}

    # Spec 0135 — prefer the new-protocol round files when present.
    phase0_dir = session_dir / "phase0"
    phase0_rounds = _discover_rounds(phase0_dir)
    if phase0_rounds:
        for r in phase0_rounds:
            per_agent: dict[str, TurnStats] = {}
            for be in _BACKEND_AGENTS:
                st = _phase0_round_stats(session_dir, r, be)
                if st is not None:
                    per_agent[ui_agent(be)] = st
            if per_agent:
                phase0[r] = per_agent
    else:
        # Legacy fallback (pre-0114 transcripts with only
        # ``preflight-{agent}.md`` files).
        for be in _BACKEND_AGENTS:
            s0 = _phase0_stats(session_dir, be)
            if s0 is not None:
                phase0[ui_agent(be)] = s0

    for be in _BACKEND_AGENTS:
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


def _phase0_round_stats(session_dir: Path, round_n: int, backend_ag: str) -> TurnStats | None:
    """Spec 0135 — per-round Phase 0 stats from
    ``phase0/round-NN-{agent}.md``. Most marker fields come through
    ``parse_turn``; ``BRIEF_ISSUES`` is parsed separately since it's not
    on ``ParsedTurn`` (the marker only appears in Phase 0 turn bodies).
    """
    text = _read(session_dir / "phase0" / f"round-{round_n:02d}-{backend_ag}.md")
    if text is None:
        return None
    p = parse_turn(text)
    brief_issues_m = BRIEF_ISSUES_RE.search(text)
    brief_issues: int | None = None
    if brief_issues_m is not None:
        try:
            brief_issues = int(brief_issues_m.group(1))
        except (TypeError, ValueError):
            brief_issues = None
    return TurnStats(
        status=p.status,
        open_questions=p.open_questions,
        open_issues=p.open_issues,
        blocking=p.blocking_disagreements,
        fsd=p.final_surfaced_disagreements,
        brief_issues=brief_issues,
    )
