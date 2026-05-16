from __future__ import annotations

import sys
import time
from typing import TextIO

from dual_research.agents.base import AgentCall, AgentResult
from dual_research.events import EventBus, TurnEnded, TurnInputs, TurnStarted
from dual_research.persistence import Metrics, Transcript


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

    start = time.perf_counter()
    result = await agent.run(
        prompt,
        max_output_tokens=max_output_tokens,
        stream_to=stream_to,
        stream_prefix=stream_prefix,
    )
    duration_ms = int((time.perf_counter() - start) * 1000)

    metrics.record(label=label, result=result)
    finish_reason = (result.extras or {}).get("stop_reason") or (result.extras or {}).get("finish_reason")
    # Spec 0031: web-search tool calls — both agents stash this count in
    # `extras["searches"]` after each call. Default to 0 for paranoia.
    searches = int((result.extras or {}).get("searches") or 0)

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
