"""Render the dual-research spec dashboard.

Inputs:
- ``specs/`` — typed spec frontmatter
- ``specs/drafts/`` — parked drafts
- ``handoffs/`` — handoff frontmatter
- ``dashboard/events/*.jsonl`` — per-spec event sidecars

Outputs (under ``--out``, default ``dashboard/site/``):
- ``index.html`` — the dashboard landing page
- ``spec-NNNN.html`` — per-spec frontmatter + event timeline
- ``draft-NNN.html`` — per-draft page
- ``tokens.css`` — copied from ``design-system/assets/styles/tokens-and-primitives.css``
- ``components.css`` — copied from ``design-system/assets/styles/composed-components.css``
- ``dashboard.css`` — page-chrome layout (this file's ``DASHBOARD_CSS``)

CI: ``.github/workflows/dashboard.yml`` runs this on every push to ``main`` and
publishes the output via GitHub Pages.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .append_event import read_events
from .frontmatter import parse
from .stages import STEP_LABELS, StageState, compute_stages, current_stage_label


REPO_URL = "https://github.com/Lexiz/dual-research"
PAGES_URL = "https://lexiz.github.io/dual-research/"

GFONTS_HEAD = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    "family=Roboto+Flex:opsz,wght@8..144,300;8..144,400;8..144,500;8..144,600&"
    'family=Roboto+Serif:opsz,wght@8..144,400;8..144,500&display=swap" rel="stylesheet">'
    '<link href="https://fonts.googleapis.com/icon?family=Material+Symbols+Outlined" rel="stylesheet">'
)


@dataclass
class SpecRow:
    fm: dict[str, Any]
    path: Path
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def number(self) -> str:
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
    def target_version(self) -> str:
        return self.fm.get("target_version", "")

    @property
    def cycle_seconds(self) -> int | None:
        started = self.fm.get("started_at") or ""
        deployed = self.fm.get("deployed_at") or ""
        if not (started and deployed):
            return None
        s = _parse_ts(started)
        d = _parse_ts(deployed)
        if not s or not d:
            return None
        return int((d - s).total_seconds())


@dataclass
class DraftRow:
    fm: dict[str, Any]
    path: Path

    @property
    def draft_id(self) -> str:
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

    @property
    def created(self) -> str:
        return str(self.fm.get("created", "") or self.fm.get("queued_at", ""))


def _parse_ts(raw: str | None) -> dt.datetime | None:
    if not raw:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


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
        spec_id = entry.name[:4]
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


def read_live_version(repo_root: Path) -> str:
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return ""
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        m = re.match(r'^version\s*=\s*"([^"]+)"', line.strip())
        if m:
            return m.group(1)
    return ""


def _humanize_seconds(seconds: int | None) -> str:
    """Render a duration in the largest natural unit pair (s / m s / h m
    / d h / w d). Used in feed, hero elapsed, history Lifetime + Cycle.

    Spec 0177 §2.3 extended the upper end to weeks so lifetimes that
    straddle multi-week gaps (drafts parked, queued specs sitting through
    a weekend) read naturally instead of as "23d" / "31d" lumps.
    """
    if seconds is None or seconds < 0:
        return "—"
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m" if sec == 0 else f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h" if minutes == 0 else f"{hours}h {minutes}m"
    days, hours = divmod(hours, 24)
    if days < 7:
        return f"{days}d" if hours == 0 else f"{days}d {hours}h"
    weeks, days = divmod(days, 7)
    return f"{weeks}w" if days == 0 else f"{weeks}w {days}d"


def _ago(then: dt.datetime | None, now: dt.datetime) -> str:
    if then is None:
        return "—"
    return _humanize_seconds(int((now - then).total_seconds())) + " ago"


def _escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _link_spec(spec_id: str, body: str | None = None) -> str:
    inner = _escape(body) if body is not None else _escape(spec_id)
    return f'<a href="spec-{_escape(spec_id)}.html">{inner}</a>'


def _link_draft(draft_id: str, body: str | None = None) -> str:
    inner = _escape(body) if body is not None else _escape(draft_id)
    return f'<a href="draft-{_escape(draft_id)}.html">{inner}</a>'


# ── Chips ──────────────────────────────────────────────────────────────────

_TYPE_TONE = {
    "new-feature": "info",
    "bug": "err",
    "refactoring": "warn",
    "test": "neutral",
    "breaking": "warn",
    "unclassified": "neutral",
}


def _type_chip(type_: str) -> str:
    tone = _TYPE_TONE.get(type_, "neutral")
    return f'<span class="chip chip-type tone-{tone} no-dot">{_escape(type_ or "—")}</span>'


def _status_chip(status: str) -> str:
    tone = {
        "deployed": "ok",
        "merged": "ok",
        "in_progress": "info",
        "queued": "neutral",
        "failed": "err",
    }.get(status, "neutral")
    return f'<span class="chip tone-{tone}">{_escape(status or "—")}</span>'


# ── Activity feed ──────────────────────────────────────────────────────────

_FEED_STEP_ICON = {
    "queued": ("add_task", "info"),
    "in_progress": ("flag_circle", "neutral"),
    "preflight_ok": ("flag_circle", "neutral"),
    "handoff_read": ("flag_circle", "neutral"),
    "spec_read": ("flag_circle", "neutral"),
    "branched": ("flag_circle", "neutral"),
    "reconcile_complete": ("rule", "ok"),
    "implement_complete": ("rule", "ok"),
    "tests_green": ("task_alt", "ok"),
    "pr_opened": ("merge", "info"),
    "merged": ("merge", "info"),
    "deployed": ("check_circle", "ok"),
    "handoff_written": ("bookmark", "info"),
    "failed": ("error", "err"),
    "reconcile_failed": ("error", "err"),
    "tests_failed": ("error", "err"),
}

_FEED_KICKER = {
    "queued": "queued",
    "in_progress": "in progress",
    "preflight_ok": "pre-flight",
    "handoff_read": "read handoff",
    "spec_read": "read spec",
    "branched": "branched",
    "reconcile_complete": "reconcile",
    "implement_complete": "implement",
    "tests_green": "tests green",
    "pr_opened": "pr opened",
    "merged": "merged",
    "deployed": "deployed",
    "handoff_written": "handoff written",
    "failed": "failed",
    "reconcile_failed": "reconcile failed",
    "tests_failed": "tests failed",
}


def _feed_detail(spec: SpecRow | None, step: str, data: dict[str, Any]) -> str:
    spec_label = _link_spec(spec.number, spec.number) if spec else ""
    title = _escape(spec.title) if spec else ""

    if step == "queued":
        pos = data.get("queue_position") or (spec.fm.get("queue_position") if spec else None)
        extra = f" · position {_escape(pos)}" if pos else ""
        return f"{spec_label} · {title}{extra}"
    if step == "deployed":
        v = data.get("version")
        suffix = f" · v{_escape(v)}" if v else ""
        return f"{spec_label} · {title}{suffix}"
    if step == "merged":
        pr = data.get("pr") or (spec.fm.get("pr") if spec else "")
        if pr:
            num_m = re.search(r"/pull/(\d+)", str(pr))
            label = f"PR #{num_m.group(1)}" if num_m else "PR"
            return (
                f"{spec_label} · "
                f'<a href="{_escape(pr)}">{label}</a> · admin squash'
            )
        return f"{spec_label} · admin squash"
    if step == "pr_opened":
        url = data.get("url") or (spec.fm.get("pr") if spec else "")
        if url:
            return f'{spec_label} · <a href="{_escape(url)}">{_escape(url)}</a>'
        return spec_label
    if step == "branched":
        branch = data.get("branch", "")
        if branch:
            return f"{spec_label} · branch <code>{_escape(branch)}</code>"
        return spec_label
    if step == "reconcile_complete":
        verdict = data.get("verdict", "clean")
        mech = data.get("mechanical", 0)
        return f"{spec_label} · {_escape(verdict)} · {_escape(mech)} patches"
    if step == "tests_green":
        passed = data.get("passed")
        if passed is not None:
            return f"{spec_label} · {_escape(passed)} passed"
        return f"{spec_label} · all green"
    if step == "handoff_written":
        path = data.get("path", "")
        return f"{spec_label} · {_escape(path)}" if path else spec_label
    if step == "handoff_read":
        return f"{spec_label} · prior handoff read"
    if step == "spec_read":
        return f"{spec_label} · spec parsed"
    if step == "preflight_ok":
        return f"{spec_label} · pre-flight clean"
    if step == "in_progress":
        return f"{spec_label} · {title}"
    if step in {"failed", "reconcile_failed", "tests_failed"}:
        reason = data.get("reason", "")
        return f"{spec_label} · {_escape(reason)}" if reason else spec_label
    if step == "implement_complete":
        commits = data.get("commits")
        if commits is not None:
            return f"{spec_label} · {_escape(commits)} commits"
        return spec_label
    return spec_label


# ── HTML head ──────────────────────────────────────────────────────────────


def _html_head(title: str) -> str:
    # Spec 0160 — dropped the 60s <meta http-equiv="refresh"> (and the JS-side
    # refresh per spec 0156 §2.2). `dashboard-bootstrap.js` now polls
    # `/api/data` every 15s for live data; `dashboard-live.js` continues to
    # tick the per-second stage-elapsed display from data attributes the
    # bootstrap script writes.
    # Spec 0169 §2.7 — inline <script> that reads localStorage for the saved
    # theme preference and writes data-theme on <html> BEFORE the body
    # paints. Prevents theme flash on first paint. Kept inline + tiny
    # (5 lines compressed) so it never blocks anything; the deferred
    # bootstrap script handles everything else.
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\" data-theme=\"light\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{_escape(title)}</title>"
        + _render_theme_init_script()
        + GFONTS_HEAD
        + '<link rel="stylesheet" href="tokens.css">'
        + '<link rel="stylesheet" href="components.css">'
        + '<link rel="stylesheet" href="dashboard.css">'
        + '<script src="dashboard-bootstrap.js" defer></script>'
        + '<script src="dashboard-live.js" defer></script>'
        + "</head>"
    )


# ── Hero ───────────────────────────────────────────────────────────────────


def _render_hero_idle(specs: list[SpecRow], queued: list[SpecRow], drafts: list[DraftRow], now: dt.datetime) -> str:
    deployed = sorted(
        [s for s in specs if s.status == "deployed"],
        key=lambda s: s.fm.get("deployed_at") or "",
        reverse=True,
    )
    last_deploy = deployed[0] if deployed else None
    last_deploy_ts = _parse_ts(last_deploy.fm.get("deployed_at")) if last_deploy else None
    ago = _ago(last_deploy_ts, now)
    big = ago.replace(" ago", "") if last_deploy else "—"
    last_label = f"last deploy · {last_deploy.number}" if last_deploy else "no deploys yet"

    return (
        '<section class="hero hero--idle" aria-label="Queue status">'
        '<div class="hero__icon"><span class="material-symbols-outlined">pause_circle</span></div>'
        '<div class="hero__body">'
        '<div class="hero__kicker">Queue · idle</div>'
        '<div class="hero__title">Nothing in flight. '
        '<span class="hero__hint">Run <code>/dev-next</code> in your queue session to start the next spec.</span>'
        '</div>'
        '<div class="hero__row">'
        f'<span class="chip tone-neutral">0 in flight</span>'
        f'<span class="chip tone-info">{len(queued)} queued</span>'
        f'<span class="chip tone-ok">last shipped {_escape(ago)}</span>'
        '</div>'
        '</div>'
        '<div class="hero__right">'
        f'<div class="hero__big">{_escape(big)}<small> ago</small></div>'
        f'<div class="hero__lbl">{_escape(last_label)}</div>'
        '</div>'
        '</section>'
    )


def _render_stage_node(stage: StageState) -> str:
    """Spec 0177 §2.2 — one node in the horizontal stage timeline.

    The status-derived class (`tl__step--done` / `--curr` / `--queued` /
    `--fail`) drives the node colour and glyph from CSS; this function
    only emits structure. The `data-stage-started-at` attribute that
    powers the live ticker (spec 0156 §2.3) now sits on the current
    node's `.tl__dur` cell — dashboard-live.js's query selector is
    unchanged so the per-second tick still finds it.
    """
    dur = _humanize_seconds(stage.duration_seconds) if stage.duration_seconds is not None else "—"
    dur_attrs = ""
    if stage.status == "curr" and stage.started_at is not None:
        dur_attrs = f' data-stage-started-at="{_escape(stage.started_at.isoformat())}"'
    return (
        f'<div class="tl__step tl__step--{stage.status}">'
        f'<div class="tl__node"></div>'
        f'<div class="tl__lbl">{_escape(stage.name)}</div>'
        f'<div class="tl__dur"{dur_attrs}>{_escape(dur)}</div>'
        f'</div>'
    )


def _render_hero_inflight(spec: SpecRow, all_specs: list[SpecRow], now: dt.datetime) -> str:
    failure_step = spec.fm.get("failure_step") or None
    states, _unknown = compute_stages(spec.number, spec.events, failure_step=failure_step, now=now)
    label = current_stage_label(states)
    step_label = (
        f"In flight · step {label[0]} of {len(states)} — {label[1].lower()}"
        if label
        else "In flight"
    )

    # Spec 0163 §2.3 — the "currently: <step>" tag mirrors the most recent
    # event. With branch-phase events now streaming live to main, this tag
    # changes throughout implementation/test/deploy instead of being frozen
    # at `in_progress` until merge.
    latest_event = spec.events[-1] if spec.events else None
    latest_step = (latest_event or {}).get("step", "") or ""
    latest_event_ts = (latest_event or {}).get("ts", "") or ""
    current_step_label = STEP_LABELS.get(latest_step, latest_step.replace("_", " "))

    # Cycle anchor preference for the elapsed display (spec 0156): the
    # `cycle_started` event (emitted in /dev-next step 1) is the canonical
    # "agent began work" marker. Fall back to frontmatter started_at for
    # legacy specs that pre-date it.
    cycle_started_ev = next(
        (e for e in spec.events if e.get("step") == "cycle_started"), None
    )
    cycle_started = (
        _parse_ts(cycle_started_ev.get("ts")) if cycle_started_ev else None
    ) or _parse_ts(spec.fm.get("started_at"))
    elapsed_seconds = (
        int((now - cycle_started).total_seconds()) if cycle_started else None
    )
    elapsed = _humanize_seconds(elapsed_seconds) if elapsed_seconds is not None else "—"

    cycle_times = [s.cycle_seconds for s in all_specs if s.status == "deployed" and s.cycle_seconds]
    eta_str = "—"
    if cycle_times and elapsed_seconds is not None:
        avg = int(statistics.mean(cycle_times[:10]))
        remaining = avg - elapsed_seconds
        if remaining > 0:
            eta_str = f"ETA {_humanize_seconds(remaining)}"

    chips: list[str] = [_type_chip(spec.type)]
    branch = spec.fm.get("branch")
    if not branch:
        # The cycle keeps the branch name conventional; derive from spec+slug.
        slug = spec.fm.get("slug") or ""
        if slug:
            branch = f"spec/{spec.number}-{slug}"
    if branch:
        chips.append(
            f'<span class="chip tone-neutral">branch · <code>{_escape(branch)}</code></span>'
        )
    # Last reconcile event note.
    reconcile_ev = next((e for e in reversed(spec.events) if e.get("step") == "reconcile_complete"), None)
    if reconcile_ev:
        verdict = (reconcile_ev.get("data") or {}).get("verdict", "clean")
        mech = (reconcile_ev.get("data") or {}).get("mechanical", 0)
        chips.append(f'<span class="chip tone-ok">{_escape(verdict)} · {_escape(mech)} patches</span>')

    # Spec 0163 §2.3 — "currently: <step>" reflects whatever the latest event is.
    if current_step_label:
        chips.append(
            f'<span class="chip tone-info">currently · {_escape(current_step_label)}</span>'
        )
    # Spec 0163 §2.4 — staleness chip, ticked by dashboard-live.js. Server-rendered
    # tone matches what the JS will compute at first paint (avoids a flash).
    if latest_event_ts:
        stale_seconds = _staleness_seconds(latest_event_ts, now)
        stale_tone = _staleness_tone(stale_seconds)
        chips.append(
            f'<span class="chip {stale_tone}" data-last-event-at="{_escape(latest_event_ts)}">'
            f'last event {_escape(_humanize_seconds(stale_seconds) if stale_seconds is not None else "—")} ago'
            f'</span>'
        )

    # Spec 0177 §2.2 — horizontal timeline replaces the vertical
    # `<ol class="stages">`. Two rails sit behind the nodes; the
    # ok-coloured `tl__rail-done` overlay's width is (done_count / total)
    # of the row minus the 28px node padding so the rail visually ends
    # under the last completed node.
    total = len(states) or 1
    done_count = sum(1 for s in states if s.status == "done")
    rail_done_pct = max(0.0, min(100.0, (done_count / total) * 100.0))
    rail_done_style = (
        f'style="width: calc(({done_count}/{total}) * (100% - 28px));"'
        if done_count
        else 'style="width: 0;"'
    )
    stage_nodes = "".join(_render_stage_node(s) for s in states)
    rail_done = f'<div class="tl__rail-done" {rail_done_style}></div>' if done_count else ''
    _ = rail_done_pct  # currently unused; kept for future inline label hover

    return (
        f'<section class="hero hero--inflight" aria-label="Queue in flight" data-current-step="{_escape(latest_step)}">'
        '<div class="hero__top">'
        '<div class="hero__icon"><span class="material-symbols-outlined">play_circle</span></div>'
        '<div class="hero__body">'
        f'<div class="hero__kicker">{_escape(step_label)}</div>'
        f'<div class="hero__title">{_link_spec(spec.number, f"Spec {spec.number} — {spec.title}")}</div>'
        f'<div class="hero__row">{"".join(chips)}</div>'
        '</div>'
        '<div class="hero__right">'
        # The cycle-started attribute powers the live ticker (spec 0156 §2.3);
        # dashboard-live.js rewrites the text every second using Date.now().
        f'<div class="hero__big" data-cycle-started-at="{_escape(cycle_started.isoformat()) if cycle_started else ""}">{_escape(elapsed)}</div>'
        f'<div class="hero__lbl">elapsed · {_escape(eta_str)}</div>'
        '</div>'
        '</div>'
        '<div class="hero__divider"></div>'
        '<div class="tl" aria-label="Cycle stages">'
        '<div class="tl__rail"></div>'
        f'{rail_done}'
        f'<div class="tl__steps">{stage_nodes}</div>'
        '</div>'
        '</section>'
    )


# Spec 0163 §2.4 — staleness thresholds. The DS uses tone-warn / tone-err
# (not the tone-warning / tone-danger names the spec body sketched, which
# aren't in design-system/assets/styles/composed-components.css).
_STALE_WARN_SECONDS = 30
_STALE_DANGER_SECONDS = 120


def _staleness_seconds(latest_event_ts: str, now: dt.datetime) -> int | None:
    ts = _parse_ts(latest_event_ts)
    if ts is None:
        return None
    return max(0, int((now - ts).total_seconds()))


def _staleness_tone(seconds: int | None) -> str:
    if seconds is None:
        return "chip-stale tone-neutral"
    if seconds < _STALE_WARN_SECONDS:
        return "chip-stale tone-ok"
    if seconds < _STALE_DANGER_SECONDS:
        return "chip-stale tone-warn"
    return "chip-stale tone-err"


# ── Pipeline strip ─────────────────────────────────────────────────────────


def _render_pipeline(specs: list[SpecRow], drafts: list[DraftRow], now: dt.datetime) -> str:
    counts: dict[str, int] = {
        "drafts": len(drafts),
        "queued": sum(1 for s in specs if s.status == "queued"),
        "inflight": sum(1 for s in specs if s.status == "in_progress"),
        "merged_today": 0,
        "deployed": sum(1 for s in specs if s.status == "deployed"),
    }
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for s in specs:
        m = _parse_ts(s.fm.get("merged_at"))
        if m and m >= today_start:
            counts["merged_today"] += 1

    max_count = max(counts.values()) or 1

    def col(key: str, label: str, css: str) -> str:
        n = counts[key]
        zero = " is-zero" if n == 0 else ""
        width = int((n / max_count) * 100)
        return (
            '<div class="pipe__col">'
            f'<div class="pipe__lbl">{_escape(label)}</div>'
            f'<div class="pipe__num{zero}">{n}</div>'
            f'<div class="pipe__bar pipe__bar--{css}" style="width: {width}%"></div>'
            '</div>'
        )

    return (
        '<section class="pipe" aria-label="Pipeline">'
        + col("drafts", "Drafts", "draft")
        + col("queued", "Queued", "queued")
        + col("inflight", "In progress", "inflight")
        + col("merged_today", "Merged today", "merged")
        + col("deployed", "Deployed (all)", "deployed")
        + '</section>'
    )


# ── Metrics row ────────────────────────────────────────────────────────────


# Spec 0177 §2.4.3 — stage groups for the stacked-bar mean-durations
# chart. We collapse the 11 raw stages into 7 buckets so the bar reads
# at a glance. The order matches the chart legend in the mockup.
_STAGE_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    # (legend label, chart-token, list of "from_step → to_step" pairs that map into this bucket)
    ("Pre-flight", "chart-grey",   ("cycle_started→preflight_ok",)),
    ("Read & plan", "chart-mint",  ("preflight_ok→handoff_read", "handoff_read→spec_read", "spec_read→planning_started")),
    ("Reconcile",   "chart-yellow",("planning_started→reconcile_complete", "spec_read→reconcile_complete")),
    ("Implement",   "chart-blue",  ("reconcile_complete→implement_complete", "branched→implement_complete", "in_progress→implement_complete")),
    ("Tests",       "chart-green", ("implement_complete→tests_green", "tests_started→tests_green")),
    ("PR + merge",  "chart-purple",("tests_green→pr_opened", "pr_opened→merged")),
    ("Deploy",      "chart-peach", ("merged→deployed", "deploy_started→deployed", "deployed→deploy_health_check_ok")),
)


def _compute_stage_durations(events: list[dict[str, Any]]) -> dict[str, int]:
    """For a single spec's event log, compute seconds spent in each named
    stage bucket from STAGE_GROUPS. Stages that didn't fire return 0.

    The algorithm walks each ``from_step → to_step`` pair in the bucket
    and uses the first matching pair where both events are present. If a
    spec took different shortcuts through the pipeline (e.g. a refactor
    that skipped Tests via xfail), the bucket is 0 for that spec — the
    mean across many specs averages this out.
    """
    by_step: dict[str, dt.datetime] = {}
    for ev in events:
        step = ev.get("step", "")
        ts = _parse_ts(ev.get("ts"))
        if step and ts and step not in by_step:
            by_step[step] = ts
    out: dict[str, int] = {label: 0 for label, _t, _p in _STAGE_GROUPS}
    for label, _token, pairs in _STAGE_GROUPS:
        for pair in pairs:
            frm, to = pair.split("→")
            if frm in by_step and to in by_step:
                delta = int((by_step[to] - by_step[frm]).total_seconds())
                if delta > 0:
                    out[label] = delta
                    break
    return out


def _iso_week_key(d: dt.datetime) -> tuple[int, int]:
    """ISO year + ISO week, used to bucket deployed specs into weekly bars."""
    iso = d.isocalendar()
    return (iso[0], iso[1])


def _render_metrics(specs: list[SpecRow], now: dt.datetime) -> str:
    """Spec 0177 §2.4 — populate the Metrics tab.

    Seven sub-sections, all inline SVG (no chart libraries):
      §2.4.1 — three top callouts (WoW cycle delta, dominant stage, reconcile drift)
      §2.4.2 — cycle-time line chart over the last 22 deployed cycles
      §2.4.3 — stage-breakdown stacked bar (mean across last 10 cycles)
      §2.4.4 — throughput per ISO week (last 8 weeks)
      §2.4.5 — by-type horizontal bars (last 30 days)
      §2.4.6 — success-rate donut (last 30 days)
      §2.4.7 — authoring funnel (drafts → queued → in-flight → deployed)
    """
    deployed = sorted(
        [s for s in specs if s.status == "deployed"],
        key=lambda s: s.fm.get("deployed_at") or "",
        reverse=True,
    )
    cycle_times = [s.cycle_seconds for s in deployed if s.cycle_seconds]

    # ─── §2.4.1: callouts ────────────────────────────────────────────
    week_ago = now - dt.timedelta(days=7)
    fortnight_ago = now - dt.timedelta(days=14)
    month_ago = now - dt.timedelta(days=30)

    def _deployed_between(start: dt.datetime, end: dt.datetime) -> list[SpecRow]:
        out = []
        for s in deployed:
            t = _parse_ts(s.fm.get("deployed_at"))
            if t and start <= t < end and s.cycle_seconds:
                out.append(s)
        return out

    last_week = _deployed_between(week_ago, now)
    prior_week = _deployed_between(fortnight_ago, week_ago)

    if last_week and prior_week:
        mean_last = statistics.mean([s.cycle_seconds for s in last_week])
        mean_prior = statistics.mean([s.cycle_seconds for s in prior_week])
        delta_pct = (mean_last - mean_prior) / mean_prior * 100 if mean_prior else 0
        if delta_pct <= 0:
            wow_label = "Cycle time improving"
            wow_val = f"{delta_pct:+.0f}% week-over-week"
            wow_sub = (
                f"Last 7d: avg {_humanize_seconds(int(mean_last))}, vs "
                f"{_humanize_seconds(int(mean_prior))} the week prior."
            )
            wow_tone = "callout--ok"
            wow_icon = "↓"
        else:
            wow_label = "Cycle time slowing"
            wow_val = f"+{delta_pct:.0f}% week-over-week"
            wow_sub = (
                f"Last 7d: avg {_humanize_seconds(int(mean_last))}, vs "
                f"{_humanize_seconds(int(mean_prior))} the week prior."
            )
            wow_tone = "callout--warn"
            wow_icon = "↑"
    else:
        wow_label = "Cycle time WoW"
        wow_val = "—"
        wow_sub = "Needs ≥ 1 deployed cycle in each of the last two ISO weeks."
        wow_tone = ""
        wow_icon = "⏱"

    # "Where time goes" — largest mean stage across last 10 deployed cycles.
    last10 = deployed[:10]
    mean_per_group: dict[str, float] = {label: 0.0 for label, _t, _p in _STAGE_GROUPS}
    if last10:
        for s in last10:
            for label, dur in _compute_stage_durations(s.events).items():
                mean_per_group[label] += dur
        for label in mean_per_group:
            mean_per_group[label] = mean_per_group[label] / len(last10)
    total_stage_mean = sum(mean_per_group.values())
    if total_stage_mean:
        top_label, top_secs = max(mean_per_group.items(), key=lambda kv: kv[1])
        share_pct = int(round(top_secs / total_stage_mean * 100))
        where_val = f'{share_pct}% in <em>{_escape(top_label.lower())}</em>'
        # Pick the next two biggest groups for the sub-line.
        ranked = sorted(mean_per_group.items(), key=lambda kv: kv[1], reverse=True)
        rest_bits = [
            f"{label} {_humanize_seconds(int(secs))}"
            for label, secs in ranked[1:3]
            if secs > 0
        ]
        where_sub = (
            f"Mean {top_label.lower()} = {_humanize_seconds(int(top_secs))}. "
            + ("Next: " + ", ".join(rest_bits) + "." if rest_bits else "")
        )
    else:
        where_val = "—"
        where_sub = "Needs ≥ 1 deployed cycle with full timings."

    # Reconcile drift over last 10 deployed cycles.
    reconciled = 0
    needed_fix = 0
    for s in last10:
        rec = next((e for e in s.events if e.get("step") == "reconcile_complete"), None)
        if rec:
            reconciled += 1
            if (rec.get("data") or {}).get("mechanical", 0):
                needed_fix += 1
    if reconciled:
        rec_val = f"{needed_fix} of {reconciled}"
        rec_pct = int(round(needed_fix / reconciled * 100))
        rec_sub = f"{rec_pct}% needed mechanical patches before code landed."
        rec_tone = "callout--warn" if rec_pct >= 30 else ""
    else:
        rec_val = "—"
        rec_sub = "No reconcile events on the last 10 cycles."
        rec_tone = ""

    def _co_classes(extra: str) -> str:
        return f"callout {extra}".strip()

    callout_html = (
        '<div class="callouts">'
        f'<div class="{_co_classes(wow_tone)}">'
        f'<div class="callout__icon">{_escape(wow_icon)}</div>'
        '<div class="callout__body">'
        f'<div class="callout__lbl">{_escape(wow_label)}</div>'
        f'<div class="callout__val">{_escape(wow_val)}</div>'
        f'<div class="callout__sub">{_escape(wow_sub)}</div>'
        '</div></div>'
        '<div class="callout">'
        '<div class="callout__icon">⏱</div>'
        '<div class="callout__body">'
        '<div class="callout__lbl">Where time goes</div>'
        f'<div class="callout__val">{where_val}</div>'
        f'<div class="callout__sub">{_escape(where_sub)}</div>'
        '</div></div>'
        f'<div class="{_co_classes(rec_tone)}">'
        '<div class="callout__icon">!</div>'
        '<div class="callout__body">'
        '<div class="callout__lbl">Reconcile drift</div>'
        f'<div class="callout__val">{_escape(rec_val)}</div>'
        f'<div class="callout__sub">{_escape(rec_sub)}</div>'
        '</div></div>'
        '</div>'
    )

    # ─── §2.4.2: cycle-time line chart + §2.4.3: stage breakdown ─────
    line_html = _render_cycle_time_chart(deployed)
    stage_html = _render_stage_breakdown_chart(mean_per_group, total_stage_mean)

    # ─── §2.4.4 throughput + §2.4.5 by-type + §2.4.6 donut ──────────
    throughput_html = _render_throughput_chart(deployed, now)
    bytype_html = _render_by_type_chart(specs, now)
    donut_html = _render_success_donut(specs, now)

    # ─── §2.4.7: authoring funnel ────────────────────────────────────
    funnel_html = _render_authoring_funnel(specs, now)

    insufficient = ""
    if not cycle_times:
        insufficient = (
            '<div class="metrics-empty"><em>No deployed cycles yet.</em> '
            'Run <code>/dev-next</code> on a queued spec to populate this tab.</div>'
        )

    return (
        f'{insufficient}'
        f'{callout_html}'
        '<div class="charts-grid">'
        f'{line_html}'
        f'{stage_html}'
        '</div>'
        '<div class="charts-grid charts-grid--3">'
        f'{throughput_html}'
        f'{bytype_html}'
        f'{donut_html}'
        '</div>'
        '<div class="sh"><div class="sh__name">Spec authoring funnel</div>'
        '<div class="sh__hint">how ideas reach deploy</div><div class="sh__rule"></div></div>'
        f'{funnel_html}'
    )


def _render_cycle_time_chart(deployed: list[SpecRow]) -> str:
    """Spec 0177 §2.4.2 — last 22 deployed cycles. Two polylines: actual
    cycle time (chart-blue, with dot markers) and rolling-10 mean overlay
    (chart-purple, dashed). Y-axis clipped at 60 minutes; specs > 1h are
    plotted at the top of the chart and annotated in the caption.
    """
    # Oldest-on-the-left for natural reading order.
    series = list(reversed(deployed[:22]))
    cycle_secs = [s.cycle_seconds for s in series if s.cycle_seconds]
    if len(cycle_secs) < 2:
        return (
            '<div class="chart-card">'
            '<div class="chart-card__title">Cycle time over last 22 cycles</div>'
            '<div class="chart-card__sub">Each point is one deployed spec.</div>'
            '<div class="metrics-empty">Needs at least 2 deployed cycles.</div>'
            '</div>'
        )

    cap = 60 * 60  # 60 minutes; outliers render at the cap and are annotated.
    outlier_count = sum(1 for v in cycle_secs if v > cap)
    plotted = [min(v, cap) for v in cycle_secs]
    # Map secs ∈ [0, cap] → y ∈ [180, 20] (inverted, top-padded for x-axis).
    width = 600
    height = 220
    pad_l, pad_r, pad_t, pad_b = 40, 10, 20, 40
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b
    step_x = inner_w / max(1, len(plotted) - 1) if len(plotted) > 1 else inner_w
    def _y(secs: int) -> float:
        return pad_t + inner_h * (1 - (secs / cap))

    actual_pts = " ".join(
        f"{round(pad_l + i * step_x, 1)},{round(_y(v), 1)}"
        for i, v in enumerate(plotted)
    )

    # Rolling-10 mean overlay.
    rolling: list[float] = []
    for i, _v in enumerate(plotted):
        window = plotted[max(0, i - 9) : i + 1]
        rolling.append(statistics.mean(window))
    rolling_pts = " ".join(
        f"{round(pad_l + i * step_x, 1)},{round(_y(int(v)), 1)}"
        for i, v in enumerate(rolling)
    )

    dot_markers = "".join(
        f'<circle cx="{round(pad_l + i * step_x, 1)}" cy="{round(_y(v), 1)}" r="3" />'
        for i, v in enumerate(plotted)
    )

    # X-axis: label every 5th spec id.
    x_labels = []
    for i, s in enumerate(series):
        if i % 5 == 0 or i == len(series) - 1:
            x_labels.append(
                f'<text x="{round(pad_l + i * step_x, 1)}" y="{height - 10}" '
                'text-anchor="middle">'
                f'{_escape(s.number)}</text>'
            )

    outlier_note = ""
    if outlier_count:
        outlier_note = (
            f" Outliers > 1h ({outlier_count}) clipped to the top."
        )

    return (
        '<div class="chart-card">'
        '<div class="chart-card__title">Cycle time over last 22 cycles</div>'
        '<div class="chart-card__sub">'
        f'Each point is one deployed spec. Dashed = rolling-10 mean.{_escape(outlier_note)}'
        '</div>'
        f'<svg class="chart" viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
        'role="img" aria-label="Cycle time line chart">'
        '<g stroke="var(--md-outline-hair)" stroke-width="1">'
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{width - pad_r}" y2="{pad_t}" stroke-dasharray="2,3"/>'
        f'<line x1="{pad_l}" y1="{pad_t + inner_h * 0.25}" x2="{width - pad_r}" y2="{pad_t + inner_h * 0.25}" stroke-dasharray="2,3"/>'
        f'<line x1="{pad_l}" y1="{pad_t + inner_h * 0.5}" x2="{width - pad_r}" y2="{pad_t + inner_h * 0.5}" stroke-dasharray="2,3"/>'
        f'<line x1="{pad_l}" y1="{pad_t + inner_h * 0.75}" x2="{width - pad_r}" y2="{pad_t + inner_h * 0.75}" stroke-dasharray="2,3"/>'
        f'<line x1="{pad_l}" y1="{pad_t + inner_h}" x2="{width - pad_r}" y2="{pad_t + inner_h}" />'
        '</g>'
        '<g fill="var(--md-on-surface-faint)" font-family="var(--md-font-data)" '
        'font-size="10" text-anchor="end">'
        f'<text x="{pad_l - 6}" y="{pad_t + 4}">60m</text>'
        f'<text x="{pad_l - 6}" y="{pad_t + inner_h * 0.25 + 4}">45m</text>'
        f'<text x="{pad_l - 6}" y="{pad_t + inner_h * 0.5 + 4}">30m</text>'
        f'<text x="{pad_l - 6}" y="{pad_t + inner_h * 0.75 + 4}">15m</text>'
        f'<text x="{pad_l - 6}" y="{pad_t + inner_h + 4}">0</text>'
        '</g>'
        f'<polyline fill="none" stroke="var(--chart-purple)" stroke-width="1.5" '
        f'stroke-dasharray="4,4" points="{rolling_pts}" />'
        f'<polyline fill="none" stroke="var(--chart-blue)" stroke-width="2" '
        f'stroke-linejoin="round" points="{actual_pts}" />'
        f'<g fill="var(--chart-blue)">{dot_markers}</g>'
        '<g fill="var(--md-on-surface-faint)" font-family="var(--md-font-data)" '
        'font-size="9" text-anchor="middle">'
        + "".join(x_labels)
        + '</g>'
        '</svg>'
        '<div class="chart-card__legend">'
        '<span><span class="lg__sw" style="background: var(--chart-blue);"></span>Cycle time</span>'
        '<span><span class="lg__sw" style="background: var(--chart-purple);"></span>Rolling-10 mean</span>'
        '</div>'
        '</div>'
    )


def _render_stage_breakdown_chart(
    mean_per_group: dict[str, float], total_stage_mean: float
) -> str:
    """Spec 0177 §2.4.3 — single horizontal stacked bar, mean of last 10
    deployed cycles. Each segment widths proportional to that bucket's
    share of total mean time; legend below names the colours.
    """
    if total_stage_mean <= 0:
        return (
            '<div class="chart-card">'
            '<div class="chart-card__title">Where time goes (mean stage durations)</div>'
            '<div class="chart-card__sub">Stacked, last 10 deployed cycles.</div>'
            '<div class="metrics-empty">Needs ≥ 1 deployed cycle with full timings.</div>'
            '</div>'
        )
    width = 320
    bar_y = 80
    bar_h = 40
    cursor = 0.0
    segments: list[str] = []
    legend_items: list[str] = []
    label_lines: list[str] = []
    for i, (label, token, _pairs) in enumerate(_STAGE_GROUPS):
        secs = mean_per_group.get(label, 0.0)
        if secs <= 0:
            continue
        w = (secs / total_stage_mean) * width
        segments.append(
            f'<rect x="{round(cursor, 1)}" y="{bar_y}" width="{round(w, 1)}" '
            f'height="{bar_h}" fill="var(--{token})" />'
        )
        cursor += w
        x_label = 0 if i < 4 else 160
        y_label = 140 + (i % 4) * 16
        label_lines.append(
            f'<text x="{x_label}" y="{y_label}">'
            f'{_escape(label)} · {_escape(_humanize_seconds(int(secs)))}</text>'
        )
        legend_items.append(
            f'<span><span class="lg__sw" style="background: var(--{token});"></span>{_escape(label)}</span>'
        )
    total_label = _humanize_seconds(int(total_stage_mean))
    return (
        '<div class="chart-card">'
        '<div class="chart-card__title">Where time goes (mean stage durations)</div>'
        f'<div class="chart-card__sub">Stacked, last 10 deployed cycles · total mean = {_escape(total_label)}</div>'
        f'<svg class="chart" viewBox="0 0 {width} 220" preserveAspectRatio="none" '
        'role="img" aria-label="Stage breakdown chart">'
        + "".join(segments)
        + '<g font-family="var(--md-font-plain)" font-size="10" fill="var(--md-on-surface-variant)">'
        + "".join(label_lines)
        + '</g>'
        '</svg>'
        '<div class="chart-card__legend">'
        + "".join(legend_items)
        + '</div>'
        '</div>'
    )


def _render_throughput_chart(deployed: list[SpecRow], now: dt.datetime) -> str:
    """Spec 0177 §2.4.4 — last 8 ISO weeks, count deployed per week.
    Current week shaded with --chart-purple, prior weeks with --chart-blue
    at graduated opacity (0.55 → 0.90).
    """
    # Build week-key list: 7 prior weeks + current.
    weeks: list[tuple[int, int]] = []
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for back in range(7, -1, -1):
        weeks.append(_iso_week_key(base - dt.timedelta(weeks=back)))
    counts: dict[tuple[int, int], int] = {w: 0 for w in weeks}
    for s in deployed:
        t = _parse_ts(s.fm.get("deployed_at"))
        if t is None:
            continue
        key = _iso_week_key(t)
        if key in counts:
            counts[key] += 1
    series = [counts[w] for w in weeks]
    if not any(series):
        return (
            '<div class="chart-card">'
            '<div class="chart-card__title">Throughput · specs deployed per week</div>'
            '<div class="chart-card__sub">last 8 ISO weeks</div>'
            '<div class="metrics-empty">No deployments in the last 8 weeks.</div>'
            '</div>'
        )
    max_count = max(series) or 1
    width = 320
    height = 160
    bar_w = 30
    gap = 10
    left_pad = 10
    bars: list[str] = []
    val_labels: list[str] = []
    week_labels: list[str] = []
    for i, c in enumerate(series):
        x = left_pad + i * (bar_w + gap)
        bar_h = int((c / max_count) * (height - 50)) if c else 0
        y = height - 16 - bar_h
        if i == len(series) - 1:
            # Current week — solid chart-purple.
            fill = 'fill="var(--chart-purple)"'
        else:
            opacity = 0.55 + (i / max(1, len(series) - 1)) * 0.35
            fill = f'fill="var(--chart-blue)" fill-opacity="{opacity:.2f}"'
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" {fill} />'
        )
        val_labels.append(
            f'<text x="{x + bar_w / 2}" y="{y - 4 if c else height - 20}">{c}</text>'
        )
        wk_label = "now" if i == len(series) - 1 else f"w-{len(series) - 1 - i}"
        week_labels.append(
            f'<text x="{x + bar_w / 2}" y="{height - 4}">{_escape(wk_label)}</text>'
        )
    return (
        '<div class="chart-card">'
        '<div class="chart-card__title">Throughput · specs deployed per week</div>'
        '<div class="chart-card__sub">last 8 ISO weeks · current week in purple</div>'
        f'<svg class="chart" viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
        'role="img" aria-label="Throughput bars">'
        + "".join(bars)
        + '<g fill="var(--md-on-surface)" font-family="var(--md-font-data)" '
        'font-size="10" text-anchor="middle">'
        + "".join(val_labels)
        + '</g>'
        '<g fill="var(--md-on-surface-faint)" font-family="var(--md-font-data)" '
        'font-size="9" text-anchor="middle">'
        + "".join(week_labels)
        + '</g>'
        '</svg>'
        '</div>'
    )


_BY_TYPE_COLOURS = {
    "new-feature": "chart-blue",
    "bug": "chart-pink",
    "refactoring": "chart-yellow",
    "test": "chart-mint",
    "breaking": "chart-peach",
    "unclassified": "chart-grey",
}


def _render_by_type_chart(specs: list[SpecRow], now: dt.datetime) -> str:
    """Spec 0177 §2.4.5 — last 30 days, deployed-spec count grouped by
    type. Right-aligned label = "<count> · <mean_cycle>".
    """
    month_ago = now - dt.timedelta(days=30)
    by_type: dict[str, list[int]] = {}
    type_counts: dict[str, int] = {}
    for s in specs:
        if s.status != "deployed":
            continue
        t = _parse_ts(s.fm.get("deployed_at"))
        if t is None or t < month_ago:
            continue
        type_ = s.type or "unclassified"
        type_counts[type_] = type_counts.get(type_, 0) + 1
        if s.cycle_seconds:
            by_type.setdefault(type_, []).append(s.cycle_seconds)
    if not type_counts:
        return (
            '<div class="chart-card">'
            '<div class="chart-card__title">By type · last 30 days</div>'
            '<div class="chart-card__sub">mean cycle by category</div>'
            '<div class="metrics-empty">No deployed specs in the last 30 days.</div>'
            '</div>'
        )
    max_count = max(type_counts.values()) or 1
    total = sum(type_counts.values())
    rows: list[str] = []
    for type_ in sorted(type_counts.keys(), key=lambda k: type_counts[k], reverse=True):
        c = type_counts[type_]
        mean_cycle = (
            _humanize_seconds(int(statistics.mean(by_type[type_])))
            if by_type.get(type_)
            else "—"
        )
        width_pct = int((c / max_count) * 100)
        token = _BY_TYPE_COLOURS.get(type_, "chart-grey")
        rows.append(
            '<div class="bar-row">'
            f'<div class="bar-row__lbl">{_escape(type_)}</div>'
            '<div class="bar-row__track">'
            f'<div class="bar-row__fill" style="width: {width_pct}%; background: var(--{token});"></div>'
            '</div>'
            f'<div class="bar-row__val">{c} · {_escape(mean_cycle)}</div>'
            '</div>'
        )
    return (
        '<div class="chart-card">'
        '<div class="chart-card__title">By type · last 30 days</div>'
        f'<div class="chart-card__sub">{total} specs total · mean cycle by category</div>'
        f'<div class="bar-list" style="margin-top: 6px;">{"".join(rows)}</div>'
        '</div>'
    )


def _render_success_donut(specs: list[SpecRow], now: dt.datetime) -> str:
    """Spec 0177 §2.4.6 — last 30 days. SVG donut: deployed / (deployed +
    failed). Centre = percentage. Legend below.
    """
    month_ago = now - dt.timedelta(days=30)
    deployed_recent = sum(
        1
        for s in specs
        if s.status == "deployed"
        and (t := _parse_ts(s.fm.get("deployed_at"))) is not None
        and t >= month_ago
    )
    failed_recent = sum(
        1
        for s in specs
        if s.status == "failed"
        and (t := _parse_ts(s.fm.get("started_at"))) is not None
        and t >= month_ago
    )
    total = deployed_recent + failed_recent
    if total == 0:
        return (
            '<div class="chart-card">'
            '<div class="chart-card__title">Success rate · last 30 days</div>'
            '<div class="chart-card__sub">deployed vs failed cycles</div>'
            '<div class="metrics-empty">No completed cycles in the last 30 days.</div>'
            '</div>'
        )
    success_pct = deployed_recent / total
    radius = 56
    circumference = 2 * 3.14159265 * radius  # ≈ 351.86
    deployed_arc = success_pct * circumference
    rest = circumference - deployed_arc
    pct_label = int(round(success_pct * 100))
    return (
        '<div class="chart-card">'
        '<div class="chart-card__title">Success rate · last 30 days</div>'
        '<div class="chart-card__sub">deployed vs failed cycles</div>'
        '<svg class="chart" viewBox="0 0 200 160" preserveAspectRatio="xMidYMid meet" '
        'role="img" aria-label="Success rate donut">'
        '<g transform="translate(100,80)">'
        f'<circle r="{radius}" fill="none" stroke="var(--chart-pink)" stroke-width="20" />'
        f'<circle r="{radius}" fill="none" stroke="var(--chart-green)" stroke-width="20" '
        f'stroke-dasharray="{deployed_arc:.2f} {rest:.2f}" stroke-dashoffset="{circumference / 4:.2f}" '
        'transform="rotate(-90)" />'
        f'<text y="-4" text-anchor="middle" font-family="var(--md-font-data)" '
        f'font-size="22" font-weight="600" fill="var(--md-on-surface)">{pct_label}%</text>'
        f'<text y="18" text-anchor="middle" font-family="var(--md-font-plain)" '
        f'font-size="10" fill="var(--md-on-surface-faint)">{deployed_recent} of {total}</text>'
        '</g>'
        '</svg>'
        '<div class="chart-card__legend" style="justify-content: center;">'
        f'<span><span class="lg__sw" style="background: var(--chart-green);"></span>Deployed · {deployed_recent}</span>'
        f'<span><span class="lg__sw" style="background: var(--chart-pink);"></span>Failed · {failed_recent}</span>'
        '</div>'
        '</div>'
    )


def _render_authoring_funnel(specs: list[SpecRow], now: dt.datetime) -> str:
    """Spec 0177 §2.4.7 — drafts → queued → in-flight → deployed counts
    over the last 30 days. Visually a funnel: each stage's rectangle
    shrinks toward the right.
    """
    month_ago = now - dt.timedelta(days=30)
    # Drafts: current draft count + drafts promoted in last 30 days.
    # We only have specs frontmatter here; use `promoted_from_draft` to
    # count promotions (each promoted spec corresponds to one draft idea).
    promoted_recent = sum(
        1
        for s in specs
        if s.fm.get("promoted_from_draft")
        and (t := _parse_ts(s.fm.get("queued_at"))) is not None
        and t >= month_ago
    )
    # Queued: count of specs queued in last 30d (including those that already shipped).
    queued_recent = sum(
        1
        for s in specs
        if (t := _parse_ts(s.fm.get("queued_at"))) is not None and t >= month_ago
    )
    inflight_recent = sum(
        1
        for s in specs
        if s.status in ("in_progress", "deployed", "failed", "merged")
        and (t := _parse_ts(s.fm.get("started_at"))) is not None
        and t >= month_ago
    )
    deployed_recent = sum(
        1
        for s in specs
        if s.status == "deployed"
        and (t := _parse_ts(s.fm.get("deployed_at"))) is not None
        and t >= month_ago
    )
    drafts_count = promoted_recent  # Drafts that produced queued specs.
    stages_data = [
        ("DRAFTS", drafts_count, "chart-grey"),
        ("QUEUED", queued_recent, "chart-mint"),
        ("IN FLIGHT", inflight_recent, "chart-blue"),
        ("DEPLOYED", deployed_recent, "chart-green"),
    ]
    if not any(c for _l, c, _t in stages_data):
        return (
            '<div class="chart-card">'
            '<div class="metrics-empty">No spec authoring activity in the last 30 days.</div>'
            '</div>'
        )
    # Compute funnel rect geometries: each stage is narrower than the last.
    total_w = 800
    stage_w = 180
    gap = 50
    cursor_x = 0
    rects: list[str] = []
    labels: list[str] = []
    heights = (60, 40, 30, 24)
    ys = (20, 30, 35, 38)
    for i, ((label, count, token), h, y) in enumerate(zip(stages_data, heights, ys)):
        rects.append(
            f'<rect x="{cursor_x}" y="{y}" width="{stage_w}" height="{h}" '
            f'fill="var(--{token})" />'
        )
        labels.append(
            f'<text x="{cursor_x + stage_w / 2}" y="{y + h / 2 - 4}" '
            'text-anchor="middle" font-size="11" fill="var(--md-on-surface-faint)">'
            f'{_escape(label)}</text>'
            f'<text x="{cursor_x + stage_w / 2}" y="{y + h / 2 + 14}" '
            'text-anchor="middle" font-size="18" font-weight="600" '
            'fill="var(--md-on-surface)">'
            f'{count}</text>'
        )
        # Tapering polygon between stages.
        if i < len(stages_data) - 1:
            next_h = heights[i + 1]
            next_y = ys[i + 1]
            rects.append(
                f'<polygon points="'
                f'{cursor_x + stage_w},{y} '
                f'{cursor_x + stage_w + gap},{next_y} '
                f'{cursor_x + stage_w + gap},{next_y + next_h} '
                f'{cursor_x + stage_w},{y + h}'
                '" fill="var(--md-surface-container-high)" />'
            )
        cursor_x += stage_w + gap

    promo_pct = int(round((queued_recent / drafts_count) * 100)) if drafts_count else 0
    ship_pct = int(round((deployed_recent / queued_recent) * 100)) if queued_recent else 0
    funnel_sub = (
        f"Last 30 days · {drafts_count} drafts promoted · {promo_pct}% reached queue · "
        f"{ship_pct}% of queued shipped"
        if drafts_count
        else f"Last 30 days · {queued_recent} queued · {deployed_recent} shipped"
    )
    return (
        '<section class="chart-card">'
        f'<svg class="chart" viewBox="0 0 {total_w} 100" preserveAspectRatio="none" '
        'role="img" aria-label="Authoring funnel">'
        '<g font-family="var(--md-font-plain)">'
        + "".join(rects)
        + "".join(labels)
        + '</g></svg>'
        f'<div class="chart-card__sub" style="text-align: center; margin-top: 8px;">'
        f'{_escape(funnel_sub)}</div>'
        '</section>'
    )


# ── Pagination (spec 0177 §2.6) ────────────────────────────────────────────


PAGER_PAGE_SIZE = 10


def _render_pager(total_rows: int, label: str) -> str:
    """Emit the `.pager` strip for a paginated list section.

    Behaviour mirrors the mockup: ``Showing X–Y of N`` on the left,
    ``← N ⋯ N →`` button row on the right. Disabled prev on page 1,
    disabled next on the last page. Mid-pages collapse into an ellipsis
    once total > 5 pages, matching the queue mockup's pager.

    First-page state: server-rendered. JS (DASHBOARD_LIVE_JS) wires the
    button clicks to toggle ``[hidden]`` on ``[data-pager-page]`` rows in
    the parent section, and updates the count + active-button state on
    each click. The page state does NOT persist across reloads; the
    bootstrap client's 5s refresh recomputes it (capturing the active
    page in a closure so the live refresh doesn't bounce the user back
    to page 1 — spec 0177 §2.6 risks).
    """
    if total_rows <= 0:
        return ""
    total_pages = max(1, (total_rows + PAGER_PAGE_SIZE - 1) // PAGER_PAGE_SIZE)
    end = min(PAGER_PAGE_SIZE, total_rows)
    page_buttons: list[str] = []
    if total_pages <= 5:
        for p in range(1, total_pages + 1):
            attrs = ' aria-current="page"' if p == 1 else ''
            page_buttons.append(
                f'<button class="pager__btn" type="button" data-pager-go="{p}"{attrs}>{p}</button>'
            )
    else:
        # 1 · 2 · 3 ⋯ N (active page is always 1 on first render)
        for p in (1, 2, 3):
            attrs = ' aria-current="page"' if p == 1 else ''
            page_buttons.append(
                f'<button class="pager__btn" type="button" data-pager-go="{p}"{attrs}>{p}</button>'
            )
        page_buttons.append('<span class="pager__ellipsis">…</span>')
        page_buttons.append(
            f'<button class="pager__btn" type="button" data-pager-go="{total_pages}">{total_pages}</button>'
        )
    prev_disabled = ' disabled' if total_pages == 1 else ' disabled'  # page 1 → prev disabled
    next_disabled = ' disabled' if total_pages == 1 else ''
    return (
        f'<div class="pager" data-pager-total="{total_rows}" data-pager-pages="{total_pages}" '
        f'aria-label="{_escape(label)} pagination">'
        f'<div class="pager__count" data-pager-count>Showing 1–{end} of {total_rows}</div>'
        '<div class="pager__nav">'
        f'<button class="pager__btn" type="button" data-pager-prev aria-label="Previous page"{prev_disabled}>←</button>'
        + "".join(page_buttons)
        + f'<button class="pager__btn" type="button" data-pager-next aria-label="Next page"{next_disabled}>→</button>'
        '</div>'
        '</div>'
    )


# ── Queue table ────────────────────────────────────────────────────────────


def _render_queue(queued: list[SpecRow], now: dt.datetime) -> str:
    header = (
        '<div class="sh"><div class="sh__name">Queue</div>'
        '<div class="sh__hint">/dev-next picks position 1 first</div><div class="sh__rule"></div></div>'
    )
    if not queued:
        body = (
            '<div class="qrow qrow--header">'
            '<div>#</div><div>Spec</div><div>Title</div><div>Type</div>'
            '<div style="text-align:right">Waiting</div></div>'
            '<div class="qrow qrow--empty">Queue is empty. Promote a draft with '
            '<code>/spec-promote &lt;id&gt;</code> or queue a new one with <code>/spec-queue</code>.</div>'
        )
        return header + f'<section class="qtable" aria-label="Queue">{body}</section>'

    rows = [
        '<div class="qrow qrow--header">'
        '<div>#</div><div>Spec</div><div>Title</div><div>Type</div>'
        '<div style="text-align:right">Waiting</div></div>'
    ]
    for idx, s in enumerate(queued):
        page = (idx // PAGER_PAGE_SIZE) + 1
        hidden = ' hidden' if page > 1 else ''
        queued_ts = _parse_ts(s.fm.get("queued_at"))
        waiting = _ago(queued_ts, now) if queued_ts else "—"
        rows.append(
            f'<div class="qrow" data-pager-page="{page}"{hidden}>'
            f'<div class="qrow__pos">{_escape(s.fm.get("queue_position", "—"))}</div>'
            f'<div class="qrow__id">{_link_spec(s.number, s.number)}</div>'
            f'<div class="qrow__title">{_escape(s.title)}</div>'
            f'<div>{_type_chip(s.type)}</div>'
            f'<div class="qrow__age">{_escape(waiting.replace(" ago", ""))}</div>'
            '</div>'
        )
    table = f'<section class="qtable" aria-label="Queue" data-pager-target>{"".join(rows)}</section>'
    pager = _render_pager(len(queued), "Queue") if len(queued) > PAGER_PAGE_SIZE else ""
    return header + table + pager


# ── Activity feed ──────────────────────────────────────────────────────────


def _render_feed(specs: list[SpecRow], now: dt.datetime) -> str:
    cutoff = now - dt.timedelta(hours=24)
    spec_by_id = {s.number: s for s in specs}
    flat: list[tuple[dt.datetime, str, dict[str, Any], SpecRow | None]] = []
    for s in specs:
        for ev in s.events:
            ts = _parse_ts(ev.get("ts"))
            if ts is None or ts < cutoff:
                continue
            flat.append((ts, ev.get("step", ""), ev.get("data") or {}, spec_by_id.get(s.number)))
    flat.sort(key=lambda t: t[0], reverse=True)

    header = (
        '<div class="sh"><div class="sh__name">Recent activity</div>'
        '<div class="sh__hint">last 24 hours</div><div class="sh__rule"></div></div>'
    )

    if not flat:
        return (
            header
            + '<section class="feed" aria-label="Recent activity">'
            '<div class="feed__row"><div class="feed__ts">—</div>'
            '<div class="feed__step feed__step--neutral"></div>'
            '<div class="feed__what"><em>No events in the last 24 hours.</em></div>'
            '<div class="feed__dur">—</div></div></section>'
        )

    capped = flat[:40]
    rows: list[str] = []
    for idx, (ts, step, data, spec) in enumerate(capped):
        page = (idx // PAGER_PAGE_SIZE) + 1
        hidden = ' hidden' if page > 1 else ''
        icon, tone = _FEED_STEP_ICON.get(step, ("circle", "neutral"))
        kicker = _FEED_KICKER.get(step, step.replace("_", " "))
        detail = _feed_detail(spec, step, data)
        ts_str = ts.strftime("%H:%M:%S UTC")
        rows.append(
            f'<div class="feed__row" data-pager-page="{page}"{hidden}>'
            f'<div class="feed__ts">{_escape(ts_str)}</div>'
            f'<div class="feed__step feed__step--{tone}">'
            f'<span class="material-symbols-outlined">{_escape(icon)}</span></div>'
            f'<div class="feed__what"><span class="kicker">{_escape(kicker)}</span>{detail}</div>'
            '<div class="feed__dur">—</div>'
            '</div>'
        )
    section = (
        f'<section class="feed" aria-label="Recent activity" data-pager-target>{"".join(rows)}</section>'
    )
    pager = _render_pager(len(capped), "Recent activity") if len(capped) > PAGER_PAGE_SIZE else ""
    return header + section + pager


# ── Drafts ─────────────────────────────────────────────────────────────────


def _render_drafts(drafts: list[DraftRow], now: dt.datetime) -> str:
    header = (
        '<div class="sh"><div class="sh__name">Drafts</div>'
        '<div class="sh__hint">backlog · promote with <code>/spec-promote &lt;id&gt;</code></div>'
        '<div class="sh__rule"></div></div>'
    )
    if not drafts:
        return (
            header
            + '<section class="drafts" aria-label="Drafts">'
            '<div class="draft-row"><div class="draft-row__id">—</div>'
            '<div class="draft-row__title"><em>No drafts parked.</em></div>'
            '<div></div><div class="draft-row__age">—</div></div></section>'
        )
    rows: list[str] = []
    for d in drafts:
        created = _parse_ts(d.created)
        age = _ago(created, now) if created else "—"
        rows.append(
            '<div class="draft-row">'
            f'<div class="draft-row__id">{_escape(d.draft_id)}</div>'
            f'<div class="draft-row__title">{_link_draft(d.draft_id, d.title)}</div>'
            f'<div>{_type_chip(d.type)}</div>'
            f'<div class="draft-row__age">park · {_escape(age.replace(" ago", ""))}</div>'
            '</div>'
        )
    return header + f'<section class="drafts" aria-label="Drafts">{"".join(rows)}</section>'


# ── All specs table ────────────────────────────────────────────────────────


def _spec_lifetime_seconds(s: SpecRow) -> int | None:
    """Wall-clock seconds from spec creation to deployment.

    Spec 0177 §2.3 — the History table's Lifetime column is "how long did
    this idea sit before it shipped" (created/queued → deployed), in
    contrast to Cycle (started → deployed, the agent-time on /dev-next).
    Falls back to ``queued_at`` when ``created`` is absent.
    """
    deployed = _parse_ts(s.fm.get("deployed_at"))
    if deployed is None:
        return None
    raw_created = s.fm.get("created") or s.fm.get("queued_at")
    if not raw_created:
        return None
    # `created` is often a bare YYYY-MM-DD; promote to a timezone-aware
    # midnight-UTC so the subtraction works.
    created_str = str(raw_created)
    if len(created_str) == 10 and created_str.count("-") == 2:
        created_str = created_str + "T00:00:00Z"
    created = _parse_ts(created_str)
    if created is None:
        return None
    return max(0, int((deployed - created).total_seconds()))


def _render_all_specs(specs: list[SpecRow]) -> str:
    """Spec 0177 §2.3 — drop the Version column; add Lifetime (created →
    deployed) and Cycle (started → deployed). The new 6-column grid:
    ``70px 1fr 110px 100px 90px 90px``. Queued / in-flight / failed rows
    render Lifetime + Cycle as ``—`` since the deployment timestamp
    they're computed from doesn't exist yet.
    """
    rows: list[str] = []
    rows.append(
        '<div class="qrow qrow--history qrow--history-header">'
        '<div>Spec</div><div>Title</div><div>Type</div><div>Status</div>'
        '<div style="text-align:right">Lifetime</div>'
        '<div style="text-align:right">Cycle</div></div>'
    )
    sorted_specs = sorted(
        [s for s in specs if (s.fm.get("kind") or "dev") == "dev"],
        key=lambda s: int(s.number or "0"),
        reverse=True,
    )
    for s in sorted_specs:
        lifetime = _humanize_seconds(_spec_lifetime_seconds(s))
        cycle = _humanize_seconds(s.cycle_seconds)
        rows.append(
            '<div class="qrow qrow--history">'
            f'<div class="qrow__id">{_link_spec(s.number, s.number)}</div>'
            f'<div class="qrow__title">{_escape(s.title)}</div>'
            f'<div>{_type_chip(s.type)}</div>'
            f'<div>{_status_chip(s.status)}</div>'
            f'<div class="qrow__age">{_escape(lifetime)}</div>'
            f'<div class="qrow__age">{_escape(cycle)}</div>'
            '</div>'
        )
    counts_deployed = sum(1 for s in specs if s.status == "deployed")
    counts_queued = sum(1 for s in specs if s.status == "queued")
    counts_inflight = sum(1 for s in specs if s.status == "in_progress")
    header = (
        '<div class="sh"><div class="sh__name">All specs</div>'
        f'<div class="sh__hint">{counts_deployed} shipped · {counts_queued} queued · {counts_inflight} in flight</div>'
        '<div class="sh__rule"></div></div>'
    )
    return header + f'<section class="qtable" aria-label="All specs">{"".join(rows)}</section>'


# ── Header / footer ────────────────────────────────────────────────────────


def _render_header(live_version: str, now: dt.datetime, *, shell_only: bool = False) -> str:
    chip = (
        f'<span class="chip tone-ok no-dot">v{_escape(live_version)} live</span>'
        if live_version
        else ""
    )
    ts = now.strftime("%Y-%m-%d %H:%M UTC")
    # Spec 0160 — the `data-last-updated` span carries the build-time
    # timestamp by default; `dashboard-bootstrap.js` rewrites it with a live
    # "X ago" string after each successful /api/data fetch.
    last_updated_initial = "" if shell_only else f"updated {_escape(ts)}"
    # Spec 0169 §2.7 — theme toggle button. Cycles light → dark → auto.
    # dashboard-live.js wires the click handler + localStorage persistence.
    # The initial label is filled in by JS on first paint (the inline init
    # script in <head> already set the html[data-theme] attribute).
    theme_toggle = (
        '<button class="theme-toggle" id="theme-toggle" type="button" '
        'aria-label="Toggle theme — light, dark, or auto (system)">'
        '<span class="material-symbols-outlined" aria-hidden="true" data-theme-icon>brightness_auto</span>'
        '<span class="theme-toggle__label" data-theme-label>auto</span>'
        '</button>'
    )
    return (
        '<header class="dh">'
        '<div>'
        '<div class="dh__title">dual-research · spec dashboard</div>'
        '<div class="dh__sub">read-only view of <code>specs/</code>, <code>handoffs/</code> '
        'and <code>dashboard/events/</code> at <code>main</code></div>'
        '</div>'
        '<div class="dh__meta">'
        f'<span>{chip}</span>'
        f'<span data-last-updated>{last_updated_initial}</span>'
        + theme_toggle +
        f'<a href="{REPO_URL}">repo ↗</a>'
        '</div>'
        '</header>'
    )


def _render_footer() -> str:
    return (
        '<footer class="foot">'
        '<span>generated by <code>scripts/spec_lifecycle/render_dashboard.py</code> · '
        'regenerated on every push to <code>main</code></span>'
        f'<a href="{PAGES_URL}">view on GitHub Pages →</a>'
        '</footer>'
    )


# ─────────────────────────────────────────────────────────────
# Spec 0169 — Dashboard redesign v2: callout strip, tabs, theme toggle,
# total-elapsed banner.
#
# The mockup at dashboard/mockups/0169-dashboard-redesign-v2.html is the
# visual contract. We bind to existing --md-* / --p-* tokens (per spec 0169
# §2.9 — the mockup's ad-hoc tokens like --bg-page / --text-1 are NOT
# reproduced here; the live tokens already cover light + dark themes via
# tokens.css's prefers-color-scheme blocks, and the theme shim below
# re-projects them onto [data-theme="light"] / "dark" / "auto" so a manual
# toggle can override the OS preference).
# ─────────────────────────────────────────────────────────────


def _build_sparkline_polyline(values: list[int]) -> str:
    """Map an integer series onto a 0–120 × 4–20 SVG polyline path string.

    Used by the avg-cycle counter's inline sparkline (spec 0177 §2.1) and
    the deferred drafts-funnel chart (§2.4.7). Returns the `points=...`
    inner content; the caller wraps it in <polyline>. Empty / single-point
    series collapse to a flat baseline so the chart still occupies space.
    """
    if not values:
        return "0,12 120,12"
    if len(values) == 1:
        return "0,12 120,12"
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1
    step = 120.0 / (len(values) - 1)
    pts = []
    for i, v in enumerate(values):
        x = round(i * step, 2)
        # invert: smaller cycle times = lower y (visually higher on the chart)
        y = round(20.0 - 16.0 * (v - lo) / rng, 2)
        pts.append(f"{x},{y}")
    return " ".join(pts)


def _render_counter_cluster(specs: list[SpecRow], drafts: list[DraftRow], now: dt.datetime) -> str:
    """Spec 0177 §2.1 — full-width 5-counter row. The avg-cycle card from
    spec 0169 folds in as the accented 5th counter, carrying the rolling-10
    mean + delta vs prior 10 + an inline sparkline of the last 12 deployed
    cycle times. The other four counters (Drafts / Queued / In flight /
    Shipped) keep their plain shape.
    """
    queued = [s for s in specs if s.status == "queued"]
    inflight = [s for s in specs if s.status == "in_progress"]
    shipped = [s for s in specs if s.status == "deployed"]
    counts = {
        "drafts": len(drafts),
        "queued": len(queued),
        "inflight": len(inflight),
        "shipped": len(shipped),
    }

    # Sub-line copy for the four plain counters.
    next_q = sorted(queued, key=lambda s: int(s.fm.get("queue_position") or 999))
    next_label = f"next is {next_q[0].number}" if next_q else "queue empty"
    inflight_label = (
        f"running · {len(inflight)} active" if inflight else "idle"
    )

    deployed_with_timing = sum(1 for s in shipped if s.cycle_seconds)
    shipped_sub = (
        f"all-time · {deployed_with_timing} with full timings"
        if deployed_with_timing
        else "all-time"
    )

    subs = {
        "drafts": "ideation",
        "queued": "pending · " + next_label,
        "inflight": inflight_label,
        "shipped": shipped_sub,
    }
    labels = {
        "drafts": "Drafts",
        "queued": "Queued",
        "inflight": "In flight",
        "shipped": "Shipped",
    }

    cells: list[str] = []
    for key in ("drafts", "queued", "inflight", "shipped"):
        num_cls = "counter__num is-zero" if counts[key] == 0 else "counter__num"
        cells.append(
            '<div class="counter">'
            f'<div class="counter__lbl">{labels[key]}</div>'
            f'<div class="{num_cls}">{counts[key]}</div>'
            f'<div class="counter__sub">{_escape(subs[key])}</div>'
            '</div>'
        )

    # The 5th, accented counter — avg cycle (last 10) with delta + sparkline.
    deployed_sorted = sorted(
        shipped,
        key=lambda s: s.fm.get("deployed_at") or "",
        reverse=True,
    )
    cycle_times = [s.cycle_seconds for s in deployed_sorted if s.cycle_seconds]
    last10 = cycle_times[:10]
    prior10 = cycle_times[10:20]
    avg_str = _humanize_seconds(int(statistics.mean(last10))) if last10 else "—"

    delta_html = ""
    if last10 and prior10:
        d = int(statistics.mean(prior10) - statistics.mean(last10))
        if d > 0:
            delta_html = (
                f'<span class="delta-up">↓ {_escape(_humanize_seconds(d))}</span> vs prior 10'
            )
        elif d < 0:
            delta_html = (
                f'<span class="delta-down">↑ {_escape(_humanize_seconds(-d))}</span> vs prior 10'
            )
        else:
            delta_html = "flat vs prior 10"
    elif last10:
        delta_html = f"rolling {len(last10)}"
    else:
        delta_html = "no deploys yet"

    # Sparkline — last 12 cycle times in chronological order (oldest → newest)
    # so the line reads left-to-right.
    spark_series = list(reversed(cycle_times[:12]))
    spark_svg = ""
    if len(spark_series) >= 2:
        pts = _build_sparkline_polyline(spark_series)
        spark_svg = (
            '<svg class="counter__spark" viewBox="0 0 120 24" '
            'preserveAspectRatio="none" aria-hidden="true">'
            '<polyline fill="none" stroke="currentColor" stroke-width="1.5" '
            'stroke-linejoin="round" stroke-linecap="round" '
            f'points="{pts}" />'
            '</svg>'
        )

    cells.append(
        '<div class="counter counter--accent" aria-label="Average cycle time">'
        '<div class="counter__lbl">Avg cycle (last 10)</div>'
        f'<div class="counter__num">{_escape(avg_str)}</div>'
        f'<div class="counter__sub">{delta_html}</div>'
        f'{spark_svg}'
        '</div>'
    )

    return (
        '<section class="counters" aria-label="Pipeline counters">'
        + "".join(cells)
        + '</section>'
    )


def _render_total_elapsed_banner(specs: list[SpecRow]) -> str:
    """Spec 0169 §2.5 — Total time spent banner, 4 tiles. The user-priority
    feature: prominent cumulative agent-hours across all timed cycles."""
    deployed = [s for s in specs if s.status == "deployed" and s.cycle_seconds]
    cycle_times = [s.cycle_seconds for s in deployed]
    if not cycle_times:
        empty = (
            '<section class="te-banner" aria-label="Total time spent">'
            '<div class="sh"><div class="sh__name">Total time spent</div><div class="sh__rule"></div></div>'
            '<div class="te-banner__empty"><em>No timed cycles yet.</em></div>'
            '</section>'
        )
        return empty

    total_sec = sum(cycle_times)
    # Spec 0169 §2.5 — mean excludes outliers > 1h (3600s). The bootstrap
    # outlier 0152 (10.8h) skews the rolling mean otherwise.
    non_outliers = [c for c in cycle_times if c <= 3600]
    excluded = len(cycle_times) - len(non_outliers)
    mean_sec = int(statistics.mean(non_outliers)) if non_outliers else 0
    # Median includes outliers (p50 of all timed cycles).
    median_sec = int(statistics.median(cycle_times))

    # Fastest / slowest with spec ids.
    fast_idx = min(range(len(cycle_times)), key=lambda i: cycle_times[i])
    slow_idx = max(range(len(cycle_times)), key=lambda i: cycle_times[i])
    fast_spec = deployed[fast_idx]
    slow_spec = deployed[slow_idx]
    fast_str = _humanize_seconds(cycle_times[fast_idx])
    slow_str = _humanize_seconds(cycle_times[slow_idx])

    def _humanize_long(sec: int) -> str:
        """For total elapsed — show as Xd Yh / Xh Ym / Xm Ys depending on magnitude."""
        if sec < 3600:
            m = sec // 60
            s = sec % 60
            return f"{m}m {s}s" if m else f"{s}s"
        if sec < 86400:
            h = sec // 3600
            m = (sec % 3600) // 60
            return f"{h}h {m}m" if m else f"{h}h"
        d = sec // 86400
        h = (sec % 86400) // 3600
        return f"{d}d {h}h" if h else f"{d}d"

    excluded_sub = f"excluding {excluded} outlier{'' if excluded == 1 else 's'} > 1h" if excluded else "no outliers excluded"

    def tile(label: str, value_html: str, sub: str) -> str:
        return (
            '<div class="te-tile">'
            f'<div class="te-tile__lbl">{_escape(label)}</div>'
            f'<div class="te-tile__val">{value_html}</div>'
            f'<div class="te-tile__sub">{_escape(sub)}</div>'
            '</div>'
        )

    return (
        '<section class="te-banner" aria-label="Total time spent">'
        '<div class="sh"><div class="sh__name">Total time spent</div>'
        f'<div class="sh__hint">across {len(cycle_times)} timed cycles</div>'
        '<div class="sh__rule"></div></div>'
        '<div class="te-banner__row">'
        + tile("Total elapsed", _escape(_humanize_long(total_sec)), f"across {len(cycle_times)} timed cycles")
        + tile("Mean cycle", _escape(_humanize_seconds(mean_sec)), excluded_sub)
        + tile("Median cycle", _escape(_humanize_seconds(median_sec)), "p50 of timed runs")
        + tile(
            "Fastest / Slowest",
            f'{_escape(fast_str)}<small> / </small>{_escape(slow_str)}',
            f"{_escape(fast_spec.number)} / {_escape(slow_spec.number)}",
        )
        + '</div></section>'
    )


def _render_tabs(*, now_count: int, spec_count: int, history_count: int) -> str:
    """Spec 0169 §2.2 — tab bar above tab panels. Active tab carries
    aria-selected="true" + visible underline (CSS-driven from --p-info).
    The default-active tab is 'now'."""
    def btn(slug: str, label: str, count: int | None = None, active: bool = False) -> str:
        ct = f' <span class="tab__count">{count}</span>' if count is not None else ''
        return (
            f'<button class="tab" role="tab" '
            f'aria-selected="{"true" if active else "false"}" '
            f'data-tab="{slug}" id="tab-{slug}">'
            f'{_escape(label)}{ct}</button>'
        )
    return (
        '<nav class="tabs" role="tablist" aria-label="Dashboard sections">'
        + btn("now", "Now", now_count, active=True)
        + btn("spec", "Spec creation", spec_count)
        + btn("history", "History", history_count)
        + btn("metrics", "Metrics")
        + '</nav>'
    )


def _render_theme_init_script() -> str:
    """Spec 0169 §2.7 — inline script in <head> that reads localStorage and
    sets data-theme on <html> before the body paints. Prevents the theme
    flash on first paint.

    Spec 0177 §2.7 — default for first-visit users flipped from 'auto' to
    'light'. Returning users with a stored preference keep it; the
    light→dark→auto toggle cycle still works. New visitors land on the
    light surface, which is the mockup baseline and reads better on the
    typical product-owner workstation.
    """
    return (
        '<script>'
        '(function(){'
        'try{'
        "var t=localStorage.getItem('dr-dashboard-theme')||'light';"
        "if(t!=='light'&&t!=='dark'&&t!=='auto')t='light';"
        "document.documentElement.setAttribute('data-theme',t);"
        '}catch(e){'
        "document.documentElement.setAttribute('data-theme','light');"
        '}'
        '})();'
        '</script>'
    )


# ── Public renderers ───────────────────────────────────────────────────────


def render_index(
    specs: list[SpecRow],
    drafts: list[DraftRow],
    *,
    live_version: str = "",
    now: dt.datetime | None = None,
    shell_only: bool = False,
) -> str:
    """Render the dashboard index.

    Default mode (``shell_only=False``): emits a fully-populated page from
    the data on disk. Used for local previews and as a build-time fallback.

    Shell mode (``shell_only=True``, spec 0160): emits the page chrome with
    empty ``data-region`` containers and skeleton placeholders. The
    ``dashboard-bootstrap.js`` client fetches ``/api/data`` and populates
    them at runtime. This is what the Cloudflare Pages build ships so the
    dashboard reflects fresh repo state without paying the rebuild lag.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    in_flight = [s for s in specs if s.status == "in_progress"]
    queued = sorted(
        [s for s in specs if s.status == "queued"],
        key=lambda s: int(s.fm.get("queue_position") or 999),
    )
    deployed_count = sum(1 for s in specs if s.status == "deployed")

    # Spec 0169 — tab counts. Now tab counts in_flight + queued (the things
    # that need attention "now"). Spec creation counts drafts + queued (the
    # authoring backlog). History counts all-time shipped.
    now_count = len(in_flight) + len(queued)
    spec_count = len(drafts) + len(queued)
    history_count = deployed_count

    parts: list[str] = []
    parts.append(_html_head("dual-research · spec dashboard"))
    parts.append('<body><main class="page">')
    parts.append(_render_header(live_version, now, shell_only=shell_only))

    # ─── Hero + counter row (spec 0177 §2.1) ──────────────────────────
    # Replaces spec 0169's 3-column callout strip. Hero spans the full
    # container width (with a horizontal stage timeline beneath when in
    # flight); counter row below holds 5 cards — the avg-cycle card from
    # spec 0169 folded in as the accented 5th counter.
    parts.append('<section class="strip" aria-label="Status callouts">')
    if shell_only:
        parts.append(_skeleton_hero())
        parts.append(_skeleton_section("counters", "Counters"))
    else:
        if in_flight:
            for spec in in_flight:
                parts.append(_wrap_region("hero", _render_hero_inflight(spec, specs, now)))
        else:
            parts.append(_wrap_region("hero", _render_hero_idle(specs, queued, drafts, now)))
        parts.append(_wrap_region("counters", _render_counter_cluster(specs, drafts, now)))
    parts.append('</section>')

    # ─── Tab bar (spec 0169 §2.2) ────────────────────────────────────
    parts.append(_render_tabs(now_count=now_count, spec_count=spec_count, history_count=history_count))

    # ─── Now tab (spec 0169 §2.3) ────────────────────────────────────
    parts.append('<section class="tab-panel" role="tabpanel" data-panel="now" aria-hidden="false">')
    if shell_only:
        parts.append(_skeleton_section("queue", "Queue"))
        parts.append(_skeleton_section("feed", "Recent activity"))
    else:
        parts.append(_wrap_region("queue", _render_queue(queued, now)))
        parts.append(_wrap_region("feed", _render_feed(specs, now)))
    parts.append('</section>')

    # ─── Spec creation tab (spec 0169 §2.4) ──────────────────────────
    parts.append('<section class="tab-panel" role="tabpanel" data-panel="spec" aria-hidden="true">')
    if shell_only:
        parts.append(_skeleton_section("drafts", "Drafts"))
    else:
        parts.append(_wrap_region("drafts", _render_drafts(drafts, now)))
    parts.append('</section>')

    # ─── History tab (spec 0169 §2.5) ────────────────────────────────
    # Total-elapsed banner leads (user-priority surface), then all-specs.
    parts.append('<section class="tab-panel" role="tabpanel" data-panel="history" aria-hidden="true">')
    if shell_only:
        parts.append(_skeleton_section("total-elapsed", "Total time spent"))
        parts.append(_skeleton_section("all-specs", "All specs"))
    else:
        parts.append(_wrap_region("total-elapsed", _render_total_elapsed_banner(specs)))
        parts.append(_wrap_region("all-specs", _render_all_specs(specs)))
    parts.append('</section>')

    # ─── Metrics tab (spec 0169 §2.6) ────────────────────────────────
    # Reuses the existing _render_metrics — full chart/by-type subsections
    # are deferred to a follow-up polish spec.
    parts.append('<section class="tab-panel" role="tabpanel" data-panel="metrics" aria-hidden="true">')
    if shell_only:
        parts.append(_skeleton_section("metrics", "Metrics"))
    else:
        parts.append(_wrap_region("metrics", _render_metrics(specs, now)))
    parts.append('</section>')

    parts.append(_render_footer())
    parts.append('</main></body></html>')
    return "\n".join(parts)


