"""Spec 0034 — reconstruct first-class ``Question`` objects from turn files.

The protocol asks each agent in Phase 2 / Phase 4 to maintain an
``## Open questions for {other}`` section listing the questions they
want the other agent to address. In the next round, the other agent's
``## Answers to {other}'s open questions`` section addresses those
in order. This module walks every turn file in a phase, assigns stable
IDs to each question at parse time, and threads the answer linkage by
positional match (with verbatim-text confirmation as a quality signal).

ID shape: ``Q-{raiser_initial}-r{round}-{idx}`` (e.g. ``Q-c-r1-01``).
The raiser initial is ``c`` for Claude and ``g`` for GPT (the UI
vocabulary; the file system uses ``claude`` / ``openai``). Indices are
0-padded to 2 digits and start at 1.

This module is the analogue of ``ui/disagreements.py::reconstruct`` for
the Question side of the critique. They share the wire-format
camelization treatment in ``ui/server.py::_to_camel``.
"""

from __future__ import annotations

import re
from pathlib import Path

from dual_research.protocol.parse import extract_review_items
from dual_research.ui.labels import ui_agent
from dual_research.ui.models import Question


# Round-file naming convention. Same regex as in ``ui/disagreements.py``.
_ROUND_FILE_RE = re.compile(r"^round-(\d{2})-(claude|openai)\.md$")


def _raiser_initial(agent: str) -> str:
    """``"claude"`` → ``"c"``; ``"gpt"`` / ``"openai"`` → ``"g"``."""
    return "c" if agent == "claude" else "g"


def _turn_key(phase: int, round_n: int, agent_ui: str) -> str:
    """Wire-compatible turn key, matching the ``item.turnKey`` plumbed by
    spec 0033's ``buildLiveTimeline``. snake-case here; the camelizer at
    the server boundary handles the rewrite to ``phase2Round3Claude``."""
    return f"phase{phase}_round{round_n}_{agent_ui}"


def _extract_questions_from_turn(turn_text: str) -> list[tuple[str, str | None, str | None]]:
    """Walk a turn's review items and pull out the question bodies + anchors.

    Returns ``[(body, quote, after), ...]`` in the order the parser
    emitted them — which mirrors the agent's numbered list.
    """
    items = extract_review_items(turn_text)
    return [(it.body, it.quote, it.after) for it in items if it.kind == "question"]


def _extract_answers_from_turn(turn_text: str, *, other_name: str) -> list[str]:
    """Pull the numbered answers from a turn's "Answers to" section.

    Returns the bodies in numbered order.

    ``other_name`` is the backend agent name (``"claude"`` / ``"openai"``)
    whose questions are being answered.

    Spec 0040 — the protocol uses two phrasings depending on the phase:
    - Phase 2: ``## Answers to {other}'s open questions``
    - Phase 4: ``## Answers to {other}'s prior comments``
    Both forms are accepted. Capitalisation is flexible (case-insensitive).
    A future phase with yet another phrasing adds a new alternation here.
    """
    if not turn_text:
        return []
    pattern = re.compile(
        r"^##\s+Answers to\s+"
        + re.escape(other_name)
        + r"['']?s\s+(?:open questions|prior comments)\b",
        re.MULTILINE | re.IGNORECASE,
    )
    m = pattern.search(turn_text)
    if not m:
        return []
    rest = turn_text[m.end():]
    # Stop at the next H2 heading.
    end = re.search(r"^##\s+\S", rest, re.MULTILINE)
    body = rest[: end.start()] if end else rest

    # Numbered list items, same regex shape as parse._NUMBERED_RE.
    numbered_re = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
    answers: list[str] = []
    current: list[str] | None = None
    for line in body.splitlines():
        if numbered_re.match(line):
            if current is not None:
                joined = "\n".join(current).strip()
                if joined:
                    answers.append(joined)
            current = [numbered_re.match(line).group(2)]
        elif current is not None:
            current.append(line)
    if current is not None:
        joined = "\n".join(current).strip()
        if joined:
            answers.append(joined)
    return answers


