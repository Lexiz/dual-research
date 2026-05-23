---
kind: dev
spec: "0179"
slug: critique-card-body-redundancies-and-parity-verification
title: "Fix: critique-card body redundancies (verdict row, bottom anchor, seen-row) + mandate side-by-side parity grid in PR"
type: bug
label: bug
version_bump: PATCH
target_version: 1.36.2
status: deployed
depends_on: ["0172", "0173"]
complexity: S
created: 2026-05-22
queued_at: "2026-05-22T22:30:00Z"
started_at: "2026-05-23T10:11:30Z"
merged_at: "2026-05-23T10:17:44Z"
deployed_at: "2026-05-23T10:20:53Z"
pr: "https://github.com/Lexiz/dual-research/pull/209"
handover: "handoffs/2026-05-23-spec-0179-critique-card-body-redundancies-and-parity-verification.md"
failure_step: ""
source_session: bug-spec-batch-2205-claude
promoted_from_draft: ""
---

# Spec 0179 — Fix: critique-card body redundancies + mandate side-by-side parity grid

> **Type:** bug  |  **Severity:** P1  |  **Affects:** every critique card across all four kinds (Question / Disagreement / Issue / Comment) in the Critique pane and any embedded item-card surface. Live since spec 0151 §3.4 introduced the per-kind body sub-renderers.
> **Bump:** PATCH — bug fix only; no schema, no API, no new component. Net diff ≤ 30 LOC.
> **Evidence:** Notion bug-batch page "Specs 2205 (Claude)" Bug 4 (`https://www.notion.so/Specs-2205-Claude-36899f3e507f802a90f6df0566d9704b`). Design-system reference targets: [design-system/notion-issues/ISSUES.md](design-system/notion-issues/ISSUES.md) Issues 7 / 8 / 9 / 10 and the four anchor screenshots `design-system/notion-issues/screenshots/{07-question-card-duplicate,08-disagreement-card,09-issue-card,10-comments-card}.png`. Spec 0172 (queue pos 5) drops the ID chip + the literal `**` markdown title. Spec 0173 (queue pos 2) drains 0166 / 0167 / 0168 deferrals — head rebuild + lifecycle chip + evidence-inline + resolver identity + expanded-view QuestionThread + per-source attribution + per-card collapse. Bug 4's residual scope after those two ship is the **body-side redundancies** Issues 7-10 still complain about plus the **chronic verification-gap process failure**.

---

## 1. Reproduction

**Environment.** Live app `https://dual-research-alex.fly.dev` after specs 0172 and 0173 have shipped. Any run with a mix of resolved + open critique items across all four kinds — anchor run `20260521-010637-dvs-backend-language-choice`. Viewport 1440 × 900 or wider.

**Steps.**

1. On the run detail page, open the **Critique** pane.
2. Scroll to a **terminal Question** or **Disagreement** card (state = `resolved` or `acknowledged`).
3. Read the head, then the body.

**Expected:** The card's state + lifecycle is conveyed once — through the head's lifecycle chip (per spec 0173 §2.6). The body shows the raise + transition rows in chronological order, with the resolution text appearing only as part of the resolve turn's `text` field. No verdict line above the turn rows.

**Actual:** The body opens with a `.item-card__verdict` row reading `[stateChip] — <resolutionText>` that re-states the state from the head and re-states the resolution text that will reappear inside the resolve turn row below. Three repetitions of the same information per terminal D/Q card. This is exactly ISSUES.md Issue 7 ("we start with the question … then we have a quote and then we say Claude round one raised and we repeat the exact same question") and Issue 8 ("we start with a resolved batch and just at the top we already have a resolved batch so that's not needed").

4. Open an **Issue** card or a **Comment** card with an anchor quote.

**Expected:** The anchor quote appears once, inline near the top of the body (matching screenshots 09 and 10).

