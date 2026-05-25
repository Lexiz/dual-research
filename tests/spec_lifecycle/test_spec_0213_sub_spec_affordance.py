"""Spec 0213 §2.4 + §4 — decimal sub-spec indent + `↳ <parent>` chip.

Two render tests cover the three surfaces that must carry the affordance:
in-flight hero, History list row, per-spec page H1. Two source-pattern
tests cover the JS-side equivalents so first-paint and 5s repaint agree.
"""

from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import (
    DASHBOARD_BOOTSTRAP_JS,
    DASHBOARD_CSS,
    SpecRow,
    _parent_id_for_decimal,
    _render_hero_inflight,
    _render_all_specs,
    _sub_spec_chip,
    _sub_spec_modifier,
    collect,
    render_index,
    render_spec_page,
)
from tests._ui_pattern_helpers import assert_jsx_contains


# ── helpers ────────────────────────────────────────────────────────────────


def _bootstrap_repo(tmp_path: Path) -> Path:
    (tmp_path / "specs" / "drafts").mkdir(parents=True)
    (tmp_path / "handoffs").mkdir()
    (tmp_path / "dashboard" / "events").mkdir(parents=True)
    return tmp_path


def _write_spec(
    root: Path,
    number: str,
    *,
    status: str = "deployed",
    title: str | None = None,
    type_: str = "refactoring",
    started_at: str = "2026-05-22T10:00:00Z",
    deployed_at: str = "2026-05-22T10:30:00Z",
    created: str = "2026-05-20",
) -> None:
    title = title or f"Spec {number} fixture row"
    fname = f"{number}-fixture.md"
    body = (
        "---\n"
        "kind: dev\n"
        f'spec: "{number}"\n'
        f"slug: fixture-{number.replace('.', '-')}\n"
        f"title: {title}\n"
        f"type: {type_}\n"
        f"status: {status}\n"
        f"created: {created}\n"
        f'started_at: "{started_at}"\n'
        f'deployed_at: "{deployed_at}"\n'
        "---\nbody\n"
    )
    (root / "specs" / fname).write_text(body, encoding="utf-8")


# ── pure helpers ───────────────────────────────────────────────────────────


def test_parent_id_for_decimal_recognises_only_decimal_children() -> None:
    assert _parent_id_for_decimal("0211.3") == "0211"
    assert _parent_id_for_decimal("0212.1") == "0212"
    # Plain integer IDs are not sub-specs.
    assert _parent_id_for_decimal("0211") is None
    assert _parent_id_for_decimal("9999") is None
    # Child 0 (e.g. "0211.0") is a malformed sub-spec id — not a child.
    assert _parent_id_for_decimal("0211.0") is None
    # Junk inputs.
    assert _parent_id_for_decimal("") is None
    assert _parent_id_for_decimal("abc") is None
    assert _parent_id_for_decimal("12.34.56") is None


def test_sub_spec_modifier_only_appends_when_decimal() -> None:
    assert _sub_spec_modifier("0211", "qrow qrow--history") == "qrow qrow--history"
    # The modifier is `<bem-root>--sub-spec` — derived from the FIRST class
    # in the base, so the CSS rule `.qrow--sub-spec .qrow__id` covers both
    # the queue-style `.qrow` rows and the history-style
    # `.qrow.qrow--history` rows with a single selector.
    assert _sub_spec_modifier("0211.3", "qrow qrow--history") == (
        "qrow qrow--history qrow--sub-spec"
    )
    assert _sub_spec_modifier("0211.3", "hero__title") == (
        "hero__title hero__title--sub-spec"
    )


def test_sub_spec_chip_renders_for_decimal_child_only() -> None:
    chip = _sub_spec_chip("0211.3")
    assert "chip-sub-spec" in chip
    assert "tone-neutral" in chip and "no-dot" in chip
    assert "↳" in chip
    assert 'href="spec-0211.html"' in chip
    assert _sub_spec_chip("0211") == ""


# ── render-time integration ────────────────────────────────────────────────


def test_history_list_renders_chip_and_indent_for_decimal_child(tmp_path: Path) -> None:
    """A decimal child + its integer parent both in the History grid: the
    child row carries the `qrow--sub-spec` class plus a `↳ 0211` chip
    pointing back at the parent; the parent row is unchanged."""
    root = _bootstrap_repo(tmp_path)
    _write_spec(root, "0211", title="Parent spec")
    _write_spec(root, "0211.3", title="Child spec")
    specs, drafts = collect(root)
    html = _render_all_specs(specs)

    # Parent row: no sub-spec class, no chip.
    parent_row_idx = html.index('href="spec-0211.html">0211</a>')
    # Walk back to the row's opening div.
    parent_row_start = html.rfind('<div class="', 0, parent_row_idx)
    parent_row_open = html[parent_row_start : parent_row_start + 200]
    assert "qrow--sub-spec" not in parent_row_open, (
        f"parent integer row picked up --sub-spec by accident: {parent_row_open!r}"
    )

    # Child row: --sub-spec modifier on the row + chip inside the id cell.
    assert "qrow--sub-spec" in html
    # Chip links back to parent.
    assert 'href="spec-0211.html">0211</a></span>' in html
    assert 'chip-sub-spec' in html


