from __future__ import annotations

import re
from dataclasses import dataclass

from dual_research.contract.categories import Category
from dual_research.contract.evidence import EvidenceRecord
from dual_research.contract.markers import (
    ADDRESS_PROPOSES_STATUS_RE,
    ADDRESSED_THIS_TURN_RE,
    ACKNOWLEDGED_THIS_TURN_RE,
    ADDRESSED_COMMENTS_RE,
    ADDRESSED_DISAGREEMENTS_RE,
    ADDRESSED_ISSUES_RE,
    ADDRESSED_QUESTIONS_RE,
    DRAFT_VERSION_RE,
    EVIDENCE_EVENT_ID_RE,
    EVIDENCE_FETCHED_AT_RE,
    EVIDENCE_SEARCH_QUERY_RE,
    EVIDENCE_TITLE_RE,
    EVIDENCE_URL_RE,
    OP_ACKNOWLEDGE_RE,
    OP_ADDRESS_RE,
    OP_EVIDENCE_RE,
    OP_RAISE_RE,
    OP_REQUEST_EVIDENCE_RE,
    OP_RESOLVE_RE,
    OP_WITHDRAW_RE,
    OPEN_COMMENTS_RE,
    OPEN_DISAGREEMENTS_RE,
    OPEN_ISSUES_RE,
    OPEN_QUESTIONS_RE,
    RAISE_ANCHOR_TEXT_RE,
    RAISE_ANCHOR_TYPE_RE,
    RAISE_EVIDENCE_REQUIRED_RE,
    RAISE_KIND_RE,
    RAISED_THIS_TURN_RE,
    RESOLVED_THIS_TURN_RE,
    SECTION_ADDRESSING_RE,
    SECTION_NEW_ITEMS_RE,
    SECTION_PHASE_ARTIFACT_RE,
    SECTION_RATIFYING_RE,
    SECTION_REVISED_DRAFT_RE,
    SECTION_STANCE_RE,
    SECTION_STATUS_RE,
    STATUS_RE as STATUS_V2_RE,
    WITHDRAWN_THIS_TURN_RE,
    list_ids,
)
from dual_research.contract.operations import (
    AcknowledgeBlock,
    AddressBlock,
    OperationBlock,
    RaiseBlock,
    RequestEvidenceBlock,
    ResolveBlock,
    WithdrawBlock,
)
from dual_research.protocol.errors import Status
from dual_research.protocol.parse_v2 import ParsedTurnV2

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

# Spec 0036 / 0114: word-boundary OR uppercase-letter lookahead.
#
# Pre-0114 the regex used a plain ``\b`` after ``round``. The bug:
# agents sometimes glue the heading directly to the body with no
# newline or whitespace between them (e.g. ``## Evidence checked this
# roundThe search confirms…`` — see runs/20260519-132908-backend-
# language-choice/phase4/round-03-claude.md line 39). Between ``d`` and
# ``T`` there is no ``\b``, so the section was silently missed and the
# legacy parser thought no evidence was checked.
#
# ``(?=\b|[A-Z])`` accepts either a real word boundary (the normal
# case) or an uppercase letter immediately after ``round`` (the glued
# case). Keeps ``roundup`` / ``roundtable`` from false-positive because
# their continuation is lowercase.
EVIDENCE_CHECKED_SECTION_RE = re.compile(
    r"^##\s+Evidence checked this round(?=\b|[A-Z])", re.MULTILINE
)
CARRYOVER_AUDIT_SECTION_RE = re.compile(
    r"^##\s+Disagreement carryover audit\b", re.MULTILINE
)


def _escape_regex(s: str) -> str:
    return re.escape(s)


# ─── Spec 0090 § C — fenced code blocks must mask H2 detection ──────────────
# `extract_fenced_section` used to naively scan for ``^##\s+`` to find the
# next section boundary. That treated `##` lines INSIDE markdown fenced code
# blocks (``` … ```) as real headings and truncated the body early.
#
# In particular, agents emit the AGREED_PLAN as a fenced ```markdown block
# containing internal `## Final-surfaced disagreements (canonical)` headers
# — pre-fix, parse_turn extracted only the fence opener (`` ```markdown ``)
# as the agreed_plan body, breaking every FSD>0 convergence check and the
# Phase 3 drafting handoff. (See run 2c4f's stuck-AGREED loop for the
# real-world impact.)
#
# The fix maps the input's fenced regions, then ignores any H2 candidate
# that falls inside one. Both ```` ``` ```` and ```` ~~~ ```` fences are
# recognised; markdown does not allow nested fences so we treat the first
# matching closer as the end of the fence.

_FENCE_OPENER_RE = re.compile(r"^(```|~~~)[^\n]*$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+\S", re.MULTILINE)


def _fenced_ranges(text: str) -> list[tuple[int, int]]:
    """Return [(start, end)] character ranges that fall inside a fenced
    code block. ``start`` is the character after the opener's newline;
    ``end`` is the character before the closer's match. An unterminated
    fence runs to end-of-text.
    """
    ranges: list[tuple[int, int]] = []
    in_fence = False
    fence_start: int | None = None
    fence_marker: str | None = None
    for m in _FENCE_OPENER_RE.finditer(text):
        marker = m.group(1)
        if not in_fence:
            in_fence = True
            fence_start = m.end()
            fence_marker = marker
        else:
            # Only the same fence marker closes (``` closes ```; ~~~ closes ~~~).
            # If a different marker is seen first, treat it as nested literal text.
            if marker != fence_marker:
                continue
            ranges.append((fence_start or 0, m.start()))
            in_fence = False
            fence_start = None
            fence_marker = None
    if in_fence and fence_start is not None:
        ranges.append((fence_start, len(text)))
    return ranges


