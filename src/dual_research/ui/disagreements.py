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

from dual_research.contract.markers import (
    RAISED_THIS_TURN_RE,
    RESOLVED_THIS_TURN_RE,
    WITHDRAWN_THIS_TURN_RE,
    list_ids,
)
from dual_research.protocol.parse import extract_fenced_section
from dual_research.ui.labels import ui_agent
from dual_research.ui.models import Disagreement, ProgressionStep

# ─── Regexes ──────────────────────────────────────────────────────────────────

# Top-level disagreement line. Tolerates all of:
#   - D-3: Compiler performance (tsc-go) — status: open
#   - **D-1 (adoption percentages):** `resolved` — Conceded...
#   - ### D-1: SQLite in production (categorical vs. conditional)
#   - 1) D-1: Scope of acceptable production use — open
#   - 4. D-1: Operational cost — non_blocking_limitation.
#
# The leading anchor is one of: a list-marker dash, an H3/H4 heading, or a
# numbered list (digit + `.` or `)`). The separator between the D-N and the
# label is either `:` or ` —`. Captures: (1) digit, (2) optional parenthetical
# label before the separator, (3) the tail after the separator.
_D_LINE_RE = re.compile(
    r"""
    ^                              # line start
    (?:                            # ─ anchor: one of three forms ─
        \s*-\s*                    #   list-marker dash
      | \s*\#{3,4}\s+              #   H3/H4 heading
      | \s*\d+[.\)]\s+             #   numbered list (1. or 1))
    )
    (?:\*\*)?                      # optional bold-open
    D-(\d+)                        # group 1: digit
    \s*
    (?:\(([^)]*)\)\s*)?            # group 2: optional parenthetical
    [:\s]?\s*                      # tolerant separator (`:` optional)
    (?:\*\*)?                      # optional bold-close
    \s*(?:[—–-]\s*)?               # may begin with em/en/hyphen dash
    (.*?)\s*$                      # group 3: tail
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

# Bare-tail form (OpenAI's negotiation output): "<label> — <state>"
# with no "status:" keyword. The state token is whitelisted (open or one of
# the terminal states) so this doesn't swallow free-text tails.
_BARE_TAIL_RE = re.compile(
    r"^(.*?)\s*[—–\-]\s*`?(open|"
    + "|".join(_TERMINAL_STATES)
    + r")`?\b(.*)$",
    re.IGNORECASE,
)

# Sub-item lines inside an open-form block. Captured: letter, body.
_SUB_RE = re.compile(r"^\s*-\s*\(([a-e])\)\s*(.+?)\s*$", re.MULTILINE)

# Section headings we read. Agents emit D-N entries in one of three sections
# depending on the entry's lifecycle stage. We pull from all three and let the
# cross-round merge deduplicate by id.
_DISAGREEMENT_SECTION_NAME = "Substantive disagreements I'm holding"
_SIBLING_SECTION_NAMES = (
    "Final-surfaced disagreements",
    "Resolved or non-blocking differences",
)

# Phase 2/4 round file pattern: "round-NN-{agent}.md" (no .malformed)
_ROUND_FILE_RE = re.compile(r"^round-(\d+)-(claude|openai)\.md$")


# ─── Spec 0217 — STATUS as the canonical closure channel ──────────────────────
#
# The protocol's ``STATUS`` footer carries the machine-readable ledger-ops
# (``RAISED_THIS_TURN`` / ``RESOLVED_THIS_TURN`` / ``WITHDRAWN_THIS_TURN``).
# Pre-0217 the reconstructor consulted only the body sections
# (``## Substantive disagreements I'm holding`` and siblings). When agents
# moved closure prose to ``## Ratifying my own items`` blocks the closures
# became invisible to the ledger even though the STATUS lists were correct.
# The fix below makes STATUS authoritative; section-tail scanning stays as a
# legacy fallback. On conflict, STATUS wins.
#
# By symmetry — the spec's principle is that STATUS is canonical — the same
# pass also seeds minimal entries from ``RAISED_THIS_TURN`` when no body
# section produced one. Without this, a session that uses the new RAISE-block
# grammar exclusively (the smoking-gun session in spec 0217 §1) would surface
# zero items, and the closure pass would have nothing to flip.


def _canonical_id(raw: str) -> str:
    """Normalize a ``D-N`` / ``Q-N`` identifier for cross-source matching.

    Numeric-only tails are zero-padded to match the body-section parser's
    ``d-NN`` output (so ``D-1`` and ``d-01`` collapse to the same key).
    Composite tails (``D-plan-c-01``) are lowercased but kept structurally
    intact so the STATUS channel and the body-section channel can refer to
    the same item without false collisions.
    """
    s = (raw or "").strip()
    if not s:
        return s
    m = re.fullmatch(r"([A-Za-z]+)-(.+)", s)
    if not m:
        return s.lower()
    prefix = m.group(1).lower()
    rest = m.group(2)
    if re.fullmatch(r"\d+", rest):
        return f"{prefix}-{int(rest):02d}"
    return f"{prefix}-{rest.lower()}"


def _status_array(text: str, pat: "re.Pattern[str]") -> list[str]:
    """Extract one STATUS-footer action array (`[a, b, c]`) into IDs."""
    m = pat.search(text)
    if not m:
        return []
    return list_ids(m.group("ids"))


def _status_d_ids(text: str, pat: "re.Pattern[str]") -> list[str]:
    """Canonical D-prefixed IDs from a STATUS action array. Q-IDs are
    silently dropped — they're handled by the question reconstructor."""
    out: list[str] = []
    for raw in _status_array(text, pat):
        canon = _canonical_id(raw)
        if canon.startswith("d-"):
            out.append(canon)
    return out


_STUB_FIELDS = {
    "label": "",
    "status": "open",
    "point": "",
    "my_position": "",
    "other_position": "",
    "why": "",
    "materiality": "",
    "resolution_note": None,
}


def _stub_entry(d_id: str, *, status: str = "open") -> dict:
    """A minimal entry dict — used to seed timeline entries from STATUS
    when no body section produced one for this round / agent."""
    entry = {"id": d_id, **_STUB_FIELDS}
    entry["status"] = status
    return entry


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
            # Bare-tail form: "<label> — <state>" without the "status:" keyword
            # (the form OpenAI emits in negotiation rounds).
            bare_m = _BARE_TAIL_RE.match(tail)
            if bare_m:
                label = bare_m.group(1).strip().strip("`").strip()
                status = bare_m.group(2).strip().lower()
                rest = bare_m.group(3).strip()
                if rest and status != "open":
                    # Treat trailing prose as the resolution note when terminal.
                    resolution_note = rest.lstrip(".").lstrip("—–-").strip() or None
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

    # Spec 0030: when the agent uses a heading-only form (no `(a) D-N: "..."`
    # sub-bullet), fall back to the first content line under the entry as
    # `point`. Same fallback feeds `my_position` / `other_position` from
    # **I claim:** / **They claim:** style bullets when the (b)/(c) markers
    # are absent.
    if not point or not my_position or not other_position:
        fallback = _fallback_from_block(block, label=label)
        if not point:
            point = fallback.get("point", "")
        if not my_position:
            my_position = fallback.get("my_position", "")
        if not other_position:
            other_position = fallback.get("other_position", "")

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


# Spec 0030 — heading-only D-N entries don't carry `(a)/(b)/(c)` markers;
# walk the block to find the first content line that's neither the entry
# header nor a meta prefix (`status:`, blockquote, label-only bold prefix).
# Position-style bullets (`**I claim**`, `**They claim**`) feed
# `my_position` / `other_position`.

# Skip lines starting with these prefixes (case-insensitive) when scanning
# for the contested-point fallback. Each is a known meta line that carries
# no semantic content for `point`.
_META_LINE_PREFIXES = (
    "status:",
    "- status:",
    "> quote:",
    "> after:",
    ">",
)

_I_CLAIM_RE = re.compile(
    r"^\s*[-*]?\s*\*\*\s*(?:I\s+claim|My\s+position|My\s+take)\b[^:]*:\s*\*\*\s*(.+?)\s*$",
    re.IGNORECASE,
)
_THEY_CLAIM_RE = re.compile(
    r"^\s*[-*]?\s*\*\*\s*(?:They\s+claim|Their\s+position|Their\s+take|"
    r"[A-Za-z]+(?:'s)?\s+position)\b[^:]*:\s*\*\*\s*(.+?)\s*$",
    re.IGNORECASE,
)


def _strip_bullet(line: str) -> str:
    """Remove leading list-marker (-, *, 1., 2.) and bold-label prefix."""
    line = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line)
    line = re.sub(r"^\*\*[^*]+\*\*[:\s]*", "", line, count=1)
    return line.strip()


