---
spec: 0123
title: How-It-Works as a full-page route + click-to-enlarge SVG viewer
label: new-feature
version-bump: PATCH
status: proposed
target-version: 1.5.1
created: 2026-05-20
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0123 — How-It-Works as a full-page route + click-to-enlarge SVG viewer

> Ship bucket: **Frontend-only follow-up to spec 0121.**
> Depends on: **0121** (How-It-Works overlay + Changelog tab rewrite).
> Complexity: **S** — two narrow UI changes, one component split + one new modal.
> Targeted version bump: **PATCH (1.5.0 → 1.5.1)** — user-visible change to the same surface, no API / contract changes.

---

## 1. Context

Two issues with spec 0121's How-It-Works overlay:

1. **Modal cramps the content.** The overlay is rendered as `<Modal variant="rich">` (1080 px max-width, 92 vh max-height) with a scrim. Long sections — the Phase 0 / Phase 2 / Phase 4 input lists, the per-piece cost table, the lifecycle transition table — overflow inside the modal and require scrolling within scrolling. The viewport has 1440+ px of horizontal space available on most desktops; the modal uses 75 % of it and dedicates the rest to dim scrim. The content is reference documentation, not a transient action — it should live at a real URL like Design Language (`#/language`), Settings (`#/settings`), Compare (`#/compare`), Search (`#/search`), which already render as full-page routes.

2. **SVGs are unreadable at embed size.** The seven new diagrams from spec 0121 render at 100 % of the `.hiw-diagram` container width (~ 960 px effective inside the modal). The pipeline diagram (`01-pipeline.{light,dark}.svg`) was drawn at 1660 × 980 viewBox — scaling down to 960 px makes the per-input row labels and the per-phase category-bubble chips illegible. Users have no way to see the SVGs at their authored size. Every embedded SVG on the page suffers the same problem.

Both fixes are minimally invasive:

1. **Route the overlay.** `HowItWorksPage` (already wired at `route.view === 'how-it-works'` in `app.jsx:176`) becomes the canonical entry. The modal-mode `<HowItWorks open onClose>` is retired. Every trigger that opened the modal navigates to `#/how-it-works` instead.

2. **Add a viewer modal.** A new `<DiagramViewer>` component renders a scrim-backed near-fullscreen image when clicked. Every `<HiwDiagram>` becomes click-to-enlarge. Same theme-aware SVG variant; same `Esc` / click-scrim close.

---

## 2. Goals

1. **How-It-Works renders as a full-page route.** Same content, same 11 sections, same Changelog tab — just no modal chrome, no scrim, no 1080 px width cap. Uses the whole viewport (capped at `--md-content-max` = 1440 px per existing convention).
2. **Every existing trigger navigates to the route.** Chrome bar "How it works" link + avatar-menu link + onboarding tour link + `HowItWorksLink` chip — all call `navigate('how-it-works')` (i.e. update `window.location.hash` to `#/how-it-works`). The modal state (`howOpen` / `setHowOpen` / `openHow` / `closeHow` in `app.jsx`) is deleted.
3. **Every embedded diagram is click-to-enlarge.** `<HiwDiagram>` wraps its `<img>` in a button (full surface, cursor-pointer, focusable). Click → opens `<DiagramViewer>` showing the same SVG at near-viewport size (`max-width: 95 vw, max-height: 90 vh, object-fit: contain`). Esc / click-scrim / close-button dismisses. Theme-aware: viewer follows the current theme just like the embed.
4. **No regression.** Direct-link URLs (`#/how-it-works`) work. Deep-links to a section anchor (`#hiw-cost` etc.) still scroll into view. Browser back navigates back to the page the user was on.

## 3. Non-goals