**Actual:** The same anchor text renders **twice** per card — once as the inline `<blockquote class="item-card__quote-inline">quote: <anchorText></blockquote>` near the top, and again as a `<blockquote class="item-card__anchor item-card__anchor--bottom">"<anchorText>"</blockquote>` at the very bottom of the body. Issues 9 ("followed again by something random, which is the exact same quote. Followed again by the exact same quote") and 10 ("the exact same thing as issue number nine can also be said about the comments") explicitly call this out.

5. Stay on the same Issue or Comment card. Scan the chip cluster between the body paragraph and the bottom-anchor blockquote.

**Expected:** The lifecycle chip in the head (per 0173 §2.6 — `raised · r1 · Claude · last seen r2`) is the only place that carries raised-by-agent + first-seen-round + last-seen-round metadata.

**Actual:** The same metadata is repeated as a chip row in the body: `[flagged by Claude] [first seen R1] [last seen R2]` for Issue cards and `[noted by Claude] [R1]` for Comment cards. Once spec 0173 §2.6 lands the lifecycle chip in the head, this body-side `seen-row` becomes the redundant second copy Issue 9 calls out ("flagged by Claude, first seen in round 1, last seen in round 2, and then followed again by something random").

Across the four cards, the user counts at least three duplicated elements per card (verdict-state, anchor-quote, seen-metadata) — the cumulative effect is what the Notion bug calls "thoroughness complaint as much as a parity complaint."

## 2. Root cause hypothesis

