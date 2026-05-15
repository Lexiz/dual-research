"""Reconstruct the UI's ``Disagreement[]`` by parsing Phase 2 / Phase 4 round
files.

Both phases of the protocol ask each agent to maintain a
``## Substantive disagreements I'm holding`` section with stable ``D-N``
identifiers (verified against fixture runs under ``runs/``). Because the
identifiers are reused across rounds AND across agents, no fuzzy clustering
is needed — we group by ``D-N`` directly.

Two line formats are tolerated:

  - Open form:
        - D-3: Compiler performance (tsc-go) — status: open
          - (a) D-3: "<the contested-point statement>"
          - (b) My position: ...
          - (c) <Other>'s position: ...
          - (d) Why I'm not yet conceding: ...
          - (e) Materiality: ...

  - Resolved / one-line form:
        - D-1: `resolved` — Unsourced numeric claims dropped...

The reconstruction is read-only and tolerates partial / missing files
(a mid-round in-progress run still produces useful output).
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from dual_research.protocol.parse import extract_fenced_section
from dual_research.ui.labels import ui_agent
from dual_research.ui.models import Disagreement, ProgressionStep

# ─── Regexes ──────────────────────────────────────────────────────────────────

# Top-level disagreement line. Tolerates both:
#   - D-3: Compiler performance (tsc-go) — status: open
#   - **D-1 (adoption percentages):** `resolved` — Conceded...
# Captures: (1) digit, (2) optional parenthetical-label before the colon,
# (3) the tail after the colon.
_D_LINE_RE = re.compile(
    r"""
    ^\s*-\s*               # list marker
    (?:\*\*)?              # optional bold-open
    D-(\d+)                # group 1: digit
    \s*
    (?:\(([^)]*)\)\s*)?    # group 2: optional parenthetical before the colon
    :                      # required colon
    (?:\*\*)?              # optional bold-close
    \s*
    (.*?)\s*$              # group 3: tail
    """,
    re.MULTILINE | re.VERBOSE,
)

# Within an open-form tail: "<label> — status: <state>"
_OPEN_TAIL_RE = re.compile(r"^(.*?)\s*[—–-]\s*status:\s*`?([A-Za-z_]+)`?", re.IGNORECASE)

# Within a resolved-form tail. The state word is whitelisted to avoid
# misclassifying open-form labels whose first word happens to look like a state.
# Separator is tolerant: em-dash, en-dash, hyphen, or period.
_TERMINAL_STATES = ("resolved", "non_blocking_limitation", "conceded", "accepted")
_RESOLVED_TAIL_RE = re.compile(
    r"^`?(" + "|".join(_TERMINAL_STATES) + r")`?[.\s]*[—–\-]?\s*(.*)$",
    re.IGNORECASE,
)

# Sub-item lines inside an open-form block. Captured: letter, body.
_SUB_RE = re.compile(r"^\s*-\s*\(([a-e])\)\s*(.+?)\s*$", re.MULTILINE)

# Section heading we read.
_DISAGREEMENT_SECTION_NAME = "Substantive disagreements I'm holding"

# Phase 2/4 round file pattern: "round-NN-{agent}.md" (no .malformed)
_ROUND_FILE_RE = re.compile(r"^round-(\d+)-(claude|openai)\.md$")


# ─── Parsing one agent's section ──────────────────────────────────────────────


def _parse_section(section: str) -> list[dict]:
    """Parse the body under ``## Substantive disagreements I'm holding``.

    Returns one dict per ``D-N`` entry found. Dicts contain raw fields the
    aggregation step then cross-merges:
        {id, label, status, point, my_position, other_position, why,
         materiality, raw_tail, resolution_note}
    """
    # Find each D-N anchor with its byte position.
    anchors: list[tuple[int, str, str | None, str]] = []
    # (start_pos, d_id, parenthetical_label_or_None, tail)
    for m in _D_LINE_RE.finditer(section):
        d_id = f"d-{int(m.group(1)):02d}"
        paren = m.group(2).strip() if m.group(2) else None
        tail = (m.group(3) or "").strip()
        anchors.append((m.start(), d_id, paren, tail))

    out: list[dict] = []
    for i, (start, d_id, paren, tail) in enumerate(anchors):
        end = anchors[i + 1][0] if i + 1 < len(anchors) else len(section)
        block = section[start:end]
        out.append(_parse_one(d_id, paren, tail, block))
    return out


def _parse_one(
    d_id: str, parenthetical_label: str | None, tail: str, block: str
) -> dict:
    """Build the raw field dict for a single ``D-N`` block."""
    status = "open"
    label = ""
    resolution_note: str | None = None

    # Try open-form first ("...— status: open").
    open_m = _OPEN_TAIL_RE.match(tail)
    if open_m:
        label = open_m.group(1).strip().strip("`").strip()
        status = open_m.group(2).strip().lower()
    else:
        # Try resolved-form ("`resolved` — note").
        resolved_m = _RESOLVED_TAIL_RE.match(tail)
        if resolved_m:
            status = resolved_m.group(1).strip().lower()
            resolution_note = resolved_m.group(2).strip()
            label = ""
        else:
            # Fallback: take the whole tail as the label, status unknown.
            label = tail.strip().strip("`").strip()

    # When the line had a "**D-N (parenthetical):**" pattern, the parenthetical
    # is the human-readable label (the tail is just the status + note).
    if parenthetical_label and not label:
        label = parenthetical_label

    point = ""
    my_position = ""
    other_position = ""
    why = ""
    materiality = ""

    for sub in _SUB_RE.finditer(block):
        letter = sub.group(1)
        body = sub.group(2).strip()
        if letter == "a":
            # "(a) D-N: "the contested-point statement""
            # Strip the "D-N: " prefix and surrounding quotes if present.
            stripped = re.sub(r"^D-\d+:\s*", "", body).strip()
            stripped = stripped.strip('"').strip("'").strip("`").strip()
            point = stripped
        elif letter == "b":
            my_position = re.sub(r"^(My position|Position):\s*", "", body).strip()
        elif letter == "c":
            other_position = re.sub(
                r"^[A-Za-z]+(?:'s)?\s+position:\s*", "", body, flags=re.IGNORECASE
            ).strip()
        elif letter == "d":
            why = body
        elif letter == "e":
            materiality = body

    return {
        "id": d_id,
        "label": label,
        "status": status,
        "point": point,
        "my_position": my_position,
        "other_position": other_position,
        "why": why,
        "materiality": materiality,
        "resolution_note": resolution_note,
    }


def _read_round_file(path: Path) -> list[dict]:
    """Read one round file and return its parsed D-N entries."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    section = extract_fenced_section(text, _DISAGREEMENT_SECTION_NAME)
    if not section:
        return []
    return _parse_section(section)


