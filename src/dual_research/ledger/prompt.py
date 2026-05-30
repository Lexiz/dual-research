"""Spec 0043 — compose the ``## Standing items from prior rounds``
section that the orchestrator injects into round-N (N≥2) prompts.
Spec 0089 § C — tightened the instruction tone so agents understand
that convergence is *actually* blocked while these items are open, and
added ``build_blocked_convergence_warning`` for the case where the
prior round was an AGREED-but-ledger-blocked one.

This is the LLM-facing surface of the ledger. The agent reads
structured prior-state alongside the existing prior-turn dump, so
they don't have to re-derive "what's still open" from prose every
round.

The instruction is **not** soft: as of spec 0089 the orchestrator
reflects the standing-items list back to the agents as a hard
convergence gate. Items the agents leave silent surface in two
places — as ``⚠ ghosted`` in the UI *and* as a blocker on
``STATUS: AGREED`` no matter what the agents self-report.
"""

from __future__ import annotations

from dual_research.ledger.models import LedgerEntry, LedgerState


_HEADER = "## Standing items from prior rounds"
_INSTRUCTION = (
    "These items were raised in earlier rounds and remain open as of "
    "this point. **Convergence will be blocked while any item below is "
    "still open**, even if you emit `OPEN_QUESTIONS: 0` / "
    "`BLOCKING_DISAGREEMENTS: 0`. To make progress this round, either:\n"
    "  (a) **Answer or address** the item directly in your reply "
    "(answer the question, resolve or hold the disagreement, "
    "incorporate the fix), OR\n"
    "  (b) **Explicitly close it out** by listing the item ID in the "
    "`## Resolved or non-blocking differences` section with a brief "
    "rationale (e.g., `dropped_as_immaterial`, `resolved` with "
    "citation, or `non_blocking_limitation`).\n"
    "Items left silent will be flagged to the user as ghosted and will "
    "continue to block convergence."
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

    .. deprecated:: spec 0257
        **DEAD SURFACE — flagged for deletion.** This function (and the
        legacy ``orchestrator/phase2.py`` / ``phase4.py`` runners that
        are its only callers) has been unreachable from the live
        ``run_dr_phase2`` / ``run_dr_phase4`` entry points since the
        spec-0118 v2 rewrite. The LIVE role-aware standing-items surface
        is ``deep_research.format_role_aware_standing_items`` (rendered
        off the contract ``LedgerEntryV2`` state machine). Spec 0257
        deliberately did NOT mirror the role-group logic here — adding a
        second diverging surface is exactly what produced 0257's
        wrong-layer citation bug. Delete this function with the legacy
        phase2/phase4 runners; do not extend it.

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


# ─── Spec 0089 § C — blocked-convergence warning ────────────────────────────


def build_blocked_convergence_warning(
    *,
    prior_round_was_blocked: bool,
    ledger_open_count: int,
    prior_round_number: int | None = None,
) -> str:
    """Spec 0089 § C — return a prominent warning section when the prior
    round emitted AGREED with `OPEN_QUESTIONS: 0` but the ledger still
    reported open items, so the orchestrator blocked convergence.

    Empty string when ``prior_round_was_blocked`` is False or
    ``ledger_open_count`` is 0 (nothing to warn about).

    Designed to be rendered just BEFORE the standing-items section so
    the agent sees the high-salience explanation first, then the
    concrete list of items below.
    """
    if not prior_round_was_blocked or ledger_open_count <= 0:
        return ""

    where = f"round {prior_round_number}" if prior_round_number is not None else "the prior round"
    chunks = [
        "## ⚠ Convergence blocked in prior round",
        "",
        (
            f"In {where} you and the other agent both emitted "
            f"`STATUS: AGREED` with `OPEN_QUESTIONS: 0`, but the "
            f"system-derived ledger reported "
            f"{ledger_open_count} item{'s' if ledger_open_count != 1 else ''} "
            f"still open. Convergence was blocked."
        ),
        "",
        (
            "The standing-items section below lists every open item. "
            "To converge this round, address or explicitly close out "
            "every item on that list (see the section's instructions "
            "for the two acceptable resolutions). Repeating an AGREED "
            "turn without addressing those items will continue to "
            "block convergence."
        ),
        "",
    ]
    return "\n".join(chunks)
