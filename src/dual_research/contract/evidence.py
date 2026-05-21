"""Spec 0114 — evidence record schema + anti-hallucination validation.

Every ADDRESS operation on an item with ``evidence_required: true`` must
emit one or more linked evidence records. Each record carries the URL,
title, search query, fetched-at timestamp, the ``evidence_event_id``
(must match a real ``ToolEvent.event_id`` from this turn's
``TurnSearchAudit``), and a content excerpt (≥200, ≤2000 chars) that
must appear as a substring of the consulted page content after light
normalization.

Validation produces ``EvidenceFlag`` results which the parser converts
to ``ParseError`` entries when any flag fires. A failed evidence
validation makes the entire ADDRESS operation invalid: the item is not
transitioned to ``addressed`` and the orchestrator emits a
``closeout_urged`` event for it in the next round.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


MIN_CONTENT_EXCERPT_CHARS = 200
MAX_CONTENT_EXCERPT_CHARS = 2000


@dataclass(frozen=True)
class EvidenceRecord:
    """One structured evidence record linked to one item ID.

    ``content_excerpt`` is the verbatim slice of the consulted page body
    the agent excerpted; it must match the source content after the
    normalization in ``_normalize_for_match``.

    Spec 0144 added denormalised round + actor fields so downstream
    surfaces (the per-card SOURCES segment) can render "raised in r1,
    answered in r2, attached by claude" without re-walking the event
    stream. Fields default to safe zero/empty values so callers
    constructing records from the protocol parser (which has neither
    round nor actor in scope) don't break.
    """

    item_id: str
    url: str
    title: str
    search_query: str
    fetched_at: str
    evidence_event_id: str
    content_excerpt: str
    raised_in_round: int = 0
    answered_in_round: int = 0
    requested_by: str | None = None
    provided_by: str = ""
    attached_at: str = ""


@dataclass(frozen=True)
class EvidenceFlag:
    """One anti-hallucination check that fired against an evidence record.

    ``code`` is one of:
    - ``"evidence_event_id_fabricated"`` — event_id does not match any
      ToolEvent in the turn's audit.
    - ``"evidence_url_not_consulted"`` — the record's URL is not in
      ``consulted_sources`` of the referenced ToolEvent.
    - ``"evidence_content_not_in_source"`` — the content_excerpt does
      not appear as a substring of the consulted content after
      normalization.
    - ``"evidence_content_too_short"`` — excerpt < ``MIN_CONTENT_EXCERPT_CHARS``.
    - ``"evidence_content_too_long"`` — excerpt > ``MAX_CONTENT_EXCERPT_CHARS``.
    """

    code: str
    message: str
    record: EvidenceRecord


_WS_RE = re.compile(r"\s+")
_SMART_QUOTES = {
    "‘": "'", "’": "'",
    "“": '"', "”": '"',
    "–": "-", "—": "-",
}


def _normalize_for_match(text: str) -> str:
    """Light normalization for substring matching.

    Collapses whitespace, folds smart quotes / em-dashes to ASCII,
    normalizes line endings. Preserves case (the substring check
    treats content excerpts as case-sensitive — agents copy verbatim).
    """
    if not text:
        return ""
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    for smart, plain in _SMART_QUOTES.items():
        out = out.replace(smart, plain)
    out = _WS_RE.sub(" ", out)
    return out.strip()


def validate_evidence(
    record: EvidenceRecord,
    *,
    tool_events: list[dict],
) -> list[EvidenceFlag]:
    """Run anti-hallucination checks on a single evidence record.

    ``tool_events`` is the ``tool_events`` list from a
    ``TurnSearchAudit`` payload (dicts as produced by ``audit_to_dict``).
    Returns a list of ``EvidenceFlag`` for every check that fired.
    """
    flags: list[EvidenceFlag] = []

    excerpt = record.content_excerpt or ""
    excerpt_len = len(excerpt)
    if excerpt_len < MIN_CONTENT_EXCERPT_CHARS:
        flags.append(EvidenceFlag(
            code="evidence_content_too_short",
            message=(
                f"content_excerpt is {excerpt_len} chars; "
                f"minimum is {MIN_CONTENT_EXCERPT_CHARS}"
            ),
            record=record,
        ))
    if excerpt_len > MAX_CONTENT_EXCERPT_CHARS:
        flags.append(EvidenceFlag(
            code="evidence_content_too_long",
            message=(
                f"content_excerpt is {excerpt_len} chars; "
                f"maximum is {MAX_CONTENT_EXCERPT_CHARS}"
            ),
            record=record,
        ))

    matching = next(
        (ev for ev in tool_events if ev.get("event_id") == record.evidence_event_id),
        None,
    )
    if matching is None:
        flags.append(EvidenceFlag(
            code="evidence_event_id_fabricated",
            message=(
                f"evidence_event_id {record.evidence_event_id!r} does not "
                "match any ToolEvent in this turn's audit"
            ),
            record=record,
        ))
        # If event_id is fabricated, URL / content checks are meaningless;
        # return early so the caller doesn't double-flag the same record.
        return flags

    consulted = matching.get("consulted_sources") or []
    consulted_urls = {
        (src.get("url") or "").strip()
        for src in consulted
        if isinstance(src, dict)
    }
    if record.url.strip() not in consulted_urls:
        flags.append(EvidenceFlag(
            code="evidence_url_not_consulted",
            message=(
                f"url {record.url!r} is not in consulted_sources of "
                f"ToolEvent {record.evidence_event_id!r}"
            ),
            record=record,
        ))

    # The consulted page content lives in ``encrypted_content`` for
    # Anthropic and is absent for OpenAI. When absent, we cannot prove
    # content match either way; the validator defers (no flag fires)
    # and the spec's risk note covers the OpenAI-no-source-content case.
    consulted_content_blob: list[str] = []
    for src in consulted:
        if not isinstance(src, dict):
            continue
        encrypted = src.get("encrypted_content")
        if isinstance(encrypted, str) and encrypted:
            consulted_content_blob.append(encrypted)
    if consulted_content_blob:
        haystack = _normalize_for_match("\n".join(consulted_content_blob))
        needle = _normalize_for_match(excerpt)
        if needle and needle not in haystack:
            flags.append(EvidenceFlag(
                code="evidence_content_not_in_source",
                message=(
                    "content_excerpt does not appear as a substring of "
                    "the consulted page content (after light normalization)"
                ),
                record=record,
            ))

    return flags


def validate_all_evidence(
    records: list[EvidenceRecord],
    *,
    tool_events: list[dict],
) -> list[EvidenceFlag]:
    """Run ``validate_evidence`` against each record, flatten the flags."""
    out: list[EvidenceFlag] = []
    for record in records:
        out.extend(validate_evidence(record, tool_events=tool_events))
    return out
