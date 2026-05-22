# `prototypes/_canvas/` — workshop scaffolding

`/canvas <pane>` spins up a pane-iteration workshop for an existing UI surface
in dual-research. The workshop is a Claude-Preview-served folder under
`prototypes/<pane>-iteration/` with four files:

- `live.html` — verbatim outerHTML dump of the running DOM, with the live CSS
  files linked so edits in `src/dual_research/ui/static/` are visible on reload.
- `ds.html` — verbatim `<section id="X" class="ds-section">…</section>` extracts
  from `design-system/assets/Design System v2.html`, with the DS CSS linked.
- `mockup.html` — the three-tab workshop wrapper (Iteration / Live / DS) with
  theme + width toggles. Loads the three other files in iframes.
- `proposed.html` — the iteration sandbox. Starts as a verbatim copy of `live.html`;
  you stack `<style id="iter-N-…">` blocks here as you iterate.
- `NOTES.md` — the running record of iters, locked four-quadrant per element.

`live.html`, `ds.html`, and `mockup.html` are **always regenerated** by the
scaffold. `proposed.html` and `NOTES.md` are **preserved** across re-runs
(unless `--force-overwrite-proposed` is passed).

## Adding a new pane

1. Open `registry.yml`. Add a new entry under `panes:` keyed by a short name.
   See the inline field docs at the top of the file. Mandatory fields:
   `name`, `live_url`, `live_selector`, `ds_sections`, `ds_label`, `port`,
   `accent`, `live_css`, `ds_css`, `default_anchor_run`.
2. Pick an unused `port`. Convention: `617X` where X is unique per pane.
3. Pick an `accent` color — sable (`#d4a574`) and sage (`#7cc4b8`) are taken
   by timeline and critique. Pick something else for new panes.
4. For multi-state panes (panes whose visual chrome changes across user-driven
   tabs/phases), populate `states:` with `{name, click}` entries — `click` is
   a CSS selector that switches the live app to that state before the dump.
5. Run `/canvas <pane>`. The skill reads the registry, dumps live HTML via the
   Claude Preview MCP, extracts the DS sections, renders the templates, and
   prints a workshop URL.

No code changes required.

## Files

| Path                       | What                                                    |
|---------------------------|---------------------------------------------------------|
| `registry.yml`            | Pane registry — single source of truth.                 |
| `templates/mockup.html.tmpl` | Workshop wrapper template.                            |
| `templates/live.html.tmpl`  | Wrapper for the dumped DOM snapshot.                  |
| `templates/ds.html.tmpl`    | Wrapper for the DS extracts.                          |
| `templates/proposed.html.tmpl` | Initial iteration sandbox (copy of live + theme JS). |
| `templates/NOTES.md.tmpl` | Per-workshop running record.                            |
| `spin-up.py`              | File-generation workhorse. Reads registry + dumps,      |
|                           | renders templates, writes workshop dir.                 |

## Manual invocation (without Claude)

If you want to drive the scaffold without Claude / the MCP layer, you must
pre-capture the live outerHTML yourself and pass it in:

```bash
# Single-state pane:
uv run python prototypes/_canvas/spin-up.py timeline \
  --live-html-file /tmp/timeline-dump.html

# Multi-state pane:
uv run python prototypes/_canvas/spin-up.py critique \
  --live-html-state P0:/tmp/crit-p0.html \
  --live-html-state P2:/tmp/crit-p2.html \
  --live-html-state P4:/tmp/crit-p4.html \
  --live-html-state sigma:/tmp/crit-sigma.html
```

Inside Claude Code, `/canvas <pane>` does this automatically.

## Iteration vocabulary

- **Iter** — one named, scoped change applied as a single `<style id="iter-N-…">`
  block at the top of `proposed.html`. Monotonic ids, short labels.
- **DS change / Live change** — the two locked-in destinations once an iter is
  ready to leave the workshop. DS goes into `design-system/SPEC.md` + the
  composed-components CSS; Live goes into `src/dual_research/ui/static/components.css`
  (and any matching JSX). Same commit, per `CLAUDE.md`.
- **Drift fix** — an iter whose purpose is to align live to DS (or vice versa)
  when they encode the same intent differently.

See `prototypes/timeline-iteration/NOTES.md` and `prototypes/critique-iteration/NOTES.md`
for working examples.
