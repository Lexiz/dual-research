"""Spec 0036 — provider-neutral audit schema for per-turn web search.

Dataclasses serialise to plain dicts via ``audit_to_dict`` and round-trip
via ``audit_from_dict``. The wire JSON payload on
``session_dir/searches/<turn-key>.json`` is the same shape.

Asymmetry between providers is captured by leaving fields ``None`` rather
than dispatching on provider — readers can ask "do we have ``cited_text``?"
without branching on the provider string. The provider tag is kept on the
top-level audit for display ("OpenAI doesn't expose unreferenced
retrievals" disclaimers in the future UI).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


# ─── Leaf objects ────────────────────────────────────────────────────────────


@dataclass
class ConsultedSource:
    """One URL the search backend served the model during a single search call.

    Anthropic populates ``url`` + ``title`` + ``page_age`` + ``encrypted_content``.
    OpenAI populates ``url`` only (the rest stay ``None``).
    """

    url: str
    title: str | None = None
    page_age: str | None = None
    encrypted_content: str | None = None


@dataclass
class Citation:
    """A piece of the model's output text attributed to a source URL.

    - Anthropic: ``cited_text`` carries the exact source-side snippet the model
      attributes to ``url``. ``text_span_start``/``end`` are derived from the
      position of the containing text block in the model's output (best-effort).
    - OpenAI: ``text_span_start``/``end`` are character offsets into the final
      ``output_text`` (provided directly by the SDK annotation). ``cited_text``
      stays ``None`` — OpenAI doesn't expose a source-side snippet, only
      annotation offsets into the model's own text.
    """

    url: str
    title: str | None = None
    text_span_start: int | None = None
    text_span_end: int | None = None
    cited_text: str | None = None
    encrypted_index: str | None = None
    # Cross-reference: which ToolEvent's retrieval set produced this URL.
    # Populated by `validate_search_audit`. ``None`` means the cited URL
    # is NOT in any retrieval set — strong hallucination signal on
    # Anthropic, weak/unknowable on OpenAI without sources include.
    matched_query_id: str | None = None


@dataclass
class ToolEvent:
    """One web_search tool invocation by the model.

    ``action_type``:
      - ``search`` — the standard case (both providers).
      - ``open_page`` / ``find_in_page`` — reasoning-model-only on OpenAI.
      - ``unknown`` — preserved so a future SDK shape change doesn't drop the
        event entirely.
    """

    event_id: str
    type: str = "web_search"
    action_type: Literal["search", "open_page", "find_in_page", "unknown"] = "search"
    queries: list[str] = field(default_factory=list)
    consulted_sources: list[ConsultedSource] = field(default_factory=list)


@dataclass
class TurnSearchFlags:
    """Validation flags computed by ``validate_search_audit``.

    All default ``False`` — the validator only sets ``True`` when the rule
    fires, so a freshly-deserialised audit (before validation) reads as
    "no flags" which is honest.
    """

    search_performed: bool = False
    citations_without_search_event: bool = False
    cited_url_not_in_consulted_sources: bool = False
    queries_missing_from_actions: bool = False


# ─── Top-level audit ─────────────────────────────────────────────────────────


@dataclass
class TurnSearchAudit:
    """Provider-neutral per-turn audit bundle.

    Persisted as ``session_dir/searches/<turn-key>.json`` by the aggregator.
    The UI server returns this verbatim from
    ``/api/runs/<id>/searches/<turn-key>``.

    ``turn_key`` is the same snake_case key used by ``inputs/<turn-key>.json``
    (spec 0033), so the future UI's Web Search tab can resolve the same key
    the Input tab already uses.
    """

    provider: str           # "anthropic" | "openai"
    model: str
    turn_key: str
    phase: str              # "phase0" | "phase1" | "phase2_round3" | ...
    agent: str              # "claude" | "openai" (backend vocab)
    label: str              # same shape as TurnStarted/TurnEnded.label
    emitted_at: str         # ISO-8601 UTC
    tool_events: list[ToolEvent] = field(default_factory=list)
    final_text: str = ""
    citations: list[Citation] = field(default_factory=list)
    flags: TurnSearchFlags = field(default_factory=TurnSearchFlags)


# ─── (De)serialisation helpers ───────────────────────────────────────────────


def audit_to_dict(audit: TurnSearchAudit) -> dict[str, Any]:
    """Convert a TurnSearchAudit to a plain dict (JSON-serialisable)."""
    return asdict(audit)


def audit_from_dict(data: dict[str, Any]) -> TurnSearchAudit:
    """Reconstruct a TurnSearchAudit from a dict (e.g. event payload).

    Handles nested lists of dataclasses + the nested ``flags`` object.
    Missing fields default to the dataclass defaults — tolerant of older
    payloads.
    """
    tool_events_raw = data.get("tool_events") or []
    tool_events: list[ToolEvent] = []
    for ev in tool_events_raw:
        if not isinstance(ev, dict):
            continue
        sources_raw = ev.get("consulted_sources") or []
        sources = [
            ConsultedSource(**{k: s.get(k) for k in ConsultedSource.__dataclass_fields__})
            for s in sources_raw
            if isinstance(s, dict) and s.get("url")
        ]
        tool_events.append(
            ToolEvent(
                event_id=str(ev.get("event_id", "")),
                type=str(ev.get("type", "web_search")),
                action_type=ev.get("action_type") or "unknown",  # type: ignore[arg-type]
                queries=[str(q) for q in (ev.get("queries") or [])],
                consulted_sources=sources,
            )
        )

    citations_raw = data.get("citations") or []
    citations: list[Citation] = []
    for c in citations_raw:
        if not isinstance(c, dict):
            continue
        citations.append(
            Citation(**{k: c.get(k) for k in Citation.__dataclass_fields__})
        )

    flags_raw = data.get("flags") or {}
    flags = TurnSearchFlags(
        **{k: bool(flags_raw.get(k, False)) for k in TurnSearchFlags.__dataclass_fields__}
    )

    return TurnSearchAudit(
        provider=str(data.get("provider", "")),
        model=str(data.get("model", "")),
        turn_key=str(data.get("turn_key", "")),
        phase=str(data.get("phase", "")),
        agent=str(data.get("agent", "")),
        label=str(data.get("label", "")),
        emitted_at=str(data.get("emitted_at", "")),
        tool_events=tool_events,
        final_text=str(data.get("final_text", "")),
        citations=citations,
        flags=flags,
    )
