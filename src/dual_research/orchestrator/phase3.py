from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Phase3Outcome:
    drafter: str
    draft_chars: int
    draft_path: str


def current_draft_path(session, draft_round: int) -> Path:
    """Resolve which file holds the current draft.

    Phase 3 writes draft-v1.md to phase3/. Phase 4 writes revisions to phase4/.
    """
    if draft_round == 1:
        return session.phase_dir("phase3") / "draft-v1.md"
    return session.phase_dir("phase4") / f"draft-v{draft_round}.md"