- **No content changes.** Section text, diagram briefs, chip vocabulary, VERSION_NOTES — all unchanged.
- **No new diagrams.** The 14 SVGs from spec 0121 are reused as-is.
- **No SVG-internal zoom controls** (pan/zoom inside the viewer). The viewer is a "show me bigger" modal, not an interactive diagram explorer. Browser zoom (`Cmd/Ctrl +`) inside the viewer still works for further zoom.
- **No design-language-page extraction of the viewer.** `<DiagramViewer>` lives locally in `how-it-works.jsx` for this spec. If another surface needs it, a follow-up spec lifts it to `shared.jsx`.
- **No URL state for the viewer-open state.** Opening the viewer is a transient UI action; it doesn't push a history entry. Closing it leaves the URL on the section anchor.
- **No changes to the onboarding tour beyond updating the trigger.** The tour still references "click here for How it works"; the click now navigates instead of opening the modal.

---

## 4. Current-state audit

### 4.1 — How the overlay is wired today

| File | Lines | What it does |
|---|---|---|
| `app.jsx:78-94` | `howOpen` React state + `openHow` / `closeHow` callbacks | Modal open/close state |
| `app.jsx:169` | `<ChromeBar … onOpenHow={openHow} />` | Trigger flows into chrome |
| `app.jsx:176` | `{route.view === 'how-it-works' && <HowItWorksPage />}` | Route-mounted page (currently stub) |
| `app.jsx:186` | `<HowItWorks open={howOpen} onClose={closeHow} />` | Modal mount point |
| `how-it-works.jsx:HowItWorks` | The whole modal — header, side menu, content, scrim | Currently does everything |
| `how-it-works.jsx:HowItWorksPage` | Vestigial stub — dispatches `dr-open-how-it-works` event | What route renders today |
| `ChromeBar` (in `app.jsx`) | "How it works" link/tab in the chrome | Calls `onOpenHow` on click |
| `RightCluster` / avatar-menu (in `app.jsx`) | "How it works" item | Calls `onOpenHow` on click (TBD — to verify during impl) |
| `onboarding.jsx` | Tour step that points at the HIW chrome tab | Doesn't navigate; just points at the trigger |

### 4.2 — How `<HiwDiagram>` renders today

```jsx
function HiwDiagram({ name, alt }) {
  const variant = useThemeMode();
  return (
    <div className="hiw-diagram">
      <img src={`/diagrams/how-it-works/${name}.${variant}.svg?v=0121a`} alt={alt} loading="lazy" />
    </div>
  );
}
```

The `.hiw-diagram` wrapper has `padding: var(--s-3); border: 1px solid var(--border-1); border-radius: var(--r-3)`. The `<img>` has `width: 100%; height: auto`. No click handler, no cursor affordance, no focusability.

---

## 5. Proposed change

### 5.1 — Route the overlay

**Split `HowItWorks` into a render function and a page wrapper.**

The pre-spec `HowItWorks({ open, onClose })` component embeds the full UI inside the modal scrim. Refactor to:

```jsx
function HowItWorksBody() {
  // The 11 sections + the tab switcher + the side menu + the changelog tab.
  // Everything currently inside <HowItWorks> EXCEPT the .md-dialog__scrim / .md-dialog wrappers
  // and the Escape-to-close handler.
  return (/* … */);
}

function HowItWorksPage() {
  // Full-page route mount. No modal, no scrim. Page-level layout.
  return (
    <div className="hiw-page">
      <HowItWorksBody />
    </div>
  );
}

// HowItWorks (the modal-mode component) is DELETED.
// window.HowItWorks export is removed.
// window.HowItWorksPage continues to export the new page.
```

**Edits to `app.jsx`:**

- **Delete** `howOpen` / `openHow` / `closeHow` state + callbacks (lines 78-94).
- **Delete** the `<HowItWorks open={howOpen} onClose={closeHow} />` mount (line 186).
- **Replace** every `onOpenHow={openHow}` prop pass with `navigate={navigate}` (which is already plumbed everywhere).
- **Update** every site that previously called `onOpenHow()` to instead call `navigate('how-it-works')`.

**Edits to onboarding (if needed):**

