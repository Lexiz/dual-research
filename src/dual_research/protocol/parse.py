from __future__ import annotations

import re
from dataclasses import dataclass

from dual_research.protocol.errors import Status

# Field regexes — tolerant of leading list markers, surrounding backticks,
# emphasis, and blockquote prefixes. The original .mjs implementation uses
# the same set; we mirror them byte-for-byte.
_LEAD = r"^[\s>*\-`#]*"

STATUS_RE = re.compile(_LEAD + r"STATUS:\s*`?([A-Z_]+)`?", re.MULTILINE)
DRAFTER_RE = re.compile(_LEAD + r"DRAFTER:\s*`?([a-z]+)`?", re.MULTILINE)
OPEN_QUESTIONS_RE = re.compile(_LEAD + r"OPEN_QUESTIONS:\s*`?(\d+)`?", re.MULTILINE)
OPEN_ISSUES_RE = re.compile(_LEAD + r"OPEN_ISSUES:\s*`?(\d+)`?", re.MULTILINE)
BLOCKING_DISAGREEMENTS_RE = re.compile(
    _LEAD + r"BLOCKING_DISAGREEMENTS:\s*`?(\d+)`?", re.MULTILINE
)
FINAL_SURFACED_DISAGREEMENTS_RE = re.compile(
    _LEAD + r"FINAL_SURFACED_DISAGREEMENTS:\s*`?(\d+)`?", re.MULTILINE
)
DOMAIN_FIT_SELF_RE = re.compile(_LEAD + r"DOMAIN_FIT_SELF:\s*`?(\d+)`?", re.MULTILINE)
DOMAIN_FIT_OTHER_RE = re.compile(_LEAD + r"DOMAIN_FIT_OTHER:\s*`?(\d+)`?", re.MULTILINE)
BRIEF_ISSUES_RE = re.compile(_LEAD + r"BRIEF_ISSUES:\s*`?(\d+)`?", re.MULTILINE)

# Presence-checked (non-empty after colon); not numeric.
# Use [ \t]* (not \s*) so the regex does not greedily consume the trailing
# newline and grab content from the next line when the value is empty.
STRONGEST_REMAINING_OBJECTION_RE = re.compile(
    _LEAD + r"STRONGEST_REMAINING_OBJECTION:[ \t]*`?(.*)`?", re.MULTILINE
)
WHY_NON_BLOCKING_RE = re.compile(_LEAD + r"WHY_NON_BLOCKING:[ \t]*`?(.*)`?", re.MULTILINE)

# Spec 0036: word-boundary anchor + tolerate trailing content. Agents
# emit headings like ``## Evidence checked this round (3 sources)`` or
# ``## Evidence checked this round:`` — the old ``\s*$`` form missed
# them. ``\b`` keeps ``roundup`` / ``roundtable`` from false-positive.
EVIDENCE_CHECKED_SECTION_RE = re.compile(
    r"^##\s+Evidence checked this round\b", re.MULTILINE
)
CARRYOVER_AUDIT_SECTION_RE = re.compile(
    r"^##\s+Disagreement carryover audit\b", re.MULTILINE
)


def _escape_regex(s: str) -> str:
    return re.escape(s)


def extract_fenced_section(text: str, heading_name: str) -> str | None:
    """Return the body under a `## <heading_name>` heading, up to the next `## ` heading.

    Returns None if the heading is absent or the body is empty after stripping.
    Mirrors the original extractFencedSection() in protocol.mjs.
    """
    heading_re = re.compile(r"^##\s+" + _escape_regex(heading_name) + r"\s*$", re.MULTILINE)
    m = heading_re.search(text)
    if not m:
        return None
    start_body = m.end()
    rest = text[start_body:]
    next_heading = re.search(r"^##\s+\S", rest, re.MULTILINE)
    body = rest[: next_heading.start()] if next_heading else rest
    body = body.strip()
    return body or None