Spec 0151 §3.4 rewrote `ItemCard` into per-kind sub-renderers ([src/dual_research/ui/static/run-detail.jsx:1657](src/dual_research/ui/static/run-detail.jsx:1657)) and added body-side elements (`.item-card__verdict`, `.item-card__seen-row`, the `.item-card__anchor--bottom` blockquote) that were already covered elsewhere — either by the head chips (0151's own header at [run-detail.jsx:1786-1800](src/dual_research/ui/static/run-detail.jsx:1786)) or by the inline anchor at the top of each body. The verification protocol for 0151 was a screenshot-grid review but the handoff PR did not embed the grid, so the duplications shipped silently. Specs 0172 and 0173 then queued to attack adjacent symptoms (the ID chip, the head rebuild, the lifecycle chip, the expanded view restructure, the per-card collapse) — but neither of them retires the body-side redundancies introduced by 0151.

Concrete code anchors:

- **Terminal-verdict row** in `ItemCardDQBody`: [src/dual_research/ui/static/run-detail.jsx:1547-1553](src/dual_research/ui/static/run-detail.jsx:1547) — renders `[stateChip] — <resolutionText>`. The same `stateChip` appears in the head at [run-detail.jsx:1789](src/dual_research/ui/static/run-detail.jsx:1789), and the `<resolutionText>` (sourced from `lastTerminal.reason`) also renders inside the resolve `ItemCardTurnRow` at [run-detail.jsx:1565-1573](src/dual_research/ui/static/run-detail.jsx:1565) via the `text={t.reason}` prop. Three displays of the same data per card.
- **Bottom-anchor blockquote** in `ItemCardIssueBody`: [src/dual_research/ui/static/run-detail.jsx:1621-1623](src/dual_research/ui/static/run-detail.jsx:1621) — renders `<blockquote class="item-card__anchor item-card__anchor--bottom">"<anchorText></blockquote>`. The same `anchorText` already renders inline at [run-detail.jsx:1607-1609](src/dual_research/ui/static/run-detail.jsx:1607).
- **Bottom-anchor blockquote** in `ItemCardCommentBody`: [src/dual_research/ui/static/run-detail.jsx:1650-1652](src/dual_research/ui/static/run-detail.jsx:1650) — same pattern, duplicates the inline anchor at [run-detail.jsx:1640-1642](src/dual_research/ui/static/run-detail.jsx:1640).
- **Seen-row chip cluster** in `ItemCardIssueBody`: [src/dual_research/ui/static/run-detail.jsx:1613-1620](src/dual_research/ui/static/run-detail.jsx:1613) — `[flagged by Claude] [first seen R1] [last seen R2]`. Spec 0173 §2.6 places the same raised-by + lifecycle data into a single chip in the **head**. Once 0173 ships, the seen-row is the redundant second copy.
- **Seen-row chip cluster** in `ItemCardCommentBody`: [src/dual_research/ui/static/run-detail.jsx:1643-1649](src/dual_research/ui/static/run-detail.jsx:1643) — same redundancy at lower density (just `[noted by Claude] [R1]`).

The **chronic process gap** is the larger root cause: every prior critique-card spec (0138, 0141, 0144, 0151) wrote a long anatomy block and cited the same four reference screenshots, but none of them embedded a before/after image grid into the PR description at merge time. The Notion Bug 4 frames this as the failure mode that has to be caught — past PRs claimed parity in prose without rendered-output proof.

## 3. Fix

Two parallel deliverables — narrow JSX edits + a design-system process gate. No new component is introduced. No CSS class is added; some unused ones are dropped if they have no remaining consumer.

**DS citations.** The card primitives this spec touches are governed by [design-system/SPEC.md](design-system/SPEC.md) §3 (Chip, Blockquote — implicit through `<blockquote>` use), §4.1 (Critique pane composition rules), and §4.7 (Sources segment, since SourceRow is adjacent but not modified here). The new process gate lands as a sub-section under §4.1 — "ItemCard parity changes MUST embed a side-by-side image grid in the PR description before merge."

### 3.1 — Drop the terminal-verdict row in `ItemCardDQBody`

[src/dual_research/ui/static/run-detail.jsx:1547-1553](src/dual_research/ui/static/run-detail.jsx:1547). Delete the entire `{isTerminal && resolutionText && (...)}` block:

```jsx
// DELETE these lines:
{isTerminal && resolutionText && (
  <div className="item-card__verdict">
    <Chip tone={stateTone} size="sm">{stateLabel}</Chip>
    <span className="item-card__verdict-sep">—</span>
    <span className="item-card__verdict-text">{resolutionText}</span>
  </div>
)}
```

The `lastTerminal` / `resolutionText` locals at lines 1536-1538 become dead — delete them too. The resolve verb + resolution text continue to render as the **last** `ItemCardTurnRow` inside the `.item-card__turns` list — that's the single canonical surface for resolution text.

**Behaviour after.** Terminal D/Q cards open with the turn-count meta row and proceed straight into chronological turns. The state remains visible via the lifecycle chip in the head (per 0173 §2.6); no body-side state echo.

**CSS hygiene.** The `.item-card__verdict`, `.item-card__verdict-sep`, `.item-card__verdict-text` rules in [src/dual_research/ui/static/components.css](src/dual_research/ui/static/components.css) and [design-system/assets/styles/composed-components.css](design-system/assets/styles/composed-components.css) become unused. Delete them in both files (CLAUDE.md's "live + DS-canonical must stay in sync" rule). If the validator/grep finds no remaining consumer, the deletion is clean; if any other surface still uses them, scope this drop conservatively and leave the rules in place.

### 3.2 — Drop the bottom-anchor blockquote in `ItemCardIssueBody`

[src/dual_research/ui/static/run-detail.jsx:1621-1623](src/dual_research/ui/static/run-detail.jsx:1621). Delete:

```jsx
// DELETE:
{anchorType && anchorText && (
  <blockquote className="item-card__anchor item-card__anchor--bottom">"{anchorText}"</blockquote>
)}
```

The inline anchor at [run-detail.jsx:1607-1609](src/dual_research/ui/static/run-detail.jsx:1607) is preserved — that's the single canonical anchor surface.

### 3.3 — Drop the bottom-anchor blockquote in `ItemCardCommentBody`

[src/dual_research/ui/static/run-detail.jsx:1650-1652](src/dual_research/ui/static/run-detail.jsx:1650). Same delete as §3.2, applied to the Comment renderer. The inline anchor at [run-detail.jsx:1640-1642](src/dual_research/ui/static/run-detail.jsx:1640) is preserved.

**CSS hygiene for §3.2 + §3.3.** The `.item-card__anchor--bottom` modifier in both CSS files becomes unused. Delete the rule. Leave `.item-card__anchor` itself in place (the inline anchor still uses it when rendered as `<blockquote class="item-card__quote-inline">` — distinct class, but the base `.item-card__anchor` may still apply on other surfaces; grep before pruning).

### 3.4 — Drop the seen-row chip cluster in `ItemCardIssueBody`

[src/dual_research/ui/static/run-detail.jsx:1613-1620](src/dual_research/ui/static/run-detail.jsx:1613). Delete:

```jsx
// DELETE:
<div className="item-card__seen-row">
  <Chip tone={_actorTone(item.raiser)} size="sm">
    <i className="dot" style={{ background: `var(--${item.raiser === 'openai' ? 'gpt' : item.raiser})` }} />
    {' '}flagged by {_actorLabel(item.raiser)}
  </Chip>
  <Chip tone="muted" size="sm">first seen R{firstSeen}</Chip>
  <Chip tone="muted" size="sm">last seen R{lastSeen}</Chip>
</div>
```

The `firstSeen` / `lastSeen` locals at lines 1595-1598 become dead — delete them. The raised-by + round metadata continues to render in the head's lifecycle chip (per 0173 §2.6).

**Edge case.** If 0173 §2.6's lifecycle chip surfaces only `raised · r1 · Claude` and **not** the last-seen-round, then dropping the seen-row loses the "last seen R2" signal. Implementer must verify: read the merged 0173 §2.6 chip text at branch-cut time. If the lifecycle chip does NOT carry last-seen-round, keep one chip — `<Chip tone="muted" size="sm">last seen R{lastSeen}</Chip>` — inline at the position the seen-row used to occupy, and drop only the other two chips. Re-evaluate during implementation.

### 3.5 — Drop the seen-row chip cluster in `ItemCardCommentBody`

[src/dual_research/ui/static/run-detail.jsx:1643-1649](src/dual_research/ui/static/run-detail.jsx:1643). Same delete as §3.4, applied to the Comment renderer. The `round` local at line 1634 becomes dead — delete it.

**CSS hygiene for §3.4 + §3.5.** The `.item-card__seen-row` rule in both CSS files becomes unused after the delete. Drop it.

### 3.6 — Codify the parity-verification gate in `design-system/SPEC.md` §4.1

Add a sub-section to §4.1 (Critique pane composition rules) — exact wording subject to implementer's tone-matching with the surrounding prose, content roughly:

> **ItemCard parity verification.** Any spec that proposes a change to `ItemCard`, its per-kind sub-renderers (`ItemCardDQBody`, `ItemCardIssueBody`, `ItemCardCommentBody`), or the `.item-card__*` CSS chrome MUST include in its PR description a **side-by-side image grid** comparing the live-app rendering of one card per kind in both collapsed and expanded states against the reference screenshots at `design-system/notion-issues/screenshots/07-question-card-duplicate.png`, `08-disagreement-card.png`, `09-issue-card.png`, `10-comments-card.png`. Eight fresh captures (4 kinds × 2 states) next to the four reference shots. PRs that cite design-system parity without embedding this grid are blocked from merge. The grid replaces verbal claims of "matches the screenshot" — the chronic failure mode this rule catches is specs that cited the reference screenshots in prose but did not verify the rendered output.

This sub-section lands in `design-system/SPEC.md` only — no other DS file is modified for §3.6. The rule is enforced by the human reviewer at merge time; no CI gate is introduced (a screenshot-diff CI rig is a multi-spec lift outside scope here).

### 3.7 — Net diff summary

- **`src/dual_research/ui/static/run-detail.jsx`** — ~25 LOC removed across `ItemCardDQBody`, `ItemCardIssueBody`, `ItemCardCommentBody`. No additions beyond a possible one-chip retention in §3.4's edge-case branch.
- **`src/dual_research/ui/static/components.css`** — drop `.item-card__verdict`, `.item-card__verdict-sep`, `.item-card__verdict-text`, `.item-card__anchor--bottom`, `.item-card__seen-row` rules (subject to grep confirming no remaining consumer).
- **`design-system/assets/styles/composed-components.css`** — mirror the CSS deletes.
- **`design-system/SPEC.md`** — add the §4.1 parity-verification sub-section.
- **`design-system/assets/Design System v2.html`** §13 (ItemCard examples) — re-render examples without the deleted elements so the canonical sample matches the live render.

No new files. No event-stream changes. No backend changes. No DS primitive changes.

## 4. Regression-prevention test

Source-level pytest matching the [tests/test_ui_jsx_syntax.py](tests/test_ui_jsx_syntax.py) pattern — locks the absence of the redundant elements in `run-detail.jsx` so they cannot regress silently. New file `tests/test_item_card_body_redundancies.py`:

```python
"""Spec 0179 — critique-card body redundancies must stay deleted.

ItemCard's per-kind sub-renderers (DQ / Issue / Comment) historically
duplicated state/anchor/seen-row metadata that the head's chips and the
inline anchor already carry. This test locks the deletions so a future
"defensive add-back" PR cannot reintroduce the redundancies without
explicit, named approval (modify this test).
"""
import re
from pathlib import Path

JSX = Path(__file__).parent.parent / "src" / "dual_research" / "ui" / "static" / "run-detail.jsx"


def _read():
    return JSX.read_text()


def test_item_card_dq_no_terminal_verdict_row():
    text = _read()
    # The `.item-card__verdict` div in ItemCardDQBody was the third repetition
    # of the resolution text — dropped by spec 0179 §3.1.
    assert "item-card__verdict" not in text, (
        "item-card__verdict class is gone from run-detail.jsx per spec 0179 §3.1. "
        "If reintroducing the verdict row deliberately, modify this test and "
        "name the spec that justifies it."
    )


def test_item_card_no_bottom_anchor_blockquote():
    text = _read()
    # The `.item-card__anchor--bottom` blockquote duplicated the inline anchor
    # in both ItemCardIssueBody and ItemCardCommentBody — dropped by §3.2 + §3.3.
    assert "item-card__anchor--bottom" not in text, (
        "item-card__anchor--bottom is gone from run-detail.jsx per spec 0179 §3.2/§3.3. "
        "The inline anchor at the top of the body is the only canonical anchor surface."
    )


def test_item_card_no_seen_row():
    text = _read()
    # The `.item-card__seen-row` chip cluster duplicated the lifecycle chip
    # 0173 §2.6 places in the head — dropped by §3.4 + §3.5.
    assert "item-card__seen-row" not in text, (
        "item-card__seen-row is gone from run-detail.jsx per spec 0179 §3.4/§3.5. "
        "Raised-by + round metadata lives in the head lifecycle chip (spec 0173 §2.6)."
    )


def test_item_card_dq_resolution_text_preserved_in_turn_rows():
    text = _read()
    # The resolve-turn ItemCardTurnRow still carries the resolution text via
    # text={t.reason}. If this regresses we lose the resolution text entirely
    # (since §3.1 dropped the verdict row).
    # Scope the regex to ItemCardDQBody to avoid false positives elsewhere.
    m = re.search(
        r"function\s+ItemCardDQBody\b.*?function\s+",
        text, re.DOTALL,
    )
    assert m is not None, "ItemCardDQBody body span not found"
    body = m.group(0)
    assert re.search(r"<ItemCardTurnRow[^>]*text=\{t\.reason\}", body), (
        "ItemCardDQBody must still pass `text={t.reason}` to the per-turn rows "
        "after spec 0179 dropped the standalone verdict row — otherwise the "
        "resolution text disappears entirely from terminal D/Q cards."
    )
```

**Before-fix behaviour.** The first three tests fail — current `run-detail.jsx` contains all three CSS class strings. The fourth test passes already.

**After-fix behaviour.** All four tests pass.

- [ ] Test: `tests/test_item_card_body_redundancies.py::test_item_card_dq_no_terminal_verdict_row` — locks §3.1 deletion.
- [ ] Test: `tests/test_item_card_body_redundancies.py::test_item_card_no_bottom_anchor_blockquote` — locks §3.2 + §3.3 deletion.
- [ ] Test: `tests/test_item_card_body_redundancies.py::test_item_card_no_seen_row` — locks §3.4 + §3.5 deletion.
- [ ] Test: `tests/test_item_card_body_redundancies.py::test_item_card_dq_resolution_text_preserved_in_turn_rows` — guards against the regression where dropping the verdict row also accidentally severs the per-turn text plumbing.

## 5. Blast radius

- **Files touched:** 1 JSX source + 2 CSS files (live + DS-canonical) + `design-system/SPEC.md` + `design-system/assets/Design System v2.html` (§13 examples) + 1 new test file. Net source diff ~25 LOC removed, ~20 LOC of CSS removed, ~5 lines of SPEC.md prose added.
- **Consumers of the deleted body elements.** `ItemCard` is the only consumer of `ItemCardDQBody`, `ItemCardIssueBody`, `ItemCardCommentBody`. `ItemCard` renders inside the Critique pane via the `CritiqueItems` parent (search for `<ItemCard` in `run-detail.jsx` — there is exactly one call site). No other surface in the codebase calls the per-kind body sub-renderers.
- **CSS classes deleted.** `.item-card__verdict`, `.item-card__verdict-sep`, `.item-card__verdict-text`, `.item-card__anchor--bottom`, `.item-card__seen-row` — grep `src/`, `design-system/` for each before deleting; if any other surface (e.g. how-it-works mockup, design-system v2 HTML page) still references the class, leave the rule and scope this drop to JSX only. The test in §4 locks only the JSX side, so a leftover CSS rule does not break the regression test.
- **No interaction with 0173.** 0173 modifies the **head** (§2.5 head rebuild, §2.6 lifecycle chip, §2.7 evidence inline, §2.8 resolver) and the **expanded view** (§2.9 QuestionThread bubbles) and **per-source attribution** (§2.10) and **per-card collapse** (§2.11). This spec modifies the **body sub-renderers only** at lines 1497-1655 — disjoint regions of `run-detail.jsx`. No merge conflict expected even if 0173 lands first.
- **No interaction with 0172.** 0172 drops the ID chip in head + short-codes in DQ/Issue bodies + renders the Issue body via `<Markdown>`. The lines 0172 deletes (1505, 1565, 1750 per Notion's anchors) are disjoint from this spec's deletes (1547-1553, 1613-1620, 1621-1623, 1643-1649, 1650-1652).
- **No data-layer changes.** All deletes are render-side. No event-stream or wire-format change. No DS primitive change.

## 6. Out of scope

- **0173's territory in full.** §2.5 head rebuild, §2.6 lifecycle chip, §2.7 evidence inline, §2.8 resolver identity, §2.9 expanded-view QuestionThread, §2.10 per-source attribution, §2.11 per-card collapse — ALL of 0168 §2.2-§2.9's deferral catalogue ships under spec 0173. This spec does NOT duplicate, supersede, or expand that scope.
- **0172's territory in full.** Drop of the head ID chip + drop of body short-codes + Markdown rendering of the Issue body title (no more literal `**`). This spec does NOT re-implement Bug 2's fixes.
- **Bug 1** (split-pane Agent Input dual-card → single column) — spec 0171.
- **Bug 3** (three-section input panel one-click reveal) — spec 0178.
- **Bug 5** (Consumption tab V2 unfolded-card anatomy) — to be queued separately.
- **Bug 6** (All-Runs stale `running` status) — to be queued separately.
- **A visual-regression CI rig** for the four reference screenshots. The §3.6 verification gate is human-enforced at PR-review time — a CI rig that diffs Playwright captures against the reference images is a multi-spec lift (test harness, snapshot baseline storage, tolerance tuning) outside Bug 4's residual scope.
- **The Issue 9 "open status while issue says resolved" data contradiction.** Issue 9 calls out "we follow up with a status that says open while the issue says resolved — I'm not sure: is it open, is it resolved?" If this is still observable on the live app post-0173, it is a **data-layer** problem (the item's `currentState` disagreeing with its transitions' terminal verb), distinct from this spec's render-side cleanup. Surface as a separate bug spec after 0173 ships if still reproducible.
- **The Issue 9 body sequence reordering** ("title then quote then paragraph" vs the prescribed "title then body then quote"). 0172 §3.4.3 in the Notion Bug 2 description explicitly mentions rendering the Issue body via `<Markdown>` end-to-end — once that lands, the title + paragraph become one Markdown block and the inline anchor follows. Sequence concerns are subsumed by 0172. If a residual sequence issue remains post-0172, surface separately.
- **Issue 11** (double divider in Phase 4 first card) and any other ISSUES.md entry beyond 7-10 — out of Bug 4's scope per Notion's per-issue focus.

## 7. Risks

- **Resolution text disappears entirely on terminal D/Q cards if the resolve turn row's `text={t.reason}` plumbing has any gap.** Mitigation: test in §4 (`test_item_card_dq_resolution_text_preserved_in_turn_rows`) asserts the prop wiring stays. Verification: open a terminal Disagreement card post-fix and confirm the resolution text is visible in the resolve turn row. If `t.reason` is sometimes empty for a resolved transition (e.g. system-resolved with no commentary), the card simply shows the turn with no quoted text — that's the design-system contract per the screenshot.
- **Last-seen-round signal lost if 0173 §2.6's lifecycle chip omits it.** Mitigation: implementer must read the merged 0173 §2.6 chip composition at branch-cut and apply the §3.4 edge-case fallback (keep a single `last seen R{lastSeen}` chip inline) if the chip does not carry that field. The fallback is one-line; the regression test in §4 still passes because it asserts the absence of the `.item-card__seen-row` class, not the absence of a single chip.
- **Stale `design-system/assets/Design System v2.html` §13 example.** If the §13 ItemCard sample still renders the deleted elements after this spec ships, the design-system reference and the live app diverge — the next person who cites the DS will copy the stale example. Mitigation: §3 explicitly lists the v2.html re-render as a file to change. Verification: open the design-system page at `/#/language` post-deploy and confirm the §13 sample matches the live Critique pane.
- **Premature merge before 0172 + 0173 land.** This spec's `depends_on: ["0172", "0173"]` is hard-required: dropping the seen-row before 0173 §2.6 lifecycle chip ships would lose the raised-by + round metadata entirely (no head chip carrying it). `/dev-next` honours `depends_on` per the spec-lifecycle contract; manual merges must respect the same ordering.
- **The §3.6 parity-verification gate becomes a paper rule if reviewers don't enforce it.** Mitigation: the rule's first instance is **this spec's own PR**, which must embed the 8-capture grid as proof. Setting that precedent at merge time is what makes the rule load-bearing. CLAUDE.md's "rendered-output-based verification" standing rule for UI specs reinforces this — the grid is now the canonical artifact.
- **CSS class deletion mismatch.** If a class is deleted from `src/dual_research/ui/static/components.css` but a different surface still references it elsewhere, the live app gets unstyled markup. Mitigation: grep `src/`, `design-system/`, `scripts/` for each class name before deleting; if a residual consumer exists, leave the rule in place and scope this spec's CSS hygiene to JSX-only deletes. The regression test in §4 locks the JSX side and is independent of CSS-side cleanup.