def _wrap_region(name: str, html: str) -> str:
    """Wrap a populated section in a ``data-region`` container so the bootstrap
    client can find and swap it the same way it finds shell placeholders.
    Spec 0160."""
    return f'<div data-region="{name}">{html}</div>'


def _skeleton_section(region: str, label: str) -> str:
    """Generic skeleton — just a labelled container the bootstrap script will
    populate. Sized to roughly match the populated state to limit reflow."""
    return (
        f'<div data-region="{region}" class="region-skeleton" aria-busy="true" aria-label="{_escape(label)}">'
        f'<div class="skeleton__line skeleton__line--header"></div>'
        f'<div class="skeleton__line"></div>'
        f'<div class="skeleton__line"></div>'
        f'<div class="skeleton__line"></div>'
        f'</div>'
    )


def _skeleton_hero() -> str:
    return (
        '<div data-region="hero" class="region-skeleton" aria-busy="true" aria-label="Queue status">'
        '<section class="hero hero--idle">'
        '<div class="hero__icon skeleton__icon"></div>'
        '<div class="hero__body">'
        '<div class="skeleton__line skeleton__line--kicker"></div>'
        '<div class="skeleton__line skeleton__line--title"></div>'
        '<div class="skeleton__line"></div>'
        '</div>'
        '<div class="hero__right">'
        '<div class="skeleton__line skeleton__line--big"></div>'
        '<div class="skeleton__line"></div>'
        '</div>'
        '</section>'
        '</div>'
    )


