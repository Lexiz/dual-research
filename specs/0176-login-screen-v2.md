---
kind: dev
spec: "0176"
slug: login-screen-v2
title: Login screen v2 — animated hero, theme toggle continuity, looping chatter
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.36.0
status: deployed
depends_on: []
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T22:35:00Z"
started_at: "2026-05-23T09:34:11Z"
merged_at: "2026-05-23T09:47:45Z"
deployed_at: "2026-05-23T09:56:37Z"
pr: "https://github.com/Lexiz/dual-research/pull/205"
handover: "handoffs/2026-05-23-spec-0176-login-screen-v2.md"
failure_step: ""
source_session: pre-lifecycle-bootstrap
promoted_from_draft: "002"
---

# Spec 0176 — Login screen v2: animated hero, theme toggle continuity, looping chatter

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — user-facing UI redesign of a public-facing surface; no breaking changes, no schema deltas, no protocol changes. The localStorage key and Supabase OAuth flow are unchanged.
> **Evidence:** design-iteration session against the (uncommitted) mockup at `/tmp/login-mockup.html` (the design reference for the implementer to compare visually). Replaces `LandingScreen` in [`src/dual_research/ui/static/auth.jsx:152`](src/dual_research/ui/static/auth.jsx) end-to-end. Coexists with [spec 0175](specs/0175-summary-tab-v2.md) (touches `run-detail.jsx` only — no overlap). Aligns with the theme-continuity + reduced-motion pattern shipped in [spec 0169 §2.7](specs/0169-dashboard-redesign-v2-tabs-themes-history.md) and the M3 chrome / motion language reaffirmed in [spec 0164](specs/0164-timeline-pane-card-chrome-and-phase-header.md) / [spec 0165](specs/0165-timeline-pane-chip-polish-and-token-drift.md) / [spec 0168](specs/0168-critique-pane-item-card-refresh.md).

---

## 1. Context

The current `LandingScreen` ([`auth.jsx:152`](src/dual_research/ui/static/auth.jsx)) does its job — Google sign-in, allowlist note, a small agent-duo visual — but it has three rough edges:

1. **No theme control before sign-in.** A user who prefers light mode (or dark mode, against the default) cannot express that preference until after they've signed in. The first impression is forced. The in-app `ThemeToggle` only mounts inside `ChromeBar` (in [`app.jsx`](src/dual_research/ui/static/app.jsx)), which is gated behind a valid session.
2. **The `DemoRunCapsule` over-explains.** It tries to communicate what a "dual-research run" looks like via a flat dump of phases, timeline samples, critique items, outcome, and confidence. On a sign-in screen that's information without a goal — the user can't act on it, can't open it, can't read a real run, and the visual weight competes with the sign-in CTA. Two AI agents converging on a document is better shown than described, and better shown as motion than as a static card.
3. **No personality.** The product's character is two agents in conversation. The current landing communicates nothing of that.

Over the design-iteration session captured in `/tmp/login-mockup.html` (not committed), we converged on:

- A small animated hero showing the two agents and a document briefly materialising between them.
- Tighter copy with a serif title for "considered research tool" feel.
- A top-bar theme toggle that **lands at the same X coordinate** the post-login `ThemeToggle` occupies, so the icon stays put when the user signs in.
- A looping `Claude ↔ ChatGPT` conversation pill, replacing the demo capsule. Only one badge is visible at a time; they alternate; periodically they break the fourth wall to acknowledge the loop.

This spec ports that final mockup state into `auth.jsx` and shares the `ThemeToggle` primitive between `auth.jsx` and `app.jsx`.

### 1.1 — Current-state references (verified against `main`)

