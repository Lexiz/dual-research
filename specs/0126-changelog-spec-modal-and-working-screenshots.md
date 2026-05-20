---
spec: 0126
title: Changelog — spec rendered in a full-view modal + working screenshots (or none)
label: bug
version-bump: PATCH
status: proposed
target-version: 1.6.1
created: 2026-05-20
pr: ""
---

# Spec 0126 — Changelog: open-spec modal + verified screenshots

> Ship bucket: **Frontend + small backend endpoint.**
> Depends on: **0096** (M3 `<Modal>` primitive), **0121** (How-It-Works overlay + Changelog tab rewrite), **0125** (current changelog data shape).
> Complexity: **S–M** — one new backend endpoint, one new `<SpecModal>` component, swap one button handler, decision on screenshots.
> Targeted version bump: **PATCH (1.6.0 → 1.6.1)** — bug fixes to the same surface, no API contract change beyond the additive `/api/specs/{id}` GET.

---

## 1. Context

A live audit on **v1.6.0** of the Changelog tab inside the How-It-Works overlay (`#/how-it-works`, tab "Changelog") found two issues:

### 1.1 — All "Open spec ↗" buttons are broken

Each ChangelogEntry that carries metadata renders a button at the bottom:

```jsx
<button onClick={() => window.open(entry.specPath, '_blank')}>Open spec ↗</button>
```

`entry.specPath` is e.g. `/specs/0121-how-it-works-and-changelog-rework.md`. Clicking opens a new tab to that URL. **All such URLs return HTTP 404 on the live site** — confirmed by `curl https://dual-research-alex.fly.dev/specs/0121-how-it-works-and-changelog-rework.md`. The static UI server (`server.py`) only mounts `src/dual_research/ui/static/` at `/`; the `specs/` directory at the repo root is not served.

There are 4 broken spec links in the current changelog (v1.5.0 / v1.4.1 / v1.4.0 / v1.3.0); a fifth will be added when v1.6.0 lands.

### 1.2 — Every changelog screenshot is broken

Each entry's `screenshots[]` array references paths like `/changelog-shots/1.5.0/overview-section-overview.dark.png`. **None of these PNGs exist.** Same `curl` check returns 404. The ChangelogEntry component renders broken `<img>` tags (with the alt text falling back when supported), so every entry has empty boxes where screenshots should be.

Counts in the live VERSION_NOTES today:
- v1.5.0 (spec 0121): 2 screenshot paths, both 404
- v1.4.1 (spec 0120): 2 paths, both 404
- v1.4.0 (spec 0119): 3 paths, all 404
- v1.3.0 (spec 0118): 2 paths, all 404

**Total: 9 broken `<img>` tags currently rendering in the Changelog.**

### 1.3 — User's directive

User stated (verbatim):
> *"If we are showing specs, show them in a modal using our components, full view, full vertical space usage, with an overlay exactly as we do on the cards on the timeline. You can check the implementation there and make sure that all the screenshots that you add actually verify working and are hosted correctly."*

The timeline cards open specs/turns via the `<Modal>` primitive from `shared.jsx:382` (`variant: 'rich'` = wide; agent-tinted left border; M3 dialog; ESC close + scrim click + focus trap built-in; supports `tabs` array of `{id, label, content}`). That's the same component to reuse.

---

## 2. Goals

1. **Open spec in a full-view modal.** Replace `window.open(specPath, '_blank')` with mounting a `<SpecModal>` that wraps `<Modal variant="rich">`. Same chrome / sizing / close behaviour / agent-tinted scrim as the timeline-card full-view modal.
2. **Serve spec markdown over a real endpoint.** New `GET /api/specs/{spec_id}` reads from the `specs/` directory at the repo root, returns the raw markdown for the requested spec.
3. **Render spec markdown nicely.** Reuse the existing `<Markdown>` component (the same one that renders turn bodies + draft documents inside the timeline modal), so syntax highlighting / headings / code blocks / tables / lists all render correctly.
4. **Settle the screenshot question.** Every screenshot path in `VERSION_NOTES` must resolve to a real file on the live server, or be removed. § 6 picks "remove the impossible ones; keep + capture the small set we can actually verify on the live site." No more broken `<img>` tags.

## 3. Non-goals

