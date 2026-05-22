# Kickoff — Critique-pane iteration session

> **Paste everything below this line into a fresh Claude Code session in the `dual-research` repo.** It is self-contained. Do not summarise it before pasting.

---

You are picking up an iteration workflow that's already been used once to lock the timeline pane. We are now doing the same thing for the **critique pane**. Read this entire prompt before touching anything.

## 1. The outcome we want

A workshop mockup at `prototypes/critique-iteration/mockup.html`, loadable via the existing `prototype-mockup` Claude-Preview server at `http://localhost:6174/prototypes/critique-iteration/mockup.html`, that contains:

- **Three tabs** in a top toolbar:
  1. **Iteration** — the proposed state, rendered as a side-by-side **dark + light** split (two iframes, each loading `proposed.html?theme=dark` / `?theme=light`).
  2. **Live** — a verbatim outerHTML dump of the live critique pane (`prototypes/critique-iteration/live.html`). Immutable reference.
  3. **Design system** — a verbatim copy of the relevant `<section>`(s) from `design-system/assets/Design System v2.html` (`prototypes/critique-iteration/ds.html`). Immutable reference.

- **Phase navigation inside the critique pane:** every tab (Iteration / Live / DS) must let me browse between **Phase 0 / Phase 2 / Phase 4 / Σ Summary**. This mirrors the live critique pane's Bar 1 phase tabs.

- **Cards openable in both states (collapsed + expanded)** in both light and dark mode. Inside the Iteration tab, both states must be visible side-by-side or via a toggle — your call, but make sure I can see both without scrolling endlessly.

- **A `NOTES.md`** in the same folder, structured exactly like [`prototypes/timeline-iteration/NOTES.md`](/Users/alexlisitzky/dual-research/prototypes/timeline-iteration/NOTES.md) — exhaustive, per-element, per-state, with current/target/DS-change/live-change quadrants. We add to it as we iterate, not at the end.

## 2. What is non-negotiable (this is the part that, if you skip, will make me angry)

> Read this section twice. The previous session almost broke trust by violating these rules. They are absolute.

1. **Recreate from the literal rendered DOM, not from source code, not from spec docs, not from subagent summaries.** When the task is "show me what the live page looks like," the only acceptable source is `document.querySelector('…').outerHTML` from the rendered live app. Do not look at the JSX and write a paraphrase of what it produces. Do not look at a spec doc and write what the spec says it should look like. Both will drift from reality and I will catch it.

2. **The Design System tab must be a verbatim copy from `Design System v2.html`** — not a re-rendering, not an "improved" version, not an extrapolation across multiple phases when the DS only documents one. If the DS shows one phase example, the DS tab shows one phase example. Copy lines from the file with a line-range reader and paste them into a wrapper. Do not generate new markup.

3. **Iteration goes one change at a time.** Each change gets its own `<style id="iter-N-…">` block in `proposed.html` and its own NOTES.md row. Banner the iteration step in the proposed.html provenance bar. Do not bundle changes. Do not "improve" things I didn't ask for.

4. **Verify visually after every iteration.** Take a screenshot with `mcp__Claude_Preview__preview_screenshot` (light theme renders best for screenshots; dark looks black at jpeg compression). Inspect computed styles with `mcp__Claude_Preview__preview_inspect`. Report what changed and confirm DOM counts match the source.

5. **Never claim "verbatim" without showing the DOM count match.** Before declaring the Live tab done, dump:
   - phase count, card count per phase, section counts (Open · new / Open · carried / Resolved / Drift), expanded vs collapsed counts
   - and prove they match what `document.querySelectorAll` returns on the live page.

6. **No CSS shortcuts via subagent summaries.** If you don't know exactly what a class does, open the actual rule in `src/dual_research/ui/static/components.css` and read it. Subagent "audits" are interpretations; they fail on details that matter.

7. **No JS-string escaping shortcuts.** If you write JS strings that contain HTML, use template literals (backticks). The previous session used `\\'` inside single-quoted strings and broke its own tab switch with a silent parse error. Don't repeat that.