def _skeleton_pipeline() -> str:
    return (
        '<div data-region="pipeline" class="region-skeleton" aria-busy="true" aria-label="Pipeline">'
        '<section class="pipe">'
        + ''.join(
            '<div class="pipe__col">'
            '<div class="skeleton__line skeleton__line--label"></div>'
            '<div class="skeleton__line skeleton__line--num"></div>'
            '<div class="pipe__bar"></div>'
            '</div>'
            for _ in range(5)
        )
        + '</section>'
        '</div>'
    )


def _skeleton_metrics() -> str:
    return (
        '<div data-region="metrics" class="region-skeleton" aria-busy="true" aria-label="Throughput &amp; cycle time">'
        '<section class="metrics">'
        + ''.join(
            '<div class="metric">'
            '<div class="skeleton__line skeleton__line--label"></div>'
            '<div class="skeleton__line skeleton__line--num"></div>'
            '<div class="skeleton__line"></div>'
            '</div>'
            for _ in range(4)
        )
        + '</section>'
        '</div>'
    )


def render_spec_page(s: SpecRow) -> str:
    parts: list[str] = []
    parts.append(_html_head(f"Spec {s.number} — {s.title}"))
    parts.append('<body><main class="page">')
    parts.append('<p><a href="index.html">← back to dashboard</a></p>')
    parts.append(f'<h1>Spec {_escape(s.number)} — {_escape(s.title)}</h1>')
    parts.append('<div class="sh"><div class="sh__name">Frontmatter</div><div class="sh__rule"></div></div>')
    parts.append('<section class="qtable"><div class="qrow qrow--header" style="grid-template-columns: 200px 1fr;">'
                 '<div>Field</div><div>Value</div></div>')
    for k, v in s.fm.items():
        parts.append(
            '<div class="qrow" style="grid-template-columns: 200px 1fr;">'
            f'<div class="qrow__pos">{_escape(k)}</div>'
            f'<div>{_escape(v)}</div></div>'
        )
    parts.append('</section>')

    parts.append('<div class="sh"><div class="sh__name">Event timeline</div><div class="sh__rule"></div></div>')
    if s.events:
        parts.append('<section class="qtable"><div class="qrow qrow--header" style="grid-template-columns: 200px 200px 1fr;">'
                     '<div>When</div><div>Step</div><div>Data</div></div>')
        for ev in s.events:
            parts.append(
                '<div class="qrow" style="grid-template-columns: 200px 200px 1fr;">'
                f'<div class="qrow__pos">{_escape(ev.get("ts"))}</div>'
                f'<div class="qrow__id">{_escape(ev.get("step"))}</div>'
                f'<div>{_escape(json.dumps(ev.get("data") or {}))}</div></div>'
            )
        parts.append('</section>')
    else:
        parts.append('<p><em>No events recorded.</em></p>')

    parts.append('<div class="sh"><div class="sh__name">Links</div><div class="sh__rule"></div></div>')
    parts.append('<ul>')
    rel = s.path.relative_to(s.path.parent.parent.parent)
    parts.append(f'<li><a href="{REPO_URL}/blob/main/{_escape(rel)}">Spec source on GitHub</a></li>')
    if pr := s.fm.get("pr"):
        parts.append(f'<li><a href="{_escape(pr)}">Pull request</a></li>')
    if handover := s.fm.get("handover"):
        parts.append(f'<li><a href="{REPO_URL}/blob/main/{_escape(handover)}">Handover</a></li>')
    parts.append('</ul>')
    parts.append(_render_footer())
    parts.append('</main></body></html>')
    return "\n".join(parts)


