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
from .stages import StageState, compute_stages, current_stage_label


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
    if hours == 0:
        return f"{days}d"
    return f"{days}d {hours}h"


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
    # Auto-refresh every 60s so the dashboard tracks new spec events without
    # the user reaching for ⌘R. Long enough not to disrupt mid-scroll reads;
    # short enough that the dashboard feels current. Spec 0156 §2.2.
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        '<meta http-equiv="refresh" content="60">'
        f"<title>{_escape(title)}</title>"
        + GFONTS_HEAD
        + '<link rel="stylesheet" href="tokens.css">'
        + '<link rel="stylesheet" href="components.css">'
        + '<link rel="stylesheet" href="dashboard.css">'
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


def _render_stage_row(stage: StageState) -> str:
    mark_inner = ""
    if stage.status == "done":
        mark_inner = '<span class="material-symbols-outlined" style="font-size:14px">check</span>'
    elif stage.status == "fail":
        mark_inner = '<span class="material-symbols-outlined" style="font-size:14px">close</span>'
    dur = _humanize_seconds(stage.duration_seconds) if stage.duration_seconds is not None else "—"
    note = stage.note or {
        "queued": "queued",
        "curr": "in progress",
        "fail": "failed",
    }.get(stage.status, "")
    # Live ticker (spec 0156 §2.3): the current stage's duration cell carries
    # a data-stage-started-at attribute so dashboard-live.js can rewrite the
    # text every second without a page reload.
    dur_attrs = ""
    if stage.status == "curr" and stage.started_at is not None:
        dur_attrs = f' data-stage-started-at="{_escape(stage.started_at.isoformat())}"'
    return (
        f'<li class="stage stage--{stage.status}">'
        f'<span class="stage__mark">{mark_inner}</span>'
        f'<span class="stage__name">{_escape(stage.name)}</span>'
        f'<span class="stage__note">{_escape(note)}</span>'
        f'<span class="stage__dur"{dur_attrs}>{_escape(dur)}</span>'
        f'</li>'
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

    stage_rows = "\n".join(_render_stage_row(s) for s in states)

    return (
        '<section class="hero hero--inflight" aria-label="Queue in flight">'
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
        f'<ol class="stages" aria-label="Cycle stages">{stage_rows}</ol>'
        '</section>'
    )


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


def _render_metrics(specs: list[SpecRow], now: dt.datetime) -> str:
    deployed = sorted(
        [s for s in specs if s.status == "deployed"],
        key=lambda s: s.fm.get("deployed_at") or "",
        reverse=True,
    )
    cycle_times = [s.cycle_seconds for s in deployed if s.cycle_seconds]

    last10 = cycle_times[:10]
    prior10 = cycle_times[10:20]
    avg_str = _humanize_seconds(int(statistics.mean(last10))) if last10 else "—"
    delta_html = ""
    if last10 and prior10:
        d = int(statistics.mean(prior10) - statistics.mean(last10))
        if d > 0:
            delta_html = (
                f'<span class="delta-up">↓ {_escape(_humanize_seconds(d))}</span>'
            )
        elif d < 0:
            delta_html = (
                f'<span class="delta-down">↑ {_escape(_humanize_seconds(-d))}</span>'
            )
        else:
            delta_html = "flat"
        delta_html = f" · {delta_html} vs prior 10"
    avg_sub = f"rolling {len(last10)}{delta_html}"

    day_ago = now - dt.timedelta(days=1)
    week_ago = now - dt.timedelta(days=7)
    per_day = sum(1 for s in deployed if (d := _parse_ts(s.fm.get("deployed_at"))) and d >= day_ago)
    per_week = sum(1 for s in deployed if (d := _parse_ts(s.fm.get("deployed_at"))) and d >= week_ago)

    # Reconcile patches: % of last-10 deployed cycles that needed >0 mechanical patches.
    reconciled = 0
    needed_fix = 0
    for s in deployed[:10]:
        rec = next((e for e in s.events if e.get("step") == "reconcile_complete"), None)
        if rec:
            reconciled += 1
            if (rec.get("data") or {}).get("mechanical", 0):
                needed_fix += 1
    if reconciled:
        rec_val = f"{needed_fix} of {reconciled}"
        rec_pct = int(round(needed_fix / reconciled * 100))
        rec_sub = f"{rec_pct}% needed handoff drift fix"
    else:
        rec_val = "—"
        rec_sub = "no reconcile data yet"

    month_ago = now - dt.timedelta(days=30)
    failed_count = sum(
        1
        for s in specs
        if s.status == "failed"
        and (t := _parse_ts(s.fm.get("started_at"))) is not None
        and t >= month_ago
    )

    def tile(label: str, value: str, sub: str) -> str:
        return (
            '<div class="metric">'
            f'<div class="metric__lbl">{_escape(label)}</div>'
            f'<div class="metric__val">{_escape(value)}</div>'
            f'<div class="metric__sub">{sub}</div>'
            '</div>'
        )

    return (
        '<div class="sh"><div class="sh__name">Throughput &amp; cycle time</div><div class="sh__rule"></div></div>'
        '<section class="metrics">'
        + tile("Avg cycle time", avg_str, avg_sub)
        + tile("Throughput", f"{per_day} / day", f"last 24h · {per_week} / week trend")
        + tile("Reconcile patches", rec_val, rec_sub)
        + tile("Failed cycles", str(failed_count), "last 30 days")
        + '</section>'
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
    for s in queued:
        queued_ts = _parse_ts(s.fm.get("queued_at"))
        waiting = _ago(queued_ts, now) if queued_ts else "—"
        rows.append(
            '<div class="qrow">'
            f'<div class="qrow__pos">{_escape(s.fm.get("queue_position", "—"))}</div>'
            f'<div class="qrow__id">{_link_spec(s.number, s.number)}</div>'
            f'<div class="qrow__title">{_escape(s.title)}</div>'
            f'<div>{_type_chip(s.type)}</div>'
            f'<div class="qrow__age">{_escape(waiting.replace(" ago", ""))}</div>'
            '</div>'
        )
    return header + f'<section class="qtable" aria-label="Queue">{"".join(rows)}</section>'


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

    rows: list[str] = []
    for ts, step, data, spec in flat[:40]:
        icon, tone = _FEED_STEP_ICON.get(step, ("circle", "neutral"))
        kicker = _FEED_KICKER.get(step, step.replace("_", " "))
        detail = _feed_detail(spec, step, data)
        ts_str = ts.strftime("%H:%M:%S UTC")
        rows.append(
            '<div class="feed__row">'
            f'<div class="feed__ts">{_escape(ts_str)}</div>'
            f'<div class="feed__step feed__step--{tone}">'
            f'<span class="material-symbols-outlined">{_escape(icon)}</span></div>'
            f'<div class="feed__what"><span class="kicker">{_escape(kicker)}</span>{detail}</div>'
            '<div class="feed__dur">—</div>'
            '</div>'
        )
    return header + f'<section class="feed" aria-label="Recent activity">{"".join(rows)}</section>'


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


def _render_all_specs(specs: list[SpecRow]) -> str:
    rows: list[str] = []
    grid_style = "grid-template-columns: 76px 1fr 130px 100px 100px;"
    rows.append(
        f'<div class="qrow qrow--header" style="{grid_style}">'
        '<div>Spec</div><div>Title</div><div>Type</div><div>Status</div>'
        '<div style="text-align:right">Version</div></div>'
    )
    sorted_specs = sorted(
        [s for s in specs if (s.fm.get("kind") or "dev") == "dev"],
        key=lambda s: int(s.number or "0"),
        reverse=True,
    )
    for s in sorted_specs:
        rows.append(
            f'<div class="qrow" style="{grid_style}">'
            f'<div class="qrow__id">{_link_spec(s.number, s.number)}</div>'
            f'<div class="qrow__title">{_escape(s.title)}</div>'
            f'<div>{_type_chip(s.type)}</div>'
            f'<div>{_status_chip(s.status)}</div>'
            f'<div class="qrow__age">{_escape(s.target_version or "—")}</div>'
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


def _render_header(live_version: str, now: dt.datetime) -> str:
    chip = (
        f'<span class="chip tone-ok no-dot">v{_escape(live_version)} live</span>'
        if live_version
        else ""
    )
    ts = now.strftime("%Y-%m-%d %H:%M UTC")
    return (
        '<header class="dh">'
        '<div>'
        '<div class="dh__title">dual-research · spec dashboard</div>'
        '<div class="dh__sub">read-only view of <code>specs/</code>, <code>handoffs/</code> '
        'and <code>dashboard/events/</code> at <code>main</code></div>'
        '</div>'
        '<div class="dh__meta">'
        f'<span>{chip}</span>'
        f'<span>updated <time>{_escape(ts)}</time></span>'
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


# ── Public renderers ───────────────────────────────────────────────────────


def render_index(
    specs: list[SpecRow],
    drafts: list[DraftRow],
    *,
    live_version: str = "",
    now: dt.datetime | None = None,
) -> str:
    now = now or dt.datetime.now(dt.timezone.utc)
    in_flight = [s for s in specs if s.status == "in_progress"]
    queued = sorted(
        [s for s in specs if s.status == "queued"],
        key=lambda s: int(s.fm.get("queue_position") or 999),
    )

    parts: list[str] = []
    parts.append(_html_head("dual-research · spec dashboard"))
    parts.append('<body><main class="page">')
    parts.append(_render_header(live_version, now))

    if in_flight:
        for spec in in_flight:
            parts.append(_render_hero_inflight(spec, specs, now))
    else:
        parts.append(_render_hero_idle(specs, queued, drafts, now))

    parts.append(_render_pipeline(specs, drafts, now))
    parts.append(_render_metrics(specs, now))
    parts.append(_render_queue(queued, now))
    parts.append(_render_feed(specs, now))
    parts.append(_render_drafts(drafts, now))
    parts.append(_render_all_specs(specs))
    parts.append(_render_footer())
    parts.append('</main></body></html>')
    return "\n".join(parts)


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

/* Stage timeline */
.stages { list-style: none; padding: 0; margin: 0; display: grid; gap: 0; }
.stage {
  display: grid;
  grid-template-columns: 24px 150px 1fr 80px;
  gap: 14px;
  align-items: center;
  padding: 9px 0;
  position: relative;
}
.stage + .stage::before {
  content: ""; position: absolute; left: 11px; top: -1px; bottom: 50%;
  width: 2px; background: var(--md-outline-hair);
}
.stage--done + .stage--done::before { background: color-mix(in srgb, var(--p-ok) 60%, var(--md-outline-hair)); }
.stage--done + .stage--curr::before { background: color-mix(in srgb, var(--p-ok) 60%, var(--md-outline-hair)); }
.stage::after {
  content: ""; position: absolute; left: 11px; top: 50%; bottom: 0;
  width: 2px; background: var(--md-outline-hair);
}
.stage:last-child::after { display: none; }
.stage--done::after { background: color-mix(in srgb, var(--p-ok) 60%, var(--md-outline-hair)); }

.stage__mark {
  width: 24px; height: 24px; border-radius: 50%;
  display: grid; place-items: center;
  font-family: var(--md-font-plain);
  font-size: 13px; font-weight: 500;
  background: var(--md-surface-container-high);
  color: var(--md-on-surface-faint);
  z-index: 1;
  position: relative;
}
.stage--done .stage__mark {
  background: color-mix(in srgb, var(--p-ok) 24%, var(--md-surface-container-high));
  color: var(--p-ok);
}
.stage--curr .stage__mark {
  background: color-mix(in srgb, var(--p-info) 26%, var(--md-surface-container-high));
  color: var(--p-info);
}
.stage--curr .stage__mark::before {
  content: ""; position: absolute; inset: -6px; border-radius: 50%;
  background: color-mix(in srgb, var(--p-info) 16%, transparent);
  animation: halo 2.2s ease-in-out infinite;
}
.stage--queued .stage__mark { background: var(--md-surface-container); color: var(--md-on-surface-decor); }
.stage--fail .stage__mark   { background: color-mix(in srgb, var(--p-err) 26%, var(--md-surface-container-high)); color: var(--p-err); }

.stage__name { font: 500 13.5px/1.2 var(--md-font-plain); color: var(--md-on-surface); }
.stage--queued .stage__name { color: var(--md-on-surface-faint); font-weight: 400; }
.stage--done .stage__name { color: var(--md-on-surface-variant); }
.stage__note {
  font: 400 12.5px/1.4 var(--md-font-data);
  color: var(--md-on-surface-muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.stage--queued .stage__note { color: var(--md-on-surface-decor); }
.stage__dur {
  font: 400 11.5px/1 var(--md-font-data);
  color: var(--md-on-surface-faint);
  text-align: right; letter-spacing: 0.02em;
}
.stage--curr .stage__dur { color: var(--p-info); font-weight: 500; }
@media (prefers-reduced-motion: reduce) {
  .stage--curr .stage__mark::before { animation: none; }
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
"""


# ── Live ticker JS (spec 0156 §2.3) ────────────────────────────────────────

DASHBOARD_LIVE_JS = """\
// dashboard-live.js — increment elapsed durations every second without a
// page reload. Powered by data attributes that the server emits:
//   data-cycle-started-at  — on the in-flight hero's ELAPSED display.
//   data-stage-started-at  — on the current stage row's duration cell.
// Spec 0156 §2.3. Tiny on purpose: no external deps, no framework.

(function () {
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    // Reduced-motion users see static server-side timings.
    return;
  }

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
  }

  // Initial paint synchronises with whatever the server rendered, then we
  // re-paint every second.
  tick();
  setInterval(tick, 1000);
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
    (out_dir / "index.html").write_text(
        render_index(specs, drafts, live_version=live_version, now=now),
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