# ─── Reconstruction across rounds and agents ──────────────────────────────────


def _discover_rounds(phase_dir: Path) -> list[int]:
    """Return the sorted list of round numbers that have at least one
    canonical (non-``.malformed``) file present."""
    if not phase_dir.exists():
        return []
    seen: set[int] = set()
    for entry in phase_dir.iterdir():
        if not entry.is_file():
            continue
        m = _ROUND_FILE_RE.match(entry.name)
        if m:
            seen.add(int(m.group(1)))
    return sorted(seen)


def _action_for_transition(prev: str | None, curr: str) -> str:
    """Map ``(prev_status, curr_status)`` to a progression action."""
    if prev is None:
        # First time we see this D-N from this agent's vantage.
        if curr == "resolved":
            return "conceded"
        if curr == "non_blocking_limitation":
            return "aligned"
        return "raised"
    if prev == curr == "open":
        return "pushed back"
    if prev == "open" and curr == "resolved":
        return "conceded"
    if prev == "open" and curr == "non_blocking_limitation":
        return "aligned"
    # Any other transition gets the generic 'restated' label.
    return "restated"


def _final_status(
    rounds_data: list[tuple[int, dict[str, dict]]],
) -> tuple[str, int | None, str | None]:
    """Decide the UI's ``status`` / ``closed_round`` / ``resolution`` for a D-N.

    ``rounds_data`` is ``[(round, {ui_agent_label: entry_dict, ...}), ...]``,
    chronological. Returns ``(status, closed_round, resolution_text)``.

    Resolution is asymmetric — whoever marks the disagreement terminal IS the
    one who conceded. ``resolved-X`` in the UI means "X's position prevailed",
    so when claude reaches ``resolved`` first, the status is ``resolved-gpt``.
    """

    def is_terminal(s: str | None) -> bool:
        return s in {"resolved", "non_blocking_limitation", "conceded", "accepted"}

    # Find the round each agent first reached a terminal state (if any).
    claude_first: int | None = None
    gpt_first: int | None = None
    claude_note: str | None = None
    gpt_note: str | None = None
    for rnd, view in rounds_data:
        c_entry = view.get("claude")
        g_entry = view.get("gpt")
        if claude_first is None and c_entry and is_terminal(c_entry["status"]):
            claude_first = rnd
            claude_note = c_entry.get("resolution_note")
        if gpt_first is None and g_entry and is_terminal(g_entry["status"]):
            gpt_first = rnd
            gpt_note = g_entry.get("resolution_note")

    if claude_first is None and gpt_first is None:
        return "open", None, None

    if claude_first is not None and gpt_first is not None:
        if claude_first < gpt_first:
            return "resolved-gpt", claude_first, claude_note or gpt_note
        if gpt_first < claude_first:
            return "resolved-claude", gpt_first, gpt_note or claude_note
        return "resolved-both", claude_first, claude_note or gpt_note

    if claude_first is not None:
        # Only claude reached terminal — claude conceded.
        return "resolved-gpt", claude_first, claude_note
    # Only gpt reached terminal — gpt conceded.
    return "resolved-claude", gpt_first, gpt_note


