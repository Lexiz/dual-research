"""Spec 0114 — phase artifact templates + canonical hashing.

Each interaction phase has a hash-matched artifact block. Convergence
requires both agents to emit byte-identical text (after light
normalization) — the orchestrator computes a normalized SHA-256 hash of
each side's block and asserts the two hashes match.

Templates here are reference layouts the prompts include; the parser
extracts the artifact body verbatim from each agent's turn and hashes
it. The actual hashing is normalization → SHA-256, lowercase hex.

Phase 4's artifact also carries the draft's content hash; the parser
verifies both agents agreed to the same ``draft_version`` and same
``draft_hash``, and the orchestrator cross-checks that the drafter did
not revise the draft in this round.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum


# Normalization pass for canonical hashing — collapse all whitespace
# runs, fold smart quotes / dashes, strip leading/trailing whitespace.
# Same rules as evidence content matching; kept in sync so semantics
# don't drift between subsystems.
_WS_RE = re.compile(r"\s+")
_SMART_QUOTES = {
    "‘": "'", "’": "'",
    "“": '"', "”": '"',
    "–": "-", "—": "-",
}


def _normalize_for_hash(text: str) -> str:
    if not text:
        return ""
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    for smart, plain in _SMART_QUOTES.items():
        out = out.replace(smart, plain)
    out = _WS_RE.sub(" ", out)
    return out.strip()


def canonical_hash(artifact_text: str) -> str:
    """Return the canonical SHA-256 hex digest of ``artifact_text``."""
    return hashlib.sha256(_normalize_for_hash(artifact_text).encode("utf-8")).hexdigest()


# ─── Template strings (reference layouts) ─────────────────────────────

AGREED_INTERPRETATION_TEMPLATE = """\
### AGREED_INTERPRETATION

#### Scope
- In scope:
  - <bullet>
- Out of scope:
  - <bullet>

#### Approach
<one paragraph: how the research will be conducted, what stance the
 agents are taking, what weightings apply, what posture they have
 toward the source materials>

#### Carry-forward items
- [<id>] <terminal-state>: <body> — <one-line rationale for carrying forward>
(or "(none)")
"""


AGREED_PLAN_TEMPLATE = """\
### AGREED_PLAN

#### Sections
1. Title: <section title>
   Key claims:
   - <key claim>
2. ...

#### Carry-forward items (from phase 2)
- [<id>] <terminal-state>: <body> — <where this appears in the final document>
(or "(none)")

#### Drafter
DRAFTER: claude | openai
"""


AGREED_DRAFT_ACCEPTANCE_TEMPLATE = """\
### AGREED_DRAFT_ACCEPTANCE

draft_version: v<N>
draft_hash: <SHA-256 hex of the draft file content>
endorsement: |
  <one sentence on why this draft satisfies the brief>
