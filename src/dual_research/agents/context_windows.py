"""Model-id → context-window-size lookup for the spec-0029 Consumption tab.

The aggregator's per-turn `TurnTokenUsage` carries the `model_id` returned
by each API call (already passed through on `TurnEnded` events). The
frontend's `TokenBar` needs a denominator — the model's actual context
window in tokens — to render the fill correctly.

Hand-maintained dict. New models get added here when they're first wired
into `pricing.py`; unknown ids fall back to `DEFAULT_CONTEXT_WINDOW`.

A small `tests/agents/test_context_windows.py` keeps this in lockstep with
`pricing.PRICING`: every priced model should have a context window entry
(or accept the default).
"""

from __future__ import annotations

# Token counts. Values are best-effort 2026-vintage; precision matters
# less than rough magnitude — the bar's visual is "how full is this
# chat" relative to its cap.
CONTEXT_WINDOWS: dict[str, int] = {
    # Anthropic — Claude 4.x line. 200K standard; some have a 1M tier.
    "claude-sonnet-4-6": 200_000,
    "claude-haiku-4-5": 200_000,
    # OpenAI — GPT-5 line.
    "gpt-5.5": 200_000,
    "gpt-5-mini": 128_000,
}

DEFAULT_CONTEXT_WINDOW = 128_000


def context_window_for(model_id: str | None) -> int:
    """Look up a context window for a model id.

    Falls back to ``DEFAULT_CONTEXT_WINDOW`` for ``None`` or unknown ids.
    Prefix-matches in the same lenient style as ``lookup_pricing`` — e.g.
    ``"claude-sonnet-4-6-20260301"`` resolves via the ``"claude-sonnet-4-6"``
    entry.
    """
    if not model_id:
        return DEFAULT_CONTEXT_WINDOW
    if model_id in CONTEXT_WINDOWS:
        return CONTEXT_WINDOWS[model_id]
    for key, window in CONTEXT_WINDOWS.items():
        if model_id.startswith(key):
            return window
    return DEFAULT_CONTEXT_WINDOW