8. **CSS specificity battles**: if a rule isn't applying, check the specificity of the rules that ARE applying. Multiple `<style>` blocks with `!important` will fight each other in source order. The cleanest fix is a slightly more specific selector (e.g. `.tl__body .tl-thread` beats `.tl-thread`).

## 3. Context — what was done before this session

The timeline pane was iterated through 12 changes on 2026-05-22. **Read [`prototypes/timeline-iteration/NOTES.md`](/Users/alexlisitzky/dual-research/prototypes/timeline-iteration/NOTES.md) before starting.** It contains the methodology, all 12 iterations, every drift fix discovered, and the implementation order. The same approach applies here.

Key takeaways from that session:
- The live app surface drifts from the design-system reference in many small ways. Surfacing the drift is part of the value of this exercise.
- The live `tokens.css` is missing several light-mode overrides that the canonical `tokens-and-primitives.css` provides. Flag any drift you find for the critique pane similarly.
- Several "live bugs" surface during iteration (e.g., `turn [object object]` rendering). When you find them, note them in NOTES.md as drift fixes — don't try to fix the underlying bug, just propose a UI-side defensive render.

## 4. The infrastructure you already have

### Servers (already running — `mcp__Claude_Preview__preview_list` to confirm)

- **dev server** on `localhost:6173` (config name `dual-research-ui`) — the live React SPA. Open it via the existing preview session; the runs page is at `/#/runs/<run-id>`. The previous session used `20260521-010637-dvs-backend-language-choice` as the reference run because it has data in P0 / P2 / P4. Reuse that run unless you have reason not to.

- **static server** on `localhost:6174` (config name `prototype-mockup`) — `python3 -m http.server` serving the repo root. Your mockup files in `prototypes/critique-iteration/` are reachable here.

If either isn't running, start it with `mcp__Claude_Preview__preview_start`.

### The POST-receiver pattern (for dumping large outerHTML to disk)

`preview_eval` returns JS values inline. For the timeline dump (176 KB) that's near the limit of what works comfortably. **Use the POST-receiver pattern** from the previous session:

```python
# /tmp/upload-server.py — run in background via Bash run_in_background:true
import http.server, os
class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'content-type')
        self.send_header('Access-Control-Allow-Methods', 'POST,OPTIONS')
    def do_OPTIONS(self): self.send_response(204); self._cors(); self.end_headers()
    def do_POST(self):
        n = int(self.headers.get('Content-Length','0'))
        data = self.rfile.read(n)
        with open('/tmp/crit-' + self.path.strip('/'), 'wb') as f: f.write(data)
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(b'OK ' + str(len(data)).encode())
    def log_message(self, *a, **kw): pass
http.server.HTTPServer(('127.0.0.1', 7890), H).serve_forever()
```

Then in `preview_eval`:
```js
fetch('http://127.0.0.1:7890/critique-pane.html', {
  method: 'POST',
  body: document.querySelectorAll('.rdvc__pane')[1].outerHTML,  // the SECOND pane is critique
  headers: {'Content-Type': 'text/html'}
})
```

This bypasses the inline-return size pressure and writes the full HTML to disk.

**Don't forget to `pkill -f upload-server.py` when you're done.**

## 5. Scope — the critique pane specifically

### 5.1 What's in the critique pane (high-level)

Per [`design-system/SPEC.md`](/Users/alexlisitzky/dual-research/design-system/SPEC.md) §4.1, the critique pane has:

- **Bar 1** — title `Critique` · phase tabs (`P0 Brief` / `P2 Negotiate` / `P4 Review` / `Σ Summary`) · run-wide totals (introduced / open / resolved) · drift chip.
- **Bar 2** — kind tabs (All / Issues / Comments / Questions / Disagreements) with per-phase counts · agent segmented filter (All / Claude / GPT) · status segmented filter (All / Open / Resolved / Drift). **Hidden when Σ Summary tab is active.**
- **Body** — status-grouped collapsible sections:
  - `Open · new this round`
  - `Open · carried over`
  - `Resolved`
  - `Drift`