- **No edits to the spec files themselves.** This spec doesn't add screenshots to the spec markdown; it only solves how the changelog renders them.
- **No restructure of the Changelog tab layout.** The cards, the filter chips, the search, the per-entry `<CollapsibleSection>` all stay the same.
- **No deep-link URLs for individual specs** (e.g. `#/spec/0121`). The modal is a transient in-overlay view; a deep-link surface is out of scope.
- **No spec list page.** Specs are reached only through Changelog entries; no standalone `/specs` route or browser.
- **No new spec frontmatter parsing or styling.** The modal renders the markdown verbatim through the existing `<Markdown>` pipeline.

---

## 4. Current-state audit

### 4.1 — How the timeline modal works (for reuse)

```jsx
// shared.jsx:382
function Modal({ open, onClose, title, subtitle, tabs, agent, agentTint, variant = 'split', footer, children }) { … }
```

Props relevant for our case:
- `open` + `onClose` — open/close
- `title` — modal heading (e.g. "Spec 0121 — How-It-Works overlay + Changelog tab rewrite")
- `subtitle` — optional secondary line (e.g. "v1.5.0 · 2026-05-20")
- `variant: 'rich'` — wide modal (~1080 px), agent-tinted left border possible
- `children` — body content when not using `tabs`
- Built-in: ESC close, scrim click close, focus trap, body overflow lock, return-focus-on-unmount

The timeline cards' `DocumentModal` shape:

```jsx
<Modal
  open={true}
  onClose={onClose}
  title={title}
  subtitle={subtitle}
  agent={agentSlot}
  tabs={[
    { id: 'content', label: 'Content', content: <LazyMarkdownBody filePath={item.filePath} /> },
    item.turnKey && { id: 'input', label: 'Agent Input', content: <InputTabContent turnKey={item.turnKey} /> },
    webSearch,
  ].filter(Boolean)}
/>
```

The body fetches via `window.useFileBody(filePath)` and renders with `<Markdown>`.

### 4.2 — How spec markdown is structured today

`specs/0121-how-it-works-and-changelog-rework.md` starts with a YAML frontmatter block:

```yaml
---
spec: 0121
title: How-It-Works overlay + Changelog tab — full content & component rewrite
label: new-feature
version-bump: MINOR
status: proposed
target-version: 1.5.0
created: 2026-05-20
pr: ""
---
```

Then the body (`# Spec 0121 — …`). The existing `<Markdown>` renderer in `static/markdown.js` (or wherever it lives — confirmed during impl) does not handle YAML frontmatter — it would render the leading `---` as a horizontal rule and the frontmatter as plain text. Two options:

- **(A) strip the frontmatter on the server** before returning the body. Cleanest. Server-side regex.
- **(B) render the frontmatter as a nicely-formatted "spec meta" header** at the top of the modal (spec ID + title + version-bump + status + target-version). Slightly nicer UX but more code.

Default in this spec: **(A) strip on server**. The modal title already shows "Spec NNNN — <title>"; duplicating the frontmatter inside is noise. The modal subtitle shows version + date.

### 4.3 — Current screenshot situation (from § 1.2)

9 broken paths across 4 entries. None are capturable from the live site as "before/after" pairs because the "before" code paths are gone (the pre-0114 modal, the pre-0118 cost card, etc.).

What IS capturable on the live site today:
- v1.5.0 (spec 0121): How-It-Works overlay — `Protocol overview` section, `Item taxonomy & categories` section, `Cost & consumption` section. All currently on `#/how-it-works`.
- v1.6.0 (spec 0125, to be added): Settings page `Allowlist` tab, Settings page `Users` tab. Both currently on `#/settings`.

What is NOT capturable:
- Anything that needs a real run (timeline turn card, critique pane filter row, cost card collapsed/unfolded, turn-modal right pane). The fixture-run requirement is the same as in spec 0121 § 12.4 (which was deferred). With no live runs, there's nothing to screenshot.

---

## 5. Proposed change — backend: `/api/specs/{spec_id}`

### 5.1 — Endpoint

