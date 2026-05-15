from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from dual_research import __version__
from dual_research.config import (
    DEFAULT_HARD_CAP,
    DEFAULT_SOFT_CAP,
    Credentials,
    MissingCredentialError,
    ModelTier,
    Paths,
    TIERS,
    load_credentials,
    resolve_paths,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dual-research",
        description=(
            "Run two AI agents (Claude + GPT) through a structured convergence "
            "protocol to produce a single converged research document. "
            "Fully autonomous — no human-in-loop."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exactly one input source is required: --prompt, --brief, or --notion.\n"
            "\n"
            "Examples:\n"
            "  dual-research --prompt 'Research the regulatory landscape for X.'\n"
            "  dual-research --brief ./my-brief.md --out ./final.md\n"
            "  dual-research --notion https://www.notion.so/Workspace/Page-abc123 --models test\n"
        ),
    )

    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt", metavar="TEXT", help="Inline brief text.")
    src.add_argument("--brief", metavar="PATH", help="Path to a markdown brief file.")
    src.add_argument(
        "--notion",
        metavar="URL",
        help="Notion page URL — child pages are recursively pulled into the brief.",
    )

    p.add_argument(
        "--out",
        metavar="PATH",
        help="Output path for the converged final document. "
             "Default: <runs-dir>/<run-id>/final.md.",
    )
    p.add_argument(
        "--name",
        metavar="SLUG",
        help="Human-readable run slug. Default: derived from the input.",
    )
    p.add_argument(
        "--models",
        choices=sorted(TIERS.keys()),
        default="prod",
        help="Model tier (default: prod). prod = Sonnet 4.6 1M + GPT-5.5; "
             "test = Haiku 4.5 + GPT-5-mini.",
    )
    p.add_argument(
        "--soft-cap",
        type=int,
        default=DEFAULT_SOFT_CAP,
        metavar="N",
        help=f"Soft round cap per negotiation phase (default: {DEFAULT_SOFT_CAP}). "
             "Soft cap warns but does not stop the run.",
    )
    p.add_argument(
        "--hard-cap",
        type=int,
        default=DEFAULT_HARD_CAP,
        metavar="N",
        help=f"Hard round cap per negotiation phase (default: {DEFAULT_HARD_CAP}). "
             "Hard cap force-stops with a deadlock-appendix final.",
    )
    p.add_argument(
        "--runs-dir",
        metavar="PATH",
        help="Where to write run artifacts. Default: <project>/runs/.",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"dual-research {__version__}",
    )
    return p


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _derive_slug(args: argparse.Namespace) -> str:
    if args.name:
        return _slugify(args.name)
    if args.brief:
        return _slugify(Path(args.brief).stem)
    if args.notion:
        return _slugify(args.notion.rsplit("/", 1)[-1].rsplit("-", 1)[0]) or "notion"
    return _slugify((args.prompt or "")[:60]) or "prompt"


def _slugify(text: str) -> str:
    s = _SLUG_RE.sub("-", text.lower()).strip("-")
    return s[:60] if s else ""


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.hard_cap < args.soft_cap:
        parser.error(f"--hard-cap ({args.hard_cap}) must be >= --soft-cap ({args.soft_cap})")

    if args.brief and not Path(args.brief).expanduser().exists():
        parser.error(f"--brief path does not exist: {args.brief}")

    require_notion = args.notion is not None
    try:
        creds = load_credentials(require_notion=require_notion)
    except MissingCredentialError as e:
        print(f"error: {e}", file=sys.stderr)
        print(
            "Set the missing variable(s) in ~/.zshrc and start a new shell, or use a session-local export.",
            file=sys.stderr,
        )
        return 1

    paths = resolve_paths(args.runs_dir)
    tier: ModelTier = TIERS[args.models]
    slug = _derive_slug(args)

    _print_launch_summary(args=args, tier=tier, paths=paths, slug=slug, creds=creds)

    print()
    print("[step 1 only — CLI shell. Orchestrator not wired yet; nothing was run.]")
    return 0


def _print_launch_summary(
    *,
    args: argparse.Namespace,
    tier: ModelTier,
    paths: Paths,
    slug: str,
    creds: Credentials,
) -> None:
    if args.prompt is not None:
        source = f"inline prompt ({len(args.prompt)} chars)"
    elif args.brief:
        source = f"markdown file: {args.brief}"
    else:
        source = f"notion url: {args.notion}"

    def _masked(value: str | None) -> str:
        if not value:
            return "(not set)"
        return f"{value[:4]}...{value[-4:]} ({len(value)} chars)"

    out_path = args.out or f"{paths.runs_dir / '<run-id>' / 'final.md'}"
    print("dual-research — launch summary")
    print(f"  source       : {source}")
    print(f"  slug         : {slug}")
    print(f"  model tier   : {tier.name}")
    print(f"     claude    : {tier.claude.model_id}  ({tier.claude.context_window:,} ctx)")
    print(f"     openai    : {tier.openai.model_id}  ({tier.openai.context_window:,} ctx)")
    print(f"  soft cap     : {args.soft_cap}")
    print(f"  hard cap     : {args.hard_cap}")
    print(f"  runs dir     : {paths.runs_dir}")
    print(f"  out path     : {out_path}")
    print(f"  credentials  :")
    print(f"     anthropic : {_masked(creds.anthropic_api_key)}")
    print(f"     openai    : {_masked(creds.openai_api_key)}")
    print(f"     notion    : {_masked(creds.notion_token)}")


if __name__ == "__main__":
    sys.exit(main())
