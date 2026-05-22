"""Spec 0114 — section heading + counter marker regexes.

The single home for every regex literal used in turn parsing. The
parser (``src/dual_research/protocol/parse.py``) imports from here; no
regex literals live in the parser file.

The leading-tolerance pattern ``_LEAD`` mirrors the legacy parser so the
same set of "list marker / emphasis / blockquote prefix" forms keep
working without re-derivation. Counter regexes are unchanged from the
legacy parser; they are retained to feed the backward-compat shim.
"""

from __future__ import annotations

import re


# Common leading-tolerance: skip whitespace, list markers, emphasis,
# backticks, blockquote prefixes, heading hashes.
_LEAD = r"^[\s>*\-`#]*"


# ─── New-protocol section headings (## level) ─────────────────────────

SECTION_STANCE_RE = re.compile(r"^##\s+Stance\b", re.MULTILINE | re.IGNORECASE)
SECTION_ADDRESSING_RE = re.compile(
    r"^##\s+Addressing items raised against me\b",
    re.MULTILINE | re.IGNORECASE,
)
SECTION_RATIFYING_RE = re.compile(
    r"^##\s+Ratifying my own items\b",
    re.MULTILINE | re.IGNORECASE,
)
SECTION_NEW_ITEMS_RE = re.compile(
    r"^##\s+New items I'?m raising\b",
    re.MULTILINE | re.IGNORECASE,
)
SECTION_PHASE_ARTIFACT_RE = re.compile(
    r"^##\s+Phase artifact\b",
    re.MULTILINE | re.IGNORECASE,
)
SECTION_STATUS_RE = re.compile(r"^##\s+Status\b", re.MULTILINE | re.IGNORECASE)
SECTION_REVISED_DRAFT_RE = re.compile(
    r"^##\s+Revised draft\b",
    re.MULTILINE | re.IGNORECASE,
)
SECTION_CLOSEOUT_CONSTRAINTS_RE = re.compile(
    r"^##\s+Closeout constraints\b",
    re.MULTILINE | re.IGNORECASE,
)


# ─── Operation-block headings (### level) ─────────────────────────────

OP_RAISE_RE = re.compile(r"^###\s+RAISE\b", re.MULTILINE)
# ADDRESS / RESOLVE / ACKNOWLEDGE / WITHDRAW are all followed by an
# item ID on the same line. The ID is constrained to the canonical
# spec-0114 format (``ID_PATTERN`` in ``contract/ids.py``) so the
# parser stops cleanly at the end of the ID even when agents glue the
# response body onto the same line without a newline (e.g.
# ``### ADDRESS Q-plan-c-01The rest of the response...``). Spec 0122
# follow-up: the previous ``\S+\s*$`` form rejected those glued lines
# entirely, silently dropping every ADDRESS operation in the turn.
_ID_TAIL = r"(?:\s+(?P<id>[QDIC]-(?:input|plan|review)-[cg]-\d{2}))?"
OP_ADDRESS_RE = re.compile(
    r"^###\s+ADDRESS\b" + _ID_TAIL,
    re.MULTILINE,
)
OP_RESOLVE_RE = re.compile(
    r"^###\s+RESOLVE\b" + _ID_TAIL,
    re.MULTILINE,
)
OP_ACKNOWLEDGE_RE = re.compile(
    r"^###\s+ACKNOWLEDGE\b" + _ID_TAIL,
    re.MULTILINE,
)
OP_WITHDRAW_RE = re.compile(
    r"^###\s+WITHDRAW\b" + _ID_TAIL,
    re.MULTILINE,
)
# Spec 0149 §5.5 (D08) — mid-run channel for requesting evidence on a
# previously-stated item, distinct from raise-time
# ``evidence_required: bool``. Same ID-tail tolerance as the other
# id-bearing ops.
OP_REQUEST_EVIDENCE_RE = re.compile(
    r"^###\s+REQUEST_EVIDENCE\b" + _ID_TAIL,
    re.MULTILINE,
)
# Linked EVIDENCE record headings — appear inside an ADDRESS block.
OP_EVIDENCE_RE = re.compile(
    r"^###\s+EVIDENCE\s+for\s+(?P<id>\S+)\s*$",
    re.MULTILINE,
)


