"""Spec 0184 — fidelity check: live dashboard vs `dashboard-redesign-v3-horizontal.html`.

Two complementary assertions, both pure-stdlib (no Playwright, no
browser, no js2py) so they run inside the existing
``uv run pytest tests/ -q`` flow without new dependencies.

1. **Structural-parity** — the mockup's hero → counters → tabs → panels
   ordering, the seven-step timeline inside the hero (spec 0213 §2.1
   collapsed the previous 11-row anatomy), the 5-counter row with
   `.counter--accent` at slot 5, and the tab strip's button order
   must all appear in the live render. Subsequence match (not exact) so
   the live render's region-swap wrapper divs are tolerated.

2. **Token-budget** — every `--md-*` / `--p-*` / `--chart-*` token the
   mockup uses inside `.tl*`, `.counter*`, `.chart*` rules must also
   appear in the live render's CSS. No hex code may leak into the live
   render (tokens-only rule from CLAUDE.md).

See spec body for what each test catches and why this lives at the
structural/token level rather than pixel diff (deferred per §2.3).
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import (
    DASHBOARD_CSS,
    collect,
    render_index,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MOCKUP_PATH = REPO_ROOT / "dashboard" / "mockups" / "dashboard-redesign-v3-horizontal.html"


# ─── HTML structure extractor ─────────────────────────────────────────────


class _StructureExtractor(HTMLParser):
    """Walk an HTML document and emit (tag, frozenset(classes), depth) for
    every element. Text nodes and most attributes are ignored — we only
    care about the structural skeleton."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.nodes: list[tuple[str, frozenset[str], int]] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = ""
        for k, v in attrs:
            if k == "class" and v:
                classes = v
                break
        self.nodes.append((tag, frozenset(classes.split()), self._depth))
        self._depth += 1

    def handle_endtag(self, tag: str) -> None:  # noqa: ARG002
        if self._depth > 0:
            self._depth -= 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Self-closing tag — emit but don't descend.
        classes = ""
        for k, v in attrs:
            if k == "class" and v:
                classes = v
                break
        self.nodes.append((tag, frozenset(classes.split()), self._depth))


def _extract_structure(html: str) -> list[tuple[str, frozenset[str], int]]:
    parser = _StructureExtractor()
    parser.feed(html)
    return parser.nodes


def _index_of_first(
    nodes: list[tuple[str, frozenset[str], int]],
    predicate,
    start: int = 0,
) -> int:
    for i in range(start, len(nodes)):
        if predicate(nodes[i]):
            return i
    return -1


def _render_inflight_fixture(tmp_path: Path) -> str:
    """Build a tiny in-flight repo + render the dashboard against it. Same
    pattern as ``test_render_dashboard_spec_0177._bootstrap_repo``."""
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "drafts").mkdir()
    (tmp_path / "handoffs").mkdir()
    (tmp_path / "dashboard" / "events").mkdir(parents=True)

    spec_md = (
        "---\n"
        "kind: dev\n"
        'spec: "0151"\n'
        "slug: fixture\n"
        "title: Fixture in-flight row\n"
        "type: new-feature\n"
        "status: in_progress\n"
        'started_at: "2026-05-22T10:00:00Z"\n'
        "---\nbody\n"
    )
    (specs / "0151-0151-fixture.md").write_text(spec_md)
    (tmp_path / "dashboard" / "events" / "0151.jsonl").write_text(
        '{"ts":"2026-05-22T10:00:00Z","step":"in_progress","data":{}}\n'
    )
    specs_list, drafts_list = collect(tmp_path)
    return render_index(specs_list, drafts_list)


# ─── 2.1 — Structural-parity assertions ──────────────────────────────────


def test_live_dashboard_has_hero_then_counters_then_tab_panels(tmp_path: Path) -> None:
    """Under ``.page`` the live dashboard must surface (in order)
    ``.hero`` → ``.counters`` → ``.tabs`` → ``.tab-panel``. Mirrors the
    mockup's hero → counters → tabs ordering established at
    dashboard-redesign-v3-horizontal.html:518-685."""
    html = _render_inflight_fixture(tmp_path)
    nodes = _extract_structure(html)

    page_idx = _index_of_first(nodes, lambda n: n[0] == "main" and "page" in n[1])
    assert page_idx >= 0, "Missing <main class='page'> in live render"

    hero_idx = _index_of_first(
        nodes,
        lambda n: n[0] == "section" and "hero" in n[1],
        start=page_idx + 1,
    )
    assert hero_idx > page_idx, "Live render missing .hero under .page"

    counters_idx = _index_of_first(
        nodes,
        lambda n: n[0] == "section" and "counters" in n[1],
        start=hero_idx + 1,
    )
    assert counters_idx > hero_idx, (
        "Live render must place .counters AFTER .hero per mockup line 642 "
        "(hero → counters ordering)."
    )

    tabs_idx = _index_of_first(
        nodes,
        lambda n: n[0] == "nav" and "tabs" in n[1],
        start=counters_idx + 1,
    )
    assert tabs_idx > counters_idx, (
        "Live render must place <nav class='tabs'> AFTER .counters per "
        "mockup line 677."
    )

    panel_idx = _index_of_first(
        nodes,
        lambda n: n[0] == "section" and "tab-panel" in n[1],
        start=tabs_idx + 1,
    )
    assert panel_idx > tabs_idx, (
        "Live render must place .tab-panel(s) AFTER <nav class='tabs'>."
    )


