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
