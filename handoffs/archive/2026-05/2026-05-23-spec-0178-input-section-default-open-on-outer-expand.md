---
spec: "0178"
date: 2026-05-23
version: 1.36.1
pr: "https://github.com/Lexiz/dual-research/pull/207"
---

# Spec 0178 — Input section default-open on outer expand (v1.36.1)

## What landed

The Agent Input three-section panel no longer requires a second click on the inner chevron to reveal piece bodies. Clicking the outer **System prompt** or **Derived inputs** chevron now shows the inner piece content immediately.

### Changes (all in [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx))

| Edit | Before | After |
|---|---|---|
| `isDefaultCollapsed` helper | `function isDefaultCollapsed(canonicalKey) { … startsWith('system.') … startsWith('prior_turns.') … }` | Deleted. Replaced by a retirement comment. |
| `<InputSection>` callsite | `<InputSection key={key} piece={key} text={…} defaultCollapsed={isDefaultCollapsed(key)} isAgentDefault={…} attachmentTitles={…} />` | `defaultCollapsed` prop dropped. |
| `InputSection` signature | `function InputSection({ piece, text, defaultCollapsed, isAgentDefault, attachmentTitles })` | `defaultCollapsed` parameter dropped. |
| Inner `<CollapsibleSection>` | `defaultOpen={!defaultCollapsed}` | `defaultOpen={true}` (unconditional). |

Per-piece chevrons remain present in the rendered output; only the *default* state changed. Users who want to fold a single long piece can still click the inner chevron.

### Test guard

[`tests/test_input_section_default_open.py`](tests/test_input_section_default_open.py) — 2 pytest static-analysis assertions matching the regression-prevention test the spec body specified verbatim:

1. `test_no_is_default_collapsed_helper` — the literal string `isDefaultCollapsed` is gone from `run-detail.jsx` (locks against future per-piece-collapse experiments accidentally reintroducing the heuristic).
2. `test_input_section_inner_default_open_unconditional` — regex over `InputSection`'s body asserts the inner `<CollapsibleSection>` declares `defaultOpen={true}`.

Note: the retirement comment in `run-detail.jsx` deliberately doesn't mention the literal symbol name `isDefaultCollapsed` — that would trip the first test. The comment uses the descriptive phrase "per-piece default-collapse heuristic" instead.

## Verification

Manual at 1440×900 against anchor run `20260521-010637-dvs-backend-language-choice` (Phase 2 turn modal → Agent Input sub-tab):

| Probe | Before | After |
|---|---|---|
| Click outer "SYSTEM PROMPT" chevron → inner bodies visible | ❌ (header rows only) | ✅ 2 entries with real text inline |
| Click outer "DERIVED INPUTS" chevron → inner bodies visible | ❌ (header rows only) | ✅ 4 populated + 4 `(empty)` placeholders, all visible |
| Inner body preview text (System prompt) | n/a (hidden) | `"You are participating in a dual-agent research protocol with…"`, `"Document Verification Service — Backend Language Choice…"` |
| Per-piece chevrons still present | ✅ | ✅ (kept for user-initiated folding) |

All other consumers (`InputBriefModal`, `PreflightResponseModal`, `DocumentModal`) share the same `PromptPiecesThreeSectionView` renderer, so they pick up the fix uniformly.

## Deploy notes

`fly deploy` clean — no lease drama. Two new v438 machines, prior v437s destroyed.

Stale-blue sweep (`scripts/sweep_stale_blues.sh`):

```
sweep: no stale blues on dual-research-alex
```

`/api/health` returns `{"ok":true,"version":"1.36.1","backend":"supabase"}`.

## Notes

- **PR rebase + re-push, fifth time this session.** Same `--push-to-main` event-divergence dance — PR #206 closed via remote-branch delete, replacement #207 admin-merged. The standing fix candidate (emit events post-merge, or whitelist `--force-with-lease` for `spec/*`) is now flagged across 0171 / 0172 / 0175 / 0176 / 0178.
- **Retirement-comment quirk.** My initial retirement comment in `run-detail.jsx` mentioned the literal symbol `isDefaultCollapsed`, which trips `test_no_is_default_collapsed_helper`. Rephrased to "per-piece default-collapse heuristic" so the comment is descriptive without referencing the deleted symbol by name.

## Out of scope (per spec §6)

- Bug 4 / Bug 5 / Bug 6 from the Notion bug batch — to be queued as separate specs.
- Documenting the inner-collapse-default rule in `design-system/SPEC.md` — optional one-line clarifier; not blocking.
- Replacing the per-piece chevron with a different primitive (e.g., `<details>`) — kept as-is per spec.
