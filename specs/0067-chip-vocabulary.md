---
spec: 0067
title: Chip vocabulary + code-cluster expansion
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.60.0
created: 2026-05-18
pr: https://github.com/Lexiz/dual-research/pull/67
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0067 — Chip vocabulary + code-cluster expansion

## Context

Ship 1 of 9 in the tweak-cycle arc (post-design-system-arc-v0.59.1).
This is **foundation spec A** of two — it lays down the new chip
vocabulary that every subsequent surface spec (0069–0075) consumes.
SPEC-0068 is foundation spec B (brand icons); the two can ship in
either order but both must land before the surface specs.

The site is currently riddled with cryptic two-letter chip codes
that require the reader to mentally decode them:

- **Stats chips** on timeline cards: `+6 Cl`, `+10 Cl`, `+1 I −1`,
  `+2 C`, `−20 prior Cl`, `× 3.8 reuse`, etc.
- **Critique-card public IDs**: `Q-c-r1-01`, `I-c-r1-06`,
  `Cl-c-r1-04`, `C-c-r1-01`, `d-04` — encoding
  `kind · raiser-initial · round · sequence` per
  [models.py:148-309](src/dual_research/ui/models.py).
- **Disagreement row chips**: `Disagreement d-04 · → gpt` where the
  arrow means "the side that conceded" (per run-detail.jsx:6711-13)
  — ambiguous without code-spelunking.
- **Drift-indicator chips**: `ghosted 4r`, `ghosted 3r`, `ghosted 2r`
  — the trailing letter is "rounds" but reads as code.

This spec is the **cross-cutting vocabulary pass**: drop the raw codes
in favour of structured chip clusters using full words. Per user
direction (briefing answer Q1 = "Replace code with structured chips"),
the migration is mechanical and exhaustive — every chip on every
surface adopts the new vocabulary.