def _fallback_from_block(block: str, *, label: str) -> dict:
    """Best-effort scan of a D-N block for missing point / position fields.

    The block always starts with the entry header line (the `D-N` anchor).
    We skip that line, then walk the remaining lines:

      - Lines starting with a known meta prefix (`status:`, blockquote) are
        skipped.
      - The first `**I claim:**` / `**They claim:**` bullet feeds
        ``my_position`` / ``other_position``.
      - The first remaining non-empty content line (with list-marker and
        bold-label prefix stripped) feeds ``point`` — capped at 200 chars.
      - If the picked content line happens to be the entry's short label
        (we de-dup with a case-insensitive equality check), we keep scanning.
    """
    lines = block.splitlines()
    # Drop the first line (the D-N anchor itself).
    body_lines = lines[1:] if lines else []

    point = ""
    my_position = ""
    other_position = ""

    for raw in body_lines:
        if not raw.strip():
            continue
        # Strip the list-marker first so meta-prefix detection catches
        # forms like `- > quote: …` (a blockquote wrapped in a bullet).
        bullet_stripped = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", raw).strip()
        lower = bullet_stripped.lower()
        if any(lower.startswith(p) for p in _META_LINE_PREFIXES):
            continue

        # Position-style bullets win first (regex handles optional list marker).
        i_m = _I_CLAIM_RE.match(raw)
        if i_m and not my_position:
            my_position = i_m.group(1).strip().rstrip(".")
            continue
        t_m = _THEY_CLAIM_RE.match(raw)
        if t_m and not other_position:
            other_position = t_m.group(1).strip().rstrip(".")
            continue

        # General content line for `point`.
        if not point:
            content = _strip_bullet(raw)
            if not content:
                continue
            # Avoid echoing back the short label when it happens to be the
            # first content line.
            if label and content.lower().strip("`") == label.lower().strip("`"):
                continue
            if len(content) > 200:
                content = content[:197].rstrip() + "…"
            point = content

    return {
        "point": point,
        "my_position": my_position,
        "other_position": other_position,
    }


