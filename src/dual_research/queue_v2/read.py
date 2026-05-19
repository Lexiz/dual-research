"""Step 1 · Read — load a spec file and persist a parsed sidecar.

Failure mode: spec file not found → step fails, queue halts.
"""

from __future__ import annotations

from pathlib import Path

from dual_research.queue_v2 import parse_spec, state


def find_spec(spec_number: str, repo_root: Path | None = None) -> Path:
    repo = repo_root or _repo_root()
    matches = sorted((repo / "specs").glob(f"{spec_number.zfill(4)}-*.md"))
    if not matches:
        raise FileNotFoundError(f"no spec file under specs/ matches {spec_number}")
    if len(matches) > 1:
        raise RuntimeError(f"multiple specs match {spec_number}: {matches}")
    return matches[0]


def run(spec_number: str, repo_root: Path | None = None) -> parse_spec.ParsedSpec:
    repo = repo_root or _repo_root()
    state.begin_step("1_read", repo_root=repo)
    try:
        spec_path = find_spec(spec_number, repo_root=repo)
        parsed = parse_spec.parse(spec_path)
        target = state.run_dir(parsed.spec, repo_root=repo) / "spec-parsed.json"
        parse_spec.write_parsed(parsed, target)
    except Exception as e:
        state.end_step("1_read", "failed", {"error": str(e)}, repo_root=repo)
        raise
    state.end_step(
        "1_read",
        "done",
        {
            "spec_file": str(spec_path),
            "files_touched_count": len(parsed.files_touched),
            "matrix_rows": len(parsed.visual_matrix),
            "acceptance_count": len(parsed.acceptance),
        },
        repo_root=repo,
    )
    return parsed


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise RuntimeError("could not locate repo root")


__all__ = ["find_spec", "run"]
