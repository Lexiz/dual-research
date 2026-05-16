"""Spec 0036 — validation rules on a normalised TurnSearchAudit.

Runs after normalisation, mutates the audit in place to:
  - stamp ``Citation.matched_query_id`` (cross-reference)
  - stamp ``TurnSearchAudit.flags`` (policy checks)

Rules (Perplexity's research note + ideation probe findings):

  * ``search_performed`` — any ToolEvent present.
  * ``cited_url_not_in_consulted_sources`` — strong hallucination signal.
    Set only when the consulted URL set is non-empty (otherwise we can't
    distinguish "URL was retrieved off-record" from "URL was never seen").
  * ``citations_without_search_event`` — citations exist but no search
    happened. Synthetic check; doesn't happen in real responses but
    catches buggy normalisers / hand-crafted payloads.
  * ``queries_missing_from_actions`` — at least one ``search``-action
    ToolEvent has no query text. OpenAI documents that queries are
    "usually but not always" present — the flag surfaces it for review.
"""

from __future__ import annotations

from urllib.parse import urlparse

from dual_research.audit.schema import TurnSearchAudit


# Tracking-style query params that should be stripped before URL set comparisons.
# Kept narrow on purpose — we don't want to over-normalise and accidentally
# treat distinct URLs as identical. Add patterns here only when a real
# observed source vs citation mismatch warrants it.
_TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}


def normalize_url(url: str) -> str:
    """Return a normalised form of ``url`` for set-membership comparison.

    - Strips known tracking query parameters (``utm_*``).
    - Lowercases the scheme + host.
    - Drops a trailing slash on the path.
    - Drops the fragment.

    Leaves path case alone (some URLs are case-sensitive on the path).
    Returns the input unchanged when the URL fails to parse.
    """
    if not url:
        return ""
    try:
        parts = urlparse(url)
    except (ValueError, TypeError):
        return url.rstrip("/").lower()
    scheme = (parts.scheme or "").lower()
    netloc = (parts.netloc or "").lower()
    path = parts.path or ""
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")
    # Filter tracking params out of the query string while preserving order
    # of the remaining params (so otherwise-distinct URLs stay distinct).
    query = parts.query or ""
    if query:
        kept = []
        for chunk in query.split("&"):
            if not chunk:
                continue
            key = chunk.split("=", 1)[0].lower()
            if key in _TRACKING_QUERY_PARAMS:
                continue
            kept.append(chunk)
        query = "&".join(kept)
    rebuilt = f"{scheme}://{netloc}{path}"
    if query:
        rebuilt = f"{rebuilt}?{query}"
    return rebuilt


def validate_search_audit(audit: TurnSearchAudit) -> TurnSearchAudit:
    """Apply all validation rules; mutates ``audit`` and returns it.

    Idempotent — running twice produces the same result.
    """
    flags = audit.flags

    # Build the consulted-URL set across all tool events. Track which event
    # each URL came from so citations can be linked back to a specific query.
    url_to_event_id: dict[str, str] = {}
    for event in audit.tool_events:
        for source in event.consulted_sources:
            key = normalize_url(source.url)
            if not key:
                continue
            # First-event-wins when the same URL appears in multiple queries.
            url_to_event_id.setdefault(key, event.event_id)

    # Cross-reference citations against the consulted set.
    any_citation_unmatched = False
    for citation in audit.citations:
        norm = normalize_url(citation.url)
        if norm and norm in url_to_event_id:
            citation.matched_query_id = url_to_event_id[norm]
        else:
            citation.matched_query_id = None
            any_citation_unmatched = True

    flags.search_performed = bool(audit.tool_events)
    flags.citations_without_search_event = bool(audit.citations) and not flags.search_performed
    # Only flag URL-not-in-consulted-set when we have a consulted set to
    # check against. OpenAI without `include=["web_search_call.action.sources"]`
    # returns no sources, so flagging here would produce false positives.
    flags.cited_url_not_in_consulted_sources = bool(url_to_event_id) and any_citation_unmatched
    flags.queries_missing_from_actions = any(
        not event.queries
        for event in audit.tool_events
        if event.action_type == "search"
    )

    return audit
