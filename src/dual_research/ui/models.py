"""Dataclasses matching the Claude Design UI shape (see
``~/Trimble/handoff/README.md`` §5).

These are Python-side internal representations. The HTTP server (spec 0010)
serializes them to JSON for the UI; field names are translated from
snake_case to camelCase at that boundary.

All shapes are plain mutable ``@dataclass`` (matching the project's existing
``SessionState`` convention). The aggregator mutates a single ``Run`` in
place as events arrive; defensive copies happen at the serialization layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# ─── Status vocabulary ────────────────────────────────────────────────────────

# Whole-run states (top-level Run.status).
RunStatus = Literal[
    "running",
    "converged",
    "deadlocked",
    "errored",
    "completed",
    "idle",
]

# Per-agent activity states (AgentState.status).
AgentStatus = Literal[
    "idle",
    "thinking",
    "drafting",
    "responding",
    "reviewing",
    "waiting",
]

# UI agent vocabulary. Backend uses {"claude", "openai"}; the aggregator
# translates "openai" → "gpt" at the labels.py boundary.
UiAgent = Literal["claude", "gpt"]


# ─── Turn (current/last) ──────────────────────────────────────────────────────


@dataclass
class Turn:
    """The ``currentTurn`` or ``lastTurn`` on an ``AgentState``.

    ``kind`` mirrors the UI's per-turn iconography:
        idle | thinking | plan-draft | response | doc-draft | review

    ``body`` is the full text of the turn (read from the corresponding round
    file once written). Empty string while the round file does not yet exist.

    ``summary``, ``agreed``, ``contested`` are populated on ``lastTurn`` only,
    and are intentionally sparse in v1 — the orchestrator does not emit them
    directly, and the UI tolerates empty values.
    """

    kind: str = "idle"
    index: int = 0
    body: str = ""
    summary: str | None = None
    agreed: list[str] = field(default_factory=list)
    contested: list[str] = field(default_factory=list)


# ─── AgentState ───────────────────────────────────────────────────────────────


@dataclass
class TokenUsage:
    in_: int = 0  # ``in`` is a Python keyword; serialized as ``in`` at the JSON boundary
    out: int = 0


@dataclass
class AgentState:
    status: AgentStatus = "idle"
    current_turn: Turn = field(default_factory=Turn)
    last_turn: Turn | None = None
    tokens: TokenUsage = field(default_factory=TokenUsage)
    cost: float = 0.0
    model_id: str | None = None  # populated from RunStarted; UI shows in chrome
    # Real context-window cap from the tier's ModelSpec (spec 0030).
    # Sourced from `RunStarted.{claude,openai}_context_window`. 0 when
    # unknown (pre-0030 transcripts); the UI falls back to 128k for the
    # bar denominator in that case.
    context_window: int = 0
    # Spec 0039: search-fee component of ``cost``. ``cost`` is now the
    # full per-agent invoice (tokens + searches); ``search_cost`` is the
    # breakdown so the CostBadge tooltip can show "of which web search".
    search_cost: float = 0.0


# ─── Round / Budget ───────────────────────────────────────────────────────────


@dataclass
class Round:
    current: int = 0
    soft: int = 6
    hard: int = 12


@dataclass
class Budget:
    limit: float
    warn_at: float = 0.75  # fraction of limit at which the meter goes yellow


# ─── Disagreement + Progression ───────────────────────────────────────────────


# UI's progression action taxonomy.
ProgressionAction = Literal[
    "raised",
    "rejected",
    "pushed back",
    "restated",
    "conceded",
    "aligned",
]


@dataclass
class ProgressionStep:
    round: int
    agent: str  # "claude" | "gpt" | "both" (UI vocabulary)
    action: ProgressionAction
    note: str = ""


# UI's disagreement status enum.
DisagreementStatus = Literal[
    "open",
    "resolved-claude",
    "resolved-gpt",
    "resolved-both",
]


@dataclass
class Disagreement:
    id: str  # e.g. "d-04" — UI displays as-is
    phase: int  # 2 or 4
    round: int  # latest round this disagreement was touched (for sort)
    opened_round: int
    closed_round: int | None = None
    status: DisagreementStatus = "open"
    deadlocked: bool = False  # set if hard cap was hit with this still open
    raised_by: str = "claude"  # "claude" | "gpt" | "both"
    short_label: str = ""  # 4–6 word headline
    point: str = ""  # full contested-point statement
    claude_position: str = ""
    gpt_position: str = ""
    resolution: str | None = None
    progression: list[ProgressionStep] = field(default_factory=list)
    # Spec 0034: turn-key references for cross-axis click-to-highlight.
    # ``raised_turn_key`` points at the timeline card where the first
    # progression step landed; ``closed_turn_key`` points at the turn
    # that flipped the status to resolved/non-blocking (None while
    # status == "open"). Format matches ``item.turnKey`` from spec
    # 0033 (e.g. ``phase2_round3_claude``).
    raised_turn_key: str = ""
    closed_turn_key: str | None = None


# ─── Question (spec 0034) ─────────────────────────────────────────────────────


QuestionStatus = Literal["open", "answered"]
QuestionMatch = Literal["positional", "verbatim"]


@dataclass
class Question:
    """Spec 0034 — first-class question object, parallel to ``Disagreement``.

    Questions in Phase 2 and Phase 4 turns previously only surfaced as a
    chip count on the timeline card (``TurnStats.open_questions``). This
    object captures the same data shape as a disagreement so the UI's
    Critique explorer can render Qs alongside Ds and the side-by-side
    viewer can pre-resolve their anchors.

    IDs follow ``Q-{raiser_initial}-r{round}-{idx}`` (e.g.
    ``Q-c-r1-01`` for Claude's first round-1 question). The protocol
    doesn't require agents to emit ``Q-N`` IDs — the parser assigns them
    deterministically at extraction time from the order they appear in
    the agent's ``## Open questions for X`` section.

    ``answered_*`` fields are populated by walking round R+1's
    ``## Answers to {other}'s open questions`` section in positional
    order. ``match='verbatim'`` means we also confirmed the answer
    quotes the question body; ``match='positional'`` is best-effort.
    """

    id: str  # "Q-c-r1-01"
    phase: int  # 2 | 4
    raised_round: int
    raised_by: str  # "claude" | "gpt"
    status: QuestionStatus = "open"
    body: str = ""
    quote: str | None = None
    after: str | None = None
    block_id: str | None = None
    raised_turn_key: str = ""
    answered_round: int | None = None
    answered_by: str | None = None
    answered_turn_key: str | None = None
    answer_body: str = ""  # excerpt of the answer when matched
    match: QuestionMatch | None = None  # set when answered


# ─── Issue + Comment (spec 0041) ─────────────────────────────────────────────


IssueStatus = Literal["open", "resolved"]


@dataclass
class Issue:
    """Spec 0041 D3 — items extracted from the Phase 4 ``Issue ledger
    (delta + currently open)`` section.

    An Issue is a reviewer-flagged problem with the converged draft.
    Status semantics differ from a Question: an Issue is closed when
    the drafter's revision incorporates the fix — which the reviewer
    signals by **dropping the entry from the next round's ledger**
    rather than by writing an ``## Answers to:`` numbered line.

    So an Issue's status is derived from presence/absence in the
    LATEST round's ledger snapshot (by raising agent), not from a
    cross-round positional match. ``round_first_seen`` is the round
    the issue first appeared; ``round_last_seen`` is the latest
    round it appeared in. ``status="resolved"`` iff the issue is
    absent from the latest round's ledger by the same agent.

    Pre-0041, these items were silently bucketed as Questions and
    rendered as a 61-strong "open questions" pile on the partner-
    vetting run even though the timeline correctly reported zero
    open issues. Spec 0041 D3 reconciles the two by giving issues
    their own type with their own closure semantics.
    """

    id: str  # "I-{agent}-r{round}-{idx}"
    phase: int  # 2 | 4
    raised_by: str  # "claude" | "gpt"
    round_first_seen: int
    round_last_seen: int
    status: IssueStatus = "open"
    body: str = ""
    quote: str | None = None
    after: str | None = None
    block_id: str | None = None
    raised_turn_key: str = ""


@dataclass
class Comment:
    """Spec 0041 — items extracted from ``Comments on the current draft``.

    Comments are non-blocking commentary. They have no closure
    protocol — once written, they stay as ``noted``. We capture them
    so the UI's Critique pane can surface them separately from
    issues and questions.
    """

    id: str  # "C-{agent}-r{round}-{idx}"
    phase: int  # 2 | 4
    raised_by: str
    raised_round: int
    body: str = ""
    quote: str | None = None
    after: str | None = None
    block_id: str | None = None
    raised_turn_key: str = ""


# ─── RunError ─────────────────────────────────────────────────────────────────


ErrorSeverity = Literal["critical", "error", "warning", "info"]
ErrorResolution = Literal["halted", "degraded", "recovered"]


@dataclass
class RunError:
    id: str
    timestamp: str  # ISO-8601 from the transcript event
    rel_ago: int  # seconds before "now" — UI re-derives, but a default is helpful
    code: str
    severity: ErrorSeverity
    run_id: str
    agent: str | None  # "claude" | "gpt" | None (orchestrator-level)
    phase: int | None
    where: str  # e.g. "phase-2 / round-3 / claude"
    summary: str
    detail: str = ""
    retried: int = 0
    resolved: ErrorResolution = "recovered"


# ─── Top-level error (when status == "errored") ───────────────────────────────


@dataclass
class TopLevelError:
    when: str
    where: str
    code: str
    detail: str


# ─── Per-turn protocol stats (for inline timeline chips, spec 0013) ───────────


@dataclass
class TurnStats:
    """The structured marker fields parsed from a single turn file.

    Each field is optional — agents occasionally omit a marker, and the
    UI silently drops chips whose value is ``None``.
    """

    status: str | None = None
    open_questions: int | None = None
    open_issues: int | None = None
    blocking: int | None = None
    fsd: int | None = None
    brief_issues: int | None = None


@dataclass
class PhaseStats:
    """All per-turn stats keyed by phase + (round, agent).

    - ``phase0`` and ``phase1`` are single-shot per-agent.
    - ``phase2`` and ``phase4`` are round-keyed dicts of per-agent stats.
    """

    phase0: dict[str, TurnStats] = field(default_factory=dict)
    phase1: dict[str, TurnStats] = field(default_factory=dict)
    phase2: dict[int, dict[str, TurnStats]] = field(default_factory=dict)
    phase4: dict[int, dict[str, TurnStats]] = field(default_factory=dict)


# ─── Per-turn token usage (spec 0029) ─────────────────────────────────────────


@dataclass
class TurnTokenUsage:
    """Per-turn token + cost detail, captured from ``TurnEnded`` events.

    One instance per API call. Stored on ``Run.phase_token_usage`` keyed by
    ``phase{N}_<agent>`` (single-shot phases) or
    ``phase{N}_round{R}_<agent>`` (round-loop phases) — the same key
    convention as ``phase_summaries`` and ``phase_review_items``.

    Powers the spec-0029 Consumption tab and (since spec 0030) its per-input
    segmented bars. ``in_`` is renamed to ``in`` at the JSON boundary
    (matches ``TokenUsage`` above).

    Spec 0030 added:
    - ``context_window``: real cap from the model's ``ModelSpec`` — the
      bar denominator on the frontend. 0 for pre-0030 transcripts (the
      UI falls back to ``AgentState.context_window`` or a hard default).
    - ``prompt_pieces``: per-piece token counts using the Tk vocabulary
      from how-it-works (``brief`` / ``d1`` / ``d2`` / ``hist`` / ``plan``
      / ``draft`` / ``histp``). Best-effort char÷3.5 heuristic computed at
      call time from the input strings — proportional, not invoice-grade.
      Empty dict for pre-0030 transcripts.
    """

    in_: int = 0
    out: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost: float = 0.0
    model_id: str | None = None
    context_window: int = 0
    prompt_pieces: dict[str, int] = field(default_factory=dict)
    # Spec 0031 + Spec 0039: web-search tool calls and their per-request
    # USD cost. ``cost`` (above) is the FULL per-turn cost (tokens +
    # search fees) since spec 0039 folded search fees into the headline
    # invoice. ``token_cost`` carries the breakdown so the Consumption
    # tab can show "of which tokens / of which web search" without
    # losing the total. Invariant: ``token_cost + search_cost == cost``.
    # ``searches`` is the count that ``search_cost`` was derived from.
    searches: int = 0
    search_cost: float = 0.0
    token_cost: float = 0.0
    # Spec 0033: relative path (from session dir) to the persisted
    # per-turn input bundle JSON. ``None`` for pre-0033 transcripts and
    # for turns whose ``TurnInputs`` event arrived but never landed on
    # disk. The UI server resolves this to an absolute path when
    # answering ``/api/runs/<id>/inputs/<key>``.
    input_path: str | None = None
    # Spec 0036: relative path (from session dir) to the persisted
    # per-turn web-search audit JSON. ``None`` for pre-0036 transcripts
    # or turns where web search didn't fire (or was disabled). The UI
    # server resolves this to an absolute path when answering
    # ``/api/runs/<id>/searches/<key>``.
    search_audit_path: str | None = None


# ─── Run ──────────────────────────────────────────────────────────────────────


@dataclass
class Run:
    """The full UI ``Run`` object. One per session directory.

    ``id`` is the canonical full session-dir name (used for URLs / API paths).
    ``display_id`` is the 4-char form the UI shows in chrome (mono cell).
    """

    id: str
    display_id: str
    topic: str = ""
    status: RunStatus = "running"
    phase: int = 0
    started_at_ago: int = 0  # seconds; updated by the server at serialization time
    started_at: str | None = None  # ISO-8601; the source of truth
    drafter: str | None = None  # "claude" | "gpt" | None
    phase_timings: dict[int, int | None] = field(
        default_factory=lambda: {0: None, 1: None, 2: None, 3: None, 4: None}
    )
    round: Round = field(default_factory=Round)
    budget: Budget | None = None  # client-side preference; None until set
    agents: dict[str, AgentState] = field(
        default_factory=lambda: {"claude": AgentState(), "gpt": AgentState()}
    )
    disagreements: list[Disagreement] = field(default_factory=list)
    # Set when ``disagreements`` is empty but at least one round file contains
    # literal ``D-<digit>`` anchors — i.e. the agent emitted disagreements that
    # the parser couldn't recognise. UI uses this to distinguish a parser miss
    # from a genuinely disagreement-free run.
    disagreements_parse_suspected_miss: bool = False
    # Spec 0034: first-class questions, parallel to disagreements. Both
    # phase 2 and phase 4 contribute. IDs are parser-assigned (the protocol
    # doesn't number questions).
    questions: list[Question] = field(default_factory=list)
    # Spec 0041: Phase 4 ``Issue ledger`` items + ``Comments on the current
    # draft`` items get their own typed lists, separate from Questions.
    # Pre-0041 these were silently bucketed as Questions and rendered
    # under that label on the Critique pane even though the protocol
    # tracks them with different closure semantics (issues are closed
    # by the drafter's revision; comments are non-blocking).
    issues: list[Issue] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)
    errors: list[RunError] = field(default_factory=list)
    error: TopLevelError | None = None  # populated only when status == "errored"
    phase_stats: PhaseStats = field(default_factory=PhaseStats)
    # ─── Summary cards (spec 0025) ────────────────────────────────────────────
    # `brief_summary` is a heuristic TL;DR of brief.md (synthesised, not LLM).
    # `phase_summaries` is keyed by `phase{N}_<agent>` or
    # `phase2_round{R}_<agent>` / `phase4_round{R}_<agent>`. Value is the
    # body under each turn's `## Summary` section. Missing keys mean the
    # agent didn't write one — the UI renders the card without a TL;DR.
    brief_summary: str | None = None
    phase_summaries: dict[str, str] = field(default_factory=dict)
    # ─── Review items (spec 0027 + 0028) ──────────────────────────────────────
    # Structured questions / disagreements / resolved items extracted from
    # Phase 2 + Phase 4 turn bodies. Keyed by `phase{N}_round{R}_<agent>`.
    # Each value is a list of dicts shaped like
    # `{kind, body, quote, after, item_id}` (serialised from ReviewItem).
    # Empty when the agent didn't anchor anything; missing keys for turns
    # we couldn't parse.
    phase_review_items: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    # ─── Phase 4 left-pane resolver (spec 0028) ───────────────────────────────
    # Path (relative to the session-dir) of the latest converged-document
    # version available — highest `phase4/draft-v*.md` if any drafter
    # revisions have landed, else `phase3/draft-v1.md`. Used by the Phase 4
    # side-by-side modal's left pane. None when neither file exists yet
    # (Phase 3 hasn't completed).
    current_draft_path: str | None = None
    # ─── Per-turn token usage (spec 0029) ─────────────────────────────────────
    # Keyed by `phase{N}_<agent>` for single-shot phases (0, 1, 3) and
    # `phase{N}_round{R}_<agent>` for round-loop phases (2, 4) — same
    # convention as `phase_summaries` / `phase_review_items`. Populated by
    # the aggregator on `TurnEnded` events; empty when the run was replayed
    # from a pre-0029 transcript that didn't record per-turn telemetry.
    # Drives the Consumption tab in the timeline pane.
    phase_token_usage: dict[str, TurnTokenUsage] = field(default_factory=dict)


# ─── RunListRow ───────────────────────────────────────────────────────────────


@dataclass
class RunListRow:
    id: str
    display_id: str
    status: RunStatus
    phase: int
    topic: str
    started_at_ago: int
    started_at: str | None
    duration: int  # seconds
    cost: float
    rounds: str | None = None  # e.g. "4/6", shown only for Phase 2/4 rows


# ─── Helpers ──────────────────────────────────────────────────────────────────


def to_jsonable(obj: Any) -> Any:
    """Recursively convert dataclass values to JSON-safe primitives.

    Renames ``in_`` → ``in`` (TokenUsage). The server layer (spec 0010) layers
    snake_case → camelCase on top of this.
    """
    from dataclasses import asdict, is_dataclass

    if is_dataclass(obj):
        return to_jsonable(asdict(obj))
    if isinstance(obj, dict):
        return {("in" if k == "in_" else k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_jsonable(v) for v in obj]
    return obj