- The onboarding tour's HIW-related step (if it dispatches `dr-open-how-it-works`) is updated to call `navigate('how-it-works')` instead. To verify during implementation by `grep "dr-open-how-it-works"` and `grep "onOpenHow"` across the static dir.

### 5.2 — Page-level layout

The new `.hiw-page` class replaces the modal chrome (`.md-dialog__scrim` + `.md-dialog.md-dialog--rich`) and the inner layout. CSS additions to `components.css`:

```css
/* spec-0123: How-It-Works page layout */
.hiw-page {
  height: 100%;
  overflow-y: auto;
  background: var(--bg-0);
}
.hiw-page__inner {
  max-width: var(--md-content-max);   /* 1440 px */
  margin: 0 auto;
  padding: var(--s-8) var(--s-6);
}
.hiw-page__header {
  display: flex; align-items: center; gap: var(--s-4);
  padding-bottom: var(--s-5);
  border-bottom: 1px solid var(--border-1);
  margin-bottom: var(--s-6);
}
.hiw-page__title {
  margin: 0; font-size: var(--t-display); font-weight: var(--w-semi);
  color: var(--fg-0);
}
.hiw-page__spacer { flex: 1; }

/* The side-menu + content split — same grid as the modal version,
   wider gutters since we have whole-viewport room now. */
.hiw-page__layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: var(--s-8);
  align-items: start;
}
.hiw-page__menu {
  position: sticky;
  top: var(--s-4);
  align-self: start;
  padding: var(--s-4);
  background: var(--bg-1);
  border: 1px solid var(--border-1);
  border-radius: var(--r-3);
}
.hiw-page__menu .hiw-overlay__menu-list {
  /* reuses the existing menu-list styles from spec 0121 */
}
.hiw-page__content {
  min-width: 0;     /* prevents children from forcing horizontal scroll */
}

/* Tab strip — same look as the modal-mode tabs, just larger touch target */
.hiw-page__tabs {
  display: inline-flex; gap: 2px;
  background: var(--bg-2); padding: 2px;
  border-radius: var(--r-2);
}
.hiw-page__tabs .tab {
  appearance: none; background: transparent; border: none;
  padding: 8px 16px; border-radius: var(--r-2);
  font-family: var(--sans); font-size: var(--t-body); font-weight: var(--w-medium);
  color: var(--fg-2); cursor: pointer;
}
.hiw-page__tabs .tab.is-active {
  background: var(--bg-1); color: var(--fg-0); box-shadow: var(--e-1);
}
```

The existing `.hiw-*` / `.cs-*` / `.cl-*` / `.changelog-*` classes are reused unchanged.

**Diagram size note:** with the wider content column (~1160 px on a 1440 px viewport, after the 240 px menu + gutters) the embedded diagrams render larger by default — closer to but still smaller than their authored 1660 px viewBox. The click-to-enlarge viewer (§ 5.3) takes care of the rest.

### 5.3 — DiagramViewer (click-to-enlarge)

**New component in `how-it-works.jsx`:**

```jsx
function DiagramViewer({ src, alt, onClose }) {
  React.useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') { e.stopPropagation(); onClose(); }
    }
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [onClose]);

  function onScrimClick(e) {
    if (e.target === e.currentTarget) onClose();
  }

  return (
    <div
      className="diagram-viewer__scrim"
      onClick={onScrimClick}
      role="dialog"
      aria-modal="true"
      aria-label={alt}
    >
      <button
        type="button"
        className="diagram-viewer__close"
        onClick={onClose}
        aria-label="Close diagram viewer"
      >×</button>
      <img className="diagram-viewer__img" src={src} alt={alt} />
    </div>
  );
}
```

**`<HiwDiagram>` is upgraded** to host a state for the viewer + render a click-to-open button wrapper around the embed:

```jsx
function HiwDiagram({ name, alt }) {
  const variant = useThemeMode();
  const src = `/diagrams/how-it-works/${name}.${variant}.svg?v=0123a`;
  const [open, setOpen] = React.useState(false);
  return (
    <React.Fragment>
      <button
        type="button"
        className="hiw-diagram hiw-diagram--clickable"
        onClick={() => setOpen(true)}
        aria-label={`Enlarge: ${alt}`}
      >
        <img src={src} alt={alt} loading="lazy" />
        <span className="hiw-diagram__hint" aria-hidden="true">⤢ click to enlarge</span>
      </button>
      {open && <DiagramViewer src={src} alt={alt} onClose={() => setOpen(false)} />}
    </React.Fragment>
  );
}
```

**CSS additions:**

```css
/* spec-0123: clickable diagram wrapper + viewer modal */
.hiw-diagram--clickable {
  display: block;
  width: 100%;
  appearance: none;
  background: var(--bg-1);
  border: 1px solid var(--border-1);
  border-radius: var(--r-3);
  padding: var(--s-3);
  margin: var(--s-5) 0;
  cursor: zoom-in;
  position: relative;
  transition: border-color var(--m-fast) var(--ease), background var(--m-fast) var(--ease);
}
.hiw-diagram--clickable:hover {
  border-color: var(--border-2);
  background: var(--bg-2);
}
.hiw-diagram--clickable:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-offset);
}
.hiw-diagram--clickable img { width: 100%; height: auto; display: block; }
.hiw-diagram__hint {
  position: absolute;
  top: var(--s-3);
  right: var(--s-3);
  background: var(--bg-2);
  color: var(--fg-3);
  font-family: var(--mono); font-size: var(--t-mono);
  padding: 2px 8px; border-radius: var(--r-pill);
  border: 1px solid var(--border-1);
  opacity: 0;
  transition: opacity var(--m-fast) var(--ease);
  pointer-events: none;
}
.hiw-diagram--clickable:hover .hiw-diagram__hint,
.hiw-diagram--clickable:focus-visible .hiw-diagram__hint { opacity: 1; }

.diagram-viewer__scrim {
  position: fixed; inset: 0;
  z-index: 1000;
  background: color-mix(in srgb, var(--bg-0) 92%, transparent);
  display: flex; align-items: center; justify-content: center;
  padding: var(--s-6);
  cursor: zoom-out;
}
.diagram-viewer__img {
  max-width: 95vw;
  max-height: 90vh;
  width: auto; height: auto;
  display: block;
  object-fit: contain;
  background: var(--bg-1);
  border: 1px solid var(--border-1);
  border-radius: var(--r-3);
  box-shadow: var(--e-2);
  cursor: default;
}
.diagram-viewer__close {
  position: fixed;
  top: var(--s-5);
  right: var(--s-5);
  width: 40px; height: 40px;
  border-radius: var(--r-pill);
  background: var(--bg-2);
  border: 1px solid var(--border-2);
  color: var(--fg-0);
  font-size: 22px; line-height: 1;
  cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
}
.diagram-viewer__close:hover { background: var(--bg-3); }
.diagram-viewer__close:focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-offset);
}
```

### 5.4 — Cache-bust bump

Bump `?v=0121a → ?v=0123a` everywhere in:
- `src/dual_research/ui/static/index.html` (every `?v=` reference)
- `src/dual_research/ui/static/how-it-works.jsx` (the `<HiwDiagram>` SVG URLs)

---

## 6. Files touched (exhaustive)