def render_draft_page(d: DraftRow) -> str:
    parts: list[str] = []
    parts.append(_html_head(f"Draft {d.draft_id} — {d.title}"))
    parts.append('<body><main class="page">')
    parts.append('<p><a href="index.html">← back to dashboard</a></p>')
    parts.append(f'<h1>Draft {_escape(d.draft_id)} — {_escape(d.title)}</h1>')
    parts.append('<div class="sh"><div class="sh__name">Frontmatter</div><div class="sh__rule"></div></div>')
    parts.append('<section class="qtable"><div class="qrow qrow--header" style="grid-template-columns: 200px 1fr;">'
                 '<div>Field</div><div>Value</div></div>')
    for k, v in d.fm.items():
        parts.append(
            '<div class="qrow" style="grid-template-columns: 200px 1fr;">'
            f'<div class="qrow__pos">{_escape(k)}</div>'
            f'<div>{_escape(v)}</div></div>'
        )
    parts.append('</section>')
    parts.append(
        f'<p><a href="{REPO_URL}/blob/main/specs/drafts/{_escape(d.path.name)}">View on GitHub</a></p>'
    )
    parts.append(_render_footer())
    parts.append('</main></body></html>')
    return "\n".join(parts)


# ── Stylesheet ─────────────────────────────────────────────────────────────

