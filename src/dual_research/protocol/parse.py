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

EVIDENCE_CHECKED_SECTION_RE = re.compile(
    r"^##\s+Evidence checked this round\s*$", re.MULTILINE
)
CARRYOVER_AUDIT_SECTION_RE = re.compile(
    r"^##\s+Disagreement carryover audit\s*$", re.MULTILINE
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


def extract_revised_draft(turn_text: str) -> str | None:
    """Return the body under `## Revised draft` (next top-level `##` ends it).

    Used by Phase 4 to detect when the DRAFTER emits a new draft version inside
    their turn. Returns None when the section is absent or empty.
    """
    return extract_fenced_section(turn_text, "Revised draft")


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