| Path | Change |
|---|---|
| `specs/0123-how-it-works-as-page-and-diagram-viewer.md` | **created** — this spec |
| `src/dual_research/ui/static/how-it-works.jsx` | Split `HowItWorks` into `HowItWorksBody` + `HowItWorksPage`; delete the old `HowItWorks` (modal version); update `<HiwDiagram>` to be clickable + open `DiagramViewer`; add `DiagramViewer` component; bump SVG cache-bust to `?v=0123a`. Remove `window.HowItWorks` export (keep `window.HowItWorksPage`). |
| `src/dual_research/ui/static/components.css` | Append spec-0123 block: `.hiw-page`, `.hiw-page__inner`, `.hiw-page__header`, `.hiw-page__title`, `.hiw-page__spacer`, `.hiw-page__layout`, `.hiw-page__menu`, `.hiw-page__content`, `.hiw-page__tabs`, `.hiw-diagram--clickable`, `.hiw-diagram__hint`, `.diagram-viewer__scrim`, `.diagram-viewer__img`, `.diagram-viewer__close`. ~80 lines net. |
| `src/dual_research/ui/static/app.jsx` | Delete `howOpen` state + `openHow` / `closeHow` callbacks; delete `<HowItWorks>` mount on line 186; update every `onOpenHow={openHow}` prop pass to `navigate={navigate}` (or remove if unused); update every `onOpenHow()` call to `navigate('how-it-works')`. |
| `src/dual_research/ui/static/onboarding.jsx` | If the tour dispatches `dr-open-how-it-works`, replace with `navigate('how-it-works')`. (Confirm during impl.) |
| Any other JSX file that calls `onOpenHow` or dispatches `dr-open-how-it-works` | Same treatment. (Grep during impl.) |
| `src/dual_research/ui/static/index.html` | Cache-bust bump `?v=0121a → ?v=0123a`. |
| `src/dual_research/__init__.py` | Version bump `1.5.0 → 1.5.1`. |
| `CHANGELOG.md` | New entry under `[Unreleased]` describing this spec. |

No backend files. No new dependencies. No diagram changes (the 14 SVGs are reused as-is).

---

## 7. Acceptance criteria

### 7.1 — Page-route behavior

- [ ] Navigating to `#/how-it-works` renders the full overlay content as a full-page view (no scrim, no centered modal).
- [ ] Clicking "How it works" anywhere in the chrome bar / avatar menu / onboarding tour navigates to `#/how-it-works` (URL changes, content swaps in `#main`).
- [ ] The page uses up to `--md-content-max` (1440 px) of horizontal space — significantly wider than the previous 1080 px modal.
- [ ] Side menu is sticky on the left; clicking a section name scrolls the content column to the anchor.
- [ ] Section anchors (`#hiw-overview`, `#hiw-cost`, etc.) deep-link correctly — pasting `#/how-it-works#hiw-cost` lands on the page with the Cost section in view.
- [ ] Switching to the Changelog tab updates the rendered content (in place; no URL change to the hash; both tabs share `#/how-it-works`).
- [ ] Browser Back returns to the page the user was on before clicking "How it works".

### 7.2 — DiagramViewer behavior

- [ ] Every `<HiwDiagram>` shows a `cursor: zoom-in` cursor on hover.
- [ ] Hovering or keyboard-focusing the diagram surfaces a `⤢ click to enlarge` hint chip in the top-right corner.
- [ ] Clicking any diagram opens the viewer modal centered over the page with the SVG sized to `max(95vw, 90vh)` (`object-fit: contain`).
- [ ] Pressing `Esc` closes the viewer.
- [ ] Clicking outside the SVG (on the scrim) closes the viewer.
- [ ] Clicking the `×` button in the top-right closes the viewer.
- [ ] The viewer respects the current theme (the same SVG variant — light or dark — that was embedded is shown enlarged).
- [ ] All 7 of the spec-0121 diagrams enlarge correctly in both themes (14 paths total).
- [ ] Keyboard: Tab focuses the diagram button; Enter / Space activates it; viewer's close button is reachable via Tab.

### 7.3 — Cleanup verification

- [ ] `git grep "onOpenHow\|dr-open-how-it-works\|howOpen\|setHowOpen\|openHow\|closeHow" src/dual_research/ui/static/` returns 0 hits after the implementation pass.
- [ ] `git grep "<HowItWorks " src/dual_research/ui/static/` returns 0 hits (the modal-mode component is fully retired).
- [ ] `window.HowItWorks` is removed; `window.HowItWorksPage` remains.