DASHBOARD_CSS = """\
/* Page chrome — dashboard-specific layout only.
   Every color/font/spacing/elevation reads from tokens.css. */

body {
  margin: 0;
  background: var(--md-surface-dim);
  color: var(--md-on-surface);
  font-family: var(--md-font-plain);
  font-feature-settings: "tnum" 1;
  line-height: 1.45;
  -webkit-font-smoothing: antialiased;
}
.page { max-width: 1280px; margin: 0 auto; padding: 28px 32px 80px; }

/* Header */
.dh {
  display: flex; align-items: baseline; justify-content: space-between;
  padding-bottom: 16px; margin-bottom: 24px;
  border-bottom: 1px solid var(--md-outline-hair);
  gap: 24px; flex-wrap: wrap;
}
.dh__title {
  font: 500 24px/1.2 var(--md-font-brand);
  letter-spacing: -0.01em;
}
.dh__sub { color: var(--md-on-surface-muted); font-size: 12.5px; }
.dh__meta { display: flex; gap: 14px; align-items: center; color: var(--md-on-surface-faint); font-size: 12px; }
.dh__meta a { color: var(--md-on-surface-variant); text-decoration: none; border-bottom: 1px dotted var(--md-outline-variant); }
.dh__meta a:hover { color: var(--md-on-surface); }

/* Section heading */
.sh {
  display: flex; align-items: baseline; gap: 12px;
  margin: 28px 0 12px;
}
.sh__name {
  font: 500 11px/1 var(--md-font-plain);
  letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--md-on-surface-faint);
}
.sh__hint { color: var(--md-on-surface-decor); font-size: 11.5px; }
.sh__rule { flex: 1; height: 1px; background: var(--md-outline-hair); }

/* HERO */
.hero {
  background: var(--md-surface-3);
  border: 1px solid var(--md-outline-hair);
  border-radius: 14px;
  padding: 22px 24px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 20px;
  align-items: center;
  margin-bottom: 12px;
}
.hero__icon {
  width: 44px; height: 44px; border-radius: 50%;
  display: grid; place-items: center;
  background: color-mix(in srgb, var(--p-idle) 22%, transparent);
  color: var(--md-on-surface-variant);
  position: relative; overflow: visible;
}
.hero--idle .hero__icon { background: color-mix(in srgb, var(--p-idle) 22%, transparent); color: var(--md-on-surface-variant); }
.hero--inflight .hero__icon { background: color-mix(in srgb, var(--p-info) 24%, transparent); color: var(--p-info); }
.hero--inflight .hero__icon::before {
  content: ""; position: absolute; width: 56px; height: 56px; border-radius: 50%;
  background: color-mix(in srgb, var(--p-info) 14%, transparent);
  animation: halo 2.2s ease-in-out infinite;
  pointer-events: none;
}
@keyframes halo {
  0%, 100% { opacity: .35; transform: scale(1); }
  50% { opacity: .12; transform: scale(1.15); }
}
@media (prefers-reduced-motion: reduce) {
  .hero__icon::before { animation: none; }
}
.hero__icon .material-symbols-outlined { font-size: 26px; font-variation-settings: 'wght' 400; }
.hero__body { min-width: 0; }
.hero__kicker {
  font: 500 11px/1 var(--md-font-plain);
  letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--md-on-surface-faint);
  margin-bottom: 6px;
}
.hero__title {
  font: 500 20px/1.25 var(--md-font-brand);
  color: var(--md-on-surface);
  margin-bottom: 10px;
}
.hero__title a { color: inherit; text-decoration: none; }
.hero__title a:hover { color: var(--p-info); }
.hero__row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.hero__hint { color: var(--md-on-surface-muted); font-size: 13px; }
.hero__right { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; min-width: 200px; }
.hero__big { font: 500 28px/1 var(--md-font-data); letter-spacing: -0.01em; }
.hero__big small { font-weight: 400; font-size: 13px; color: var(--md-on-surface-faint); letter-spacing: 0; }
.hero__lbl { color: var(--md-on-surface-faint); font-size: 11.5px; letter-spacing: 0.08em; text-transform: uppercase; }

/* In-flight hero expands to wrap a stages list */
.hero--inflight { display: block; }
.hero--inflight .hero__top {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 20px;
  align-items: center;
}
.hero--inflight .hero__divider {
  height: 1px;
  background: var(--md-outline-hair);
  margin: 22px -24px 18px;
}

/* Horizontal timeline (spec 0177 §2.2) — replaces the prior vertical
   `.stages` list. Each stage is a `.tl__step` that sits in an equal-width
   grid column under the in-flight hero. Two rails behind the nodes: the
   grey base rail spans the full width, the ok-coloured `.tl__rail-done`
   overlay is sized at render time to (done_count / total) of the row. */
.tl { position: relative; padding: 4px 0 8px; }
.tl__rail {
  position: absolute; left: 14px; right: 14px; top: 18px;
  height: 3px; background: var(--md-outline-hair); border-radius: 2px;
  z-index: 0;
}
.tl__rail-done {
  position: absolute; left: 14px; top: 18px; height: 3px;
  background: color-mix(in srgb, var(--p-ok) 70%, var(--md-outline-hair));
  border-radius: 2px;
  z-index: 1;
}
.tl__steps {
  display: grid; grid-auto-flow: column; grid-auto-columns: 1fr;
  position: relative; z-index: 2;
}
.tl__step {
  display: flex; flex-direction: column; align-items: center;
  gap: 8px; padding: 0 4px; text-align: center; min-width: 0;
}
.tl__node {
  width: 28px; height: 28px; border-radius: 50%;
  display: grid; place-items: center;
  background: var(--md-surface-container-high);
  color: var(--md-on-surface-faint);
  font: 600 13px/1 var(--md-font-plain);
  border: 2px solid var(--md-surface-dim);
  position: relative;
}
.tl__step--done .tl__node {
  background: color-mix(in srgb, var(--p-ok) 28%, var(--md-surface-container-high));
  color: var(--p-ok);
}
.tl__step--done .tl__node::after { content: "\\2713"; }
.tl__step--curr .tl__node {
  background: color-mix(in srgb, var(--p-info) 32%, var(--md-surface-container-high));
  color: var(--p-info);
}
.tl__step--curr .tl__node::before {
  content: ""; position: absolute; inset: -6px; border-radius: 50%;
  background: color-mix(in srgb, var(--p-info) 16%, transparent);
  animation: halo 2.2s ease-in-out infinite;
}
.tl__step--curr .tl__node::after {
  content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--p-info);
}
.tl__step--queued .tl__node { background: var(--md-surface-container); color: var(--md-on-surface-decor); }
.tl__step--fail .tl__node {
  background: color-mix(in srgb, var(--p-err) 28%, var(--md-surface-container-high));
  color: var(--p-err);
}
.tl__step--fail .tl__node::after { content: "!"; }
.tl__lbl {
  font: 500 11px/1.25 var(--md-font-plain);
  color: var(--md-on-surface);
  max-width: 100%; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap;
}
.tl__step--queued .tl__lbl { color: var(--md-on-surface-decor); font-weight: 400; }
.tl__step--done .tl__lbl   { color: var(--md-on-surface-variant); }
.tl__step--curr .tl__lbl   { color: var(--p-info); font-weight: 600; }
.tl__dur {
  font: 400 10.5px/1 var(--md-font-data);
  color: var(--md-on-surface-faint);
  letter-spacing: 0.02em;
}
.tl__step--curr .tl__dur { color: var(--p-info); font-weight: 500; }
@media (prefers-reduced-motion: reduce) {
  .tl__step--curr .tl__node::before { animation: none; }
}

/* Pipeline strip */
.pipe {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px;
  padding: 18px 22px;
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-hair);
  border-radius: 14px;
  margin-top: 16px;
}
.pipe__col { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
.pipe__lbl {
  font: 500 11px/1 var(--md-font-plain);
  letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--md-on-surface-faint);
}
.pipe__num { font: 500 22px/1 var(--md-font-data); }
.pipe__num.is-zero { color: var(--md-on-surface-decor); font-weight: 400; }
.pipe__bar { height: 6px; width: 100%; border-radius: 3px; background: var(--md-surface-container-highest); }
.pipe__bar--draft { background: color-mix(in srgb, var(--md-on-surface-faint) 35%, var(--md-surface-container-highest)); }
.pipe__bar--queued { background: color-mix(in srgb, var(--p-idle) 60%, var(--md-surface-container-highest)); }
.pipe__bar--inflight { background: var(--p-info); }
.pipe__bar--merged { background: color-mix(in srgb, var(--p-ok) 45%, var(--md-surface-container-highest)); }
.pipe__bar--deployed { background: var(--p-ok); }

/* Metrics grid */
.metrics {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 12px;
}
.metric {
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-hair);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 6px;
}
.metric__lbl {
  font: 500 11px/1 var(--md-font-plain);
  letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--md-on-surface-faint);
}
.metric__val { font: 500 22px/1 var(--md-font-data); }
.metric__sub { font-size: 11.5px; color: var(--md-on-surface-muted); }
.metric__sub .delta-up { color: var(--p-ok); }
.metric__sub .delta-down { color: var(--p-warn); }

/* Queue table */
.qtable {
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-hair);
  border-radius: 12px;
  overflow: hidden;
}
.qrow {
  display: grid; grid-template-columns: 44px 76px 1fr 130px 100px;
  gap: 12px; align-items: center;
  padding: 12px 16px;
  border-top: 1px solid var(--md-outline-hair);
}
.qrow:first-of-type { border-top: 0; }
.qrow--header {
  background: var(--md-surface-container-low);
  color: var(--md-on-surface-faint);
  font: 500 11px/1 var(--md-font-plain);
  letter-spacing: 0.10em; text-transform: uppercase;
  padding: 10px 16px;
}
.qrow__pos { font: 500 13px/1 var(--md-font-data); color: var(--md-on-surface-variant); }
.qrow__id  { font: 500 13px/1 var(--md-font-data); color: var(--md-on-surface); }
.qrow__id a { color: inherit; text-decoration: none; border-bottom: 1px dotted var(--md-outline-variant); }
.qrow__id a:hover { color: var(--p-info); border-bottom-color: var(--p-info); }
.qrow__title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.qrow__age { color: var(--md-on-surface-muted); font-size: 12px; font-family: var(--md-font-data); text-align: right; }
.qrow--empty { padding: 22px 16px; color: var(--md-on-surface-faint); text-align: center; font-size: 13px; }

/* Activity feed */
.feed { display: flex; flex-direction: column; }
.feed__row {
  display: grid; grid-template-columns: 140px 28px 1fr 80px;
  gap: 14px; align-items: baseline;
  padding: 10px 0;
  border-top: 1px dashed var(--md-outline-hair);
}
.feed__row:first-child { border-top: 0; }
.feed__ts {
  font: 400 12px/1.2 var(--md-font-data);
  color: var(--md-on-surface-faint);
  letter-spacing: 0.02em;
}
.feed__step .material-symbols-outlined { font-size: 18px; vertical-align: middle; }
.feed__step--ok { color: var(--p-ok); }
.feed__step--info { color: var(--p-info); }
.feed__step--warn { color: var(--p-warn); }
.feed__step--err { color: var(--p-err); }
.feed__step--neutral { color: var(--md-on-surface-faint); }
.feed__what { font-size: 13.5px; }
.feed__what a { color: var(--md-on-surface); text-decoration: none; border-bottom: 1px dotted var(--md-outline-variant); }
.feed__what a:hover { color: var(--p-info); border-bottom-color: var(--p-info); }
.feed__what .kicker {
  display: inline-block; min-width: 80px;
  font: 500 11px/1 var(--md-font-plain);
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--md-on-surface-faint);
  margin-right: 8px;
}
.feed__dur { color: var(--md-on-surface-faint); font-family: var(--md-font-data); font-size: 12px; text-align: right; }

/* Drafts */
.drafts {
  background: var(--md-surface-container-low);
  border: 1px solid var(--md-outline-hair);
  border-radius: 12px;
  overflow: hidden;
}
.draft-row {
  display: grid; grid-template-columns: 60px 1fr 140px 100px;
  gap: 12px; align-items: center;
  padding: 10px 16px;
  border-top: 1px dashed var(--md-outline-hair);
}
.draft-row:first-child { border-top: 0; }
.draft-row__id { font: 500 12px/1 var(--md-font-data); color: var(--md-on-surface-faint); }
.draft-row__title { font-size: 13px; }
.draft-row__title a { color: var(--md-on-surface); text-decoration: none; }
.draft-row__title a:hover { color: var(--p-info); }
.draft-row__age { color: var(--md-on-surface-faint); font-family: var(--md-font-data); font-size: 12px; text-align: right; }

/* Chip tweaks (DS chip is the base) */
.chip { font-family: var(--md-font-plain); }
.chip-type { text-transform: uppercase; letter-spacing: 0.08em; font-size: 10.5px; }

/* Footer */
.foot {
  margin-top: 56px;
  padding-top: 18px;
  border-top: 1px solid var(--md-outline-hair);
  color: var(--md-on-surface-decor);
  font-size: 12px;
  display: flex; justify-content: space-between; align-items: center;
}
.foot a { color: var(--md-on-surface-faint); text-decoration: none; border-bottom: 1px dotted var(--md-outline-variant); }

@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; }
  .hero__right { align-items: flex-start; }
  .pipe { grid-template-columns: repeat(2, 1fr); }
  .metrics { grid-template-columns: repeat(2, 1fr); }
  .qrow, .qrow--header { grid-template-columns: 36px 70px 1fr 90px; }
  .qrow__age { display: none; }
  .feed__row { grid-template-columns: 110px 22px 1fr; }
  .feed__dur { display: none; }
  .stage { grid-template-columns: 24px 110px 1fr 60px; }
}

/* Shell mode skeletons (spec 0160). The bootstrap script swaps these out
   once /api/data resolves. Shapes match populated state to limit reflow. */
.region-skeleton { display: block; }
.region-skeleton .skeleton__line,
.region-skeleton .skeleton__icon {
  background: color-mix(in srgb, var(--md-on-surface-faint) 12%, var(--md-surface-container));
  border-radius: 4px;
  height: 16px;
  margin: 6px 0;
  width: 100%;
}
.region-skeleton .skeleton__line--header { width: 40%; height: 18px; margin-bottom: 14px; }
.region-skeleton .skeleton__line--kicker { width: 35%; height: 11px; }
.region-skeleton .skeleton__line--title  { width: 70%; height: 22px; }
.region-skeleton .skeleton__line--label  { width: 50%; height: 11px; }
.region-skeleton .skeleton__line--num    { width: 30%; height: 22px; margin-top: 4px; }
.region-skeleton .skeleton__line--big    { width: 60%; height: 28px; }
.region-skeleton .skeleton__icon {
  width: 44px; height: 44px; border-radius: 50%; margin: 0;
}
@keyframes skeleton-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
.region-skeleton .skeleton__line,
.region-skeleton .skeleton__icon { animation: skeleton-pulse 1.6s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) {
  .region-skeleton .skeleton__line,
  .region-skeleton .skeleton__icon { animation: none; }
}

/* `stale` chip in the header when /api/data fetch fails and the bootstrap
   script repaints from localStorage. Spec 0160 §3 error states. */
.dh__meta .chip.tone-warn { background: color-mix(in srgb, var(--p-warn) 18%, transparent); color: var(--p-warn); }

/* ════════════════════════════════════════════════════════════════════
   Spec 0169 — Dashboard redesign v2
   Theme shim · callout strip · tabs · total-elapsed banner
   ════════════════════════════════════════════════════════════════════ */

/* ─── Theme shim (spec 0169 §2.7) ────────────────────────────────────
   The DS canonical tokens.css keys dark-mode overrides by
   prefers-color-scheme. The dashboard's manual toggle needs to override
   the OS preference, so we project the dark deltas onto the
   [data-theme="dark"] selector explicitly. [data-theme="auto"] is the
   default — it lets the existing prefers-color-scheme media inside
   tokens.css drive the page.

   `color-scheme` on the <html> tells the browser's UA which native
   form-control palette to use; we set it explicitly per data-theme so
   scrollbars and form controls follow the manual override.

   The actual token re-projection (the meaty color overrides) lives in
   the `body.dark` block at the bottom of tokens.css. Dashboard-live.js
   toggles `body.dark` / `body.light` in tandem with html[data-theme] so
   the same selectors fire whether the OS preference matches or a
   manual toggle is in play.
   ──────────────────────────────────────────────────────────────────── */
html[data-theme="dark"]  { color-scheme: dark; }
html[data-theme="light"] { color-scheme: light; }
html[data-theme="auto"]  { color-scheme: light dark; }

/* ─── Hero + counter row layout (spec 0177 §2.1) ─────────────────────
   The `.strip` wrapper from spec 0169 used to be a 3-column grid that
   pinned the avg-cycle card next to the counters and made the in-flight
   hero stack a narrow timeline alongside it. v3 lets the hero span the
   full container width with the horizontal timeline beneath, and folds
   the avg-cycle card into the counter row as its 5th counter. `.strip`
   becomes `display: contents` so its children (hero region, counters
   region) become direct block children of `.page`.
   ──────────────────────────────────────────────────────────────────── */
.strip { display: contents; }
.strip > [data-region="hero"] { display: block; margin-bottom: 12px; }
.strip > [data-region="counters"] { display: block; }
.strip .hero { margin: 0; }

/* Counter row — 5 cards in one full-width row. The accent variant
   carries the avg-cycle counter (rolling-10 mean + delta + sparkline).
   The other four counters keep their plain shape. */
.counters {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 8px;
}
.counter {
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-hair);
  border-radius: var(--md-shape-lg);
  padding: 14px 16px;
  display: flex; flex-direction: column; gap: 6px;
  min-width: 0;
}
.counter__lbl {
  font: var(--md-w-medium) 10.5px/1 var(--md-font-plain);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--md-on-surface-faint);
}
.counter__num {
  font: var(--md-w-semi) 26px/1 var(--md-font-data);
  color: var(--md-on-surface);
  font-variant-numeric: tabular-nums;
}
.counter__num.is-zero { color: var(--md-on-surface-decor); font-weight: 400; }
.counter__sub {
  font: 11.5px/1.3 var(--md-font-plain);
  color: var(--md-on-surface-faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.counter__sub .delta-up   { color: var(--p-ok); }
.counter__sub .delta-down { color: var(--p-warn); }
.counter--accent .counter__num { color: var(--p-info); }
.counter__spark {
  margin-top: 2px;
  width: 100%;
  height: 24px;
  display: block;
  color: var(--p-info);
}

@media (max-width: 1100px) {
  .counters { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 700px) {
  .counters { grid-template-columns: repeat(2, 1fr); }
}

/* ─── Tab bar (spec 0169 §2.2) ─────────────────────────────────────── */
.tabs {
  display: flex;
  gap: 4px;
  margin: 20px 0 12px;
  border-bottom: 1px solid var(--md-outline-hair);
  flex-wrap: wrap;
}
.tabs .tab {
  background: transparent;
  border: 0;
  padding: 10px 14px 11px;
  font: var(--md-w-medium) 13px/1 var(--md-font-plain);
  color: var(--md-on-surface-variant);
  cursor: pointer;
  position: relative;
  border-radius: var(--md-shape-md) var(--md-shape-md) 0 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background var(--md-dur-short-3) var(--md-easing-standard),
              color      var(--md-dur-short-3) var(--md-easing-standard);
}
.tabs .tab:hover {
  background: color-mix(in srgb, var(--md-on-surface) 6%, transparent);
  color: var(--md-on-surface);
}
.tabs .tab:focus-visible { outline: 2px solid var(--md-primary); outline-offset: -2px; }
.tabs .tab[aria-selected="true"] { color: var(--md-on-surface); font-weight: var(--md-w-semi); }
.tabs .tab[aria-selected="true"]::after {
  content: "";
  position: absolute;
  left: 8px; right: 8px; bottom: -1px;
  height: 2px;
  background: var(--p-info);
  border-radius: 1px;
}
.tabs .tab__count {
  font: var(--md-w-regular) 11px/1 var(--md-font-data);
  color: var(--md-on-surface-faint);
  padding: 2px 6px;
  border-radius: var(--md-shape-full);
  background: color-mix(in srgb, var(--md-on-surface) 8%, transparent);
}
.tabs .tab[aria-selected="true"] .tab__count {
  background: color-mix(in srgb, var(--p-info) 14%, transparent);
  color: var(--p-info);
}

.tab-panel { display: none; margin: 8px 0 16px; }
.tab-panel[aria-hidden="false"] { display: block; }

/* ─── Total-elapsed banner (spec 0169 §2.5) ─────────────────────────── */
.te-banner {
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-hair);
  border-radius: var(--md-shape-lg);
  padding: 14px 16px 16px;
  margin-bottom: 20px;
}
.te-banner__row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-top: 10px;
}
.te-banner__empty { padding: 20px 0; text-align: center; color: var(--md-on-surface-faint); }
.te-tile { display: flex; flex-direction: column; min-width: 0; }
.te-tile__lbl {
  font: var(--md-w-medium) 10.5px/1 var(--md-font-plain);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--md-on-surface-faint);
  margin-bottom: 6px;
}
.te-tile__val {
  font: var(--md-w-semi) 24px/1.1 var(--md-font-data);
  color: var(--md-on-surface);
  font-variant-numeric: tabular-nums;
}
.te-tile__val small {
  font: var(--md-w-regular) 16px/1 var(--md-font-data);
  color: var(--md-on-surface-faint);
  margin: 0 4px;
}
.te-tile__sub { font: 11px/1.4 var(--md-font-plain); color: var(--md-on-surface-faint); margin-top: 6px; }

@media (max-width: 1100px) {
  .te-banner__row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .te-banner__row { grid-template-columns: 1fr; }
}

/* ─── Theme toggle button (spec 0169 §2.7) ──────────────────────────── */
.theme-toggle {
  background: transparent;
  border: 1px solid var(--md-outline-hair);
  border-radius: var(--md-shape-full);
  padding: 4px 10px 4px 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font: var(--md-w-medium) 12px/1 var(--md-font-plain);
  color: var(--md-on-surface-variant);
  cursor: pointer;
  transition: background var(--md-dur-short-3) var(--md-easing-standard),
              border-color var(--md-dur-short-3) var(--md-easing-standard),
              color var(--md-dur-short-3) var(--md-easing-standard);
}
.theme-toggle:hover {
  background: color-mix(in srgb, var(--md-on-surface) 6%, transparent);
  border-color: var(--md-outline);
  color: var(--md-on-surface);
}
.theme-toggle:focus-visible { outline: 2px solid var(--md-primary); outline-offset: 2px; }
.theme-toggle .material-symbols-outlined { font-size: 16px; }
.theme-toggle__label { letter-spacing: 0.04em; }

@media (prefers-reduced-motion: reduce) {
  .theme-toggle,
  .tabs .tab,
  .strip,
  .te-banner { transition: none !important; }
}

/* ════════════════════════════════════════════════════════════════════
   Spec 0177 — Dashboard redesign v3
   Metrics tab populate · pagination · history-table columns
   ════════════════════════════════════════════════════════════════════ */

/* ─── Metrics tab: callout strip (spec 0177 §2.4.1) ─────────────────── */
.callouts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.callout {
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-hair);
  border-radius: var(--md-shape-md);
  padding: 14px 16px;
  display: flex; gap: 12px; align-items: flex-start;
  min-width: 0;
}
.callout__icon {
  width: 32px; height: 32px; border-radius: 8px;
  display: grid; place-items: center; flex-shrink: 0;
  background: color-mix(in srgb, var(--p-info) 18%, transparent);
  color: var(--p-info);
  font: var(--md-w-semi) 16px/1 var(--md-font-plain);
}
.callout--ok .callout__icon   { background: color-mix(in srgb, var(--p-ok) 18%, transparent);   color: var(--p-ok); }
.callout--warn .callout__icon { background: color-mix(in srgb, var(--p-warn) 18%, transparent); color: var(--p-warn); }
.callout__body { min-width: 0; }
.callout__lbl {
  font: var(--md-w-medium) 10.5px/1 var(--md-font-plain);
  letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--md-on-surface-faint);
  margin-bottom: 4px;
}
.callout__val {
  font: var(--md-w-semi) 18px/1.2 var(--md-font-data);
  color: var(--md-on-surface);
}
.callout__sub {
  font: 11.5px/1.4 var(--md-font-plain);
  color: var(--md-on-surface-variant);
  margin-top: 4px;
}

/* ─── Metrics tab: chart cards + grid (spec 0177 §2.4) ──────────────── */
.charts-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.charts-grid--3 { grid-template-columns: 1fr 1fr 1fr; }
.chart-card {
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-hair);
  border-radius: var(--md-shape-lg);
  padding: 16px 18px;
  min-width: 0;
}
.chart-card__title {
  font: var(--md-w-medium) 13px/1.2 var(--md-font-plain);
  color: var(--md-on-surface);
  margin-bottom: 2px;
}
.chart-card__sub {
  font: 11.5px/1.4 var(--md-font-plain);
  color: var(--md-on-surface-faint);
  margin-bottom: 12px;
}
.chart-card__legend {
  display: flex; gap: 14px; flex-wrap: wrap;
  font: 11px/1 var(--md-font-plain);
  color: var(--md-on-surface-variant);
  margin-top: 10px;
}
.chart-card__legend .lg__sw {
  display: inline-block;
  width: 10px; height: 10px;
  border-radius: 2px; margin-right: 6px;
  vertical-align: middle;
}
svg.chart { width: 100%; display: block; }

/* Horizontal bar list — used for the "by type" breakdown. */
.bar-list { display: flex; flex-direction: column; gap: 10px; }
.bar-row {
  display: grid; grid-template-columns: 100px 1fr 70px;
  gap: 12px; align-items: center;
}
.bar-row__lbl {
  font: 12.5px/1 var(--md-font-plain);
  color: var(--md-on-surface-variant);
  text-transform: capitalize;
}
.bar-row__track {
  height: 10px; border-radius: 5px;
  background: var(--chart-track);
  overflow: hidden; position: relative;
}
.bar-row__fill { height: 100%; border-radius: 5px; }
.bar-row__val {
  font: var(--md-w-medium) 12px/1 var(--md-font-data);
  color: var(--md-on-surface);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.metrics-empty {
  padding: 20px;
  text-align: center;
  color: var(--md-on-surface-faint);
  font: 12px/1.5 var(--md-font-plain);
}

@media (max-width: 1100px) {
  .callouts { grid-template-columns: 1fr; }
  .charts-grid, .charts-grid--3 { grid-template-columns: 1fr; }
}

/* ─── History tab: 6-column All-specs grid (spec 0177 §2.3) ─────────── */
.qrow--history,
.qrow--history-header {
  grid-template-columns: 70px 1fr 110px 100px 90px 90px;
}
.qrow--history-header { padding: 10px 16px; }
.qrow--history .qrow__age { text-align: right; }

@media (max-width: 1100px) {
  .qrow--history,
  .qrow--history-header { grid-template-columns: 60px 1fr 90px 90px 80px 80px; }
}
@media (max-width: 700px) {
  .qrow--history,
  .qrow--history-header { grid-template-columns: 60px 1fr 80px 70px; }
  .qrow--history > :nth-child(5),
  .qrow--history > :nth-child(6),
  .qrow--history-header > :nth-child(5),
  .qrow--history-header > :nth-child(6) { display: none; }
}

/* ─── Pagination strip (spec 0177 §2.6) ─────────────────────────────────
   New `.pager` component. Lands in both the canonical design-system
   composed-components.css AND the live-app components.css in the same
   spec (DS sync rule from CLAUDE.md). This block in dashboard.css is
   the dashboard-specific tuning; the structural rules are in the DS.
   ──────────────────────────────────────────────────────────────────── */
.pager {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; padding: 10px 4px 0;
  font: 12px/1 var(--md-font-plain);
  color: var(--md-on-surface-faint);
}
.pager__count {
  font-family: var(--md-font-data);
  font-variant-numeric: tabular-nums;
}
.pager__nav { display: flex; gap: 4px; align-items: center; }
.pager__btn {
  background: var(--md-surface-container);
  border: 1px solid var(--md-outline-hair);
  border-radius: var(--md-shape-sm);
  padding: 5px 10px;
  font: var(--md-w-medium) 12px/1 var(--md-font-plain);
  color: var(--md-on-surface-variant);
  cursor: pointer;
  min-width: 30px;
  transition: background var(--md-dur-short-3) var(--md-easing-standard),
              border-color var(--md-dur-short-3) var(--md-easing-standard),
              color var(--md-dur-short-3) var(--md-easing-standard);
}
.pager__btn:hover {
  border-color: var(--md-outline);
  color: var(--md-on-surface);
}
.pager__btn[aria-current="page"] {
  background: color-mix(in srgb, var(--p-info) 14%, var(--md-surface-container));
  border-color: color-mix(in srgb, var(--p-info) 40%, var(--md-outline-hair));
  color: var(--p-info);
  font-weight: var(--md-w-semi);
}
.pager__btn[disabled] { opacity: 0.4; cursor: not-allowed; }
.pager__btn[disabled]:hover { border-color: var(--md-outline-hair); color: var(--md-on-surface-variant); }
.pager__ellipsis { color: var(--md-on-surface-decor); padding: 0 4px; }

@media (prefers-reduced-motion: reduce) {
  .pager__btn { transition: none !important; }
}

/* ─── Timeline responsive collapse (spec 0177 §2.2) ─────────────────── */
@media (max-width: 700px) {
  .tl__steps { overflow-x: auto; }
  .hero--inflight .hero__right { display: none; }
}
"""