This spec **does not** touch the underlying IDs (`Q-c-r1-01` stays
in the data model, the API, and the URL fragment for deep-linking).
Only the rendering changes.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **New `<CodeCluster>` primitive** in shared.jsx — renders a structured chip cluster for any public ID. Parses the ID (e.g. `I-c-r1-06`) into its components and renders `[Kind chip "Issue 06"]` · `[Brand-icon + agent name chip]` · `[Round chip "R1"]`. Accepts `{ id, kind?, hideRound?, size? }`. Falls back to raw code if parse fails. | One primitive subsumes the decoded rendering for every critique-card and disagreement row. |
| D2  | **Parser util `parseCodeId(id)`** in shared.jsx — returns `{ kind, raiser: 'claude'\|'gpt'\|'both'\|null, round: int\|null, phase: int\|null, sequence: int }` for the five known prefixes (`Q-`, `I-`, `C-`, `Cl-`, `d-`). | Pure function; testable; reused by `<CodeCluster>` and any consumer that wants to extract one component. |
| D3  | **Kind labels** — drop single-letter encoding entirely in user-facing copy: `Q-` → "Question", `I-` → "Issue", `C-` → "Comment", `Cl-` → "Claim", `d-` → "Disagreement". | Per brief §1 "calm, observability-grade language." |
| D4  | **`+N Cl` / `−N prior Cl` stats chips on timeline cards** — restyle to full-word labels: `+6 claims`, `−20 prior claims`, `+1 issue −1`, `+2 comments`. Tone unchanged (info/warn/ok). The current chip primitive's `count` + `label` props already support this; D4 is a content-only sweep across the helper that generates stats-chip arrays. | Same primitive; longer string. |
| D5  | **`× 3.8 reuse` chip** — keep numeric value, expand label: `× 3.8 reuse` → `× 3.8 token reuse` OR `reused 3.8×`. Final wording subject to space; pick the variant that fits widest column. | Cross-cutting through Consumption tab cards and timeline stats. |
| D6  | **`ghosted 4r` chip** — expand to `ghosted 4 rounds`. Truncation at ~14 chars OK; tooltip shows full. | Replace `${n}r` formatter site-wide. |
| D7  | **Disagreement row status chip** — replace ambiguous `→ gpt` / `→ claude` / `aligned` / `open` / `deadlocked` with a **chip pair**: `[raised by · Claude]` + `[conceded by · GPT]` (or `[both aligned]` when `which === 'both'`, or just `[open]` / `[deadlocked]` for unresolved). Drop the arrow notation. Render via two adjacent `<Chip>` primitives. | Per briefing 18.47 — the arrow's meaning was never decoded by users. |
| D8  | **Disagreement `R${openedRound} → R${closedRound}` chip** — keep arrow notation (this one is unambiguously "from R2 to R5"); just relabel as `opened R2 · closed R5` (no arrow) for consistency. | Arrows reserved for "feeds into" Consumption labels. |
| D9  | **Consumption tab `→ d1` / `→ hist` / `→ draft` labels** (run-detail.jsx:1006-1040) — keep arrow ("feeds into"); expand slot codes: `→ d1` → `→ feeds Claude's Phase 1 draft`, `→ d2` → `→ feeds GPT's Phase 1 draft`, `→ hist` → `→ feeds Phase 2 history`, `→ draft` → `→ feeds final draft`, `→ histp` → `→ feeds Phase 4 history`. Render truncated in cards (icon + slot name), full text in tooltips. | Keeps the "feeds" semantic clear. |
| D10 | **Critique-card headlines** in run-detail.jsx (`Question 01` / `Issue I-c-r1-06` / `Comment C-c-r1-01` / `Claim Cl-c-r1-04` / `Disagreement d-04`) — migrate to `<CodeCluster>`. The `CardHeadline` component (run-detail.jsx, used by Q/I/C/Cl/D) takes `publicId` directly today (lines 6378, 6745, 6881, 6977); refactor to take a parsed `{ kind, id }` and render via the new primitive. | Single replacement site; verifies the primitive end-to-end. |
| D11 | **Tooltip on every CodeCluster** — `title` attribute with the original raw code (`I-c-r1-06`) for searchability/debug. Power users can still copy the raw code. | No info lost, just demoted. |
| D12 | **Keep the raw code in the URL** — when a critique row is opened via `#/runs/<id>?focus=<code>`, the focus param still uses the raw code. Backwards-compatible with existing deep links. | No router change needed. |
| D13 | **`Disagreement` chip — drop the `d-`/numeric prefix entirely in clusters**: the raised-by + conceded-by chip pair already encodes everything; the `d-04` becomes a small sequence chip `04` next to the "Disagreement" kind chip. Format: `[Disagreement 04]` `[raised by Claude]` `[conceded by GPT]`. | Match the rest of the cluster style. |
| D14 | **Cache-bust bumped to `?v=0067` in index.html.** | Per arc convention. |
| D15 | **No backend changes.** All public IDs remain the same in payloads; only rendering migrates. | Scope discipline; downstream specs depend on this being a frontend-only foundation. |
| D16 | **Tests** — add `tests/test_ui_codecluster.py` covering `parseCodeId` for all five prefixes + edge cases (missing round, both-raised, malformed input falls back to raw). Frontend logic test via headless render check is out of scope (no JS test harness in this repo). | Minimal Python tests to lock parser semantics. |

## Files touched

- `src/dual_research/ui/static/shared.jsx` — add `parseCodeId(id)` util; add `<CodeCluster>` primitive; export both on `window`.
- `src/dual_research/ui/static/run-detail.jsx` — replace `CardHeadline`'s `publicId` rendering with `<CodeCluster>`; sweep stats-chip generators (search for `+${n} Q`, `+${n} Cl`, `+${n} I`, `+${n} C`, `−${n} prior`, `× ${x} reuse`, `ghosted ${n}r`); migrate disagreement status chip (lines ~6708-6713) to chip pair; migrate Consumption labels (`→ d1` etc.).
- `src/dual_research/ui/static/run-list.jsx` — sweep any stats chips (verify; may have none).
- `src/dual_research/ui/static/compare.jsx` — sweep any stats chips that appear in compare-view deltas.
- `src/dual_research/ui/static/search.jsx` — sweep any chip codes appearing in search-result previews.
- `src/dual_research/ui/static/components.css` — minor — verify `.chip` accommodates the wider labels; bump max-width if needed.
- `src/dual_research/ui/static/index.html` — cache-bust `?v=0591` → `?v=0067` (replace_all).
- `tests/test_ui_codecluster.py` — **new**; parser semantics tests.
- `pyproject.toml` + `__init__.py` + `uv.lock` + `CHANGELOG.md` + `how-it-works.jsx` VERSION_NOTES.

