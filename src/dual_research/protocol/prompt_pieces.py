"""Per-piece token-size estimators for the Consumption tab.

Spec 0145: piece-dict keys ARE the canonical artifact IDs from spec
0117's registry (``src/dual_research/contract/artifacts.py``). The
``user_prompt`` aggregate key (legacy) is no longer emitted — it is
replaced by ``user_prompt.message`` plus zero-or-more
``user_prompt.attachment.<id>`` keys, one per attachment. The
aggregator propagates the resulting dict unchanged via the
``TurnEnded`` event payload's ``promptPieces`` field; the frontend
groups them per phase per spec 0118's "Per-phase grouping rules"
master table.

Tokenization stays a single char÷3.5 heuristic for both providers. The
provider's reported ``input_tokens`` is the cost-of-record; the
heuristic only computes proportions, which the frontend renormalises to
sum to ``input_tokens`` for honest segment widths.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


# 3.5 chars/token is the widely cited rule-of-thumb for English-leaning
# prose. Slightly under-counts symbol-heavy text; good enough for
# proportional widths after renormalization.
_CHARS_PER_TOKEN = 3.5


def estimate_tokens(text: str | None) -> int:
    """Char-based token estimate. Returns 0 for empty / None."""
    if not text:
        return 0
    return max(1, round(len(text) / _CHARS_PER_TOKEN))


@dataclass(frozen=True)
class Attachment:
    """Minimal piece-emitter view of a brief attachment.

    Spec 0145 §5.1 — ``id`` is the canonical attachment ID used in
    ``user_prompt.attachment.<id>``; ``title`` is the human-readable
    string resolved by ``display_name()``'s ``title_for_id`` map at
    render time (lives in ``attachments.json``); ``content`` is the
    text-or-byte payload the model actually sees. Token estimate uses
    ``len(content)`` like every other piece — binary attachments with
    no extractable text contribute zero to the heuristic; their cost
    lands in the provider-reported ``input_tokens`` and renormalises
    proportionally across the other pieces.
    """

    id: str
    title: str
    content: str


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


def _estimate_iter(prior_turns: Iterable[object] | None) -> int:
    """Token estimate over a PriorTurn iterable. 0 for None / empty."""
    if not prior_turns:
        return 0
    return max(1, round(_sum_prior_turn_chars(prior_turns) / _CHARS_PER_TOKEN))


def _emit_user_prompt(
    out: dict[str, int],
    user_prompt_message: str,
    attachments: Iterable[Attachment],
) -> None:
    """Spec 0145 §5.1 — emit ``user_prompt.message`` + one
    ``user_prompt.attachment.<id>`` row per attachment.

    Insertion order is the attachment-list order (Python 3.7+ dict
    semantics carry it). Binary attachments with empty ``content``
    contribute a zero-token row so they still appear on the
    consumption card.
    """
    out["user_prompt.message"] = estimate_tokens(user_prompt_message)
    for att in attachments:
        out[f"user_prompt.attachment.{att.id}"] = estimate_tokens(att.content)


def pieces_for_preflight(
    *,
    system_task: str,
    user_prompt_message: str,
    attachments: Iterable[Attachment] = (),
    prior_turns: Iterable[object] | None = None,
    ledger: str | None = None,
    closeout_request: str | None = None,
) -> dict[str, int]:
    """Phase 0 — preflight critique.

    ``prior_turns`` / ``ledger`` / ``closeout_request`` are round- and
    mode-conditional; they only appear in the emitted dict when present.
    ``attachments`` defaults to empty — every attachment becomes a
    ``user_prompt.attachment.<id>`` key on the emitted dict.
    """
    out: dict[str, int] = {
        "system.task.input": estimate_tokens(system_task),
    }
    _emit_user_prompt(out, user_prompt_message, attachments)
    if prior_turns:
        out["prior_turns.phase0"] = _estimate_iter(prior_turns)
    if ledger:
        out["ledger.standing_items"] = estimate_tokens(ledger)
    if closeout_request:
        out["closeout.request"] = estimate_tokens(closeout_request)
    return out


def pieces_for_research_plan(
    *,
    system_task: str,
    user_prompt_message: str,
    attachments: Iterable[Attachment] = (),
    agreed_interpretation: str,
) -> dict[str, int]:
    """Phase 1 — research plan (single-shot, no rounds)."""
    out: dict[str, int] = {
        "system.task.research_plan": estimate_tokens(system_task),
    }
    _emit_user_prompt(out, user_prompt_message, attachments)
    out["phase0.agreement.interpretation"] = estimate_tokens(agreed_interpretation)
    return out


def pieces_for_plan_negotiation(
    *,
    system_task: str,
    user_prompt_message: str,
    attachments: Iterable[Attachment] = (),
    agreed_interpretation: str,
    phase1_claude: str,
    phase1_openai: str,
    prior_turns: Iterable[object] | None = None,
    ledger: str | None = None,
    closeout_request: str | None = None,
) -> dict[str, int]:
    """Phase 2 — plan negotiation.

    Used for round 1 (with ``prior_turns=None``) and rounds 2+ (with the
    accumulated phase 2 transcript). ``ledger`` / ``closeout_request`` are
    only present on the relevant rounds.
    """
    out: dict[str, int] = {
        "system.task.plan_negotiation": estimate_tokens(system_task),
    }
    _emit_user_prompt(out, user_prompt_message, attachments)
    out["phase0.agreement.interpretation"] = estimate_tokens(agreed_interpretation)
    out["phase1.claude"] = estimate_tokens(phase1_claude)
    out["phase1.openai"] = estimate_tokens(phase1_openai)
    if prior_turns:
        out["prior_turns.phase2"] = _estimate_iter(prior_turns)
    if ledger:
        out["ledger.standing_items"] = estimate_tokens(ledger)
    if closeout_request:
        out["closeout.request"] = estimate_tokens(closeout_request)
    return out


def pieces_for_drafting(
    *,
    system_task: str,
    user_prompt_message: str,
    attachments: Iterable[Attachment] = (),
    agreed_interpretation: str,
    phase1_claude: str,
    phase1_openai: str,
    agreed_plan: str,
    all_p2_turns: Iterable[object] | None = None,
    carry_forward: str | None = None,
) -> dict[str, int]:
    """Phase 3 — single-shot drafting by the chosen drafter."""
    out: dict[str, int] = {
        "system.task.drafting": estimate_tokens(system_task),
    }
    _emit_user_prompt(out, user_prompt_message, attachments)
    out["phase0.agreement.interpretation"] = estimate_tokens(agreed_interpretation)
    out["phase1.claude"] = estimate_tokens(phase1_claude)
    out["phase1.openai"] = estimate_tokens(phase1_openai)
    out["phase2.agreement.plan"] = estimate_tokens(agreed_plan)
    if all_p2_turns:
        out["all_p2_turns"] = _estimate_iter(all_p2_turns)
    if carry_forward:
        out["carry_forward.phase2"] = estimate_tokens(carry_forward)
    return out


def pieces_for_review(
    *,
    system_task: str,
    user_prompt_message: str,
    attachments: Iterable[Attachment] = (),
    current_draft: str,
    prior_turns: Iterable[object] | None = None,
    ledger: str | None = None,
    closeout_request: str | None = None,
) -> dict[str, int]:
    """Phase 4 — review-draft (round 1 + rounds 2+).

    ``prior_turns`` / ``ledger`` / ``closeout_request`` are round- and
    mode-conditional; only included when present.
    """
    out: dict[str, int] = {
        "system.task.review": estimate_tokens(system_task),
    }
    _emit_user_prompt(out, user_prompt_message, attachments)
    out["current_draft"] = estimate_tokens(current_draft)
    if prior_turns:
        out["prior_turns.phase4"] = _estimate_iter(prior_turns)
    if ledger:
        out["ledger.standing_items"] = estimate_tokens(ledger)
    if closeout_request:
        out["closeout.request"] = estimate_tokens(closeout_request)
    return out


def renormalize(pieces: dict[str, int], target_total: int) -> dict[str, int]:
    """Scale piece-counts so they sum to ``target_total``.

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
    return {
        k: max(0, round(v * scale)) if v > 0 else 0
        for k, v in pieces.items()
    }