# ── Live ticker JS (spec 0156 §2.3) ────────────────────────────────────────

DASHBOARD_LIVE_JS = """\
// dashboard-live.js — increment elapsed durations every second without a
// page reload. Powered by data attributes that the server emits:
//   data-cycle-started-at  — on the in-flight hero's ELAPSED display.
//   data-stage-started-at  — on the current stage row's duration cell.
//   data-last-event-at     — on the staleness chip (spec 0163 §2.4).
// Spec 0156 §2.3, extended by spec 0163 §2.4. Tiny on purpose: no external
// deps, no framework.

(function () {
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    // Reduced-motion users see static server-side timings.
    return;
  }

  // Spec 0163 §2.4 staleness thresholds — must match _STALE_WARN_SECONDS /
  // _STALE_DANGER_SECONDS in scripts/spec_lifecycle/render_dashboard.py.
  var STALE_WARN_S = 30;
  var STALE_DANGER_S = 120;
  var STALE_TONES = ['tone-ok', 'tone-warn', 'tone-err', 'tone-neutral'];

  function fmt(seconds) {
    if (seconds < 0) seconds = 0;
    if (seconds < 60) return seconds + 's';
    var minutes = Math.floor(seconds / 60);
    var sec = seconds % 60;
    if (minutes < 60) return sec === 0 ? minutes + 'm' : minutes + 'm ' + sec + 's';
    var hours = Math.floor(minutes / 60);
    var mins = minutes % 60;
    if (hours < 24) return mins === 0 ? hours + 'h' : hours + 'h ' + mins + 'm';
    var days = Math.floor(hours / 24);
    var hrs = hours % 24;
    return hrs === 0 ? days + 'd' : days + 'd ' + hrs + 'h';
  }

  function staleTone(seconds) {
    if (seconds === null) return 'tone-neutral';
    if (seconds < STALE_WARN_S) return 'tone-ok';
    if (seconds < STALE_DANGER_S) return 'tone-warn';
    return 'tone-err';
  }

  function tick() {
    var now = Date.now();
    // Cycle elapsed display (the hero's big number).
    document.querySelectorAll('[data-cycle-started-at]').forEach(function (el) {
      var raw = el.getAttribute('data-cycle-started-at');
      if (!raw) return;
      var startMs = Date.parse(raw);
      if (isNaN(startMs)) return;
      el.textContent = fmt(Math.floor((now - startMs) / 1000));
    });
    // Current-stage duration cell.
    document.querySelectorAll('[data-stage-started-at]').forEach(function (el) {
      var raw = el.getAttribute('data-stage-started-at');
      if (!raw) return;
      var startMs = Date.parse(raw);
      if (isNaN(startMs)) return;
      el.textContent = fmt(Math.floor((now - startMs) / 1000));
    });
    // Spec 0163 §2.4 — staleness chip text + tone.
    document.querySelectorAll('[data-last-event-at]').forEach(function (el) {
      var raw = el.getAttribute('data-last-event-at');
      var ageSec = null;
      if (raw) {
        var t = Date.parse(raw);
        if (!isNaN(t)) ageSec = Math.max(0, Math.floor((now - t) / 1000));
      }
      var nextTone = staleTone(ageSec);
      STALE_TONES.forEach(function (cls) { el.classList.remove(cls); });
      el.classList.add(nextTone);
      el.textContent = 'last event ' + (ageSec === null ? '—' : fmt(ageSec)) + ' ago';
    });
  }

  // Initial paint synchronises with whatever the server rendered, then we
  // re-paint every second.
  tick();
  setInterval(tick, 1000);

  // Spec 0169 §2.2 — tab switching. CSS-only show/hide via aria-hidden.
  // No router, no state persistence between visits.
  function activateTab(slug) {
    document.querySelectorAll('.tabs .tab').forEach(function (b) {
      b.setAttribute('aria-selected', b.getAttribute('data-tab') === slug ? 'true' : 'false');
    });
    document.querySelectorAll('.tab-panel').forEach(function (p) {
      p.setAttribute('aria-hidden', p.getAttribute('data-panel') === slug ? 'false' : 'true');
    });
  }
  document.querySelectorAll('.tabs .tab').forEach(function (b) {
    b.addEventListener('click', function () { activateTab(b.getAttribute('data-tab')); });
    b.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        activateTab(b.getAttribute('data-tab'));
      }
    });
  });

  // Spec 0169 §2.7 — theme toggle. Cycles light → dark → auto and
  // persists to localStorage. The inline <head> script already set the
  // initial data-theme attribute before this script ran; here we wire
  // the click handler + the body.dark/body.light mirroring (so the
  // tokens.css overrides keyed on body.dark fire under manual toggle).
  var THEMES = ['light', 'dark', 'auto'];
  var THEME_ICONS = { light: 'light_mode', dark: 'dark_mode', auto: 'brightness_auto' };
  function applyTheme(theme) {
    if (THEMES.indexOf(theme) < 0) theme = 'auto';
    document.documentElement.setAttribute('data-theme', theme);
    // Mirror onto body.dark / body.light so the existing tokens.css
    // overrides (keyed on body.dark) fire under manual override.
    document.body.classList.remove('dark', 'light');
    if (theme === 'dark') document.body.classList.add('dark');
    if (theme === 'light') document.body.classList.add('light');
    // auto: leave body class alone — prefers-color-scheme drives it.
    try { localStorage.setItem('dr-dashboard-theme', theme); } catch (e) { /* quota */ }
    var icon = document.querySelector('[data-theme-icon]');
    var label = document.querySelector('[data-theme-label]');
    if (icon) icon.textContent = THEME_ICONS[theme] || 'brightness_auto';
    if (label) label.textContent = theme;
  }
  var toggleBtn = document.getElementById('theme-toggle');
  if (toggleBtn) {
    var saved = (function () { try { return localStorage.getItem('dr-dashboard-theme'); } catch (e) { return null; } })();
    // Spec 0177 §2.7 — default for first-visit users is 'light' (was 'auto').
    if (saved && THEMES.indexOf(saved) >= 0) applyTheme(saved);
    else applyTheme('light');
    toggleBtn.addEventListener('click', function () {
      var current = document.documentElement.getAttribute('data-theme') || 'auto';
      var idx = THEMES.indexOf(current);
      var next = THEMES[(idx + 1) % THEMES.length];
      applyTheme(next);
    });
  }
})();
"""