def _next_h2_outside_fences(text: str) -> "re.Match[str] | None":
    """First `^##\\s+\\S` match in ``text`` that is NOT inside a fenced
    code block. ``None`` if no such heading exists.
    """
    fenced = _fenced_ranges(text)
    for m in _H2_RE.finditer(text):
        pos = m.start()
        if any(start <= pos < end for start, end in fenced):
            continue
        return m
    return None


def extract_fenced_section(text: str, heading_name: str) -> str | None:
    """Return the body under a `## <heading_name>` heading, up to the next `## ` heading.

    Returns None if the heading is absent or the body is empty after stripping.
    Mirrors the original extractFencedSection() in protocol.mjs.

    Spec 0090 § C — `##` lines inside fenced code blocks (``` or ~~~) no
    longer falsely terminate the section. The target heading is still
    located via the naive regex (heading_name itself is escaped, and the
    heading line MUST be at the top level — we don't currently support
    fenced section headings as start anchors, which is fine: the
    protocol never puts section openers inside fences).
    """
    heading_re = re.compile(r"^##\s+" + _escape_regex(heading_name) + r"\s*$", re.MULTILINE)
    m = heading_re.search(text)
    if not m:
        return None
    start_body = m.end()
    rest = text[start_body:]
    next_heading = _next_h2_outside_fences(rest)
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

