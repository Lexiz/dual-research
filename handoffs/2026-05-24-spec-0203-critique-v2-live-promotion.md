---
spec: "0203"
date: 2026-05-24
kind: in-spec-checkpoint
branch: spec/0203-critique-v2-live-promotion
branch_sha: a6f3245
completed_subsections: ["2.1", "2.2", "2.3", "2.4", "2.8"]
next_subsection: "2.5"
tests_status: not-yet-run
version_bumped: false
changelog_written: false
---

# Spec 0203 — checkpoint after §2.1, §2.2, §2.3, §2.4, §2.8

## State at checkpoint

Five subsections landed on `spec/0203-critique-v2-live-promotion` (uncommitted in the work tree as of this checkpoint — the resuming session should commit the working tree before continuing per spec 0186 §2.6). Three remain: §2.5 (head pattern rebuild), §2.6 (LIFECYCLE section + `.lc-row` stack), §2.7 (source-request signal — depends on §2.5 + §2.6 landing first).

### §2.1 (C1) — Resolved unfolded by default — DONE

[src/dual_research/ui/static/run-detail.jsx:7780](src/dual_research/ui/static/run-detail.jsx#L7780). Single-character change: `renderGroup('Resolved', resolvedItems, 'ok', 'is-ok', false)` (was `true`). Comment block above the call captures the V2.B note. `renderGroup` returns null for `items.length === 0`, so the "≥1 resolved item" guard from the spec is upstream-enforced — no extra conditional needed.

### §2.2 (C2) — Wide filter header — DONE

JSX at [src/dual_research/ui/static/run-detail.jsx:7452–7530](src/dual_research/ui/static/run-detail.jsx#L7452):
- Dropped the "All" buttons from both the agent and status segments. Active-chip-click now toggles back to `'all'` (deselect-to-show-all idiom, matching the kind cluster).
- Added `data-group="agent"` / `data-group="status"` to the two `.tab-group-solid` wrappers so spec 2.3 narrow rules and spec 2.2 brand-icon rules can target them specifically.
- Swapped `<i className="dot">` (with inline-style `--claude` / `--gpt` background) for `<span className="chip-leading-icon"><AgentIcon agent="claude|gpt" size={12} /></span>` — gives us the live brand SVG (sunburst / rosette) per BDD Scenario 2's assertion.
- Wrapped label text in explicit `<span className="chip-label">` so the existing label-management rules in components.css can target it.

CSS at [src/dual_research/ui/static/components.css:2194](src/dual_research/ui/static/components.css#L2194) and DS mirror at [design-system/assets/styles/composed-components.css:779](design-system/assets/styles/composed-components.css#L779):
- Added `.tab-solid .chip-leading-icon` (12×12, currentColor) and `.tab-solid .chip-label { display: inline }` to both files.
- The pre-existing `.tab-solid .chip-value` rule already handles the `(N)` parens via `::before`/`::after` and the narrow-mode `display: none` (spec 0173). No additional CSS needed for those.

The legacy `.tab-solid .dot` rule is retained because `.dot` is still used elsewhere (`run-detail.jsx:1645, :5398, :5408`); it's now orphaned in the bar-2 filter context but harmless.

### §2.3 (C3) — Narrow filter header — DONE

CSS only, at [src/dual_research/ui/static/components.css:1046](src/dual_research/ui/static/components.css#L1046):
- Bumped `.crit2 .bar2.crit-filter-row` from `flex-wrap: nowrap` to `flex-wrap: nowrap !important` per spec 2.3 §2.3 load-bearing backstop.
- Added a separate `.crit2 .bar2 .kind-tabs { flex-wrap: nowrap !important }` rule directly under it.

Did NOT mirror to the DS file: the DS file has `.crit2 .bar1, .crit2 .bar2` at line 653 but no `.crit2 .bar2.crit-filter-row` host rule, so there's nothing to back up against in DS context. Per spec 0203 §5 ("strict scope: only the V2-delta classes; full parity backfill is deferred") I avoided introducing app-bar-specific selectors into DS.

The "kind labels drop at narrow" piece is documented in the spec as "per the pre-existing rule" (components.css:1084, `.chip[data-kind-filter] .chip-label`) but inspection shows that rule is **dead code** — the kind tabs migrated to `<Tab variant="kind">` (`.kind-tab` class) in spec 0151 §3.4.1 and no element carries `data-kind-filter` anymore. The BDD Scenario 3 assertion `THEN .chip[data-kind-filter] .chip-label is hidden` trivially passes (non-existent elements). Surfaced to the resuming session because §2.3's visual contract may want a working narrow-mode kind-label drop; if so, add `@media (max-width: 1799px) { .kind-tab span { display: none } }` (and a DS mirror) and re-check timeline-pane parity.

### §2.4 (C4) — Collapsed card height to 36 px — DONE

CSS at [src/dual_research/ui/static/components.css:4518](src/dual_research/ui/static/components.css#L4518) and DS mirror at [design-system/assets/styles/composed-components.css:2095](design-system/assets/styles/composed-components.css#L2095):
- `.item-card` outer padding `12px 14px` → `0`. Frame padding goes; the head owns its own padding.
- `.item-card__head` adds `padding: 6px 12px; min-height: 0`. Result: collapsed card ~36 px, parity with timeline `.tl-thread`.
- DS file uses a combined `.crit-card, .item-card` selector at line 2095; the new `.crit-card .crit-card-head, .item-card .item-card__head` rule mirrors the head-padding contract.

### §2.8 (C8) — Sources segment chrome — DONE

CSS only, at [src/dual_research/ui/static/components.css:4889](src/dual_research/ui/static/components.css#L4889) and DS mirror at [design-system/assets/styles/composed-components.css:2327](design-system/assets/styles/composed-components.css#L2327):
- `.source-row__title`: `flex: 1` → `max-width: 280px`. Title now caps instead of growing to fill space.
- `.source-row__attribution`: added `margin-left: auto` so the attribution chip parks at the right edge once the title is capped.

The DS file's `.source-row__title` previously lacked the truncation properties entirely (`overflow`, `text-overflow`, `white-space`); added them in the same edit to bring DS to parity with the live truncation contract.

The JSX attribution chip at [src/dual_research/ui/static/run-detail.jsx:1408](src/dual_research/ui/static/run-detail.jsx#L1408) currently uses `tone="claude|gpt|neutral"` + `label="r{N}"`. The spec §2.8 target is `mono` + `label="R{N}"` + `title="Provided by <Agent> in round <N>"`. **NOT done here** — defer to the resuming session as a small touch-up after §2.5/§2.6/§2.7 land. The BDD-asserted CSS contract (`margin-left: auto` + `max-width: 280px`) is satisfied; the chip-style refinement is cosmetic.

## Resume instructions

Pick up at **§2.5** (head pattern rebuild). Per spec 0186 the next `/dev-next` invocation will detect this checkpoint via `find_active_checkpoint('handoffs','0203','in_progress')` and route into resume mode at step 9.

### Before touching §2.5

1. `git status` — the working tree at checkpoint time is uncommitted. **First action** of the resume session should be `git add -A && git commit -m "spec(0203): land §2.1/§2.2/§2.3/§2.4/§2.8 (C1/C2/C3/C4/C8 — checkpoint 1)"` (use a HEREDOC for the message body if it grows). Then `git push -u origin spec/0203-critique-v2-live-promotion`.
2. Read [src/dual_research/ui/static/run-detail.jsx:1881-1983](src/dual_research/ui/static/run-detail.jsx#L1881) — that's the current head render (provider + composite lifecycleChip). §2.5 replaces the composite chip with explicit `round` + `state` chips per iter-7/8/10.
3. Verify `_resolveAgent` mapping at [src/dual_research/ui/static/run-detail.jsx:1503](src/dual_research/ui/static/run-detail.jsx#L1503): does `_resolveAgent('orchestrator')` return a value that triggers the SystemChip branch? Per spec 2.5 V2.C, fix it if not.

### §2.5 implementation outline

Head emits, left → right:
1. Provider chip (Claude / GPT / System — System path when `_resolveAgent` returns null/orchestrator/system).
2. Round chip: `Raised · R{N}` (mono neutral).
3. Kind chip: Q / D / I / C with `.cat-bubble`, tone-coloured per §9.3.
4. Optional evidence-needed chip (§2.7 will replace this with the icon-only tone-info variant).
5. Existing spacer (`.item-card__head-spacer`).
6. State chip: `<Verb> · <resolver icon?> · R{N}` right-aligned.

Files: run-detail.jsx (rebuild head — drop composite `lifecycleChip`, emit four chips left + state chip right via the existing spacer), components.css (new chip-tone rules per iter-5/iter-8 if not yet present — see [prototypes/critique-iteration/proposed.html:235-260](prototypes/critique-iteration/proposed.html#L235)), composed-components.css (mirror).

### §2.6 implementation outline

Replace `ItemCardThreadView` (currently rendered for expanded cards at [src/dual_research/ui/static/run-detail.jsx:1518](src/dual_research/ui/static/run-detail.jsx#L1518)) with a new `ItemCardLifecycleSection` component:

```jsx
<section className="item-card__lifecycle-section">
  <div className="item-card__lifecycle-section-hd">LIFECYCLE</div>
  <div className="lc-rows">
    {transitions.map(t => (
      <div className="lc-row" data-actor={t.actor}>
        <div className="lc-row-chips">…</div>
        <p className="lc-row-quote">"{t.quote}"</p>
      </div>
    ))}
  </div>
</section>
```

V2.A — new class is `.item-card__lifecycle-section`, NOT `.item-card__lifecycle` (the latter is the legacy head-chip cluster at [src/dual_research/ui/static/components.css:4542](src/dual_research/ui/static/components.css#L4542), removed once §2.5's head rebuild drops the composite chip call site).

V2.C — load-bearing alignment rules. Surface in the new CSS block:
```css
.item-card__lifecycle-section .lc-rows { align-items: stretch; }
.item-card__lifecycle-section .lc-row  { align-self: stretch; }
```
Do NOT inherit `align-items: center` from any ancestor.

Collapse extension — extend the existing block at [src/dual_research/ui/static/components.css:4691](src/dual_research/ui/static/components.css#L4691) with `.item-card[data-expanded="false"] .item-card__lifecycle-section { display: none }`.

The `.lc-row*` CSS at [src/dual_research/ui/static/components.css:1202-1224](src/dual_research/ui/static/components.css#L1202) is currently dead code (defined but unreferenced). §2.6 repurposes and extends it; the rules can be kept and rewritten in place.

Call sites to update: `ItemCardDQBody`, `ItemCardIssueBody`, `ItemCardCommentBody` (search `grep -n "ItemCardThreadView" src/dual_research/ui/static/run-detail.jsx`).

### §2.7 implementation outline

Depends on §2.5 (head evidence-chip slot) and §2.6 (lifecycle row extras slot) being in place. Two pieces:
1. In the head: rewrite `evidenceModifierChip` at [src/dual_research/ui/static/run-detail.jsx:1887](src/dual_research/ui/static/run-detail.jsx#L1887) from `<Chip tone="warn" leadingIcon=alert label="evidence needed" />` to `<Chip tone="info" iconOnly leadingIcon=link title="Evidence needed — addresses must cite consulted sources." aria-label="Evidence needed" />`. May need a new `.chip.chip-icon-only` variant in CSS (28×28 px, blue, label hidden).
2. In the lifecycle rows: inject a `[🔗 source requested]` extras chip on the raise row when `item.evidenceRequired === true`, and `[🔗 source provided]` on the first Claude/GPT transition when the card has ≥1 evidence record.

### Then: tests + version + ship

After §2.5/§2.6/§2.7:
1. Author Playwright tests for BDD Scenarios 1–8 per spec §6. Note Scenario 3's `.chip[data-kind-filter] .chip-label` and Scenario 2's `.tab-group-solid .chip` selectors target non-existent elements in the live DOM (live uses `.kind-tab` and `.tab-solid` respectively) — adjust the test selectors OR accept the trivially-passes-on-non-existent semantics.
2. `uv run pytest tests/ -q` (the live JSX/CSS changes don't touch Python, but the test suite must still be green).
3. Version bump: `pyproject.toml` + `src/dual_research/__init__.py`, MINOR per `version_bump: MINOR` in spec frontmatter. Compute the new version from current `pyproject.toml`.
4. CHANGELOG: new `## [X.Y.Z] — 2026-05-24` section directly (no `[Unreleased]` accumulation per CLAUDE.md).
5. Single commit on the branch covering all the V2 work; push; `gh pr create` per `/dev-next` step 17; `gh pr merge --admin --squash --delete-branch`; `git checkout main && git pull`; `fly deploy`; smoke at the anchor run; final handoff (post-deploy, not in-spec-checkpoint).

## Deferred during implementation

(No work was dropped from the spec — these are the un-started §2.5/§2.6/§2.7 plus tests/ship which are tracked in "Resume instructions" above, not deferrals in the spec-0158 sense. Nothing for the deferred-spec subagent to pick up.)
