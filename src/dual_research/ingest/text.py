from __future__ import annotations

from pathlib import Path


def prompt_to_brief(text: str) -> str:
    body = text.strip()
    if not body:
        raise ValueError("--prompt is empty")
    return body + "\n"


def markdown_to_brief(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"--brief path does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"--brief file is empty: {path}")
    return text if text.endswith("\n") else text + "\n"
