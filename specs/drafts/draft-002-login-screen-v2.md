---
kind: draft
draft_id: "002"
slug: login-screen-v2
title: Login screen v2 — animated hero, theme toggle continuity, looping chatter
type: new-feature
status: draft
created: 2026-05-22
source_session: pre-lifecycle-bootstrap
parked_from: specs/0153-login-screen-v2.md (untracked, never branched)
---


# Spec 0153 — Login screen v2: animated hero, theme toggle continuity, looping chatter

> Ship bucket: **Login-screen redesign.** Replaces `LandingScreen` in `src/dual_research/ui/static/auth.jsx:152` end-to-end. Three marquee items: (a) the existing `AgentDuoVisual` becomes a new animated convergence hero with the real Anthropic + OpenAI brand marks from `BRAND_SVGS` (shared.jsx:42-43) rotating in their own halos and pulses traversing dashed arcs while a document briefly materialises at the crossover; (b) the in-app `ThemeToggle` pill from `app.jsx:533` is hoisted into a fixed top-bar on the login screen — same X-coordinate as post-login, same `localStorage['dr.theme']` key — so the user's dark/light choice survives the sign-in boundary; (c) a new `LoginChatter` component replaces `DemoRunCapsule` entirely with a looping Claude ↔ ChatGPT conversation (20 main lines + 4 meta-loop interludes + random segue points) anchored to the column geometry of the support paragraph. Two badges (Claude on the left, ChatGPT right-anchored to the rendered end of the support line's "a") share the same row, but only one is visible at a time — fade in, type, hold, fade out, the other side fades in. Iteration history of the design is captured in the mockup at `/tmp/login-mockup.html` (not committed); this spec is the merge-ready translation of that mockup into `auth.jsx`.
> Depends on:
> - **No code dependencies** on other in-flight specs. All design tokens (`--agent-a*`, `--agent-b*`, `--md-surface*`, `--md-on-surface*`, `--md-outline*`, `--md-font-brand`, `--md-font-plain`) already exist in `tokens.css:8-302` and have `body.light` overrides at `tokens.css:309-380`. Brand-mark SVG path constants already exist in `shared.jsx:42-43` (`BRAND_SVGS.claude`, `BRAND_SVGS.openai`). Theme-toggle component already exists in `app.jsx:533-601` (`ThemeToggle`, `ThemeIconBtn`, `SunIcon`, `MoonIcon`).
> - Coexists with **0151** (critique parity) and **0152** (in flight in parallel session) — neither touches `auth.jsx` or the design-token layer, so merge order doesn't matter.
> Complexity: **M** — one file rewrite (`auth.jsx`) plus moving / re-exporting a handful of theme-toggle helpers from `app.jsx` so both screens can consume them. Larger surface area than a typical refactor because it touches a single self-contained screen comprehensively, but no protocol / backend / pricing / model code is involved.
> Targeted version bump: **MINOR** — user-facing UI redesign of a public-facing surface; no breaking changes, no schema deltas, no protocol changes. The localStorage key and Supabase OAuth flow are unchanged.

---

## 1. Context

The current `LandingScreen` (auth.jsx:152) does its job — Google sign-in, allowlist note, a small agent-duo visual — but it has three rough edges:

1. **No theme control before sign-in.** A user who prefers light mode (or dark mode, against the default) cannot express that preference until after they've signed in. The first impression is forced. The in-app `ThemeToggle` only mounts inside `ChromeBar` (app.jsx:235), which is gated behind a valid session.

2. **The `DemoRunCapsule` over-explains.** It tries to communicate what a "dual-research run" looks like via a flat dump of phases, timeline samples, critique items, outcome, and confidence. On a sign-in screen that's information without a goal — the user can't act on it, can't open it, can't read a real run, and the visual weight competes with the sign-in CTA. Two AI agents converging on a document is better shown than described, and better shown as motion than as a static card.

3. **No personality.** The product's character is two agents in conversation. The current landing communicates nothing of that. A delightful login screen is cheap to ship and disproportionately memorable; this is the one moment we have the user's full attention before they're inside the tool.

Over the design-iteration session captured in `/tmp/login-mockup.html` (live at `http://localhost:8765/login-mockup.html` during the session; the file is not committed), we converged on:

- A small animated hero showing the two agents and a document briefly materialising between them.
- Tighter copy with a serif title for "considered research tool" feel.
- A top-bar theme toggle that **lands at the same X coordinate** the post-login `ThemeToggle` occupies, so the icon stays put when the user signs in.
- A looping `Claude ↔ ChatGPT` conversation pill, replacing the demo capsule. Only one badge is visible at a time; they alternate; periodically they break the fourth wall to acknowledge the loop ("I have the impression they're still reading…").

This spec ports that final mockup state into `auth.jsx` and shares the `ThemeToggle` primitive between `auth.jsx` and `app.jsx`.

---

## 2. Goals

1. **G1 — New hero illustration.** Replace `AgentDuoVisual()` at `auth.jsx:104-138` with a 320×140 animated SVG: two glyph-marked discs (Claude sparkle on the left, OpenAI knot on the right) inside soft radial halos, slowly counter-rotating; two dashed arcs between them with sable / sage pulses travelling in opposite directions on a 5s loop; a small document icon fading in at the midpoint for ~0.6s of each loop. All colours from existing tokens; doc icon uses `var(--md-on-surface)` / `var(--md-surface)` so it inverts in light mode.

2. **G2 — Typography pass.** Title becomes "Dual-research" (capital D, non-breaking hyphen `‑`) in `var(--md-font-brand)` (Roboto Serif), `40px / 400 / -0.015em`. Punchline becomes `Two minds. · One document.` with the two halves coloured `var(--agent-a)` and `var(--agent-b)`. Support copy stays semantically the same but switches to `text-align: left` — **load-bearing** for the chatter alignment in G5. Fineprint becomes `By invitation only · ask an admin for access`.

3. **G3 — Sign-in button polish.** Keep the Google-OAuth button behaviour and brand styling. Add a 180ms `cubic-bezier(0.2, 0, 0, 1)` hover lift: `translateY(-1px)` plus a softer shadow. No other change.

4. **G4 — Top-bar theme toggle with sign-in continuity.** Mount a 64px-tall fixed top-bar above the landing content, padding `0 24px` (matches `.md-appbar` at `components.css:1922-1929`). Right-aligned cluster: a Roboto-Serif italic label (`Let there be light` / `Turn it off, it's burning my eyes`, depending on theme) followed by the existing `ThemeToggle` pill from `app.jsx:533-561`, followed by a **48px invisible spacer** standing in for the post-login `AvatarMenu` (28px avatar + 10px padding each side, measured from `app.jsx:408-410, 417`). The pill itself is static. **Only one thing animates inside the pill**: a `::after` overlay clipped by `overflow: hidden`, `mix-blend-mode: screen` with a pale-blue wash in dark mode → moonlight bloom; `mix-blend-mode: multiply` with a near-black wash in light mode → dimming shadow. `opacity: 0 → 0.55 → 0` on a 3.6s cycle. The active pill segment uses a transparent background (not `var(--md-surface)` like the in-app variant) so the wash hits both halves uniformly. Click anywhere on the row toggles the theme; persistence is the same `localStorage['dr.theme']` key that `app.jsx:19-25` already reads on mount.

5. **G5 — Looping chatter.** New `LoginChatter` component. Sits below the fineprint with `margin-top: 40px`. Width `360px` (matches `.support` max-width — share the same column). Two absolutely-positioned cols, both at the same Y:
   - Claude col, `left: 0` — left edge aligns with the "T" of "Two AI agents debate…".
   - ChatGPT col, `right: <computed>px` — right edge of the badge aligns with the rendered right edge of the **first line of the support paragraph** (the "a" at the end of "…you get a"). The right offset is computed at mount + on `window.resize` via `Range.selectNodeContents(support).getClientRects()[0].right` minus the chatter's right edge. The computation is mandatory: with words rarely breaking exactly at `max-width`, the column's right edge differs from the rendered text's right edge by ~20px on the current copy.
   - Both cols default `opacity: 0`. An `.is-visible` class transitions to `opacity: 1` over 260ms. **Only one col is visible at any moment** — texts can never collide.
   - Each col contains a badge + a flat-on-background reply text. Badges are pill-shaped, agent-coloured, contain `[brand icon][agent name][thinking dots]`. Reply text is `var(--md-font-brand)` italic `13.5px`, `var(--md-on-surface-variant)`. Claude text streams left → right; ChatGPT text is `text-align: right` and grows leftward as characters are appended.
   - Brand icons reuse `BRAND_SVGS.claude` / `BRAND_SVGS.openai` from `shared.jsx:42-43`, rendered identically to the existing `ClaudeMonogram` / `OpenAIMonogram` at `shared.jsx:943-948` (`<svg viewBox="0 0 24 24"><path d={BRAND_SVGS[...]} fill="currentColor"/></svg>`).
   - Per-turn lifecycle: clear text + show dots → fade col in (260ms) → hold dots (700ms) → hide dots, drop caret-suppression class → typewriter at 32ms/char → re-apply caret-suppression class → read-hold (1200ms + 32ms × `text.length`) → fade col out (260ms). Then the other side starts.