def _normalize_for_match(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


_QUESTION_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "should",
    "could", "can", "may", "might", "must", "shall", "and", "or", "but",
    "if", "then", "else", "what", "when", "where", "who", "whom", "why",
    "how", "which", "that", "this", "these", "those", "you", "your",
    "we", "our", "i", "my", "me", "us", "of", "in", "on", "at", "to",
    "for", "with", "by", "from", "about", "as", "any", "all", "some",
    "it", "its", "they", "their", "them",
})


def _content_tokens(text: str) -> list[str]:
    """Lowercase non-stopword tokens of length >= 4. Strips punctuation."""
    if not text:
        return []
    norm = re.sub(r"[^\w\s-]", " ", text.lower())
    tokens = []
    for w in norm.split():
        if len(w) < 4:
            continue
        if w in _QUESTION_STOPWORDS:
            continue
        tokens.append(w)
    return tokens


def _confirms_question(answer_body: str, question_body: str) -> bool:
    """Verbatim-match confidence check (D3): does the answer mention enough
    of the question's content tokens that we can confidently say they're
    talking about the same thing?

    Strategy: take the question's content tokens (non-stopword, ≥4 chars).
    If 3+ of those tokens (or all of them, whichever is smaller) appear in
    the answer body, treat as confirmed.

    Tuned for the real shape of LLM-paraphrased answers: an answer like
    "Yes, we load-tested SQLite under WAL mode with 1000 concurrent
    readers" confirms a question that asks "Have you load-tested SQLite
    under WAL mode?" — without requiring the question's question-words
    to echo into the answer.
    """
    if not answer_body or not question_body:
        return False
    q_tokens = _content_tokens(question_body)
    if not q_tokens:
        return False
    a_text = " " + _normalize_for_match(answer_body) + " "
    threshold = min(3, len(q_tokens))
    hits = 0
    for tok in q_tokens:
        if f" {tok} " in a_text or f" {tok}." in a_text or f" {tok}," in a_text:
            hits += 1
            if hits >= threshold:
                return True
    return False


def reconstruct_questions(session_dir: Path, *, phase: int) -> list[Question]:
    """Build the ordered list of Question objects for ``phase`` (2 or 4).

    Walks ``session_dir/phase{N}/round-NN-{agent}.md`` files, extracts
    questions from each, then walks the NEXT round's per-agent turn
    files to thread answer matches positionally.
    """
    phase_dir = session_dir / f"phase{phase}"
    if not phase_dir.is_dir():
        return []

    # rounds[round_n][backend_agent] = (turn_text, [(body, quote, after), ...])
    rounds: dict[int, dict[str, tuple[str, list[tuple[str, str | None, str | None]]]]] = {}
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
        questions = _extract_questions_from_turn(text)
        rounds.setdefault(round_n, {})[backend_agent] = (text, questions)

    out: list[Question] = []
    for round_n in sorted(rounds):
        per_agent = rounds[round_n]
        for backend_agent in ("claude", "openai"):
            entry = per_agent.get(backend_agent)
            if not entry:
                continue
            _, questions = entry
            other_backend = "openai" if backend_agent == "claude" else "claude"
            other_ui = ui_agent(other_backend)
            ui_raiser = ui_agent(backend_agent)
            # Look up next-round answers from the OTHER agent's turn file.
            next_round = rounds.get(round_n + 1, {})
            answerer_entry = next_round.get(other_backend)
            answer_texts = (
                _extract_answers_from_turn(
                    answerer_entry[0], other_name=backend_agent
                )
                if answerer_entry
                else []
            )
            for idx, (body, quote, after) in enumerate(questions, start=1):
                qid = f"Q-{_raiser_initial(ui_raiser)}-r{round_n}-{idx:02d}"
                q = Question(
                    id=qid,
                    phase=phase,
                    raised_round=round_n,
                    raised_by=ui_raiser,
                    status="open",
                    body=body,
                    quote=quote,
                    after=after,
                    block_id=None,  # resolved by aggregator with prior blocks
                    raised_turn_key=_turn_key(phase, round_n, ui_raiser),
                )
                if idx - 1 < len(answer_texts):
                    answer_body = answer_texts[idx - 1]
                    q.status = "answered"
                    q.answered_round = round_n + 1
                    q.answered_by = other_ui
                    q.answered_turn_key = _turn_key(phase, round_n + 1, other_ui)
                    q.answer_body = answer_body
                    q.match = "verbatim" if _confirms_question(answer_body, body) else "positional"
                out.append(q)
    return out
