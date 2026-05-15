from __future__ import annotations

from enum import StrEnum


class Status(StrEnum):
    NEGOTIATING = "NEGOTIATING"
    AGREED = "AGREED"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    BRIEF_OK = "BRIEF_OK"
    BRIEF_NEEDS_INPUT = "BRIEF_NEEDS_INPUT"


class ProtocolParseError(RuntimeError):
    def __init__(self, agent: str, errors: list[str]):
        self.agent = agent
        self.errors = errors
        super().__init__(f"Malformed turn from {agent}: {'; '.join(errors)}")
