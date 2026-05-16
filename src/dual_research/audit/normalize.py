"""Spec 0036 — provider-specific normalisers feeding the unified audit schema.

Each function walks one provider's response shape and emits a
``TurnSearchAudit``. The Anthropic path reads from ``message.content``
blocks; the OpenAI path reads from ``response.output`` items (with
``include=["web_search_call.action.sources"]`` requested upstream so the
full retrieval list is present).

Validation (cross-reference, flags) lives in ``validate.py`` and runs
separately so a normaliser stays a pure response walk.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from dual_research.audit.schema import (
    Citation,
    ConsultedSource,
    ToolEvent,
    TurnSearchAudit,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _model_dump(obj: Any) -> Any:
    """Pydantic v2 ``model_dump`` if available, else best-effort dict cast."""
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            pass
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return obj


# ─── Anthropic ───────────────────────────────────────────────────────────────


def normalize_anthropic_search_audit(
    message: Any,
    *,
    turn_key: str,
    phase: str,
    agent: str,
    label: str,
    emitted_at: str | None = None,
) -> TurnSearchAudit:
    """Walk an Anthropic ``Message`` and return a normalised audit.

    Reads:
      - ``server_tool_use`` blocks with ``name == "web_search"`` → one ToolEvent.
        The block's ``id`` is the event id; ``input.query`` is the query string.
      - ``web_search_tool_result`` blocks → attached to the matching ToolEvent
        by ``tool_use_id``. Each inner ``web_search_result`` becomes a
        ConsultedSource (url + title + page_age + encrypted_content).
      - ``text`` blocks → accumulated into ``final_text``; each citation
        annotation becomes a Citation (url + title + cited_text +
        encrypted_index).

    Block-position char offsets are recorded on each citation as
    ``text_span_start``/``end`` (the offsets where the *containing* text
    block lives in ``final_text``). Best-effort — Anthropic doesn't give
    sub-block ranges on citations themselves.
    """
    audit = TurnSearchAudit(
        provider="anthropic",
        model=getattr(message, "model", "") or "",
        turn_key=turn_key,
        phase=phase,
        agent=agent,
        label=label,
        emitted_at=emitted_at or _utcnow_iso(),
    )

    by_tool_use_id: dict[str, ToolEvent] = {}
    text_parts: list[str] = []

    for block in getattr(message, "content", None) or []:
        btype = getattr(block, "type", None)

        if btype == "server_tool_use" and getattr(block, "name", None) == "web_search":
            block_input = getattr(block, "input", None)
            query: str | None = None
            if isinstance(block_input, dict):
                q = block_input.get("query")
                if isinstance(q, str):
                    query = q
            event = ToolEvent(
                event_id=str(getattr(block, "id", "") or ""),
                action_type="search",
                queries=[query] if query else [],
            )
            by_tool_use_id[event.event_id] = event
            audit.tool_events.append(event)
            continue

        if btype == "web_search_tool_result":
            tool_use_id = str(getattr(block, "tool_use_id", "") or "")
            target = by_tool_use_id.get(tool_use_id)
            if target is None:
                continue
            content = getattr(block, "content", None)
            if not isinstance(content, list):
                continue
            for item in content:
                item_d = _model_dump(item)
                if not isinstance(item_d, dict):
                    continue
                if item_d.get("type") != "web_search_result":
                    continue
                target.consulted_sources.append(
                    ConsultedSource(
                        url=str(item_d.get("url", "") or ""),
                        title=item_d.get("title"),
                        page_age=item_d.get("page_age"),
                        encrypted_content=item_d.get("encrypted_content"),
                    )
                )
            continue

        if btype == "text":
            text_value = getattr(block, "text", "") or ""
            base_offset = sum(len(p) for p in text_parts)
            text_parts.append(text_value)
            block_end = base_offset + len(text_value)
            for cit in getattr(block, "citations", None) or []:
                cit_d = _model_dump(cit)
                if not isinstance(cit_d, dict):
                    continue
                audit.citations.append(
                    Citation(
                        url=str(cit_d.get("url", "") or ""),
                        title=cit_d.get("title"),
                        cited_text=cit_d.get("cited_text"),
                        encrypted_index=cit_d.get("encrypted_index"),
                        text_span_start=base_offset,
                        text_span_end=block_end,
                    )
                )

    audit.final_text = "".join(text_parts)
    return audit


# ─── OpenAI ──────────────────────────────────────────────────────────────────


def normalize_openai_search_audit(
    response: Any,
    *,
    turn_key: str,
    phase: str,
    agent: str,
    label: str,
    emitted_at: str | None = None,
) -> TurnSearchAudit:
    """Walk an OpenAI Responses-API ``Response`` and return a normalised audit.

    Requires the request to have included ``include=["web_search_call.action.sources"]``
    upstream so ``action.sources`` is populated. When ``include`` is omitted
    the retrieval list is empty — the validator's empty-set guard prevents
    a spurious ``cited_url_not_in_consulted_sources`` flag in that case.

    Walks ``response.output``:
      - ``web_search_call`` items → one ToolEvent each. ``action.type`` →
        ``action_type``. ``action.query`` (+ optional ``action.queries`` list)
        → ``queries``. ``action.sources`` → ConsultedSources (url only —
        OpenAI returns no title/page_age).
      - ``message`` items with ``output_text`` content → accumulated into
        ``final_text``; each ``url_citation`` annotation becomes a Citation
        with ``text_span_start``/``end`` taken directly from the annotation.
        ``cited_text`` stays ``None``.
    """
    audit = TurnSearchAudit(
        provider="openai",
        model=getattr(response, "model", "") or "",
        turn_key=turn_key,
        phase=phase,
        agent=agent,
        label=label,
        emitted_at=emitted_at or _utcnow_iso(),
    )

    for item in getattr(response, "output", None) or []:
        itype = getattr(item, "type", None)

        if itype == "web_search_call":
            action = getattr(item, "action", None)
            action_d = _model_dump(action) if action is not None else {}
            if not isinstance(action_d, dict):
                action_d = {}

            queries: list[str] = []
            primary_q = action_d.get("query")
            if isinstance(primary_q, str) and primary_q:
                queries.append(primary_q)
            for q in action_d.get("queries") or []:
                if isinstance(q, str) and q and q not in queries:
                    queries.append(q)

            sources_raw = action_d.get("sources") or []
            sources: list[ConsultedSource] = []
            for s in sources_raw:
                if not isinstance(s, dict):
                    continue
                url = s.get("url")
                if not isinstance(url, str) or not url:
                    continue
                sources.append(
                    ConsultedSource(
                        url=url,
                        title=s.get("title"),  # OpenAI omits this — stays None
                    )
                )

            action_type = action_d.get("type")
            if action_type not in ("search", "open_page", "find_in_page"):
                action_type = "unknown"

            audit.tool_events.append(
                ToolEvent(
                    event_id=str(getattr(item, "id", "") or ""),
                    action_type=action_type,  # type: ignore[arg-type]
                    queries=queries,
                    consulted_sources=sources,
                )
            )
            continue

        if itype == "message":
            for c in getattr(item, "content", None) or []:
                if getattr(c, "type", None) != "output_text":
                    continue
                text_value = getattr(c, "text", "") or ""
                base_offset = len(audit.final_text)
                audit.final_text += text_value
                for ann in getattr(c, "annotations", None) or []:
                    ann_d = _model_dump(ann)
                    if not isinstance(ann_d, dict):
                        continue
                    if ann_d.get("type") != "url_citation":
                        continue
                    start = ann_d.get("start_index")
                    end = ann_d.get("end_index")
                    audit.citations.append(
                        Citation(
                            url=str(ann_d.get("url", "") or ""),
                            title=ann_d.get("title"),
                            text_span_start=(base_offset + int(start)) if isinstance(start, int) else None,
                            text_span_end=(base_offset + int(end)) if isinstance(end, int) else None,
                            cited_text=None,
                        )
                    )

    return audit
