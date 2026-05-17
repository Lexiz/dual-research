---
spec: 0061
title: Onboarding (3-screen first-time flow) + landing demo capsule
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.59.0
created: 2026-05-17
pr: ""
---

# Spec 0061 — Onboarding + landing demo capsule

## Context

Final spec of the design-system arc. Two growth surfaces (NEW-03, NEW-05).
NEW-04 (shortcuts overlay) shipped in SPEC-0059.

1. **Onboarding** — 3-screen flow shown on first sign-in. A new admin currently
   lands on an empty list with no context.
2. **Landing demo capsule** — auth-free landing page that shows a demo run
   (capsule version) before sign-in. "Show the product before asking for
   sign-in" (brief).

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **New `onboarding.jsx`** — 3-screen carousel. Screen 1: "What is dual-research?" (intro + AgentDuoVisual). Screen 2: "How a run works" (anatomy of phases). Screen 3: "Start exploring" (how to create or view a run). Pagination dots + next/prev + skip. | Mounts when `localStorage.getItem('dr_onboarded') !== 'true'`. |
| D2  | **Enhanced `LandingScreen` in auth.jsx** — instead of a new file, the existing LandingScreen gains a DemoRunCapsule below the sign-in CTA. Keeps auth boundary in one file. | Minimal surface area change. |
| D3  | **`DemoRunCapsule`** — read-only mini-render of the partner-vetting run: topic, cost, phases, 3 timeline entries, 3 critique items. Data from `demo-run.json`. | Static fixture, no interactions beyond visual. |
| D4  | **Router changes** — no router changes needed. Existing auth gate in app.jsx already shows LandingScreen when unauthenticated; onboarding gates after auth. | Simpler than D4 in the draft. |
| D5  | **Onboarding completion marker** — `localStorage.setItem('dr_onboarded', 'true')` on skip or finish. `?reset_onboarding=1` URL param resets for testing. | Simple persistence. |
| D6  | **AgentDuoVisual** — already exported on `window` from auth.jsx. Reuse directly. | No duplication needed. |
| D7  | **Cache-bust `?v=0061`** in index.html. | Per arc convention. |
| D8  | **No backend changes.** Landing demo reads from static JSON fixture; onboarding is pure frontend. | Scope discipline. |

## Files touched

- `src/dual_research/ui/static/onboarding.jsx` — **new file**; 3-screen carousel.
- `src/dual_research/ui/static/demo-run.json` — **new file**; canonical demo run fixture.
- `src/dual_research/ui/static/auth.jsx` — add DemoRunCapsule to LandingScreen.
- `src/dual_research/ui/static/app.jsx` — onboarding gate after auth check.
- `src/dual_research/ui/static/index.html` — add onboarding.jsx script; cache-bust to ?v=0061.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`.

## Out of scope

- **Backend onboarding tracking** (server-side flag) — localStorage only for MVP.
- **Sign-up flow** — current auth model is invite-based.
- **A/B testing the landing copy** — single canonical version.

## Test plan

- 735 baseline pytest green (no new Python tests — pure frontend).
- Preview-verify:
  - Open localhost:6173 in fs-mode → run list directly (no auth, no onboarding).
  - Hosted mode while signed-out → landing renders with hero + DemoRunCapsule + sign-in CTA.
  - After sign-in → onboarding 3-screen carousel renders.
  - Click through screens or skip → run list.
  - Reload → run list directly (onboarding complete).
  - `?reset_onboarding=1` → onboarding re-appears.
- Both themes. Zero console errors. ReconcileChip 5-state untouched.

## Risks

- **Demo run fixture** — subset of partner-vetting. No PII (software-arch run).
- **localStorage clearing** — users on private browsing see onboarding every visit. Known limitation.
- **Onboarding copy** — 3 screens x ~3 sentences. Matches brief's voice: calm, terminal-adjacent.

## Brief mapping

`NEW-03` (3-screen onboarding), `NEW-05` (landing demo-run capsule).
