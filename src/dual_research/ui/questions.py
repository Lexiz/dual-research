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

    Spec 0041 D2 — only items classified as ``kind="question"`` count
    here. Pre-0041 the parser bucketed Phase 4's Issue ledger and
    Comments sections under ``"question"`` too; those now have their
    own kinds (``"issue"`` / ``"comment"``) and their own reconstruction
    paths in ``ui/issues.py`` / ``ui/comments.py``.
    """
    items = extract_review_items(turn_text)
    return [(it.body, it.quote, it.after) for it in items if it.kind == "question"]


# Spec 0090 § A — protocol IDs that may anchor an answer block's head.
# Covers every ID shape the protocol emits. Used to extract the first
# ID-like token from an answer block's first line for ID-based matching.
#
# Order matters: longer/more-specific patterns first so they're not
# pre-empted by shorter prefixes (e.g. ``OAI-P4-1`` must match before
# the bare ``OAI-1`` form).
_HEAD_ID_RE = re.compile(
    r"\b("
    r"Q-[cg]-r\d+-\d+"            # Q-c-r1-01, Q-g-r3-12
    r"|I-[cg]-r\d+-\d+"           # I-c-r2-05
    r"|Cl-[cg]-[pr]\d+-\d+"       # Cl-c-p1-04, Cl-c-r1-02
    r"|OAI-P\d+-\d+"              # OAI-P4-1
    r"|OAI-\d+"                   # OAI-1
    r"|FSD-\d+"                   # FSD-1
    r"|D-\d+"                     # D-3
    r"|C-\d+"                     # C-2
    r")\b"
)


# Recognised block-start patterns inside an "Answers to" section body.
# Used by ``_extract_answer_blocks`` to split the section into per-answer
# blocks regardless of which surface format the agent chose.
_BLOCK_START_NUMBERED_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")  # `1. foo` / `2) foo`
_BLOCK_START_BOLD_LINE_RE = re.compile(r"^\*\*[^*\n]+\*\*\s*:?\s*$")  # `**Q-g-r1-01 — title**`
_BLOCK_START_H3_RE = re.compile(r"^###\s+\S")  # `### Q-g-r1-01: title`


def _block_head_id(head_line: str) -> str | None:
    """Return the first protocol-ID-shaped token in ``head_line``, or None.

    The head line is the first line of an answer block (the numbered-list
    item line, the bold-header line, or the H3 heading line). For
    ID-based matching to fire, the ID must be present in this head — IDs
    appearing only in the body are NOT used (prevents narrative
    cross-references like "see Q-g-r1-01 above" from triggering false
    matches).
    """
    m = _HEAD_ID_RE.search(head_line)
    return m.group(1) if m else None


def _extract_answer_blocks(
    turn_text: str, *, other_name: str
) -> list[tuple[str | None, str]]:
    """Pull answer blocks from a turn's "Answers to" section.

    Returns ``[(head_id, body), ...]`` in source order. ``head_id`` is
    the first protocol-ID-shaped token on the block's head line (or
    ``None`` if the head carries no ID — then positional matching is
    the fallback in ``reconstruct_questions``).

    ``other_name`` is the backend agent name (``"claude"`` / ``"openai"``)
    whose questions are being answered.

    Spec 0040 — the protocol uses two phrasings depending on the phase:
    - Phase 2: ``## Answers to {other}'s open questions``
    - Phase 4: ``## Answers to {other}'s prior comments``
    Both forms are accepted. Capitalisation is flexible (case-insensitive).

    Spec 0090 § A — three block-start patterns are recognised so the
    extractor works across the formats both vendor models actually
    emit (Claude prefers bold-header per-Q blocks; OpenAI prefers
    numbered-list with embedded bold IDs). Pre-spec the extractor only
    saw numbered lists, which silently dropped half the answers in
    real production runs (see spec 0090 context).
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
    # Stop at the next H2 heading. (We don't need fence-awareness here
    # — the "Answers to" section is plain prose, not inside a fence.)
    end = re.search(r"^##\s+\S", rest, re.MULTILINE)
    body = rest[: end.start()] if end else rest

    blocks: list[tuple[str | None, str]] = []
    current_head: str | None = None
    current_lines: list[str] | None = None

    def _flush() -> None:
        nonlocal blocks, current_head, current_lines
        if current_lines is None:
            return
        # Join body lines (NOT the head line; it's stored separately).
        body_text = "\n".join(current_lines).strip()
        if body_text or current_head is not None:
            blocks.append((current_head, body_text))
        current_head = None
        current_lines = None

    for line in body.splitlines():
        # Detect a new block start.
        m_num = _BLOCK_START_NUMBERED_RE.match(line)
        m_bold = _BLOCK_START_BOLD_LINE_RE.match(line)
        m_h3 = _BLOCK_START_H3_RE.match(line)
        if m_num:
            _flush()
            head_content = m_num.group(2)
            current_head = _block_head_id(head_content)
            current_lines = [head_content]
        elif m_bold:
            _flush()
            current_head = _block_head_id(line)
            current_lines = []  # body follows on subsequent lines
        elif m_h3:
            _flush()
            current_head = _block_head_id(line)
            current_lines = []
        elif current_lines is not None:
            current_lines.append(line)
        # else: pre-first-block text (e.g. an intro line); skip.
    _flush()
    return blocks


