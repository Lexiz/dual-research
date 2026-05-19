from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SessionState:
    phase: str = "phase0"
    drafter: str | None = None
    agreed_plan: str | None = None
    final_surfaced_disagreements: list[dict[str, Any]] = field(default_factory=list)
    draft_round: int = 1
    final_emitted_to: str | None = None
    # ─── Spec 0114 — Deep Research state ──────────────────────────────
    # ``agreed_interpretation`` is the AGREED_INTERPRETATION block body
    # captured at phase 0 convergence; consumed by phase 1's prompt.
    # ``carry_forward_phase{0,2,4}`` are the terminal-not-resolved
    # items as captured at each phase boundary, used by phase 3's
    # drafting prompt and the finalize-step appendix.
    # ``closeout_budgets`` records per-phase, per-agent remaining
    # closeout budget across the run (resumed via load_state).
    agreed_interpretation: str | None = None
    carry_forward_phase0: list[dict[str, Any]] = field(default_factory=list)
    carry_forward_phase2: list[dict[str, Any]] = field(default_factory=list)
    carry_forward_phase4: list[dict[str, Any]] = field(default_factory=list)
    closeout_budgets: dict[str, dict[str, int]] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "SessionState":
        data = json.loads(text)
        return cls(
            phase=data.get("phase", "phase0"),
            drafter=data.get("drafter"),
            agreed_plan=data.get("agreed_plan"),
            final_surfaced_disagreements=data.get("final_surfaced_disagreements", []),
            draft_round=int(data.get("draft_round", 1)),
            final_emitted_to=data.get("final_emitted_to"),
            agreed_interpretation=data.get("agreed_interpretation"),
            carry_forward_phase0=data.get("carry_forward_phase0", []),
            carry_forward_phase2=data.get("carry_forward_phase2", []),
            carry_forward_phase4=data.get("carry_forward_phase4", []),
            closeout_budgets=data.get("closeout_budgets", {}),
        )


def write_atomic(path: Path, content: str) -> None:
    """Write content to path atomically: tempfile in same dir → fsync → rename.

    A crash between write and rename leaves the original file intact, so the
    state file is never half-written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def load_state(state_path: Path) -> SessionState:
    if not state_path.exists():
        return SessionState()
    return SessionState.from_json(state_path.read_text(encoding="utf-8"))


def save_state(state_path: Path, state: SessionState) -> None:
    write_atomic(state_path, state.to_json())