## Out of scope

- **Brand-icon migration** — see SPEC-0068. CodeCluster's "agent" chip in this spec uses the existing `<AgentIcon>` / agent name; 0068 swaps that for `<BrandMark>` later.
- **Critique-pane structural changes** (collapsibility, section split) — see SPEC-0072.
- **Disagreement detail-modal "PROGRESSION" rewrite** — see SPEC-0073. This spec only touches the row chip; the modal contents stay untouched.
- **Stats-chip layout / sizing** — see SPEC-0071. This spec only changes text content, not the visual chip.
- **Renaming IDs in the data model** — out of scope forever; the raw codes stay in API + URL.

## Test plan

- `tests/test_ui_codecluster.py` green: `parseCodeId('I-c-r1-06')` returns `{ kind: 'issue', raiser: 'claude', round: 1, sequence: 6 }`; same for the other prefixes; malformed falls back; both-raised (`d-04`) returns raiser=null.
- 735 baseline pytest green + new tests (~5 added).
- Preview-verify on partner-vetting (`3a4a`):
  - Critique pane: every Question / Issue / Comment / Claim / Disagreement row renders as a structured chip cluster (no raw `I-c-r1-06` visible).
  - Disagreement rows show `[Disagreement 04] [raised by Claude] [conceded by GPT]` (or appropriate variant) — no `→ gpt` arrow.
  - Timeline cards: stats chips read `+6 claims`, `−20 prior claims`, `+1 issue −1`, `× 3.8 token reuse`, `ghosted 4 rounds` — no `Cl`/`I`/`C`/`r` abbreviations.
  - Consumption tab: `→ feeds Claude's Phase 1 draft` etc.
  - Hover over any chip → tooltip shows raw code.
- Both themes; zero console errors.
- Deep link `#/runs/<id>?focus=I-c-r1-06` still works (URL contract preserved).
- Cache-bust query updated.
- `/api/health` reports new version.

## Risks

- **Stats-chip width** — `+6 claims` is ~3× wider than `+6 Cl`. Card row may wrap or overflow on narrow viewports. Mitigation: use `<ChipCluster max={N}>` (already exists per SPEC-0057) to collapse overflow into `+N`. Verify timeline card row at 1024px width.
- **`Question 01` collision** — two questions in different phases both have sequence `01`. The cluster shows `[Question 01] [Claude] [R1]` which is unique per (round, raiser) — but if a power user copies "Question 01" out of context they lose the round/agent qualifier. Mitigation: tooltip shows raw `Q-c-r1-01`.
- **`d-04` has no round in its ID** — disagreements are per-run-scoped, not per-round. The cluster renders `[Disagreement 04] [raised by Claude] [conceded by GPT]` — no round chip. Verify D7's chip pair handles the `which === null` (still open) and `which === 'both'` (aligned) cases cleanly.
- **`Cl-c-p1-01` (phase) vs `Cl-c-r1-04` (round)** — claims encode either phase OR round depending on context (per models.py:309). Parser must handle both `p${n}` and `r${n}` patterns. Tests cover this.
- **Sweep completeness** — easy to miss a string-template chip somewhere. Mitigation: grep for the patterns (`/[+-]\d+ (Q|I|C|Cl)\b/`, `/ghosted \d+r\b/`, `/× ?\d+\.?\d* reuse/`, `/→ (d1|d2|hist|draft|histp)\b/`) and verify every hit migrates.

## Brief mapping

Not a direct brief item — this is a user-feedback-driven post-arc tweak. Touches the **CMP-04 Chip** primitive's vocabulary (briefing §1 voice principles), and indirectly all surfaces that consume it.

## Design system alignment (per arc M1)