@dataclass(frozen=True)
class ParsedTurn:
    status: str | None
    drafter: str | None
    open_questions: int | None
    open_issues: int | None
    blocking_disagreements: int | None
    final_surfaced_disagreements: int | None
    domain_fit_self: int | None
    domain_fit_other: int | None
    agreed_plan: str | None
    strongest_remaining_objection: bool
    why_non_blocking: bool
    evidence_checked_section: bool
    carryover_audit_section: bool


@dataclass(frozen=True)
class ParsedPreflightTurn:
    status: str | None
    brief_issues: int | None


def _int_or_none(match: re.Match[str] | None) -> int | None:
    if match is None:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _str_present(match: re.Match[str] | None) -> bool:
    if match is None:
        return False
    val = match.group(1) or ""
    return len(val.replace("`", "").strip()) > 0


def parse_turn(text: str) -> ParsedTurn:
    status_m = STATUS_RE.search(text)
    drafter_m = DRAFTER_RE.search(text)
    return ParsedTurn(
        status=status_m.group(1) if status_m else None,
        drafter=drafter_m.group(1) if drafter_m else None,
        open_questions=_int_or_none(OPEN_QUESTIONS_RE.search(text)),
        open_issues=_int_or_none(OPEN_ISSUES_RE.search(text)),
        blocking_disagreements=_int_or_none(BLOCKING_DISAGREEMENTS_RE.search(text)),
        final_surfaced_disagreements=_int_or_none(
            FINAL_SURFACED_DISAGREEMENTS_RE.search(text)
        ),
        domain_fit_self=_int_or_none(DOMAIN_FIT_SELF_RE.search(text)),
        domain_fit_other=_int_or_none(DOMAIN_FIT_OTHER_RE.search(text)),
        agreed_plan=extract_fenced_section(text, "AGREED_PLAN"),
        strongest_remaining_objection=_str_present(
            STRONGEST_REMAINING_OBJECTION_RE.search(text)
        ),
        why_non_blocking=_str_present(WHY_NON_BLOCKING_RE.search(text)),
        evidence_checked_section=bool(EVIDENCE_CHECKED_SECTION_RE.search(text)),
        carryover_audit_section=bool(CARRYOVER_AUDIT_SECTION_RE.search(text)),
    )


def parse_preflight_turn(text: str) -> ParsedPreflightTurn:
    status_m = STATUS_RE.search(text)
    return ParsedPreflightTurn(
        status=status_m.group(1) if status_m else None,
        brief_issues=_int_or_none(BRIEF_ISSUES_RE.search(text)),
    )


def has_agreed_plan(parsed: ParsedTurn) -> bool:
    return parsed.agreed_plan is not None and len(parsed.agreed_plan) > 0


# Spec 0036 — HR-only stripping helper for extract_revised_draft.
# A body that's nothing but ``----`` (markdown horizontal rule) should
# read as "no draft" rather than "draft body = ----". The agent often
# emits the rule as a section separator that the rest of the protocol
# text didn't make it past.
_HR_LINE_RE = re.compile(r"^\s*[-_*]{3,}\s*$", re.MULTILINE)


def _strip_horizontal_rules(body: str | None) -> str | None:
    if not body:
        return body
    cleaned = _HR_LINE_RE.sub("", body).strip()
    return cleaned or None


def extract_revised_draft(turn_text: str) -> str | None:
    """Return the body under `## Revised draft` (next top-level `##` ends it).

    Used by Phase 4 to detect when the DRAFTER emits a new draft version inside
    their turn. Returns None when the section is absent or empty.

    Spec 0036: a body whose remaining content is horizontal-rule-only
    after stripping returns ``None`` — the agent meant a separator, not a
    draft. Without this the orchestrator promoted ``----`` as a revised
    draft and overwrote the converged document.
    """
    raw = extract_fenced_section(turn_text, "Revised draft")
    return _strip_horizontal_rules(raw)