def test_live_dashboard_timeline_has_seven_steps_inside_hero(tmp_path: Path) -> None:
    """Spec 0213 §2.1 — `.tl` lives inside `.hero` with exactly 7
    `.tl__step` children (one per honest span: Pre-flight, Read & plan,
    Implement, Test, Ship, Deploy, Handoff). Spec 0177's existing test
    only counts the steps anywhere — this asserts they're nested inside
    `.hero`. The mockup at dashboard/mockups/dashboard-redesign-v3-horizontal.html
    shipped with 11 single-event rows; updated in spec 0213 to the new
    span anatomy."""
    html = _render_inflight_fixture(tmp_path)
    nodes = _extract_structure(html)

    hero_idx = _index_of_first(
        nodes, lambda n: n[0] == "section" and "hero" in n[1]
    )
    assert hero_idx >= 0, ".hero missing from live render"
    hero_depth = nodes[hero_idx][2]

    # Walk forward; stop when we leave the hero (return to depth ≤ hero_depth).
    tl_idx = -1
    steps: list[int] = []
    for i in range(hero_idx + 1, len(nodes)):
        tag, classes, depth = nodes[i]
        if depth <= hero_depth:
            break
        if tag == "div" and "tl" in classes and tl_idx == -1:
            tl_idx = i
        if tl_idx >= 0 and tag == "div" and "tl__step" in classes:
            steps.append(i)

    assert tl_idx > hero_idx, ".tl must live inside .hero (mockup line 560)"
    assert len(steps) == 7, (
        f"Spec 0213 defines exactly 7 .tl__step nodes (one per honest span); "
        f"live render has {len(steps)}. Mismatch fails the structural contract."
    )


def test_live_dashboard_has_five_counters_with_accent_last(tmp_path: Path) -> None:
    """Mockup `.counters` (line 642) carries 5 `.counter` cards with the
    5th flagged `.counter--accent` (line 663). Spec 0177's test counts
    "≥ 5" — this locks the exact count + position."""
    html = _render_inflight_fixture(tmp_path)
    nodes = _extract_structure(html)

    counters_idx = _index_of_first(
        nodes, lambda n: n[0] == "section" and "counters" in n[1]
    )
    assert counters_idx >= 0, ".counters missing"
    counters_depth = nodes[counters_idx][2]

    counter_nodes: list[tuple[str, frozenset[str], int]] = []
    for i in range(counters_idx + 1, len(nodes)):
        tag, classes, depth = nodes[i]
        if depth <= counters_depth:
            break
        if tag == "div" and "counter" in classes and depth == counters_depth + 1:
            counter_nodes.append(nodes[i])

    assert len(counter_nodes) == 5, (
        f"Mockup defines exactly 5 counters under .counters; live render "
        f"has {len(counter_nodes)}."
    )
    accent_idx = next(
        (i for i, n in enumerate(counter_nodes) if "counter--accent" in n[1]),
        -1,
    )
    assert accent_idx == 4, (
        f"Mockup carries .counter--accent on the 5th (final) counter "
        f"(line 663). Live render has it at slot {accent_idx + 1}."
    )


def test_live_dashboard_tab_strip_order(tmp_path: Path) -> None:
    """Mockup tab strip (line 677-682) carries 4 tab buttons in this
    exact order: Now, Spec creation, History, Metrics. The tab labels
    drive both the markup and the URL slug via ``data-tab``."""
    html = _render_inflight_fixture(tmp_path)
    # Parse the rendered HTML and extract data-tab values in document order.
    pattern = re.compile(r'<button[^>]*\bdata-tab="([^"]+)"', re.IGNORECASE)
    tabs = pattern.findall(html)
    # Filter to the four canonical dashboard tabs (in case a future spec
    # introduces other data-tab buttons; only the dashboard nav matters).
    expected = ["now", "spec", "history", "metrics"]
    dashboard_tabs = [t for t in tabs if t in set(expected)]
    assert dashboard_tabs[:4] == expected, (
        f"Mockup tab strip order is {expected}; live render emits "
        f"{dashboard_tabs[:4]}."
    )


