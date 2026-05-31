from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Coroutine

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
from dual_research.ingest import (
    AttachmentBundle,
    BriefResult,
    IngestError,
    build_brief,
    materialise_local_markdown_attachments,
)
from dual_research.ingest.attachments import kind_counts
from dual_research.ingest.notion import NotionError


async def _run_with_signal_handlers(coro: Coroutine) -> object:
    # Spec 0224 — install asyncio cancel handlers for SIGTERM, SIGHUP, and
    # SIGINT so raw signal kills route into Python's exception machinery
    # as `asyncio.CancelledError`, which the spec 0222 `except BaseException`
    # at orchestrator/run.py already tombstones. Without this, SIGTERM/SIGHUP
    # terminate the process before any except or finally clause runs and
    # the run dies silently with `metrics.ended_at == null`.
    loop = asyncio.get_running_loop()
    main_task = asyncio.current_task()
    installed: list[int] = []
    for name in ("SIGTERM", "SIGHUP", "SIGINT"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            loop.add_signal_handler(sig, main_task.cancel)
            installed.append(sig)
        except NotImplementedError:
            # POSIX-only API; orchestrator is mac-local per spec 0224 §7.
            pass
    try:
        return await coro
    finally:
        for sig in installed:
            try:
                loop.remove_signal_handler(sig)
            except (NotImplementedError, ValueError):
                pass


# Spec 0243 — operational guard: refuse to fire an E2E run inside Claude
# Code. Four consecutive Claude-Code-hosted runs died silently in phase 2-4
# (no Python exception, no signal, no jetsam log); the first plain-Terminal.app
# run completed cleanly. Root cause: Claude Code's background-task manager
# reaps long-running children at parent-session lifecycle events. The CLI
# refuses-by-default; DUAL_RESEARCH_ALLOW_CLAUDE_P=1 is the documented escape.
def _running_inside_claude_code() -> bool:
    if os.environ.get("CLAUDECODE"):
        return True
    return any(k.startswith("CLAUDE_CODE_") for k in os.environ)


_CLAUDE_CODE_REFUSAL_MESSAGE = (
    "dual-research: refusing to run inside Claude Code.\n"
    "\n"
    "Claude Code's background-task manager terminates long-running\n"
    "children at parent-session lifecycle events (idle timeout,\n"
    "suspend, session close), reaping the dual-research process\n"
    "mid-run with no Python exception, no signal, no traceable\n"
    "termination. Four consecutive runs died this way; the first\n"
    "plain-Terminal.app run completed cleanly. See spec 0243 +\n"
    "cowork/briefs/2026-05-28-h4-plain-terminal-next.md for full\n"
    "evidence.\n"
    "\n"
    "Run instead from a plain Terminal.app session:\n"
    "\n"
    "  cd /Users/alexlisitzky/ClaudeCode/dual-research-workspace/dual-research && \\\n"
    "  eval \"$(grep -hE '^export (ANTHROPIC_API_KEY|OPENAI_API_KEY|SUPABASE_(URL|ANON_KEY|SERVICE_ROLE_KEY))=' ~/.zshenv ~/.zshrc 2>/dev/null)\" && \\\n"
    "  caffeinate -i uv run dual-research \\\n"
    "    --notion '<url>' --models prod --push-while-running \\\n"
    "    --name <slug> 2>&1 | tee /tmp/dr-run-<slug>.log\n"
    "\n"
    "Override (NOT RECOMMENDED — kills will recur silently):\n"
    "  DUAL_RESEARCH_ALLOW_CLAUDE_P=1 dual-research ...\n"
)


def _maybe_refuse_claude_code_host() -> None:
    if not _running_inside_claude_code():
        return
    if os.environ.get("DUAL_RESEARCH_ALLOW_CLAUDE_P") == "1":
        return
    sys.stderr.write(_CLAUDE_CODE_REFUSAL_MESSAGE)
    sys.exit(2)


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
            "At least one input source is required: --prompt, --brief, and/or --notion (repeatable).\n"
            "When multiple input sources are passed, they're concatenated in CLI order with a\n"
            "`# Source: ...` divider between adjacent sources.\n"
            "\n"
            "Examples:\n"
            "  dual-research --prompt 'Research the regulatory landscape for X.'\n"
            "  dual-research --brief ./my-brief.md --out ./final.md\n"
            "  dual-research --notion https://www.notion.so/Workspace/Page-abc123 --models test\n"
            "  dual-research --notion URL_A --notion URL_B --prompt 'compare and contrast'\n"
            "\n"
            "ENVIRONMENT VARIABLES:\n"
            "  DUAL_RESEARCH_ALLOW_CLAUDE_P=1   Allow `dual-research` to fire an E2E run inside\n"
            "                                   a Claude Code surface despite the spec-0243 guard.\n"
            "                                   See CLAUDE.md \"Operational\" for intended use.\n"
        ),
    )

    # Input sources — can be freely combined. Spec 0036: `--notion` is
    # repeatable; `--brief` and `--prompt` stay singleton but combine with
    # each other and with `--notion`.
    p.add_argument("--prompt", metavar="TEXT", help="Inline brief text.")
    p.add_argument("--brief", metavar="PATH", help="Path to a markdown brief file.")
    p.add_argument(
        "--notion",
        action="append",
        default=[],
        metavar="URL_OR_ID",
        help="Notion page URL or ID — child pages are recursively pulled. "
             "Repeatable; each occurrence appends one root. Concatenated in CLI order.",
    )
    # Operational modes — exclusive with each other AND with --prompt/--brief/--notion.
    op = p.add_mutually_exclusive_group(required=False)
    op.add_argument(
        "--resume",
        metavar="SESSION_DIR",
        help="Resume an existing session by path. Skips already-completed phases. "
             "Reads the brief from the session directory.",
    )
    op.add_argument(
        "--push",
        metavar="SESSION_DIR",
        help="Push a completed session-dir to Supabase. Requires SUPABASE_URL, "
             "SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY in the environment. "
             "Idempotent — re-pushing replaces the run's rows.",
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
        "--attach",
        metavar="VALUE",
        action="append",
        default=[],
        help="Attach an image, PDF, file, or URL alongside the brief. "
             "Repeatable. Local paths are copied into the session-dir's "
             "attachments/ directory; URLs are recorded as link entries.",
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
        "--push-while-running",
        action="store_true",
        help="Push the session-dir to Supabase every 30s during the run so the "
             "hosted UI streams updates as the orchestrator progresses (spec 0032). "
             "Requires SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY "
             "in the environment. A final synchronous push runs on exit so the "
             "hosted UI always sees the completed state.",
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
    # Spec 0036: --notion is now a list. Use the first root for slug derivation.
    notion_list = getattr(args, "notion", None) or []
    if notion_list:
        first = notion_list[0]
        return _slugify(first.rsplit("/", 1)[-1].rsplit("-", 1)[0]) or "notion"
    return _slugify((args.prompt or "")[:60]) or "prompt"


def _slugify(text: str) -> str:
    s = _SLUG_RE.sub("-", text.lower()).strip("-")
    return s[:60] if s else ""


def _apply_title(content: str, name: str | None) -> str:
    """Override the first H1 of a brief with ``name`` so ``--name`` doubles as
    the run display title (spec 0260). Source-agnostic — applied at the single
    ``brief.md`` write point, so it covers --notion / --prompt / --brief alike.
    When ``name`` is falsy, returns ``content`` verbatim (existing behavior).
    """
    if not name:
        return content
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):  # replace first H1 (e.g. "# Research brief")
            lines[i] = f"# {name}"
            return "\n".join(lines)
    return f"# {name}\n\n{content}"  # no H1 present → prepend one


