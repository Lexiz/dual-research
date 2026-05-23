"""Spec 0175 — Summary tab v2 structural guard.

The summary-tab rewrite ships a deterministic `_computeSummaryStats`
helper, a verdict-tone picker, a status-aware hero variant picker, and
three new components — StatTile, AgentSummaryCard, CritiqueBreakdown —
on top of an auto-jump-to-summary effect inside `CritiqueExplorer`.

The repo has no vitest harness that mounts `run-detail.jsx` (loaded via
in-browser babel, not bundled), so the spec's behavioural assertions are
covered by static-analysis here: the structural contracts that survive
in pytest. Runtime verification of the deduplicated tally, the hero
variants, and the confetti gate is done manually in the live preview
(documented in the handoff).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent.parent
RUN_DETAIL = REPO_ROOT / "src" / "dual_research" / "ui" / "static" / "run-detail.jsx"
HOW_IT_WORKS = REPO_ROOT / "src" / "dual_research" / "ui" / "static" / "how-it-works.jsx"


@pytest.fixture(scope="module")
def jsx() -> str:
    return RUN_DETAIL.read_text()


@pytest.fixture(scope="module")
def hiw() -> str:
    return HOW_IT_WORKS.read_text()


# ── New helpers exist and have the expected signatures ────────────────────


def test_compute_summary_stats_defined(jsx: str) -> None:
    """Stats helper is the contract surface for verdict + per-agent tally."""
    assert re.search(
        r"function _computeSummaryStats\(\s*run,\s*questions,\s*disagreements,\s*issues,\s*comments\s*\)",
        jsx,
    ), "_computeSummaryStats(run, questions, disagreements, issues, comments) signature missing"


def test_verdict_thresholds_tightened(jsx: str) -> None:
    """Spec 0175 §2.2 — green verdict requires resolveRatio >= 0.85 AND
    driftRatio < 0.2. The old 0.70 threshold must be retired."""
    body = jsx
    fn_match = re.search(
        r"function _computeSummaryStats\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        body, flags=re.DOTALL,
    )
    assert fn_match is not None
    fn_body = fn_match.group("body")
    # Green = positive.
    assert re.search(r"resolveRatio\s*>=\s*0\.85", fn_body), (
        "Mostly-positive threshold must be `resolveRatio >= 0.85` (spec 0175 §2.2)"
    )
    assert "0.7" not in re.sub(r"//[^\n]*", "", fn_body) or "0.85" in fn_body, (
        "Old 0.7 threshold lingering in _computeSummaryStats; spec 0175 retires it"
    )
    # Negative threshold preserved.
    assert re.search(r"resolveRatio\s*<\s*0\.40", fn_body) or \
           re.search(r"resolveRatio\s*<\s*0\.4\b", fn_body)


def test_resolved_both_deduplication(jsx: str) -> None:
    """Spec 0175 §2.3 — `resolved-both` increments `mutualAligned`, NOT
    the per-agent `solved` rows."""
    fn_match = re.search(
        r"function _computeSummaryStats\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        jsx, flags=re.DOTALL,
    )
    fn_body = fn_match.group("body")
    # Look for the mutualAligned counter.
    assert "mutualAligned" in fn_body, "mutualAligned counter missing"
    # The resolved-both branch must increment mutualAligned and NOT call
    # _creditSolve('both', ...).
    assert re.search(r"resolved-both[^\n]*mutualAligned\+\+", fn_body), (
        "resolved-both branch should increment mutualAligned"
    )
    assert "_creditSolve('both'," not in fn_body, (
        "_creditSolve('both', ...) would double-credit per-agent solved rows"
    )


def test_pick_verdict_tone_defined(jsx: str) -> None:
    """Verdict-tone resolver maps verdict → color + label, with the errored
    override for the hero variant."""
    assert re.search(r"function _pickVerdictTone\(verdict,\s*runStatus\)", jsx), (
        "_pickVerdictTone(verdict, runStatus) missing"
    )
    # Errored case must short-circuit to 'Incomplete'.
    match = re.search(
        r"function _pickVerdictTone\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        jsx, flags=re.DOTALL,
    )
    body = match.group("body")
    assert "'errored'" in body and "Incomplete" in body, (
        "_pickVerdictTone errored branch should yield the 'Incomplete' label"
    )


def test_pick_hero_variant_defined(jsx: str) -> None:
    """Hero variant resolver covers completed / deadlocked / errored
    branches per spec §2.4."""
    assert re.search(r"function _pickHeroVariant\(run,\s*stats\)", jsx)
    match = re.search(
        r"function _pickHeroVariant\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        jsx, flags=re.DOTALL,
    )
    body = match.group("body")
    for status in ("deadlocked", "errored"):
        assert f"'{status}'" in body, f"_pickHeroVariant missing {status} branch"


def test_compute_web_search_stats_defined(jsx: str) -> None:
    """The web-searches stat tile reads from SearchIndexContext via this helper."""
    assert "function _computeWebSearchStats" in jsx
    assert "queries" in jsx and "consulted" in jsx


def test_confetti_helper_defined(jsx: str) -> None:
    """A standalone, dependency-free confetti primitive (~80 lines)."""
    assert re.search(r"function _fireConfetti\(originRect\)", jsx)
    fn_match = re.search(
        r"function _fireConfetti\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        jsx, flags=re.DOTALL,
    )
    body = fn_match.group("body")
    # Compositor-only animation: transform + opacity, not layout properties.
    assert "transform" in body and "opacity" in body
    assert "requestAnimationFrame" in body


# ── New components exist ──────────────────────────────────────────────────


def test_stat_tile_defined(jsx: str) -> None:
    assert re.search(r"function StatTile\(\{\s*icon,\s*label,\s*value,\s*hint\s*\}\)", jsx)


def test_agent_summary_card_defined(jsx: str) -> None:
    assert re.search(r"function AgentSummaryCard\(\{\s*agent,\s*stats\s*\}\)", jsx)


def test_critique_breakdown_defined(jsx: str) -> None:
    assert "function CritiqueBreakdown(" in jsx
    assert "function CritiqueBreakdownRow(" in jsx
    # Four expandable rows.
    assert jsx.count("<CritiqueBreakdownRow") >= 4, (
        "CritiqueBreakdown should render 4 expandable rows (Claude/GPT × raised/solved)"
    )


# ── Auto-jump + tab-pick wiring (spec 0175 §2.5) ──────────────────────────


def test_user_picked_tab_ref_wired(jsx: str) -> None:
    """The auto-jump suppression flag must exist and be set when any
    phase-tab button is clicked."""
    assert "userPickedTabRef" in jsx
    # The pickPhase callback wraps setSelectedPhase and sets the ref.
    pick = re.search(
        r"const pickPhase = React\.useCallback\(\(phase\) => \{(?P<body>.*?)\}, \[\]\);",
        jsx, flags=re.DOTALL,
    )
    assert pick is not None, "pickPhase callback missing"
    assert "userPickedTabRef.current = true" in pick.group("body")
    assert "setSelectedPhase(phase)" in pick.group("body")
    # All four phase-tab onClicks route through pickPhase.
    onclicks = re.findall(r"onClick=\{\(\) => (pickPhase|setSelectedPhase)\((?:0|2|4|'summary')\)\}", jsx)
    via_pick = sum(1 for handler, in [(o,) for o in onclicks] if handler == "pickPhase")
    assert via_pick == 4, (
        f"Expected 4 phase-tab onClicks via pickPhase, got {via_pick}; "
        f"raw matches: {onclicks}"
    )


def test_auto_jump_effect_fires_on_terminal_transition(jsx: str) -> None:
    """The effect must compare prior isTerminal (wasTerminalRef) to fire
    exactly once on false → true, scoped to the [isTerminal] dependency."""
    assert "wasTerminalRef" in jsx
    # Anchor on the auto-jump effect's tail-end and walk backwards to the
    # opening `React.useEffect`. The body has nested braces (the inner
    # `if (...) { setSelectedPhase(...) }`), so a simple greedy match on
    # `[^}]*` won't span them — locate the dependency tail and the unique
    # interior tokens instead.
    tail = re.search(r"wasTerminalRef\.current = isTerminal;\s*\},\s*\[isTerminal\]\)", jsx)
    assert tail is not None, (
        "Auto-jump useEffect tail (`wasTerminalRef.current = isTerminal; }, [isTerminal])`) missing"
    )
    # Trace back to the enclosing useEffect — there's only one with this exact dep tuple.
    matches = list(re.finditer(r"React\.useEffect\(\(\) => \{", jsx))
    assert matches, "no React.useEffect blocks found at all"
    # Pick the one whose tail is closest before our anchor.
    starts = [m.start() for m in matches if m.start() < tail.start()]
    assert starts, "no useEffect opens before the auto-jump tail"
    start = max(starts)
    body = jsx[start:tail.end()]
    assert "!wasTerminalRef.current" in body
    assert "isTerminal" in body
    assert "!userPickedTabRef.current" in body
    assert "setSelectedPhase('summary')" in body


# ── Layout shell ──────────────────────────────────────────────────────────


def test_summary_layout_has_expected_sections(jsx: str) -> None:
    """The CritiqueSummaryView body should mount all the v2 surfaces."""
    body_match = re.search(
        r"function CritiqueSummaryView\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        jsx, flags=re.DOTALL,
    )
    assert body_match is not None
    body = body_match.group("body")
    # Hero + stat grid + agent cards + breakdown + drill-down toggle + footer.
    assert "<AgentSummaryCard" in body
    assert "<CritiqueBreakdown" in body
    assert "<StatTile" in body
    # The download link points at the canonical artifact endpoint.
    assert "/api/runs/" in body and "/files/final.md" in body
    # The drill-down still mounts the legacy renderPhase calls.
    assert "renderPhase('Phase 2" in body
    assert "renderPhase('Phase 4" in body


def test_max_width_container(jsx: str) -> None:
    """Spec 0175 §3.2 — 980 px container max so larger viewports get
    whitespace rather than a stretched layout."""
    body_match = re.search(
        r"function CritiqueSummaryView\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        jsx, flags=re.DOTALL,
    )
    body = body_match.group("body")
    assert "maxWidth: 980" in body, (
        "CritiqueSummaryView should set maxWidth: 980 on the inner container"
    )


# ── how-it-works.jsx changelog sync ───────────────────────────────────────


def test_how_it_works_has_v1_35_0_entry(hiw: str) -> None:
    """Spec 0175 §6 step 11 — the in-app changelog must carry a v1.35.0
    entry that points at spec 0175."""
    assert "version: '1.35.0'" in hiw, "Missing 1.35.0 changelog entry"
    # The new entry must surface spec 0175.
    entry = re.search(
        r"version: '1\.35\.0'.*?screenshots: \[\]",
        hiw, flags=re.DOTALL,
    )
    assert entry is not None, "1.35.0 entry malformed"
    assert "'0175'" in entry.group(0)
    # And mention the Summary tab.
    assert "Summary" in entry.group(0)


# ── Old behaviour preserved ───────────────────────────────────────────────


def test_legacy_summary_kind_table_unchanged(jsx: str) -> None:
    """SummaryKindTable is the byte-identical per-round drill-down body."""
    assert "function SummaryKindTable(" in jsx


def test_no_duplicate_verdict_in_story_block(jsx: str) -> None:
    """Spec 0175 §2.7 — the story block must not re-render the verdict
    line (the hero band carries it). The summaryCopy memo should be
    constructed only from sentence2 + sentence3."""
    fn = re.search(
        r"function CritiqueSummaryView\([^)]*\)\s*\{(?P<body>.*?)\n\}\n",
        jsx, flags=re.DOTALL,
    )
    body = fn.group("body")
    # The original spec-0072 D7-D10 memo built `**${verdict}**` into
    # sentence1 of summaryCopy. After this spec the memo must not do that.
    assert "`**${verdict}**`" not in body, (
        "summaryCopy still embeds a verdict prefix into the story block — "
        "spec 0175 §2.7 surfaces the verdict in the hero band instead"
    )
