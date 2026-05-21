"""Spec 0147 §7 — Phase 0 critique section grouping (B01).

Regex-level assertions over `run-detail.jsx`:
    - `PHASE_CHIP_ALLOWLIST[0]` lists `questions` and `disagreements`
      (was `[]` pre-spec; Phase 0 was missing from the chip kinds the
      filter row + per-card chips render).
    - The `<div className="phase-tabs">` row in `CritiqueExplorer`
      renders three phase buttons (P0 + P2 + P4) and not just two.
    - The default-tab guard in `CritiqueExplorer.initial` accepts
      `run.phase === 0` and falls back to `haveAny(0)` before defaulting
      to 2.
    - The `dr-critique-jump` cross-pane handler accepts
      `targetPhase === 0`.
    - The `CritiquePhaseContent` `pending` branch carries a
      `phaseId === 0` arm.

These are structural guards against an accidental revert of the spec's
JSX edits, mirroring the spec-0144 convention (Python tests covering
JSX-side changes via grep / AST-shape inspection in the absence of a
JS test harness).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RUN_DETAIL = (
    Path(__file__).parent.parent.parent
    / "src"
    / "dual_research"
    / "ui"
    / "static"
    / "run-detail.jsx"
)


@pytest.fixture(scope="module")
def jsx() -> str:
    return RUN_DETAIL.read_text()


def test_phase_chip_allowlist_phase0_lists_questions_and_disagreements(
    jsx: str,
) -> None:
    """Spec 0147 §5.1 — `PHASE_CHIP_ALLOWLIST[0]` must include the
    chip kinds the spec-0135 Phase 0 protocol emits.

    Pre-spec value was `0: []`, which gated the new tab's chips out of
    the filter row + per-card cluster.
    """
    m = re.search(
        r"const\s+PHASE_CHIP_ALLOWLIST\s*=\s*\{(.*?)\}\s*;",
        jsx,
        re.DOTALL,
    )
    assert m is not None, "PHASE_CHIP_ALLOWLIST not found in run-detail.jsx"
    body = m.group(1)
    line = re.search(r"^\s*0\s*:\s*\[(?P<kinds>[^\]]*)\]", body, re.MULTILINE)
    assert line is not None, (
        f"PHASE_CHIP_ALLOWLIST[0] entry not found in body:\n{body}"
    )
    kinds = {
        token.strip().strip("'").strip('"')
        for token in line.group("kinds").split(",")
        if token.strip()
    }
    assert "questions" in kinds and "disagreements" in kinds, (
        f"PHASE_CHIP_ALLOWLIST[0] must list questions+disagreements; "
        f"got {kinds!r}"
    )


def test_phase_tabs_row_contains_p0_p2_p4(jsx: str) -> None:
    """Spec 0147 §5.1 — the `<div className="phase-tabs">` row in
    `CritiqueExplorer` renders three phase buttons.
    """
    pattern = re.compile(
        r'<div\s+className="phase-tabs">(?P<body>.*?)</div>',
        re.DOTALL,
    )
    blocks = pattern.findall(jsx)
    assert blocks, "no <div className=\"phase-tabs\"> block found"
    for body in blocks:
        for code in ("P0", "P2", "P4"):
            assert f">{code}<" in body, (
                f"phase-tabs row missing {code} button; saw:\n{body}"
            )
        for name in ("Brief", "Negotiate", "Review"):
            assert f">{name}<" in body, (
                f"phase-tabs row missing {name} label; saw:\n{body}"
            )


def test_initial_default_tab_falls_through_phase0(jsx: str) -> None:
    """Spec 0147 §5.1 — `CritiqueExplorer.initial` must accept
    `run.phase === 0` directly and fall back to `haveAny(0)` before
    defaulting to 2.
    """
    m = re.search(
        r"const\s+initial\s*=\s*\(run\.phase\s*===\s*4"
        r".*?run\.phase\s*===\s*2"
        r".*?run\.phase\s*===\s*0\s*\).*?"
        r"haveAny\(4\).*?haveAny\(2\).*?haveAny\(0\)",
        jsx,
        re.DOTALL,
    )
    assert m is not None, (
        "default-tab guard does not include `run.phase === 0` and "
        "`haveAny(0)` fallback"
    )


def test_critique_jump_handler_accepts_phase0(jsx: str) -> None:
    """Spec 0147 §5.1 — the `dr-critique-jump` handler in
    `CritiqueExplorer` accepts `targetPhase === 0` so a Phase 0
    timeline-card chip can jump to the P0 critique tab.
    """
    m = re.search(
        r"if\s*\(targetPhase\s*===\s*0\s*\|\|\s*"
        r"targetPhase\s*===\s*2\s*\|\|\s*"
        r"targetPhase\s*===\s*4\)\s*\{",
        jsx,
    )
    assert m is not None, (
        "cross-pane jump handler does not accept targetPhase === 0"
    )


def test_critique_phase_content_pending_branch_handles_phase0(jsx: str) -> None:
    """Spec 0147 §5.1 — the `CritiquePhaseContent` pending branch
    carries a `phaseId === 0` arm (defensive; in practice pending
    never fires for P0 since `run.phase < 0` is unreachable).
    """
    fn_match = re.search(
        r"function\s+CritiquePhaseContent\s*\(.*?\)\s*\{(?P<body>.*?)"
        r"\n(?=function\s+\w+\s*\()",
        jsx,
        re.DOTALL,
    )
    assert fn_match is not None, "CritiquePhaseContent function not found"
    body = fn_match.group("body")
    assert "phaseId === 0" in body, (
        "CritiquePhaseContent pending branch missing phaseId === 0 arm"
    )
    assert "Phase 0 hasn't started yet" in body, (
        "CritiquePhaseContent pending branch missing P0 text"
    )
