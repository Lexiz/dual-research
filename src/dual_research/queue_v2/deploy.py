"""Step 7 · Deploy — wait for CI green, squash-merge, fly deploy, health probe.

CI uses GitHub Actions; the queue polls ``gh pr checks`` until all
checks pass. After squash-merge the queue runs ``fly deploy`` and
polls ``https://dual-research-alex.fly.dev/api/health`` until the
returned version field matches the spec's target-version.

Failure modes:
- CI red → halt, alert with failing job log.
- Health probe doesn't converge inside the timeout → halt; the
  operator decides whether to fly rollback or hand-fix.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import httpx

from dual_research.queue_v2 import state

HEALTH_URL = "https://dual-research-alex.fly.dev/api/health"
CI_POLL_INTERVAL_S = 15
HEALTH_POLL_INTERVAL_S = 5
CI_TIMEOUT_S = 60 * 20
HEALTH_TIMEOUT_S = 60 * 10


def begin(spec_number: str, repo_root: Path | None = None) -> None:
    state.begin_step("7_deploy", repo_root=repo_root or _repo_root())


def wait_for_ci(pr_url: str, repo_root: Path | None = None) -> None:
    repo = repo_root or _repo_root()
    deadline = time.time() + CI_TIMEOUT_S
    while time.time() < deadline:
        out = subprocess.run(
            ["gh", "pr", "checks", pr_url],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        status = (out.stdout or "") + (out.stderr or "")
        if "All checks were successful" in status or _all_pass(out.stdout or ""):
            return
        if "fail" in status.lower() or out.returncode == 1 and "pending" not in status.lower():
            raise RuntimeError(f"CI failed for {pr_url}\n{status}")
        time.sleep(CI_POLL_INTERVAL_S)
    raise TimeoutError(f"CI did not converge inside {CI_TIMEOUT_S}s for {pr_url}")


def squash_merge(pr_url: str, repo_root: Path | None = None) -> str:
    repo = repo_root or _repo_root()
    out = subprocess.run(
        ["gh", "pr", "merge", "--admin", "--squash", "--delete-branch", pr_url],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "fetch", "origin", "main"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "main"], cwd=repo, check=True)
    subprocess.run(["git", "pull", "--ff-only"], cwd=repo, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()
    return head


def fly_deploy(repo_root: Path | None = None) -> None:
    repo = repo_root or _repo_root()
    subprocess.run(["fly", "deploy"], cwd=repo, check=True)


def wait_for_health(target_version: str) -> dict:
    deadline = time.time() + HEALTH_TIMEOUT_S
    last_payload: dict = {}
    while time.time() < deadline:
        try:
            r = httpx.get(HEALTH_URL, timeout=5.0)
            r.raise_for_status()
            last_payload = r.json()
            if last_payload.get("version") == target_version:
                return last_payload
        except httpx.HTTPError:
            pass
        time.sleep(HEALTH_POLL_INTERVAL_S)
    raise TimeoutError(
        f"/api/health did not report version {target_version} within {HEALTH_TIMEOUT_S}s "
        f"(last seen: {last_payload})"
    )


def complete(
    spec_number: str,
    merge_commit: str,
    deployed_version: str,
    repo_root: Path | None = None,
) -> None:
    repo = repo_root or _repo_root()
    log_path = state.run_dir(spec_number, repo) / "deploy-log.md"
    log_path.write_text(
        f"# Spec {spec_number} — deploy log\n\n"
        f"- Merge commit: `{merge_commit}`\n"
        f"- Deployed version: `{deployed_version}`\n"
        f"- /api/health: {HEALTH_URL}\n"
    )
    state.end_step(
        "7_deploy",
        "done",
        {"merge_commit": merge_commit, "deployed_version": deployed_version},
        repo_root=repo,
    )


def _all_pass(text: str) -> bool:
    if not text.strip():
        return False
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return False
    return all(("pass" in l.lower() or "✓" in l) for l in lines)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root")


__all__ = [
    "HEALTH_URL",
    "begin",
    "complete",
    "fly_deploy",
    "squash_merge",
    "wait_for_ci",
    "wait_for_health",
]