# Backward-compat shim: callers that want only the body strings (the
# pre-spec-0090 signature) can still call ``_extract_answers_from_turn``.
def _extract_answers_from_turn(turn_text: str, *, other_name: str) -> list[str]:
    """Bodies only, in source order. Preserves the pre-spec-0090 return
    type for any external callers; ``reconstruct_questions`` uses the
    richer ``_extract_answer_blocks`` directly."""
    return [body for _id, body in _extract_answer_blocks(turn_text, other_name=other_name)]


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


# Spec 0090 § A — how many rounds beyond ``raised_round`` we scan for an
# answer. Most answers land in `raised_round + 1`, but agents sometimes
# defer (especially across hash-drift-repair rounds or when the answer
# becomes part of a larger argument in a later round). 5 covers the
# typical Phase 2 / Phase 4 soft cap with headroom.
MAX_ANSWER_LOOKAHEAD_ROUNDS = 5


def reconstruct_questions(session_dir: Path, *, phase: int) -> list[Question]:
    """Build the ordered list of Question objects for ``phase`` (2 or 4).

    Walks ``session_dir/phase{N}/round-NN-{agent}.md`` files, extracts
    questions from each, then walks SUBSEQUENT rounds' per-agent turn
    files to thread answer matches.

    Spec 0090 § A — matching is now ID-based when the answering agent
    includes the question's protocol ID (``Q-c-r1-01`` etc.) in the
    head line of their answer block. When the head carries no ID, we
    fall back to positional matching for backward compatibility. Look-
    ahead extends to ``MAX_ANSWER_LOOKAHEAD_ROUNDS`` rounds beyond the
    raised round (was: only the immediate next round). First match
    wins; later restatements of the same Q-N don't overwrite an
    earlier answered status.
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

    # Build the question objects first (no answer linkage yet).
    out: list[Question] = []
    # qid → Question for ID-based lookup during answer matching.
    by_id: dict[str, Question] = {}
    for round_n in sorted(rounds):
        per_agent = rounds[round_n]
        for backend_agent in ("claude", "openai"):
            entry = per_agent.get(backend_agent)
            if not entry:
                continue
            _, questions = entry
            ui_raiser = ui_agent(backend_agent)
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
                out.append(q)
                by_id[qid] = q

    # Walk every (round, agent) AGAIN to link answers. The answer for
    # Q raised by agent X in round R may appear in any of agent (NOT X)'s
    # rounds R+1 .. R+MAX_ANSWER_LOOKAHEAD_ROUNDS. We iterate in chronological
    # order so the earliest matching answer wins.
    for answer_round in sorted(rounds):
        for answerer_backend in ("claude", "openai"):
            answerer_entry = rounds[answer_round].get(answerer_backend)
            if not answerer_entry:
                continue
            other_backend = "openai" if answerer_backend == "claude" else "claude"
            # Each answer block in this turn might link to a question
            # raised by the OTHER agent in some earlier round.
            answer_blocks = _extract_answer_blocks(
                answerer_entry[0], other_name=other_backend,
            )
            answerer_ui = ui_agent(answerer_backend)
            other_ui = ui_agent(other_backend)

            # ID-based pass first: any block whose head carries a Q-N
            # token gets matched directly. Tracks consumed positions
            # so the positional-fallback pass below doesn't re-use them.
            positional_blocks: list[tuple[int, str]] = []
            for idx, (head_id, body_text) in enumerate(answer_blocks):
                if head_id is not None and head_id.startswith("Q-"):
                    q = by_id.get(head_id)
                    if q is None or q.status == "answered":
                        # Either unknown ID (shouldn't happen if agents
                        # use the standing-items section) OR already
                        # matched — first match wins, skip.
                        continue
                    # Only accept the answer if the question was raised
                    # in a round STRICTLY BEFORE this answer round and
                    # within the look-ahead window.
                    delta = answer_round - q.raised_round
                    if delta <= 0 or delta > MAX_ANSWER_LOOKAHEAD_ROUNDS:
                        continue
                    # And the answer must be FROM the other agent
                    # (the one who didn't raise it).
                    if q.raised_by == answerer_ui:
                        continue
                    q.status = "answered"
                    q.answered_round = answer_round
                    # The answerer is the agent writing this turn; they
                    # answer questions raised by the OTHER agent. So
                    # answered_by = answerer (not other).
                    q.answered_by = answerer_ui
                    q.answered_turn_key = _turn_key(phase, answer_round, answerer_ui)
                    q.answer_body = body_text
                    q.match = "verbatim" if _confirms_question(body_text, q.body) else "positional"
                else:
                    positional_blocks.append((idx, body_text))

            # Positional-fallback pass: any blocks without IDs get
            # matched positionally against the OTHER agent's MOST RECENT
            # round of questions that are still open. This matches the
            # pre-spec-0090 behaviour for legacy turns where agents
            # haven't switched to the new ID-anchored format yet.
            if positional_blocks:
                # Find the most recent prior round where `other_backend`
                # raised questions.
                candidate_round = answer_round - 1
                while candidate_round >= 1:
                    if (
                        candidate_round in rounds
                        and other_backend in rounds[candidate_round]
                        and rounds[candidate_round][other_backend][1]
                    ):
                        break
                    candidate_round -= 1
                if candidate_round >= 1 and answer_round - candidate_round <= MAX_ANSWER_LOOKAHEAD_ROUNDS:
                    raiser_questions = rounds[candidate_round][other_backend][1]
                    # Pull the still-open ones in their original numbering.
                    still_open: list[Question] = []
                    for idx, _ in enumerate(raiser_questions, start=1):
                        qid = f"Q-{_raiser_initial(ui_agent(other_backend))}-r{candidate_round}-{idx:02d}"
                        q = by_id.get(qid)
                        if q is not None and q.status == "open":
                            still_open.append(q)
                    for (block_idx, body_text), q in zip(positional_blocks, still_open):
                        q.status = "answered"
                        q.answered_round = answer_round
                        q.answered_by = answerer_ui  # see ID-pass comment
                        q.answered_turn_key = _turn_key(phase, answer_round, answerer_ui)
                        q.answer_body = body_text
                        q.match = "verbatim" if _confirms_question(body_text, q.body) else "positional"

    return out
