from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from dual_research.protocol.parse import ParsedTurn


@dataclass(frozen=True)
class DrafterChoice:
    drafter: str
    reason: str
    domain_fit_scores: dict[str, int] | None = None
    plan_alignment: dict[str, float] | None = None
    note: str | None = None


def _last_drafter_vote(turns: list[ParsedTurn]) -> str | None:
    for t in reversed(turns):
        if t.drafter is not None:
            return t.drafter
    return None


def _last_fits(turns: list[ParsedTurn]) -> tuple[int | None, int | None]:
    for t in reversed(turns):
        if t.domain_fit_self is not None:
            return t.domain_fit_self, t.domain_fit_other
    return None, None


def _by_domain_fit(
    claude_turns: list[ParsedTurn], openai_turns: list[ParsedTurn]
) -> tuple[str | None, dict[str, int]]:
    c_self, c_other = _last_fits(claude_turns)
    o_self, o_other = _last_fits(openai_turns)
    if c_self is None and o_self is None:
        return None, {"claude": 0, "openai": 0}

    claude_score = (c_self or 0) + (o_other or 0)
    openai_score = (o_self or 0) + (c_other or 0)
    scores = {"claude": claude_score, "openai": openai_score}
    if claude_score == openai_score:
        return None, scores
    return ("claude" if claude_score > openai_score else "openai"), scores


def _word_set(text: str) -> set[str]:
    return {w for w in re.split(r"\W+", text.lower()) if len(w) > 3}


def _word_list(text: str) -> list[str]:
    return [w for w in re.split(r"\W+", text.lower()) if len(w) > 3]


def _by_plan_alignment(
    agreed_plan_text: str | None, phase1_drafts: dict[str, str]
) -> tuple[str | None, dict[str, float]]:
    if not agreed_plan_text:
        return None, {"claude": 0.0, "openai": 0.0}
    plan_words = _word_set(agreed_plan_text)
    if not plan_words:
        return None, {"claude": 0.0, "openai": 0.0}

    def overlap(draft: str) -> float:
        words = _word_list(draft)
        if not words:
            return 0.0
        return sum(1 for w in words if w in plan_words) / len(plan_words)

    c = overlap(phase1_drafts.get("claude", "") or "")
    o = overlap(phase1_drafts.get("openai", "") or "")
    alignment = {"claude": c, "openai": o}
    if abs(c - o) < 0.01:
        return None, alignment
    return ("claude" if c > o else "openai"), alignment


def pick_drafter(
    *,
    claude_phase2_turns: list[ParsedTurn],
    openai_phase2_turns: list[ParsedTurn],
    phase1_drafts: dict[str, str],
    agreed_plan_text: str | None,
    brief_content: str,
) -> DrafterChoice:
    """Three-step tiebreak: domain-fit scores → plan alignment → hash-of-brief.

    Concession asymmetry is intentionally absent — it would incentivise stubbornness.
    """
    c_vote = _last_drafter_vote(claude_phase2_turns)
    o_vote = _last_drafter_vote(openai_phase2_turns)
    if c_vote is not None and c_vote == o_vote:
        return DrafterChoice(drafter=c_vote, reason="matching-recommendations")

    winner, scores = _by_domain_fit(claude_phase2_turns, openai_phase2_turns)
    if winner is not None:
        return DrafterChoice(drafter=winner, reason="domain-fit", domain_fit_scores=scores)

    winner, alignment = _by_plan_alignment(agreed_plan_text, phase1_drafts)
    if winner is not None:
        return DrafterChoice(drafter=winner, reason="plan-alignment", plan_alignment=alignment)

    h = hashlib.sha256((brief_content or "").encode("utf-8")).digest()
    drafter = "claude" if (h[0] & 1) == 0 else "openai"
    return DrafterChoice(
        drafter=drafter,
        reason="hash-of-brief",
        note="structured criteria did not break tie",
    )
