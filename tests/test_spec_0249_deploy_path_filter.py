"""YAML-shape test: deploy.yml only deploys image-affecting commits (spec 0249).

`.github/workflows/deploy.yml` triggered on *every* push to main with no
`paths:` filter, so each queue-state telemetry commit (`dashboard/**`, at most
`handoffs/**`) fired a full `test → flyctl deploy → sweep` pipeline that shipped
a byte-identical image — ~13 redundant deploys per `/dev-next` cycle.

Spec 0249 adds an allow-list `paths:` filter scoped to the files that actually
change the shipped image. This test locks the post-fix shape:

  - Positive: `on.push.paths` exists and contains the image-affecting globs.
  - Antipodal-absence: telemetry-only paths (dashboard/handoffs/specs) are NOT
    in the allow-list — they must never trigger a deploy.
  - Invariant guard: the version-bump-guaranteed paths (`pyproject.toml` and
    `src/**`) are present — the property that keeps `/dev-next` step-20
    deploy-watch alive (spec 0249 §4). A future edit dropping either fails here.
"""

from __future__ import annotations

from pathlib import Path

import yaml

DEPLOY_YML = (
    Path(__file__).resolve().parent.parent / ".github" / "workflows" / "deploy.yml"
)


def _push_paths() -> list[str]:
    doc = yaml.safe_load(DEPLOY_YML.read_text(encoding="utf-8"))
    # YAML 1.1 parses the bare key `on` as boolean True; PyYAML keys it as True.
    on = doc.get("on", doc.get(True))
    assert isinstance(on, dict), f"deploy.yml `on:` is not a mapping: {on!r}"
    push = on.get("push")
    assert isinstance(push, dict), f"deploy.yml `on.push` is not a mapping: {push!r}"
    paths = push.get("paths")
    assert isinstance(paths, list), (
        "deploy.yml `on.push.paths` must be a list — spec 0249 added the "
        f"allow-list filter; got {paths!r}"
    )
    return paths


def test_push_paths_allowlist_present() -> None:
    """Positive: the allow-list exists and contains the image-affecting globs."""
    paths = _push_paths()
    for expected in ("src/**", "pyproject.toml", "uv.lock"):
        assert expected in paths, (
            f"deploy.yml on.push.paths must contain {expected!r} (spec 0249); "
            f"got {paths!r}"
        )


def test_telemetry_paths_excluded() -> None:
    """Antipodal-absence: telemetry-only paths must NOT trigger a deploy."""
    paths = _push_paths()
    for forbidden in ("dashboard/**", "handoffs/**", "specs/**"):
        assert forbidden not in paths, (
            f"deploy.yml on.push.paths must NOT contain {forbidden!r} — "
            "queue-state telemetry commits must not deploy (spec 0249); "
            f"got {paths!r}"
        )


def test_version_bump_paths_keep_dev_next_alive() -> None:
    """Invariant guard: the version-bump-guaranteed paths must stay in the
    allow-list so every spec merge-commit still triggers a deploy that
    `/dev-next` step 20 can watch (spec 0249 §4)."""
    paths = _push_paths()
    for guaranteed in ("pyproject.toml", "src/**"):
        assert guaranteed in paths, (
            f"deploy.yml on.push.paths dropped {guaranteed!r} — every spec PR "
            "bumps pyproject.toml + src/dual_research/__init__.py (CLAUDE.md "
            "versioning rule); removing it would silently skip the merge-commit "
            "deploy and trip /dev-next step-20 deploy_run_not_found (spec 0249)"
        )
