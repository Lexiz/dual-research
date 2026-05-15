from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelSpec:
    provider: str           # "anthropic" | "openai"
    model_id: str           # exact API model identifier
    context_window: int     # tokens
    extra_headers: dict[str, str] | None = None


@dataclass(frozen=True)
class ModelTier:
    name: str
    claude: ModelSpec
    openai: ModelSpec


PROD_TIER = ModelTier(
    name="prod",
    claude=ModelSpec(
        provider="anthropic",
        model_id="claude-sonnet-4-6",
        context_window=1_000_000,
        extra_headers={"anthropic-beta": "context-1m-2025-08-07"},
    ),
    openai=ModelSpec(
        provider="openai",
        model_id="gpt-5.5",
        context_window=1_000_000,
    ),
)

TEST_TIER = ModelTier(
    name="test",
    claude=ModelSpec(
        provider="anthropic",
        model_id="claude-haiku-4-5",
        context_window=200_000,
    ),
    openai=ModelSpec(
        provider="openai",
        model_id="gpt-5-mini",
        context_window=400_000,
    ),
)

TIERS: dict[str, ModelTier] = {"prod": PROD_TIER, "test": TEST_TIER}


DEFAULT_SOFT_CAP = 6
DEFAULT_HARD_CAP = 12


@dataclass(frozen=True)
class Paths:
    project_root: Path
    runs_dir: Path


def resolve_paths(runs_dir_override: str | None = None) -> Paths:
    project_root = Path(__file__).resolve().parents[2]
    runs_dir = Path(runs_dir_override).resolve() if runs_dir_override else project_root / "runs"
    return Paths(project_root=project_root, runs_dir=runs_dir)


@dataclass(frozen=True)
class Credentials:
    anthropic_api_key: str
    openai_api_key: str
    notion_token: str | None


class MissingCredentialError(RuntimeError):
    pass


def load_credentials(*, require_notion: bool) -> Credentials:
    anthropic = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    openai = os.environ.get("OPENAI_API_KEY", "").strip()
    notion = os.environ.get("NOTION_TOKEN", "").strip()

    missing: list[str] = []
    if not anthropic:
        missing.append("ANTHROPIC_API_KEY")
    if not openai:
        missing.append("OPENAI_API_KEY")
    if require_notion and not notion:
        missing.append("NOTION_TOKEN")

    if missing:
        raise MissingCredentialError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )

    return Credentials(
        anthropic_api_key=anthropic,
        openai_api_key=openai,
        notion_token=notion or None,
    )