# Spec 0036 — sibling-section tolerance for the drafter's ## Revised draft.
# The drafter sometimes emits sub-sections (``## Plan summary``, ``##
# Implementation steps``) as siblings of ``## Revised draft`` instead of
# nested ``### …``. The strict extractor truncates at the first sibling
# and returns just the preamble. The inclusive variant walks forward and
# absorbs any ``## …`` heading that is NOT in the protocol allowlist.

_PROTOCOL_TOP_HEADINGS: frozenset[str] = frozenset({
    "summary",
    "status block",
    "disagreement carryover audit",
    "evidence checked this round",
    "substantive disagreements i'm holding",
    "resolved or non-blocking differences",
    "final-surfaced disagreements",
    "comments on the current draft",
    "agreed_plan",
    "issue ledger (delta + currently open)",
})

# Headings that are protocol-known but use a variable suffix (agent name,
# round number, etc.). The check matches the prefix lowercased.
_PROTOCOL_TOP_HEADING_PREFIXES: tuple[str, ...] = (
    "open questions for ",
    "issue ledger",
    "diff vs ",
    "answers to ",
    "summary of ",        # "Summary of my position" / "Summary of position"
    "tl;dr",
    "tldr",
)


def _is_protocol_top_heading(line: str) -> bool:
    """True when ``line`` is a ``## ...`` heading matching the protocol allowlist."""
    m = re.match(r"^##\s+(.+?)\s*$", line)
    if not m:
        return False
    text = m.group(1).strip().lower()
    if text in _PROTOCOL_TOP_HEADINGS:
        return True
    return any(text.startswith(prefix) for prefix in _PROTOCOL_TOP_HEADING_PREFIXES)


_REVISED_DRAFT_HEADING_RE = re.compile(r"^##\s+Revised draft\s*$", re.MULTILINE)
_TOP_HEADING_RE = re.compile(r"^##\s+\S", re.MULTILINE)


def extract_revised_draft_inclusive(turn_text: str) -> str | None:
    """Like ``extract_revised_draft`` but absorbs stray sibling sub-sections.

    Spec 0036: walks forward from ``## Revised draft``; ``## ...`` headings
    that are NOT in the protocol allowlist are absorbed as part of the
    draft body. The first protocol-allowlisted heading ends the draft.

    Returns ``None`` when the heading is absent or the resulting body is
    horizontal-rule-only after stripping.
    """
    if not turn_text:
        return None
    m = _REVISED_DRAFT_HEADING_RE.search(turn_text)
    if not m:
        return None

    start = m.end()
    cursor = start
    end = len(turn_text)

    while True:
        rest = turn_text[cursor:]
        next_match = _TOP_HEADING_RE.search(rest)
        if not next_match:
            break
        heading_start = cursor + next_match.start()
        # The matched ``## `` prefix; need the full heading line to decide.
        line_end = turn_text.find("\n", heading_start)
        if line_end == -1:
            line_end = len(turn_text)
        heading_line = turn_text[heading_start:line_end]
        if _is_protocol_top_heading(heading_line):
            end = heading_start
            break
        # Stray sibling — absorb and keep walking from the next char after the
        # heading line so we don't re-match the same one.
        cursor = line_end + 1
        if cursor >= len(turn_text):
            break

    body = turn_text[start:end].strip()
    return _strip_horizontal_rules(body)


# ─── Summary extraction (spec 0025) ────────────────────────────────────────────