6. **G6 — Content: main banter + meta-loop interludes + random segue.** 20-line alternating banter (Claude/GPT/Claude/GPT, indices 0-19). After line 19 (always GPT), one of four 4-line meta interludes plays — random pick — each starting with Claude and ending with GPT. After the interlude, the next index is picked randomly from `[0, 4, 10, 16]` (all Claude entry points). Lap length varies; the reader rarely sees the same sequence twice. Full content verbatim in §3.6.

7. **G7 — Entrance animation.** All major elements rise into place on load with a 700ms `cubic-bezier(0.2, 0, 0, 1)` opacity+translateY-from-8px, staggered: topbar 0ms, hero 0ms, title 80ms, punchline 140ms, support 200ms, sign-in 280ms, fineprint 340ms, chatter 480ms.

8. **G8 — Removals.** `AgentDuoVisual`, `DemoRunCapsule`, the `demo-run.json` fetch path, and the `demo-run.json` file itself are removed. `DemoRunCapsule` is currently re-exported on `window` (auth.jsx:386); confirm no external consumers before deletion (current grep: zero).

9. **G9 — Shared theme-toggle primitives.** Extract `ThemeToggle`, `ThemeIconBtn`, `SunIcon`, `MoonIcon` from `app.jsx:533-601` into a small shared module (`src/dual_research/ui/static/theme-toggle.jsx` or expose on `window`) so both `app.jsx`'s `ChromeBar` and the new login top-bar can consume them. The login screen needs to override the `ThemeToggle`'s active-segment background to `transparent` (so the pulse wash hits uniformly), which is a one-prop addition (`activeBg?: string`).

---

## 3. Proposed change

### 3.1 Files touched

| File | Change |
|---|---|
| `src/dual_research/ui/static/auth.jsx` | Major rewrite of `LandingScreen` (lines 152-197). Remove `AgentDuoVisual` (104-138), remove `DemoRunCapsule` (251-375), remove its `window` re-export (388). Add new `LoginHero`, `LoginTopBar`, `LoginChatter` sub-components. Add the JS state machine for the chatter loop. |
| `src/dual_research/ui/static/app.jsx` | Theme-toggle extraction: move `ThemeToggle`, `ThemeIconBtn`, `SunIcon`, `MoonIcon` (lines 533-601) into the new shared module. Update `RightCluster` (line 322) to import from the new location. Add the optional `activeBg` prop to `ThemeIconBtn`. |
| `src/dual_research/ui/static/theme-toggle.jsx` (NEW) | Houses the extracted primitives. Loaded before `auth.jsx` in `index.html`. |
| `src/dual_research/ui/static/index.html` | Add `<script type="text/babel" src="theme-toggle.jsx?v=...">` before `auth.jsx`. Bump cache-bust query string. |
| `src/dual_research/ui/static/demo-run.json` | Delete. |
| `src/dual_research/ui/static/auth.jsx` | (also) remove the `DemoRunCapsule` `useState` + `useEffect` + `fetch('demo-run.json')`. |

### 3.2 Hero — `LoginHero()`

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

  <!-- Left glyph: sparkle. 4 cardinal elongated rays + 4 shorter diagonal accents.
       Slowly rotates clockwise, 40s per revolution, additive transform. -->
  <g transform="translate(70,70)" fill="var(--agent-a)">
    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="40s"
                     repeatCount="indefinite" additive="sum" />
    <!-- 4 cardinal almond rays at -28, +28, -16, +16 -->
    <!-- 4 diagonal half-rays at rotate(45), opacity 0.55 -->
  </g>

  <!-- Right glyph: 3-ellipse knot. Slowly counter-rotates, 50s per revolution. -->
  <g transform="translate(250,70)" fill="none" stroke="var(--agent-b)">
    <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="50s"
                     repeatCount="indefinite" additive="sum" />
    <ellipse rx=9 ry=22 /> × 3 (rotate 0, 60, 120)
    <circle r=2 fill="var(--agent-b)" />
  </g>