def test_hero_renders_chip_and_indent_for_decimal_in_flight(tmp_path: Path) -> None:
    """An in-flight decimal child renders the hero title with the
    `hero__title--sub-spec` modifier + the `↳ <parent>` chip."""
    import datetime as dt

    root = _bootstrap_repo(tmp_path)
    _write_spec(
        root,
        "0211.3",
        status="in_progress",
        deployed_at="",
    )
    (root / "dashboard" / "events" / "0211.3.jsonl").write_text(
        '{"ts":"2026-05-22T10:00:00Z","step":"cycle_started","data":{}}\n'
        '{"ts":"2026-05-22T10:00:30Z","step":"in_progress","data":{}}\n'
    )
    specs, _drafts = collect(root)
    inflight = next(s for s in specs if s.status == "in_progress")
    now = dt.datetime(2026, 5, 22, 10, 30, 0, tzinfo=dt.timezone.utc)
    html = _render_hero_inflight(inflight, specs, now)

    assert 'class="hero__title hero__title--sub-spec"' in html, (
        f"hero title should carry the --sub-spec modifier; got: {html[:1200]!r}"
    )
    assert 'chip-sub-spec' in html
    # Chip links to the integer parent.
    assert 'href="spec-0211.html">0211</a>' in html


def test_per_spec_page_h1_carries_chip_only_no_indent(tmp_path: Path) -> None:
    """The per-spec page H1 carries the chip but NOT the indent — there's
    no sibling row to indent against (spec 0213 §6 Risks decision)."""
    root = _bootstrap_repo(tmp_path)
    _write_spec(root, "0211.3", title="Child page")
    specs, _drafts = collect(root)
    sub = next(s for s in specs if s.number == "0211.3")
    html = render_spec_page(sub)
    # Chip in the H1.
    assert "<h1>" in html
    h1_open = html.index("<h1>")
    h1_close = html.index("</h1>", h1_open)
    h1 = html[h1_open : h1_close + len("</h1>")]
    assert "chip-sub-spec" in h1
    assert "↳" in h1
    # No indent modifier on the H1 itself.
    assert "h1--sub-spec" not in h1
    assert "hero__title--sub-spec" not in h1


def test_render_index_end_to_end_with_decimal_child(tmp_path: Path) -> None:
    """End-to-end: render_index against a mixed parent/child fixture
    produces history rows with the new chrome and the existing dashboard
    chrome survives."""
    root = _bootstrap_repo(tmp_path)
    _write_spec(root, "0211", title="Parent spec")
    _write_spec(root, "0211.3", title="Child spec")
    specs, drafts = collect(root)
    html = render_index(specs, drafts)
    # New chrome shows up.
    assert "qrow--sub-spec" in html
    assert "chip-sub-spec" in html
    # The History grid header survives.
    assert "qrow--history-header" in html
    # Both rows render with their IDs.
    assert "spec-0211.html" in html
    assert "spec-0211.3.html" in html


# ── source-pattern tests for the JS mirror ────────────────────────────────


def test_bootstrap_js_carries_sub_spec_helpers() -> None:
    """The 5s repaint uses the same `subSpecChip` / `subSpecModifier` so
    first paint and bootstrap repaint emit byte-identical sub-spec chrome."""
    assert_jsx_contains(
        DASHBOARD_BOOTSTRAP_JS, r"function\s+subSpecChip\s*\(",
        msg="DASHBOARD_BOOTSTRAP_JS must define subSpecChip",
    )
    assert_jsx_contains(
        DASHBOARD_BOOTSTRAP_JS, r"function\s+subSpecModifier\s*\(",
        msg="DASHBOARD_BOOTSTRAP_JS must define subSpecModifier",
    )
    # Hero invokes both.
    assert_jsx_contains(
        DASHBOARD_BOOTSTRAP_JS, r"subSpecModifier\(spec\.number,\s*'hero__title'\)",
        msg="bootstrap hero must wrap its title via subSpecModifier",
    )
    # All-specs row invokes both.
    assert_jsx_contains(
        DASHBOARD_BOOTSTRAP_JS, r"subSpecModifier\(s\.number,\s*'qrow qrow--history'\)",
        msg="bootstrap all-specs row must wrap via subSpecModifier",
    )


def test_dashboard_css_carries_sub_spec_padding_rule() -> None:
    """The `.hero__title--sub-spec` and `.qrow--sub-spec .qrow__id`
    selectors must both ship `padding-left: 16px` so the indent shows up
    on both surfaces."""
    assert ".hero__title--sub-spec" in DASHBOARD_CSS
    assert ".qrow--sub-spec .qrow__id" in DASHBOARD_CSS
    assert "padding-left: 16px" in DASHBOARD_CSS
