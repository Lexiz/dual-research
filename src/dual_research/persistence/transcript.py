from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Transcript:
    """Append-only JSONL event log. One JSON object per line. Each record gets
    an ISO-8601 UTC timestamp added under the `ts` key."""

    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def write(self, event: str, **fields: Any) -> None:
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
        }
        record.update(fields)
        line = json.dumps(record, ensure_ascii=False, default=_default)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def read_events(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
        return out


def _default(obj: Any) -> Any:
    # Serialise dataclasses, paths, enums by string conversion as a fallback
    from dataclasses import asdict, is_dataclass
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "value"):
        return obj.value
    return str(obj)