This spec amends the design system; the new vocabulary is canonical, not a per-surface override:

- **New primitives** added to the system:
  - `<CodeCluster id kind? hideRound? size?>` — first-class primitive for any structured public ID rendering. Exposed on `window`. SPEC-0068 (which ships immediately after this one) establishes the Design page's `<ComponentSpotlights>` scaffolding; if 0068 is already merged when this spec ships, ADD a CodeCluster spotlight there as part of M1 alignment. If 0067 ships before 0068, the spotlight is added to design-language.jsx by 0068 as part of its DNA reskin work — leave a clear note in the handover so 0068 picks it up.
  - `parseCodeId(id)` utility — companion pure function; documented in `shared.jsx`.
- **Vocabulary rule (codified)** — chips that previously used compact codes (`+6 Cl`, `+1 I −1`, `× 3.8 reuse`, `ghosted 4r`, `→ d1`, etc.) now use full words. This is the SYSTEM PATTERN going forward. Document in CHANGELOG and via SPEC-0068's DNA Construction section ("Vocabulary discipline: full words, never abbreviated codes").
- **Chip primitive (`<Chip>`)** — no API change; just a `max-content` width allowance verified for the longer labels. If a width-cap is currently in `components.css`, raise it.
- **Disagreement status chip pair pattern** — codified: any "two-state agent attribution" (raised-by + conceded-by) renders as two adjacent `<Chip>` instances with brand icons. Pattern reused by SPEC-0073 (Q/D detail) + future similar surfaces.
- **Frozen brief reference** — the brief's `DESIGN-SYSTEM.md` is NOT edited (frozen per arc M1). The in-app Design Language page becomes the live SoT post-SPEC-0068.

---

## Pre-draft notes for the implementing session

- **Start with the parser**: `parseCodeId` is pure and testable in Python via dedent + a tiny JS-equivalent test. Write it first, lock semantics with tests, then build `<CodeCluster>`.
- **Search patterns** to find every chip site:
  ```
  grep -nE "\\+\\$\\{|\\+[0-9]+ (Q|I|C|Cl|Cl\\b)|ghosted [0-9]+r|× ?[0-9]+\\.?[0-9]* reuse|→ (d1|d2|hist|draft|histp)\\b" src/dual_research/ui/static/*.jsx
  ```
- **Disagreement chip pair (D7)** is the trickiest bit. Render logic:
  - `status === 'open' && deadlocked` → single chip `[deadlocked]` (warn tone)
  - `status === 'open'` → single chip `[open]` (warn tone)
  - `status === 'resolved-both'` → single chip `[aligned]` (ok tone) — no raiser/conceder split since both moved
  - `status === 'resolved-claude'` → `[raised by GPT]` + `[conceded by Claude]` (note: if Claude conceded, GPT was the side that didn't move — verify against `d.raisedBy` field). Use AGENT_META for icon + color.
  - `status === 'resolved-gpt'` → `[raised by Claude]` + `[conceded by GPT]` similarly.
  - **Verify with the data model**: `d.raisedBy` may be `'claude' | 'gpt' | 'both'`; conceder is encoded in `d.status` suffix. Cross-check by opening a real disagreement in the partner-vetting run.
- **D9 (Consumption arrow labels)** — only the chip TEXT changes; the destination-slot color logic (run-detail.jsx ~923, ~1005-1040) is unchanged.
- **D13 (Disagreement sequence chip)** — `d-04` parses to `sequence=4`. Render `Disagreement 04` (zero-padded to 2 digits to match the source format).
- **Don't pre-empt SPEC-0068** — in this spec, the "agent" chip inside CodeCluster uses `<AgentIcon>` + name as today. 0068 will swap the icon component; the API of CodeCluster stays stable.
- **Backward-compat alias** — if any external code path (search index? URL?) references the raw `I-c-r1-06`, keep that alive in `aria-label` / `data-code` attributes so screen readers + selector hooks still find rows.
- **Verify the existing stats-chip generator** lives in shared.jsx near `toneFromColor` (per SPEC-0057 handover D10 carve-out). That's the single point where `+6 Cl` strings are produced; ideal edit site.
