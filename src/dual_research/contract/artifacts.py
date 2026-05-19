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