### 7.4 — Build / no regressions

- [ ] `uv run pytest tests/ -q` → green.
- [ ] No browser-console errors when loading `#/how-it-works` or opening the viewer.
- [ ] Theme toggle while viewer is open swaps the SVG variant cleanly (the viewer reads from the same `useThemeMode` source).

---

## 8. Test plan

- [ ] **Manual — navigation.** Click "How it works" from chrome / avatar / onboarding. URL changes to `#/how-it-works`. Content fills the viewport. Browser Back returns to prior page.
- [ ] **Manual — deep link.** Paste `https://dual-research-alex.fly.dev/#/how-it-works#hiw-cost` in a fresh tab. Page loads with Cost section in view (scroll-margin handles the top offset).
- [ ] **Manual — sticky menu.** Scroll the content column. Side menu stays sticky on the left.
- [ ] **Manual — tab switch.** Click Changelog. Content swaps to changelog view. Click How it works. Content swaps back.
- [ ] **Manual — viewer open/close.** Click each of the 7 embedded diagrams (in both themes — 14 paths). Each opens the viewer with the correct SVG variant. Esc / scrim-click / × button all close.
- [ ] **Manual — keyboard.** Tab to a diagram, Enter to open viewer, Esc to close. Focus returns to the diagram.
- [ ] **Manual — theme switch while viewer open.** Open viewer in dark, toggle theme, expect viewer to swap to light variant.
- [ ] **Manual — no regression on other surfaces.** Load `/`, `/runs/<id>`, `/compare`, `/search`, `/language`, `/settings` — chrome bar still works, no console errors.
- [ ] **Automated.** `uv run pytest tests/ -q` → green.

---

## 9. Risks

- **Trigger sites missed.** If `onOpenHow` is plumbed through multiple components, missing one would leave a dead callback. Mitigation: § 7.3 grep checks catch this.
- **Sticky menu height.** A very tall side menu could clip on short viewports. Mitigation: `align-self: start` and content scrolls independently; the menu itself fits comfortably (11 sections × ~28 px each = ~310 px tall).
- **Viewer image size on portrait monitors.** On tall narrow viewports (e.g. iPad portrait), `max-height: 90 vh` could make the SVG taller than wide. Mitigation: `object-fit: contain` preserves aspect ratio; image stays readable. Worst case the viewer shows the SVG at its natural size with whitespace around it.
- **Click on a chip inside a diagram footnote.** Diagrams have no interactive children; clicking anywhere on the diagram triggers the viewer. (If a future diagram embeds clickable text, the brief should avoid that.)
- **Browser zoom + viewer.** Browser zoom (Cmd/Ctrl +) inside the viewer compounds. Confirmed acceptable — that's the user's choice.

---

## 10. Out of scope (explicit)

- **No SVG pan/zoom controls.** The viewer is a static "show me bigger" modal.
- **No `<DiagramViewer>` lift to `shared.jsx`.** Lives locally in `how-it-works.jsx`. Future spec can lift if needed.
- **No diagram content changes.** The 14 SVGs from spec 0121 are reused at the same paths.
- **No `<HowItWorks>` modal-mode wrapper kept as a fallback.** Fully retired; only the page-route renders the content.

---

## 11. Open questions

- **OQ-1.** Should the side menu collapse on narrow viewports (< 900 px)? *Default: yes — hide the menu and show a top breadcrumb-style anchor link list inline above the content. Implementer's call during impl.*
- **OQ-2.** Should the page have a title in the browser tab (`document.title = 'How it works · Dual Research'`)? *Default: yes; ~3 lines in the page component. Mirrors how Compare / Search update title.*
- **OQ-3.** Should we add a "Back to home" button in the page header? *Default: no — the browser back button and the chrome bar's back-arrow cover this. The page header just shows "How it works" + the tab strip.*

---

## 12. Backend touched?

**no.** Pure frontend.
