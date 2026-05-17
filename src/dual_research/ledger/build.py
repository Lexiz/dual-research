"""Spec 0043 — build a per-phase ledger from a session's turn files.

The ledger reuses the existing per-kind reconstructors
(``reconstruct_questions`` / ``reconstruct`` for disagreements /
``reconstruct_issues`` / ``reconstruct_comments`` /
``reconstruct_claims``) as its data sources. Each reconstructor
already implements the closure-detection semantics specific to its
kind (positional + verbatim-match answer linkage for questions,
D-N anchored resolved/final-surfaced for disagreements, latest-
round-ledger-presence for issues). The ledger:

1. Maps each reconstructed object to a unified ``LedgerEntry``.
2. Adds the **claim → escalated** transition: a Phase 1 or Phase 2 R1
   claim whose D-N suffix appears in any later round's
   ``## Substantive disagreements I'm holding`` section flips to
   ``escalated``. This is the cross-kind linkage spec 0042's
   round-1 ``Diff vs`` re-bucketing set up but didn't track.
3. Computes per-round ``ghosted_rounds`` — bumped each round an item
   was open without an addressing signal.

The build is deterministic + idempotent: same session-dir always
produces the same LedgerState; no hidden state, no I/O side effects.
"""

from __future__ import annotations

import re
from pathlib import Path

from dual_research.ledger.models import (
    LedgerEntry,
    LedgerState,
    LedgerStatusTransition,
)

# Reconstructor imports are deferred to call time to avoid a circular
# import chain: dual_research.ui.aggregator imports from this module,
# and dual_research.ui's package __init__ imports aggregator — so a
# top-level ``from dual_research.ui.X import …`` here would trip
# partial-init at import time.


# Match a D-N (or D-OAI-N etc) token anywhere in a string — used to
# extract IDs from item bodies for cross-round claim → disagreement
# escalation linkage.
_D_TOKEN_RE = re.compile(r"\bD-(?:[A-Z]+-)?\d+\b")

_ROUND_FILE_RE = re.compile(r"^round-(\d+)-(claude|openai)\.md$")
_SUBSTANTIVE_HDR_RE = re.compile(
    r"^##\s+Substantive disagreements I'm holding\s*$", re.MULTILINE
)
_RESOLVED_HDR_RE = re.compile(
    r"^##\s+Resolved or non-blocking differences\s*$", re.MULTILINE
)
_FINAL_HDR_RE = re.compile(
    r"^##\s+Final-surfaced disagreements\s*$", re.MULTILINE
)


def _body_snippet(body: str, *, max_chars: int = 120) -> str:
    s = (body or "").strip().replace("\n", " ")
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _extract_d_id(text: str) -> str | None:
    if not text:
        return None
    m = _D_TOKEN_RE.search(text)
    return m.group(0) if m else None