```python
# In src/dual_research/ui/server.py, both _make_app and _make_supabase_app.

@app.get("/api/specs/{spec_id}")
async def get_spec_markdown(spec_id: str) -> PlainTextResponse:
    """Return the raw markdown body of a spec, frontmatter stripped.

    `spec_id` is the spec filename or its leading number — both
    `0121-how-it-works-and-changelog-rework` and `0121` work. Returns
    404 if no spec matches.
    """
    spec_id = spec_id.strip()
    if not _SPEC_ID_RE.match(spec_id):
        raise HTTPException(status_code=400, detail="invalid spec id")

    specs_dir = _resolve_specs_dir()
    # Try exact filename first; fall back to prefix match by leading digits.
    target = None
    if (specs_dir / f"{spec_id}.md").is_file():
        target = specs_dir / f"{spec_id}.md"
    else:
        # Prefix match: spec_id "0121" → "0121-*.md"
        for f in specs_dir.glob(f"{spec_id}-*.md"):
            target = f
            break
    if target is None or not target.is_file():
        raise HTTPException(status_code=404, detail="spec not found")

    text = target.read_text(encoding="utf-8")
    body = _strip_yaml_frontmatter(text)
    return PlainTextResponse(body, media_type="text/markdown; charset=utf-8")
```

Helpers (top-level in `server.py`):

```python
_SPEC_ID_RE = re.compile(r"^[0-9a-zA-Z][0-9a-zA-Z\-_]*$")

def _resolve_specs_dir() -> Path:
    """Resolve the repo's specs/ directory.

    Walks up from the server module file until it finds a sibling
    `specs/` directory. Tests stub via `app.state.specs_dir` if set.
    """
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / "specs"
        if candidate.is_dir() and (candidate / "0121-how-it-works-and-changelog-rework.md").exists():
            return candidate
    # Fallback: repo root sibling of src/
    return here.parents[3] / "specs"

_FRONTMATTER_RE = re.compile(r"^---\r?\n.*?\r?\n---\r?\n", re.DOTALL)

def _strip_yaml_frontmatter(text: str) -> str:
    """Strip a leading `--- … ---` YAML block, if present."""
    m = _FRONTMATTER_RE.match(text)
    if m:
        return text[m.end():].lstrip("\n")
    return text
```

### 5.2 — Why a server endpoint, not static-serving `specs/`

- **Defensive surface.** A regex-gated endpoint can't be tricked into reading arbitrary files (no path traversal — `spec_id` is matched against `^[0-9a-zA-Z][0-9a-zA-Z\-_]*$`).
- **Frontmatter strip happens once on the server**, not on every client.
- **Future-proof.** Want to render a different format (HTML?) or add caching? One place to change.

Alternative considered: mounting `specs/` at `/specs/` via `StaticFiles`. Cheaper but couples the public URL to repo layout, can't strip frontmatter, can't gate against files we don't want public.

### 5.3 — Tests

```
tests/ui/test_specs_api.py — new
  - returns 200 + body for "0121-how-it-works-and-changelog-rework"
  - returns 200 + body for "0121" (prefix match)
  - returns 404 for "9999" (no such spec)
  - returns 400 for "../etc/passwd" (regex reject)
  - returns 400 for "0121/../config" (regex reject)
  - body has frontmatter stripped (first non-blank line is `# Spec 0121 — …`)
  - Content-Type is text/markdown
