from __future__ import annotations

import re
import sys
import time
from typing import TextIO

from dual_research.agents.base import AgentCall, AgentResult
from dual_research.events import EventBus, TurnEnded, TurnInputs, TurnSearches, TurnStarted
from dual_research.persistence import Metrics, Transcript


# Spec 0036 — turn-key derivation. Same convention as the aggregator's
# ``_on_turn_inputs`` so a turn's inputs/<key>.json and searches/<key>.json
# pair up. Kept here (not imported from ui/) to keep the orchestrator free
# of UI imports.
_ROUND_FROM_LABEL_RE_R = re.compile(r"-r(\d+)(?:[-_]|$)")
_ROUND_FROM_LABEL_RE_LEGACY = re.compile(r"round[-_](\d+)")


def _round_index_from_label(label: str) -> int:
    m = _ROUND_FROM_LABEL_RE_R.search(label)
    if m:
        return int(m.group(1))
    m = _ROUND_FROM_LABEL_RE_LEGACY.search(label)
    return int(m.group(1)) if m else 0


def _phase_to_int(phase: str) -> int:
    """``"phase2"`` -> ``2``; tolerant of unexpected shapes (returns 0)."""
    m = re.match(r"^phase(\d+)", phase)
    return int(m.group(1)) if m else 0


def _derive_turn_key(*, agent_label: str, phase: str, label: str) -> str:
    """Return the snake_case turn-key shared with inputs/<key>.json.

    Mirrors ``_on_turn_inputs`` in ``ui/aggregator.py``.
    """
    ui_ag = "gpt" if agent_label == "openai" else agent_label
    phase_int = _phase_to_int(phase)
    idx = _round_index_from_label(label)
    if phase_int in (2, 4) and idx > 0:
        key = f"phase{phase_int}_round{idx}_{ui_ag}"
    else:
        key = f"phase{phase_int}_{ui_ag}"
    if "-repair" in label or "-hashdrift" in label:
        key = f"{key}_repair"
    return key


async def run_one_call(
    *,
    agent: AgentCall,
    prompt: str,
    label: str,
    phase: str,
    metrics: Metrics,
    transcript: Transcript,
    event_bus: EventBus,
    stream_to: TextIO | None = sys.stdout,
    stream_prefix: str = "",
    max_output_tokens: int = 8192,
    prompt_pieces: dict[str, int] | None = None,
    prompt_bundle: dict[str, str] | None = None,
) -> AgentResult:
    """Run one agent call with event emission and persistence side-effects.

    Publishes TurnStarted before the call, TurnEnded after, records the
    AgentResult into metrics, and appends both events to the transcript.
    Streams tokens to stdout by default with a per-agent prefix.

    ``prompt_pieces`` (spec 0030) is the per-input token breakdown computed
    by the phase orchestrator from the same input strings used to build
    the prompt. It's surfaced on ``TurnEnded`` and consumed by the
    Consumption tab to render segmented bars. Pass ``None`` to omit (the
    event carries an empty dict by default).

    ``prompt_bundle`` (spec 0033) is the per-input *text* — the Tk-keyed
    dict produced by ``protocol/prompts.py::*_input_bundle()``. Emitted
    on a ``TurnInputs`` event right after ``TurnStarted`` so the
    aggregator can persist it to ``session_dir/inputs/<key>.json``;
    the UI's Input tab reads from that file on demand. Pass ``None`` to
    omit (no ``TurnInputs`` event is emitted, equivalent to pre-0033
    behaviour).
    """
    await event_bus.publish(TurnStarted(agent=agent.label, phase=phase, label=label))
    transcript.write("turn_started", agent=agent.label, phase=phase, label=label)

    if prompt_bundle is not None:
        inputs_event = TurnInputs(
            agent=agent.label,
            phase=phase,
            label=label,
            pieces=dict(prompt_bundle),
        )
        await event_bus.publish(inputs_event)
        transcript.write(
            "turn_inputs",
            agent=inputs_event.agent,
            phase=inputs_event.phase,
            label=inputs_event.label,
            pieces=inputs_event.pieces,
        )

    # Spec 0036 — turn-key + audit context (so the agent can construct
    # the per-turn search-audit payload using the same key the aggregator
    # will later write to disk).
    turn_key = _derive_turn_key(agent_label=agent.label, phase=phase, label=label)
    audit_context = {
        "turn_key": turn_key,
        "phase": phase,
        "agent": agent.label,
        "label": label,
    }

    start = time.perf_counter()
    result = await agent.run(
        prompt,
        max_output_tokens=max_output_tokens,
        stream_to=stream_to,
        stream_prefix=stream_prefix,
        audit_context=audit_context,
    )
    duration_ms = int((time.perf_counter() - start) * 1000)

    metrics.record(label=label, result=result)
    finish_reason = (result.extras or {}).get("stop_reason") or (result.extras or {}).get("finish_reason")
    # Spec 0031: web-search tool calls — both agents stash this count in
    # `extras["searches"]` after each call. Default to 0 for paranoia.
    searches = int((result.extras or {}).get("searches") or 0)

    # Spec 0036: emit TurnSearches BEFORE TurnEnded so the aggregator
    # has the audit bundle on disk + `search_audit_path` stamped on
    # `TurnTokenUsage` by the time the TurnEnded handler runs (which
    # would otherwise overwrite a fresh `TurnTokenUsage` row).
    search_audit = (result.extras or {}).get("search_audit")
    if isinstance(search_audit, dict) and search_audit:
        searches_event = TurnSearches(
            agent=agent.label,
            phase=phase,
            label=label,
            turn_key=turn_key,
            audit=search_audit,
        )
        await event_bus.publish(searches_event)
        transcript.write(
            "turn_searches",
            agent=searches_event.agent,
            phase=searches_event.phase,
            label=searches_event.label,
            turn_key=searches_event.turn_key,
            audit=searches_event.audit,
        )

    end_event = TurnEnded(
        agent=agent.label,
        phase=phase,
        label=label,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        cache_read_tokens=result.usage.cache_read_tokens,
        cache_write_tokens=result.usage.cache_write_tokens,
        cost_usd=result.cost_usd,
        duration_ms=duration_ms,
        finish_reason=str(finish_reason) if finish_reason is not None else None,
        model_id=result.model_id,
        prompt_pieces=dict(prompt_pieces) if prompt_pieces else {},
        searches=searches,
    )
    await event_bus.publish(end_event)
    transcript.write(
        "turn_ended",
        agent=end_event.agent,
        phase=end_event.phase,
        label=end_event.label,
        input_tokens=end_event.input_tokens,
        output_tokens=end_event.output_tokens,
        cache_read_tokens=end_event.cache_read_tokens,
        cache_write_tokens=end_event.cache_write_tokens,
        cost_usd=end_event.cost_usd,
        duration_ms=end_event.duration_ms,
        finish_reason=end_event.finish_reason,
        model_id=end_event.model_id,
        prompt_pieces=end_event.prompt_pieces,
        searches=end_event.searches,
    )

    return result
