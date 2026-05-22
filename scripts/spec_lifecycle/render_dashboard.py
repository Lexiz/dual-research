"""Render the dashboard from spec frontmatter + handoff frontmatter + event sidecars.

Output: static HTML at `dashboard/site/` (or `--out` override). Run from CI on
push to `main`; the workflow publishes the output to the `gh-pages` branch.

Usage:

    uv run python scripts/spec_lifecycle/render_dashboard.py \
        --repo-root /Users/alexlisitzky/dual-research --out dashboard/site/
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .frontmatter import parse
from .append_event import read_events


@dataclass
class SpecRow:
    fm: dict[str, Any]
    path: Path
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def number(self) -> str:
        # Filename is canonical: YAML safe_load mangles 0NNN as octal when valid.
        # Filename always has the 4-digit prefix we want.
        return self.path.stem[:4]

    @property
    def status(self) -> str:
        return self.fm.get("status", "")

    @property
    def title(self) -> str:
        return self.fm.get("title", self.path.stem)

    @property
    def type(self) -> str:
        return self.fm.get("type", "—")

    @property
    def cycle_seconds(self) -> int | None:
        started = self.fm.get("started_at") or ""
        deployed = self.fm.get("deployed_at") or ""
        if not (started and deployed):
            return None
        try:
            s = dt.datetime.fromisoformat(started.replace("Z", "+00:00"))
            d = dt.datetime.fromisoformat(deployed.replace("Z", "+00:00"))
            return int((d - s).total_seconds())
        except (ValueError, TypeError):
            return None


@dataclass
class DraftRow:
    fm: dict[str, Any]
    path: Path

    @property
    def draft_id(self) -> str:
        # Filename has zero-padded form; frontmatter may be int-coerced
        import re

        m = re.match(r"^draft-(\d{3})-", self.path.name)
        if m:
            return m.group(1)
        return str(self.fm.get("draft_id", "—"))

    @property
    def title(self) -> str:
        return self.fm.get("title", self.path.stem)

    @property
    def type(self) -> str:
        return self.fm.get("type", "unclassified")


def collect(repo_root: Path) -> tuple[list[SpecRow], list[DraftRow]]:
    specs_dir = repo_root / "specs"
    drafts_dir = specs_dir / "drafts"
    events_dir = repo_root / "dashboard" / "events"

    specs: list[SpecRow] = []
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        if not entry.name[:4].isdigit():
            continue
        fm = parse(entry).frontmatter
        # Note: fm may be empty for older specs without frontmatter — still include them
        spec_id = entry.name[:4]  # canonical: filename, not frontmatter (YAML 0NNN parses inconsistently)
        events = read_events(events_dir, spec_id)
        specs.append(SpecRow(fm=fm, path=entry, events=events))

    drafts: list[DraftRow] = []
    if drafts_dir.exists():
        for entry in sorted(drafts_dir.iterdir()):
            if not entry.is_file() or not entry.name.endswith(".md"):
                continue
            if entry.name == "README.md":
                continue
            fm = parse(entry).frontmatter
            if not fm:
                continue
            drafts.append(DraftRow(fm=fm, path=entry))

    return specs, drafts


def _fmt_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _row(*cells: str) -> str:
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def _escape(value: Any) -> str:
    return html.escape(str(value or ""))


def render_index(specs: list[SpecRow], drafts: list[DraftRow]) -> str:
    in_flight = [s for s in specs if s.status == "in_progress"]
    queued = sorted(
        [s for s in specs if s.status == "queued"],
        key=lambda s: int(s.fm.get("queue_position") or 999),
    )
    deployed = sorted(
        [s for s in specs if s.status == "deployed"],
        key=lambda s: s.fm.get("deployed_at") or "",
        reverse=True,
    )
    failed = [s for s in specs if s.status == "failed"]

    cycle_times = [s.cycle_seconds for s in deployed if s.cycle_seconds]
    avg_cycle = statistics.mean(cycle_times[:10]) if cycle_times else None

    parts: list[str] = []
    parts.append(_html_head("dual-research — spec dashboard"))
    parts.append("<body>")
    parts.append("<header><h1>dual-research — spec dashboard</h1>")
    parts.append(
        '<p class="sub">All data read from spec frontmatter, handoff frontmatter, and '
        "event sidecars under <code>dashboard/events/</code>. Regenerated on every push "
        "to main.</p></header>")

    parts.append('<section><h2>Metrics</h2><div class="metrics">')
    parts.append(_metric("Deployed", str(len(deployed))))
    parts.append(_metric("In flight", str(len(in_flight))))
    parts.append(_metric("Queued", str(len(queued))))
    parts.append(_metric("Drafts", str(len(drafts))))
    parts.append(_metric("Failed", str(len(failed))))
    parts.append(_metric(
        "Avg cycle (last 10)",
        _fmt_duration(int(avg_cycle)) if avg_cycle else "—",
    ))
    parts.append("</div></section>")

    if in_flight:
        parts.append("<section><h2>In flight</h2><table>")
        parts.append("<thead><tr><th>Spec</th><th>Title</th><th>Type</th><th>Started</th></tr></thead><tbody>")
        for s in in_flight:
            parts.append(_row(
                _link_spec(s),
                _escape(s.title),
                _escape(s.type),
                _escape(s.fm.get("started_at")),
            ))
        parts.append("</tbody></table></section>")

    parts.append("<section><h2>Queue</h2>")
    if queued:
        parts.append("<table><thead><tr><th>Position</th><th>Spec</th><th>Title</th><th>Type</th><th>Queued at</th></tr></thead><tbody>")
        for s in queued:
            parts.append(_row(
                _escape(s.fm.get("queue_position")),
                _link_spec(s),
                _escape(s.title),
                _escape(s.type),
                _escape(s.fm.get("queued_at")),
            ))
        parts.append("</tbody></table>")
    else:
        parts.append("<p><em>Queue is empty.</em></p>")
    parts.append("</section>")

    parts.append("<section><h2>Recently shipped</h2>")
    if deployed:
        parts.append("<table><thead><tr><th>Spec</th><th>Title</th><th>Type</th><th>Deployed</th><th>Cycle</th><th>PR</th></tr></thead><tbody>")
        for s in deployed[:15]:
            pr = s.fm.get("pr") or ""
            pr_cell = f'<a href="{_escape(pr)}">PR</a>' if pr else "—"
            parts.append(_row(
                _link_spec(s),
                _escape(s.title),
                _escape(s.type),
                _escape(s.fm.get("deployed_at")),
                _fmt_duration(s.cycle_seconds),
                pr_cell,
            ))
        parts.append("</tbody></table>")
    else:
        parts.append("<p><em>Nothing deployed under the new system yet.</em></p>")
    parts.append("</section>")

    parts.append("<section><h2>Drafts</h2>")
    if drafts:
        parts.append("<table><thead><tr><th>ID</th><th>Title</th><th>Type (guess)</th></tr></thead><tbody>")
        for d in drafts:
            parts.append(_row(
                _escape(d.draft_id),
                _link_draft(d),
                _escape(d.type),
            ))
        parts.append("</tbody></table>")
    else:
        parts.append("<p><em>No drafts.</em></p>")
    parts.append("</section>")

    parts.append("<section><h2>All specs</h2><table>")
    parts.append("<thead><tr><th>Spec</th><th>Title</th><th>Type</th><th>Status</th><th>Version</th></tr></thead><tbody>")
    for s in sorted(specs, key=lambda s: int(s.number or "0"), reverse=True):
        parts.append(_row(
            _link_spec(s),
            _escape(s.title),
            _escape(s.type),
            _escape(s.status),
            _escape(s.fm.get("target_version")),
        ))
    parts.append("</tbody></table></section>")

    parts.append("</body></html>")
    return "\n".join(parts)


def _link_spec(s: SpecRow) -> str:
    return f'<a href="spec-{s.number}.html">{_escape(s.number)}</a>'


def _link_draft(d: DraftRow) -> str:
    return f'<a href="draft-{d.draft_id}.html">{_escape(d.title)}</a>'


def _metric(label: str, value: str) -> str:
    return f'<div class="metric"><div class="value">{_escape(value)}</div><div class="label">{_escape(label)}</div></div>'


def render_spec_page(s: SpecRow) -> str:
    parts: list[str] = []
    parts.append(_html_head(f"Spec {s.number} — {s.title}"))
    parts.append("<body>")
    parts.append('<p><a href="index.html">← back</a></p>')
    parts.append(f"<h1>Spec {_escape(s.number)} — {_escape(s.title)}</h1>")
    parts.append("<section><h2>Frontmatter</h2><table>")
    for k, v in s.fm.items():
        parts.append(_row(_escape(k), _escape(v)))
    parts.append("</table></section>")

    parts.append("<section><h2>Event timeline</h2>")
    if s.events:
        parts.append("<table><thead><tr><th>When</th><th>Step</th><th>Data</th></tr></thead><tbody>")
        for ev in s.events:
            parts.append(_row(
                _escape(ev.get("ts")),
                _escape(ev.get("step")),
                _escape(json.dumps(ev.get("data") or {})),
            ))
        parts.append("</tbody></table>")
    else:
        parts.append("<p><em>No events recorded.</em></p>")
    parts.append("</section>")

    spec_id = s.number
    parts.append("<section><h2>Links</h2><ul>")
    parts.append(
        f'<li><a href="https://github.com/Lexiz/dual-research/blob/main/{_escape(s.path.relative_to(s.path.parent.parent.parent))}">Spec source on GitHub</a></li>'
    )
    pr = s.fm.get("pr")
    if pr:
        parts.append(f'<li><a href="{_escape(pr)}">Pull request</a></li>')
    handover = s.fm.get("handover")
    if handover:
        parts.append(
            f'<li><a href="https://github.com/Lexiz/dual-research/blob/main/{_escape(handover)}">Handover</a></li>'
        )
    parts.append("</ul></section>")
    parts.append("</body></html>")
    return "\n".join(parts)


def render_draft_page(d: DraftRow) -> str:
    parts: list[str] = []
    parts.append(_html_head(f"Draft {d.draft_id} — {d.title}"))
    parts.append("<body>")
    parts.append('<p><a href="index.html">← back</a></p>')
    parts.append(f"<h1>Draft {_escape(d.draft_id)} — {_escape(d.title)}</h1>")
    parts.append("<section><h2>Frontmatter</h2><table>")
    for k, v in d.fm.items():
        parts.append(_row(_escape(k), _escape(v)))
    parts.append("</table></section>")
    parts.append("<section><h2>Source</h2>")
    parts.append(
        f'<p><a href="https://github.com/Lexiz/dual-research/blob/main/specs/drafts/{_escape(d.path.name)}">View on GitHub</a></p>'
    )
    parts.append("</section>")
    parts.append("</body></html>")
    return "\n".join(parts)


def _html_head(title: str) -> str:
    return (
        "<!DOCTYPE html>\n<html lang='en'><head><meta charset='utf-8'>"
        f"<title>{_escape(title)}</title>"
        "<link rel='stylesheet' href='style.css'>"
        "</head>"
    )


STYLE = """\
:root { --bg: #14181d; --panel: #1b2027; --fg: #e6edf3; --muted: #8b949e; --accent: #58a6ff; --border: #2b323a; }
* { box-sizing: border-box; }
body { font: 14px/1.5 system-ui, sans-serif; background: var(--bg); color: var(--fg); margin: 0; padding: 32px 48px; max-width: 1200px; }
header h1 { margin: 0 0 4px; font-size: 22px; }
header .sub { color: var(--muted); margin: 0 0 32px; }
h2 { font-size: 16px; margin: 24px 0 12px; padding-bottom: 4px; border-bottom: 1px solid var(--border); }
section { margin-bottom: 24px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 500; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
.metric { background: var(--panel); padding: 14px 16px; border-radius: 6px; border: 1px solid var(--border); }
.metric .value { font-size: 22px; font-weight: 600; }
.metric .label { color: var(--muted); font-size: 12px; margin-top: 2px; }
code { background: var(--panel); padding: 1px 6px; border-radius: 3px; font-size: 12.5px; }
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", type=Path)
    parser.add_argument("--out", default="dashboard/site", type=Path)
    ns = parser.parse_args(argv)

    repo_root = ns.repo_root.resolve()
    out_dir = (repo_root / ns.out) if not ns.out.is_absolute() else ns.out
    out_dir.mkdir(parents=True, exist_ok=True)

    specs, drafts = collect(repo_root)

    (out_dir / "index.html").write_text(render_index(specs, drafts), encoding="utf-8")
    (out_dir / "style.css").write_text(STYLE, encoding="utf-8")

    for s in specs:
        (out_dir / f"spec-{s.number}.html").write_text(render_spec_page(s), encoding="utf-8")
    for d in drafts:
        (out_dir / f"draft-{d.draft_id}.html").write_text(render_draft_page(d), encoding="utf-8")

    print(f"rendered {len(specs)} specs + {len(drafts)} drafts → {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