def reconstruct(session_dir: Path, *, phase: int) -> list[Disagreement]:
    """Reconstruct the disagreement list for one phase (2 or 4).

    Returns an empty list when the phase directory does not exist (e.g. the
    run hasn't reached this phase yet).
    """
    if phase not in (2, 4):
        return []
    phase_dir = session_dir / f"phase{phase}"
    rounds = _discover_rounds(phase_dir)
    if not rounds:
        return []

    # Per-D-N timeline:
    #   { d_id: [(round_num, {ui_agent: entry, ...}), ...] }
    timeline: dict[str, list[tuple[int, dict[str, dict]]]] = {}

    for rnd in rounds:
        per_agent: dict[str, dict] = {}
        for backend_ag in ("claude", "openai"):
            entries = _read_round_file(phase_dir / f"round-{rnd:02d}-{backend_ag}.md")
            for entry in entries:
                ui_ag = ui_agent(backend_ag)
                per_agent.setdefault(entry["id"], {})  # ensure entry exists
                per_agent[entry["id"]][ui_ag] = entry

        for d_id, agents_view in per_agent.items():
            timeline.setdefault(d_id, []).append((rnd, agents_view))

    out: list[Disagreement] = []
    for d_id, rounds_data in timeline.items():
        d = _build_disagreement(d_id, phase, rounds_data)
        out.append(d)

    # Sort: open first (by opened_round asc), then resolved (by closed_round desc).
    out.sort(
        key=lambda d: (
            0 if d.status == "open" else 1,
            d.opened_round if d.status == "open" else -(d.closed_round or 0),
        )
    )
    return out


