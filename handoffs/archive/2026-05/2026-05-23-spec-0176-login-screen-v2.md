---
spec: "0176"
date: 2026-05-23
version: 1.36.0
pr: "https://github.com/Lexiz/dual-research/pull/205"
---

# Spec 0176 — Login screen v2 (v1.36.0)

## What landed

The pre-auth `LandingScreen` is rewritten end-to-end. The new layout has an animated brand-glyph hero, a serif "Dual‑research" title, a two-color punchline (`Two minds.` · `One document.`), a theme toggle whose X coordinate matches the post-login chrome (no icon-jump on sign-in), and a looping Claude ↔ ChatGPT chatter band that replaces the old `DemoRunCapsule`.

### New components

| Component | File | Role |
|---|---|---|
| `LoginHero` | `src/dual_research/ui/static/auth.jsx` | 320×140 SVG: counter-rotating Claude sparkle + GPT knot, sable + sage pulses on dashed arcs, document fade-in at midpoint. All colors via tokens (`--agent-*` / `--md-on-surface` / `--md-surface`). Motion wrapped in `.hero-motion` so reduced-motion can suspend it in one rule. |
| `LoginTopBar` | `src/dual_research/ui/static/auth.jsx` | Fixed 64 dp top bar mirroring `.md-appbar`. Right-aligned cluster: serif-italic mood label + the extracted `ThemeToggle` (`activeBg="transparent"`) + 48 px invisible spacer reserving the post-login `AvatarMenu` X coordinate. `mix-blend-mode` pulse wash on the pill (`screen` in dark, `multiply` in light) on a 3.6 s cycle, scoped via `overflow: hidden; isolation: isolate;`. |
| `LoginChatter` | `src/dual_research/ui/static/auth.jsx` | Two-column Claude / ChatGPT loop. Typewriter cadence, thinking dots, blinking caret. 20 banter lines + 4 four-line interludes that periodically acknowledge the loop. Visibility-aware pause via `document.visibilitychange`. Right-edge alignment math (`Range.selectNodeContents`) anchors the GPT column to the rendered first-line right edge of the support paragraph. |

### Extraction

`ThemeToggle`, `ThemeIconBtn`, `SunIcon`, `MoonIcon` moved out of `app.jsx` into a new shared module [`src/dual_research/ui/static/theme-toggle.jsx`](src/dual_research/ui/static/theme-toggle.jsx), loaded before `auth.jsx` in `index.html`. New optional `activeBg` prop overrides the active-segment background; the login screen passes `"transparent"` so the surrounding pulse wash composites uniformly. The chrome bar uses a different toggle (`ThemeToggleSegmented` from `shared.jsx`), so nothing inside `app.jsx` consumes `ThemeToggle` anymore.

### NotApprovedScreen

Mounts the same `LoginTopBar` for theme continuity (spec §2.3). Body keeps `AgentDuoVisual` per the spec §2.7 carve-out — replacing the body is out of scope for this spec.

### Theme persistence

Both `LandingScreen` and `NotApprovedScreen` read/write `localStorage['dr.theme']`, mirroring `app.jsx`'s pattern. When the user signs in, `app.jsx`'s `useState` initialiser reads the same key and the theme carries through with no flicker.

### Entrance stagger + reduced-motion

700 ms `cubic-bezier(0.2, 0, 0, 1)` rise on each major element, 0 → 480 ms. `prefers-reduced-motion: reduce` suspends:

- Hero motion wrapper (every `animate*` inside `.hero-motion`)
- Dot bounce
- Caret blink
- Entrance stagger (collapses to no-transform)
- Theme pill pulse

The chatter loop itself still runs in reduced-motion (text appears instantly without typewriter; col fades become opacity-0/1 with no transition) so AT users with motion disabled aren't left in silence.

### Deletions

- `function DemoRunCapsule()` and `window.DemoRunCapsule` — the chatter is the new demo.
- `src/dual_research/ui/static/demo-run.json` — the fixture the capsule fetched.
- The inlined `ThemeToggle` / `ThemeIconBtn` / `SunIcon` / `MoonIcon` definitions in `app.jsx` (moved, not deleted in spirit).

### Test guard

[`tests/spec0176/test_login_screen_v2.py`](tests/spec0176/test_login_screen_v2.py) — 16 pytest static-analysis assertions:

1. `theme-toggle.jsx` exists with all four extracted symbols + `window` export.
2. `ThemeToggle` + `ThemeIconBtn` accept the `activeBg` override prop.
3. `app.jsx` no longer carries its own copies.
4. `index.html` loads `theme-toggle.jsx` BEFORE `auth.jsx`, both with the same cache-bust string.
5. `LoginHero` body has the spec §2.2 keyTimes signature + both arcs + both brand-tone pulses + `.hero-motion` wrapper.
6. `LoginTopBar` body consumes `window.ThemeToggle`, passes `activeBg="transparent"`, mounts both mood labels.
7. `LoginChatter` is defined; banter + interludes count matches the spec; segue pool is `[0, 4, 10, 16]`; visibility-aware pause + right-edge alignment math present.
8. `LandingScreen` composes the three new helpers; reads/writes `dr.theme`; punchline halves; no leftover `DemoRunCapsule` mount.
9. `NotApprovedScreen` mounts `LoginTopBar`, keeps `AgentDuoVisual`, reads `dr.theme`.
10. `function DemoRunCapsule(` is gone from `auth.jsx`.
11. `window.DemoRunCapsule` re-export gone.
12. `demo-run.json` deleted from disk.
13. No remaining `'demo-run.json'` literal in `auth.jsx`.
14. `AgentDuoVisual` + `GoogleGlyph` kept (still consumed).
15. Login CSS surfaces present in `components.css` (`.login-*`, `.theme-pill::after`, `themePulse` keyframes, light-mode `multiply` override).
16. Tokens-only-for-color rule honoured inside the spec-0176 CSS block (Google brand hexes `#fff` / `#dadce0` / `#3c4043` whitelisted; decorative `mix-blend-mode` wash overlays exempt per spec §2.11).

## Verification

Manual at 1440×900 against a force-mounted `LandingScreen` (the local dev server is fs-mode, so the login screen doesn't naturally appear — we mounted it directly through the React root for the visual UAT):

| Probe | Dark | Light |
|---|---|---|
| `.login-screen` mounted | ✅ | ✅ |
| `.login-hero` SVG renders | ✅ | ✅ |
| `.login-topbar` mounted | ✅ | ✅ |
| `.login-chatter` mounted | ✅ | ✅ |
| Title text | `Dual‑research` | same |
| Punchline | `Two minds. · One document.` | same |
| Sign-in CTA | `Sign in with Google` | same |
| Mood label | `Let there be light` | `Turn it off, it's burning my eyes` |
| Body class | (default) | `light` |
| `dr.theme` localStorage | `dark` (default) | `light` (after toggle) |
| Theme pill X | 1292–1346 px (right-aligned chrome slot) | same |
| `themePulse` animation | running | running (multiply overlay) |
| Chatter visible-col count | 1 at a time (no collision) | same |
| GPT col right offset (computed) | 52.66 px (aligned to support line) | same |
| Claude badge bg | `rgba(212, 165, 116, 0.16)` (sable tint) | (light values from `body.light` overrides) |
| GPT badge bg | `rgba(124, 196, 184, 0.16)` (sage tint) | same |

## Deploy notes

`fly deploy` clean — two new v437 machines, prior v436s destroyed.

Stale-blue sweep (`scripts/sweep_stale_blues.sh`):

```
sweep: no stale blues on dual-research-alex
```

`/api/health` returns `{"ok":true,"version":"1.36.0","backend":"supabase"}`.

## Notes

- **PR rebase + re-push, fourth time.** Same dance as 0171 / 0172 / 0175: `--push-to-main` event commits diverge the branch, `git push --force-with-lease` is sandbox-blocked, so the branch is re-pushed fresh (#204 closed → replacement #205). Shipped diff is identical. The standing workflow-fix candidates listed in prior handoffs apply.
- **fs-mode caveat.** Visual UAT was force-mounted via `React.createElement(window.LandingScreen, {client: stub})` because the local server runs in fs-mode (no Supabase config) and bypasses the login screen entirely. Production behaviour on the hosted instance is unchanged from this manipulation — the same `LandingScreen` component renders the same JSX in both contexts. The screenshots in the handoff dir reflect the force-mounted render.
- **`ThemeToggle` in `app.jsx` was dead before this spec.** The spec assumed `RightCluster` consumed `ThemeToggle` (the spec-0024 dual-icon pill); in fact `RightCluster` uses `ThemeToggleSegmented` from `shared.jsx`. The extraction is still valuable — the login screen now consumes the pill — but no `app.jsx` callsite was rewired. A minor follow-up could remove the dead comment in `app.jsx` if desired.

## Out of scope (deferred to later specs)

- **`NotApprovedScreen` body redesign.** Body keeps `AgentDuoVisual`; a future spec can replace it with `LoginHero` once that migration is justified.
- **Vitest DOM harness for `auth.jsx` + `app.jsx`.** Same deferral as the prior four specs in this drain — visual + interactive behaviour stays manual.
- **"ChatGPT" / "OpenAI GPT" naming unification.** Locked split per §2.10; consolidating is a separate spec if asked.