"""


# Mapping from phase number to the artifact heading the parser looks for
# in the ``## Phase artifact`` section. Used by the orchestrator's
# convergence cross-check.
ARTIFACT_HEADING: dict[int, str] = {
    0: "AGREED_INTERPRETATION",
    2: "AGREED_PLAN",
    4: "AGREED_DRAFT_ACCEPTANCE",
}


def hash_draft_content(text: str) -> str:
    """Hash the on-disk draft content for phase 4's ``draft_hash``.

    Uses the same normalization as the artifact hash so a draft that
    differs only in trailing-newline / smart-quote substitution still
    matches.
    """
    return canonical_hash(text)


# ─── Spec 0117 — artifact registry ────────────────────────────────────
#
# Single source of truth mapping every canonical artifact ID to its
# human-readable display name. Every consumer (UI, validator, CLI,
# how-it-works diagrams) resolves names through ``display_name()``;
# display strings are never duplicated outside this module.


class ArtifactKind(StrEnum):
    SYSTEM = "system"
    USER = "user"
    DERIVED = "derived"
    AGENT_OUTPUT = "agent_output"
    AGREEMENT = "agreement"
    DRAFT = "draft"
    FINAL = "final"


@dataclass(frozen=True)
class ArtifactDef:
    id_template: str  # e.g. "phase0.<agent>.r<N>"
    display_template: str  # e.g. "Preflight turn · {agent} · round {n}"
    kind: ArtifactKind
    scope: str  # "run" | "per-turn" | "per-round" | "per-phase" | "per-revision"
    per_agent: bool  # True when there is one instance per agent


REGISTRY: tuple[ArtifactDef, ...] = (
    ArtifactDef("system.preamble", "Methodology preamble",
                ArtifactKind.SYSTEM, "run", False),
    ArtifactDef("system.task.input", "Preflight instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("system.task.research_plan", "Research-plan instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("system.task.plan_negotiation", "Plan-negotiation instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("system.task.drafting", "Drafting instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("system.task.review", "Review instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("system.task.closeout", "Closeout instructions",
                ArtifactKind.SYSTEM, "per-turn", False),
    # Spec 0148 D13 — concatenated text of every web_search_tool_result /
    # web_search_call.action.sources entry on this turn's response. The
    # provider feeds search snippets back to the model mid-generation;
    # those snippets contribute to the turn's input-token bill but
    # spec-0145's prompt-pieces emitter never broke them out. The agent
    # layer concatenates the surfaced title + url per result (best
    # available without decrypted snippet text) and stashes the
    # concatenated string in ``AgentResult.extras["web_sources_text"]``;
    # orchestrator/_call.py tokenises it and emits this piece.
    ArtifactDef("system.web_sources", "Web search results",
                ArtifactKind.SYSTEM, "per-turn", False),
    # Spec 0148 D14 — JSON-serialised tools array the agent ships to
    # the provider API. Small (~15-25 tokens) but discoverable on the
    # Consumption card so the operator can see the per-turn cost of
    # ferrying tool defs vs. the prompt instructions proper. Emitted
    # from ``AgentResult.extras["tool_definitions_text"]`` via the
    # same orchestrator/_call.py augmentation site as system.web_sources.
    ArtifactDef("system.tool_definitions", "Tool definitions",
                ArtifactKind.SYSTEM, "per-turn", False),
    ArtifactDef("user_prompt", "User prompt",
                ArtifactKind.USER, "run", False),
    ArtifactDef("user_prompt.message", "Chat message",
                ArtifactKind.USER, "run", False),
    ArtifactDef("user_prompt.attachment.<id>", "Attachment · {title}",
                ArtifactKind.USER, "run", False),
    ArtifactDef("prior_turns.phase0", "Prior preflight turns",
                ArtifactKind.DERIVED, "per-round", False),
    ArtifactDef("prior_turns.phase2", "Prior negotiation turns",
                ArtifactKind.DERIVED, "per-round", False),
    ArtifactDef("prior_turns.phase4", "Prior review turns",
                ArtifactKind.DERIVED, "per-round", False),
    ArtifactDef("ledger.standing_items", "Ledger (standing items)",
                ArtifactKind.DERIVED, "per-round", True),
    ArtifactDef("closeout.request", "Closeout request",
                ArtifactKind.SYSTEM, "per-round", True),
    ArtifactDef("phase0.<agent>.r<N>", "Preflight turn · {agent} · round {n}",
                ArtifactKind.AGENT_OUTPUT, "per-turn", True),
    ArtifactDef("phase1.claude", "Claude's research plan",
                ArtifactKind.AGENT_OUTPUT, "run", True),
    ArtifactDef("phase1.openai", "GPT's research plan",
                ArtifactKind.AGENT_OUTPUT, "run", True),
    ArtifactDef("phase2.<agent>.r<N>", "Negotiation turn · {agent} · round {n}",
                ArtifactKind.AGENT_OUTPUT, "per-turn", True),
    ArtifactDef("phase3.draft.v1", "Initial unified draft (v1)",
                ArtifactKind.DRAFT, "run", False),
    ArtifactDef("phase4.<agent>.r<N>", "Review turn · {agent} · round {n}",
                ArtifactKind.AGENT_OUTPUT, "per-turn", True),
    ArtifactDef("phase4.draft.v<N>", "Revised draft v{n}",
                ArtifactKind.DRAFT, "per-revision", False),
    ArtifactDef("current_draft", "Current draft (latest version)",
                ArtifactKind.DRAFT, "per-round", False),
    ArtifactDef("all_p2_turns", "All negotiation turns",
                ArtifactKind.DERIVED, "run", False),
    ArtifactDef("phase0.agreement.interpretation", "Agreed interpretation",
                ArtifactKind.AGREEMENT, "run", False),
    ArtifactDef("phase2.agreement.plan", "Agreed plan",
                ArtifactKind.AGREEMENT, "run", False),
    ArtifactDef("phase2.agreement.drafter", "Drafter selection",
                ArtifactKind.AGREEMENT, "run", False),
    ArtifactDef("phase4.agreement.draft_acceptance", "Agreed draft acceptance",
                ArtifactKind.AGREEMENT, "run", False),
    ArtifactDef("carry_forward.phase0", "Carry-forward items (phase 0)",
                ArtifactKind.DERIVED, "per-phase", False),
    ArtifactDef("carry_forward.phase2", "Carry-forward items (phase 2)",
                ArtifactKind.DERIVED, "per-phase", False),
    ArtifactDef("carry_forward.phase4", "Carry-forward items (phase 4)",
                ArtifactKind.DERIVED, "per-phase", False),
    ArtifactDef("all_carry_forward", "All carry-forward items",
                ArtifactKind.DERIVED, "run", False),
    ArtifactDef("final.document", "Final document",
                ArtifactKind.FINAL, "run", False),
)


_AGENT_DISPLAY = {"claude": "Claude", "openai": "GPT", "gpt": "GPT"}

_TEMPLATE_VAR_RE = re.compile(r"<(agent|N|id)>")


def _id_template_to_regex(id_template: str) -> re.Pattern[str]:
    """Convert an id_template like ``phase0.<agent>.r<N>`` into a regex
    with named groups so a concrete ID can be matched against it.
    """
    # NB: in Python ≥3.7 ``re.escape`` only escapes regex metacharacters,
    # so ``<`` and ``>`` stay unescaped — replace the bare placeholders.
    pattern = re.escape(id_template)
    pattern = pattern.replace("<agent>", r"(?P<agent>claude|openai|gpt)")
    pattern = pattern.replace("<N>", r"(?P<n>\d+)")
    pattern = pattern.replace("<id>", r"(?P<id>[^.]+(?:\..+)?)")
    return re.compile(f"^{pattern}$")


# Pre-compile each registry entry's regex once at import time.
_REGISTRY_REGEX: tuple[tuple[ArtifactDef, re.Pattern[str]], ...] = tuple(
    (defn, _id_template_to_regex(defn.id_template)) for defn in REGISTRY
)


def display_name(
    artifact_id: str,
    *,
    title_for_id: dict[str, str] | None = None,
) -> str:
    """Resolve an artifact ID to its human-readable display name.

    Substitutes variable parts (``<agent>``, ``<N>``, ``<id>``) into the
    display template. For ``<id>`` (attachment IDs), the caller provides
    ``title_for_id`` mapping attachment-id → human title (looked up at
    run time from attachments.json). Falls back to the ID itself if no
    title is supplied.

    Returns the unchanged ``artifact_id`` if no template matches — this
    is a signal that the registry is incomplete, which the coverage
    test in the test plan turns into a CI failure.
    """
    for defn, rx in _REGISTRY_REGEX:
        m = rx.match(artifact_id)
        if not m:
            continue
        groups = m.groupdict()
        subs: dict[str, str] = {}
        if groups.get("agent"):
            subs["agent"] = _AGENT_DISPLAY.get(groups["agent"], groups["agent"])
        if groups.get("n"):
            subs["n"] = groups["n"]
        if groups.get("id"):
            raw = groups["id"]
            subs["title"] = (title_for_id or {}).get(raw, raw)
        try:
            return defn.display_template.format(**subs)
        except KeyError:
            return defn.display_template
    return artifact_id


def is_known(artifact_id: str) -> bool:
    """True iff ``artifact_id`` matches any template in REGISTRY.

    Also returns True for the literal template strings themselves
    (e.g. ``"phase0.<agent>.r<N>"``) so callers can check membership
    without expanding placeholders.
    """
    if any(defn.id_template == artifact_id for defn in REGISTRY):
        return True
    return any(rx.match(artifact_id) for _, rx in _REGISTRY_REGEX)


def kind_of(artifact_id: str) -> ArtifactKind | None:
    """Return the ArtifactKind for ``artifact_id``, or None if unknown."""
    for defn, rx in _REGISTRY_REGEX:
        if rx.match(artifact_id):
            return defn.kind
    return None
