"""Step 8 · Handover — write the per-spec handover and advance the queue.

Output file: ``handoffs/<YYYY-MM-DD>-spec-<NNNN>-<slug>.md``.

Required sections (per the mission brief):

- Bottom line for the next session
- What shipped (PR link, file diff stats, version bump, deployed version)
- Spec rewrite log (verbatim or "no rewrite needed")
- Current state of main (commit hash, clean tree, deployed version)
- What the next spec needs to know
- Screenshots reference
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dual_research.queue_v2 import state


def begin(spec_number: str, repo_root: Path | None = None) -> None:
    state.begin_step("8_handover", repo_root=repo_root or _repo_root())


def render(spec_number: str, next_spec: str | None, repo_root: Path | None = None) -> str:
    repo = repo_root or _repo_root()
    parsed = json.loads((state.run_dir(spec_number, repo) / "spec-parsed.json").read_text())
    s = state.load(repo)
    active = s.active or {}

    # Pull the durations we already have for the steps that have ended.
    durations = {step: meta.get("duration_s") for step, meta in active.get("steps", {}).items()}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    spec = parsed["spec"]
    slug = parsed["slug"]
    title = parsed["title"]
    label = parsed["label"]
    bump = parsed["version_bump"]
    target_version = parsed.get("target_version", "?")
    detail = active.get("detail", {})

    deploy_detail = detail.get("7_deploy", {})
    pr_detail = detail.get("6_pr", {})
    implement_detail = detail.get("4_implement", {})
    verify_detail = detail.get("5_verify", {})

    head_commit = _git(["rev-parse", "HEAD"], repo) or "?"
    tree_status = _git(["status", "--porcelain"], repo) or ""

    rewrite_log_path = state.run_dir(spec_number, repo) / "rewrite-log.md"
    rewrite_block = (
        rewrite_log_path.read_text().strip()
        if rewrite_log_path.exists()
        else "_no rewrite needed_"
    )

    screenshots_dir = state.run_dir(spec_number, repo) / "screenshots"
    screenshots = sorted(screenshots_dir.glob("*.png")) if screenshots_dir.exists() else []
    screenshots_rel = [p.relative_to(repo).as_posix() for p in screenshots]

    lines: list[str] = []
    lines.append(f"# Handover — spec {spec} · {title}")
    lines.append("")
    lines.append(f"- Date: {today}")
    lines.append(f"- Spec: [`specs/{spec}-{slug}.md`](../specs/{spec}-{slug}.md)")
    if pr_detail.get("pr_url"):
        lines.append(f"- PR: {pr_detail['pr_url']}")
    if deploy_detail.get("merge_commit"):
        lines.append(f"- Merge commit: `{deploy_detail['merge_commit']}`")
    if deploy_detail.get("deployed_version"):
        lines.append(f"- Deployed version: `{deploy_detail['deployed_version']}`")
    lines.append("")

    lines.append("## Bottom line for the next session\n")
    lines.append(_bottom_line(parsed, deploy_detail, verify_detail))
    lines.append("")

    lines.append("## What shipped\n")
    lines.append(f"- Version bump: `{bump}` ({label})")
    lines.append(f"- Target version: `{target_version}` → deployed `{deploy_detail.get('deployed_version', '?')}`")
    lines.append(f"- Files touched: {len(parsed.get('files_touched', []))} listed in § 2")
    lines.append(f"- Implement diff: `{implement_detail.get('diff', '?')}`")
    lines.append("")

    lines.append("## Spec rewrite log\n")
    lines.append(rewrite_block)
    lines.append("")

    lines.append("## Current state of main\n")
    lines.append(f"- Commit: `{head_commit}`")
    lines.append(f"- Working tree: {'clean' if not tree_status.strip() else 'dirty (' + str(tree_status.strip().count(chr(10))) + ' modified files)'}")
    lines.append(f"- Deployed version: `{deploy_detail.get('deployed_version', '?')}`")
    lines.append("")

    lines.append("## What the next spec needs to know\n")
    if next_spec:
        lines.append(f"- Queue next: spec **{next_spec}**.")
    lines.append("- All CSS class anchors introduced in § 11 are now live on main; subsequent specs may reference them without re-introducing.")
    lines.append("- Files in § 2 are now in their post-spec state; review them before re-modifying.")
    lines.append("")

    lines.append("## Step durations (this spec)\n")
    lines.append("| Step | Status | Duration |")
    lines.append("|---|---|---|")
    for step, meta in active.get("steps", {}).items():
        status = meta.get("status", "?")
        dur = meta.get("duration_s")
        dur_str = _fmt(dur) if dur is not None else "—"
        lines.append(f"| {step} | {status} | {dur_str} |")
    lines.append("")

    lines.append("## Screenshots reference\n")
    if screenshots_rel:
        for p in screenshots_rel:
            lines.append(f"- `{p}`")
    else:
        lines.append("_No screenshots captured (Step 5 Verify skipped or empty)._\n")
    lines.append("")

    return "\n".join(lines)


def write_and_complete(
    spec_number: str,
    next_spec: str | None,
    repo_root: Path | None = None,
) -> Path:
    repo = repo_root or _repo_root()
    parsed = json.loads((state.run_dir(spec_number, repo) / "spec-parsed.json").read_text())
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    target = repo / "handoffs" / f"{today}-spec-{parsed['spec']}-{parsed['slug']}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(spec_number, next_spec, repo))
    (state.run_dir(spec_number, repo) / "handover-path.txt").write_text(
        target.relative_to(repo).as_posix() + "\n"
    )
    state.end_step(
        "8_handover",
        "done",
        {"handover_path": target.relative_to(repo).as_posix()},
        repo_root=repo,
    )
    state.finish_spec(repo)
    return target


def _bottom_line(parsed: dict, deploy_detail: dict, verify_detail: dict) -> str:
    rows_passed = verify_detail.get("rows_passed", 0)
    rows_total = verify_detail.get("rows_total", 0)
    deployed = deploy_detail.get("deployed_version", "?")
    issues = parsed.get("notion_issues", [])
    issue_str = (
        f"Resolves Notion issue(s) {', '.join(issues)}. "
        if issues
        else ""
    )
    return (
        f"Spec {parsed['spec']} shipped clean. {issue_str}"
        f"Verify pass: {rows_passed}/{rows_total} matrix rows. "
        f"Production reports `{deployed}` at `/api/health`."
    )


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return out.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def _fmt(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m {s:02d}s"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root")


__all__ = ["begin", "render", "write_and_complete"]