# ─── Phase-artifact sub-headings (### level inside ## Phase artifact) ─

ARTIFACT_AGREED_INTERPRETATION_RE = re.compile(
    r"^###\s+AGREED_INTERPRETATION\b",
    re.MULTILINE,
)
ARTIFACT_AGREED_PLAN_RE = re.compile(
    r"^###\s+AGREED_PLAN\b",
    re.MULTILINE,
)
ARTIFACT_AGREED_DRAFT_ACCEPTANCE_RE = re.compile(
    r"^###\s+AGREED_DRAFT_ACCEPTANCE\b",
    re.MULTILINE,
)


# ─── Status-footer counter markers ────────────────────────────────────

STATUS_RE = re.compile(_LEAD + r"STATUS:\s*`?([A-Z_]+)`?", re.MULTILINE)

RAISED_THIS_TURN_RE = re.compile(
    _LEAD + r"RAISED_THIS_TURN:\s*\[(?P<ids>[^\]]*)\]",
    re.MULTILINE,
)
ADDRESSED_THIS_TURN_RE = re.compile(
    _LEAD + r"ADDRESSED_THIS_TURN:\s*\[(?P<ids>[^\]]*)\]",
    re.MULTILINE,
)
RESOLVED_THIS_TURN_RE = re.compile(
    _LEAD + r"RESOLVED_THIS_TURN:\s*\[(?P<ids>[^\]]*)\]",
    re.MULTILINE,
)
ACKNOWLEDGED_THIS_TURN_RE = re.compile(
    _LEAD + r"ACKNOWLEDGED_THIS_TURN:\s*\[(?P<ids>[^\]]*)\]",
    re.MULTILINE,
)
WITHDRAWN_THIS_TURN_RE = re.compile(
    _LEAD + r"WITHDRAWN_THIS_TURN:\s*\[(?P<ids>[^\]]*)\]",
    re.MULTILINE,
)

OPEN_QUESTIONS_RE = re.compile(_LEAD + r"OPEN_QUESTIONS:\s*`?(\d+)`?", re.MULTILINE)
OPEN_DISAGREEMENTS_RE = re.compile(
    _LEAD + r"OPEN_DISAGREEMENTS:\s*`?(\d+)`?",
    re.MULTILINE,
)
OPEN_ISSUES_RE = re.compile(_LEAD + r"OPEN_ISSUES:\s*`?(\d+)`?", re.MULTILINE)
OPEN_COMMENTS_RE = re.compile(_LEAD + r"OPEN_COMMENTS:\s*`?(\d+)`?", re.MULTILINE)
ADDRESSED_QUESTIONS_RE = re.compile(
    _LEAD + r"ADDRESSED_QUESTIONS:\s*`?(\d+)`?",
    re.MULTILINE,
)
ADDRESSED_DISAGREEMENTS_RE = re.compile(
    _LEAD + r"ADDRESSED_DISAGREEMENTS:\s*`?(\d+)`?",
    re.MULTILINE,
)
ADDRESSED_ISSUES_RE = re.compile(
    _LEAD + r"ADDRESSED_ISSUES:\s*`?(\d+)`?",
    re.MULTILINE,
)
ADDRESSED_COMMENTS_RE = re.compile(
    _LEAD + r"ADDRESSED_COMMENTS:\s*`?(\d+)`?",
    re.MULTILINE,
)


# ─── Within-RAISE / within-block field markers ────────────────────────

# Generic field line "key: value" (single line) and "key: |" (block
# scalar) detection lives in the parser; we only expose the canonical
# field-name regexes here for one-shot extraction in tests / validation.

