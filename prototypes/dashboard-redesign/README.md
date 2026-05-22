# Dashboard redesign mockup

Visual target for [`specs/0153-dashboard-redesign-staged-hero-and-activity-feed.md`](../../specs/0153-dashboard-redesign-staged-hero-and-activity-feed.md).

## Files

- `mockup.html` — full static preview of the redesigned dashboard. Open in a browser; uses a `#idle` / `#inflight` URL-hash toggle to switch between the idle and in-flight hero states. The toggle is preview-only — the production renderer picks the state from spec frontmatter at build time.

## How to view

```bash
# From the repo root:
open prototypes/dashboard-redesign/mockup.html
```

The mockup links to the canonical design-system stylesheets at:

- `design-system/assets/styles/tokens-and-primitives.css`
- `design-system/assets/styles/composed-components.css`

So changes to those tokens / primitives flow through to the mockup automatically — no duplication.

## Status

This mockup is the visual contract for spec 0153. The implementer of that spec rewrites `scripts/spec_lifecycle/render_dashboard.py` to emit HTML that matches this layout (using the same composed primitives + tokens). When 0153 ships, the live Cloudflare dashboard at `https://dual-research.pages.dev` matches what you see here.
