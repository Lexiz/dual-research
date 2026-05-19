"""Spec 0114 — stable item-ID format.

Format: ``<kind>-<phase>-<raiser>-<seq>``

- ``kind``   : ``Q`` | ``D`` | ``I`` | ``C``
- ``phase``  : ``input`` | ``plan`` | ``review``
- ``raiser`` : ``c`` (claude) | ``g`` (gpt / openai)
- ``seq``    : zero-padded 2-digit, monotonic per (kind, phase, raiser)

IDs are assigned by the orchestrator at parse time. The agent emits a
RAISE block without a sequence; the parser stamps the next available
sequence in the (kind, phase, raiser) namespace. Once assigned, IDs are
immutable for the lifetime of the run.
"""

from __future__ import annotations

import re

from dual_research.contract.categories import (
    ID_TOKEN,
    PHASE_TOKEN,
    TOKEN_TO_CATEGORY,
    TOKEN_TO_PHASE,
    Category,
)


ID_PATTERN = re.compile(r"^([QDIC])-(input|plan|review)-([cg])-(\d{2})$")


# Mapping between the orchestrator's agent vocabulary ("claude"/"openai")
# and the raiser letter used in IDs ("c"/"g"). The repo's legacy events
# use "claude" / "openai"; the lifecycle uses "c" / "g" inside IDs and
# "claude" / "gpt" in event payloads. We standardize on:
#   * agent vocabulary in events:  "claude" / "openai"
#   * raiser letter in IDs:        "c" / "g"
# and provide helpers to convert both directions.
AGENT_TO_RAISER: dict[str, str] = {
    "claude": "c",
    "openai": "g",
    "gpt": "g",
}

RAISER_TO_AGENT: dict[str, str] = {
    "c": "claude",
    "g": "openai",
}


def raiser_letter(agent: str) -> str:
    """Translate orchestrator agent vocabulary into the raiser letter."""
    try:
        return AGENT_TO_RAISER[agent]
    except KeyError as exc:
        raise ValueError(f"unknown agent name for raiser letter: {agent!r}") from exc


def agent_name(raiser: str) -> str:
    """Translate a raiser letter back into the orchestrator agent name."""
    try:
        return RAISER_TO_AGENT[raiser]
    except KeyError as exc:
        raise ValueError(f"unknown raiser letter: {raiser!r}") from exc


def format_id(kind: Category, phase: int, raiser: str, seq: int) -> str:
    """Format a stable item ID from its components.

    ``kind`` is a ``Category``; ``phase`` is the integer phase number;
    ``raiser`` may be the raiser letter (``"c"``/``"g"``) or an agent
    name (``"claude"``/``"openai"``/``"gpt"``); ``seq`` is a positive
    int (1..99).
    """
    if phase not in PHASE_TOKEN:
        raise ValueError(f"phase {phase} does not raise items")
    phase_tok = PHASE_TOKEN[phase]
    if raiser in AGENT_TO_RAISER:
        raiser_tok = AGENT_TO_RAISER[raiser]
    elif raiser in RAISER_TO_AGENT:
        raiser_tok = raiser
    else:
        raise ValueError(f"unknown raiser: {raiser!r}")
    if not 0 < seq < 100:
        raise ValueError(f"seq out of range [1, 99]: {seq}")
    return f"{ID_TOKEN[kind]}-{phase_tok}-{raiser_tok}-{seq:02d}"


def parse_id(item_id: str) -> tuple[Category, int, str, int]:
    """Parse a stable item ID. Returns ``(kind, phase, raiser, seq)``.

    ``phase`` is the integer phase number; ``raiser`` is the raiser
    letter (``"c"``/``"g"``). Raises ``ValueError`` on malformed input.
    """
    m = ID_PATTERN.match(item_id)
    if not m:
        raise ValueError(f"malformed item ID: {item_id!r}")
    kind_token, phase_token, raiser, seq = m.groups()
    kind = TOKEN_TO_CATEGORY[kind_token]
    phase = TOKEN_TO_PHASE[phase_token]
    return kind, phase, raiser, int(seq)


def is_well_formed(item_id: str) -> bool:
    """``True`` iff ``item_id`` matches the canonical ID pattern."""
    return bool(ID_PATTERN.match(item_id))