RAISE_KIND_RE = re.compile(
    r"^\s*kind:\s*(question|disagreement|issue|comment)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
RAISE_ANCHOR_TYPE_RE = re.compile(
    r"^\s*anchor_type:\s*(quote|after|none)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
RAISE_ANCHOR_TEXT_RE = re.compile(
    r"^\s*anchor_text:\s*(.*?)\s*$",
    re.MULTILINE,
)
RAISE_EVIDENCE_REQUIRED_RE = re.compile(
    r"^\s*evidence_required:\s*(true|false)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

ADDRESS_PROPOSES_STATUS_RE = re.compile(
    r"^\s*proposes_status:\s*(addressed|acknowledged_proposed)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


# ─── AGREED_DRAFT_ACCEPTANCE field markers ────────────────────────────

DRAFT_VERSION_RE = re.compile(
    r"^\s*draft_version:\s*v?(\d+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
DRAFT_HASH_RE = re.compile(
    r"^\s*draft_hash:\s*([0-9a-fA-F]+)\s*$",
    re.MULTILINE,
)
DRAFTER_RE = re.compile(_LEAD + r"DRAFTER:\s*`?([a-z]+)`?", re.MULTILINE)


# ─── EVIDENCE-record field markers ────────────────────────────────────

EVIDENCE_URL_RE = re.compile(r"^\s*-?\s*url:\s*(\S.*?)\s*$", re.MULTILINE)
EVIDENCE_TITLE_RE = re.compile(r"^\s*title:\s*(.*?)\s*$", re.MULTILINE)
EVIDENCE_SEARCH_QUERY_RE = re.compile(r"^\s*search_query:\s*(.*?)\s*$", re.MULTILINE)
EVIDENCE_FETCHED_AT_RE = re.compile(r"^\s*fetched_at:\s*(\S+)\s*$", re.MULTILINE)
EVIDENCE_EVENT_ID_RE = re.compile(r"^\s*evidence_event_id:\s*(\S+)\s*$", re.MULTILINE)


# ─── Legacy section markers (retained for the backward-compat shim) ──

# The spec keeps these so the legacy event payloads can be populated by
# the shim. The new parser does NOT use them; they remain only for the
# few legacy event fields that need them. Deprecated and slated for
# removal in spec 0115.

LEGACY_DRAFTER_RE = re.compile(_LEAD + r"DRAFTER:\s*`?([a-z]+)`?", re.MULTILINE)
LEGACY_OPEN_QUESTIONS_RE = re.compile(
    _LEAD + r"OPEN_QUESTIONS:\s*`?(\d+)`?",
    re.MULTILINE,
)
LEGACY_OPEN_ISSUES_RE = re.compile(
    _LEAD + r"OPEN_ISSUES:\s*`?(\d+)`?",
    re.MULTILINE,
)
LEGACY_BLOCKING_DISAGREEMENTS_RE = re.compile(
    _LEAD + r"BLOCKING_DISAGREEMENTS:\s*`?(\d+)`?",
    re.MULTILINE,
)
LEGACY_FINAL_SURFACED_DISAGREEMENTS_RE = re.compile(
    _LEAD + r"FINAL_SURFACED_DISAGREEMENTS:\s*`?(\d+)`?",
    re.MULTILINE,
)
LEGACY_BRIEF_ISSUES_RE = re.compile(
    _LEAD + r"BRIEF_ISSUES:\s*`?(\d+)`?",
    re.MULTILINE,
)
LEGACY_STRONGEST_REMAINING_OBJECTION_RE = re.compile(
    _LEAD + r"STRONGEST_REMAINING_OBJECTION:[ \t]*`?(.*)`?",
    re.MULTILINE,
)


# Spec 0036 / 0114: the "Evidence checked this round" heading the
# legacy parser used carried a ``\b`` anchor that failed when the body
# was glued directly to the heading line (e.g. ``## Evidence checked
# this roundThe search ...`` with no newline). The lookahead ``(?=\b|
# [A-Z])`` accepts EITHER a word boundary OR an uppercase letter so the
# glued case parses too. Verified against the bug pattern in
# ``runs/20260519-132908-backend-language-choice/phase4/round-03-claude.md``
# at line 39.
EVIDENCE_CHECKED_SECTION_RE = re.compile(
    r"^##\s+Evidence checked this round(?=\b|[A-Z])",
    re.MULTILINE,
)


def list_ids(arr_text: str) -> list[str]:
    """Split a ``[a, b, c]`` action-array body into a list of IDs.

    ``arr_text`` is the bracket interior; an empty / whitespace body
    returns ``[]``. Items are split on commas, stripped, and any
    surrounding backticks / quotes are removed.
    """
    body = (arr_text or "").strip()
    if not body:
        return []
    out: list[str] = []
    for token in body.split(","):
        cleaned = token.strip().strip("`'\"")
        if cleaned:
            out.append(cleaned)
    return out