# Match `## Summary`, `## Summary of my position`, `## Summary of position`,
# `## TL;DR`, or `## tldr`. Case-insensitive on the heading word.
_SUMMARY_HEADING_RE = re.compile(
    r"^##\s+(?:Summary(?:\s+of(?:\s+my)?\s+position)?|TL;DR|TLDR)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def extract_summary(text: str) -> str | None:
    """Return the body under the first `## Summary` (or `## TL;DR`) heading.

    Body ends at the next `## ` heading or EOF. Returns None when the
    heading is absent or its body is empty after stripping. Used by the
    UI's summary-card layer to surface a TL;DR for plan drafts and
    negotiation turns without rendering the whole document.
    """
    m = _SUMMARY_HEADING_RE.search(text or "")
    if not m:
        return None
    start = m.end()
    rest = text[start:]
    next_heading = re.search(r"^##\s+\S", rest, re.MULTILINE)
    body = rest[: next_heading.start()] if next_heading else rest
    body = body.strip()
    return body or None


# ─── Review-item extraction (spec 0027) ───────────────────────────────────────


@dataclass(frozen=True)
class ReviewItem:
    """One question / disagreement / resolved item extracted from a Phase 2 turn.

    `quote` and `after` are the optional anchor markers the agent
    emits as ``> quote: …`` / ``> after: …`` blockquote sub-lines under
    each item. The UI uses them to scroll the prior content (the
    other agent's most recent turn, or Phase 1 draft for round 1) so
    that clicking a review card brings the referenced span into view.

    Spec 0034: ``block_id`` is the pre-resolved anchor — set by
    ``resolve_review_items`` after running ``assign_block_ids`` over
    the prior content. The UI uses it directly via
    ``document.getElementById`` (no DOM text scan) and only falls back
    to ``quote``/``after`` substring matching when ``block_id`` is None
    (paraphrased anchor / parser miss).
    """

    kind: str           # "question" | "disagreement" | "resolved" | "issue" | "comment"
    body: str           # the item's full body, joined newlines
    quote: str | None   # verbatim ≤25-word span (anchor target)
    after: str | None   # heading text for "missing X" critiques
    item_id: str | None  # e.g. "D-3" for disagreements; None for plain questions
    block_id: str | None = None  # spec 0034: pre-resolved against prior blocks


_QUOTE_RE = re.compile(r"^\s*>\s*quote:\s*(.+?)\s*$", re.IGNORECASE)
_AFTER_RE = re.compile(r"^\s*>\s*after:\s*(.+?)\s*$", re.IGNORECASE)
# Numbered question lines: `1. …`, `1) …`, with optional leading whitespace.
_NUMBERED_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
# D-N open-form anchor line, tolerant of leading list marker / surrounding asterisks.
_D_OPEN_RE = re.compile(
    r"^\s*-\s+\*?\*?(?P<id>D-\d+)\*?\*?\s*:\s*(?P<title>.+?)\s*[—-]\s*status:\s*open\s*$",
    re.IGNORECASE,
)
# D-N terminal-form anchor line — same shape as the open-form regex on
# the prefix; status is one of the protocol's terminal-state keywords.
_D_TERMINAL_RE = re.compile(
    r"^\s*-\s+\*?\*?(?P<id>D-\d+)\*?\*?\s*"
    r"(?:\(.*?\))?\s*:?\*?\*?\s*"
    r"`?(?P<state>resolved|non_blocking_limitation|conceded|accepted|dropped_as_immaterial)`?",
    re.IGNORECASE,
)


def _extract_anchor_markers(body_lines: list[str]) -> tuple[str | None, str | None]:
    """Return (quote, after) from the first matching blockquote line in body_lines."""
    quote: str | None = None
    after: str | None = None
    for line in body_lines:
        if quote is None:
            m = _QUOTE_RE.match(line)
            if m:
                quote = m.group(1).strip().strip("`'\"")
                continue
        if after is None:
            m = _AFTER_RE.match(line)
            if m:
                after = m.group(1).strip().strip("`'\"# ")
                continue
        if quote and after:
            break
    return quote, after


def _walk_section_items(body: str, *, kind: str = "question") -> list[ReviewItem]:
    """Yield ReviewItems for a numbered-list section.

    The classifier — spec 0041 D1 — passes the kind explicitly:
    - ``Open questions for {other}``   → ``kind="question"``
    - ``Issue ledger (delta + currently open)`` → ``kind="issue"``
    - ``Comments on the current draft`` → ``kind="comment"``
    Pre-0041 the parser bucketed all three under ``"question"`` "so the
    UI groups them"; the side-effect was a Phase 4 critique view that
    reported 61 open ``questions`` for a run that the protocol counted
    as 0 open issues + approved. The kinds now match the protocol.
    """
    out: list[ReviewItem] = []
    lines = body.splitlines()
    current: list[str] | None = None

    def _flush() -> None:
        if current is None:
            return
        text_lines = [line for line in current if line.strip()]
        if not text_lines:
            return
        # The first line is the numbered prefix; strip leading numbering for body.
        m = _NUMBERED_RE.match(current[0])
        first_body = m.group(2) if m else current[0]
        rest = current[1:]
        body_text = "\n".join([first_body] + rest).strip()
        quote, after = _extract_anchor_markers(current)
        out.append(
            ReviewItem(
                kind=kind,
                body=body_text,
                quote=quote,
                after=after,
                item_id=None,
            )
        )

    # Spec 0041 — Issue ledgers in this run alternate between two styles:
    #   GPT  uses  ``1. **OAI-1 — open — ...**``  (numbered + bold)
    #   Claude uses ``**C-1** — `open` — ...``   (bold heading only)
    # Both should be treated as discrete entries. We detect either a
    # numbered prefix or a bold-prefixed ID-token line as a new entry.
    for line in lines:
        if (
            _NUMBERED_RE.match(line)
            or _BOLD_ID_HEADING_RE.match(line)
            or _BOLD_QID_HEADING_RE.match(line)
        ):
            _flush()
            current = [line]
        elif current is not None:
            current.append(line)
    _flush()
    return out


# A bolded ledger-entry header: line starts with ``**`` followed by a
# token that looks like an issue/disagreement ID (``C-1`` / ``OAI-3`` /
# ``D-5`` / ``D-OAI-1``). Used by ``_walk_section_items`` to recognise
# the Claude-style Issue ledger that's bold-prefixed but not numbered.
_BOLD_ID_HEADING_RE = re.compile(
    r"^\s*\*\*\s*(?:[A-Z]{1,4}-)+(?:[A-Z]+-)?\d+\b",
)


# Spec 0042 — Phase 1 ``Open Questions`` entries are bold-prefixed with
# a single-letter id and no hyphen (``**Q1: …**``). The numbered/dashed
# regexes above don't match these.
_BOLD_QID_HEADING_RE = re.compile(
    r"^\s*\*\*\s*[A-Z]\d+\b",
)


# Back-compat alias — preserved so any external caller still works.
_walk_section_questions = _walk_section_items


def _walk_section_disagreements(body: str, *, kind: str) -> list[ReviewItem]:
    """Yield ReviewItems for a D-N anchored disagreements section."""
    out: list[ReviewItem] = []
    lines = body.splitlines()
    current: list[str] | None = None
    current_id: str | None = None
    current_kind: str = kind

    def _flush() -> None:
        if current is None or current_id is None:
            return
        body_text = "\n".join(line for line in current if line.strip()).strip()
        if not body_text:
            return
        quote, after = _extract_anchor_markers(current)
        out.append(
            ReviewItem(
                kind=current_kind,
                body=body_text,
                quote=quote,
                after=after,
                item_id=current_id,
            )
        )

    for line in lines:
        open_m = _D_OPEN_RE.match(line)
        terminal_m = _D_TERMINAL_RE.match(line)
        if open_m:
            _flush()
            current = [line]
            current_id = open_m.group("id")
            current_kind = kind
        elif terminal_m:
            _flush()
            current = [line]
            current_id = terminal_m.group("id")
            # Reclassify terminal-form items as resolved when seen inside an
            # "Open form" section. The Resolved-or-non-blocking section calls
            # this with kind="resolved" already.
            state = (terminal_m.group("state") or "").lower()
            current_kind = "resolved" if state in (
                "resolved", "non_blocking_limitation", "conceded",
                "accepted", "dropped_as_immaterial",
            ) else kind
        elif current is not None:
            current.append(line)
    _flush()
    return out


def extract_review_items(turn_text: str) -> list[ReviewItem]:
    """Extract structured review items from a Phase 2 turn body.

    Walks the four protocol sections (Open questions / Substantive
    disagreements / Resolved or non-blocking / Final-surfaced) and
    returns a flat list. Each item carries an optional `quote` or
    `after` anchor extracted from the ``> quote:`` / ``> after:``
    blockquote sub-lines the agent is asked to emit under each entry.

    Tolerant of:
    - Round-1 difference inventory (``## Diff vs … Phase 1`` — treated
      as a disagreement-style section with numbered items).
    - Missing sections (returns an empty list for those).
    - Items without any anchor markers (quote/after are None).
    """
    if not turn_text:
        return []

    out: list[ReviewItem] = []

    # Open questions section — heading text is "Open questions for <name>".
    # Match the heading prefix only; agent name varies. Phase 2 uses this
    # form with a "for X" suffix.
    open_q_match = re.search(r"^##\s+Open questions for .+?$", turn_text, re.MULTILINE)
    if open_q_match:
        body = _section_body_at(turn_text, open_q_match.end())
        out.extend(_walk_section_items(body, kind="question"))

    # Spec 0042 D1 — Phase 1 draft "Open Questions" section. Heading text
    # has no "for X" suffix and may carry a leading numeric prefix
    # (``## 5. Open Questions``). Skip if the Phase 2 form already matched
    # so we don't double-extract on a malformed transcript.
    if not open_q_match:
        open_q_p1 = re.search(
            r"^##\s+(?:\d+\.\s+)?Open Questions\s*$",
            turn_text,
            re.MULTILINE,
        )
        if open_q_p1:
            body = _section_body_at(turn_text, open_q_p1.end())
            out.extend(_walk_section_items(body, kind="question"))

    # Spec 0042 D1 — Phase 1 draft "Claims I Expect the Other Agent Might
    # Dispute" section. Tolerates a leading numeric prefix.
    claims_p1 = re.search(
        r"^##\s+(?:\d+\.\s+)?Claims I Expect the Other Agent Might Dispute\s*$",
        turn_text,
        re.MULTILINE,
    )
    if claims_p1:
        body = _section_body_at(turn_text, claims_p1.end())
        out.extend(_walk_section_items(body, kind="claim"))

    # Spec 0042 D6 — Round-1 difference inventory parses as ``kind="claim"``
    # (was ``"disagreement"``). Semantically these are contested points
    # being raised; only the items that survive into R≥2's
    # ``## Substantive disagreements I'm holding`` section harden into
    # held disagreements. Spec 0043's cross-round ledger tracks the
    # transition explicitly.
    diff_match = re.search(r"^##\s+Diff vs .+?Phase 1\s*$", turn_text, re.MULTILINE)
    if diff_match:
        body = _section_body_at(turn_text, diff_match.end())
        out.extend(_walk_section_items(body, kind="claim"))

    # Spec 0041 D1 — Phase 4 ``Issue ledger`` and ``Comments on the
    # current draft`` no longer get bucketed as "question". They have
    # different protocol semantics (issues are stateful and closed by
    # the drafter's revision; comments are non-blocking) and the
    # critique pane now renders them as their own typed groups.
    body_issues = extract_fenced_section(turn_text, "Issue ledger (delta + currently open)")
    if body_issues:
        out.extend(_walk_section_items(body_issues, kind="issue"))

    body_comments = extract_fenced_section(turn_text, "Comments on the current draft")
    if body_comments:
        out.extend(_walk_section_items(body_comments, kind="comment"))

    body_substantive = extract_fenced_section(turn_text, "Substantive disagreements I'm holding")
    if body_substantive:
        out.extend(_walk_section_disagreements(body_substantive, kind="disagreement"))

    body_resolved = extract_fenced_section(turn_text, "Resolved or non-blocking differences")
    if body_resolved:
        out.extend(_walk_section_disagreements(body_resolved, kind="resolved"))

    body_final = extract_fenced_section(turn_text, "Final-surfaced disagreements")
    if body_final:
        out.extend(_walk_section_disagreements(body_final, kind="disagreement"))

    return out


def _section_body_at(text: str, start: int) -> str:
    """Return text from `start` up to the next ``## `` heading or EOF."""
    rest = text[start:]
    next_heading = re.search(r"^##\s+\S", rest, re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def _normalize_for_match(s: str) -> str:
    """Whitespace + case-insensitive normalisation for anchor resolution."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip().lower()


def resolve_review_items(
    turn_text: str,
    prior_blocks: "list",  # list[BlockRecord] — typed loosely to avoid circular import
) -> list[ReviewItem]:
    """Spec 0034 — pre-resolve each review item's anchor against prior content.

    Walks the items extracted from ``turn_text`` and, for each item that
    carries a ``quote`` or ``after`` anchor, searches ``prior_blocks``
    for a matching block. Returns a new list of ``ReviewItem`` with
    ``block_id`` populated when a match is found.

    Resolution strategy:
    - ``quote: X``: find the first prior block whose normalised text
      contains the normalised quote. Whitespace + case-insensitive.
    - ``after: H``: find the first prior block whose normalised text
      equals the normalised heading (heading blocks are stripped of
      ``#`` markers when text-ified by ``assign_block_ids``).
    - No match → ``block_id`` stays ``None`` (UI falls back to the
      runtime text-scan).
    """
    items = extract_review_items(turn_text)
    if not prior_blocks:
        return items

    # Pre-normalise block text for O(N) match.
    norm_blocks = [(b, _normalize_for_match(b.text)) for b in prior_blocks]

    resolved: list[ReviewItem] = []
    for it in items:
        block_id: str | None = None
        if it.quote:
            needle = _normalize_for_match(it.quote)
            if needle:
                for b, btxt in norm_blocks:
                    if needle in btxt:
                        block_id = b.id
                        break
        if block_id is None and it.after:
            needle = _normalize_for_match(it.after)
            if needle:
                for b, btxt in norm_blocks:
                    if btxt == needle:
                        block_id = b.id
                        break
        resolved.append(ReviewItem(
            kind=it.kind,
            body=it.body,
            quote=it.quote,
            after=it.after,
            item_id=it.item_id,
            block_id=block_id,
        ))
    return resolved


def synthesise_brief_tldr(brief_text: str, *, max_sentences: int = 2, max_chars: int = 360) -> str | None:
    """Cheap TL;DR for a brief that doesn't carry an explicit Summary.

    Skips H1/H2 lines and code fences. Joins up to `max_sentences`
    sentence fragments, truncates at `max_chars` with an ellipsis. The
    UI uses this for the preflight `input` card; it's intentionally
    heuristic — a future spec can layer an LLM-generated TL;DR on top.
    """
    if not brief_text:
        return None
    in_fence = False
    candidate_lines: list[str] = []
    for raw in brief_text.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith(">") or line.startswith("---"):
            continue
        candidate_lines.append(line)
        if len(candidate_lines) >= 6:
            break
    if not candidate_lines:
        return None
    body = " ".join(candidate_lines)
    # Split on sentence terminators that aren't part of a number/abbreviation.
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", body)
    chosen = " ".join(sentences[:max_sentences]).strip()
    if not chosen:
        chosen = body
    if len(chosen) > max_chars:
        chosen = chosen[:max_chars].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return chosen or None