def _build_disagreement(
    d_id: str, phase: int, rounds_data: list[tuple[int, dict[str, dict]]]
) -> Disagreement:
    """Assemble one ``Disagreement`` from its chronological per-agent timeline."""
    opened_round = rounds_data[0][0]
    last_round = rounds_data[-1][0]

    # Pick the most informative entry for label / point / positions.
    label = ""
    point = ""
    claude_position = ""
    gpt_position = ""

    for _, view in rounds_data:
        for ui_ag, entry in view.items():
            if entry["label"] and not label:
                label = entry["label"]
            if entry["point"] and not point:
                point = entry["point"]
            if ui_ag == "claude":
                # Each agent's "(b) My position" is THAT agent's view; the
                # other agent's view of the same disagreement is "(c)".
                if entry["my_position"]:
                    claude_position = entry["my_position"]
                elif entry["other_position"] and not claude_position:
                    # If we only have openai's file, its (c) is claude's view.
                    pass
            elif ui_ag == "gpt":
                if entry["my_position"]:
                    gpt_position = entry["my_position"]

    # Backfill positions from the OTHER agent's (c) field if still missing.
    for _, view in rounds_data:
        if not claude_position and "gpt" in view and view["gpt"]["other_position"]:
            claude_position = view["gpt"]["other_position"]
        if not gpt_position and "claude" in view and view["claude"]["other_position"]:
            gpt_position = view["claude"]["other_position"]

    # Determine raised_by: which agent's file first contained the D-N.
    first_view = rounds_data[0][1]
    if "claude" in first_view and "gpt" in first_view:
        raised_by = "both"
    elif "claude" in first_view:
        raised_by = "claude"
    elif "gpt" in first_view:
        raised_by = "gpt"
    else:
        raised_by = "claude"  # defensive default; shouldn't happen

    # Progression timeline: emit a step on each state transition per agent.
    progression: list[ProgressionStep] = []
    seen_prev: dict[str, str | None] = {"claude": None, "gpt": None}
    for rnd, view in rounds_data:
        for ui_ag in ("claude", "gpt"):
            entry = view.get(ui_ag)
            if entry is None:
                continue
            curr = entry["status"]
            prev = seen_prev[ui_ag]
            if prev == curr and prev not in {None}:
                # No transition; skip to avoid noisy repeats.
                continue
            action = _action_for_transition(prev, curr)
            note = _progression_note(action, entry)
            progression.append(
                ProgressionStep(round=rnd, agent=ui_ag, action=action, note=note)  # type: ignore[arg-type]
            )
            seen_prev[ui_ag] = curr

    status, closed_round, resolution = _final_status(rounds_data)

    short_label = label or _slug_from_point(point) or d_id

    return Disagreement(
        id=d_id,
        phase=phase,
        round=last_round,
        opened_round=opened_round,
        closed_round=closed_round,
        status=status,  # type: ignore[arg-type]
        raised_by=raised_by,
        short_label=short_label,
        point=point,
        claude_position=claude_position,
        gpt_position=gpt_position,
        resolution=resolution,
        progression=progression,
    )


def _progression_note(action: str, entry: dict) -> str:
    """Pick the most useful one-liner to surface on a progression step."""
    if action == "conceded" and entry.get("resolution_note"):
        return entry["resolution_note"]
    if action == "raised":
        return entry.get("point") or entry.get("my_position") or ""
    if action in ("pushed back", "restated"):
        return entry.get("why") or entry.get("my_position") or ""
    if action == "aligned":
        return entry.get("resolution_note") or entry.get("my_position") or ""
    return ""


def _slug_from_point(point: str) -> str:
    """Fallback short label if the agent never gave an explicit label."""
    if not point:
        return ""
    # First clause / first 6 words.
    head = re.split(r"[.:;]", point, maxsplit=1)[0]
    words = head.split()
    return " ".join(words[:6]).strip()


def mark_deadlocked_open(
    disagreements: list[Disagreement], hard_cap_hit: bool
) -> list[Disagreement]:
    """If the run hit hard cap with open disagreements, tag them ``deadlocked``."""
    if not hard_cap_hit:
        return disagreements
    out: list[Disagreement] = []
    for d in disagreements:
        if d.status == "open":
            out.append(replace(d, deadlocked=True))
        else:
            out.append(d)
    return out