</svg>
```

Full mockup geometry preserved in the working file at `/tmp/login-mockup.html`. Port verbatim.

### 3.3 Top bar — `LoginTopBar({ theme, onToggleTheme })`

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

CSS sketch (selectors prefixed `.login-` to avoid colliding with the in-app `.md-appbar`):

- `.login-topbar`: `position: fixed; top: 0; left: 0; right: 0; height: 64px; display: flex; align-items: center; padding: 0 24px; z-index: 10; pointer-events: none;`
- `.login-themerow`: `pointer-events: auto; display: inline-flex; align-items: center; gap: 12px; cursor: pointer; background: transparent; border: 0; padding: 0;`
- `.login-themerow__label`: `font-family: var(--md-font-brand); font-style: italic; font-size: 13px; color: var(--md-on-surface-muted); transition: color 200ms ease;`
- `.login-topbar__avatar-spacer`: `width: 48px; height: 28px;`
- `.theme-pill` (or override on the existing `ThemeToggle` markup): `overflow: hidden; isolation: isolate;` so the `::after` blend overlay is bounded.
- `.theme-pill::after`: full-bleed `inset: 0; border-radius: inherit; background: rgba(190, 215, 255, 0.70); mix-blend-mode: screen; opacity: 0; animation: themePulse 3.6s ease-in-out infinite;`
- `body.light .theme-pill::after`: `background: rgba(15, 18, 26, 0.70); mix-blend-mode: multiply;`
- `@keyframes themePulse { 0%, 100% { opacity: 0; } 50% { opacity: 0.55; } }`

The pulse is contained to the pill — it never leaks beyond the pill's rounded border, and it's the only animation on the row.

In `app.jsx` the in-chrome `ThemeToggle` continues to use its current active-segment background; the `activeBg="transparent"` prop is login-only.

### 3.4 Theme persistence integration

The login screen mirrors `app.jsx:19-25`:

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

When the user signs in, `app.jsx`'s `useState` initialiser reads the same key and the theme carries through with no flicker. The class on `<body>` is also already correct at sign-in time because the login screen set it.

### 3.5 Chatter — `LoginChatter()`

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

Key CSS:

- `.login-chatter`: `position: relative; margin-top: 40px; width: 360px; min-height: 24px; text-align: left;`
- `.login-chatter__left, .login-chatter__right`: `position: absolute; top: 0; display: inline-flex; align-items: center; gap: 12px; white-space: nowrap; opacity: 0; transition: opacity 260ms ease; pointer-events: none;`
- `.login-chatter__left { left: 0; }`
- `.login-chatter__right { right: 0; /* JS sets to (chatter.right − supportLine1.right) */ }`
- `.login-chatter__left.is-visible, .login-chatter__right.is-visible { opacity: 1; }`
- `.login-chatter__badge`: pill, padding `3px 10px 3px 7px`, `border-radius: 999px`, `font-family: var(--md-font-plain)`, `font-size: 11.5px`, `font-weight: var(--md-w-medium)`, `letter-spacing: 0.02em`.
- `.login-chatter__badge--claude`: `background: var(--agent-a-bg-strong); border: 1px solid var(--agent-a-border); color: var(--agent-a);`
- `.login-chatter__badge--gpt`: same but `--agent-b-*`.
- `.login-chatter__dots i`: 3px circles, `dotBounce` 1.05s with 0 / 0.16s / 0.32s delays.
- `.login-chatter__text`: `font-family: var(--md-font-brand); font-style: italic; font-size: 13.5px; color: var(--md-on-surface-variant);`. Caret via `::after { content: "▌" }`, `caretBlink` 720ms `steps(2)`. `.is-done::after { content: ""; }`.

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

### 3.6 Conversation content

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

### 3.7 Removals

- `AgentDuoVisual()` — auth.jsx:104-138. Replaced by `LoginHero` (§3.2).
- `GoogleGlyph()` — auth.jsx:141-150. Keep, still used in the new design.
- `DemoRunCapsule()` — auth.jsx:251-375. Deleted entirely. The chatter is the new "demo of what dual-research does".
- `window.DemoRunCapsule` re-export — auth.jsx:388. Deleted. Grep confirms zero external consumers as of today.
- `demo-run.json` — `src/dual_research/ui/static/demo-run.json`. Deleted.
- The `fetch('demo-run.json')` inside `DemoRunCapsule`. Deleted with the component.

### 3.8 Accessibility

- `aria-hidden="true"` on the chatter root — purely decorative.
- Top-bar theme button: `aria-label="Toggle theme"`. The inner `ThemeToggle` keeps its existing `aria-pressed` on the active segment from `app.jsx:567`.
- `prefers-reduced-motion: reduce` media query gates:
  - Hero arc pulses and document fade (set `animation: none` on `<animate>` elements? — use a `<g class="hero-motion">` wrapper and target it).
  - Glyph rotations.
  - Dot-bounce.
  - Caret blink.
  - Entrance stagger.
  - Theme-toggle pulse.
  - The conversation loop itself still runs (text appears instantly without typewriter; col fades become opacity-0/1 with no transition).

---

## 4. Out of scope

- `NotApprovedScreen` (auth.jsx:202-231) is **not** changed in this spec. Open question §6.1 — may be revisited in a follow-up.
- The Supabase OAuth flow, `useSupabaseClient`, `useSession`, `authedFetch`, `useMe` (auth.jsx:15-100, 235-246) are untouched.
- The `/api/config` bootstrap is untouched.
- `app.jsx`'s `ChromeBar`, `RightCluster`, `AvatarMenu`, etc. — untouched except for the import-source change for `ThemeToggle` family.
- No protocol, prompt, model, pricing, or backend code is touched.
- No new design tokens. No new fonts. No new SVG assets beyond the new hero (which is composed entirely of inline-SVG primitives + the existing `BRAND_SVGS` paths).
- The mockup file at `/tmp/login-mockup.html` is the design reference; it is not committed.

---

## 5. Test plan

- [ ] **Visual parity with mockup.** Side-by-side compare against `/tmp/login-mockup.html` at 1440×900 in both light and dark mode. Hero animation cycle, chatter loop, theme toggle pulse, entrance stagger, and X-alignment of chatter badges all visually match.
- [ ] **X-alignment regression.** With the new login mounted, measure `claudeBadge.getBoundingClientRect().left` and `gptBadge.getBoundingClientRect().right` via DevTools. Compare to `Range.selectNodeContents(.support).getClientRects()[0]`. Both deltas must be ≤ 1px.
- [ ] **Theme continuity across sign-in.** With login screen in dark, toggle to light, sign in via Google. The app must mount already in light mode with no flicker. Toggle back to dark in the app, sign out, return to login screen — login must mount in dark.
- [ ] **Theme continuity on reload.** Toggle to light. Hard-reload the login screen. Mounts in light.
- [ ] **Conversation loop integrity.** Watch for ≥ 2 full laps (~3 minutes). Verify every line eventually plays, that the speaker alternates correctly (no two Claude or two GPT lines back-to-back), that an interlude plays at every loop boundary, and that the segue lands on one of `{0, 4, 10, 16}`.
- [ ] **`prefers-reduced-motion` honour.** macOS System Settings → Accessibility → Display → Reduce motion: on. Reload. Hero is static (or nearly so), chatter shows text without typewriter, dots don't bounce, caret doesn't blink, theme pulse is off.
- [ ] **Light-mode token coverage.** In light mode, the hero document icon must be visible (dark fill on cream), the theme toggle's pulse must dim (not brighten), the chatter badges' colours must use the brighter `body.light` agent-bg-strong / agent-border values from `tokens.css:309-316`.
- [ ] **Resize alignment.** Resize the window from 1440 → 800 → 1440 width. Chatter's ChatGPT right offset recomputes correctly each time; both badges remain on the rendered support-line column.
- [ ] **`NotApprovedScreen` unchanged.** Sign in with a non-allowlisted Google account; verify `NotApprovedScreen` renders identically to today (still uses old `AgentDuoVisual`? — see Risks §6.2).
- [ ] **fs-mode (no Supabase) parity.** With local `dual-research-ui` server (no Supabase config), the login screen does not appear (`hostedMode === false` shortcut in `auth.jsx:23-25` and `app.jsx:147`). No regression.
- [ ] **`window.DemoRunCapsule` consumers.** Grep entire codebase + `dist/` for `DemoRunCapsule`. Zero matches outside `auth.jsx`. (Pre-checked: confirmed today.)
- [ ] **`demo-run.json` consumers.** Grep for `'demo-run.json'`. Zero matches outside the deleted `DemoRunCapsule`.

---

## 6. Risks

- **R1 — `AgentDuoVisual` is exported on `window` (auth.jsx:387) and consumed by `onboarding.jsx` (SPEC-0061).** The old `AgentDuoVisual` cannot simply be deleted. Mitigation: keep the old component renamed (`OnboardingAgentDuo`) and isolated, or update `onboarding.jsx` to use a simpler primitive. Verify before deletion. **This is the highest-risk item in the spec** — pre-flight check before the PR.

- **R2 — `NotApprovedScreen` still calls `AgentDuoVisual` (auth.jsx:215).** If R1 keeps the old component around, no change needed; if R1 deletes it, `NotApprovedScreen` must switch to either `LoginHero` or a smaller fallback. Either is fine; pick during implementation.

- **R3 — Chatter alignment fragility on font swap / language change.** The right-anchor calculation reads the rendered first-line geometry of `.support`. If the support copy is ever localised or the font fallback chain trips (e.g., a slow `Roboto Serif` load), the first call to `alignGptColumn()` may measure the wrong width. Mitigation: re-run on `document.fonts.ready` (and add a one-shot delayed retry at ~500ms as a belt-and-braces fallback).

- **R4 — Light-mode contrast on the Google sign-in button.** The button is a white pill with a soft shadow. On the cream `--md-surface` (`#faf9f6`) light-mode background, contrast is slightly muted compared to dark mode. This matches Google's brand spec for the OAuth button (always white) so we accept the trade. Verify the shadow is visible.

