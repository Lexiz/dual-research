---
spec: "0254"
date: 2026-05-29
version: 1.63.5
pr: https://github.com/Lexiz/dual-research/pull/294
kind: post-deploy
---

# Spec 0254 — Fix: parked spec's activity event renders as QUEUED instead of Parked

**Shipped v1.63.5.** PR [#294](https://github.com/Lexiz/dual-research/pull/294), admin squash-merged (`93e14f6`), deployed via `deploy.yml` (run 26628608888, conclusion `success`) and the live dashboard regenerated via `dashboard.yml` (run 26628608900, `success`).

## What landed

A parked spec's creation event uses the same `queued` lifecycle step as a runnable spec, so the dashboard RECENT ACTIVITY feed mislabelled it — e.g. spec 0253.1 (`status: parked`, `disposition: archive`) showed `08:35:22 UTC · QUEUED · 0253.1` even though the Parked lane and queue-picker correctly excluded it. This is a **labelling** fix — no new lifecycle event type is introduced (which would be a contract change requiring a non-`bug` label); the `queued` step stays the single creation event and the feed renderers became parked-aware.

- **`scripts/spec_lifecycle/render_dashboard.py`** — a shared parked-ness predicate now re-keys the `queued` activity row:
  - server-side: `_feed_event_is_parked(spec, data)` + a `step == "queued"` branch in `_render_feed`.
  - client-side bootstrap JS (the genuine parity twin): `feedEventIsParked(spec, data)` + the matching branch in `renderFeed`.
  - Both render `parked` with an `inventory_2`/`warn` glyph. Parked-ness reads the self-describing event payload (`data.status == "parked"`) with a fallback to the spec's parked frontmatter (`_is_parked` / `spec.parked`), so 0253.1's existing event re-labels with **no data migration** (§3.4), and pre-self-describing parked specs (empty `{}` payload) are still caught (§8 stale-payloads).
- **`functions/api/data.js`** — documents the `spec.parked` parity-source contract it supplies to the feed.
- **`tests/test_spec_0254_parked_activity_feed.py`** — functional renders (parked payload → "parked"; frontmatter-fallback → "parked"; runnable `disposition: ship` → "queued" guard; 0253.1 actual-event fixture → "parked") + source-pattern parity asserting the parked branch is present in **both** renderers and that `data.js` documents the parity source. Full suite: 2446 passed.

## Smoke

Local render of the live queue-state via `_render_feed` confirmed 0253.1's row renders kicker `parked` + icon `inventory_2`, while runnable specs retain their `queued` kicker (no over-match). `dashboard.yml` regenerated the GitHub Pages dashboard on the merge commit (`success`).

## Spec deviation (surfaced, intentional)

Spec §3.3 and §2 frame `functions/api/data.js` as the feed parity twin and prescribe applying the parked-aware mapping there, with a §5 test asserting `data.js`'s "activity event derivation" contains it. **`data.js` performs no feed-label derivation** — it is the Cloudflare data API that returns raw events plus a per-spec `spec.parked` flag (line 217). The genuine parity twin of the server-side Python feed renderer is the **client-side bootstrap JS embedded in `render_dashboard.py`** (`renderFeed` / `FEED_KICKER` / `feedDetail`), which consumes `spec.parked`.

The fix therefore lands the parked-aware mapping in the two real renderers (Python + client JS, both in `render_dashboard.py`), the §5 parity test targets that real twin, and `data.js` gets the parity-source contract comment instead of a meaningless feed-label mapping. The user-facing behaviour matches the spec's §4 acceptance scenarios exactly. This is a correction of the spec's architectural premise, not a scope reduction — nothing behaviourally in-scope was dropped.