```

---

## 6. Proposed change — frontend: SpecModal + click-handler swap + screenshot policy

### 6.1 — New `<SpecModal>` component

Lives in `how-it-works.jsx` (the same file as the existing `ChangelogEntry`).

```jsx
function SpecModal({ specId, version, date, summary, onClose }) {
  const [body, setBody] = React.useState(null);
  const [err, setErr] = React.useState(null);

  React.useEffect(() => {
    let cancelled = false;
    setBody(null);
    setErr(null);
    authedFetch(`/api/specs/${encodeURIComponent(specId)}`)
      .then(r => r.ok ? r.text() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(text => { if (!cancelled) setBody(text); })
      .catch(e => { if (!cancelled) setErr(String(e.message || e)); });
    return () => { cancelled = true; };
  }, [specId]);

  return (
    <Modal
      open={true}
      onClose={onClose}
      title={`Spec ${specId}`}
      subtitle={`v${version} · ${date} · ${summary}`}
      variant="rich"
    >
      <div className="spec-modal__body">
        {body === null && !err && <LoadingState size="inline" label="Loading spec…" />}
        {err && <div className="spec-modal__error">Couldn't load spec: {err}</div>}
        {body && <Markdown text={body} />}
      </div>
    </Modal>
  );
}
```

- Uses the SAME `<Modal>` component the timeline cards use → identical chrome.
- `variant="rich"` → wide layout (~1080 px), same as timeline.
- ESC / scrim / focus trap all inherited.
- Body uses the existing `<Markdown>` renderer the rest of the app uses.
- Loading + error states explicit.

CSS additions (small, spec-0126 block in `components.css`):

```css
.spec-modal__body {
  max-height: 75vh;
  overflow-y: auto;
  padding: var(--s-3) var(--s-2);
  font-size: var(--t-body);
  line-height: var(--lh-prose);
}
.spec-modal__body h1 { font-size: var(--t-title); margin-top: 0; }
.spec-modal__body h2 { font-size: var(--t-h3); margin-top: var(--s-6); }
.spec-modal__body h3 { font-size: var(--t-body); font-weight: var(--w-semi); margin-top: var(--s-4); }
.spec-modal__body table { width: 100%; border-collapse: collapse; font-size: var(--t-meta); }
.spec-modal__body th, .spec-modal__body td { padding: var(--s-2) var(--s-3); border-bottom: 1px solid var(--border-1); text-align: left; }
.spec-modal__body code { font-family: var(--mono); background: var(--bg-2); padding: 1px 4px; border-radius: 3px; font-size: var(--t-mono); }
.spec-modal__body pre { background: var(--bg-2); padding: var(--s-3) var(--s-4); border-radius: var(--r-2); overflow-x: auto; font-size: var(--t-mono); border: 1px solid var(--border-1); }
.spec-modal__error { color: var(--err); padding: var(--s-4); }
```

### 6.2 — ChangelogEntry: swap the click handler

In `how-it-works.jsx`, the existing pattern at ~line 1202–1209:

```jsx
{entry.specPath && (
  <div className="changelog-spec-link">
    <button
      type="button"
      className="md-btn md-btn--text md-btn--sm"
      onClick={() => window.open(entry.specPath, '_blank')}
    >Open spec ↗</button>
  </div>
)}
```

Becomes:

```jsx
{entry.specs && entry.specs.length > 0 && (
  <div className="changelog-spec-link">
    {entry.specs.map(s => (
      <button
        key={s}
        type="button"
        className="md-btn md-btn--text md-btn--sm"
        onClick={() => onOpenSpec({ specId: s, version: entry.version, date: entry.date, summary: entry.summary })}
      >Open spec {s} ↗</button>
    ))}
  </div>
)}
```

The parent (`ChangelogList` or `HowItWorksBody`) owns the open-spec state:

```jsx
const [openSpec, setOpenSpec] = React.useState(null);
// pass setOpenSpec as onOpenSpec to ChangelogEntry
// render: {openSpec && <SpecModal {...openSpec} onClose={() => setOpenSpec(null)} />}
```

**Why per-spec buttons instead of one-button-opens-first-spec:** entries can list multiple specs (v1.4.1 → spec 0120; v1.5.0 → spec 0121; etc., currently 1-to-1 — but the data shape supports multiple). The pre-0126 button used `entry.specPath` (singular, redundant with `entry.specs`). This spec drops `specPath` and uses `entry.specs[]` as the source of truth.

`VERSION_NOTES` entries get their `specPath` field removed; `specs: ['0121']` etc. is kept.

### 6.3 — Screenshot policy (the hard call)

Three options examined:

| Option | Cost | Outcome |
|---|---|---|
| **A.** Capture every screenshot referenced in `VERSION_NOTES` from the live site | High — needs a real run (which we don't have on live), needs both themes, needs surfaces that don't exist anymore | Most thorough but blocked by missing fixture run |
| **B.** Drop the `screenshots[]` arrays entirely. Render no images. | Low — pure deletion | Cleanest. No broken images. The "Open spec ↗" button satisfies the "show what changed" need. |
| **C.** Keep the `screenshots[]` field but mark each entry `screenshots: []` (no actual paths) for now, and document a capture protocol for when a fixture run lands. | Low — same as B but preserves the field for future use | Same UX as B today, with a smoother migration when fixtures land. |

**Default: C.** Empty screenshot arrays today; the field stays in place so future entries (or a future fixture-run population) can add screenshots without code changes. Plus: capture and **bundle** a small "starter set" of 2 screenshots for v1.6.0 that point at the **new Settings/Users page** — that surface exists on live, doesn't need a fixture run, and verifies the capture pipeline.

The starter set:
- `1.6.0/settings-users.dark.png` — `/settings#users` rendered in dark
- `1.6.0/settings-users.light.png` — same, light theme

Both bundled at `src/dual_research/ui/static/changelog-shots/1.6.0/`. Captured via Chrome MCP (now that we have it; the spec-0125 work confirmed it can reach the live site). Path resolves as `/changelog-shots/1.6.0/settings-users.{dark,light}.png` automatically via the existing static mount.

A new helper in `ChangelogEntry` skips the screenshots block when `entry.screenshots` is empty or missing, so the entries that drop screenshots render cleanly.

```jsx
{entry.screenshots && entry.screenshots.length > 0 && (
  <>
    <div className="crit-section-title">Screenshots</div>
    <div className="changelog-shots">
      {entry.screenshots.map((s, i) =>
        <figure key={i}>
          <img src={s.path} alt={s.alt} loading="lazy"
               onError={(e) => { e.target.closest('figure').style.display = 'none'; }} />
          <figcaption>{s.caption}</figcaption>
        </figure>
      )}
    </div>
  </>
)}
```

The `onError` handler is belt-and-suspenders: if a path 404s anyway, the figure hides itself instead of showing a broken-image icon. Net effect: zero visible-broken screenshots no matter what's in the data.

### 6.4 — Cleanup of broken screenshot paths in VERSION_NOTES

For v1.5.0, v1.4.1, v1.4.0, v1.3.0: set `screenshots: []`. The 9 broken paths are removed entirely.

For v1.6.0 (the new entry that will land with this spec): include the 2 settings-page screenshots (light + dark, both verified-reachable post-capture).

---

## 7. Files touched (exhaustive)

| Path | Status | Change |
|---|---|---|
| `specs/0126-changelog-spec-modal-and-working-screenshots.md` | new | this spec |
| `src/dual_research/ui/server.py` | edit | add `GET /api/specs/{spec_id}` to both `_make_app` (fs mode) and `_make_supabase_app` (hosted mode) + helpers `_resolve_specs_dir`, `_strip_yaml_frontmatter`, `_SPEC_ID_RE`, `_FRONTMATTER_RE` |
| `tests/ui/test_specs_api.py` | new | endpoint coverage |
| `src/dual_research/ui/static/how-it-works.jsx` | edit | add `<SpecModal>`; rewrite the `Open spec ↗` button handler; clear `screenshots: []` for v1.3.0 / v1.4.0 / v1.4.1 / v1.5.0; add v1.6.0 entry with 2 working screenshots; drop `specPath` field |
| `src/dual_research/ui/static/components.css` | append | `.spec-modal__body` + `.spec-modal__error` (small block) |
| `src/dual_research/ui/static/changelog-shots/1.6.0/settings-users.dark.png` | new | captured live |
| `src/dual_research/ui/static/changelog-shots/1.6.0/settings-users.light.png` | new | captured live |
| `src/dual_research/ui/static/index.html` | edit | cache-bust bump |
| `src/dual_research/__init__.py` | edit | `1.6.0 → 1.6.1` |
| `CHANGELOG.md` | edit | new entry under `[Unreleased] / Fixed` |

---

## 8. Acceptance criteria

### 8.1 — Backend

- [ ] `curl https://<host>/api/specs/0121` returns HTTP 200 with `Content-Type: text/markdown; charset=utf-8` and body starting with `# Spec 0121 — How-It-Works overlay …` (no leading `---` YAML frontmatter).
- [ ] `curl https://<host>/api/specs/0121-how-it-works-and-changelog-rework` returns the same body.
- [ ] `curl https://<host>/api/specs/9999` returns HTTP 404.
- [ ] `curl https://<host>/api/specs/..%2Fetc%2Fpasswd` returns HTTP 400.
- [ ] `uv run pytest tests/ui/test_specs_api.py -q` → green.
- [ ] Existing tests stay green.

### 8.2 — Frontend

- [ ] On `/#/how-it-works` → Changelog tab, every visible entry's "Open spec N ↗" button opens a `<SpecModal>` (not a new tab).
- [ ] The modal shows the spec content rendered as markdown (headings, tables, code blocks). Spec frontmatter is NOT shown.
- [ ] The modal's title shows `Spec NNNN` and subtitle shows `v<version> · <date> · <summary>`.
- [ ] The modal uses the same chrome as the timeline-card full-view modal (M3 dialog, ESC closes, scrim click closes, body overflow lock, focus trap).
- [ ] Modal body scrolls internally; modal itself fills ~75 vh of vertical space.
- [ ] No `<img>` tag in the Changelog tab references a 404'ing path. `Network` panel shows 0 failed image loads on the Changelog tab.
- [ ] v1.6.0 entry shows 2 screenshots (light + dark of the Settings/Users page), both load successfully (`HTTP 200`).
- [ ] `<img onError>` handler hides figures whose source fails (belt-and-braces).

### 8.3 — Cache-bust + version

- [ ] `?v=0125b → ?v=0126a` in `index.html`.
- [ ] `__version__ = "1.6.1"` in `__init__.py`.
- [ ] `CHANGELOG.md` has a new `[Unreleased] / Fixed` entry.

---

## 9. Test plan

- [ ] **Unit** — test_specs_api covers the cases in § 5.3.
- [ ] **Manual — open spec modal.** Click "Open spec 0121 ↗" on the v1.5.0 entry. Modal opens with the spec rendered cleanly. ESC closes. Click-outside closes.
- [ ] **Manual — opens different specs.** Repeat for 0120, 0119, 0118 — all render.
- [ ] **Manual — modal scroll.** Spec body is long enough to scroll inside the modal. Modal chrome stays fixed.
- [ ] **Manual — theme toggle.** While the modal is open, toggle theme. Body re-renders correctly (markdown styling uses tokens).
- [ ] **Manual — verify no 404 images.** Open browser devtools → Network → filter `Img` → reload the Changelog tab. 0 failed requests for `changelog-shots/*`.
- [ ] **Manual — v1.6.0 screenshots load.** Both 2 settings-users screenshots load successfully and display under the entry.
- [ ] **Cross-browser** — Safari, Chrome, Firefox: modal renders + closes correctly.

---

## 10. Risks

- **Frontmatter regex over-strips.** A spec without frontmatter still loads correctly (regex doesn't match → no-op). Verified by including 2 test cases: spec WITH frontmatter, spec WITHOUT.
- **Path traversal.** `_SPEC_ID_RE` only allows `[0-9a-zA-Z][0-9a-zA-Z\-_]*` — no `..`, no `/`, no extension. The endpoint refuses anything else with 400.
- **Spec body too long for modal.** A 2,500-line spec (e.g. spec 0121) needs internal scroll. `.spec-modal__body { max-height: 75vh; overflow-y: auto; }` handles it.
- **Markdown renderer chokes on a YAML-frontmatter-less syntactic edge case.** The existing `<Markdown>` already renders turn bodies + draft documents (markdown that can have arbitrary structure). Specs use only markdown features the renderer already handles (tables, fenced code, lists, headings). No new edge cases.
- **Live capture of Settings/Users screenshot includes user-identifiable emails.** That's already the user's own account on the live site (private to them). Acceptable.
- **Tests on the specs endpoint require the specs/ directory to exist next to src/.** In CI it does (the repo checkout); locally too. If a future deploy strips specs/, the endpoint 404s — same failure mode as today. § 11 OQ-1 captures the deferred decision: bundle specs into the Docker image vs. read from the repo.

---

## 11. Out of scope (explicit)

- **No `/api/specs` list endpoint.** Only fetch-by-id. Listing is unnecessary — the changelog already knows which specs exist.
- **No syntax highlighting beyond what the existing `<Markdown>` does.** Code blocks render with a mono background; no language-specific highlighting.
- **No frontmatter-as-table-of-contents.** Frontmatter is stripped, not displayed.
- **No spec edit / annotation in the modal.** Read-only.
- **No fixture-run-based screenshots for v1.5.0 / v1.4.x / v1.3.0 entries.** Those stay empty (per § 6.3 option C) until a fixture run becomes available.
- **No retroactive bundling of all 80+ historic specs into Docker.** Defer to OQ-1.

---

## 12. Open questions

- **OQ-1.** Should `specs/` be copied into the Docker image at build time so the endpoint works regardless of how the app is deployed? *Default: yes (a one-line `COPY specs/ /app/specs/` in the Dockerfile). Confirm during impl that Fly's existing Dockerfile copies `specs/` already — it likely does since the whole repo is COPYed.*
- **OQ-2.** Should the modal also load and render any images referenced inside the spec body (e.g. `![…](/diagrams/...)`)? *Default: yes — the existing `<Markdown>` already resolves `<img>` tags to the static-mount paths, so this works for free.*
- **OQ-3.** Should the avatar menu add a "Browse all specs" entry? *Default: no — out of scope per § 3. Changelog is the only entry point.*

---

## 13. Backend touched?

**yes** — one new endpoint, two helpers, two regexes.
