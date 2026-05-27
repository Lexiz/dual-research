---
kind: draft
draft_id: "001"
slug: jsx-cache-bust-dev-mode-fragility
title: "JSX cache-bust query strategy is fragile during in-spec iteration"
status: draft
created: 2026-05-26
source_session: deferred-from-0220
parent_spec: "0220"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Draft 001 — JSX cache-bust query strategy is fragile during in-spec iteration

> **Source:** spec 0220 handoff, "Deferred during implementation" — [handoffs/2026-05-26-spec-0220-in-app-changelog-auto-generated.md:47](handoffs/2026-05-26-spec-0220-in-app-changelog-auto-generated.md:47).

## Context

The in-app JSX is loaded via `<script type="text/babel" src="<file>.jsx?v=<bust>"></script>` in [src/dual_research/ui/static/index.html:43-49](src/dual_research/ui/static/index.html:43). The `?v=NNNNa` query string is hand-bumped per spec (today: `?v=0220c` on `how-it-works.jsx` and `app.jsx`, `?v=0209a` on the rest).

The convention works fine in production: each spec touches the JSX, bumps the query once, the browser sees a new URL on the next page load, and the cache cleanly invalidates.

It breaks down during in-spec iteration. During spec 0220's preview-verification pass, the cache-bust had to be bumped **three times** (`?v=0220a` → `?v=0220b` → `?v=0220c`) because the browser kept serving the cached JSX even after `location.reload()`. The transcript: source edits land, `location.reload()` runs, the verification screenshot shows pre-edit behavior; the only reliable workaround is to re-edit `index.html` and bump the query letter again.

## Why this is a draft, not a spec

The deferral names two distinct remediation paths and doesn't pick one. Both are real options with different tradeoffs:

1. **Dev-mode no-cache HTTP header on `*.jsx`.** The static-files mount at [src/dual_research/ui/server.py:320](src/dual_research/ui/server.py:320) is `app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")` — FastAPI's `StaticFiles` does not set `Cache-Control` headers by default, but the browser's heuristic caching kicks in nonetheless. A custom middleware that sets `Cache-Control: no-store` on `*.jsx` responses **only when running under the dev server** (not in production behind Fly's CDN) would let `location.reload()` always pick up source edits, and would obsolete the `?v=NNNNa` convention entirely for dev work.
2. **Content-hash cache-bust.** Replace the hand-bumped query letter with a hash of the file content, computed at request time or at startup. Removes the human-bump step entirely; the bust string changes whenever the file content changes. Works in both dev and prod. Cost: a startup-time hash pass (cheap — ~15 JSX files) plus either an `index.html` template indirection or a server-side rewrite at response time.

The right answer depends on taste questions that haven't been adjudicated:

- Do we want to keep the `?v=NNNNa` per-spec convention as a human-readable provenance signal (visible in browser devtools — "this build is from spec 0220")? Option 1 preserves that; option 2 destroys it.
- Do we trust a server-side content-hash bust to be cheap enough at request time? (`StaticFiles` doesn't currently rewrite response bodies, so option 2 likely requires moving JSX serving out of the `StaticFiles` mount and into a dedicated route.)
- Is the friction during in-spec iteration actually frequent enough to justify either option? Spec 0220 was the first time this was reported as a blocker; before that, the convention worked.

## Unresolved questions

- **Which remediation path?** Dev-mode no-cache header (cheap, dev-only, preserves the human-readable bust string) vs. content-hash cache-bust (general-purpose, obsoletes the bust string)? Tied to whether we want to keep `?v=NNNNa` as provenance signal.
- **What's the dev/prod switch?** If we go with the no-cache header, how does the server know it's in "dev" mode? Env var (`DUAL_RESEARCH_DEV=1`)? `localhost` check on the request? Both?
- **Frequency.** Is this worth fixing now, or is it a once-per-many-specs annoyance? Need at least one more cycle of evidence (a non-0220 spec hitting the same friction) before this graduates from "we noticed it once" to "we should fix it." Possibly defer until the second occurrence.
- **Production cache-busting behavior.** Even if we add a dev-mode no-cache header, the production cache-bust still relies on the manual `?v=NNNNa` bump. If a spec author forgets to bump, production users get stale JSX. Should we land the production-side content-hash bust regardless of the dev-mode fix?

## Sketch of remediation path 1 (dev-mode no-cache header)

```python
# src/dual_research/ui/server.py — wrap the static mount with a middleware
# that sets Cache-Control on *.jsx requests when running under the dev server.
@app.middleware("http")
async def no_cache_jsx_in_dev(request, call_next):
    response = await call_next(request)
    if (
        os.environ.get("DUAL_RESEARCH_DEV") == "1"
        and request.url.path.endswith(".jsx")
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response
```

Then dev sessions launch with `DUAL_RESEARCH_DEV=1 uv run uvicorn …`; production (Fly) doesn't set the env var, behavior unchanged.

## Sketch of remediation path 2 (content-hash cache-bust)

At server startup, compute `sha256(file_contents)[:8]` for every `.jsx` under `src/dual_research/ui/static/`. Cache the mapping in memory. Rewrite `index.html` at first-load time (or serve a template-rendered version) replacing `?v=NNNNa` with `?v=<hash>`. On next request, hash is the same → 304. On source edit → restart picks up new hash → cache miss.

Trickier: requires either moving `index.html` out of the static mount into a dedicated route (so it can be templated), or running a startup-time rewrite pass on the file itself (mutating the checked-in `index.html` — uncomfortable).

## Promotion criteria

Promote this draft to a queued dev spec when:

1. The friction reoccurs on a second non-0220 spec — confirming this is recurring, not one-off.
2. The remediation path is picked (option 1 vs option 2) with the dev/prod switch nailed down.
3. The promotion-time answer to "do we keep the `?v=NNNNa` provenance signal" is recorded.

Until then: park here.
