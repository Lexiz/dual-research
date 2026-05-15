from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dual_research.persistence.metrics import Metrics
from dual_research.persistence.state import (
    SessionState,
    load_state,
    save_state,
    write_atomic,
)
from dual_research.persistence.transcript import Transcript


@dataclass
class SessionDirectory:
    """Filesystem layout for one orchestrator run.

    All paths are absolute. Subdirectories for phase artifacts are created
    on demand by the orchestrator phases.
    """
    root: Path

    @property
    def brief_path(self) -> Path:
        return self.root / "brief.md"

    @property
    def state_path(self) -> Path:
        return self.root / "state.json"

    @property
    def transcript_path(self) -> Path:
        return self.root / "transcript.jsonl"

    @property
    def metrics_path(self) -> Path:
        return self.root / "metrics.json"

    def phase_dir(self, phase: str) -> Path:
        d = self.root / phase
        d.mkdir(parents=True, exist_ok=True)
        return d

    def ensure(self) -> "SessionDirectory":
        self.root.mkdir(parents=True, exist_ok=True)
        return self

    def write_brief(self, content: str) -> None:
        write_atomic(self.brief_path, content)

    def load_state(self) -> SessionState:
        return load_state(self.state_path)

    def save_state(self, state: SessionState) -> None:
        save_state(self.state_path, state)

    def open_transcript(self) -> Transcript:
        return Transcript(self.transcript_path)


@dataclass
class SessionContext:
    """Bundle of the moving parts a phase needs."""
    session: SessionDirectory
    state: SessionState
    transcript: Transcript
    metrics: Metrics
