---
spec: "0260"
date: 2026-05-31
version: 1.68.0
pr: https://github.com/Lexiz/dual-research/pull/302
---

# Spec 0260 — Make `--name` double as the run display title

**Shipped v1.68.0** ([PR #302](https://github.com/Lexiz/dual-research/pull/302), merged + deployed).

## What landed

`--name` now overrides the first `# ` H1 of `brief.md` — the string both UIs
render as the run title — so named runs stop displaying the hardcoded
"Research Brief".

- **New helper** `_apply_title(content, name)` in [`cli.py`](src/dual_research/cli.py:283):
  replaces the first `# ` line with `# {name}` when `name` is truthy; prepends
  `# {name}` when no H1 exists; returns `content` verbatim (bit-for-bit) when
  `name` is falsy.
- **Single chokepoint** — applied at the one `brief.md` write point
  ([`cli.py:407`](src/dual_research/cli.py:407)):
  `brief_path.write_text(_apply_title(brief.content, args.name), ...)`. Because
  it sits at the source-agnostic write, it covers `--notion`, `--prompt`, and
  `--brief` alike, and propagates to both the local
  ([`aggregator.py:_read_topic`](src/dual_research/ui/aggregator.py)) and hosted
  ([`server.py:_extract_h1`](src/dual_research/ui/server.py)) title surfaces —
  the hosted upload carries the same `brief.md` via the `*.md` glob.
- **Unchanged when omitted** — no `--name` → verbatim pass-through, preserving
  the existing Notion-ingest `# Research brief` default and topic-extraction
  fallback. No new flag; `_derive_slug` slug behavior untouched.

## Tests

New file [`tests/cli/test_spec_0260_apply_title.py`](tests/cli/test_spec_0260_apply_title.py)
covers all four test-plan branches plus an empty-string-`--name` pass-through
case, with the first two exercising the on-disk first-H1 the renderers read via
a tmp-file round-trip. Full suite: **2454 passed**.

## Notes

- Not a captured-live-failure fix (spec 0238 real-entry-point rule not
  triggered, per spec §7) — the change is a pure string transform gated on
  `args.name`, so write-path transform tests are sufficient.
- Reconciler was clean (0 mechanical, 0 semantic). The 4 "unreachable
  (informational)" warnings are expected: the cited surfaces (`cli.py`,
  `aggregator.py`, `server.py`) are reachable from the CLI/UI entry points, not
  the phase2/4 LLM path the liveness check scopes to.
- No retroactive title fix for runs already uploaded (per spec §5 Out of scope).