# Spec 0140 — keep this set in sync with the Spec 0114 section regexes in
# ``contract/markers.py`` (SECTION_STANCE_RE, SECTION_ADDRESSING_RE,
# SECTION_RATIFYING_RE, SECTION_NEW_ITEMS_RE, SECTION_PHASE_ARTIFACT_RE,
# SECTION_STATUS_RE, SECTION_CLOSEOUT_CONSTRAINTS_RE). ``## Revised draft``
# is deliberately absent — the extractor's start anchor matches it directly
# via ``_REVISED_DRAFT_HEADING_RE``; including it here would cause a
# same-section re-match.
_PROTOCOL_TOP_HEADINGS: frozenset[str] = frozenset({
    # ── v1 protocol headings (legacy phase2.py) ──
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
    # ── Spec 0114 v2 protocol headings (Deep Research) ──
    "stance",
    "addressing items raised against me",
    "ratifying my own items",
    "new items i'm raising",
    "phase artifact",
    "status",
    "closeout constraints",
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


# ─── Spec 0218 §3.2 — Section-delta drafter contract ──────────────────────────

# Operation kinds for the section-delta revised-draft body. Each block is a
# `### REPLACE_SECTION <heading>` / `### APPEND_SECTION <heading>` /
# `### DELETE_SECTION <heading>` / `### REPLACE_DRAFT_FULL` sub-heading inside
# the drafter's `## Revised draft` section. The orchestrator applies these
# against the current `draft-vN.md` to produce `draft-v(N+1).md`.

@dataclass(frozen=True)
class ReplaceSectionOp:
    heading: str
    body: str


@dataclass(frozen=True)
class AppendSectionOp:
    heading: str
    body: str


@dataclass(frozen=True)
class DeleteSectionOp:
    heading: str


@dataclass(frozen=True)
class ReplaceDraftFullOp:
    body: str


DraftDeltaOp = ReplaceSectionOp | AppendSectionOp | DeleteSectionOp | ReplaceDraftFullOp


@dataclass(frozen=True)
class RevisedDraftFull:
    """Legacy / escape-hatch shape — body is the full new draft text.

    Today reachable only via `### REPLACE_DRAFT_FULL` per spec 0218 §3.2;
    legacy full-prose `## Revised draft` bodies raise `ProtocolParseError
    ("revised_draft_body_missing_delta_op")` and route through repair.
    """

    content: str


@dataclass(frozen=True)
class RevisedDraftDeltas:
    """The new shape — a sequence of section-delta operations."""

    ops: tuple[DraftDeltaOp, ...]


RevisedDraftPayload = RevisedDraftFull | RevisedDraftDeltas


_REVISED_DRAFT_DELTA_HEADING_RE = re.compile(
    r"^###\s+(REPLACE_SECTION|APPEND_SECTION|DELETE_SECTION|REPLACE_DRAFT_FULL)\b(.*)$",
    re.MULTILINE,
)


def extract_revised_draft_deltas(turn_text: str) -> RevisedDraftPayload | None:
    """Parse the drafter's `## Revised draft` body as section-delta ops.

    Returns:
      - ``None`` — `## Revised draft` heading absent or body is empty
        after stripping horizontal rules / whitespace.
      - ``RevisedDraftDeltas(ops=...)`` — body contains one or more
        ``### REPLACE_SECTION`` / ``### APPEND_SECTION`` /
        ``### DELETE_SECTION`` blocks.
      - ``RevisedDraftFull(content=...)`` — body contains a single
        ``### REPLACE_DRAFT_FULL`` block (the escape hatch).

    Raises ``ProtocolParseError("revised_draft_body_missing_delta_op")``
    when the body is non-empty but contains NO delta-op sub-headings
    (i.e. legacy full-draft prose shape). The orchestrator routes this
    through the existing parse_with_repair flow.

    Multiple ``### REPLACE_DRAFT_FULL`` blocks: last-writer-wins.
    Mixed `### REPLACE_SECTION` + `### REPLACE_DRAFT_FULL`: full re-emit
    wins (the escape hatch is exclusive — no point applying deltas on
    top of a wholesale replacement).
    """
    from dual_research.protocol.errors import ProtocolParseError

    body = extract_revised_draft_inclusive(turn_text)
    if body is None or not body.strip():
        return None

    matches = list(_REVISED_DRAFT_DELTA_HEADING_RE.finditer(body))
    if not matches:
        # Body is present but carries no delta-op sub-heading — legacy
        # full-prose shape. Reject and route through repair.
        raise ProtocolParseError(
            "drafter", ["revised_draft_body_missing_delta_op"]
        )

    ops: list[DraftDeltaOp] = []
    full_replacement: ReplaceDraftFullOp | None = None

    for i, m in enumerate(matches):
        kind = m.group(1)
        rest = (m.group(2) or "").strip()
        block_start = m.end()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        block_body = body[block_start:block_end].strip()

        if kind == "REPLACE_DRAFT_FULL":
            # last-writer-wins across multiple REPLACE_DRAFT_FULL blocks.
            full_replacement = ReplaceDraftFullOp(body=block_body)
        elif kind == "REPLACE_SECTION":
            if not rest:
                # Heading argument missing — skip; the application layer
                # treats heading-less ops as no-ops.
                continue
            ops.append(ReplaceSectionOp(heading=rest, body=block_body))
        elif kind == "APPEND_SECTION":
            if not rest:
                continue
            ops.append(AppendSectionOp(heading=rest, body=block_body))
        elif kind == "DELETE_SECTION":
            if not rest:
                continue
            ops.append(DeleteSectionOp(heading=rest))

    if full_replacement is not None:
        # The escape hatch is exclusive — return RevisedDraftFull with
        # the last REPLACE_DRAFT_FULL body. Any per-section ops in the
        # same turn are dropped (the drafter chose the escape hatch).
        return RevisedDraftFull(content=full_replacement.body)

    return RevisedDraftDeltas(ops=tuple(ops))


# Heading normaliser for section matching. Case-insensitive, trim-equal —
# also strips a leading numeric prefix ("1. Summary" → "summary") so the
# drafter can write `### REPLACE_SECTION Summary` against `## 1. Summary`.
def _normalise_section_heading(heading: str) -> str:
    h = heading.strip().lower()
    # Strip leading "<digit>." or "<digit>.<digit>" prefix.
    h = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", h)
    return h


_DRAFT_SECTION_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def apply_revised_draft_deltas(
    *,
    prior_draft: str,
    payload: RevisedDraftPayload,
) -> tuple[str, list[str]]:
    """Apply a `RevisedDraftPayload` to ``prior_draft``, returning the new draft.

    Returns ``(new_draft_text, violations)`` where ``violations`` is a list
    of human-readable strings describing protocol-violation events the
    orchestrator should publish (e.g. ``REPLACE_SECTION`` promoted to
    ``APPEND_SECTION`` because no matching heading exists; two
    ``REPLACE_SECTION`` blocks for the same heading in one turn).

    Semantics (spec 0218 §3.2):
      - ``ReplaceDraftFullOp``: replace the entire draft.
      - ``ReplaceSectionOp``: replace the body of the matching ``## <h>``
        section. Heading match is case-insensitive trim-equal with
        numeric-prefix tolerance. Missing heading → promote to APPEND.
      - ``AppendSectionOp``: append a new ``## <h>`` section at the end.
      - ``DeleteSectionOp``: remove the matching section. Missing heading
        is a violation (recorded) but not an error.
      - Two ``ReplaceSectionOp`` for the same heading: apply in order,
        last-writer-wins, record a violation.
    """
    violations: list[str] = []

    if isinstance(payload, RevisedDraftFull):
        return payload.content, violations

    # Slice the prior draft into (heading_text, body) tuples in document
    # order. The pre-first-heading prelude (if any) is captured as a
    # special-cased "" heading at index 0.
    matches = list(_DRAFT_SECTION_HEADING_RE.finditer(prior_draft))
    sections: list[tuple[str, str]] = []
    if not matches:
        # No `## ` headings — treat the whole document as a single
        # untitled prelude; per-section ops will all promote to APPEND.
        prelude = prior_draft
        sections = []
    else:
        prelude = prior_draft[: matches[0].start()]
        for i, m in enumerate(matches):
            heading_line = m.group(0).rstrip()
            heading_text = m.group(1).strip()
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(prior_draft)
            body = prior_draft[body_start:body_end]
            sections.append((heading_text, body))

    seen_replace: dict[str, int] = {}
    for op in payload.ops:
        if isinstance(op, ReplaceSectionOp):
            target = _normalise_section_heading(op.heading)
            idx: int | None = None
            for i, (h, _) in enumerate(sections):
                if _normalise_section_heading(h) == target:
                    idx = i
                    break
            if idx is None:
                violations.append(
                    f"REPLACE_SECTION {op.heading!r} promoted to APPEND "
                    "(no matching heading in prior draft)"
                )
                sections.append((op.heading, "\n" + op.body + "\n"))
            else:
                if target in seen_replace:
                    violations.append(
                        f"REPLACE_SECTION {op.heading!r} appears twice in "
                        "one turn — last-writer-wins"
                    )
                seen_replace[target] = idx
                sections[idx] = (sections[idx][0], "\n" + op.body + "\n")
        elif isinstance(op, AppendSectionOp):
            sections.append((op.heading, "\n" + op.body + "\n"))
        elif isinstance(op, DeleteSectionOp):
            target = _normalise_section_heading(op.heading)
            idx = None
            for i, (h, _) in enumerate(sections):
                if _normalise_section_heading(h) == target:
                    idx = i
                    break
            if idx is None:
                violations.append(
                    f"DELETE_SECTION {op.heading!r} — no matching heading"
                )
            else:
                sections.pop(idx)

    rendered_parts: list[str] = []
    if prelude:
        rendered_parts.append(prelude.rstrip("\n"))
    for heading_text, body in sections:
        rendered_parts.append(f"## {heading_text}".rstrip())
        rendered_parts.append(body.rstrip("\n"))

    new_text = "\n\n".join(p for p in rendered_parts if p) + "\n"
    return new_text, violations


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


# ─── Spec 0114 — new-protocol parser (parse_turn_v2) ──────────────────
#
# Reads a turn in the new Deep Research output protocol and returns a
# ParsedTurnV2 carrying typed operation blocks, action-array IDs, the
# STATUS value, optional phase artifact text, and self-reported
# counters. The legacy parse_turn / ParsedTurn remain available for
# the backward-compat shim path during the migration.


# Regex for "key: value" single-line fields (used inside operation
# block bodies). The capture group is the raw value text after the
# colon, NOT stripped of surrounding whitespace.
_FIELD_LINE_RE = re.compile(r"^\s*([A-Za-z_]+)\s*:\s*(.*?)\s*$", re.MULTILINE)

# Regex for "key: |" line indicating a YAML block scalar follows.
_BLOCK_SCALAR_OPENER_RE = re.compile(r"^\s*([A-Za-z_]+)\s*:\s*\|\s*$", re.MULTILINE)


def _extract_block_scalar(text: str, start_after: int) -> tuple[str, int]:
    """Extract an indented YAML-style block scalar starting after
    ``start_after``. Returns ``(body, end_offset)`` where ``end_offset``
    is the character index in ``text`` where the block ended.

    The first non-empty line after ``start_after`` establishes the
    indent prefix; subsequent lines belonging to the block are those
    starting with at least that indent. The block ends at the first
    less-indented non-empty line.
    """
    lines = text[start_after:].splitlines(keepends=True)
    body_lines: list[str] = []
    indent: str | None = None
    consumed = 0
    for line in lines:
        if not line.strip():
            # Blank line — part of the scalar if we already started, otherwise
            # leading whitespace we skip.
            if indent is None:
                consumed += len(line)
                continue
            body_lines.append("")
            consumed += len(line)
            continue
        # Determine leading indent (spaces only — YAML block scalars
        # don't use tabs).
        stripped = line.lstrip(" ")
        leading = len(line) - len(stripped)
        if indent is None:
            if leading == 0:
                # First non-blank line has no indent — block scalar is empty.
                break
            indent = " " * leading
            body_lines.append(stripped.rstrip("\n"))
            consumed += len(line)
            continue
        if leading >= len(indent):
            body_lines.append(line[len(indent):].rstrip("\n"))
            consumed += len(line)
            continue
        # Less-indented line: block ends here.
        break
    body = "\n".join(body_lines).rstrip()
    return body, start_after + consumed


def _section_body(
    text: str,
    *,
    start_match: "re.Match[str]",
    end_patterns: list["re.Pattern[str]"],
) -> str:
    """Return the body of a section starting at ``start_match`` up to
    the first match of any pattern in ``end_patterns``."""
    start = start_match.end()
    rest = text[start:]
    end_offsets = []
    for pat in end_patterns:
        m = pat.search(rest)
        if m:
            end_offsets.append(m.start())
    if not end_offsets:
        return rest
    return rest[: min(end_offsets)]


# All section patterns the parser knows about — used to define section
# boundaries when extracting the body of a specific section.
_ALL_SECTION_PATTERNS = [
    SECTION_STANCE_RE,
    SECTION_ADDRESSING_RE,
    SECTION_RATIFYING_RE,
    SECTION_NEW_ITEMS_RE,
    SECTION_PHASE_ARTIFACT_RE,
    SECTION_REVISED_DRAFT_RE,
    SECTION_STATUS_RE,
]


def _other_section_patterns(this: "re.Pattern[str]") -> list["re.Pattern[str]"]:
    return [p for p in _ALL_SECTION_PATTERNS if p is not this]


def _extract_section_body(text: str, pattern: "re.Pattern[str]") -> str | None:
    """Return the body of the section identified by ``pattern``.

    Spec 0122 follow-up: agents sometimes emit duplicate section
    headings — typically a "private reasoning" preamble with a stray
    ``## Stance`` / ``## Addressing items raised against me`` followed
    by the canonical structured turn. The naive ``pattern.search(...)``
    grabs the FIRST occurrence, which for the duplicate-heading case
    points at the freeform preamble and contains none of the real
    operation blocks.

    Heuristic: when a section heading matches multiple times, score
    each candidate body by how many operation-block openers it contains
    and keep the highest-scoring body. Ties break by the LATER position
    (the canonical structure typically follows any preamble). When all
    candidates score zero (e.g. the section legitimately has no
    operation blocks, like ``## Stance`` itself), the FIRST occurrence
    wins — matching legacy behaviour.
    """
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    if len(matches) == 1:
        return _section_body(
            text,
            start_match=matches[0],
            end_patterns=_other_section_patterns(pattern),
        ).strip() or None

    end_patterns = _other_section_patterns(pattern)
    best_body: str | None = None
    best_score: tuple[int, int] = (-1, -1)
    for m in matches:
        body = _section_body(
            text, start_match=m, end_patterns=end_patterns,
        ).strip()
        score = _operation_block_density(body)
        # Higher density wins; on tie, the later occurrence wins.
        key = (score, m.start())
        if key > best_score:
            best_score = key
            best_body = body or None
    return best_body


# Block openers we use to score section candidates. Cheap substring
# checks — false positives don't matter since the operation parser
# re-validates each opener with its full regex.
_OP_OPENER_SNIPPETS = (
    "### RAISE",
    "### ADDRESS",
    "### RESOLVE",
    "### ACKNOWLEDGE",
    "### WITHDRAW",
)


def _operation_block_density(body: str) -> int:
    """Cheap heuristic — count operation-block openers in ``body``."""
    if not body:
        return 0
    return sum(body.count(snippet) for snippet in _OP_OPENER_SNIPPETS)


# ─── Operation-block extraction ───────────────────────────────────────


def _split_blocks(section_body: str, openers: list["re.Pattern[str]"]) -> list[tuple[str, "re.Match[str]"]]:
    """Walk through ``section_body`` and return the substrings
    delimited by ``### `` operation-block headings.

    Each return entry is ``(raw_block_text, opening_match)``. The
    ``opening_match`` is one of the supplied openers. A trailing block
    runs to the end of ``section_body``.
    """
    matches: list[tuple[int, "re.Match[str]"]] = []
    for pat in openers:
        for m in pat.finditer(section_body):
            matches.append((m.start(), m))
    matches.sort(key=lambda x: x[0])
    out: list[tuple[str, "re.Match[str]"]] = []
    for i, (start, m) in enumerate(matches):
        end = matches[i + 1][0] if i + 1 < len(matches) else len(section_body)
        out.append((section_body[start:end], m))
    return out


def _strip_evidence_block(raw: str) -> tuple[str, str]:
    """Split an ADDRESS block body into (pre_evidence_body, evidence_yaml_text).

    The evidence: yaml-list-style block runs from the first occurrence
    of ``evidence:`` on its own line (with optional whitespace) until
    the next sibling field key at the same indent or the end of the
    block.
    """
    m = re.search(r"^\s*evidence\s*:\s*$", raw, re.MULTILINE)
    if not m:
        return raw, ""
    head = raw[: m.start()]
    rest = raw[m.end():]
    # Sibling field marker = a non-indented line containing "<key>:"
    # at zero indent inside the block. Use proposes_status as the
    # primary terminator since it always follows the evidence list.
    end_m = re.search(r"^[a-z_]+\s*:.*$", rest, re.MULTILINE)
    if not end_m:
        return head, rest
    return head + rest[end_m.start():], rest[: end_m.start()]


def _parse_evidence_yaml(yaml_text: str, *, item_id: str) -> list[EvidenceRecord]:
    """Parse the YAML-list-of-mappings under ``evidence:`` into records.

    Tolerant: each entry begins with ``- url:`` or just ``url:`` on its
    own indented line. Fields after the leading url: are mapped by name.
    The ``content_excerpt:`` field is a YAML block scalar.
    """
    records: list[EvidenceRecord] = []
    # Split entries on the leading "- url:" marker.
    entry_starts = [m.start() for m in re.finditer(
        r"^\s*-\s*url\s*:", yaml_text, re.MULTILINE,
    )]
    if not entry_starts:
        return records
    entry_starts.append(len(yaml_text))
    for i in range(len(entry_starts) - 1):
        chunk = yaml_text[entry_starts[i]: entry_starts[i + 1]]
        url_m = EVIDENCE_URL_RE.search(chunk)
        title_m = EVIDENCE_TITLE_RE.search(chunk)
        sq_m = EVIDENCE_SEARCH_QUERY_RE.search(chunk)
        fa_m = EVIDENCE_FETCHED_AT_RE.search(chunk)
        eid_m = EVIDENCE_EVENT_ID_RE.search(chunk)
        # content_excerpt: |  + indented block
        excerpt_m = re.search(
            r"^\s*content_excerpt\s*:\s*\|\s*$",
            chunk,
            re.MULTILINE,
        )
        excerpt = ""
        if excerpt_m:
            excerpt, _ = _extract_block_scalar(chunk, excerpt_m.end())
        records.append(EvidenceRecord(
            item_id=item_id,
            url=(url_m.group(1).strip() if url_m else ""),
            title=(title_m.group(1).strip() if title_m else ""),
            search_query=(sq_m.group(1).strip() if sq_m else ""),
            fetched_at=(fa_m.group(1).strip() if fa_m else ""),
            evidence_event_id=(eid_m.group(1).strip() if eid_m else ""),
            content_excerpt=excerpt,
        ))
    return records


def _parse_field_block_scalar(block_text: str, field_name: str) -> str:
    """Return the body of ``<field_name>: |`` followed by an indented
    block, or empty string when absent."""
    m = re.search(
        r"^\s*" + re.escape(field_name) + r"\s*:\s*\|\s*$",
        block_text,
        re.MULTILINE,
    )
    if not m:
        return ""
    body, _ = _extract_block_scalar(block_text, m.end())
    return body


def _parse_raise_block(raw: str) -> RaiseBlock | None:
    kind_m = RAISE_KIND_RE.search(raw)
    if not kind_m:
        return None
    body = _parse_field_block_scalar(raw, "body")
    anchor_type_m = RAISE_ANCHOR_TYPE_RE.search(raw)
    anchor_text_m = RAISE_ANCHOR_TEXT_RE.search(raw)
    evidence_req_m = RAISE_EVIDENCE_REQUIRED_RE.search(raw)
    blockquote_m = re.search(
        r"^\s*>\s*(?:quote|after)\s*:\s*(.+?)\s*$",
        raw,
        re.MULTILINE | re.IGNORECASE,
    )
    try:
        kind = Category(kind_m.group(1).lower())
    except ValueError:
        return None
    return RaiseBlock(
        kind=kind,
        body=body.strip(),
        anchor_type=(anchor_type_m.group(1).lower() if anchor_type_m else "none"),
        anchor_text=(anchor_text_m.group(1).strip() if anchor_text_m else ""),
        evidence_required=(
            (evidence_req_m.group(1).lower() == "true") if evidence_req_m else False
        ),
        blockquote_anchor=(blockquote_m.group(1).strip() if blockquote_m else ""),
        raw_text=raw,
    )


def _parse_address_block(raw: str, *, item_id: str | None) -> AddressBlock | None:
    if not item_id:
        return None
    pre_evidence, evidence_yaml = _strip_evidence_block(raw)
    response = _parse_field_block_scalar(pre_evidence, "response")
    proposes_m = ADDRESS_PROPOSES_STATUS_RE.search(raw)
    evidence_records = _parse_evidence_yaml(evidence_yaml, item_id=item_id)
    return AddressBlock(
        item_id=item_id,
        response=response.strip(),
        evidence=evidence_records,
        proposes_status=(
            proposes_m.group(1).lower() if proposes_m else "addressed"
        ),
        raw_text=raw,
    )


def _parse_resolve_block(raw: str, *, item_id: str | None) -> ResolveBlock | None:
    if not item_id:
        return None
    reason = _parse_field_block_scalar(raw, "reason")
    return ResolveBlock(item_id=item_id, reason=reason.strip(), raw_text=raw)


def _parse_acknowledge_block(
    raw: str,
    *,
    item_id: str | None,
    section: str,
) -> AcknowledgeBlock | None:
    if not item_id:
        return None
    reason = _parse_field_block_scalar(raw, "reason")
    return AcknowledgeBlock(
        item_id=item_id,
        reason=reason.strip(),
        section=section,
        raw_text=raw,
    )


def _parse_withdraw_block(raw: str, *, item_id: str | None) -> WithdrawBlock | None:
    if not item_id:
        return None
    reason = _parse_field_block_scalar(raw, "reason")
    return WithdrawBlock(item_id=item_id, reason=reason.strip(), raw_text=raw)


def _parse_request_evidence_block(
    raw: str,
    *,
    item_id: str | None,
) -> RequestEvidenceBlock | None:
    """Spec 0149 §5.5 (D08) — parse a ``### REQUEST_EVIDENCE <item-id>`` block.

    The block carries a single ``reason:`` field (block-scalar). An empty
    or whitespace-only reason is rejected (returns None); the validator
    additionally enforces that the requester ≠ original author and that
    ``item_id`` references an existing item.
    """
    if not item_id:
        return None
    reason = _parse_field_block_scalar(raw, "reason")
    if not reason or not reason.strip():
        return None
    return RequestEvidenceBlock(
        item_id=item_id,
        reason=reason.strip(),
        raw_text=raw,
    )


# ─── Action-array + counter parsing ───────────────────────────────────


def _parse_action_array(text: str, pat: "re.Pattern[str]") -> list[str]:
    m = pat.search(text)
    if not m:
        return []
    return list_ids(m.group("ids"))


def _parse_counter(text: str, pat: "re.Pattern[str]") -> int | None:
    m = pat.search(text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None


# ─── Top-level parse_turn_v2 ──────────────────────────────────────────


def parse_turn_v2(text: str) -> ParsedTurnV2:
    """Parse a Deep Research turn text into a typed ``ParsedTurnV2``.

    The parser is best-effort: malformed blocks are skipped rather than
    raised. The validator (``contract.validate_parsed``) is the authority
    on rejection; ``parse_turn_v2`` always returns a value so the
    validator can report errors against it.
    """
    text = text or ""

    # STATUS
    status_m = STATUS_V2_RE.search(text)
    status = status_m.group(1) if status_m else None

    # Section bodies
    addressing_body = _extract_section_body(text, SECTION_ADDRESSING_RE) or ""
    ratifying_body = _extract_section_body(text, SECTION_RATIFYING_RE) or ""
    new_items_body = _extract_section_body(text, SECTION_NEW_ITEMS_RE) or ""
    phase_artifact = _extract_section_body(text, SECTION_PHASE_ARTIFACT_RE)
    revised_draft = _extract_section_body(text, SECTION_REVISED_DRAFT_RE)
    stance = _extract_section_body(text, SECTION_STANCE_RE)

    blocks: list[OperationBlock] = []

    # RAISE blocks live in `## New items I'm raising`.
    for raw, _ in _split_blocks(new_items_body, [OP_RAISE_RE]):
        rb = _parse_raise_block(raw)
        if rb is not None:
            blocks.append(rb)

    # ADDRESS / ACKNOWLEDGE / REQUEST_EVIDENCE blocks live in `## Addressing
    # items raised against me`. REQUEST_EVIDENCE (spec 0149 §5.5, D08) is
    # a mid-run response op — instead of immediately ADDRESSing an item,
    # the responder asks the original author to supply evidence first.
    for raw, opener_m in _split_blocks(
        addressing_body,
        [OP_ADDRESS_RE, OP_ACKNOWLEDGE_RE, OP_REQUEST_EVIDENCE_RE, OP_EVIDENCE_RE],
    ):
        if OP_ADDRESS_RE.match(opener_m.group(0)):
            ab = _parse_address_block(
                raw,
                item_id=opener_m.group("id") if opener_m.groupdict().get("id") else None,
            )
            if ab is not None:
                blocks.append(ab)
        elif OP_REQUEST_EVIDENCE_RE.match(opener_m.group(0)):
            reb = _parse_request_evidence_block(
                raw,
                item_id=opener_m.group("id") if opener_m.groupdict().get("id") else None,
            )
            if reb is not None:
                blocks.append(reb)
        elif OP_ACKNOWLEDGE_RE.match(opener_m.group(0)):
            ack = _parse_acknowledge_block(
                raw,
                item_id=opener_m.group("id") if opener_m.groupdict().get("id") else None,
                section="addressing",
            )
            if ack is not None:
                blocks.append(ack)
        elif OP_EVIDENCE_RE.match(opener_m.group(0)):
            # Standalone EVIDENCE-for-<id> block (alternative to inline
            # evidence: under the ADDRESS body). Attach to the matching
            # ADDRESS block when one already exists.
            ev_id = opener_m.group("id")
            attached = False
            for blk in blocks:
                if isinstance(blk, AddressBlock) and blk.item_id == ev_id:
                    rec = _parse_evidence_yaml("- " + raw, item_id=ev_id)
                    if rec:
                        # Replace the block with one that has appended evidence.
                        new_evidence = list(blk.evidence) + rec
                        idx = blocks.index(blk)
                        blocks[idx] = AddressBlock(
                            item_id=blk.item_id,
                            response=blk.response,
                            evidence=new_evidence,
                            proposes_status=blk.proposes_status,
                            raw_text=blk.raw_text,
                        )
                        attached = True
                        break
            if not attached:
                # No matching ADDRESS; ignore the orphan record.
                pass

    # RESOLVE / ACKNOWLEDGE / WITHDRAW blocks live in `## Ratifying my own items`.
    for raw, opener_m in _split_blocks(
        ratifying_body,
        [OP_RESOLVE_RE, OP_ACKNOWLEDGE_RE, OP_WITHDRAW_RE],
    ):
        if OP_RESOLVE_RE.match(opener_m.group(0)):
            rb = _parse_resolve_block(
                raw,
                item_id=opener_m.group("id") if opener_m.groupdict().get("id") else None,
            )
            if rb is not None:
                blocks.append(rb)
        elif OP_ACKNOWLEDGE_RE.match(opener_m.group(0)):
            ack = _parse_acknowledge_block(
                raw,
                item_id=opener_m.group("id") if opener_m.groupdict().get("id") else None,
                section="ratifying",
            )
            if ack is not None:
                blocks.append(ack)
        elif OP_WITHDRAW_RE.match(opener_m.group(0)):
            wb = _parse_withdraw_block(
                raw,
                item_id=opener_m.group("id") if opener_m.groupdict().get("id") else None,
            )
            if wb is not None:
                blocks.append(wb)

    # Action arrays — searched anywhere in the turn (the status footer
    # is at the end but tolerance for placement is cheap).
    raised_ids = _parse_action_array(text, RAISED_THIS_TURN_RE)
    addressed_ids = _parse_action_array(text, ADDRESSED_THIS_TURN_RE)
    resolved_ids = _parse_action_array(text, RESOLVED_THIS_TURN_RE)
    acknowledged_ids = _parse_action_array(text, ACKNOWLEDGED_THIS_TURN_RE)
    withdrawn_ids = _parse_action_array(text, WITHDRAWN_THIS_TURN_RE)

    # Per-kind counters.
    counters: dict[str, int] = {}
    for label, pat in [
        ("OPEN_QUESTIONS", OPEN_QUESTIONS_RE),
        ("OPEN_DISAGREEMENTS", OPEN_DISAGREEMENTS_RE),
        ("OPEN_ISSUES", OPEN_ISSUES_RE),
        ("OPEN_COMMENTS", OPEN_COMMENTS_RE),
        ("ADDRESSED_QUESTIONS", ADDRESSED_QUESTIONS_RE),
        ("ADDRESSED_DISAGREEMENTS", ADDRESSED_DISAGREEMENTS_RE),
        ("ADDRESSED_ISSUES", ADDRESSED_ISSUES_RE),
        ("ADDRESSED_COMMENTS", ADDRESSED_COMMENTS_RE),
    ]:
        val = _parse_counter(text, pat)
        if val is not None:
            counters[label] = val

    return ParsedTurnV2(
        status=status,
        blocks=blocks,
        raised_this_turn=raised_ids,
        addressed_this_turn=addressed_ids,
        resolved_this_turn=resolved_ids,
        acknowledged_this_turn=acknowledged_ids,
        withdrawn_this_turn=withdrawn_ids,
        counters=counters,
        phase_artifact=phase_artifact,
        revised_draft=revised_draft,
        stance=stance,
    )


# ─── ID assignment (post-parse) ───────────────────────────────────────


def assign_raise_ids(
    parsed: ParsedTurnV2,
    *,
    phase: int,
    raiser: str,
    next_seq_provider,
) -> ParsedTurnV2:
    """Stamp orchestrator-assigned IDs onto the parser's RAISE blocks.

    ``next_seq_provider`` is a callable ``(kind: Category) -> int`` that
    returns the next monotonic sequence in the (kind, phase, raiser)
    namespace and advances it. Returns a new ``ParsedTurnV2`` with
    ``raised_this_turn`` populated with the stamped IDs.

    The parser itself does NOT call this — the orchestrator owns the
    ledger and the next-seq counters, so it invokes ``assign_raise_ids``
    after ``parse_turn_v2`` returns.
    """
    from dual_research.contract.ids import format_id

    new_raised: list[str] = []
    new_blocks: list[OperationBlock] = []
    for blk in parsed.blocks:
        if isinstance(blk, RaiseBlock):
            seq = next_seq_provider(blk.kind)
            item_id = format_id(blk.kind, phase, raiser, seq)
            new_raised.append(item_id)
            # RaiseBlock doesn't itself carry the ID — the orchestrator
            # records the assignment separately. We surface it via
            # raised_this_turn on the returned ParsedTurnV2.
            new_blocks.append(blk)
        else:
            new_blocks.append(blk)
    return ParsedTurnV2(
        status=parsed.status,
        blocks=new_blocks,
        raised_this_turn=new_raised,
        addressed_this_turn=parsed.addressed_this_turn,
        resolved_this_turn=parsed.resolved_this_turn,
        acknowledged_this_turn=parsed.acknowledged_this_turn,
        withdrawn_this_turn=parsed.withdrawn_this_turn,
        counters=parsed.counters,
        phase_artifact=parsed.phase_artifact,
        revised_draft=parsed.revised_draft,
        stance=parsed.stance,
    )


# ─── Phase-artifact extraction helpers ────────────────────────────────


def extract_agreed_interpretation_body(turn_text: str) -> str | None:
    """Return the body under ``## Phase artifact`` > ``### AGREED_INTERPRETATION``.

    Phase 0 hash-target. Returns ``None`` when the artifact section is
    absent.
    """
    artifact = _extract_section_body(turn_text, SECTION_PHASE_ARTIFACT_RE)
    if not artifact:
        return None
    m = re.search(r"^###\s+AGREED_INTERPRETATION\b", artifact, re.MULTILINE)
    if not m:
        return None
    body_start = m.end()
    return artifact[body_start:].strip() or None


def extract_agreed_plan_body(turn_text: str) -> str | None:
    """Return the body under ``## Phase artifact`` > ``### AGREED_PLAN``.

    Phase 2 hash-target. Returns ``None`` when the artifact section is
    absent.
    """
    artifact = _extract_section_body(turn_text, SECTION_PHASE_ARTIFACT_RE)
    if not artifact:
        return None
    m = re.search(r"^###\s+AGREED_PLAN\b", artifact, re.MULTILINE)
    if not m:
        return None
    return artifact[m.end():].strip() or None


def extract_agreed_draft_acceptance(turn_text: str) -> tuple[int, str] | None:
    """Return ``(draft_version, endorsement)`` from ``### AGREED_DRAFT_ACCEPTANCE``.

    Phase 4 acceptance block. Returns ``None`` when the section is
    absent. Missing fields default to ``(0, "")`` per field. Spec 0214
    dropped the agent-emitted ``draft_hash`` field — the orchestrator
    owns provenance via ``Phase4Complete.draft_file_sha256``.
    """
    artifact = _extract_section_body(turn_text, SECTION_PHASE_ARTIFACT_RE)
    if not artifact:
        return None
    m = re.search(r"^###\s+AGREED_DRAFT_ACCEPTANCE\b", artifact, re.MULTILINE)
    if not m:
        return None
    body = artifact[m.end():]
    ver_m = DRAFT_VERSION_RE.search(body)
    endorsement = _parse_field_block_scalar(body, "endorsement")
    version = int(ver_m.group(1)) if ver_m else 0
    return version, endorsement.strip()


def extract_drafter_from_agreed_plan(agreed_plan_body: str) -> str | None:
    """Return the ``DRAFTER:`` line value from an AGREED_PLAN body.

    Returns ``None`` when the line is absent or the value is unknown.
    """
    m = re.search(
        r"^\s*DRAFTER:\s*`?(claude|openai)`?\s*$",
        agreed_plan_body or "",
        re.MULTILINE | re.IGNORECASE,
    )
    return m.group(1).lower() if m else None
