"""Spec 0041 — reconstruct first-class ``Issue`` objects from turn files.

Phase 4 turn files maintain an ``## Issue ledger (delta + currently
open)`` section listing the reviewer's open concerns about the
converged draft. Unlike a Question, an Issue closes when the
**drafter's revision incorporates the fix** — the reviewer signals
this by dropping the entry from the next round's ledger, NOT by
writing an ``## Answers to:`` numbered line.

This module walks every Phase 4 turn file in chronological order for
each agent, builds the set of issues each round, and marks an issue
``resolved`` when it's absent from the latest round's ledger by that
same agent (matched by body-prefix). Pre-spec-0041 these entries were
silently bucketed as Questions and the cross-round positional-match
heuristic produced misleading "still open" counts.

Phase 2 also occasionally emits an Issue ledger when an agent flags
a draft-shape concern mid-negotiation; this module handles both
phases identically.
"""

from __future__ import annotations

import re
from pathlib import Path

from dual_research.protocol.parse import extract_review_items
from dual_research.ui.labels import ui_agent
from dual_research.ui.models import Issue


_ROUND_FILE_RE = re.compile(r"^round-(\d{2})-(claude|openai)\.md$")


def _turn_key(phase: int, round_n: int, agent_ui: str) -> str:
    return f"phase{phase}_round{round_n}_{agent_ui}"


# Each Issue ledger entry carries an identifier somewhere in its head:
#   **C-1** — open — ...                  (leading bold ID; rounds 2+)
#   **Description (C-7):** ...            (parenthesised ID; round 1 Claude)
#   **OAI-1 / D-OAI-1 — resolved — ...**  (compound; signature uses first)
#   **D-5** — `open` (non-blocking)       (Phase-2-carried disagreement)
#   **[I-g-r1-01]** — resolved — ...      (spec 0090 — cross-round system ID)
#   **OAI-P4-3** — open — ...             (phased-suffix form: OAI-P{n}-N)
# We scan the first ~200 chars for the FIRST occurrence of an ID-shaped
# token. The agents use it as the stable cross-round handle; the body
# wording around it shifts as the resolution lands. Fall back to a
# normalised body-prefix when no ID can be found.
#
# Spec 0090 § A.2 — broadened to also match lowercase-initial system
# IDs (``I-g-r1-01``, ``Cl-c-p1-04``, ``Q-c-r2-03``). Pre-spec the
# regex required all-uppercase initials, which silently dropped every
# claude-side cross-round ID and forced dedup to fall back to
# body-prefix matching — which then failed when the body rewording
# changed across rounds. This narrowed the catch but also masked
# the asymmetric ghosting visible in real production runs (the
# investigation under spec 0090's context section).
_ID_TOKEN_RE = re.compile(
    r"\b("
    # System-generated cross-round IDs (lowercase initial):
    r"I-[cg]-r\d+-\d+"
    r"|Q-[cg]-r\d+-\d+"
    r"|Cl-[cg]-[pr]\d+-\d+"
    # Agent-emitted human-readable IDs (uppercase):
    r"|OAI-P\d+-\d+"
    r"|D-OAI-\d+"
    r"|[A-Z]{1,4}-(?:[A-Z]{2,4}-)?\d+"
    r")\b"
)


def _body_signature(body: str) -> str:
    """Cheap matcher for "is this the same issue as last round".

    Preferred: the FIRST ``C-N`` / ``OAI-N`` / ``D-N`` token in the
    first 160 chars of the body. The agents use these as stable
    cross-round handles even when they rewrite the description.
    Fall back to a normalised body-prefix when no ID is found.
    """
    if not body:
        return ""
    head = body[:200]
    m = _ID_TOKEN_RE.search(head)
    if m:
        token = m.group(1).lower()
        return f"id:{token}"
    s = body.strip()
    s = re.sub(r"^\s*[\*_]+", "", s)
    s = s.lower()
    return "body:" + re.sub(r"\s+", " ", s).strip()[:120]


def _initial(agent_ui: str) -> str:
    return "c" if agent_ui == "claude" else "g"


def _extract_issues_from_turn(
    turn_text: str,
) -> list[tuple[str, str | None, str | None]]:
    items = extract_review_items(turn_text)
    return [
        (it.body, it.quote, it.after)
        for it in items
        if it.kind == "issue"
    ]