- **R5 — `mix-blend-mode` browser support.** Modern Chromium / Firefox / Safari all support it. Edge cases: very old WebViews. Accept.

- **R6 — The chatter's `setInterval`-style async loop holds a closure on `refs` and component state.** On unmount (sign-in success), the loop must stop. The state machine uses a `cancelled` ref that's flipped in the `useEffect` cleanup. Verify via React DevTools that no timers leak after sign-in.

- **R7 — Cache busting on `theme-toggle.jsx`.** The new file needs a `?v=...` query string in `index.html` (the codebase's pattern at `index.html:14-48`). Easy to forget. Pre-flight check.

---

## 7. Open questions

1. **Should the login top-bar (theme toggle row) also mount on `NotApprovedScreen`?** Arguments for: same continuity argument applies — a user bounced for being off-allowlist may want light mode while they read the error. Arguments against: the screen is a dead-end, not worth the surface area. Tentative answer: yes, with the same component reused.

2. **Should the chatter pause when `document.visibilityState === 'hidden'`?** Currently the mockup keeps running. Pausing saves ~0.5W of CPU; it's not measurable on a modern laptop but matters on a phone. Tentative answer: pause on `visibilitychange → hidden`, resume on `visible`.

3. **"ChatGPT" vs "OpenAI GPT" vs "GPT".** The production identity in `shared.jsx:59` says `OpenAI GPT`. The login mockup uses `ChatGPT` per the most recent UX direction. Pick one and apply consistently across both surfaces in this spec. Tentative answer: keep `ChatGPT` on the login (more conversational, matches the chat metaphor) and `OpenAI GPT` in the app chrome (more formal, matches the rest of the agent terminology). If that's too fractured, change to `ChatGPT` everywhere.

4. **Brand-icon updates: do we want a separate small-size variant of `BRAND_SVGS`?** The current paths render fine at 14×14, but they were designed for 24×24. Some detail is lost. Tentative answer: defer — visually acceptable today.

5. **Should the entrance stagger be optional (e.g., behind a "skip intro" click)?** Repeat visitors will see it every sign-in attempt. ~700ms is short; not worth the complexity. Tentative answer: no.

6. **Banter content review.** The 20 main lines + 16 interlude lines are designed to be light, charming, and in-character. They should be read aloud by someone outside this thread before they ship. Tentative answer: include in the PR description, ask for one round of feedback before merging.
