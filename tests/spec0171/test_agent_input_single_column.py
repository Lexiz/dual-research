"""Spec 0171 — Agent Input pane structural-regression guard.

The bug spec 0151 attempted to fix was the inner anatomy of the per-card
body (now shared with `InputTabContent` via `PromptPiecesThreeSectionView`),
but it preserved the dual-card outer frame. Spec 0171 replaces the outer
frame: one consumer call-site swaps `<AgentInputDualPane>` for
`<AgentInputSingleColumn>`, the two dual-pane functions are deleted, and
the `.agent-input*` CSS block is removed from both stylesheets in
lock-step.

A vitest DOM test that mounts `NegotiateLeftPane` and asserts no
horizontal overflow would be the ideal regression check, but the project
has no vitest harness for `run-detail.jsx` (loaded via in-browser babel,
not bundled). This static-analysis pass is the cheap version that lives
inside the existing pytest run: it fails before the change and passes
after.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent.parent
RUN_DETAIL = REPO_ROOT / "src" / "dual_research" / "ui" / "static" / "run-detail.jsx"
COMPONENTS_CSS = REPO_ROOT / "src" / "dual_research" / "ui" / "static" / "components.css"
COMPOSED_CSS = REPO_ROOT / "design-system" / "assets" / "styles" / "composed-components.css"


@pytest.fixture(scope="module")
def jsx() -> str:
    return RUN_DETAIL.read_text()


@pytest.fixture(scope="module")
def components_css() -> str:
    return COMPONENTS_CSS.read_text()


@pytest.fixture(scope="module")
def composed_css() -> str:
    return COMPOSED_CSS.read_text()


def test_dual_pane_functions_deleted(jsx: str) -> None:
    """`AgentInputDualPane` and `AgentInputPane` must be gone — they
    are the symbols that rendered the two-column frame this spec
    retires."""
    assert "function AgentInputDualPane" not in jsx, (
        "AgentInputDualPane still defined — spec 0171 deletes the dual-pane primitive"
    )
    assert "function AgentInputPane" not in jsx, (
        "AgentInputPane still defined — spec 0171 deletes it alongside AgentInputDualPane"
    )
    # And no JSX consumer reference (we allow narrative mentions in comments).
    consumer_re = re.compile(r"<\s*AgentInputDualPane\b")
    assert not consumer_re.search(jsx), (
        "<AgentInputDualPane> JSX call-site still present"
    )
    assert not re.search(r"<\s*AgentInputPane\b", jsx), (
        "<AgentInputPane> JSX call-site still present"
    )


def test_single_column_component_defined(jsx: str) -> None:
    """The replacement single-column component must be wired in."""
    assert "function AgentInputSingleColumn" in jsx, (
        "AgentInputSingleColumn function not defined"
    )
    # It must be the one rendered when sub === 'input'.
    sub_input_re = re.compile(
        r"sub\s*===\s*'input'\s*&&\s*<\s*AgentInputSingleColumn\b"
    )
    assert sub_input_re.search(jsx), (
        "The sub === 'input' branch in NegotiateLeftPane does not render "
        "<AgentInputSingleColumn>"
    )


def test_single_column_uses_canonical_segmented_control(jsx: str) -> None:
    """Per spec 0171 §3.1 the agent selector must use the canonical
    `.tab-group-solid` + `.tab-solid` segmented control (the post-0173
    DS pattern), not the retired `.fgroup` markup."""
    # Find the AgentInputSingleColumn function body and inspect it.
    match = re.search(
        r"function AgentInputSingleColumn[^{]*\{(?P<body>.*?)\n\}\n",
        jsx,
        flags=re.DOTALL,
    )
    assert match is not None, "AgentInputSingleColumn function body not located"
    body = match.group("body")
    assert "tab-group-solid" in body, "AgentInputSingleColumn missing .tab-group-solid wrapper"
    assert "tab-solid" in body, "AgentInputSingleColumn missing .tab-solid buttons"
    assert "data-active=" in body, (
        "AgentInputSingleColumn missing the data-active={…} state attribute "
        "(spec 0173 §2.3 replaces .is-active class)"
    )
    # PromptPiecesThreeSectionView must be invoked with frame="single".
    assert re.search(
        r"<\s*PromptPiecesThreeSectionView[^>]*frame=\"single\"", body
    ), "AgentInputSingleColumn must render PromptPiecesThreeSectionView frame=\"single\""


def test_agent_input_css_deleted_from_live_stylesheet(components_css: str) -> None:
    """The `.agent-input*` CSS rules in src/dual_research/ui/static/components.css
    must be deleted along with their JSX consumer (CLAUDE.md rule: DS-canonical
    and live copies stay in sync — spec 0171 deletes from both in one commit)."""
    for selector in (
        ".agent-input ",
        ".agent-input__pane",
        ".agent-input__head",
        ".agent-input__body",
    ):
        assert selector not in components_css, (
            f"Live components.css still defines `{selector}` — spec 0171 deletes the dual-pane CSS"
        )
    # Also: no remaining `.agent-input { ... }` rule body — guard against
    # a rule on the bare selector with no trailing space (`.agent-input{...}`).
    assert not re.search(r"\.agent-input\s*\{", components_css), (
        "Live components.css still has a bare .agent-input rule body"
    )


def test_agent_input_css_deleted_from_ds_stylesheet(composed_css: str) -> None:
    """Mirror of the previous assertion for the DS-canonical copy."""
    for selector in (
        ".agent-input ",
        ".agent-input__pane",
        ".agent-input__head",
        ".agent-input__body",
    ):
        assert selector not in composed_css, (
            f"DS composed-components.css still defines `{selector}`"
        )
    assert not re.search(r"\.agent-input\s*\{", composed_css), (
        "DS composed-components.css still has a bare .agent-input rule body"
    )


def test_inputtabcontent_unchanged(jsx: str) -> None:
    """`InputTabContent` (the single-pane consumer used by DocumentModal,
    PreflightResponseModal, InputBriefModal) must keep delegating to
    `PromptPiecesThreeSectionView` with `frame="single"` — spec 0171 §3
    explicitly leaves it untouched."""
    match = re.search(
        r"function InputTabContent\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        jsx,
        flags=re.DOTALL,
    )
    assert match is not None, "InputTabContent function body not located"
    body = match.group("body")
    assert "PromptPiecesThreeSectionView" in body, (
        "InputTabContent no longer delegates to PromptPiecesThreeSectionView"
    )
    assert 'frame="single"' in body, "InputTabContent must keep frame=\"single\""