def _read_round_file(path: Path) -> list[dict]:
    """Read one round file and return its parsed D-N entries.

    Pulls from the canonical ``## Substantive disagreements I'm holding``
    section AND from two sibling sections where agents migrate terminal-state
    entries (``## Final-surfaced disagreements``, ``## Resolved or
    non-blocking differences``). Duplicate ids are merged keeping the
    longest-information record.
    """
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return _parse_round_text(text)


def _parse_round_text(text: str) -> list[dict]:
    """Body-section pass — extract D-N entries from the three legacy section
    headers. Kept separate from ``_read_round_file`` so callers that already
    have the file text (e.g. ``reconstruct`` for the STATUS pass) don't have
    to re-read the file."""
    collected: dict[str, dict] = {}
    for name in (_DISAGREEMENT_SECTION_NAME, *_SIBLING_SECTION_NAMES):
        section = extract_fenced_section(text, name)
        if not section:
            continue
        for entry in _parse_section(section):
            d_id = entry["id"]
            prev = collected.get(d_id)
            if prev is None:
                collected[d_id] = entry
                continue
            # Same id seen across sections — pick the better record.
            collected[d_id] = _merge_entries(prev, entry)
    return list(collected.values())


def _merge_entries(a: dict, b: dict) -> dict:
    """Combine two raw entry dicts for the same ``D-N`` id."""
    out = dict(a)
    for key, value in b.items():
        if key == "status":
            # Prefer terminal status over "open"/"unknown" once we have one.
            if value and value != "open" and (not out.get("status") or out["status"] == "open"):
                out["status"] = value
            continue
        if not out.get(key) and value:
            out[key] = value
        elif isinstance(value, str) and isinstance(out.get(key), str) and len(value) > len(out[key]):
            out[key] = value
    return out


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
    # IDs that have been raised in any prior round (any agent). Spec 0217 §8 —
    # STATUS closure only flips entries previously seen `raised`; spurious
    # IDs are silently dropped.
    raised_ever: set[str] = set()

    for rnd in rounds:
        per_agent: dict[str, dict[str, dict]] = {}
        for backend_ag in ("claude", "openai"):
            path = phase_dir / f"round-{rnd:02d}-{backend_ag}.md"
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            ui_ag = ui_agent(backend_ag)

            # ─── Body-section pass (legacy fallback) ──────────────────
            for entry in _parse_round_text(text):
                d_id = _canonical_id(entry["id"])
                entry["id"] = d_id
                per_agent.setdefault(d_id, {})[ui_ag] = entry
                raised_ever.add(d_id)

            # ─── Spec 0217 STATUS pass — RAISED seeds, RESOLVED/WITHDRAWN closes ──
            raised_ids = _status_d_ids(text, RAISED_THIS_TURN_RE)
            resolved_ids = _status_d_ids(text, RESOLVED_THIS_TURN_RE)
            withdrawn_ids = _status_d_ids(text, WITHDRAWN_THIS_TURN_RE)

            # STATUS.RAISED — seed minimal entries for IDs not produced by
            # the body pass. The raiser is the agent who wrote this turn.
            for d_id in raised_ids:
                raised_ever.add(d_id)
                if ui_ag not in per_agent.get(d_id, {}):
                    per_agent.setdefault(d_id, {})[ui_ag] = _stub_entry(d_id)

            # STATUS.RESOLVED / WITHDRAWN — flip to resolved at this turn's
            # round. STATUS wins on conflict with body-section state (§3.3).
            # Filter to IDs we've seen `raised` somewhere already (§8).
            for d_id in resolved_ids + withdrawn_ids:
                if d_id not in raised_ever:
                    # Spurious — silently drop. (A debug log line would land here.)
                    continue
                entry = per_agent.get(d_id, {}).get(ui_ag)
                if entry is None:
                    entry = _stub_entry(d_id, status="resolved")
                    per_agent.setdefault(d_id, {})[ui_ag] = entry
                else:
                    entry["status"] = "resolved"

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