# The agent embeds a status marker inside each ledger entry's body:
#   **OAI-1** — `resolved` — body...
#   **OAI-1 — open — body...**
#   1. **OAI-2 — resolved — body...**
#   **D-5** — `open` (non-blocking, Phase 2 FSD) — ...
# We don't care about exact punctuation — we just need to find the first
# status word inside the leading "header" portion of the body (first
# ~200 chars are conservative). The marker is case-sensitive in
# practice but we lowercase to be forgiving of drift.
_STATUS_MARKER_RE = re.compile(
    r"\b(resolved|non[-_ ]blocking|held|escalated|open|new)\b",
    re.IGNORECASE,
)


def _status_from_body(body: str) -> str:
    """Map the marker tokens in the body to ``"open"`` or ``"resolved"``.

    Resolution rules — first match wins down the list:
    - ``non-blocking`` anywhere in the head → ``resolved``
      (overrides a leading ``open`` because the agent's
      ``OPEN_ISSUES: N`` end-of-turn counter doesn't count
      non-blocking carry-overs).
    - First marker is ``resolved`` → ``resolved``.
    - First marker is ``open`` / ``new`` / ``held`` / ``escalated``
      → ``open``.
    - No marker found → ``open`` (conservative).
    """
    if not body:
        return "open"
    head = body[:240].lower().replace("_", "-")
    if "non-blocking" in head:
        return "resolved"
    m = _STATUS_MARKER_RE.search(head)
    if not m:
        return "open"
    tok = m.group(1).lower().replace("_", "-").replace(" ", "-")
    if tok == "resolved":
        return "resolved"
    return "open"


def reconstruct_issues(session_dir: Path, *, phase: int) -> list[Issue]:
    """Build the ordered list of Issue objects for ``phase`` (2 or 4).

    The protocol's Issue ledger is structured as a running list with
    status markers (`open` / `resolved` / `non-blocking`) inside each
    entry's body. We extract those markers as the canonical status —
    not a cross-round body-signature heuristic — so the reconstructed
    counts agree with the agent's own ``OPEN_ISSUES: N`` end-of-turn
    counter (and the timeline chip that reads it).

    For each agent independently:
      1. Walk that agent's round files in numeric order.
      2. Within each round, dedupe issues by body-signature so a
         re-stated issue keeps its ``round_first_seen`` from the
         earlier round.
      3. The status of each Issue is the marker read from the
         LATEST round's entry (``open`` / ``resolved``).
      4. The Issue's ``round_last_seen`` is the latest round it
         appeared in.
    """
    phase_dir = session_dir / f"phase{phase}"
    if not phase_dir.is_dir():
        return []

    rounds_by_agent: dict[str, dict[int, str]] = {"claude": {}, "openai": {}}
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
        rounds_by_agent.setdefault(backend_agent, {})[round_n] = text

    out: list[Issue] = []
    for backend_agent, rounds in rounds_by_agent.items():
        if not rounds:
            continue
        ui = ui_agent(backend_agent)

        # signature → Issue
        active: dict[str, Issue] = {}
        per_agent_idx = 0
        for round_n in sorted(rounds.keys()):
            items = _extract_issues_from_turn(rounds[round_n])
            for (body, quote, after) in items:
                sig = _body_signature(body)
                if not sig:
                    continue
                marker = _status_from_body(body)
                if sig in active:
                    # Same issue restated this round — update the
                    # last-seen marker (current round's marker wins)
                    # and any anchors that weren't captured before.
                    active[sig].round_last_seen = round_n
                    active[sig].status = marker
                    if quote and not active[sig].quote:
                        active[sig].quote = quote
                    if after and not active[sig].after:
                        active[sig].after = after
                else:
                    per_agent_idx += 1
                    issue = Issue(
                        id=f"I-{_initial(ui)}-r{round_n}-{per_agent_idx:02d}",
                        phase=phase,
                        raised_by=ui,
                        round_first_seen=round_n,
                        round_last_seen=round_n,
                        status=marker,
                        body=body,
                        quote=quote,
                        after=after,
                        block_id=None,
                        raised_turn_key=_turn_key(phase, round_n, ui),
                    )
                    active[sig] = issue
                    out.append(issue)
    out.sort(key=lambda i: (i.phase, i.raised_by, i.round_first_seen))
    return out
