"""Spec 0254 — a parked spec's RECENT ACTIVITY row reads "Parked", not "Queued".

Covers §5 (regression-prevention test) of
`specs/0254-parked-spec-activity-event-renders-as-queued.md`.

Two layers, per the UI test doctrine (spec 0206) — no Playwright:

* **Functional unit tests** drive the real Python feed renderer
  (`_render_feed`) over synthetic `SpecRow`s and assert the rendered kicker.
* **Source-pattern parity test** asserts the parked-aware mapping is present
  in BOTH feed renderers (the server-side Python and the client-side bootstrap
  JS, which are the two genuine parity twins — see the note below).

Architecture note (deviation from spec §3.3): the spec names
`functions/api/data.js` as the feed parity twin, but that Cloudflare data API
performs **no** feed-label derivation — it only supplies the `spec.parked`
flag. The genuine parity twin of the server-side feed renderer is the
client-side `renderFeed`/`feedEventIsParked` bootstrap JS embedded in
`render_dashboard.py`. The parity test therefore targets that real twin and
asserts `data.js` documents the `spec.parked` parity-source contract.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from scripts.spec_lifecycle.render_dashboard import SpecRow, _render_feed
from tests._ui_pattern_helpers import (
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)

# A fixed "now" so synthetic events land inside the feed's 24h window.
_NOW = dt.datetime(2026, 5, 29, 9, 0, 0, tzinfo=dt.timezone.utc)
_TS = "2026-05-29T08:35:22Z"  # within 24h of _NOW


def _spec(
    number: str,
    *,
    status: str,
    disposition: str,
    event_data: dict,
) -> SpecRow:
    """A SpecRow carrying a single `queued`-step activity event."""
    fm = {
        "status": status,
        "disposition": disposition,
        "title": f"fixture {number}",
    }
    events = [{"ts": _TS, "step": "queued", "data": event_data}]
    return SpecRow(fm=fm, path=Path(f"specs/{number}-fixture.md"), events=events)


# ── Functional: parked spec reads "Parked" (Scenario 1) ───────────────────────


def test_parked_event_renders_parked_kicker() -> None:
    """A `queued` event whose `data.status == "parked"` renders the Parked
    kicker and does NOT render the "queued" kicker for that row."""
    spec = _spec("0299", status="parked", disposition="archive",
                 event_data={"status": "parked"})
    html = _render_feed([spec], _NOW)
    assert '<span class="kicker">parked</span>' in html
    # Antipodal-absence: the pre-fix shape (verbatim "queued" kicker) is gone.
    assert '<span class="kicker">queued</span>' not in html


def test_parked_via_frontmatter_fallback_renders_parked_kicker() -> None:
    """§8 stale-payload path: an event with an empty `{}` payload still reads
    Parked when its owning spec's frontmatter is parked (queued + disposition
    != ship)."""
    spec = _spec("0298", status="queued", disposition="archive", event_data={})
    html = _render_feed([spec], _NOW)
    assert '<span class="kicker">parked</span>' in html
    assert '<span class="kicker">queued</span>' not in html


# ── Functional: runnable spec still reads "Queued" (Scenario 2 — guard) ────────


def test_runnable_queued_event_still_renders_queued_kicker() -> None:
    """A `disposition: ship` queued spec with an empty payload keeps the
    "queued" kicker — the parked branch must not swallow the normal path."""
    spec = _spec("0297", status="queued", disposition="ship", event_data={})
    html = _render_feed([spec], _NOW)
    assert '<span class="kicker">queued</span>' in html
    assert '<span class="kicker">parked</span>' not in html


# ── Functional: real 0253.1 event fixture → "Parked" (§5 bullet 3) ─────────────


def test_spec_0253_1_actual_event_renders_parked() -> None:
    """Regression fixture built from spec 0253.1's actual recorded event
    (`step: queued`, `data: {"disposition":"archive","status":"parked"}`)
    renders the Parked kicker."""
    spec = _spec("0253.1", status="parked", disposition="archive",
                 event_data={"disposition": "archive", "status": "parked"})
    html = _render_feed([spec], _NOW)
    assert '<span class="kicker">parked</span>' in html
    assert '<span class="kicker">queued</span>' not in html


# ── Source-pattern parity: both feed renderers carry the parked-aware mapping ──


def test_python_feed_renderer_has_parked_branch() -> None:
    """Server-side `_render_feed` re-keys the `queued` step on parked-ness
    (positive); the helper it calls exists (no verbatim pass-through)."""
    src = read_repo_text("scripts", "spec_lifecycle", "render_dashboard.py")
    assert_jsx_contains(
        src,
        r'if step == "queued" and _feed_event_is_parked\(spec, data\):',
        msg="render_dashboard.py server feed renderer must branch the queued "
            "kicker on parked-ness (spec 0254 §3.2).",
    )
    assert_jsx_contains(
        src,
        r'def _feed_event_is_parked\(',
        msg="render_dashboard.py must define the _feed_event_is_parked helper.",
    )


def test_client_js_feed_renderer_has_parked_branch() -> None:
    """Client-side bootstrap JS (the genuine parity twin of the Python feed
    renderer) carries the identical parked-aware mapping."""
    src = read_repo_text("scripts", "spec_lifecycle", "render_dashboard.py")
    assert_jsx_contains(
        src,
        r"step === 'queued' && feedEventIsParked\(r\.spec, r\.ev\.data \|\| \{\}\)",
        msg="client-side renderFeed must branch the queued kicker on "
            "parked-ness (spec 0254 §3.2 parity twin).",
    )
    assert_jsx_contains(
        src,
        r'function feedEventIsParked\(spec, data\)',
        msg="render_dashboard.py bootstrap JS must define feedEventIsParked.",
    )


def test_data_js_documents_parked_parity_source() -> None:
    """`functions/api/data.js` supplies the `spec.parked` flag the feed
    renderer consumes; it documents that parity contract (spec 0254) so the
    twin renderers stay in lock-step."""
    src = read_repo_text("functions", "api", "data.js")
    assert_jsx_contains(
        src,
        r"spec\.parked = spec\.status === 'parked'",
        msg="data.js must derive spec.parked (the parity source).",
    )
    assert_jsx_contains(
        src,
        r"Spec 0254",
        msg="data.js must document the spec.parked parity-source contract.",
    )
