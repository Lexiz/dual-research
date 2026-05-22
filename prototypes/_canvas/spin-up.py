"""Scaffold a pane-iteration workshop from prototypes/_canvas/registry.yml.

This is the workhorse behind ``/canvas <pane>``. See spec 0170 for the
contract; in short: read the registry entry for ``<pane>``, take the
verbatim live-HTML dumps the caller pre-captured, extract the matching
``<section id="…" class="ds-section">`` blocks from
``design-system/assets/Design System v2.html``, render the three
templates in ``prototypes/_canvas/templates/``, and write the workshop
under ``prototypes/<pane>-iteration/``.

The script does **not** drive a headless browser or start a workshop
preview server — both are MCP-level operations that the ``/canvas``
skill body performs in Claude's tool layer. The split (script does
file generation; skill does headless-browser interactions) keeps this
file dep-free beyond ``pyyaml`` and lets the skill compose pre-dumped
live HTML into the script via ``--live-html-file`` /
``--live-html-state``.

Idempotent: re-running refreshes ``live.html`` + ``ds.html`` (always
canonical snapshots) but preserves ``proposed.html`` and ``NOTES.md``
unless ``--force-overwrite-proposed`` is passed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "prototypes" / "_canvas" / "registry.yml"
TEMPLATES_DIR = REPO_ROOT / "prototypes" / "_canvas" / "templates"
DS_HTML_PATH = REPO_ROOT / "design-system" / "assets" / "Design System v2.html"


@dataclass
class PaneState:
    name: str
    click: str | None


@dataclass
class PaneEntry:
    key: str
    name: str
    description: str
    live_url: str
    live_selector: str
    ds_sections: list[str]
    ds_label: str
    port: int
    accent: str
    states: list[PaneState]
    initial_note: str
    live_css: list[str]
    ds_css: list[str]
    default_anchor_run: str

    @property
    def output_dir_name(self) -> str:
        return f"{self.key}-iteration"

    @property
    def output_dir(self) -> Path:
        return REPO_ROOT / "prototypes" / self.output_dir_name


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, PaneEntry]:
    """Parse registry.yml into a dict of pane key → PaneEntry."""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    raw_panes = data.get("panes") or {}
    entries: dict[str, PaneEntry] = {}
    for key, raw in raw_panes.items():
        states_raw = raw.get("states") or []
        states = [PaneState(name=s["name"], click=s.get("click")) for s in states_raw]
        entries[key] = PaneEntry(
            key=key,
            name=raw["name"],
            description=raw.get("description", ""),
            live_url=raw["live_url"],
            live_selector=raw["live_selector"],
            ds_sections=list(raw.get("ds_sections") or []),
            ds_label=raw.get("ds_label", ""),
            port=int(raw["port"]),
            accent=raw.get("accent", "#7cc4b8"),
            states=states,
            initial_note=raw.get("initial_note", "iter 1"),
            live_css=list(raw.get("live_css") or []),
            ds_css=list(raw.get("ds_css") or []),
            default_anchor_run=raw.get("default_anchor_run", ""),
        )
    return entries


_SECTION_OPEN = re.compile(r"<section\b[^>]*>")
_SECTION_CLOSE = re.compile(r"</section\s*>")


def extract_ds_section(html: str, section_id: str) -> str:
    """Return the verbatim ``<section id="X" class="ds-section">…</section>``.

    Balanced-tag match: the section may contain nested ``<section>`` elements
    (e.g. ``id="how"`` wraps ``<section class="hiw-sec">``), so we count
    opens vs. closes from the start tag and return when depth returns to 0.
    """
    start_pat = re.compile(
        r'<section\s+id="' + re.escape(section_id) + r'"[^>]*class="[^"]*\bds-section\b[^"]*"[^>]*>'
    )
    m = start_pat.search(html)
    if not m:
        raise ValueError(f"DS section id={section_id!r} not found in {DS_HTML_PATH}")
    start = m.start()
    depth = 1
    pos = m.end()
    while pos < len(html) and depth > 0:
        next_open = _SECTION_OPEN.search(html, pos)
        next_close = _SECTION_CLOSE.search(html, pos)
        if next_close is None:
            break
        if next_open is not None and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            if depth == 0:
                return html[start : next_close.end()]
            pos = next_close.end()
    raise ValueError(f"DS section id={section_id!r} closing tag not found")


def render_template(tmpl: str, substitutions: dict[str, str]) -> str:
    """Replace ``{{key}}`` tokens in ``tmpl`` with values from ``substitutions``.

    Simple string-replace; no escaping. Substitution values are inlined verbatim,
    so callers must pre-escape if a value could contain ``{{...}}``.
    """
    out = tmpl
    for k, v in substitutions.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def build_live_html(pane: PaneEntry, dumps: list[tuple[str, str]], anchor_run: str, today: str) -> str:
    """Wrap pre-captured live outerHTML dumps in the canonical live.html shell.

    ``dumps`` is a list of ``(state_name, html)`` pairs. Single-state panes
    pass one entry with state_name="" (or "default"). Multi-state panes pass
    one entry per registry state.
    """
    css_links = "\n".join(
        f'<link rel="stylesheet" href="{path}" />' for path in pane.live_css
    )
    state_sections: list[str] = []
    tab_buttons: list[str] = []
    multi = len(dumps) > 1
    for idx, (state_name, html) in enumerate(dumps):
        active = idx == 0
        hidden_attr = "" if active else " hidden"
        state_sections.append(
            f'<section class="phase-state{"" if not active else " is-active"}" data-state="{state_name}"{hidden_attr}>\n{html}\n</section>'
        )
        if multi:
            tab_buttons.append(
                f'<button type="button" class="ps-tab{"" if not active else " is-active"}" data-target="{state_name}">{state_name}</button>'
            )
    phase_state_tabs = ""
    if multi:
        phase_state_tabs = (
            '<span class="pill" style="display: inline-flex; gap: 4px; padding: 0;">'
            + "".join(tab_buttons)
            + "</span>"
        )
    phase_state_script = (
        "<script>(function(){"
        "var tabs=document.querySelectorAll('.ps-tab');"
        "var states=document.querySelectorAll('.phase-state');"
        "tabs.forEach(function(t){t.addEventListener('click',function(){"
        "var key=t.dataset.target;"
        "tabs.forEach(function(x){x.classList.toggle('is-active',x===t);});"
        "states.forEach(function(s){var on=s.dataset.state===key;s.classList.toggle('is-active',on);if(on){s.removeAttribute('hidden');}else{s.setAttribute('hidden','');}});"
        "});});})();</script>"
        if multi
        else ""
    )
    tmpl = (TEMPLATES_DIR / "live.html.tmpl").read_text(encoding="utf-8")
    return render_template(
        tmpl,
        {
            "pane_name": pane.name,
            "anchor_run": anchor_run,
            "date": today,
            "live_css_links": css_links,
            "phase_state_tabs": phase_state_tabs,
            "live_states": "\n".join(state_sections),
            "phase_state_script": phase_state_script,
        },
    )


def build_ds_html(pane: PaneEntry, today: str) -> str:
    """Concatenate the verbatim DS sections inside the canonical ds.html shell."""
    if not DS_HTML_PATH.exists():
        raise FileNotFoundError(f"DS source missing: {DS_HTML_PATH}")
    src = DS_HTML_PATH.read_text(encoding="utf-8")
    sections = [extract_ds_section(src, sid) for sid in pane.ds_sections]
    css_links = "\n".join(
        f'<link rel="stylesheet" href="{path}" />' for path in pane.ds_css
    )
    tmpl = (TEMPLATES_DIR / "ds.html.tmpl").read_text(encoding="utf-8")
    return render_template(
        tmpl,
        {
            "pane_name": pane.name,
            "ds_label": pane.ds_label,
            "date": today,
            "ds_css_links": css_links,
            "ds_sections": "\n".join(sections),
        },
    )


def build_mockup_html(pane: PaneEntry, today: str) -> str:
    tmpl = (TEMPLATES_DIR / "mockup.html.tmpl").read_text(encoding="utf-8")
    return render_template(
        tmpl,
        {
            "pane_name": pane.name,
            "pane_brand": pane.key,
            "output_dir": pane.output_dir_name,
            "ds_label": pane.ds_label,
            "accent": pane.accent,
            "initial_note": pane.initial_note,
            "narrow_width_px": "1280",
            "wide_width_px": "1920",
            "date": today,
        },
    )


def build_proposed_html(pane: PaneEntry, dumps: list[tuple[str, str]], anchor_run: str) -> str:
    css_links = "\n".join(
        f'<link rel="stylesheet" href="{path}" />' for path in pane.live_css
    )
    state_sections: list[str] = []
    multi = len(dumps) > 1
    for idx, (state_name, html) in enumerate(dumps):
        active = idx == 0
        hidden_attr = "" if active else " hidden"
        state_sections.append(
            f'<section class="phase-state{"" if not active else " is-active"}" data-state="{state_name}"{hidden_attr}>\n{html}\n</section>'
        )
    phase_state_script = (
        "<script>(function(){"
        "var states=document.querySelectorAll('.phase-state');"
        "if(states.length<=1)return;"
        "var bar=document.createElement('div');"
        "bar.style.cssText='position:sticky;top:0;z-index:11;background:var(--md-surface-container,#14171c);border-bottom:1px solid var(--md-outline-hair,#1c1f24);padding:6px 16px;display:flex;gap:6px;font-family:var(--md-font-data,ui-monospace,SF Mono,monospace);font-size:11px;';"
        "states.forEach(function(s){"
        "var b=document.createElement('button');"
        "b.textContent=s.dataset.state;"
        "b.dataset.target=s.dataset.state;"
        "b.style.cssText='background:transparent;border:1px solid var(--md-outline-hair);color:var(--md-on-surface-variant);padding:3px 10px;border-radius:999px;cursor:pointer;font:inherit;';"
        "if(s.classList.contains('is-active')){b.style.background='var(--md-surface-container-high)';b.style.color='var(--md-on-surface)';}"
        "b.addEventListener('click',function(){"
        "states.forEach(function(x){var on=x.dataset.state===b.dataset.target;x.classList.toggle('is-active',on);if(on){x.removeAttribute('hidden');}else{x.setAttribute('hidden','');}});"
        "bar.querySelectorAll('button').forEach(function(y){var on=y===b;y.style.background=on?'var(--md-surface-container-high)':'transparent';y.style.color=on?'var(--md-on-surface)':'var(--md-on-surface-variant)';});"
        "});"
        "bar.appendChild(b);"
        "});"
        "var stage=document.querySelector('.wrap__stage');"
        "if(stage)stage.parentNode.insertBefore(bar,stage);"
        "})();</script>"
        if multi
        else ""
    )
    tmpl = (TEMPLATES_DIR / "proposed.html.tmpl").read_text(encoding="utf-8")
    return render_template(
        tmpl,
        {
            "pane_name": pane.name,
            "anchor_run": anchor_run,
            "live_css_links": css_links,
            "live_css_count": str(len(pane.live_css)),
            "live_states": "\n".join(state_sections),
            "phase_state_script": phase_state_script,
        },
    )


def build_notes_md(pane: PaneEntry, anchor_run: str, today: str) -> str:
    tmpl = (TEMPLATES_DIR / "NOTES.md.tmpl").read_text(encoding="utf-8")
    return render_template(
        tmpl,
        {
            "pane_name": pane.name,
            "pane_key": pane.key,
            "output_dir": pane.output_dir_name,
            "anchor_run": anchor_run,
            "live_selector": pane.live_selector,
            "ds_section_list": ", ".join(f"`{s}`" for s in pane.ds_sections),
            "date": today,
        },
    )


def parse_state_args(values: list[str], pane: PaneEntry) -> list[tuple[str, str]]:
    """Parse ``--live-html-state name:path`` args into ``(name, html)`` pairs.

    Order: matches the registry's ``states`` order so the workshop's per-state
    tab order is stable across re-runs. Missing states fail loudly.
    """
    dumps_by_name: dict[str, str] = {}
    for v in values:
        if ":" not in v:
            raise SystemExit(f"--live-html-state expects 'name:path', got: {v!r}")
        name, path = v.split(":", 1)
        p = Path(path)
        if not p.exists():
            raise SystemExit(f"--live-html-state {name}: file not found: {path}")
        dumps_by_name[name] = p.read_text(encoding="utf-8")
    expected = [s.name for s in pane.states]
    missing = [n for n in expected if n not in dumps_by_name]
    if missing:
        raise SystemExit(
            f"missing live-html-state dumps for: {', '.join(missing)} "
            f"(pane {pane.key!r} expects states: {', '.join(expected)})"
        )
    return [(n, dumps_by_name[n]) for n in expected]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prototypes/_canvas/spin-up.py",
        description="Scaffold a pane-iteration workshop from registry.yml.",
    )
    parser.add_argument("pane", help="Pane key from registry.yml (e.g. timeline, critique).")
    parser.add_argument(
        "--anchor-run",
        default=None,
        help="Run id to substitute into live_url. Defaults to the pane's default_anchor_run.",
    )
    parser.add_argument(
        "--live-html-file",
        default=None,
        help="Path to a pre-captured outerHTML dump for single-state panes.",
    )
    parser.add_argument(
        "--live-html-state",
        action="append",
        default=[],
        metavar="NAME:PATH",
        help="Per-state outerHTML dump for multi-state panes. Repeat once per state.",
    )
    parser.add_argument(
        "--force-overwrite-proposed",
        action="store_true",
        help="Overwrite proposed.html + NOTES.md even if they exist (destroys iter work).",
    )
    parser.add_argument(
        "--registry",
        default=str(REGISTRY_PATH),
        help="Path to registry.yml (default: prototypes/_canvas/registry.yml).",
    )
    args = parser.parse_args(argv)

    registry = load_registry(Path(args.registry))
    if args.pane not in registry:
        avail = ", ".join(sorted(registry.keys()))
        print(f"unknown pane {args.pane!r}. Available: {avail}", file=sys.stderr)
        return 2
    pane = registry[args.pane]
    anchor_run = args.anchor_run or pane.default_anchor_run
    today = dt.date.today().isoformat()

    if pane.states:
        dumps = parse_state_args(args.live_html_state, pane)
    else:
        if not args.live_html_file:
            print(
                f"pane {pane.key!r} is single-state; pass --live-html-file <path> to a "
                f"pre-captured document.querySelector('{pane.live_selector}').outerHTML dump.\n"
                f"(The /canvas skill body normally does this via the Claude Preview MCP "
                f"before invoking this script.)",
                file=sys.stderr,
            )
            return 2
        p = Path(args.live_html_file)
        if not p.exists():
            print(f"--live-html-file not found: {args.live_html_file}", file=sys.stderr)
            return 2
        dumps = [("default", p.read_text(encoding="utf-8"))]

    out_dir = pane.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    live_html = build_live_html(pane, dumps, anchor_run, today)
    ds_html = build_ds_html(pane, today)
    mockup_html = build_mockup_html(pane, today)

    (out_dir / "live.html").write_text(live_html, encoding="utf-8")
    (out_dir / "ds.html").write_text(ds_html, encoding="utf-8")
    (out_dir / "mockup.html").write_text(mockup_html, encoding="utf-8")

    proposed_path = out_dir / "proposed.html"
    if not proposed_path.exists() or args.force_overwrite_proposed:
        proposed_path.write_text(build_proposed_html(pane, dumps, anchor_run), encoding="utf-8")
        proposed_written = True
    else:
        proposed_written = False

    notes_path = out_dir / "NOTES.md"
    if not notes_path.exists() or args.force_overwrite_proposed:
        notes_path.write_text(build_notes_md(pane, anchor_run, today), encoding="utf-8")
        notes_written = True
    else:
        notes_written = False

    iter_count = len(
        re.findall(
            r'<style\s+id="iter-\d',
            proposed_path.read_text(encoding="utf-8"),
        )
    )

    workshop_url = f"http://localhost:{pane.port}/prototypes/{pane.output_dir_name}/mockup.html"
    print(f"workshop ready · {pane.name} · {anchor_run}")
    print(f"  dir:        prototypes/{pane.output_dir_name}/")
    print(f"  live.html:  {(out_dir / 'live.html').stat().st_size} bytes ({len(dumps)} state(s))")
    print(f"  ds.html:    {(out_dir / 'ds.html').stat().st_size} bytes ({len(pane.ds_sections)} section(s))")
    print(f"  mockup:     {(out_dir / 'mockup.html').stat().st_size} bytes")
    print(f"  proposed:   {'written (starter)' if proposed_written else 'preserved'}")
    print(f"  NOTES.md:   {'written (starter)' if notes_written else 'preserved'}")
    print(f"  iter style blocks in proposed.html: {iter_count}")
    print(f"  port:       {pane.port}")
    print(f"  url:        {workshop_url}")
    print()
    print("Next: ensure a Claude Preview server is running on the workshop port,")
    print("rooted at the repo root, then open the URL above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
