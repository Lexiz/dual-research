"""Per-piece token-size estimators for the spec-0030 Consumption tab.

Each phase orchestrator builds its prompt from a known set of input
strings (brief, drafts, prior turns, plan, current draft). This module
turns those input strings into a Tk-vocabulary dict that the agent layer
attaches to the ``TurnEnded`` event:

  ``brief``  → research brief
  ``d1``     → Phase 1 draft by Claude
  ``d2``     → Phase 1 draft by OpenAI
  ``hist``   → all prior Phase 2 turns inlined into a Phase 2 round
  ``plan``   → the AGREED_PLAN block carried into Phase 3
  ``draft``  → the current converged draft (Phase 4 input)
  ``histp``  → all prior Phase 4 turns inlined into a Phase 4 round

Vocabulary matches the ``Tk`` chips in ``how-it-works.jsx`` exactly, so
the segmented bars on the Consumption tab read as direct numerical
read-outs of the same conceptual lifecycle.

Tokenization is a single char÷3.5 heuristic for both providers. The
provider's reported ``input_tokens`` is the cost-of-record; the
heuristic only computes *proportions*, which the frontend renormalises
to sum to ``input_tokens`` for honest segment widths.
"""

from __future__ import annotations

from collections.abc import Iterable


# Single heuristic for both providers. 3.5 chars/token is the widely
# cited rule-of-thumb for English-leaning prose; it slightly under-counts
# code-heavy or symbol-heavy text. Good enough for proportional widths.
_CHARS_PER_TOKEN = 3.5


def estimate_tokens(text: str | None) -> int:
    """Char-based token estimate. Returns 0 for empty / None."""
    if not text:
        return 0
    return max(1, round(len(text) / _CHARS_PER_TOKEN))


def _sum_prior_turn_chars(prior_turns: Iterable[object]) -> int:
    """Total character count across an iterable of PriorTurn-shaped objects.

    Accepts anything with a ``.content`` attribute (the ``PriorTurn``
    dataclass from ``prompts.py``).
    """
    total = 0
    for t in prior_turns:
        content = getattr(t, "content", "") or ""
        total += len(content)
    return total


def pieces_for_preflight(*, brief: str) -> dict[str, int]:
    """Phase 0 — preflight critique. Only the brief is inlined."""
    return {"brief": estimate_tokens(brief)}


def pieces_for_research(*, brief: str) -> dict[str, int]:
    """Phase 1 — research draft. Only the brief is inlined."""
    return {"brief": estimate_tokens(brief)}


def pieces_for_negotiation_round1(
    *, brief: str, claude_draft: str, openai_draft: str
) -> dict[str, int]:
    """Phase 2 round 1 — brief + both Phase-1 drafts (no prior turns yet)."""
    return {
        "brief": estimate_tokens(brief),
        "d1": estimate_tokens(claude_draft),
        "d2": estimate_tokens(openai_draft),
    }


def pieces_for_negotiation_turn(
    *,
    brief: str,
    claude_draft: str,
    openai_draft: str,
    prior_turns: Iterable[object],
) -> dict[str, int]:
    """Phase 2 rounds 2+ — brief + both drafts + all prior P2 turns."""
    return {
        "brief": estimate_tokens(brief),
        "d1": estimate_tokens(claude_draft),
        "d2": estimate_tokens(openai_draft),
        "hist": max(1, round(_sum_prior_turn_chars(prior_turns) / _CHARS_PER_TOKEN))
        if prior_turns
        else 0,
    }


def pieces_for_drafting(
    *,
    brief: str,
    claude_draft: str,
    openai_draft: str,
    plan: str | None,
    prior_turns: Iterable[object],
) -> dict[str, int]:
    """Phase 3 — brief + drafts + AGREED_PLAN + full P2 history."""
    return {
        "brief": estimate_tokens(brief),
        "d1": estimate_tokens(claude_draft),
        "d2": estimate_tokens(openai_draft),
        "plan": estimate_tokens(plan or ""),
        "hist": max(1, round(_sum_prior_turn_chars(prior_turns) / _CHARS_PER_TOKEN))
        if prior_turns
        else 0,
    }


def pieces_for_review(
    *,
    brief: str,
    draft: str,
    prior_turns: Iterable[object],
) -> dict[str, int]:
    """Phase 4 — brief + current draft + prior P4 review turns.

    Note: Phase 4's history uses the ``histp`` key (P4 history), distinct
    from Phase 2's ``hist`` key, mirroring the how-it-works Tk vocabulary.
    """
    return {
        "brief": estimate_tokens(brief),
        "draft": estimate_tokens(draft),
        "histp": max(1, round(_sum_prior_turn_chars(prior_turns) / _CHARS_PER_TOKEN))
        if prior_turns
        else 0,
    }


def renormalize(pieces: dict[str, int], target_total: int) -> dict[str, int]:
    """Scale the piece-counts so they sum to ``target_total``.

    Used by the aggregator / frontend to align heuristic estimates with
    the provider's reported ``input_tokens``. Returns a new dict; pieces
    with a zero starting value stay at zero. If ``target_total`` is zero
    or all pieces are zero, returns the input unchanged.
    """
    if target_total <= 0:
        return dict(pieces)
    raw_total = sum(v for v in pieces.values() if v > 0)
    if raw_total <= 0:
        return dict(pieces)
    scale = target_total / raw_total
    out: dict[str, int] = {}
    for k, v in pieces.items():
        out[k] = max(0, round(v * scale)) if v > 0 else 0
    return out
