"""Tests for queue_v2.parse_spec — the section-header parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.queue_v2 import parse_spec

SPEC_FIXTURE = """---
spec: 0092
title: M3 token foundation
label: refactoring
version-bump: PATCH
target-version: 0.72.1
status: proposed
---

# Spec 0092 — M3 token foundation

## 1. Goal

Lay down the M3 token layer.

## 2. Files touched

- `src/dual_research/ui/static/tokens.css` — replace tree.
- `src/dual_research/ui/static/theme.css` — light/dark flip.
- `src/dual_research/ui/static/base.css` — boot block.
- `src/dual_research/ui/static/index.html` — font preconnect.
- `pyproject.toml` — version bump.

## 3. Material 3 anatomy

Implements `#identity`, `#palette`, `#type`, `#shape`, `#elevation`, `#system`.

## 4. Notion issues addressed

Implements design-system foundation only; no Notion issue. Issues 7 and 8
become addressable after this lands.

## 5. Acceptance criteria

- [ ] `getComputedStyle(document.body).fontFamily` contains Roboto Flex.
- [ ] `body.light` flips `--md-surface` from dark to cream.
- [ ] Focus ring visible on every focusable.

## 6. Visual verification matrix

- `2200×1300 dark` — `#/runs`
- `2200×1300 light` — `#/runs`
- `1400×900 dark` — `#/runs/<latest>`
- `1400×900 light` — `#/runs/<latest>`

## 7. Anti-pattern checks

- [ ] No emoji as icons.

## 8. Handover read

> *First task on running this spec: read `docs/design-system-v2/README.md` end-to-end, then `handoffs/2026-05-19-data-integrity-arc-complete.md`.*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any criterion below, edit this file in-place to align.*

## 10. Backend touched?

**no.** Frontend tokens only.

## 11. CSS class anchor list

```
:root  declarations             → #palette
body.light                       → #light
.t-display-l                     → #type
```
"""


@pytest.fixture()
def spec_file(tmp_path: Path) -> Path:
    p = tmp_path / "0092-m3-token-foundation.md"
    p.write_text(SPEC_FIXTURE)
    return p


def test_frontmatter(spec_file: Path) -> None:
    parsed = parse_spec.parse(spec_file)
    assert parsed.spec == "0092"
    assert parsed.slug == "m3-token-foundation"
    assert parsed.title == "M3 token foundation"
    assert parsed.label == "refactoring"
    assert parsed.version_bump == "PATCH"
    assert parsed.target_version == "0.72.1"


def test_files_touched_extracts_paths(spec_file: Path) -> None:
    parsed = parse_spec.parse(spec_file)
    assert "src/dual_research/ui/static/tokens.css" in parsed.files_touched
    assert "src/dual_research/ui/static/theme.css" in parsed.files_touched
    assert "src/dual_research/ui/static/index.html" in parsed.files_touched
    assert "pyproject.toml" in parsed.files_touched
    # All entries unique.
    assert len(parsed.files_touched) == len(set(parsed.files_touched))


def test_visual_matrix_normalises(spec_file: Path) -> None:
    parsed = parse_spec.parse(spec_file)
    assert len(parsed.visual_matrix) == 4
    pairs = {(s.viewport, s.theme) for s in parsed.visual_matrix}
    assert pairs == {
        ("2200x1300", "dark"),
        ("2200x1300", "light"),
        ("1400x900", "dark"),
        ("1400x900", "light"),
    }


def test_visual_matrix_empty_does_not_raise(tmp_path: Path) -> None:
    # The fallback is in verify.planned_shots, not the parser — but the
    # parser must hand back an empty list rather than raising.
    p = tmp_path / "0099-vague.md"
    p.write_text(
        "---\nspec: 0099\ntitle: t\nlabel: bug\nversion-bump: PATCH\n"
        "target-version: 0.72.2\n---\n\n"
        "## 6. Visual verification matrix\n\n_Same as last spec._\n"
    )
    parsed = parse_spec.parse(p)
    assert parsed.visual_matrix == []


def test_acceptance_strips_checkboxes(spec_file: Path) -> None:
    parsed = parse_spec.parse(spec_file)
    assert len(parsed.acceptance) == 3
    assert parsed.acceptance[0].startswith("`getComputedStyle")
    assert all(not l.startswith("[") for l in parsed.acceptance)


def test_handover_read_path_extracted(spec_file: Path) -> None:
    parsed = parse_spec.parse(spec_file)
    assert "docs/design-system-v2/README.md" in parsed.handover_read_paths
    assert "handoffs/2026-05-19-data-integrity-arc-complete.md" in parsed.handover_read_paths


def test_design_anchors_filtered_to_known(spec_file: Path) -> None:
    parsed = parse_spec.parse(spec_file)
    for anchor in ("identity", "palette", "type", "shape", "elevation", "system"):
        assert anchor in parsed.design_anchors
    # Unknown junk anchors are filtered.
    assert "xyznotreal" not in parsed.design_anchors


def test_css_anchors_pulled_from_code_block(spec_file: Path) -> None:
    parsed = parse_spec.parse(spec_file)
    assert any("body.light" in c for c in parsed.css_anchors)
    assert any(".t-display-l" in c for c in parsed.css_anchors)


def test_backend_touched_flag(spec_file: Path) -> None:
    parsed = parse_spec.parse(spec_file)
    assert parsed.backend_touched is False


def test_notion_issues_extracted(spec_file: Path) -> None:
    parsed = parse_spec.parse(spec_file)
    # "Issues 7 and 8" in §4 prose.
    assert "07" in parsed.notion_issues
    assert "08" in parsed.notion_issues