- Each section contains critique-item cards. New-protocol items render via `<ItemCard>`; legacy items render via `<QuestionThread>`. Per spec 0144 §6.3.d, ItemCard composition is: header chips → body → optional Evidence-needed → Lifecycle → footer → SOURCES (N).

### 5.2 What I want to be able to do in the Iteration tab

For each of these four states, I need to see a fully-rendered critique pane:

- **Phase 0** — typically Q + D categories only. Probably less critique activity than P2 / P4.
- **Phase 2** — the bulk of the critique work happens here. Q + D categories.
- **Phase 4** — Q + D + I + C all surface here. Most variety.
- **Σ Summary** — Bar 2 is hidden, the body shows a different layout (read SPEC.md §4.1 carefully — the Summary tab swaps the body for a summary view).

I want to switch between these four phase states inside a single Iteration view. Use either:
- The actual phase-tab buttons in Bar 1 (preferred — it's what the live app does, so the simulation is most faithful), or
- A query-param mechanism similar to `?theme=light` on the iframe.

Pick what's cleanest. The phase-tab buttons would be ideal but require either real JS state or pre-rendering all four views and toggling.

### 5.3 Card states — collapsed vs expanded

Each critique card has at minimum two states:
- **Collapsed** — header chips only (or header + body, depending on what the live shows)
- **Expanded** — full ItemCard composition (header + body + anchor + Evidence-needed + Lifecycle + footer + SOURCES)

In the Iteration tab, I want to see both states visible — either side-by-side, or with a toggle, or by having one card pre-expanded in the rendering. Your call but make sure I can audit both states without arguing about layout.

## 6. The procedure — bootstrap, then iterate

### Phase A — Bootstrap (verbatim copies first; no proposals yet)

**A.1 Read context** — read [`prototypes/timeline-iteration/NOTES.md`](/Users/alexlisitzky/dual-research/prototypes/timeline-iteration/NOTES.md), [`design-system/SPEC.md`](/Users/alexlisitzky/dual-research/design-system/SPEC.md) §4.1 + §4.2 + §4.7 + §4.8, [`specs/0144-sources-provenance-investigation-and-critique-card-surface.md`](/Users/alexlisitzky/dual-research/specs/0144-sources-provenance-investigation-and-critique-card-surface.md). These contain the contractual reference for what the critique pane is supposed to be.

**A.2 Confirm servers** — `mcp__Claude_Preview__preview_list`. Both `dual-research-ui` and `prototype-mockup` should be running. Start any that isn't.

**A.3 Navigate to a representative run.** The previous session used `20260521-010637-dvs-backend-language-choice` because it has rich critique data across all four phases. Open it.

**A.4 Identify the critique pane wrapper.** Use `preview_eval` to find the right selector. The critique pane is the SECOND `.rdvc__pane` (the first is timeline). Confirm by counting cards, checking for `.crit-group` / `.qthread` / `.tl-thread` elements.

```js
// In the live dev-server preview
(() => {
  const panes = document.querySelectorAll('.rdvc__pane');
  return Array.from(panes).map((p, i) => ({
    i,
    threads: p.querySelectorAll('.qthread, .tl-thread').length,
    sections: p.querySelectorAll('.crit-group, .cr-group').length,
    has_phase_tabs: !!p.querySelector('.crv__phasetabs, .phase-tabs')
  }));
})()
```

**A.5 Spin up the POST-receiver** (background bash). **A.6 Dump the critique pane outerHTML** to `/tmp/crit-critique-pane.html` via `fetch` POST.

**A.7 Important: the critique pane changes content when you switch phase tabs.** You'll need to dump it FOUR TIMES — once per phase tab (P0 / P2 / P4 / Σ). Save as four separate HTML files (or one big file containing all four states wrapped). The cleanest approach: dump the four states into `live-p0.html` / `live-p2.html` / `live-p4.html` / `live-sigma.html`, then have `live.html` be a small wrapper with phase-tab buttons that swap which is visible. Use the SAME tab markup the live app uses for consistency.

Alternatively: drive the live app via `preview_click` to switch tabs, dump after each click. Both work; pick one.

**A.8 Extract the DS reference** — find the relevant `<section>` blocks in `Design System v2.html`. The critique surface is documented across multiple sections:
- §12 "Critique header" (`id="critique"`)
- §13 "Critique card · ItemCard + Sources" (`id="itemcard"`) — added by spec 0144 in the PR I shipped during this session
- §13b "QuestionThread (legacy)" (`id="thread"`)
- §15 "QuestionThread" (the older legacy reference; check whether the section IDs still match — the file evolved)

Pull line ranges from each `<section>` and concatenate into `ds.html` with a wrapper that loads the design-system CSS files (`/design-system/assets/styles/v2-m3.css` and `/design-system/assets/styles/v2-m3-page.css`).

**A.9 Build `live.html` wrappers** — each dump file gets wrapped in a small HTML page that:
- Loads the live CSS (`/src/dual_research/ui/static/{tokens,base,components,theme}.css`)
- Inserts the dumped outerHTML inside `<body class="dark"><div class="__shell">…</div></body>`
- Has a thin provenance banner at the top

**A.10 Build `proposed.html`** — copies `live.html` (or the multi-phase wrapper) but adds the `?theme=` query-param script:
```html
<body class="dark"><script>(function(){var t=new URLSearchParams(location.search).get('theme');if(t==='light'){document.body.className='light';}})();</script>
```

**A.11 Build `mockup.html`** — the 3-tab wrapper. Use template literals for any JS strings containing HTML (no `\\'` escaping). Tabs: Iteration (default) / Live / DS. The Iteration tab mounts TWO iframes side-by-side (dark + light proposed.html with the theme query-param). The Live and DS tabs mount single iframes.

**A.12 Verify** — count phases, count cards, count sections, count expanded states. Confirm they match what the live page shows. Take a screenshot in light mode (more legible than dark for screenshots). Report findings to me.

**A.13 STOP. Show me the verbatim reproduction. Get my approval before any iteration starts.** Do not silently start proposing changes. The previous session got into trouble by trying to "help" before establishing the ground truth.

### Phase B — Iterate

After I approve the verbatim reproduction:

**B.1 One change at a time.** Each iteration gets:
- A new `<style id="iter-N-<short-name>">` block at the TOP of `proposed.html` (highest CSS source-order specificity wins)
- A banner update in the provenance bar
- A new row in `NOTES.md` with the four-quadrant format (Now / After / DS change / Live change)

**B.2 Verify each change visually.** Screenshot before/after if it helps. Inspect computed styles. Report what changed.

**B.3 Don't extrapolate.** If I say "increase the chip background opacity slightly," do exactly that. Don't also redo the radius, or the padding, or the shadow. Save those for the next iteration.

**B.4 Surface drift continuously.** Every time you notice the live app diverges from the design system spec or has a small bug, add a "Drift fix" row to NOTES.md.

**B.5 Use `:has()` for derived-state selectors.** It's clean and browser-supported. If you find yourself wanting to add JS-derived classes (e.g., `is-active-phase`) for visual purposes, prefer a CSS `:has()` or `:has-text()` pattern unless I tell you otherwise.

### Phase C — Document and close out

When we lock the iteration:

**C.1 NOTES.md is the deliverable.** Make sure every iteration has its quadrant entry. Make sure the drift fixes are all listed. Make sure the implementation order section at the bottom groups independent changes.

**C.2 Don't write a spec.** I'll do that separately. Your output is the NOTES.md + the visible mockup.

**C.3 Keep `live.html` and `ds.html` immutable.** Don't touch them once dumped. They are the "before" reference.

## 7. The starter checklist (paste this into your TaskCreate as the initial task list)

```
1. Read prototypes/timeline-iteration/NOTES.md + design-system/SPEC.md §4.1/4.2/4.7/4.8 + specs/0144
2. Confirm both preview servers are running (preview_list)
3. Identify the critique pane wrapper selector in the live app (preview_eval)
4. Spin up the /tmp/upload-server.py POST receiver in background
5. Dump critique pane outerHTML for each of P0 / P2 / P4 / Σ Summary states
6. Extract DS critique-related sections from Design System v2.html (line ranges)
7. Build live.html (or live-p0.html etc) + ds.html with verbatim wrappers
8. Build proposed.html with ?theme= query-param script (initially identical to live.html)
9. Build mockup.html with 3-tab switch and side-by-side dark/light Iteration tab
10. Verify counts match between live page and dumps; screenshot in light mode; report findings
11. STOP and get user approval before iterating
12. Iterate (one change per iter, NOTES.md row per iter, verify each)
13. On lock, produce final NOTES.md with implementation-order section
```

## 8. Tools you will use

- `mcp__Claude_Preview__preview_list` — confirm servers
- `mcp__Claude_Preview__preview_start` — bring servers up
- `mcp__Claude_Preview__preview_eval` — dump DOM, drive interactions, inspect state
- `mcp__Claude_Preview__preview_click` — click phase tabs to re-render
- `mcp__Claude_Preview__preview_inspect` — verify computed styles
- `mcp__Claude_Preview__preview_screenshot` — visual confirmation (light mode best)
- `mcp__Claude_Preview__preview_console_logs` — check for runtime errors
- `Bash` — file ops, Python POST receiver in background, sed/awk for line ranges
- `Read` — open existing files in the repo
- `Write` / `Edit` — author the four mockup files + NOTES.md
- `TaskCreate` / `TaskUpdate` — the starter checklist; one task per iteration after

## 9. Where to save everything

```
/Users/alexlisitzky/dual-research/prototypes/critique-iteration/
  mockup.html           # 3-tab wrapper (the only thing you load directly in the browser)
  proposed.html         # the iteration sandbox (modified each iter)
  live.html             # verbatim live dump wrapper (immutable)
  live-p0.html          # individual phase dumps (if you use the multi-file approach)
  live-p2.html
  live-p4.html
  live-sigma.html
  ds.html               # verbatim DS section wrapper (immutable)
  NOTES.md              # the working notes (grows with each iter)
  KICKOFF-PROMPT.md     # this file (don't delete it)
```

If you choose to keep the four phase dumps in one file (live.html with internal phase switching), that's fine too — just be explicit about which approach you chose in NOTES.md.

## 10. Final reminders before you start

- **The mockup is a workshop scratchpad.** It's in `prototypes/`, untracked by default. Don't commit it without asking.
- **Don't open PRs.** This session's output is the mockup + NOTES.md, not code changes.
- **Don't update SPEC.md, components.css, or run-detail.jsx yet.** Those changes come from specs I draft from your NOTES.md.
- **If something fails or you're uncertain, stop and ask.** Don't paper over.
- **If you find yourself wanting to summarise instead of dump, stop.** Re-read sections 2 and 6 of this prompt.
- **Light mode renders better in screenshots** than dark mode (which compresses to flat black). Take screenshots in light when proving things work.
- **Verify CSS specificity** — if a rule isn't taking effect, check what other rule is winning. Don't escalate to `!important` until you've checked the specificity chain.
- **Use template literals (`` ` ``) for any JS string containing HTML.** Don't use `\\'`-escaping inside single-quoted strings.
- **Mark each iteration's stylesheet with a clear `id`** (`iter-N-<short-name>`) and a clear comment block. The NOTES.md will reference these directly.

When you're done with bootstrap (Phase A through A.13), report back with:
- the four-phase card counts you measured
- the screenshot of the Iteration tab in light mode
- any drift you noticed in passing

Then we iterate.