def _section_body(text: str, hdr_match: re.Match[str] | None) -> str:
    if not hdr_match:
        return ""
    rest = text[hdr_match.end() :]
    nxt = re.search(r"^##\s+\S", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


# ─── Public build entry-point ─────────────────────────────────────────


def build_phase_ledger(session_dir: Path, phase: int) -> LedgerState:
    """Build the LedgerState for ``phase`` (2 or 4).

    Phase 2 includes claims (Phase 1 seed + Phase 2 R1 diff inventory)
    plus questions and disagreements from R≥2 rounds.

    Phase 4 includes issues, comments, and any disagreements raised
    during review rounds.
    """
    if phase not in (2, 4):
        return LedgerState(phase=phase)

    state = LedgerState(phase=phase)
    if phase == 2:
        _ingest_claims(state, session_dir)
        _ingest_questions(state, session_dir, phase=2)
        _ingest_disagreements(state, session_dir, phase=2)
        _apply_claim_escalations(state, session_dir, phase=2)
    else:  # phase == 4
        _ingest_questions(state, session_dir, phase=4)
        _ingest_disagreements(state, session_dir, phase=4)
        _ingest_issues(state, session_dir, phase=4)
        _ingest_comments(state, session_dir, phase=4)

    _compute_ghosted_rounds(state, session_dir, phase=phase)

    # Sort entries by (raised_round, raised_by, id) so the ledger is
    # presented in a stable chronological + agent-deterministic order.
    state.entries.sort(key=lambda e: (e.raised_round, e.raised_by, e.id))

    return state


# ─── Per-kind ingest ──────────────────────────────────────────────────


def _ingest_claims(state: LedgerState, session_dir: Path) -> None:
    from dual_research.ui.claims import reconstruct_claims
    for c in reconstruct_claims(session_dir):
        # Spec 0042 — Phase 1 claims have raised_round=0; Phase 2 R1
        # diff-inventory claims have raised_round=1 + phase=2 (we only
        # ingest into the Phase 2 ledger). Filter on phase to avoid
        # cross-contamination when this helper is called for ledger
        # state of one specific phase.
        if c.phase not in (1, 2):
            continue
        # Phase 1 claims are part of the Phase 2 ledger's "seed" — the
        # entry's phase here is Phase 2 (ledger phase), even though
        # the raising surface was Phase 1.
        entry = LedgerEntry(
            id=c.id,
            kind="claim",
            raised_round=c.raised_round,
            raised_by=c.raised_by,
            raised_turn_key=c.raised_turn_key,
            current_status="open",
            body_snippet=_body_snippet(c.body),
            status_history=[
                LedgerStatusTransition(
                    round=c.raised_round,
                    status="open",
                    reason="claim raised",
                    turn_key=c.raised_turn_key,
                )
            ],
        )
        state.entries.append(entry)


def _ingest_questions(state: LedgerState, session_dir: Path, *, phase: int) -> None:
    from dual_research.ui.questions import reconstruct_questions
    for q in reconstruct_questions(session_dir, phase=phase):
        entry = LedgerEntry(
            id=q.id,
            kind="question",
            raised_round=q.raised_round,
            raised_by=q.raised_by,
            raised_turn_key=q.raised_turn_key,
            current_status="open",
            body_snippet=_body_snippet(q.body),
            status_history=[
                LedgerStatusTransition(
                    round=q.raised_round,
                    status="open",
                    reason="question raised",
                    turn_key=q.raised_turn_key,
                )
            ],
        )
        if q.status == "answered":
            entry.current_status = "answered"
            entry.last_addressed_round = q.answered_round
            entry.status_history.append(LedgerStatusTransition(
                round=q.answered_round or q.raised_round,
                status="answered",
                reason=(
                    f"answered in {q.answered_turn_key} "
                    f"({'verbatim' if q.match == 'verbatim' else 'positional'} match)"
                ),
                turn_key=q.answered_turn_key or q.raised_turn_key,
            ))
        state.entries.append(entry)


def _ingest_disagreements(state: LedgerState, session_dir: Path, *, phase: int) -> None:
    from dual_research.ui.disagreements import reconstruct as reconstruct_disagreements
    for d in reconstruct_disagreements(session_dir, phase=phase):
        # The existing Disagreement model uses status values like
        # "open" / "resolved-claude" / "resolved-gpt" / "resolved-both".
        # Map them to ledger statuses.
        if d.status == "open":
            ledger_status = "open"
        else:
            ledger_status = "resolved"
        entry = LedgerEntry(
            id=d.id,
            kind="disagreement",
            raised_round=d.opened_round,
            raised_by=d.raised_by,
            raised_turn_key=d.raised_turn_key,
            current_status=ledger_status,
            body_snippet=_body_snippet(d.short_label or d.point),
            status_history=[
                LedgerStatusTransition(
                    round=d.opened_round,
                    status="open",
                    reason="disagreement raised",
                    turn_key=d.raised_turn_key,
                )
            ],
        )
        if ledger_status == "resolved":
            entry.last_addressed_round = d.closed_round
            entry.status_history.append(LedgerStatusTransition(
                round=d.closed_round or d.opened_round,
                status="resolved",
                reason=f"resolved ({d.status})",
                turn_key=d.closed_turn_key or d.raised_turn_key,
            ))
        state.entries.append(entry)


def _ingest_issues(state: LedgerState, session_dir: Path, *, phase: int) -> None:
    from dual_research.ui.issues import reconstruct_issues
    for i in reconstruct_issues(session_dir, phase=phase):
        ledger_status = "fixed" if i.status == "resolved" else "open"
        entry = LedgerEntry(
            id=i.id,
            kind="issue",
            raised_round=i.round_first_seen,
            raised_by=i.raised_by,
            raised_turn_key=i.raised_turn_key,
            current_status=ledger_status,
            body_snippet=_body_snippet(i.body),
            status_history=[
                LedgerStatusTransition(
                    round=i.round_first_seen,
                    status="open",
                    reason="issue raised",
                    turn_key=i.raised_turn_key,
                )
            ],
        )
        if ledger_status == "fixed":
            entry.last_addressed_round = i.round_last_seen
            entry.status_history.append(LedgerStatusTransition(
                round=i.round_last_seen,
                status="fixed",
                reason="absent from latest round's ledger by same raiser",
                turn_key=i.raised_turn_key,
            ))
        state.entries.append(entry)


def _ingest_comments(state: LedgerState, session_dir: Path, *, phase: int) -> None:
    from dual_research.ui.comments import reconstruct_comments
    for c in reconstruct_comments(session_dir, phase=phase):
        state.entries.append(LedgerEntry(
            id=c.id,
            kind="comment",
            raised_round=c.raised_round,
            raised_by=c.raised_by,
            raised_turn_key=c.raised_turn_key,
            current_status="noted",
            body_snippet=_body_snippet(c.body),
            status_history=[
                LedgerStatusTransition(
                    round=c.raised_round,
                    status="noted",
                    reason="comment noted",
                    turn_key=c.raised_turn_key,
                )
            ],
        ))


# ─── Claim → disagreement escalation linkage ──────────────────────────


def _apply_claim_escalations(state: LedgerState, session_dir: Path, *, phase: int) -> None:
    """Apply closure transitions to open claim entries by scanning
    later-round sections for matching D-N tokens.

    A claim flips status when its D-N appears in:
    - ``## Substantive disagreements I'm holding`` → ``escalated``
      (claim hardened into a held disagreement; the disagreement
      entry is tracked separately in the ledger).
    - ``## Resolved or non-blocking differences`` → ``escalated``
      with reason "resolved-without-escalation". Semantically the
      claim got addressed; the ``escalated`` status here is a
      shorthand for "no longer open" since we don't track a separate
      ``resolved`` claim state. (Future spec could distinguish if
      the lifecycle nuance matters.)
    - ``## Final-surfaced disagreements`` → ``escalated`` (claim
      hardened all the way through to final).

    Whichever signal fires first (by chronological round + agent
    order) wins.
    """
    phase_dir = session_dir / f"phase{phase}"
    if not phase_dir.is_dir():
        return

    # (round, backend_agent, source_kind, turn_key) per first occurrence
    # of each D-N in any closing section.
    d_id_first_close: dict[str, tuple[int, str, str, str]] = {}

    def _record_d_ids(text: str, hdr_re: re.Pattern[str], round_n: int,
                      backend_agent: str, turn_key: str, source_kind: str) -> None:
        hdr_match = hdr_re.search(text)
        if not hdr_match:
            return
        body = _section_body(text, hdr_match)
        for d_id in set(_D_TOKEN_RE.findall(body)):
            if d_id not in d_id_first_close:
                d_id_first_close[d_id] = (round_n, backend_agent, source_kind, turn_key)

    for entry in sorted(phase_dir.iterdir()):
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        if ".malformed" in entry.name:
            continue
        m = _ROUND_FILE_RE.match(entry.name)
        if not m:
            continue
        round_n = int(m.group(1))
        backend_agent = m.group(2)
        try:
            text = entry.read_text(encoding="utf-8")
        except OSError:
            continue
        turn_key = f"phase{phase}_round{round_n}_{'gpt' if backend_agent == 'openai' else backend_agent}"
        _record_d_ids(text, _SUBSTANTIVE_HDR_RE, round_n, backend_agent, turn_key, "substantive")
        _record_d_ids(text, _RESOLVED_HDR_RE, round_n, backend_agent, turn_key, "resolved")
        _record_d_ids(text, _FINAL_HDR_RE, round_n, backend_agent, turn_key, "final")

    for entry in state.entries:
        if entry.kind != "claim":
            continue
        if entry.current_status != "open":
            continue
        claim_d = _extract_d_id(entry.body_snippet)
        if claim_d is None:
            continue
        match = d_id_first_close.get(claim_d)
        if match is None:
            continue
        round_n, _backend_agent, source_kind, turn_key = match
        entry.current_status = "escalated"
        entry.last_addressed_round = round_n
        reasons = {
            "substantive": f"escalated to substantive disagreement {claim_d} in {turn_key}",
            "resolved":    f"closed via resolved-or-non-blocking differences ({claim_d}) in {turn_key}",
            "final":       f"closed via final-surfaced disagreements ({claim_d}) in {turn_key}",
        }
        entry.status_history.append(LedgerStatusTransition(
            round=round_n,
            status="escalated",
            reason=reasons[source_kind],
            turn_key=turn_key,
        ))


# ─── Ghosted-rounds bookkeeping ───────────────────────────────────────


def _compute_ghosted_rounds(state: LedgerState, session_dir: Path, *, phase: int) -> None:
    """For each entry, count the rounds in which it was OPEN at the
    start of the round AND received no addressing signal during the
    round.

    Addressing signal = a transition in ``status_history`` whose round
    matches. For entries that were open until end-of-phase and never
    addressed: ghosted_rounds = (last_round_observed -
    raised_round) — they were open through every round between.
    """
    phase_dir = session_dir / f"phase{phase}"
    if not phase_dir.is_dir():
        return

    # Determine the last observed round in this phase.
    last_round = 0
    for entry in phase_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        m = _ROUND_FILE_RE.match(entry.name)
        if m:
            last_round = max(last_round, int(m.group(1)))
    if last_round == 0:
        return

    for entry in state.entries:
        if entry.kind == "comment":
            continue  # terminal status; no ghosting
        addressed_rounds = {
            t.round for t in entry.status_history
            if t.status != "open"
        }
        # Rounds the entry was open: from raised_round+1 through
        # last_addressed_round (if addressed) or last_round (if still
        # open). Cap at last_round.
        start_round = max(entry.raised_round + 1, 1)
        end_round = entry.last_addressed_round if entry.last_addressed_round else last_round
        end_round = min(end_round, last_round)
        if end_round < start_round:
            continue
        # Count rounds in [start_round, end_round) where no addressing
        # transition happened. (The end_round itself is the round the
        # entry was addressed in — not ghosted. If still open, end_round
        # = last_round and is also still-open territory.)
        for r in range(start_round, end_round + 1):
            if r in addressed_rounds:
                continue
            if r == end_round and entry.last_addressed_round == r:
                continue
            entry.ghosted_rounds += 1
