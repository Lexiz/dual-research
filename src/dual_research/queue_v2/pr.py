"""Step 6 · PR — push the branch and open a GitHub PR via gh.

Reuses ``.github/PULL_REQUEST_TEMPLATE.md`` shape but fills it with
spec-driven data: title from § 1 Goal, acceptance criteria as a
checkbox list, label per spec front-matter, screenshots inlined.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from dual_research.queue_v2 import state


def begin(spec_number: str, repo_root: Path | None = None) -> None:
    state.begin_step("6_pr", repo_root=repo_root or _repo_root())


def push_branch(branch: str, repo_root: Path | None = None) -> None:
    repo = repo_root or _repo_root()
    subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=repo,
        check=True,
    )


def render_body(spec_number: str, repo_root: Path | None = None) -> str:
    repo = repo_root or _repo_root()
    parsed = json.loads((state.run_dir(spec_number, repo) / "spec-parsed.json").read_text())
    spec_file = parsed["file_path"]
    label = parsed["label"]
    bump = parsed["version_bump"]
    acceptance = parsed.get("acceptance", [])
    title = parsed.get("title", "")
    notion_issues = parsed.get("notion_issues", [])

    handover_paths = parsed.get("handover_read_paths", [])
    rewrite_log = state.run_dir(spec_number, repo) / "rewrite-log.md"
    verify_report = state.run_dir(spec_number, repo) / "verify-report.md"

    lines: list[str] = []
    lines.append("## Spec\n")
    rel = Path(spec_file).relative_to(repo) if Path(spec_file).is_absolute() else Path(spec_file)
    lines.append(f"Implements [`{rel.as_posix()}`](./{rel.as_posix()}).\n")
    if handover_paths:
        lines.append("Previous handover read:\n")
        for h in handover_paths:
            lines.append(f"- [`{h}`](./{h})")
        lines.append("")
    lines.append("## Summary\n")
    lines.append(f"{title}\n")
    if notion_issues:
        lines.append("Resolves Notion issue(s): " + ", ".join(notion_issues) + ".\n")
    lines.append("## Changes\n")
    for path in parsed.get("files_touched", []):
        lines.append(f"- `{path}`")
    lines.append("")
    lines.append("## Version\n")
    lines.append(f"- Spec label: `{label}`")
    lines.append(f"- Version bump: `{bump}`")
    lines.append(f"- Target version: `{parsed.get('target_version', '')}`")
    lines.append("")
    lines.append("## Acceptance criteria\n")
    for line in acceptance:
        marker = "x" if line.startswith("[x]") else " "
        body = line[3:].strip() if line.startswith(("[ ]", "[x]")) else line
        lines.append(f"- [{marker}] {body}")
    lines.append("")

    if rewrite_log.exists() and "_No alignment notes" not in rewrite_log.read_text():
        lines.append("## Spec rewrite log\n")
        lines.append(rewrite_log.read_text().strip())
        lines.append("")
    else:
        lines.append("## Spec rewrite log\n_No rewrite needed for this spec._\n")

    if verify_report.exists():
        lines.append("## Verify report\n")
        lines.append(verify_report.read_text().strip())
        lines.append("")

    lines.append("## Queue checklist\n")
    lines.append("- [x] Step 1 Read · spec parsed")
    lines.append("- [x] Step 2 Reason · alignment notes computed")
    lines.append("- [x] Step 3 Rewrite · in-place edits logged (or skipped)")
    lines.append("- [x] Step 4 Implement · scope-guarded code edits")
    lines.append("- [x] Step 5 Verify · all matrix rows pass")
    lines.append("- [ ] Step 7 Deploy · CI green, fly deploy, /api/health matches new version")
    lines.append("- [ ] Step 8 Handover · `handoffs/<date>-spec-<NNNN>-<slug>.md` written")
    lines.append("")
    return "\n".join(lines)


def open_pr(
    spec_number: str,
    branch: str,
    repo_root: Path | None = None,
    dry_run: bool = False,
) -> str:
    """Open a PR. Returns the PR URL (empty when dry_run=True)."""
    repo = repo_root or _repo_root()
    parsed = json.loads((state.run_dir(spec_number, repo) / "spec-parsed.json").read_text())
    pr_title = f"Spec {parsed['spec']} — {parsed['title']}"
    label = f"spec/{parsed['label']}"
    body = render_body(spec_number, repo)

    if dry_run:
        return ""

    body_file = state.run_dir(spec_number, repo) / "pr-body.md"
    body_file.write_text(body)
    out = subprocess.run(
        [
            "gh", "pr", "create",
            "--head", branch,
            "--base", "main",
            "--title", pr_title,
            "--label", label,
            "--body-file", str(body_file),
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    url = out.stdout.strip().splitlines()[-1] if out.stdout else ""
    (state.run_dir(spec_number, repo) / "pr-url.txt").write_text(url + "\n")
    return url


def complete(spec_number: str, pr_url: str, repo_root: Path | None = None) -> None:
    state.end_step(
        "6_pr",
        "done",
        {"pr_url": pr_url},
        repo_root=repo_root or _repo_root(),
    )


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root")


__all__ = ["begin", "complete", "open_pr", "push_branch", "render_body"]
