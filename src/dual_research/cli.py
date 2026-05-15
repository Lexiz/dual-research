from __future__ import annotations

import argparse
import asyncio
import re
import sys
from datetime import datetime, timezone
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
from dual_research.ingest import BriefResult, IngestError, build_brief
from dual_research.ingest.notion import NotionError


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
    src.add_argument(
        "--resume",
        metavar="SESSION_DIR",
        help="Resume an existing session by path. Skips already-completed phases. "
             "Reads the brief from the session directory.",
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
        "--notion-max-depth",
        type=int,
        default=5,
        metavar="N",
        help="Maximum child-page recursion depth for --notion ingest (default: 5).",
    )
    p.add_argument(
        "--notion-max-pages",
        type=int,
        default=100,
        metavar="N",
        help="Maximum total pages fetched for --notion ingest (default: 100).",
    )
    p.add_argument(
        "--ingest-only",
        action="store_true",
        help="Build the brief and exit. Useful for verifying input ingest "
             "before paying for a full research run.",
    )
    p.add_argument(
        "--extend-caps",
        type=int,
        default=0,
        metavar="N",
        help="When resuming, add N to BOTH soft and hard caps. Useful when the "
             "previous run hit hard cap and you want to give it more rounds.",
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


def _run_id(slug: str) -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + slug


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.hard_cap < args.soft_cap:
        parser.error(f"--hard-cap ({args.hard_cap}) must be >= --soft-cap ({args.soft_cap})")

    if args.brief and not Path(args.brief).expanduser().exists():
        parser.error(f"--brief path does not exist: {args.brief}")

    if args.resume:
        return _run_resume(args, parser)

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
    run_id = _run_id(slug)
    session_dir = paths.runs_dir / run_id

    _print_launch_summary(
        args=args, tier=tier, paths=paths, slug=slug, run_id=run_id, creds=creds
    )

    try:
        brief = asyncio.run(_ingest(args, creds))
    except (IngestError, NotionError, ValueError, FileNotFoundError) as e:
        print(f"\n[ingest error] {e}", file=sys.stderr)
        return 2

    session_dir.mkdir(parents=True, exist_ok=True)
    brief_path = session_dir / "brief.md"
    brief_path.write_text(brief.content, encoding="utf-8")

    _print_brief_report(brief=brief, brief_path=brief_path)

    if args.ingest_only:
        print()
        print("[--ingest-only set — done. Brief is ready for the orchestrator.]")
        return 0

    return _run_orchestrator(
        args=args,
        creds=creds,
        tier=tier,
        slug=slug,
        session_dir=session_dir,
        soft_cap=args.soft_cap,
        hard_cap=args.hard_cap,
    )


def _run_orchestrator(
    *,
    args: argparse.Namespace,
    creds: Credentials,
    tier: ModelTier,
    slug: str,
    session_dir: Path,
    soft_cap: int,
    hard_cap: int,
) -> int:
    from dual_research.orchestrator import run_session

    result = asyncio.run(
        run_session(
            session_root=session_dir,
            slug=slug,
            creds=creds,
            tier=tier,
            soft_cap=soft_cap,
            hard_cap=hard_cap,
            out_path=Path(args.out).expanduser().resolve() if args.out else None,
        )
    )

    print(
        f"\n[run] phase reached: {result.phase_reached}  "
        f"exit code: {result.exit_code}  "
        f"total cost: ${result.total_cost_usd:.4f}  "
        f"duration: {result.duration_ms / 1000:.1f}s",
        flush=True,
    )
    print(f"[run] session dir: {session_dir}", flush=True)
    if result.final_path:
        print(f"[run] final document: {result.final_path}", flush=True)
        if args.out:
            print(f"[run] also copied to: {args.out}", flush=True)
    return result.exit_code


def _run_resume(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    session_dir = Path(args.resume).expanduser().resolve()
    if not session_dir.is_dir():
        parser.error(f"--resume path is not a directory: {session_dir}")
    state_path = session_dir / "state.json"
    brief_path = session_dir / "brief.md"
    if not state_path.exists():
        parser.error(f"no state.json in {session_dir} — cannot resume")
    if not brief_path.exists():
        parser.error(f"no brief.md in {session_dir} — cannot resume")

    try:
        creds = load_credentials(require_notion=False)
    except MissingCredentialError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    tier: ModelTier = TIERS[args.models]
    soft_cap = args.soft_cap + args.extend_caps
    hard_cap = args.hard_cap + args.extend_caps

    from dual_research.persistence.state import load_state

    state = load_state(state_path)
    slug = session_dir.name.split("-", 2)[-1] if "-" in session_dir.name else session_dir.name

    print(f"[resume] session: {session_dir}")
    print(f"[resume] state.phase = {state.phase}  drafter = {state.drafter}  "
          f"draft_round = {state.draft_round}")
    print(f"[resume] caps: soft={soft_cap}  hard={hard_cap}"
          f"  (extended by {args.extend_caps})")
    print(f"[resume] model tier: {tier.name}")

    return _run_orchestrator(
        args=args,
        creds=creds,
        tier=tier,
        slug=slug,
        session_dir=session_dir,
        soft_cap=soft_cap,
        hard_cap=hard_cap,
    )


async def _ingest(args: argparse.Namespace, creds: Credentials) -> BriefResult:
    from dual_research.ingest.notion import IngestLimits

    limits = IngestLimits(
        max_depth=args.notion_max_depth,
        max_pages=args.notion_max_pages,
    )
    return await build_brief(args, notion_token=creds.notion_token, limits=limits)


def _print_launch_summary(
    *,
    args: argparse.Namespace,
    tier: ModelTier,
    paths: Paths,
    slug: str,
    run_id: str,
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

    print("dual-research — launch summary")
    print(f"  source       : {source}")
    print(f"  run id       : {run_id}")
    print(f"  model tier   : {tier.name}")
    print(f"     claude    : {tier.claude.model_id}  ({tier.claude.context_window:,} ctx)")
    print(f"     openai    : {tier.openai.model_id}  ({tier.openai.context_window:,} ctx)")
    print(f"  soft cap     : {args.soft_cap}")
    print(f"  hard cap     : {args.hard_cap}")
    print(f"  session dir  : {paths.runs_dir / run_id}")
    print(f"  credentials  :")
    print(f"     anthropic : {_masked(creds.anthropic_api_key)}")
    print(f"     openai    : {_masked(creds.openai_api_key)}")
    print(f"     notion    : {_masked(creds.notion_token)}")


def _print_brief_report(*, brief: BriefResult, brief_path: Path) -> None:
    print()
    print("brief ingested")
    print(f"  kind         : {brief.source_kind}")
    print(f"  source       : {brief.source_ref}")
    print(f"  size         : {brief.char_count:,} chars  ·  {brief.line_count:,} lines")
    if brief.notion is not None:
        n = brief.notion
        print(f"  notion       : {n.pages_fetched} page(s) fetched"
              f"  ·  max depth {n.max_depth_reached}"
              f"  ·  {len(n.pages_failed)} failed"
              f"  ·  truncated={n.truncated}")
        if n.pages_failed:
            print("  failed pages :")
            for pid, msg in n.pages_failed[:5]:
                print(f"     - {pid}: {msg}")
            if len(n.pages_failed) > 5:
                print(f"     ...and {len(n.pages_failed) - 5} more")
    print(f"  written to   : {brief_path}")

    preview_lines = brief.content.splitlines()[:20]
    print()
    print("  --- first 20 lines of brief ---")
    for line in preview_lines:
        print(f"  | {line}")
    print("  --- end preview ---")


if __name__ == "__main__":
    sys.exit(main())
