"""Tests for prototypes/_canvas/spin-up.py.

Covers the importable surface: registry parsing, DS-section extraction
against a synthetic fixture, and template substitution. The shell-out
behavior (live-html dumping, server start) is owned by the /canvas
skill body and not unit-tested here.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPIN_UP_PATH = REPO_ROOT / "prototypes" / "_canvas" / "spin-up.py"


def _import_spin_up():
    spec = importlib.util.spec_from_file_location("canvas_spin_up", SPIN_UP_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["canvas_spin_up"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def spin_up():
    return _import_spin_up()


def test_load_registry_pretty_panes(spin_up) -> None:
    reg = spin_up.load_registry()
    assert "timeline" in reg
    assert "critique" in reg
    assert reg["timeline"].name == "Timeline pane"
    assert reg["timeline"].live_selector == ".rdvc__pane"
    assert reg["timeline"].port == 6175
    assert reg["timeline"].states == []
    assert reg["critique"].name == "Critique pane"
    assert reg["critique"].live_selector == ".crit2"
    assert reg["critique"].port == 6174
    assert [s.name for s in reg["critique"].states] == ["P0", "P2", "P4", "sigma"]


def test_load_registry_ports_unique(spin_up) -> None:
    reg = spin_up.load_registry()
    ports = [p.port for p in reg.values()]
    assert len(ports) == len(set(ports)), f"duplicate ports in registry: {ports}"


def test_extract_ds_section_simple(spin_up) -> None:
    html = (
        '  <section id="alpha" class="ds-section">\n'
        "    <p>hello</p>\n"
        "  </section>\n"
        '  <section id="beta" class="ds-section">\n'
        "    <p>other</p>\n"
        "  </section>\n"
    )
    out = spin_up.extract_ds_section(html, "alpha")
    assert out.startswith('<section id="alpha"')
    assert out.endswith("</section>")
    assert "<p>hello</p>" in out
    assert "beta" not in out


def test_extract_ds_section_balanced_nested(spin_up) -> None:
    html = (
        '<section id="outer" class="ds-section">\n'
        '  <section class="inner-thing">\n'
        "    <p>nested</p>\n"
        "  </section>\n"
        "  <p>trailing</p>\n"
        "</section>\n"
        '<section id="sibling" class="ds-section"></section>\n'
    )
    out = spin_up.extract_ds_section(html, "outer")
    assert "<p>nested</p>" in out
    assert "<p>trailing</p>" in out
    assert out.count("</section>") == 2
    assert "sibling" not in out


def test_extract_ds_section_missing_raises(spin_up) -> None:
    html = '<section id="alpha" class="ds-section"></section>'
    with pytest.raises(ValueError, match="not found"):
        spin_up.extract_ds_section(html, "ghost")


def test_extract_ds_section_against_real_design_system(spin_up) -> None:
    ds_path = REPO_ROOT / "design-system" / "assets" / "Design System v2.html"
    if not ds_path.exists():
        pytest.skip("Design System v2.html not present in checkout")
    src = ds_path.read_text(encoding="utf-8")
    timeline = spin_up.extract_ds_section(src, "timeline")
    assert timeline.startswith('<section id="timeline"')
    assert 'class="ds-section"' in timeline.split(">", 1)[0]
    assert timeline.rstrip().endswith("</section>")
    # Spot-check: §16 Timeline pane body mentions "Timeline pane" somewhere.
    assert "Timeline pane" in timeline


def test_render_template_substitutes(spin_up) -> None:
    out = spin_up.render_template(
        "hello {{name}} · {{name}} · {{other}}",
        {"name": "world", "other": "x"},
    )
    assert out == "hello world · world · x"


def test_render_template_leaves_unknown_tokens(spin_up) -> None:
    out = spin_up.render_template("{{a}} {{b}}", {"a": "1"})
    assert out == "1 {{b}}"


def test_parse_state_args_orders_per_registry(spin_up, tmp_path: Path) -> None:
    reg = spin_up.load_registry()
    pane = reg["critique"]
    files = {}
    for name in ["P0", "P2", "P4", "sigma"]:
        p = tmp_path / f"{name}.html"
        p.write_text(f"<div data-state='{name}'/>")
        files[name] = p
    # Pass them in reverse order; expect script to reorder per pane.states.
    args = [f"{name}:{files[name]}" for name in ["sigma", "P4", "P2", "P0"]]
    dumps = spin_up.parse_state_args(args, pane)
    assert [n for n, _ in dumps] == ["P0", "P2", "P4", "sigma"]


def test_parse_state_args_missing_states_fail(spin_up, tmp_path: Path) -> None:
    reg = spin_up.load_registry()
    pane = reg["critique"]
    p0 = tmp_path / "p0.html"
    p0.write_text("<div/>")
    with pytest.raises(SystemExit, match="missing live-html-state dumps"):
        spin_up.parse_state_args([f"P0:{p0}"], pane)


def test_build_ds_html_includes_live_section(spin_up, tmp_path: Path) -> None:
    reg = spin_up.load_registry()
    pane = reg["timeline"]
    out = spin_up.build_ds_html(pane, "2026-05-22")
    assert "Timeline pane" in out
    assert 'class="ds-section"' in out
    assert "v2-m3.css" in out


def test_build_mockup_html_uses_pane_fields(spin_up) -> None:
    reg = spin_up.load_registry()
    out = spin_up.build_mockup_html(reg["timeline"], "2026-05-22")
    assert "Timeline pane" in out
    assert "#d4a574" in out
    assert "§16 Timeline pane" in out
    assert "prototypes/timeline-iteration" in out
    assert "1280" in out


def test_build_live_html_single_state_no_phase_tabs(spin_up) -> None:
    reg = spin_up.load_registry()
    pane = reg["timeline"]
    dumps = [("default", "<div class='rdvc__pane'>x</div>")]
    out = spin_up.build_live_html(pane, dumps, "anchor-x", "2026-05-22")
    assert "anchor-x" in out
    assert "<div class='rdvc__pane'>x</div>" in out
    assert 'class="ps-tab' not in out


def test_build_live_html_multi_state_renders_tabs(spin_up) -> None:
    reg = spin_up.load_registry()
    pane = reg["critique"]
    dumps = [
        ("P0", "<div data-phase='P0'/>"),
        ("P2", "<div data-phase='P2'/>"),
        ("P4", "<div data-phase='P4'/>"),
        ("sigma", "<div data-phase='sigma'/>"),
    ]
    out = spin_up.build_live_html(pane, dumps, "anchor-y", "2026-05-22")
    assert "P0" in out and "P2" in out and "P4" in out and "sigma" in out
    assert 'class="ps-tab' in out
    assert out.count('class="phase-state') == 4
