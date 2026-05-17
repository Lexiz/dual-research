"""Spec 0043 — compose the ``## Standing items from prior rounds``
section that the orchestrator injects into round-N (N≥2) prompts.

This is the LLM-facing surface of the ledger. The agent reads
structured prior-state alongside the existing prior-turn dump, so
they don't have to re-derive "what's still open" from prose every
round.

The instruction is intentionally soft — the section is informational,
not output-required. Agents naturally address each standing item in
their reply (the protocol already provides ``## Answers to:``,
``## Substantive disagreements I'm holding``, etc.); items left
unaddressed surface as ``⚠ ghosted`` in the UI.
"""

from __future__ import annotations

from dual_research.ledger.models import LedgerEntry, LedgerState


_HEADER = "## Standing items from prior rounds"
_INSTRUCTION = (
    "These items were raised in earlier rounds and remain open as of "
    "this point. Address each in your reply: answer it directly (for "
    "questions), resolve or hold the position (for disagreements / "
    "claims), incorporate the fix (for issues). Items you leave "
    "unaddressed will be flagged to the user as ghosted."
)


# Order kinds so the most "actionable" land near the top.
_KIND_ORDER = ("issue", "disagreement", "claim", "question", "comment")


def build_standing_items_section(
    ledger: LedgerState,
    *,
    perspective: str,           # "claude" | "gpt" — items by the other agent surface first
    max_items: int = 30,
    max_chars: int = 3000,
) -> str:
    """Return the markdown section text — empty string if no open items.

    When ``DR_LEDGER_MODE=legacy`` is set the orchestrator should pass
    an empty string into the prompt template instead of calling this
    (see ``ledger.ledger_mode()``); this function itself doesn't read
    the env flag.

    Grouping: items raised by the OTHER agent first ("what's still on
    them to address"), then items raised by YOU ("what you still
    owe / hold"). Within each group, kinds are ordered by
    ``_KIND_ORDER``. Within a (group, kind) bucket, items are
    chronological by ``raised_round``.

    Truncation: hard caps at ``max_items`` entries OR ``max_chars``
    body characters, whichever fires first. When truncated, a final
    line indicates how many entries were omitted.
    """
    open_entries = ledger.open_entries()
    if not open_entries:
        return ""

    them = perspective_other(perspective)
    by_them = [e for e in open_entries if e.raised_by == them]
    by_you = [e for e in open_entries if e.raised_by == perspective]

    by_them.sort(key=_sort_key)
    by_you.sort(key=_sort_key)

    chunks: list[str] = [_HEADER, "", _INSTRUCTION, ""]
    char_count = sum(len(c) + 1 for c in chunks)
    rendered = 0
    truncated = 0

    def add_group(label: str, entries: list[LedgerEntry]) -> None:
        nonlocal char_count, rendered, truncated
        if not entries:
            return
        header = f"### {label} ({len(entries)} items)"
        chunks.append(header)
        char_count += len(header) + 1
        for e in entries:
            if rendered >= max_items or char_count >= max_chars:
                truncated += 1
                continue
            line = _format_entry_line(e)
            if char_count + len(line) + 1 > max_chars:
                truncated += 1
                continue
            chunks.append(line)
            char_count += len(line) + 1
            rendered += 1
        chunks.append("")

    add_group(f"Raised by {them} ({_them_label(them)})", by_them)
    add_group("Raised by you", by_you)

    if truncated > 0:
        chunks.append(
            f"_(…and {truncated} more open item(s) omitted for length; "
            f"full ledger persisted to <session>/ledger.json)_"
        )

    return "\n".join(chunks).rstrip() + "\n"


def perspective_other(p: str) -> str:
    return "gpt" if p == "claude" else "claude"


def _them_label(them: str) -> str:
    return "the other agent" if them in ("claude", "gpt") else them


def _sort_key(entry: LedgerEntry) -> tuple[int, int, int]:
    kind_rank = _KIND_ORDER.index(entry.kind) if entry.kind in _KIND_ORDER else len(_KIND_ORDER)
    return (kind_rank, entry.raised_round, _id_sort(entry.id))


def _id_sort(entry_id: str) -> int:
    """Best-effort trailing-digit extraction for stable in-kind ordering.

    ``Q-c-r1-04`` → 4. ``D-12`` → 12. ``Cl-c-p1-02`` → 2. Unparseable
    → 0.
    """
    import re

    m = re.search(r"(\d+)\D*$", entry_id)
    return int(m.group(1)) if m else 0


def _format_entry_line(e: LedgerEntry) -> str:
    """One-line standing-item entry — compact, machine-parseable, but
    human-readable.

    Format:
      - [ID] kind raised in r{N}: <body snippet> — status: open
    """
    where = "p1" if e.raised_round == 0 else f"r{e.raised_round}"
    return f"- [{e.id}] {e.kind} raised in {where}: {e.body_snippet} — status: {e.current_status}"