def _run_id(slug: str) -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + slug


def main(argv: list[str] | None = None) -> int:
    # `dual-research serve [...]` shortcut: hand off to the UI server without
    # going through the orchestrator's argparse (which would reject `serve`).
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] == "serve":
        from dual_research.ui.server import main as serve_main
        return serve_main(raw[1:])

    # Spec 0039: `dual-research recompute-costs [--run RUN_ID | --all]
    # [--push] [--runs-dir PATH]` reprices existing runs from their
    # transcripts under the current pricing rules (1h cache writes priced
    # at the 1h tier, search fees folded into the headline).
    if raw and raw[0] == "recompute-costs":
        return _run_recompute(raw[1:])

    # Spec 0048: `dual-research reconcile-costs [--day YYYY-MM-DD | --from/--to
    # | --all | --run RUN_ID | --since-yesterday]` compares local cost
    # accounting against provider invoices (Anthropic + OpenAI admin APIs)
    # and writes a per-day snapshot to reconcile/<date>.json. Each provider's
    # admin key is independently optional (env vars ANTHROPIC_ADMIN_KEY +
    # OPENAI_ADMIN_KEY); missing key → that side reported as "skipped".
    if raw and raw[0] == "reconcile-costs":
        return _run_reconcile(raw[1:])

    # Spec 0252: `dual-research backfill-critique [--run RUN_ID | --all]
    # [--push] [--runs-dir PATH] [--dry-run]` recomputes critique_by_agent
    # for existing runs that predate spec 0248's write-time tally (their
    # metrics.json carries critique_by_agent: null, so the All Runs band
    # renders zero counters). Mirrors recompute-costs exactly; --push
    # upserts the Supabase `metrics` JSONB so the *deployed* cards repair.
    # Out-of-band by design — the /api/runs list path never replays
    # transcripts (spec 0248 §1/§7). Read-only w.r.t. the Claude Code host
    # guard (no LLM call), like recompute-costs / reconcile-costs.
    if raw and raw[0] == "backfill-critique":
        return _run_backfill_critique(raw[1:])

    # Spec 0115: `dual-research validate-run <session-dir>` audits a
    # finished Deep Research run against the contract.
    if raw and raw[0] == "validate-run":
        from dual_research.validate_cli import main as _validate_main
        return _validate_main(raw[1:])

    # Spec 0225: `dual-research verify <run-dir> ...` runs the lifecycle-
    # trace verifier (the 22 invariants of the 0114-unified contract in
    # executable form) against each supplied run.
    if raw and raw[0] == "verify":
        from dual_research.verifier_cli import main as _verify_main
        return _verify_main(raw[1:])

    parser = _build_parser()
    args = parser.parse_args(argv)

    # Spec 0243 — refuse to fire an E2E run inside Claude Code. --push is
    # a read-only Supabase upload (no LLM call) and is exempt; all other
    # paths (default --prompt/--brief/--notion firing and --resume) go
    # through this guard before any further work (ingest, cred load,
    # session-dir creation). DUAL_RESEARCH_ALLOW_CLAUDE_P=1 is the escape.
    if not args.push:
        _maybe_refuse_claude_code_host()

    if args.hard_cap < args.soft_cap:
        parser.error(f"--hard-cap ({args.hard_cap}) must be >= --soft-cap ({args.soft_cap})")

    if args.brief and not Path(args.brief).expanduser().exists():
        parser.error(f"--brief path does not exist: {args.brief}")

    # Spec 0036: --resume / --push are mutually exclusive with input sources.
    input_sources_set = bool(args.prompt) or bool(args.brief) or bool(args.notion)
    if args.resume:
        if input_sources_set:
            parser.error("--resume cannot be combined with --prompt / --brief / --notion")
        return _run_resume(args, parser)

    if args.push:
        if input_sources_set:
            parser.error("--push cannot be combined with --prompt / --brief / --notion")
        return _run_push(args, parser)

    # Otherwise require at least one input source.
    if not input_sources_set:
        parser.error(
            "at least one of --prompt, --brief, --notion, --resume, or --push is required"
        )

    require_notion = bool(args.notion)
    try:
        creds = load_credentials(require_notion=require_notion)
    except MissingCredentialError as e:
        print(f"error: {e}", file=sys.stderr)
        print(
            "Set the missing variable(s) in ~/.zshenv and start a new shell, or use a session-local export.",
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
        brief = asyncio.run(_run_with_signal_handlers(_ingest(args, creds)))
    except (IngestError, NotionError, ValueError, FileNotFoundError) as e:
        print(f"\n[ingest error] {e}", file=sys.stderr)
        return 2

    session_dir.mkdir(parents=True, exist_ok=True)
    brief_path = session_dir / "brief.md"
    brief_path.write_text(_apply_title(brief.content, args.name), encoding="utf-8")

    # Materialise any local-file attachments into <session>/attachments/
    # and write the metadata index. URL-only entries pass through
    # unchanged. (Spec 0025.)
    attachments_dir = session_dir / "attachments"
    materialised = materialise_local_markdown_attachments(
        brief.attachments, dest_dir=attachments_dir
    )
    brief.attachments = materialised
    attachments_path = session_dir / "attachments.json"
    attachments_path.write_text(
        json.dumps(AttachmentBundle(materialised).to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )

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

    # Spec 0032 — --push-while-running enables periodic supabase pushes
    # during the run. Load creds eagerly so we fail fast with a clear
    # error if Supabase env is missing.
    supabase_creds = None
    if getattr(args, "push_while_running", False):
        from dual_research.config import load_supabase_credentials
        try:
            supabase_creds = load_supabase_credentials()
        except MissingCredentialError as e:
            print(f"error: --push-while-running set, but {e}", file=sys.stderr)
            print(
                "Set SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY "
                "in ~/.zshenv and start a new shell, or use a session-local export.",
                file=sys.stderr,
            )
            return 1

    result = asyncio.run(
        _run_with_signal_handlers(
            run_session(
                session_root=session_dir,
                slug=slug,
                creds=creds,
                tier=tier,
                soft_cap=soft_cap,
                hard_cap=hard_cap,
                out_path=Path(args.out).expanduser().resolve() if args.out else None,
                push_while_running=supabase_creds,
            )
        )
    )

    # Spec 0039: `total_cost_usd` is the FULL invoice (tokens + web
    # search). When search fees fired, surface the breakdown so a
    # reviewer can see "of which web search" without opening the UI.
    cost_line = f"total cost: ${result.total_cost_usd:.4f}"
    if getattr(result, "total_search_cost_usd", 0.0) > 0:
        token_cost = max(0.0, result.total_cost_usd - result.total_search_cost_usd)
        cost_line += (
            f"  (tokens ${token_cost:.4f} · "
            f"web search ${result.total_search_cost_usd:.4f})"
        )
    print(
        f"\n[run] phase reached: {result.phase_reached}  "
        f"exit code: {result.exit_code}  "
        f"{cost_line}  "
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


def _run_push(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    from dual_research.config import load_supabase_credentials
    from dual_research.persistence.remote import RemoteSession

    session_dir = Path(args.push).expanduser().resolve()
    if not session_dir.is_dir():
        parser.error(f"--push path is not a directory: {session_dir}")

    try:
        sb = load_supabase_credentials()
    except MissingCredentialError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    try:
        remote = RemoteSession.from_credentials(sb.url, sb.service_role_key)
        summary = remote.push_session_dir(session_dir)
    except FileNotFoundError as e:
        print(f"[push error] {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"[push error] {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print(
        f"[push] run={summary.run_id}  "
        f"events={summary.events_upserted}  "
        f"files={summary.files_upserted}  "
        f"duration={summary.duration_ms / 1000:.1f}s",
        flush=True,
    )
    return 0


def _run_recompute(argv: list[str]) -> int:
    """Spec 0039 — repricing backfill for existing runs.

    Walks each run's transcript, recomputes per-turn cost under the
    current pricing rules, and rewrites ``metrics.json``. Optionally
    re-pushes the updated session-dir to Supabase so the hosted UI
    catches up immediately.
    """
    from dual_research.audit.recompute import recompute_all, recompute_run

    sub = argparse.ArgumentParser(
        prog="dual-research recompute-costs",
        description=(
            "Reprice existing runs from their transcripts under the "
            "current pricing rules (spec 0039)."
        ),
    )
    g = sub.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", metavar="RUN_ID",
                   help="Recompute a single run by id (directory name under --runs-dir).")
    g.add_argument("--all", action="store_true",
                   help="Recompute every run under --runs-dir.")
    sub.add_argument("--runs-dir", default=None,
                     help="Override the default runs directory (otherwise resolved from config).")
    sub.add_argument("--push", action="store_true",
                     help="After rewriting metrics.json, re-push the session to Supabase.")
    sub.add_argument("--dry-run", action="store_true",
                     help="Report the diff without writing metrics.json.")
    args = sub.parse_args(argv)

    paths = resolve_paths(args.runs_dir)
    runs_dir = paths.runs_dir

    if args.run:
        session_dir = runs_dir / args.run
        if not session_dir.is_dir():
            print(f"error: run not found: {session_dir}", file=sys.stderr)
            return 2
        reports = [recompute_run(session_dir, write=not args.dry_run)]
    else:
        reports = recompute_all(runs_dir, write=not args.dry_run)

    grand_old = sum(r.old_total for r in reports)
    grand_new = sum(r.new_total for r in reports)
    for r in reports:
        diff_marker = "✓" if abs(r.delta) < 1e-6 else "Δ"
        print(
            f"[{diff_marker}] {r.run_id}: ${r.old_total:.4f} → ${r.new_total:.4f}  "
            f"({r.delta:+.4f})"
            + ("  [backed up]" if r.backed_up else "")
            + ("  [written]" if r.metrics_written else "")
        )
        # Spec 0048: surface pricing-table transitions; quiet on no-op.
        if r.pricing_version_before != r.pricing_version_after:
            before = r.pricing_version_before or "(unknown)"
            print(f"  ↳ pricing table: {before} → {r.pricing_version_after}")
    print(
        f"--- {len(reports)} run(s) | "
        f"${grand_old:.4f} → ${grand_new:.4f} ({grand_new - grand_old:+.4f})"
    )

    if args.push and not args.dry_run:
        from dual_research.config import load_supabase_credentials
        from dual_research.persistence.remote import RemoteSession

        try:
            sb = load_supabase_credentials()
        except MissingCredentialError as e:
            print(f"--push requested but: {e}", file=sys.stderr)
            return 1
        remote = RemoteSession.from_credentials(sb.url, sb.service_role_key)
        for r in reports:
            if not r.metrics_written:
                continue
            session_dir = runs_dir / r.run_id
            try:
                summary = remote.push_session_dir(session_dir)
                print(
                    f"[pushed] {summary.run_id}  events={summary.events_upserted}  "
                    f"files={summary.files_upserted}  "
                    f"duration={summary.duration_ms / 1000:.1f}s"
                )
            except Exception as e:
                print(f"[push error] {r.run_id}: {type(e).__name__}: {e}", file=sys.stderr)

    return 0


def _run_backfill_critique(argv: list[str]) -> int:
    """Spec 0252 — backfill ``critique_by_agent`` for pre-0248 runs.

    Recomputes the per-agent Q/D/I/C tally for existing runs whose
    ``metrics.json`` predates spec 0248's write-time tally (and so carries
    ``critique_by_agent: null``, rendering the All Runs band all-zero).
    Rewrites ``metrics.json`` in place; ``--push`` additionally upserts the
    Supabase ``metrics`` JSONB so the **deployed** cards repair. Mirrors
    ``recompute-costs`` (``_run_recompute``); the ``/api/runs`` list path
    is untouched (spec 0248 §1/§7 — never replays transcripts).
    """
    from dual_research.audit.backfill_critique import backfill_all, backfill_critique_run

    sub = argparse.ArgumentParser(
        prog="dual-research backfill-critique",
        description=(
            "Recompute and persist critique_by_agent for existing runs that "
            "predate spec 0248's write-time tally (spec 0252)."
        ),
    )
    g = sub.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", metavar="RUN_ID",
                   help="Backfill a single run by id (directory name under --runs-dir).")
    g.add_argument("--all", action="store_true",
                   help="Backfill every run under --runs-dir.")
    sub.add_argument("--runs-dir", default=None,
                     help="Override the default runs directory (otherwise resolved from config).")
    sub.add_argument("--push", action="store_true",
                     help="After rewriting metrics.json, re-push the session to Supabase.")
    sub.add_argument("--dry-run", action="store_true",
                     help="Report the would-write tally without writing metrics.json.")
    args = sub.parse_args(argv)

    paths = resolve_paths(args.runs_dir)
    runs_dir = paths.runs_dir

    if args.run:
        session_dir = runs_dir / args.run
        if not session_dir.is_dir():
            print(f"error: run not found: {session_dir}", file=sys.stderr)
            return 2
        if not (session_dir / "metrics.json").exists():
            print(f"error: no metrics.json in {session_dir}", file=sys.stderr)
            return 2
        reports = [backfill_critique_run(session_dir, write=not args.dry_run)]
    else:
        reports = backfill_all(runs_dir, write=not args.dry_run)

    repaired = 0
    for r in reports:
        # A run is "repaired" when the tally went from empty → non-empty.
        marker = "Δ" if (not r.before_nonempty and r.after_nonempty) else "✓"
        if marker == "Δ":
            repaired += 1
        counts = ", ".join(
            f"{agent}: " + "/".join(
                str(r.raised_counts.get(agent, {}).get(c, 0))
                for c in ("questions", "disagreements", "issues", "comments")
            )
            for agent in sorted(r.raised_counts)
        )
        print(
            f"[{marker}] {r.run_id}: "
            f"{'empty' if not r.before_nonempty else 'present'} → "
            f"{'non-empty' if r.after_nonempty else 'empty'}  "
            f"[{counts or 'no items'}]"
            + ("  [written]" if r.metrics_written else "  [dry-run]")
        )
    print(
        f"--- {len(reports)} run(s) | {repaired} repaired (empty → non-empty)"
        + ("  [dry-run — nothing written]" if args.dry_run else "")
    )

    if args.push and not args.dry_run:
        from dual_research.config import load_supabase_credentials
        from dual_research.persistence.remote import RemoteSession

        try:
            sb = load_supabase_credentials()
        except MissingCredentialError as e:
            print(f"--push requested but: {e}", file=sys.stderr)
            return 1
        remote = RemoteSession.from_credentials(sb.url, sb.service_role_key)
        for r in reports:
            if not r.metrics_written:
                continue
            session_dir = runs_dir / r.run_id
            try:
                # Spec 0252.2 — metrics-only repair. The backfill mutates only
                # critique_by_agent inside metrics; the full push_session_dir
                # re-upload of events/files/blobs/pieces is wasted work and times
                # out (Supabase 57014) on large runs. A single-column runs.metrics
                # update is provably sufficient — no derived runs column moves.
                summary = remote.push_metrics_only(session_dir)
                print(f"[pushed] {summary.run_id}  metrics-only  ok={summary.ok}")
            except Exception as e:
                print(f"[push error] {r.run_id}: {type(e).__name__}: {e}", file=sys.stderr)

    return 0


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
    # Spec 0036: sources can combine. Describe each set source on its own line.
    parts: list[str] = []
    if args.prompt is not None:
        parts.append(f"inline prompt ({len(args.prompt)} chars)")
    if args.brief:
        parts.append(f"markdown file: {args.brief}")
    notion_list = getattr(args, "notion", None) or []
    if len(notion_list) == 1:
        parts.append(f"notion url: {notion_list[0]}")
    elif len(notion_list) > 1:
        parts.append(f"notion urls ({len(notion_list)}):")
        for i, url in enumerate(notion_list, 1):
            parts.append(f"      [{i}] {url}")
    source = parts[0] if len(parts) == 1 else "multi-source — " + "; ".join(parts)

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
    if brief.attachments:
        counts = kind_counts(brief.attachments)
        breakdown = ", ".join(
            f"{label}={counts[label]}"
            for label in ("image", "pdf", "file", "link")
            if counts.get(label)
        )
        print(
            f"  attachments  : {len(brief.attachments)} item(s)"
            f"  ·  {breakdown or '—'}"
        )

    preview_lines = brief.content.splitlines()[:20]
    print()
    print("  --- first 20 lines of brief ---")
    for line in preview_lines:
        print(f"  | {line}")
    print("  --- end preview ---")


def _run_reconcile(argv: list[str]) -> int:
    """Spec 0048: ``dual-research reconcile-costs`` — verify local cost
    accounting against provider invoices. Each provider's admin key is
    independently optional via env vars; missing key ⇒ that side
    surfaces as ``skipped`` in the report.
    """
    import datetime as _dt

    import httpx as _httpx

    from dual_research.audit.reconcile import (
        ProviderConfig,
        format_json,
        format_text,
        reconcile_day,
        write_reconcile_json,
    )

    sub = argparse.ArgumentParser(
        prog="dual-research reconcile-costs",
        description=(
            "Verify local cost accounting against provider invoices. "
            "Pulls daily aggregates from Anthropic + OpenAI admin APIs, "
            "compares to local metrics.json totals, writes "
            "reconcile/<date>.json. Each provider's admin key is "
            "independently optional (env: ANTHROPIC_ADMIN_KEY, "
            "OPENAI_ADMIN_KEY)."
        ),
    )
    mode = sub.add_mutually_exclusive_group(required=True)
    mode.add_argument("--day", metavar="YYYY-MM-DD",
                      help="Reconcile a single UTC date.")
    mode.add_argument("--from", dest="from_date", metavar="YYYY-MM-DD",
                      help="Start date (inclusive); requires --to.")
    mode.add_argument("--all", action="store_true",
                      help="Every UTC date with at least one local run.")
    mode.add_argument("--run", metavar="RUN_ID",
                      help="The UTC date containing this run's started_at.")
    mode.add_argument("--since-yesterday", action="store_true",
                      help="Yesterday + today (recommended cron entry).")

    sub.add_argument("--to", dest="to_date", metavar="YYYY-MM-DD",
                     help="End date (inclusive); used with --from.")
    sub.add_argument("--runs-dir", metavar="PATH",
                     help="Override runs/ directory (default: <project>/runs).")
    sub.add_argument("--format", choices=("text", "json"), default="text",
                     help="Report format (default: text).")
    sub.add_argument("--out", metavar="PATH",
                     help="Write report to PATH instead of stdout.")
    sub.add_argument("--tolerance", type=float, default=1.0,
                     help="Per-row delta %% above which to flag (default: 1.0).")
    sub.add_argument("--write-snapshots", dest="write_snapshots",
                     action="store_true", default=True,
                     help="Persist ReconcileReport to reconcile/<date>.json (default true).")
    sub.add_argument("--no-write-snapshots", dest="write_snapshots",
                     action="store_false",
                     help="Skip persistence; print only.")
    sub.add_argument("--push", action="store_true",
                     help="Upsert each ReconcileReport into Supabase "
                          "(reconcile_results table). Requires Supabase creds in env.")
    sub.add_argument("--source", choices=("local", "supabase"), default="local",
                     help="Where to gather run-cost data from. ``local`` "
                          "(default) walks --runs-dir on disk. ``supabase`` "
                          "queries the hosted ``runs`` table (requires "
                          "Supabase creds in env). Spec 0049.")

    args = sub.parse_args(argv)

    project_root = Path(__file__).resolve().parents[2]
    runs_dir = Path(args.runs_dir).expanduser() if args.runs_dir else project_root / "runs"
    # Spec 0048 follow-up: don't exit when runs/ is missing. The reconcile
    # path is meaningful even with zero local runs — provider-side billing
    # data still surfaces, and ``gather_local_totals`` already returns an
    # empty dict for a missing directory. Honest report > spurious exit.
    # Spec 0049: when --source supabase, runs_dir is unused; skip the warn.
    if args.source == "local" and not runs_dir.exists():
        print(
            f"warning: runs dir not found ({runs_dir}); proceeding with "
            "empty local totals — report will reflect provider-side data only",
            file=sys.stderr,
        )

    # Resolve mode → list of UTC dates.
    try:
        dates = _resolve_reconcile_dates(args, runs_dir=runs_dir)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not dates:
        print("error: no dates resolved from mode flags", file=sys.stderr)
        return 2

    config = ProviderConfig.from_env()
    client = _httpx.Client(timeout=30.0)

    # Spec 0049 — Supabase-source path. Both `--source supabase` and
    # `--push` need credentials; load once and reuse the client.
    supabase_client = None
    remote = None
    if args.source == "supabase" or args.push:
        from dual_research.config import load_supabase_credentials
        from dual_research.persistence.remote import RemoteSession
        try:
            sb = load_supabase_credentials()
        except MissingCredentialError as e:
            verb = "--source supabase" if args.source == "supabase" else "--push"
            print(f"{verb} requested but: {e}", file=sys.stderr)
            return 1
        remote = RemoteSession.from_credentials(sb.url, sb.service_role_key)
        if args.source == "supabase":
            from supabase import create_client
            supabase_client = create_client(sb.url, sb.service_role_key)

    # Spec 0049 — gather local totals once per source, over the whole date
    # range. This lets the supabase branch make a single SQL query for
    # multi-date reconciliations instead of one per date.
    if args.source == "supabase":
        from dual_research.audit.reconcile import gather_supabase_totals
        gather_start = min(dates)
        gather_end = max(dates) + _dt.timedelta(days=1)
        local_totals = gather_supabase_totals(
            supabase_client, start_date=gather_start, end_date=gather_end,
        )
    else:
        local_totals = None  # reconcile_day will gather per-date from runs_dir

    try:
        reports = []
        for date in dates:
            report = reconcile_day(
                date,
                client=client, runs_dir=runs_dir,
                config=config, tolerance_pct=args.tolerance,
                local_totals=local_totals,
            )
            if args.write_snapshots:
                write_reconcile_json(report, project_root=project_root)
            if remote is not None:
                from dataclasses import asdict
                remote.push_reconcile_report(
                    date=report.date, payload=asdict(report),
                )
            reports.append(report)
    finally:
        client.close()

    body = format_json(reports) if args.format == "json" else format_text(reports)
    if args.out:
        Path(args.out).expanduser().write_text(body, encoding="utf-8")
        print(f"report written to {args.out}", file=sys.stderr)
    else:
        print(body)

    return 0 if all(r.within_tolerance for r in reports) else 1


def _resolve_reconcile_dates(args, *, runs_dir: Path) -> list:
    """Translate the CLI mode flags into a list of ``datetime.date`` UTC dates."""
    import datetime as _dt
    import json as _json

    if args.day:
        return [_dt.date.fromisoformat(args.day)]
    if args.from_date:
        if not args.to_date:
            raise ValueError("--from requires --to")
        start = _dt.date.fromisoformat(args.from_date)
        end = _dt.date.fromisoformat(args.to_date)
        if end < start:
            raise ValueError("--to must be >= --from")
        return [start + _dt.timedelta(days=i) for i in range((end - start).days + 1)]
    if args.run:
        session_dir = runs_dir / args.run
        metrics_path = session_dir / "metrics.json"
        if not metrics_path.exists():
            raise ValueError(f"run not found or missing metrics.json: {session_dir}")
        payload = _json.loads(metrics_path.read_text(encoding="utf-8"))
        started_at = payload.get("started_at")
        if not started_at:
            raise ValueError(f"run has no started_at: {args.run}")
        run_date = _dt.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        return [run_date.astimezone(_dt.timezone.utc).date()]
    if args.since_yesterday:
        today = _dt.datetime.now(_dt.timezone.utc).date()
        return [today - _dt.timedelta(days=1), today]
    if args.all:
        dates: set[_dt.date] = set()
        for entry in runs_dir.iterdir():
            if not entry.is_dir():
                continue
            metrics_path = entry / "metrics.json"
            if not metrics_path.exists():
                continue
            try:
                payload = _json.loads(metrics_path.read_text(encoding="utf-8"))
                started_at = payload.get("started_at")
                if not started_at:
                    continue
                run_date = _dt.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                dates.add(run_date.astimezone(_dt.timezone.utc).date())
            except (ValueError, OSError, json.JSONDecodeError):
                continue
        return sorted(dates)
    raise ValueError("no mode flag provided")


if __name__ == "__main__":
    sys.exit(main())
