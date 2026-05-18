---
spec: 0069
title: Run-list & chrome polish (status pills, top bar, top tabs, right cluster)
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.62.0
created: 2026-05-18
pr: ""
---

# Spec 0069 — Run-list & chrome polish

## Context

Ship 3 of 9 in the tweak-cycle arc. First "surface" spec; depends on
SPEC-0067 (chip vocabulary) and SPEC-0068 (brand icons) — both merged.
Targets the user's entry surface (run list + top chrome) which the user
described as "doesn't feel like we have a design system."

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Fixed-width status pill** — `StatusBadge` gets `min-width: 88px` + `text-align: center` | Uniform pill widths across all statuses |
| D2  | **Slightly smaller status pill** — height stays at 20px (already in `.sb`), font stays 11px in legacy `StatusBadge` | Consistent with existing chip vocabulary |
| D3  | **TOPIC column left padding** — grid gap not changed; paddingLeft added to topic cell | Breathing room between STATUS and TOPIC |
| D4  | **Top header info -> chip row** — replace `N runs · N running · cost` text with three `<Chip>` instances | Scannable structured info |
| D5  | **Top chip tone mapping** — runs: neutral, running: info, cost: neutral with $ icon | Cohesive with chip system |
| D6  | **Chrome left tabs uniform** — All runs gets `size="sm"` like Compare/Search for consistency | Same visual weight across all chrome tabs |
| D7  | **Right cluster reorganized** — ConnectionPill flattened to single-line chip | Cohesive designed cluster |
| D8  | **ConnectionPill subtitle dropped** — "localhost · 6173" removed, state-only chip | Reduces chrome noise |
| D9  | **"How it works" already a Tab** — just verify consistent size="sm" | Already correct from prior spec |
| D10 | **AppVersionChip restyle** — use `<Chip>` primitive instead of bespoke button | Cohesive with chip vocabulary |
| D11 | **DesignLanguageButton** — restyle to use Tab primitive | Consistent with chrome tabs |
| D12 | **AvatarMenu unchanged** — just verify spacing | Scope discipline |
| D13 | **Attention section headers kept** — count badge provides scan-value | Decide-and-document |
| D14 | **Cache-bust to `?v=0069`** | Per arc convention |
| D15 | **No structural changes** — sort, filter, search preserved | Polish not rework |

## Files touched

- `src/dual_research/ui/static/run-list.jsx` — header chip-ification (D4-D5); topic padding (D3)
- `src/dual_research/ui/static/components.css` — `.sb` min-width + text-align (D1)
- `src/dual_research/ui/static/app.jsx` — ConnectionPill flatten (D7-D8); AppVersionChip restyle (D10); DesignLanguageButton restyle (D11); chrome tab sizing (D6)
- `src/dual_research/ui/static/shared.jsx` — StatusBadge min-width (D1)
- `src/dual_research/ui/static/design-language.jsx` — StatusBadge spotlight (M1)
- `src/dual_research/ui/static/index.html` — cache-bust
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx`

## Out of scope

- Sort / filter / search behaviour — preserved as-is from SPEC-0055.
- Attention promotion logic — preserved.
- Run-list row content — unchanged.
- Compare / Search / Settings / How-it-works pages — not touched.

### Noted for follow-up

(None discovered.)

## Test plan

- 744 baseline pytest green.
- Preview-verify on partner-vetting run.
- Both themes verified.
- Zero console errors. Cache-bust updated. `/api/health` new version.

## Risks

- `min-width: 88px` on `.sb` is safe — `deadlocked` is the longest at 10 chars.
- ConnectionPill flatten drops visible URL; tooltip preserves it.

## Design system alignment (per arc M1)

- **`StatusBadge` codified** — `min-width: 88px`, `text-align: center` become canonical `.sb` defaults in `components.css`.
- **`ConnectionPill` retired** — replaced with a flat `<Chip>` instance.
- **`AppVersionChip` retired** — replaced with `<Chip>` primitive.
- **Run-list info line** — migrated from plain text to `<Chip>` primitives.