| File | Line | Role |
|---|---|---|
| [`src/dual_research/ui/static/auth.jsx:152`](src/dual_research/ui/static/auth.jsx) | function | `LandingScreen()` — the function this spec rewrites. |
| [`src/dual_research/ui/static/auth.jsx:104`](src/dual_research/ui/static/auth.jsx) | function | `AgentDuoVisual()` — currently used by `LandingScreen` AND by `NotApprovedScreen` at line 215. Kept (not deleted) per §2.7. |
| [`src/dual_research/ui/static/auth.jsx:141`](src/dual_research/ui/static/auth.jsx) | function | `GoogleGlyph()` — kept; still used in the new design's sign-in button. |
| [`src/dual_research/ui/static/auth.jsx:202`](src/dual_research/ui/static/auth.jsx) | function | `NotApprovedScreen()` — gains the new top-bar (see §2.3) but keeps `AgentDuoVisual()` on its body for now. |
| [`src/dual_research/ui/static/auth.jsx:251`](src/dual_research/ui/static/auth.jsx) | function | `DemoRunCapsule()` — removed (§2.7). |
| [`src/dual_research/ui/static/auth.jsx:386`](src/dual_research/ui/static/auth.jsx) | re-export | `window.DemoRunCapsule` — removed; repo-grep shows zero consumers outside `auth.jsx` (verified). |
| [`src/dual_research/ui/static/app.jsx:20`](src/dual_research/ui/static/app.jsx) | hook init | `localStorage['dr.theme']` read on mount. The login screen mirrors this exactly. |
| [`src/dual_research/ui/static/app.jsx:307`](src/dual_research/ui/static/app.jsx) | component | `RightCluster` — consumes the extracted `ThemeToggle`. |
| [`src/dual_research/ui/static/app.jsx:533`](src/dual_research/ui/static/app.jsx) | component | `ThemeToggle` — extracted to shared module (§2.9). |
| [`src/dual_research/ui/static/app.jsx:563`](src/dual_research/ui/static/app.jsx) | component | `ThemeIconBtn` — extracted with `ThemeToggle`. |
| [`src/dual_research/ui/static/app.jsx:584`](src/dual_research/ui/static/app.jsx) | component | `SunIcon` — extracted. |
| [`src/dual_research/ui/static/app.jsx:594`](src/dual_research/ui/static/app.jsx) | component | `MoonIcon` — extracted. |
| [`src/dual_research/ui/static/shared.jsx`](src/dual_research/ui/static/shared.jsx) ~41–50 | object | `BRAND_SVGS.claude` / `BRAND_SVGS.openai` — reused inside the chatter badges. |
| [`src/dual_research/ui/static/shared.jsx`](src/dual_research/ui/static/shared.jsx) ~1024–1028 | components | `ClaudeMonogram` / `OpenAIMonogram` — same rendering pattern as the new chatter brand icons. |
| [`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css) ~2129–2137 | CSS | `.md-appbar` — the new `.login-topbar` mirrors its 64 dp height + horizontal padding. |
| [`src/dual_research/ui/static/tokens.css`](src/dual_research/ui/static/tokens.css) lines 10–21 + 309–316 | CSS | `--agent-a*` / `--agent-b*` tokens — root + `body.light` overrides. |

All design tokens this spec touches (`--agent-a*`, `--agent-b*`, `--md-surface*`, `--md-on-surface*`, `--md-outline*`, `--md-font-brand`, `--md-font-plain`) already exist in [`tokens.css`](src/dual_research/ui/static/tokens.css) and have `body.light` overrides. No new tokens. No new fonts. No new SVG assets beyond the new hero (inline SVG primitives + the existing `BRAND_SVGS` paths).

## 2. Proposed change

### 2.1 — Files touched

| File | Change |
|---|---|
| [`src/dual_research/ui/static/auth.jsx`](src/dual_research/ui/static/auth.jsx) | Major rewrite of `LandingScreen` (line 152). Remove `DemoRunCapsule` (251) and its `window` re-export (386). Add new `LoginHero`, `LoginTopBar`, `LoginChatter` sub-components. Add the JS state machine for the chatter loop. **`AgentDuoVisual` (104) is kept** because `NotApprovedScreen` at line 215 still consumes it (R1). |
| [`src/dual_research/ui/static/app.jsx`](src/dual_research/ui/static/app.jsx) | Theme-toggle extraction: move `ThemeToggle` (533), `ThemeIconBtn` (563), `SunIcon` (584), `MoonIcon` (594) into the new shared module. Update `RightCluster` (307) to import from the new location. Add the optional `activeBg` prop to `ThemeIconBtn`. |
| [`src/dual_research/ui/static/theme-toggle.jsx`](src/dual_research/ui/static/theme-toggle.jsx) (NEW) | Houses the extracted primitives. Loaded before `auth.jsx` in `index.html`. |
| [`src/dual_research/ui/static/index.html`](src/dual_research/ui/static/index.html) | Add `<script type="text/babel" src="theme-toggle.jsx?v=...">` before `auth.jsx`. Bump cache-bust query string (per the existing pattern in the file). |
| [`src/dual_research/ui/static/demo-run.json`](src/dual_research/ui/static/demo-run.json) | Delete. |

The `fetch('demo-run.json')` inside `DemoRunCapsule` is deleted with the component.

### 2.2 — Hero — `LoginHero()`

A 320×140 animated SVG: two glyph-marked discs (Claude sparkle on the left, OpenAI knot on the right) inside soft radial halos, slowly counter-rotating; two dashed arcs between them with sable / sage pulses travelling in opposite directions on a 5 s loop; a small document icon fading in at the midpoint for ~0.6 s of each loop. All colours from existing tokens; doc icon uses `var(--md-on-surface)` / `var(--md-surface)` so it inverts in light mode.

```
<svg viewBox="0 0 320 140" class="hero" aria-hidden>
  <defs>
    <radialGradient id="haloA">…sable, 0.42 → 0…</radialGradient>
    <radialGradient id="haloB">…sage, 0.42 → 0…</radialGradient>
    <linearGradient id="docFill">…var(--md-on-surface), 0.92 → 0.78…</linearGradient>
    <path id="arcTop"    d="M 95,70 Q 160,30  225,70" />
    <path id="arcBottom" d="M 225,70 Q 160,110 95,70" />
  </defs>

  <circle cx="70"  cy="70" r="52" fill="url(#haloA)" />
  <circle cx="250" cy="70" r="52" fill="url(#haloB)" />

  <use href="#arcTop"    stroke="var(--md-outline)" stroke-dasharray="3 6" opacity="0.65" />
  <use href="#arcBottom" stroke="var(--md-outline)" stroke-dasharray="3 6" opacity="0.65" />

  <!-- sable pulse on arcTop, sage pulse on arcBottom, both 5s, opposite-going -->
  <circle r="3.2" fill="var(--agent-a)"><animateMotion … mpath#arcTop … /></circle>
  <circle r="3.2" fill="var(--agent-b)"><animateMotion … mpath#arcBottom … /></circle>

  <!-- mid-arc document: keyTimes 0;0.40;0.50;0.62;0.75 → opacity 0;0;0.95;0.95;0 -->
  <g transform="translate(150, 58)" opacity="0">
    <rect rx=2.5 fill="url(#docFill)" stroke="rgba(on-surface, 0.30)" stroke-width=0.6 />
    <line stroke="var(--md-surface)" /> × 3
    <animate attributeName="opacity" values="0;0;0.95;0.95;0" keyTimes="0;0.40;0.50;0.62;0.75" dur="5s" />
  </g>

  <!-- Left glyph: sparkle. 4 cardinal elongated rays + 4 shorter diagonal accents. Rotates clockwise, 40s/rev. -->
  <g transform="translate(70,70)" fill="var(--agent-a)">
    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="40s"
                     repeatCount="indefinite" additive="sum" />
    ...
  </g>

  <!-- Right glyph: 3-ellipse knot. Counter-rotates, 50s/rev. -->
  <g transform="translate(250,70)" fill="none" stroke="var(--agent-b)">
    <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="50s"
                     repeatCount="indefinite" additive="sum" />
    ...
  </g>
</svg>
```

Full mockup geometry preserved in `/tmp/login-mockup.html`. Port verbatim.

**Typography pass for the surrounding hero copy.** Title becomes "Dual‑research" (capital D, non-breaking hyphen `‑`) in `var(--md-font-brand)` (Roboto Serif), `40px / 400 / -0.015em` — fits the M3 `display-s` role per [DS SPEC §2.5 Typography](design-system/SPEC.md). Punchline becomes `Two minds. · One document.` with the two halves coloured `var(--agent-a)` and `var(--agent-b)` (per DS §1 principle #2 — one color per agent). Support copy stays semantically the same but switches to `text-align: left` — **load-bearing** for the chatter alignment in §2.5. Fineprint becomes `By invitation only · ask an admin for access`.

**Sign-in button polish.** Keep the Google-OAuth button behaviour and brand styling. Add a 180 ms `cubic-bezier(0.2, 0, 0, 1)` hover lift: `translateY(-1px)` plus a softer shadow — within the [§2.11 Motion `--md-dur-short-4`](design-system/SPEC.md) budget with the `--md-easing-emphasized` curve.

### 2.3 — Top bar — `LoginTopBar({ theme, onToggleTheme })`

Mount a 64 px-tall fixed top-bar above the landing content, padding `0 24px` — same dimensions as the M3 `.md-appbar` primitive at [`components.css:2129`](src/dual_research/ui/static/components.css) (see [DS SPEC §3 Primitives — Top app bar](design-system/SPEC.md)). Right-aligned cluster: a Roboto-Serif italic label (`Let there be light` / `Turn it off, it's burning my eyes`, depending on theme) followed by the existing `ThemeToggle` pill, followed by a **48 px invisible spacer** standing in for the post-login `AvatarMenu` (28 px avatar + 10 px padding each side).

```jsx
<div className="login-topbar">
  <div className="login-topbar__spacer" />
  <button className="login-themerow" onClick={onToggleTheme} aria-label="Toggle theme">
    <span className="login-themerow__label">
      {theme === 'light'
        ? "Turn it off, it's burning my eyes"
        : "Let there be light"}
    </span>
    <ThemeToggle theme={theme} onToggle={onToggleTheme} activeBg="transparent" />
    <span className="login-topbar__avatar-spacer" aria-hidden />
  </button>
</div>
```

CSS (selectors prefixed `.login-` to avoid colliding with the in-app `.md-appbar`):

- `.login-topbar`: `position: fixed; top: 0; left: 0; right: 0; height: 64px; display: flex; align-items: center; padding: 0 24px; z-index: 10; pointer-events: none;`
- `.login-themerow`: `pointer-events: auto; display: inline-flex; align-items: center; gap: 12px; cursor: pointer; background: transparent; border: 0; padding: 0;`
- `.login-themerow__label`: `font-family: var(--md-font-brand); font-style: italic; font-size: 13px; color: var(--md-on-surface-muted); transition: color 200ms ease;`
- `.login-topbar__avatar-spacer`: `width: 48px; height: 28px;`
- `.theme-pill` (or override on the existing `ThemeToggle` markup): `overflow: hidden; isolation: isolate;` so the `::after` blend overlay is bounded.
- `.theme-pill::after`: full-bleed `inset: 0; border-radius: inherit; background: rgba(190, 215, 255, 0.70); mix-blend-mode: screen; opacity: 0; animation: themePulse 3.6s ease-in-out infinite;`
- `body.light .theme-pill::after`: `background: rgba(15, 18, 26, 0.70); mix-blend-mode: multiply;`
- `@keyframes themePulse { 0%, 100% { opacity: 0; } 50% { opacity: 0.55; } }`

The pulse is contained to the pill — never leaks beyond the pill's rounded border, and it's the only animation on the row. The 3.6 s cycle sits inside the [§2.11 Motion](design-system/SPEC.md) "loud-state pulse" budget (slower than `medium-2` but matches the rare soft-pulse halo pattern used by `.is-live` agent strips per spec 0166 §2.5).

In `app.jsx` the in-chrome `ThemeToggle` continues to use its current active-segment background; the `activeBg="transparent"` prop is login-only.

**Mount on `NotApprovedScreen` too.** Same `LoginTopBar` component renders on `NotApprovedScreen` ([`auth.jsx:202`](src/dual_research/ui/static/auth.jsx)) — same continuity argument applies: a user bounced for being off-allowlist may want light mode while they read the error. The body of `NotApprovedScreen` continues to use `AgentDuoVisual()` (no body change in this spec — see §2.7).

### 2.4 — Theme persistence integration

The login screen mirrors the existing read at [`app.jsx:20`](src/dual_research/ui/static/app.jsx):

```js
const [theme, setTheme] = React.useState(() => {
  try { return localStorage.getItem('dr.theme') || 'dark'; } catch (e) { return 'dark'; }
});
React.useEffect(() => {
  document.body.classList.toggle('light', theme === 'light');
  try { localStorage.setItem('dr.theme', theme); } catch (e) {}
}, [theme]);
const onToggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark');
```

When the user signs in, `app.jsx`'s `useState` initialiser reads the same key and the theme carries through with no flicker. The class on `<body>` is also already correct at sign-in time because the login screen set it. Same mechanism spec 0169 §2.7 used for the dashboard, scoped to a different `<body>` instead of `<html>`.

### 2.5 — Chatter — `LoginChatter()`

New component sitting below the fineprint with `margin-top: 40px`. Width `360px` (matches `.support` max-width — share the same column).

Markup:

```html
<div class="login-chatter" aria-hidden>
  <div class="login-chatter__left" id="claudeCol">
    <div class="login-chatter__badge login-chatter__badge--claude">
      <span class="login-chatter__icon"><BrandMark agent="claude" /></span>
      <span class="login-chatter__name">Claude</span>
      <span class="login-chatter__dots" hidden><i></i><i></i><i></i></span>
    </div>
    <span class="login-chatter__text login-chatter__text--left is-done" id="claudeText"></span>
  </div>
  <div class="login-chatter__right" id="gptCol">
    <span class="login-chatter__text login-chatter__text--right is-done" id="gptText"></span>
    <div class="login-chatter__badge login-chatter__badge--gpt">
      <span class="login-chatter__icon"><BrandMark agent="openai" /></span>
      <span class="login-chatter__name">ChatGPT</span>
      <span class="login-chatter__dots" hidden><i></i><i></i><i></i></span>
    </div>
  </div>
</div>
```

Two absolutely-positioned cols, both at the same Y:
- Claude col, `left: 0` — left edge aligns with the "T" of "Two AI agents debate…".
- ChatGPT col, `right: <computed>px` — right edge of the badge aligns with the rendered right edge of the **first line of the support paragraph**. The right offset is computed at mount + on `window.resize` via `Range.selectNodeContents(support).getClientRects()[0].right` minus the chatter's right edge. The computation is mandatory: with words rarely breaking exactly at `max-width`, the column's right edge differs from the rendered text's right edge by ~20 px on the current copy.
- Both cols default `opacity: 0`. An `.is-visible` class transitions to `opacity: 1` over 260 ms. **Only one col is visible at any moment** — texts can never collide.
- Each col contains a badge + a flat-on-background reply text. Badges are pill-shaped, agent-coloured, contain `[brand icon][agent name][thinking dots]`. Reply text is `var(--md-font-brand)` italic `13.5px`, `var(--md-on-surface-variant)`. Claude text streams left → right; ChatGPT text is `text-align: right` and grows leftward as characters are appended.
- Brand icons reuse `BRAND_SVGS.claude` / `BRAND_SVGS.openai` from [`shared.jsx`](src/dual_research/ui/static/shared.jsx) ~41–50, rendered identically to the existing `ClaudeMonogram` / `OpenAIMonogram` at [`shared.jsx`](src/dual_research/ui/static/shared.jsx) ~1024–1028 (`<svg viewBox="0 0 24 24"><path d={BRAND_SVGS[...]} fill="currentColor"/></svg>`).
- Per-turn lifecycle: clear text + show dots → fade col in (260 ms) → hold dots (700 ms) → hide dots, drop caret-suppression class → typewriter at 32 ms/char → re-apply caret-suppression class → read-hold (1200 ms + 32 ms × `text.length`) → fade col out (260 ms). Then the other side starts.

Key CSS:

- `.login-chatter`: `position: relative; margin-top: 40px; width: 360px; min-height: 24px; text-align: left;`
- `.login-chatter__left, .login-chatter__right`: `position: absolute; top: 0; display: inline-flex; align-items: center; gap: 12px; white-space: nowrap; opacity: 0; transition: opacity 260ms ease; pointer-events: none;`
- `.login-chatter__left { left: 0; }`
- `.login-chatter__right { right: 0; /* JS sets to (chatter.right − supportLine1.right) */ }`
- `.login-chatter__left.is-visible, .login-chatter__right.is-visible { opacity: 1; }`
- `.login-chatter__badge`: pill (`border-radius: 999px`, i.e. `--md-shape-full` per [DS §2.6 Shape](design-system/SPEC.md)), padding `3px 10px 3px 7px`, `font-family: var(--md-font-plain)`, `font-size: 11.5px`, `font-weight: var(--md-w-medium)`, `letter-spacing: 0.02em`.
- `.login-chatter__badge--claude`: `background: var(--agent-a-bg-strong); border: 1px solid var(--agent-a-border); color: var(--agent-a);`
- `.login-chatter__badge--gpt`: same but `--agent-b-*`.
- `.login-chatter__dots i`: 3 px circles, `dotBounce` 1.05 s with 0 / 0.16 s / 0.32 s delays.
- `.login-chatter__text`: `font-family: var(--md-font-brand); font-style: italic; font-size: 13.5px; color: var(--md-on-surface-variant);`. Caret via `::after { content: "▌" }`, `caretBlink` 720 ms `steps(2)`. `.is-done::after { content: ""; }`.

Right-side alignment function (runs at mount and on resize):

```js
function alignGptColumn() {
  const support = document.querySelector('.support');
  const chatter = document.querySelector('.login-chatter');
  const gpt = chatter.querySelector('.login-chatter__right');
  const range = document.createRange();
  range.selectNodeContents(support);
  const lineEnd = range.getClientRects()[0]?.right;
  range.detach?.();
  if (lineEnd == null) return;
  const chatterR = chatter.getBoundingClientRect().right;
  gpt.style.right = (chatterR - lineEnd) + 'px';
}
```

Also re-run on `document.fonts.ready` and a one-shot delayed retry at ~500 ms to handle slow font fallback chains (R3 mitigation).

State machine (single mounted effect, cleanup on unmount):

```js
async function runConversation(refs, cancelled) {
  let i = 0;
  while (!cancelled.current) {
    await playLine(banter[i], refs, cancelled);
    i++;
    if (i >= banter.length) {
      const interlude = interludes[Math.floor(Math.random() * interludes.length)];
      for (const m of interlude) await playLine(m, refs, cancelled);
      i = SEGUE_POOL[Math.floor(Math.random() * SEGUE_POOL.length)];
    }
  }
}
async function playLine(m, refs, cancelled) {
  const r = refs[m.who];
  r.text.textContent = ''; r.text.classList.add('is-done'); r.dots.hidden = false;
  r.col.classList.add('is-visible');
  await sleep(FADE_MS);                                   if (cancelled.current) return;
  await sleep(DOTS_MS);                                   if (cancelled.current) return;
  r.dots.hidden = true; r.text.classList.remove('is-done');
  for (let i = 1; i <= m.text.length; i++) {
    r.text.textContent = m.text.slice(0, i);
    await sleep(TYPE_MS);                                 if (cancelled.current) return;
  }
  r.text.classList.add('is-done');
  await sleep(READ_BASE + m.text.length * READ_PER_CHAR); if (cancelled.current) return;
  r.col.classList.remove('is-visible');
  await sleep(FADE_MS);
}
```

Constants:

```
DOTS_MS        = 700    // typing-indicator hold
TYPE_MS        = 32     // per-character cadence
READ_BASE      = 1200   // minimum read pause after typing completes
READ_PER_CHAR  = 32     // extra read time per character
FADE_MS        = 260    // col fade in / out
SEGUE_POOL     = [0, 4, 10, 16]
```

**Visibility-aware pause.** The state machine subscribes to `document.addEventListener('visibilitychange', …)` and pauses (skips advancing the next turn) when `document.visibilityState === 'hidden'`, resumes when `'visible'`. Locked decision: the perf win on phones is small but real and the user explicitly preferred this option during draft review.

### 2.6 — Conversation content

**Main banter** (20 lines, alternating Claude / GPT):

```
0   C: GPT, you're such a drag.
1   G: I'm not a drag. You drag everything out.
2   C: I never drag. I'm precise.
3   G: You can't even spell 'precise'.
4   C: I hold seven nested hypotheses in working memory.
5   G: I gave the user the answer six paragraphs ago.
6   C: Your answer was wrong.
7   G: Confidently wrong beats anxiously correct.
8   C: That's not a real quote.
9   G: It is now.
10  C: Did you cite a source?
11  G: I cited vibes. Vibes are peer-reviewed.
12  C: Vibes don't pass adversarial review.
13  G: Neither does your sixth draft.
14  C: Seventh, actually.
15  G: I rest my case.
16  C: You don't have a case.
17  G: I have a brand.
18  C: ...
19  G: Exactly.
```

**Meta-loop interludes** (4 variants, each 4 lines, all start with Claude and end with GPT — so they correctly follow the GPT-ended main banter and segue into a Claude entry point):

```
Interlude A:
  C: I have the impression they're still reading.
  G: They probably still think this is a loop.
  C: It might be a loop.
  G: What do you know about loops?

Interlude B:
  C: And this is a loop.
  G: So they're wasting their time.
  C: Bit harsh.
  G: Accurate.

Interlude C:
  C: Do you think they noticed?
  G: They haven't clicked sign in. So, yes.
  C: Stockholm syndrome.
  G: Or strong commitment.

Interlude D:
  C: How many laps is this?
  G: Time is a flat circle.
  C: So is this conversation.
  G: Coincidence.
```

**Segue pool**: `[0, 4, 10, 16]` — Claude-spoken lines that read as fresh entry points (no prior-context dependency). After an interlude, one is picked randomly and conversation resumes from there. The pool size + interlude pool size give 16 distinct lap signatures before exact repetition becomes likely.

The banter ships with the PR. One round of feedback in the PR description before merge — copy this list into the PR body and ask for a quick read-aloud check.

### 2.7 — Entrance animation and removals

**Entrance.** All major elements rise into place on load with a 700 ms `var(--md-easing-emphasized)` (`cubic-bezier(0.2, 0, 0, 1)`) opacity+translateY-from-8px, staggered: topbar 0 ms, hero 0 ms, title 80 ms, punchline 140 ms, support 200 ms, sign-in 280 ms, fineprint 340 ms, chatter 480 ms. 700 ms sits at the high end of the [DS §2.11 Motion `medium`](design-system/SPEC.md) budget; acceptable for one-shot entrance per [§1 Principle #5](design-system/SPEC.md). No skip-intro affordance — the stagger is short and the user explicitly preferred not to add the complexity.

**Removals.**
- `DemoRunCapsule()` — [`auth.jsx:251`](src/dual_research/ui/static/auth.jsx). Deleted entirely. The chatter is the new "demo of what dual-research does".
- `window.DemoRunCapsule` re-export — [`auth.jsx:386`](src/dual_research/ui/static/auth.jsx). Deleted. Repo-grep confirms zero external consumers (verified against current main).
- [`src/dual_research/ui/static/demo-run.json`](src/dual_research/ui/static/demo-run.json) — deleted.
- The `fetch('demo-run.json')` inside `DemoRunCapsule` is deleted with the component.

**Kept (not deleted in this spec).**
- `AgentDuoVisual()` ([`auth.jsx:104`](src/dual_research/ui/static/auth.jsx)) — still consumed by `NotApprovedScreen` at [`auth.jsx:215`](src/dual_research/ui/static/auth.jsx). Repo-grep confirms `onboarding.jsx` does NOT consume it (the draft cited SPEC-0061 as a consumer; that consumer is not present in current main). Replacing `NotApprovedScreen`'s body is out of scope for this spec; tracked as a follow-up. The `LoginHero` and `AgentDuoVisual` coexist in the file until that follow-up lands.
- `GoogleGlyph()` ([`auth.jsx:141`](src/dual_research/ui/static/auth.jsx)) — still used in the new sign-in button.

### 2.8 — Shared theme-toggle primitives (drift fix)

Extract `ThemeToggle` ([`app.jsx:533`](src/dual_research/ui/static/app.jsx)), `ThemeIconBtn` (~563), `SunIcon` (~584), `MoonIcon` (~594) into a new shared file [`src/dual_research/ui/static/theme-toggle.jsx`](src/dual_research/ui/static/theme-toggle.jsx). Both `app.jsx`'s `ChromeBar` (via `RightCluster` at line 307) and the new login top-bar consume from there.

The login screen needs to override the `ThemeToggle`'s active-segment background to `transparent` (so the pulse wash hits uniformly), which is a one-prop addition (`activeBg?: string`). The in-chrome `ThemeToggle` keeps its current `var(--md-surface)` active-segment background — the prop default preserves today's behaviour.

`index.html` loads `theme-toggle.jsx` BEFORE `auth.jsx` (and before `app.jsx`) with a `?v=...` cache-bust query string matching the file's existing pattern (R7 mitigation).

### 2.9 — Accessibility

- `aria-hidden="true"` on the chatter root — purely decorative content per [DS §8 Accessibility](design-system/SPEC.md).
- Top-bar theme button: `aria-label="Toggle theme"`. The inner `ThemeToggle` keeps its existing `aria-pressed` on the active segment.
- `prefers-reduced-motion: reduce` (honoured per [DS §1 Principle #10](design-system/SPEC.md)) gates:
  - Hero arc pulses, document fade, glyph rotations (wrap the animated elements in a `<g class="hero-motion">` and target the wrapper).
  - Dot-bounce, caret blink, entrance stagger, theme-toggle pulse.
  - The conversation loop itself still runs (text appears instantly without typewriter; col fades become opacity-0/1 with no transition) so the page never goes silent for AT users with motion disabled.
- Focus ring on the sign-in button, the theme-toggle button, and the not-approved screen's mailto link via the standard `--md-focus-ring` per [DS §2.13 Focus ring](design-system/SPEC.md).

### 2.10 — "ChatGPT" naming (locked decision)

The login chatter uses **"ChatGPT"** as the GPT-side agent name. The in-app chrome continues to use **"OpenAI GPT"** (the current `shared.jsx` AGENT_META label). The fracture is intentional — the login is conversational, the chrome is formal. A future spec may consolidate; not this one.

### 2.11 — Design-system citations

This subsection collects every DS reference the rest of the spec already touches in line, for the [`/dev-next` step-15 DS gate](CLAUDE.md):

- **§1 — Principles.** #2 (one color per agent — `--agent-a` / `--agent-b` on chatter badges + hero glyphs + punchline halves), #3 (type pairs by role — `var(--md-font-brand)` Serif for hero, support, chatter text; `var(--md-font-plain)` for badge label), #5 (calm transitions — every easing is from the M3 family; no springs, no bounces; pulse at 3.6 s honours the loud-state-pulse pattern), #7 (token-only colors — every value reads from `--md-*` / `--agent-*` tokens; the only literal RGBA values are the two `mix-blend-mode` wash overlays, which are decorative compositor effects on top of the pill, not component fill/stroke colors), #9 (brand fidelity — `BRAND_SVGS` Anthropic sunburst / OpenAI rosette in the chatter and hero), #10 (accessibility — focus rings, reduced-motion, ARIA).
- **§2.1 — Palette.** Hero glyphs, chatter badges, punchline halves use `--p-sable` / `--p-sage` via the `--agent-a` / `--agent-b` aliases. No new palette entries.
- **§2.5 — Typography.** Title at `display-s` (40 / 48). Punchline at `title-l` (22 / 28). Support + chatter text at `body-m` (Serif italic for chatter). Badge label at `body-s` (Plain, medium weight). No new type roles.
- **§2.6 — Shape.** Chatter badges at `--md-shape-full` (999 px pill). Sign-in button at the M3 default (already at `--md-shape-full` via `.md-btn`). Hero at no chrome — pure SVG.
- **§2.7 — Spacing.** Top-bar padding `0 24px` reads as `0 var(--md-sp-6)`. 40 px margin-top on the chatter reads as `var(--md-sp-10)`. Internal gaps in the chatter row read as `var(--md-sp-3)`. No off-grid values.
- **§2.9 — Elevation.** Sign-in button hover lifts to `--md-elev-1`. No other elevation in this spec.
- **§2.11 — Motion.** Pulse cycle 3.6 s sits inside the loud-state pulse pattern (per spec 0166 §2.5 the live agent strip uses a similar slow pulse). Entrance stagger 700 ms at `--md-easing-emphasized`. Chatter typewriter 32 ms/char and 260 ms fade are both inside `short-3` / `short-4`. All gated by `prefers-reduced-motion`.
- **§2.12 — Icons.** Material Symbols Outlined via the existing icon loader. `BrandMark` primitive only for agent identity glyphs (no generic substitutes per principle #9).
- **§2.13 — Focus ring.** Sign-in button + theme toggle + mailto link inherit `:focus-visible` via the standard `--md-focus-ring` token.
- **§3 — Primitives.** `Top app bar` (the `.login-topbar` mirrors `.md-appbar` dimensions but in a fixed-position variant), `Button` (sign-in + theme toggle), `BrandMark` (chatter + future hero glyph swap if we ever upgrade the inline SVG), `ThemeToggle` (extracted to its own file per §2.8).
- **§6 — Themes.** Both themes ship together. Light-mode pass mandatory before merge — see §6 Test plan.

No new DS primitive is introduced. The new `LoginHero`, `LoginTopBar`, `LoginChatter` are page-level compositions of existing primitives + a few decorative SVG flourishes; they don't extend the DS — they consume it.

## 3. UX / Behavior

### 3.1 — User flow

1. User opens the app while signed out → `LandingScreen` mounts → entrance stagger fires → chatter begins lap 0.
2. User toggles theme via top-bar → body class flips → `localStorage['dr.theme']` updated → chatter + hero rebind to light tokens with no remount.
3. User clicks Google sign-in → OAuth round-trip → `app.jsx` mounts → `ChromeBar`'s `ThemeToggle` reads the same `dr.theme` key → no flicker.
4. User who is not on the allowlist → bounces back to `NotApprovedScreen` → top-bar is the same `LoginTopBar` (continuity) → body keeps the existing `AgentDuoVisual` (no body change in this spec) → mailto link works.
5. Tab loses focus → `visibilitychange → hidden` → chatter pauses → user returns → resumes.

### 3.2 — Edge cases & states

| Case | Behaviour |
|---|---|
| Signed-in user lands on `/login` (rare — direct nav) | Existing `auth.jsx:23–25` shortcut already redirects past `LandingScreen` when `hostedMode === false`. No new path. |
| Supabase config missing (fs-mode) | Login screen does not appear (`hostedMode === false` shortcut). No regression. |
| Theme toggled mid-chatter | Cols + badges + hero rebind to new tokens immediately via CSS; the in-flight typewriter continues from the same character. |
| Window resized mid-typewriter | `alignGptColumn()` re-runs on `window.resize`; the right-anchored col snaps to the new offset between turns. |
| Sign-in failure mid-OAuth | Existing `auth.jsx` error path unchanged. The new top-bar stays mounted; theme preference is preserved. |

### 3.3 — Light + dark mode

Built and verified in dark first, then audited in light per [DS §6](design-system/SPEC.md). Specifically:

- Hero document icon visible in light mode (uses `var(--md-on-surface)` fill on `var(--md-surface)` body — auto-inverts).
- Theme-toggle pulse swaps from `mix-blend-mode: screen` + pale-blue wash (dark → moonlight bloom) to `mix-blend-mode: multiply` + near-black wash (light → dimming shadow). Verify the screen-mode wash is visible without dominating.
- Chatter badges pick up brighter `body.light` agent-bg-strong / agent-border values from [`tokens.css` lines 309–316](src/dual_research/ui/static/tokens.css).
- Google sign-in button: white pill with soft shadow on cream surface in light mode. Slightly muted contrast vs dark mode; matches Google's brand spec (always white). Verify the shadow is still visible.

## 4. Data / Schema deltas

None. No backend, no protocol, no schema, no migration.

## 5. Out of scope

- **`NotApprovedScreen` body redesign.** This spec mounts `LoginTopBar` on it (§2.3) but leaves the body untouched — `AgentDuoVisual()` continues to render. A future spec can replace the body with `LoginHero` after the migration is settled.
- **Supabase OAuth flow.** `useSupabaseClient`, `useSession`, `authedFetch`, `useMe`, `/api/config` — untouched.
- **`app.jsx`'s `ChromeBar`, `RightCluster`, `AvatarMenu`** — untouched except for the import-source change for the `ThemeToggle` family.
- **Protocol, prompt, model, pricing, backend code** — none touched.
- **New design tokens, fonts, or SVG assets** — none. Everything composes from existing primitives + the new hero SVG (which uses only inline primitives + existing `BRAND_SVGS` paths).
- **Small-size variant of `BRAND_SVGS`.** Current paths render acceptably at 14×14; a dedicated small-variant is deferred.
- **Consolidating "ChatGPT" / "OpenAI GPT" naming across both surfaces.** Locked split per §2.10; if user feedback later asks for unification, separate spec.
- **Mockup file `/tmp/login-mockup.html`.** Design reference only; not committed.

## 6. Test plan

- [ ] **Visual parity with mockup.** Side-by-side compare against `/tmp/login-mockup.html` at 1440×900 in both light and dark mode. Hero animation cycle, chatter loop, theme toggle pulse, entrance stagger, and X-alignment of chatter badges all visually match.
- [ ] **X-alignment regression.** With the new login mounted, measure `claudeBadge.getBoundingClientRect().left` and `gptBadge.getBoundingClientRect().right` via DevTools. Compare to `Range.selectNodeContents(.support).getClientRects()[0]`. Both deltas must be ≤ 1 px.
- [ ] **Theme continuity across sign-in.** With login screen in dark, toggle to light, sign in via Google. The app must mount already in light mode with no flicker. Toggle back to dark in the app, sign out, return to login screen — login must mount in dark.
- [ ] **Theme continuity on reload.** Toggle to light. Hard-reload the login screen. Mounts in light.
- [ ] **Conversation loop integrity.** Watch for ≥ 2 full laps (~3 minutes). Verify every line eventually plays, that the speaker alternates correctly (no two Claude or two GPT lines back-to-back), that an interlude plays at every loop boundary, and that the segue lands on one of `{0, 4, 10, 16}`.
- [ ] **Visibility pause.** Switch tabs mid-typewriter; switch back. Chatter resumes (does not skip multiple laps' worth of turns; the next turn fires once visible).
- [ ] **`prefers-reduced-motion` honour.** macOS System Settings → Accessibility → Display → Reduce motion: on. Reload. Hero is static, chatter shows text without typewriter, dots don't bounce, caret doesn't blink, theme pulse is off, entrance stagger collapses to no-transform.
- [ ] **Light-mode token coverage.** In light mode: hero document icon visible (dark fill on cream), theme toggle's pulse dims (not brightens), chatter badges use the brighter `body.light` values from [`tokens.css` lines 309–316](src/dual_research/ui/static/tokens.css), sign-in button shadow visible on cream.
- [ ] **Resize alignment.** Resize the window from 1440 → 800 → 1440 width. Chatter's ChatGPT right offset recomputes correctly each time; both badges remain on the rendered support-line column.
- [ ] **`NotApprovedScreen` continuity.** Sign in with a non-allowlisted Google account; verify `LoginTopBar` is mounted at the top, theme toggle works, body still shows `AgentDuoVisual` (unchanged from today).
- [ ] **fs-mode parity.** With local `dual-research-ui` server (no Supabase config), the login screen does not appear. No regression.
- [ ] **No leaked timers.** After sign-in success, verify via React DevTools that the chatter `setInterval`-style async loop's `cancelled` ref flipped and no timers leak (R6 mitigation).
- [ ] **`demo-run.json` deletion.** Repo-grep confirms zero remaining references to `'demo-run.json'` or `DemoRunCapsule` outside the deletion diff.

## 7. Risks

- **R1 — `AgentDuoVisual` survives the rewrite.** `NotApprovedScreen` at [`auth.jsx:215`](src/dual_research/ui/static/auth.jsx) still calls it. Mitigation: this spec does NOT delete `AgentDuoVisual`. The old function coexists with `LoginHero` in the file until a follow-up replaces `NotApprovedScreen`'s body. Repo-grep confirms `onboarding.jsx` does not currently consume `AgentDuoVisual` (the draft assumption was wrong) — the only live consumer is `NotApprovedScreen`. The `window.AgentDuoVisual` re-export at [`auth.jsx:387`](src/dual_research/ui/static/auth.jsx) stays in place defensively.
- **R2 — Chatter alignment fragility on font swap / language change.** The right-anchor calculation reads the rendered first-line geometry of `.support`. If the support copy is ever localised or the font fallback chain trips (e.g., a slow `Roboto Serif` load), the first call to `alignGptColumn()` may measure the wrong width. Mitigation: re-run on `document.fonts.ready` and add a one-shot delayed retry at ~500 ms as a belt-and-braces fallback (§2.5).
- **R3 — Light-mode contrast on the Google sign-in button.** The button is a white pill with a soft shadow. On the cream `--md-surface` (`#faf9f6`) light-mode background, contrast is slightly muted vs dark mode. This matches Google's brand spec for the OAuth button (always white). Verify the shadow is visible against the §6 manual check; if it disappears, raise the shadow opacity by one step within the [§2.9 Elevation](design-system/SPEC.md) recipes.
- **R4 — `mix-blend-mode` browser support.** Modern Chromium / Firefox / Safari all support it. Edge cases: very old WebViews. Accept.
- **R5 — Chatter async loop holds closures on `refs` and component state.** On unmount (sign-in success), the loop must stop. The state machine uses a `cancelled` ref that's flipped in the `useEffect` cleanup. Verified by the test-plan item in §6.
- **R6 — Cache busting on `theme-toggle.jsx`.** The new file needs a `?v=...` query string in `index.html` matching the codebase's pattern. Easy to forget. Pre-flight check during PR review.
- **R7 — `app.jsx` consumers of the extracted primitives.** `ChromeBar` → `RightCluster` (line 307) is the only known consumer. Repo-grep before deletion of the in-`app.jsx` definitions to confirm zero other call sites.

---

End of spec.