# ── Live data bootstrap (spec 0160) ────────────────────────────────────────

DASHBOARD_BOOTSTRAP_JS = """\
// dashboard-bootstrap.js (spec 0160 + spec 0174) — fetch live data from the
// Cloudflare Pages Function at /api/data and populate the dashboard's
// data-region containers. Polls every 5s (was 15s; the underlying Function
// edge-caches responses for 15s so most polls hit Cloudflare's cache and
// don't reach GitHub). On error: fall back to localStorage cache with a
// `stale` chip. No-op gracefully if /api/data is unreachable (e.g. local
// preview without the Function running) — the server-rendered content
// stays in place.

(function () {
  'use strict';

  var POLL_MS = 5000;
  var CACHE_KEY = 'dr-dashboard-data-v1';
  var ESC = function (s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  };

  // Spec 0163 §2.3 — must mirror STEP_LABELS in scripts/spec_lifecycle/stages.py.
  // Used by the "currently: <step>" chip on the in-flight hero.
  var STEP_LABELS = {
    'queued': 'queued',
    'cycle_started': 'starting',
    'preflight_ok': 'pre-flight',
    'handoff_read': 'reading handoff',
    'spec_read': 'reading spec',
    'planning_started': 'planning',
    'reconcile_complete': 'reconciled',
    'in_progress': 'starting',
    'branched': 'branched',
    'implementing_started': 'implementing',
    'implement_complete': 'implement done',
    'tests_started': 'testing',
    'tests_green': 'tests green',
    'pr_opened': 'PR opened',
    'merged': 'merged',
    'deploy_started': 'deploying',
    'deployed': 'deployed',
    'deploy_health_check_ok': 'health check ok',
    'handoff_written': 'handoff written'
  };

  // Spec 0177 §2.2 — STAGE_DEFS must mirror STAGES in
  // scripts/spec_lifecycle/stages.py. Each entry is [name, completedStep].
  // The bootstrap re-implements compute_stages so the horizontal timeline
  // survives the 5s /api/data refresh (previously the timeline was server-
  // rendered only, then wiped on first bootstrap repaint).
  var STAGE_DEFS = [
    ['Pre-flight',   'preflight_ok'],
    ['Read handoff', 'handoff_read'],
    ['Read spec',    'spec_read'],
    ['Reconcile',    'reconcile_complete'],
    ['Branch',       'branched'],
    ['Implement',    'implement_complete'],
    ['Test',         'tests_green'],
    ['PR',           'pr_opened'],
    ['Merge',        'merged'],
    ['Deploy',       'deployed'],
    ['Handoff',      'handoff_written']
  ];

  // Spec 0177 §2.6 pager state. Page index per section name; consulted
  // by paint() after each refresh so the user doesn't get bounced back
  // to page 1 every 5s.
  var pagerState = {};
  var PAGER_PAGE_SIZE = 10;

  // Spec 0163 §2.4 staleness thresholds — must match _STALE_*_SECONDS in
  // scripts/spec_lifecycle/render_dashboard.py.
  var STALE_WARN_S = 30;
  var STALE_DANGER_S = 120;

  function staleTone(seconds) {
    if (seconds === null) return 'tone-neutral';
    if (seconds < STALE_WARN_S) return 'tone-ok';
    if (seconds < STALE_DANGER_S) return 'tone-warn';
    return 'tone-err';
  }
  function stepLabel(step) {
    if (!step) return '';
    return STEP_LABELS[step] || step.replace(/_/g, ' ');
  }

  // ── Time/duration helpers (mirror Python _humanize_seconds / _ago) ──────
  function humanizeSec(s) {
    if (s === null || s === undefined || s < 0) return '—';
    if (s < 60) return s + 's';
    var m = Math.floor(s / 60), sec = s % 60;
    if (m < 60) return sec === 0 ? m + 'm' : m + 'm ' + sec + 's';
    var h = Math.floor(m / 60), min = m % 60;
    if (h < 24) return min === 0 ? h + 'h' : h + 'h ' + min + 'm';
    var d = Math.floor(h / 24), hr = h % 24;
    return hr === 0 ? d + 'd' : d + 'd ' + hr + 'h';
  }
  function ago(iso, nowMs) {
    if (!iso) return '—';
    var t = Date.parse(iso);
    if (isNaN(t)) return '—';
    return humanizeSec(Math.floor((nowMs - t) / 1000)) + ' ago';
  }

  // ── Chips, type → tone (mirror Python _TYPE_TONE) ───────────────────────
  var TYPE_TONE = {
    'new-feature': 'info', 'bug': 'err', 'refactoring': 'warn',
    'test': 'neutral', 'breaking': 'warn', 'unclassified': 'neutral'
  };
  function typeChip(type) {
    var tone = TYPE_TONE[type] || 'neutral';
    return '<span class="chip chip-type tone-' + tone + ' no-dot">' + ESC(type || '—') + '</span>';
  }
  function statusChip(status) {
    var tone = ({'deployed':'ok','merged':'ok','in_progress':'info','queued':'neutral','failed':'err'})[status] || 'neutral';
    return '<span class="chip tone-' + tone + '">' + ESC(status || '—') + '</span>';
  }

  // Spec 0177 §2.2 — compute stage states for an in-flight spec from its
  // event log. Mirrors stages.py:compute_stages but trimmed: we don't
  // compute durations (the server already rendered them and they don't
  // change often within a 5s refresh window), only done/curr/queued.
  // Spec 0182 — computeStages now also walks event timestamps to derive
  // per-stage duration_seconds, mirroring the server-side algorithm at
  // stages.compute_stages. Without this, every completed stage's
  // .tl__dur flipped to em-dash after each 5s repaint.
  function computeStages(events, failureStep) {
    var byStep = {};
    events.forEach(function (e) {
      var step = e && e.step;
      if (step && !(step in byStep)) byStep[step] = e;
    });
    var failIdx = null;
    if (failureStep) {
      var key = String(failureStep).toLowerCase().replace(/[ -]/g, '_');
      for (var fi = 0; fi < STAGE_DEFS.length; fi++) {
        if (key === STAGE_DEFS[fi][0].toLowerCase().replace(/[ -]/g, '_')) {
          failIdx = fi; break;
        }
      }
    }
    var currIdx = null;
    if (failIdx === null) {
      for (var i = 0; i < STAGE_DEFS.length; i++) {
        if (STAGE_DEFS[i][1] in byStep) continue;
        if (i === 0 || STAGE_DEFS[i - 1][1] in byStep) { currIdx = i; break; }
      }
    }
    // Anchor preference must mirror stages.py:225-229 — cycle_started
    // first, then queued, then in_progress. Historical specs (pre
    // spec 0156) only have in_progress; new specs have all three.
    function _ms(iso) {
      if (!iso) return null;
      var t = new Date(iso).getTime();
      return isFinite(t) ? t : null;
    }
    var anchorEv = byStep['cycle_started'] || byStep['queued'] || byStep['in_progress'];
    var prevTs = anchorEv ? _ms(anchorEv.ts) : null;
    var nowMs = Date.now();
    return STAGE_DEFS.map(function (def, i) {
      var status;
      if (def[1] in byStep) status = 'done';
      else if (failIdx !== null && i === failIdx) status = 'fail';
      else if (currIdx !== null && i === currIdx) status = 'curr';
      else status = 'queued';
      var ev = byStep[def[1]] || null;
      var duration_seconds = null;
      if (ev) {
        var evTs = _ms(ev.ts);
        if (evTs != null && prevTs != null) {
          duration_seconds = Math.max(0, Math.floor((evTs - prevTs) / 1000));
        }
        if (evTs != null) prevTs = evTs;
      } else if (status === 'curr' && prevTs != null) {
        duration_seconds = Math.max(0, Math.floor((nowMs - prevTs) / 1000));
      }
      return { name: def[0], status: status, ev: ev, duration_seconds: duration_seconds };
    });
  }

  // Spec 0182 — mirror server-side _humanize_seconds for stage durations.
  // Format must match exactly so first-paint (server-rendered) and the
  // 5s repaint (this helper) don't flicker between forms.
  function _fmtDurSecs(secs) {
    if (secs == null || secs < 0) return '—';
    if (secs < 60) return secs + 's';
    var m = Math.floor(secs / 60);
    var s = secs % 60;
    if (m < 60) return s === 0 ? (m + 'm') : (m + 'm ' + s + 's');
    var h = Math.floor(m / 60);
    m = m % 60;
    if (h < 24) return m === 0 ? (h + 'h') : (h + 'h ' + m + 'm');
    var d = Math.floor(h / 24);
    h = h % 24;
    if (d < 7) return h === 0 ? (d + 'd') : (d + 'd ' + h + 'h');
    var w = Math.floor(d / 7);
    d = d % 7;
    return d === 0 ? (w + 'w') : (w + 'w ' + d + 'd');
  }

  function renderTimeline(states, cycleStartedIso) {
    var doneCount = states.filter(function (s) { return s.status === 'done'; }).length;
    var total = states.length || 1;
    var railStyle = doneCount
      ? 'style="width: calc((' + doneCount + '/' + total + ') * (100% - 28px));"'
      : 'style="width: 0;"';
    var nodes = states.map(function (s) {
      // Carry data-stage-started-at on the current node so dashboard-live.js's
      // 1s ticker (spec 0156 §2.3) can keep rewriting the elapsed text.
      var attrs = '';
      if (s.status === 'curr' && cycleStartedIso) {
        attrs = ' data-stage-started-at="' + ESC(cycleStartedIso) + '"';
      }
      // Spec 0182 — render the computed duration_seconds via _fmtDurSecs
      // instead of the previous hard-coded em-dash. The 1s ticker keeps
      // rewriting the curr node's text regardless of the initial value.
      return (
        '<div class="tl__step tl__step--' + s.status + '">' +
        '<div class="tl__node"></div>' +
        '<div class="tl__lbl">' + ESC(s.name) + '</div>' +
        '<div class="tl__dur"' + attrs + '>' + _fmtDurSecs(s.duration_seconds) + '</div>' +
        '</div>'
      );
    }).join('');
    var railDone = doneCount ? '<div class="tl__rail-done" ' + railStyle + '></div>' : '';
    return (
      '<div class="tl" aria-label="Cycle stages">' +
      '<div class="tl__rail"></div>' +
      railDone +
      '<div class="tl__steps">' + nodes + '</div>' +
      '</div>'
    );
  }

  // Spec 0177 §2.6 — pager strip. The server-side helper lives at
  // _render_pager in scripts/spec_lifecycle/render_dashboard.py; mirror
  // its output here so re-renders preserve the strip.
  function renderPager(totalRows, label, currentPage) {
    if (totalRows <= PAGER_PAGE_SIZE) return '';
    var totalPages = Math.ceil(totalRows / PAGER_PAGE_SIZE);
    var current = Math.min(Math.max(1, currentPage || 1), totalPages);
    var start = (current - 1) * PAGER_PAGE_SIZE + 1;
    var end = Math.min(current * PAGER_PAGE_SIZE, totalRows);
    var buttons = [];
    function btn(p) {
      var attrs = (p === current) ? ' aria-current="page"' : '';
      return '<button class="pager__btn" type="button" data-pager-go="' + p + '"' + attrs + '>' + p + '</button>';
    }
    if (totalPages <= 5) {
      for (var p = 1; p <= totalPages; p++) buttons.push(btn(p));
    } else {
      buttons.push(btn(1), btn(2), btn(3));
      buttons.push('<span class="pager__ellipsis">…</span>');
      buttons.push(btn(totalPages));
    }
    var prevDisabled = current <= 1 ? ' disabled' : '';
    var nextDisabled = current >= totalPages ? ' disabled' : '';
    return (
      '<div class="pager" data-pager-total="' + totalRows + '" data-pager-pages="' + totalPages +
      '" data-pager-current="' + current + '" aria-label="' + ESC(label) + ' pagination">' +
      '<div class="pager__count" data-pager-count>Showing ' + start + '–' + end + ' of ' + totalRows + '</div>' +
      '<div class="pager__nav">' +
      '<button class="pager__btn" type="button" data-pager-prev aria-label="Previous page"' + prevDisabled + '>←</button>' +
      buttons.join('') +
      '<button class="pager__btn" type="button" data-pager-next aria-label="Next page"' + nextDisabled + '>→</button>' +
      '</div></div>'
    );
  }

  // ── Section renderers ───────────────────────────────────────────────────
  function renderHero(data, nowMs) {
    var inflight = data.specs.filter(function (s) { return s.status === 'in_progress'; });
    if (inflight.length === 0) return renderHeroIdle(data, nowMs);
    return renderHeroInflight(inflight[0], data, nowMs);
  }

  function renderHeroIdle(data, nowMs) {
    var queued = data.specs.filter(function (s) { return s.status === 'queued'; });
    var deployed = data.specs
      .filter(function (s) { return s.status === 'deployed'; })
      .sort(function (a, b) { return (b.deployed_at || '').localeCompare(a.deployed_at || ''); });
    var last = deployed[0] || null;
    var lastAgo = last ? ago(last.deployed_at, nowMs) : '—';
    var big = last ? lastAgo.replace(' ago', '') : '—';
    var lastLabel = last ? 'last deploy · ' + ESC(last.number) : 'no deploys yet';
    return (
      '<section class="hero hero--idle" aria-label="Queue status">' +
      '<div class="hero__icon"><span class="material-symbols-outlined">pause_circle</span></div>' +
      '<div class="hero__body">' +
      '<div class="hero__kicker">Queue · idle</div>' +
      '<div class="hero__title">Nothing in flight. ' +
      '<span class="hero__hint">Run <code>/dev-next</code> in your queue session to start the next spec.</span>' +
      '</div>' +
      '<div class="hero__row">' +
      '<span class="chip tone-neutral">0 in flight</span>' +
      '<span class="chip tone-info">' + queued.length + ' queued</span>' +
      '<span class="chip tone-ok">last shipped ' + ESC(lastAgo) + '</span>' +
      '</div></div>' +
      '<div class="hero__right">' +
      '<div class="hero__big">' + ESC(big) + '<small> ago</small></div>' +
      '<div class="hero__lbl">' + lastLabel + '</div>' +
      '</div></section>'
    );
  }

  function renderHeroInflight(spec, data, nowMs) {
    var events = (data.events && data.events[spec.number]) || [];
    var cycleStartedEv = events.find(function (e) { return e.step === 'cycle_started'; });
    var cycleStartedIso = (cycleStartedEv && cycleStartedEv.ts) || spec.started_at || '';
    var elapsedSec = cycleStartedIso ? Math.floor((nowMs - Date.parse(cycleStartedIso)) / 1000) : null;
    var elapsed = elapsedSec !== null ? humanizeSec(elapsedSec) : '—';
    var slug = spec.slug || '';
    var branch = 'spec/' + spec.number + '-' + slug;
    var chips = [typeChip(spec.type)];
    if (branch) chips.push('<span class="chip tone-neutral">branch · <code>' + ESC(branch) + '</code></span>');
    var rec = events.slice().reverse().find(function (e) { return e.step === 'reconcile_complete'; });
    if (rec) {
      var verdict = (rec.data && rec.data.verdict) || 'clean';
      var mech = (rec.data && rec.data.mechanical) || 0;
      chips.push('<span class="chip tone-ok">' + ESC(verdict) + ' · ' + ESC(mech) + ' patches</span>');
    }
    // Spec 0163 §2.3 — "currently: <step>" reflects the latest event.
    var latest = events.length ? events[events.length - 1] : null;
    var latestStep = (latest && latest.step) || '';
    var latestTs = (latest && latest.ts) || '';
    var currentLabel = stepLabel(latestStep);
    if (currentLabel) {
      chips.push('<span class="chip tone-info">currently · ' + ESC(currentLabel) + '</span>');
    }
    // Spec 0163 §2.4 — staleness chip ticked every second by dashboard-live.js.
    if (latestTs) {
      var ageSec = Math.max(0, Math.floor((nowMs - Date.parse(latestTs)) / 1000));
      var tone = staleTone(isNaN(ageSec) ? null : ageSec);
      chips.push(
        '<span class="chip chip-stale ' + tone + '" data-last-event-at="' + ESC(latestTs) + '">' +
        'last event ' + (isNaN(ageSec) ? '—' : humanizeSec(ageSec)) + ' ago</span>'
      );
    }
    // Spec 0177 §2.2 — horizontal stage timeline beneath the hero. Without
    // this, the bootstrap repaint wipes the server-rendered timeline 5s
    // after page load.
    var states = computeStages(events, spec.failure_step);
    var timeline = renderTimeline(states, cycleStartedIso);
    return (
      '<section class="hero hero--inflight" aria-label="Queue in flight" data-current-step="' + ESC(latestStep) + '">' +
      '<div class="hero__top">' +
      '<div class="hero__icon"><span class="material-symbols-outlined">play_circle</span></div>' +
      '<div class="hero__body">' +
      '<div class="hero__kicker">In flight — ' + ESC(spec.slug) + '</div>' +
      '<div class="hero__title"><a href="spec-' + ESC(spec.number) + '.html">Spec ' +
      ESC(spec.number) + ' — ' + ESC(spec.title) + '</a></div>' +
      '<div class="hero__row">' + chips.join('') + '</div>' +
      '</div>' +
      '<div class="hero__right">' +
      '<div class="hero__big" data-cycle-started-at="' + ESC(cycleStartedIso) + '">' + ESC(elapsed) + '</div>' +
      '<div class="hero__lbl">elapsed</div>' +
      '</div></div>' +
      '<div class="hero__divider"></div>' +
      timeline +
      '</section>'
    );
  }

  function renderQueue(data, nowMs) {
    var queued = data.specs
      .filter(function (s) { return s.status === 'queued'; })
      .sort(function (a, b) { return (a.queue_position || 999) - (b.queue_position || 999); });
    var header =
      '<div class="sh"><div class="sh__name">Queue</div>' +
      '<div class="sh__hint">/dev-next picks position 1 first</div>' +
      '<div class="sh__rule"></div></div>';
    if (queued.length === 0) {
      return header +
        '<section class="qtable" aria-label="Queue">' +
        '<div class="qrow qrow--header"><div>#</div><div>Spec</div><div>Title</div>' +
        '<div>Type</div><div style="text-align:right">Waiting</div></div>' +
        '<div class="qrow qrow--empty">Queue is empty. Promote a draft with ' +
        '<code>/spec-promote &lt;id&gt;</code> or queue a new one with <code>/spec-queue</code>.</div>' +
        '</section>';
    }
    var current = pagerState['Queue'] || 1;
    var rows = ['<div class="qrow qrow--header"><div>#</div><div>Spec</div>' +
      '<div>Title</div><div>Type</div><div style="text-align:right">Waiting</div></div>'];
    queued.forEach(function (s, idx) {
      var page = Math.floor(idx / PAGER_PAGE_SIZE) + 1;
      var hidden = page !== current ? ' hidden' : '';
      var waiting = ago(s.queued_at, nowMs).replace(' ago', '');
      rows.push(
        '<div class="qrow" data-pager-page="' + page + '"' + hidden + '>' +
        '<div class="qrow__pos">' + ESC(s.queue_position) + '</div>' +
        '<div class="qrow__id"><a href="spec-' + ESC(s.number) + '.html">' + ESC(s.number) + '</a></div>' +
        '<div class="qrow__title">' + ESC(s.title) + '</div>' +
        '<div>' + typeChip(s.type) + '</div>' +
        '<div class="qrow__age">' + ESC(waiting) + '</div></div>'
      );
    });
    var table =
      '<section class="qtable" aria-label="Queue" data-pager-target>' + rows.join('') + '</section>';
    return header + table + renderPager(queued.length, 'Queue', current);
  }

  function renderFeed(data, nowMs) {
    var cutoff = nowMs - 24 * 3600 * 1000;
    var flat = [];
    var specByNum = {};
    data.specs.forEach(function (s) { specByNum[s.number] = s; });
    Object.keys(data.events || {}).forEach(function (num) {
      (data.events[num] || []).forEach(function (e) {
        var ts = Date.parse(e.ts || '');
        if (!isNaN(ts) && ts >= cutoff) flat.push({ ts: ts, ev: e, spec: specByNum[num] });
      });
    });
    flat.sort(function (a, b) { return b.ts - a.ts; });

    var header =
      '<div class="sh"><div class="sh__name">Recent activity</div>' +
      '<div class="sh__hint">last 24 hours</div><div class="sh__rule"></div></div>';
    if (flat.length === 0) {
      return header +
        '<section class="feed" aria-label="Recent activity"><div class="feed__row">' +
        '<div class="feed__ts">—</div><div></div>' +
        '<div class="feed__what"><em>No events in the last 24 hours.</em></div>' +
        '<div class="feed__dur">—</div></div></section>';
    }
    var capped = flat.slice(0, 40);
    var current = pagerState['Recent activity'] || 1;
    var rows = capped.map(function (r, idx) {
      var page = Math.floor(idx / PAGER_PAGE_SIZE) + 1;
      var hidden = page !== current ? ' hidden' : '';
      var d = new Date(r.ts);
      var hh = String(d.getUTCHours()).padStart(2, '0');
      var mm = String(d.getUTCMinutes()).padStart(2, '0');
      var ss = String(d.getUTCSeconds()).padStart(2, '0');
      var step = r.ev.step || '';
      var specLink = r.spec
        ? '<a href="spec-' + ESC(r.spec.number) + '.html">' + ESC(r.spec.number) + '</a>'
        : '';
      var detail = r.spec ? specLink + ' · ' + ESC(r.spec.title) : ESC(step);
      return (
        '<div class="feed__row" data-pager-page="' + page + '"' + hidden + '>' +
        '<div class="feed__ts">' + hh + ':' + mm + ':' + ss + ' UTC</div>' +
        '<div class="feed__step feed__step--neutral"></div>' +
        '<div class="feed__what"><span class="kicker">' + ESC(step.replace(/_/g, ' ')) + '</span>' +
        detail + '</div><div class="feed__dur">—</div></div>'
      );
    });
    var section =
      '<section class="feed" aria-label="Recent activity" data-pager-target>' +
      rows.join('') + '</section>';
    return header + section + renderPager(capped.length, 'Recent activity', current);
  }

  function renderDrafts(data, nowMs) {
    var drafts = data.drafts || [];
    var header =
      '<div class="sh"><div class="sh__name">Drafts</div>' +
      '<div class="sh__hint">backlog · promote with <code>/spec-promote &lt;id&gt;</code></div>' +
      '<div class="sh__rule"></div></div>';
    if (drafts.length === 0) {
      return header +
        '<section class="drafts" aria-label="Drafts">' +
        '<div class="draft-row"><div class="draft-row__id">—</div>' +
        '<div class="draft-row__title"><em>No drafts parked.</em></div>' +
        '<div></div><div class="draft-row__age">—</div></div></section>';
    }
    var rows = drafts.map(function (d) {
      var age = d.created ? ago(d.created, nowMs).replace(' ago', '') : '—';
      return (
        '<div class="draft-row">' +
        '<div class="draft-row__id">' + ESC(d.draft_id) + '</div>' +
        '<div class="draft-row__title"><a href="draft-' + ESC(d.draft_id) + '.html">' +
        ESC(d.title) + '</a></div>' +
        '<div>' + typeChip(d.type) + '</div>' +
        '<div class="draft-row__age">park · ' + ESC(age) + '</div></div>'
      );
    });
    return header + '<section class="drafts" aria-label="Drafts">' + rows.join('') + '</section>';
  }

  // Spec 0177 §2.3 — Lifetime + Cycle columns mirror the Python
  // `_spec_lifetime_seconds` + `SpecRow.cycle_seconds`. Returns null when
  // either anchor is missing (so the column renders as `—`).
  function specLifetimeSeconds(s) {
    if (!s.deployed_at) return null;
    var rawCreated = s.created || s.queued_at || '';
    if (!rawCreated) return null;
    var createdStr = String(rawCreated);
    // Bare YYYY-MM-DD → midnight-UTC isoformat
    if (/^\\d{4}-\\d{2}-\\d{2}$/.test(createdStr)) createdStr += 'T00:00:00Z';
    var created = Date.parse(createdStr);
    var deployed = Date.parse(s.deployed_at);
    if (isNaN(created) || isNaN(deployed)) return null;
    return Math.max(0, Math.floor((deployed - created) / 1000));
  }
  function specCycleSeconds(s) {
    if (!s.started_at || !s.deployed_at) return null;
    var st = Date.parse(s.started_at), dp = Date.parse(s.deployed_at);
    if (isNaN(st) || isNaN(dp)) return null;
    return Math.max(0, Math.floor((dp - st) / 1000));
  }

  function renderAllSpecs(data) {
    var dev = (data.specs || []).slice().sort(function (a, b) {
      return parseInt(b.number, 10) - parseInt(a.number, 10);
    });
    var counts = {
      deployed: dev.filter(function (s) { return s.status === 'deployed'; }).length,
      queued: dev.filter(function (s) { return s.status === 'queued'; }).length,
      inflight: dev.filter(function (s) { return s.status === 'in_progress'; }).length
    };
    var header =
      '<div class="sh"><div class="sh__name">All specs</div>' +
      '<div class="sh__hint">' + counts.deployed + ' shipped · ' + counts.queued +
      ' queued · ' + counts.inflight + ' in flight</div>' +
      '<div class="sh__rule"></div></div>';
    var rows = ['<div class="qrow qrow--history qrow--history-header">' +
      '<div>Spec</div><div>Title</div><div>Type</div><div>Status</div>' +
      '<div style="text-align:right">Lifetime</div>' +
      '<div style="text-align:right">Cycle</div></div>'];
    dev.forEach(function (s) {
      var lifetime = humanizeSec(specLifetimeSeconds(s));
      var cycle = humanizeSec(specCycleSeconds(s));
      rows.push(
        '<div class="qrow qrow--history">' +
        '<div class="qrow__id"><a href="spec-' + ESC(s.number) + '.html">' + ESC(s.number) + '</a></div>' +
        '<div class="qrow__title">' + ESC(s.title) + '</div>' +
        '<div>' + typeChip(s.type) + '</div>' +
        '<div>' + statusChip(s.status) + '</div>' +
        '<div class="qrow__age">' + ESC(lifetime) + '</div>' +
        '<div class="qrow__age">' + ESC(cycle) + '</div></div>'
      );
    });
    return header + '<section class="qtable" aria-label="All specs">' + rows.join('') + '</section>';
  }

  function paint(data, nowMs, opts) {
    opts = opts || {};
    var hero = document.querySelector('[data-region="hero"]');
    if (hero) hero.innerHTML = renderHero(data, nowMs);
    var q = document.querySelector('[data-region="queue"]');
    if (q) q.innerHTML = renderQueue(data, nowMs);
    var feed = document.querySelector('[data-region="feed"]');
    if (feed) feed.innerHTML = renderFeed(data, nowMs);
    var drafts = document.querySelector('[data-region="drafts"]');
    if (drafts) drafts.innerHTML = renderDrafts(data, nowMs);
    var all = document.querySelector('[data-region="all-specs"]');
    if (all) all.innerHTML = renderAllSpecs(data);

    var updated = document.querySelector('[data-last-updated]');
    if (updated) {
      var generatedAt = data.generated_at ? Date.parse(data.generated_at) : nowMs;
      var age = humanizeSec(Math.floor((nowMs - generatedAt) / 1000));
      var stalePrefix = opts.stale ? '<span class="chip tone-warn">stale · </span> ' : '';
      updated.innerHTML = stalePrefix + 'updated ' + age + ' ago';
    }
  }

  function readCache() {
    try {
      var raw = localStorage.getItem(CACHE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }
  function writeCache(data) {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(data)); } catch (e) { /* quota */ }
  }

  function refresh() {
    fetch('/api/data', { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) throw new Error('http ' + r.status);
        return r.json();
      })
      .then(function (data) {
        writeCache(data);
        paint(data, Date.now(), {});
      })
      .catch(function (err) {
        console.warn('[dr-dashboard] /api/data failed:', err && err.message);
        var cached = readCache();
        if (cached) paint(cached, Date.now(), { stale: true });
        // else: leave server-rendered content in place; no destructive swap.
      });
  }

  // Spec 0177 §2.6 — pager click delegation. One handler attached to
  // document so it survives the 5s repaint cycle (which destroys and
  // recreates pager DOM). When a button fires, we look up the
  // surrounding `.pager`'s nav-label (the section name) to drive the
  // pagerState map; the bootstrap reads pagerState on next paint to keep
  // the user on the same page across /api/data refreshes.
  function wirePager() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest && e.target.closest('.pager__btn');
      if (!btn) return;
      if (btn.hasAttribute('disabled')) return;
      var pager = btn.closest('.pager');
      if (!pager) return;
      var label = (pager.getAttribute('aria-label') || '').replace(/ pagination$/, '');
      var total = parseInt(pager.getAttribute('data-pager-total') || '0', 10);
      var totalPages = parseInt(pager.getAttribute('data-pager-pages') || '1', 10);
      var current = parseInt(pager.getAttribute('data-pager-current') || '1', 10) || 1;
      var target = null;
      if (btn.hasAttribute('data-pager-go')) {
        target = parseInt(btn.getAttribute('data-pager-go'), 10);
      } else if (btn.hasAttribute('data-pager-prev')) {
        target = current - 1;
      } else if (btn.hasAttribute('data-pager-next')) {
        target = current + 1;
      }
      if (!target || target < 1 || target > totalPages) return;
      pagerState[label] = target;
      applyPager(pager, target, total, totalPages);
    }, false);
  }

  function applyPager(pager, page, total, totalPages) {
    pager.setAttribute('data-pager-current', String(page));
    // Toggle [hidden] on rows in the previous `[data-pager-target]` section.
    var section = pager.previousElementSibling;
    while (section && !(section.hasAttribute && section.hasAttribute('data-pager-target'))) {
      section = section.previousElementSibling;
    }
    if (section) {
      section.querySelectorAll('[data-pager-page]').forEach(function (row) {
        var p = parseInt(row.getAttribute('data-pager-page'), 10);
        if (p === page) row.removeAttribute('hidden');
        else row.setAttribute('hidden', '');
      });
    }
    // Recompute count text.
    var count = pager.querySelector('[data-pager-count]');
    if (count) {
      var start = (page - 1) * PAGER_PAGE_SIZE + 1;
      var end = Math.min(page * PAGER_PAGE_SIZE, total);
      count.textContent = 'Showing ' + start + '–' + end + ' of ' + total;
    }
    // Update button aria-current + disabled states.
    pager.querySelectorAll('.pager__btn[data-pager-go]').forEach(function (b) {
      var p = parseInt(b.getAttribute('data-pager-go'), 10);
      if (p === page) b.setAttribute('aria-current', 'page');
      else b.removeAttribute('aria-current');
    });
    var prev = pager.querySelector('[data-pager-prev]');
    var next = pager.querySelector('[data-pager-next]');
    if (prev) {
      if (page <= 1) prev.setAttribute('disabled', '');
      else prev.removeAttribute('disabled');
    }
    if (next) {
      if (page >= totalPages) next.setAttribute('disabled', '');
      else next.removeAttribute('disabled');
    }
  }

  function start() {
    // First paint: if we have cached data, paint it immediately so returning
    // visitors see populated content before the network round-trip completes.
    wirePager();
    var cached = readCache();
    if (cached) paint(cached, Date.now(), {});
    refresh();
    setInterval(refresh, POLL_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
"""