# ─── 2.2 — Token-budget assertions ───────────────────────────────────────


_TOKEN_REF_RE = re.compile(r"var\(\s*(--(?:md|p|chart|accent|panel|elev|font|dur|easing|on)[-a-z0-9]*)\s*[,)]")
_HEX_LITERAL_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _extract_style_blocks(html: str) -> str:
    """Pull every <style>…</style> body out of the HTML and concatenate.
    The mockup carries a single big inline <style>; the live render does
    not (CSS is external via DASHBOARD_CSS), but supports either."""
    blocks = re.findall(r"<style[^>]*>(.*?)</style>", html, re.DOTALL | re.IGNORECASE)
    return "\n".join(blocks)


def _tokens_used_in_region(css: str, region_selectors: list[str]) -> set[str]:
    """Extract all token references that appear inside CSS rules whose
    selector contains one of ``region_selectors`` (e.g. ``.tl``, ``.tl__``,
    ``.counter``, ``.chart``)."""
    tokens: set[str] = set()
    # Naive rule-block scan — split on `}` and inspect each block's selector.
    for chunk in css.split("}"):
        if "{" not in chunk:
            continue
        selector, _, body = chunk.partition("{")
        if not any(sel in selector for sel in region_selectors):
            continue
        for m in _TOKEN_REF_RE.finditer(body):
            tokens.add(m.group(1))
    return tokens


# Spec 0197 — empty by design. The mockup was rewritten to use the
# canonical `--p-info` / `--md-font-plain` / `--md-font-data` token
# names so this allowlist no longer needs exceptions. The set is kept
# as a single named extension point — if a future renaming pass
# transiently needs to tolerate shorthand drift (e.g. mid-rename when
# the mockup and live render briefly diverge), the entries land here.
# The intended steady state is empty.
_MOCKUP_SHORTHAND_ALLOWLIST: set[str] = set()


def test_live_css_uses_every_token_the_mockup_uses_for_timeline_counters_charts() -> None:
    """Spec 0184 §2.2 — every `--md-*` / `--p-*` / `--chart-*` token the
    mockup references inside `.tl*` / `.counter*` / `.chart*` rules must
    appear in the live render's CSS for the same region. Token drift
    (e.g. swapping `--md-on-surface` for `--md-on-surface-faint`) would
    break the parity contract."""
    mockup_html = MOCKUP_PATH.read_text()
    mockup_css = _extract_style_blocks(mockup_html)
    region_selectors = [".tl", ".counter", ".chart"]
    mockup_tokens = _tokens_used_in_region(mockup_css, region_selectors)
    live_tokens = _tokens_used_in_region(DASHBOARD_CSS, region_selectors)

    missing = (mockup_tokens - live_tokens) - _MOCKUP_SHORTHAND_ALLOWLIST
    assert not missing, (
        f"{len(missing)} token(s) used in mockup's "
        f"{region_selectors} regions are absent from the live CSS: "
        f"{sorted(missing)}. Either the live render dropped them "
        f"(regression) or the mockup needs updating to match a renamed "
        f"token (workflow risk — flagged in spec 0184 §4)."
    )


def test_live_render_carries_no_hex_color_literals_in_timeline_counters_charts(
    tmp_path: Path,
) -> None:
    """CLAUDE.md tokens-only rule. The live render's HTML output for the
    timeline / counters / chart regions must contain zero hex color
    literals — every color comes from a `var(--…)` token."""
    html = _render_inflight_fixture(tmp_path)
    # Inspect inline styles and svg attributes inside the regions of
    # interest. We scope by extracting each region's HTML slice.
    region_re = re.compile(
        r'(<section[^>]+class="[^"]*(?:hero|counters)[^"]*"[^>]*>.*?</section>)',
        re.DOTALL | re.IGNORECASE,
    )
    region_chunks = region_re.findall(html)
    assert region_chunks, "Expected to find .hero / .counters sections in live render"
    region_html = "\n".join(region_chunks)
    hex_hits = _HEX_LITERAL_RE.findall(region_html)
    assert not hex_hits, (
        f"Found {len(hex_hits)} hex color literal(s) in the live render's "
        f"timeline / counters regions: {hex_hits[:5]}. CLAUDE.md "
        f"'Design system' rule: tokens-only colors. Replace with "
        f"`var(--…)` references."
    )