# ── Asset copy + entrypoint ────────────────────────────────────────────────


def copy_design_system_assets(repo_root: Path, out_dir: Path) -> None:
    """Copy tokens-and-primitives.css and composed-components.css into ``out_dir``.

    Raises ``FileNotFoundError`` with a clear message if the design-system
    stylesheets move; the renderer is meant to fail loud, not silently.
    """
    src_dir = repo_root / "design-system" / "assets" / "styles"
    sources = {
        "tokens.css": src_dir / "tokens-and-primitives.css",
        "components.css": src_dir / "composed-components.css",
    }
    missing = [str(p) for p in sources.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Design-system stylesheets missing — expected at "
            + ", ".join(missing)
            + ". Did design-system/ move?"
        )
    for name, src in sources.items():
        shutil.copy(src, out_dir / name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", type=Path)
    parser.add_argument("--out", default="dashboard/site", type=Path)
    parser.add_argument(
        "--shell-only",
        action="store_true",
        help=(
            "Emit data-empty skeleton placeholders for hero/queue/feed/drafts/all-specs "
            "(spec 0160). dashboard-bootstrap.js fetches /api/data at runtime and "
            "populates them. Per-spec pages are still emitted in full. Used by the "
            "Cloudflare Pages build; local previews omit the flag to bake data in."
        ),
    )
    ns = parser.parse_args(argv)

    repo_root = ns.repo_root.resolve()
    out_dir = (repo_root / ns.out) if not ns.out.is_absolute() else ns.out
    out_dir.mkdir(parents=True, exist_ok=True)

    specs, drafts = collect(repo_root)
    live_version = read_live_version(repo_root)
    now = dt.datetime.now(dt.timezone.utc)

    copy_design_system_assets(repo_root, out_dir)
    (out_dir / "dashboard.css").write_text(DASHBOARD_CSS, encoding="utf-8")
    (out_dir / "dashboard-live.js").write_text(DASHBOARD_LIVE_JS, encoding="utf-8")
    (out_dir / "dashboard-bootstrap.js").write_text(DASHBOARD_BOOTSTRAP_JS, encoding="utf-8")
    (out_dir / "index.html").write_text(
        render_index(
            specs, drafts, live_version=live_version, now=now, shell_only=ns.shell_only,
        ),
        encoding="utf-8",
    )
    for s in specs:
        (out_dir / f"spec-{s.number}.html").write_text(render_spec_page(s), encoding="utf-8")
    for d in drafts:
        (out_dir / f"draft-{d.draft_id}.html").write_text(render_draft_page(d), encoding="utf-8")

    # Surface unknown event-step names so future spec authors notice when the
    # mapping in stages.py / _FEED_STEP_ICON drifts.
    for s in specs:
        if s.status not in {"in_progress", "deployed", "merged"}:
            continue
        _, unknown = compute_stages(
            s.number, s.events, failure_step=s.fm.get("failure_step"), now=now
        )
        if unknown:
            print(f"warning: spec {s.number} has unknown event steps: {sorted(set(unknown))}")

    print(f"rendered {len(specs)} specs + {len(drafts)} drafts → {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
